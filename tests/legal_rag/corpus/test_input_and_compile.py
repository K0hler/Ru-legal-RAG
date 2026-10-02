from contextlib import redirect_stderr, redirect_stdout
import copy
import hashlib
from io import StringIO
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "sources"))

from legal_rag.corpus.__main__ import main  # noqa: E402
from legal_rag.corpus.compiler import compile_input, json_bytes, load_input, manifest_digest  # noqa: E402
from legal_rag.sources.acquisition import acquire_fixture  # noqa: E402
from legal_rag.sources.handoff import build_edition_candidate  # noqa: E402
import test_candidate_handoff as handoff_fixture  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures"
TARGET = "2025-01-01"


class InputAndCompileTest(unittest.TestCase):
    def _prepare(self, root):
        acquire_fixture(FIXTURES / "sample_act.txt", FIXTURES / "sample_act.json", root)
        permission = json.loads((FIXTURES / "processing_permission.json").read_bytes())
        self._write(root / "reviews/fixture-permission.json", permission)
        manifest = json.loads((FIXTURES / "corpus_input_v1.json").read_bytes())
        manifest["archive_root"] = "."
        path = root / "input.json"
        self._write(path, manifest)
        return path, manifest

    @staticmethod
    def _write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes(value))

    @staticmethod
    def _snapshot(root):
        return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    def _cli(self, path, output, target=TARGET):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["compile", "--input", str(path), "--target-date", target, "--output-dir", str(output)])
        self.assertEqual(code, 0, stderr.getvalue())
        return json.loads(stdout.getvalue())

    def test_cli_repeat_accounts_every_character_and_preserves_raw_and_approved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            path, manifest = self._prepare(root)
            self._write(root / "approved/build.json", {"sentinel": "approved"})
            before = self._snapshot(root)
            output = Path(temporary) / "m1"
            first = self._cli(path, output)
            retained = self._snapshot(output)
            second = self._cli(path, output)
            self.assertEqual(first["result"], "new")
            self.assertEqual(second, {**first, "result": "unchanged"})
            self.assertEqual(self._snapshot(output), retained)
            self.assertEqual(self._snapshot(root), before)
            draft = json.loads(Path(first["draft"]).read_bytes())
            tree = draft["content"]["trees"][0]
            source = (FIXTURES / "sample_act.txt").read_bytes()
            blocks = sorted([*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]],
                            key=lambda block: block["source_span"]["byte_start"])
            self.assertEqual("".join(block["text"] for block in blocks).encode("utf-8"), source)
            cursor = 0
            for block in blocks:
                span = block["source_span"]
                self.assertEqual(span["byte_start"], cursor)
                self.assertEqual(source[span["byte_start"]:span["byte_end"]], block["text"].encode("utf-8"))
                cursor = span["byte_end"]
            self.assertEqual(cursor, len(source))
            accounting = tree["accounting"]
            for unit in ("chars", "bytes"):
                self.assertEqual(accounting["total_" + unit], sum(accounting[name + "_" + unit]
                                 for name in ("parsed", "unresolved", "excluded")))
            self.assertEqual([node["address"] for node in tree["nodes"]], ["act/title", "act/article/1", "act/article/2"])
            self.assertIn("unresolved_structure", first["blockers"])
            self.assertEqual(draft["legal_admission"], "not_requested")
            self.assertEqual(first["manifest_hash"], manifest["manifest_hash"])
            report = Path(first["report"]).read_text(encoding="utf-8")
            self.assertIn("Приложение А", report)
            self.assertIn("utf8:bytes:", report)
            self.assertIn(manifest["assets"][0]["sha256"], report)
            self.assertNotIn("<script", report)
            self.assertNotIn("<link", report)

    def test_input_validation_failures_write_nothing(self):
        cases = ("missing_permission", "unknown_input_version", "unknown_permission_version", "denied_permission",
                 "permission_scope", "corrupt_raw", "missing_raw", "missing_metadata", "wrong_length",
                 "identity", "act_identity", "path_escape", "permission_path_escape", "misbound_evidence",
                 "wrong_url", "wrong_locator", "unknown_target", "bad_date", "manifest_hash", "unknown_field", "duplicate_asset")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "archive"
                path, manifest = self._prepare(root)
                asset = manifest["assets"][0]
                digest = asset["sha256"]
                raw_path = root / "raw" / digest
                metadata_path = root / "assets" / f"{digest}.json"
                permission_path = root / manifest["processing_permission"]["path"]
                metadata = json.loads(metadata_path.read_bytes())
                permission = json.loads(permission_path.read_bytes())
                target = TARGET
                if case == "missing_permission":
                    permission_path.unlink()
                elif case == "unknown_input_version":
                    manifest["schema_version"] = "corpus-input/99"
                elif case in {"unknown_permission_version", "denied_permission", "permission_scope"}:
                    key, value = {"unknown_permission_version": ("schema_version", "processing-permission/99"),
                                  "denied_permission": ("decision", "denied"),
                                  "permission_scope": ("act_identity", "Another Act")}[case]
                    permission[key] = value
                    self._write(permission_path, permission)
                    manifest["processing_permission"]["sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest()
                elif case == "corrupt_raw":
                    raw_path.write_bytes(b"corrupt")
                elif case == "missing_raw":
                    raw_path.unlink()
                elif case == "missing_metadata":
                    metadata_path.unlink()
                elif case == "wrong_length":
                    metadata["byte_length"] += 1
                    self._write(metadata_path, metadata)
                elif case == "identity":
                    asset["declared_identity"] = "Wrong source identity"
                elif case == "act_identity":
                    manifest["act_identity_claim"]["declared_identity"] = "Wrong act identity"
                elif case == "path_escape":
                    metadata["archive_key"] = "../outside.txt"
                    self._write(metadata_path, metadata)
                elif case == "permission_path_escape":
                    manifest["processing_permission"]["path"] = "../outside.json"
                elif case == "misbound_evidence":
                    asset["evidence"]["source_asset_sha256"] = "0" * 64
                elif case == "wrong_url":
                    asset["source_url"] = "https://example.invalid/another"
                elif case == "wrong_locator":
                    asset["evidence"]["locator"] = "utf8:bytes:0:999999"
                elif case == "unknown_target":
                    target = "2026-10-02"
                elif case == "bad_date":
                    target = "20250101"
                elif case == "unknown_field":
                    manifest["baseid"] = "private"
                elif case == "duplicate_asset":
                    manifest["assets"].append(copy.deepcopy(asset))
                manifest["manifest_hash"] = manifest_digest(manifest)
                if case == "manifest_hash":
                    manifest["manifest_hash"] = "0" * 64
                self._write(path, manifest)
                self._write(root / "approved/build.json", {"sentinel": True})
                before = self._snapshot(root)
                output = Path(temporary) / "m1"
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    code = main(["compile", "--input", str(path), "--target-date", target, "--output-dir", str(output)])
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(stderr.getvalue())["result"], "failed")
                self.assertFalse(output.exists())
                self.assertEqual(self._snapshot(root), before)

    def test_diagnostic_keeps_stale_and_rejected_source_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            path, manifest = self._prepare(root)
            source_item = manifest["assets"][0]["source_item"]
            item_path = root / "items" / (hashlib.sha256(source_item.encode()).hexdigest() + ".json")
            item = json.loads(item_path.read_bytes())
            item.update(candidate_status="stale", review_status="rejected", unresolved_items=[
                {"reason": "retained_source_gap", "diagnostic_message": "Keep the original blocker."}])
            self._write(item_path, item)
            manifest["admission_status"] = "rejected"
            manifest["admission_blockers"] = ["m0_review_rejected"]
            manifest["manifest_hash"] = manifest_digest(manifest)
            self._write(path, manifest)
            result = self._cli(path, Path(temporary) / "m1")
            self.assertTrue({"stale", "rejected", "m0_review_rejected", "retained_source_gap"} <= set(result["blockers"]))
            validated = json.loads((Path(result["draft"]).parent / "input.json").read_bytes())
            self.assertEqual(validated["source_statuses"][0]["candidate_status"], "stale")
            self.assertEqual(validated["admission_status"], "rejected")

    def test_frozen_candidate_wrap_is_read_only_and_stale_wrap_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            setup = handoff_fixture.CandidateHandoffTest()
            reconciliation, item_path, _ = setup._write_records(root)
            result = build_edition_candidate(reconciliation, root)
            candidate_path = Path(result["candidate"])
            frozen = (Path(__file__).parent.parent / "sources/fixtures/edition_candidate_v1.json").read_bytes()
            self.assertEqual(candidate_path.read_bytes(), frozen)
            candidate = json.loads(frozen)
            digest = candidate["edition_claim"]["snapshot_asset_sha256"]
            asset = json.loads((root / "assets" / f"{digest}.json").read_bytes())
            manifest = json.loads((FIXTURES / "corpus_input_v1.json").read_bytes())
            manifest.update(archive_root=".", kind="official_consolidated", act_identity_claim={"declared_identity": "Test Act"},
                            edition_candidate={"path": str(candidate_path.relative_to(root)), "sha256": hashlib.sha256(frozen).hexdigest()})
            manifest["assets"] = [{"sha256": digest, "source_item": candidate["edition_claim"]["source_item"],
                "source_url": asset["source_url"], "role": "consolidated", "declared_identity": "Test Act",
                "evidence": {"source_asset_sha256": digest, "source_url": asset["source_url"], "locator": "$.text"}}]
            permission = json.loads((FIXTURES / "processing_permission.json").read_bytes())
            permission.update(act_identity="Test Act", source_asset_sha256s=[digest])
            permission_path = root / manifest["processing_permission"]["path"]
            self._write(permission_path, permission)
            manifest["processing_permission"]["sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest()
            manifest["manifest_hash"] = manifest_digest(manifest)
            path = root / "input.json"
            self._write(path, manifest)
            before = self._snapshot(root)
            loaded, _, _ = load_input(path, TARGET)
            self.assertEqual(loaded["edition_candidate"], candidate)
            self.assertEqual(self._snapshot(root), before)
            relation_path = root / "relations/relation-consolidates.json"
            relation = json.loads(relation_path.read_bytes())
            relation["evidence_reference"]["source_asset_sha256"] = "0" * 64
            self._write(relation_path, relation)
            with self.assertRaisesRegex(ValueError, "relation evidence mismatch"):
                load_input(path, TARGET)
            self._write(relation_path, json.loads(before[str(relation_path.relative_to(root))]))
            item = json.loads(item_path.read_bytes())
            item["candidate_status"] = "stale"
            self._write(item_path, item)
            with self.assertRaisesRegex(ValueError, "stale edition candidate"):
                load_input(path, TARGET)
            with self.assertRaisesRegex(ValueError, "stale edition candidate"):
                build_edition_candidate(reconciliation, root)
            self.assertEqual(candidate_path.read_bytes(), frozen)

    def test_paths_and_input_order_do_not_change_content_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            first_root = Path(temporary) / "first"
            path, manifest = self._prepare(first_root)
            first = self._cli(path, Path(temporary) / "output1")
            second_root = Path(temporary) / "second"
            shutil.copytree(first_root, second_root)
            manifest["target_dates"].reverse()
            manifest["archive_root"] = "./"
            self._write(second_root / "input.json", manifest)
            second = self._cli(second_root / "input.json", Path(temporary) / "output2")
            for key in ("manifest_hash", "draft_id", "content_hash"):
                self.assertEqual(first[key], second[key])
            other_date = self._cli(path, Path(temporary) / "output1", "2026-10-01")
            self.assertNotEqual(first["draft_id"], other_date["draft_id"])

    def test_amendments_stay_separate_and_ambiguous_text_keeps_exact_crlf_spans(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            path, manifest = self._prepare(root)
            text = "Учебная поправка М1-01\r\nСтатья 1. Учебное изменение.\r\nСтатья 1. Дубликат.\r\n<script>text</script>\r\n"
            source_path = Path(temporary) / "amendment.txt"
            source_path.write_bytes(text.encode("utf-8"))
            metadata = json.loads((FIXTURES / "sample_act.json").read_bytes())
            metadata.update(external_id="m1-01-amendment", declared_act_identity="Учебная поправка М1-01",
                            source_url="https://example.invalid/amendment", expected_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest())
            metadata_path = Path(temporary) / "amendment.json"
            self._write(metadata_path, metadata)
            acquire_fixture(source_path, metadata_path, root)
            digest = metadata["expected_sha256"]
            manifest["assets"].append({"sha256": digest, "source_item": "fixture:m1-01-amendment",
                "source_url": metadata["source_url"], "role": "amendment", "declared_identity": metadata["declared_act_identity"],
                "evidence": {"source_asset_sha256": digest, "source_url": metadata["source_url"], "locator": "utf8:bytes:0:" + str(len(source_path.read_bytes()))}})
            permission_path = root / manifest["processing_permission"]["path"]
            permission = json.loads(permission_path.read_bytes())
            permission["source_asset_sha256s"].append(digest)
            self._write(permission_path, permission)
            manifest["processing_permission"]["sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest()
            manifest["manifest_hash"] = manifest_digest(manifest)
            self._write(path, manifest)
            result = self._cli(path, Path(temporary) / "m1")
            draft = json.loads(Path(result["draft"]).read_bytes())
            original, amendment = draft["content"]["trees"]
            self.assertEqual(original["namespace"], "act")
            self.assertEqual(amendment["namespace"], "amendment/" + digest)
            self.assertEqual(len(amendment["unresolved_blocks"]), 2)
            self.assertTrue(amendment["nodes"][1]["text"].endswith("\r\n"))
            self.assertEqual(amendment["accounting"]["total_bytes"], len(source_path.read_bytes()))
            self.assertIn("amendments_not_applied", result["blockers"])
            report = Path(result["report"]).read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;text&lt;/script&gt;", report)
            self.assertNotIn("<script>", report)
            manifest["assets"].reverse()
            # Manifest list order is immaterial; permission bytes remain authoritative.
            self._write(path, manifest)
            repeated = self._cli(path, Path(temporary) / "m1")
            self.assertEqual(repeated, {**result, "result": "unchanged"})

    def test_unknown_identity_makes_all_nonblank_text_unresolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            path, manifest = self._prepare(root)
            source_path = Path(temporary) / "unknown-title.txt"
            source_path.write_bytes("Нераспознанный заголовок\nСтатья 1. Текст.\n".encode("utf-8"))
            metadata_path = Path(temporary) / "metadata.json"
            metadata = json.loads((FIXTURES / "sample_act.json").read_bytes())
            self._write(metadata_path, metadata)
            acquire_fixture(source_path, metadata_path, root)
            digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            manifest["assets"][0]["sha256"] = digest
            manifest["assets"][0]["evidence"]["source_asset_sha256"] = digest
            manifest["assets"][0]["evidence"]["locator"] = "utf8:bytes:0:" + str(len(source_path.read_bytes()))
            permission_path = root / manifest["processing_permission"]["path"]
            permission = json.loads(permission_path.read_bytes())
            permission["source_asset_sha256s"] = [digest]
            self._write(permission_path, permission)
            manifest["processing_permission"]["sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest()
            manifest["manifest_hash"] = manifest_digest(manifest)
            self._write(path, manifest)
            result = self._cli(path, Path(temporary) / "m1")
            tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
            self.assertEqual(tree["nodes"], [])
            self.assertEqual(tree["identity_decision"]["status"], "unresolved")
            self.assertIn("identity_unresolved", result["blockers"])

    def test_immutable_output_conflict_and_protected_destination_write_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            path, _ = self._prepare(root)
            for protected in ("raw", "approved"):
                before = self._snapshot(root)
                with self.assertRaisesRegex(ValueError, "protected"):
                    compile_input(path, TARGET, root / protected)
                self.assertEqual(self._snapshot(root), before)
            output = Path(temporary) / "m1"
            result = self._cli(path, output)
            Path(result["draft"]).write_bytes(b"corrupt retained draft")
            before = self._snapshot(output)
            with self.assertRaisesRegex(ValueError, "immutable artifact conflict"):
                compile_input(path, TARGET, output)
            self.assertEqual(self._snapshot(output), before)


if __name__ == "__main__":
    unittest.main()
