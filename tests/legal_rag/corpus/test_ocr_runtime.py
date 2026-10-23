import hashlib
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from legal_rag.corpus import ocr_runtime as runtime  # noqa: E402
from legal_rag.corpus.compiler import compile_input, json_bytes, manifest_digest  # noqa: E402
from legal_rag.corpus.__main__ import main  # noqa: E402
import test_input_and_compile as input_fixture  # noqa: E402
from test_pdf_extraction import saved_result  # noqa: E402


class OcrRuntimeTest(unittest.TestCase):
    def prepare(self, temporary):
        root = Path(temporary) / "archive"
        helper = input_fixture.InputAndCompileTest()
        path, manifest = helper._prepare(root)
        old = manifest["assets"][0]["sha256"]
        payload = b"%PDF-1.7\nsynthetic transport fixture"
        digest = hashlib.sha256(payload).hexdigest()
        metadata = json.loads((root / "assets" / (old + ".json")).read_bytes())
        metadata.update(sha256=digest, archive_key="raw/" + digest,
                        byte_length=len(payload), media_type="application/pdf")
        helper._write(root / "assets" / (digest + ".json"), metadata)
        (root / "raw" / digest).write_bytes(payload)
        item_id = hashlib.sha256(manifest["assets"][0]["source_item"].encode()).hexdigest()
        item_path = root / "items" / (item_id + ".json")
        item = json.loads(item_path.read_bytes())
        item["asset_sha256s"] = [digest]
        helper._write(item_path, item)
        reference = manifest["assets"][0]
        reference["sha256"] = reference["evidence"]["source_asset_sha256"] = digest
        reference["evidence"]["locator"] = "pdf:pages:1-2"
        permission_path = root / manifest["processing_permission"]["path"]
        permission = json.loads(permission_path.read_bytes())
        permission["source_asset_sha256s"] = [digest]
        helper._write(permission_path, permission)
        manifest["processing_permission"]["sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest()
        manifest["manifest_hash"] = manifest_digest(manifest)
        helper._write(path, manifest)
        native = Path(temporary) / "native"
        native.mkdir()
        document, run = saved_result()
        run["source_sha256"] = digest
        helper._write(native / "document.json", document)
        helper._write(native / "run.json", run)
        mapping = Path(temporary) / "results.json"
        helper._write(mapping, {"schema_version": "ocr-results/1", "results": {digest: str(native)}})
        return path, mapping, Path(temporary) / "output", digest

    def test_saved_import_repeats_and_compiles_without_docker(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, mapping, output, digest = self.prepare(temporary)
            first = runtime.extract_input(path, output, results_path=mapping)
            second = runtime.extract_input(path, output, results_path=mapping)
            self.assertEqual((first["result"], second["result"]), ("new", "unchanged"))
            self.assertEqual(first["index"], second["index"])
            index = json.loads(Path(first["index"]).read_bytes())
            self.assertEqual(list(index["extractions"]), [digest])
            result = compile_input(path, "2025-01-01", output, extraction_index=Path(first["index"]))
            draft = json.loads(Path(result["draft"]).read_bytes())
            tree = draft["content"]["trees"][0]
            self.assertTrue(tree["accounting"]["exactly_once"])
            self.assertIn("pdf_structure_unqualified", tree["structural_issues"])
            self.assertIn("ocr_review_required", result["blockers"])
            self.assertEqual(draft["legal_admission"], "not_requested")

    @staticmethod
    def sidecar_export(native):
        """Rewrite a saved inline-native result as OCR-Lab's layout-only export."""
        document = json.loads((native / "document.json").read_bytes())
        run = json.loads((native / "run.json").read_bytes())
        (native / "native").mkdir()
        for page in document["pages"]:
            sidecar = {"page_number": page["page_number"], "image_size": page["image_size"],
                       "native": page.pop("native")}
            (native / "native" / f"page_{page['page_number']:04d}.json").write_bytes(json_bytes(sidecar))
        run["export"] = {"format": "dotsmocr-layout/2", "native": "native/page_NNNN.json",
                         "markdown": "document.md"}
        (native / "document.json").write_bytes(json_bytes(document))
        (native / "run.json").write_bytes(json_bytes(run))

    def test_layout_only_export_reads_native_sidecars_and_replays_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, mapping, output, digest = self.prepare(temporary)
            inline = runtime.extract_input(path, Path(temporary) / "inline-output", results_path=mapping)
            self.sidecar_export(Path(temporary) / "native")
            result = runtime.extract_input(path, output, results_path=mapping)
            self.assertEqual(result["extractions"][digest]["extraction_id"],
                             inline["extractions"][digest]["extraction_id"])
            evidence = Path(result["native_evidence"][digest])
            self.assertTrue((evidence / "native/page_0002.json").is_file())
            compiled = compile_input(path, "2025-01-01", output, extraction_index=Path(result["index"]))
            tree = json.loads(Path(compiled["draft"]).read_bytes())["content"]["trees"][0]
            self.assertTrue(tree["accounting"]["exactly_once"])
            (evidence / "native/page_0002.json").write_bytes(b"{}")
            with self.assertRaises(ValueError):
                compile_input(path, "2025-01-01", output / "draft-output", extraction_index=Path(result["index"]))
            self.assertFalse((output / "draft-output").exists())

    def test_layout_only_export_rejects_missing_mismatched_or_embedded_native(self):
        for case in ("missing", "mismatch", "embedded", "format"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                path, mapping, output, _ = self.prepare(temporary)
                native = Path(temporary) / "native"
                self.sidecar_export(native)
                sidecar = native / "native/page_0002.json"
                if case == "missing":
                    sidecar.unlink()
                elif case == "mismatch":
                    sidecar.write_bytes(json_bytes({**json.loads(sidecar.read_bytes()), "page_number": 1}))
                elif case == "embedded":
                    document = json.loads((native / "document.json").read_bytes())
                    document["pages"][1]["native"] = json.loads(sidecar.read_bytes())["native"]
                    (native / "document.json").write_bytes(json_bytes(document))
                else:
                    run = json.loads((native / "run.json").read_bytes())
                    run["export"]["format"] = "dotsmocr-layout/3"
                    (native / "run.json").write_bytes(json_bytes(run))
                with self.assertRaises(ValueError):
                    runtime.extract_input(path, output, results_path=mapping)
                self.assertFalse(output.exists())

    def test_permission_and_wrong_source_refusal_write_no_output(self):
        for case in ("permission", "wrong_source", "partial", "unsafe_output"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                path, mapping, output, _ = self.prepare(temporary)
                if case == "permission":
                    (path.parent / "reviews/fixture-permission.json").unlink()
                elif case in {"wrong_source", "partial"}:
                    run_path = Path(temporary) / "native/run.json"
                    run = json.loads(run_path.read_bytes())
                    if case == "wrong_source":
                        run["source_sha256"] = "d" * 64
                    else:
                        run.update(source_pages=3)
                    run_path.write_bytes(json_bytes(run))
                else:
                    output = path.parent / "raw"
                before = input_fixture.InputAndCompileTest._snapshot(path.parent)
                with self.assertRaises((ValueError, OSError)):
                    runtime.extract_input(path, output, results_path=mapping)
                self.assertEqual(input_fixture.InputAndCompileTest._snapshot(path.parent), before)
                if case != "unsafe_output":
                    self.assertFalse(output.exists())

    def test_tampered_index_or_extraction_cannot_compile(self):
        for case in ("index", "extraction", "native"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                path, mapping, output, digest = self.prepare(temporary)
                result = runtime.extract_input(path, output, results_path=mapping)
                index_path = Path(result["index"])
                index = json.loads(index_path.read_bytes())
                if case == "index":
                    index["input_hash"] = "d" * 64
                    index_path.write_bytes(json_bytes(index))
                elif case == "extraction":
                    extraction_path = index_path.parent / index["extractions"][digest]["path"]
                    extraction = json.loads(extraction_path.read_bytes())
                    extraction["pages"][0]["regions"][0]["bbox"][0] = 9
                    extraction_path.write_bytes(json_bytes(extraction))
                else:
                    evidence = output / "ocr-evidence" / index["extractions"][digest]["native_evidence_id"]
                    (evidence / "document.json").write_bytes(b"{}")
                with self.assertRaises(ValueError):
                    compile_input(path, "2025-01-01", output / "draft-output", extraction_index=index_path)
                self.assertFalse((output / "draft-output").exists())

    def test_runtime_failure_has_retained_structured_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, _, output, _ = self.prepare(temporary)
            config = Path(temporary) / "config.json"
            config.write_bytes(json_bytes({"schema_version": "ocr-provider/1", "provider": "ocr-lab",
                                           "engine": "dotsmocr", "lab_root": temporary}))
            with patch.object(runtime, "run_ocr_lab", side_effect=RuntimeError("Docker is unavailable")):
                with self.assertRaises(ValueError):
                    runtime.extract_input(path, output, config_path=config)
            receipts = list(output.glob("ocr-runs/*/run.json"))
            self.assertEqual(len(receipts), 1)
            self.assertEqual(json.loads(receipts[0].read_bytes())["status"], "failed")
            self.assertFalse(list(output.glob("extractions/index-*.json")))

    def test_fresh_runtime_provenance_survives_saved_evidence_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, mapping, output, digest = self.prepare(temporary)
            config = Path(temporary) / "config.json"
            config.write_bytes(json_bytes({"schema_version": "ocr-provider/1", "provider": "ocr-lab",
                                           "engine": "dotsmocr", "lab_root": temporary}))

            def execute(settings, payload, source_hash, receipt):
                (receipt / "runtime.json").write_bytes(json_bytes({"image_id": "sha256:fixture"}))
                return Path(temporary) / "native"

            with patch.object(runtime, "run_ocr_lab", side_effect=execute):
                first = runtime.extract_input(path, output, config_path=config)
            mapping.write_bytes(json_bytes({"schema_version": "ocr-results/1", "results": {
                digest: first["native_evidence"][digest]}}))
            replay = runtime.extract_input(path, output / "replayed", results_path=mapping)
            self.assertEqual(first["extractions"][digest]["extraction_id"],
                             replay["extractions"][digest]["extraction_id"])
            self.assertEqual(compile_input(path, "2025-01-01", output / "draft",
                                          extraction_index=Path(replay["index"]))["result"], "new")

    def test_cli_imports_without_a_target_date_or_ocr_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, mapping, output, _ = self.prepare(temporary)
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = main(["extract", "--input", str(path), "--output-dir", str(output),
                             "--ocr-results", str(mapping)])
            self.assertEqual(code, 0)
            self.assertTrue(Path(json.loads(stdout.getvalue())["index"]).is_file())

    def test_command_adapter_stages_content_addressed_pdf_and_uses_unique_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            lab = Path(temporary) / "lab with spaces"
            for name in ("compose.yaml", "docker/Dockerfile.dotsmocr", "scripts/new_ocr_pdf.py",
                         "config/new_ocr_models.json", "config/dotsmocr_prompt.txt", "config/dotsmocr_picture_ocr.json"):
                path = lab / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(json_bytes({"max_tokens": 512}) if name.endswith("picture_ocr.json") else b"fixture")
            receipt = Path(temporary) / "run-unique"
            receipt.mkdir()
            commands = []

            def execute(command, **kwargs):
                commands.append(command)
                text = "running healthy\n" if "{{.State.Status}}" in " ".join(command) else "sha256:image\n"
                return subprocess.CompletedProcess(command, 0, stdout=text)

            with patch.object(runtime.subprocess, "run", side_effect=execute):
                native = runtime.run_ocr_lab({"provider": "ocr-lab", "engine": "dotsmocr", "lab_root": str(lab),
                                              "picture_ocr_max_tokens": 2048,
                                              "picture_ocr_failure_policy": "retain_unresolved"},
                                             b"%PDF-fixture", "a" * 64, receipt)
            self.assertEqual((lab / "input" / ("legal-rag-" + "a" * 64 + ".pdf")).read_bytes(), b"%PDF-fixture")
            self.assertEqual(native, lab / "results/legal-rag/run-unique")
            settings = next((lab / "results/legal-rag-runtime").glob("*/config/dotsmocr_picture_ocr.json"))
            self.assertTrue(json.loads(settings.read_bytes())["recover_repetitions"])
            command = commands[-1]
            self.assertEqual(command[command.index("--project-directory") + 1], str(lab))
            self.assertEqual(command[command.index("--output") + 1], "/data/results/legal-rag/run-unique")
            snapshot_config = next((lab / "results/legal-rag-runtime").glob("*/config/dotsmocr_picture_ocr.json"))
            self.assertEqual(json.loads(snapshot_config.read_bytes())["max_tokens"], 2048)
            self.assertEqual(json.loads(snapshot_config.read_bytes())["failure_policy"], "retain_unresolved")
            self.assertEqual(json.loads((lab / "config/dotsmocr_picture_ocr.json").read_bytes())["max_tokens"], 512)
            self.assertNotIn("--rotation-retry", command)
            self.assertNotIn("rotation_retry", json.loads((receipt / "runtime.json").read_bytes()))
            turned = Path(temporary) / "run-turned"
            turned.mkdir()
            with patch.object(runtime.subprocess, "run", side_effect=execute):
                runtime.run_ocr_lab({"provider": "ocr-lab", "engine": "dotsmocr", "lab_root": str(lab),
                                     "rotation_retry": True}, b"%PDF-fixture", "a" * 64, turned)
            self.assertIn("--rotation-retry", commands[-1])
            self.assertTrue(json.loads((turned / "runtime.json").read_bytes())["rotation_retry"])
            with self.assertRaises(ValueError):
                runtime.run_ocr_lab({"provider": "ocr-lab", "engine": "dotsmocr", "lab_root": str(lab),
                                     "rotation_retry": "yes"}, b"%PDF-fixture", "a" * 64, turned)

    def test_output_subdirectory_symlink_cannot_write_into_raw_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, mapping, output, _ = self.prepare(temporary)
            output.mkdir()
            try:
                (output / "extractions").symlink_to(path.parent / "raw", target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlinks unavailable: {error}")
            before = input_fixture.InputAndCompileTest._snapshot(path.parent)
            with self.assertRaises(ValueError):
                runtime.extract_input(path, output, results_path=mapping)
            self.assertEqual(input_fixture.InputAndCompileTest._snapshot(path.parent), before)
            self.assertFalse((output / "ocr-evidence").exists())

    def test_foreign_native_evidence_cannot_be_bound_by_rehashing_an_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, mapping, output, digest = self.prepare(temporary)
            first = runtime.extract_input(path, output, results_path=mapping)
            index_path = Path(first["index"])
            index = json.loads(index_path.read_bytes())
            old = output / "ocr-evidence" / index["extractions"][digest]["native_evidence_id"]
            evidence = json.loads((old / "evidence-manifest.json").read_bytes())
            run = json.loads((old / "run.json").read_bytes())
            run["source_sha256"] = "d" * 64
            payload = json_bytes(run)
            evidence["run.json"] = hashlib.sha256(payload).hexdigest()
            evidence_id = runtime.content_hash(evidence)
            destination = output / "ocr-evidence" / evidence_id
            destination.mkdir()
            for name in evidence:
                (destination / name).write_bytes(payload if name == "run.json" else (old / name).read_bytes())
            (destination / "evidence-manifest.json").write_bytes(json_bytes(evidence))
            index["extractions"][digest]["native_evidence_id"] = evidence_id
            index["index_id"] = runtime.content_hash({k: v for k, v in index.items() if k != "index_id"})
            index_path.write_bytes(json_bytes(index))
            with self.assertRaises(ValueError):
                compile_input(path, "2025-01-01", output / "draft", extraction_index=index_path)

    def test_malformed_runtime_response_records_failure_instead_of_running_forever(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, _, output, _ = self.prepare(temporary)
            native = Path(temporary) / "native"
            document = json.loads((native / "document.json").read_bytes())
            document["pages"][0]["native"] = None
            (native / "document.json").write_bytes(json_bytes(document))
            config = Path(temporary) / "config.json"
            config.write_bytes(json_bytes({"schema_version": "ocr-provider/1", "provider": "ocr-lab",
                                           "engine": "dotsmocr", "lab_root": temporary}))

            def execute(settings, payload, source_hash, receipt):
                (receipt / "runtime.json").write_bytes(json_bytes({"image_id": "sha256:fixture"}))
                return native

            with patch.object(runtime, "run_ocr_lab", side_effect=execute):
                with self.assertRaises(ValueError):
                    runtime.extract_input(path, output, config_path=config)
            receipts = list(output.glob("ocr-runs/*/run.json"))
            self.assertEqual(json.loads(receipts[0].read_bytes())["status"], "failed")


if __name__ == "__main__":
    unittest.main()
