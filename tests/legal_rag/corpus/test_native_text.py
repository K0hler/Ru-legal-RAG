from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from legal_rag.corpus.__main__ import main  # noqa: E402
from legal_rag.corpus.compiler import json_bytes, manifest_digest  # noqa: E402
from legal_rag.sources.acquisition import acquire_fixture  # noqa: E402


# Project-authored, redistributable examples; no gold-set or real legal labels.
IDENTITY = 'Федеральный закон от 02.05.2006 № 59-ФЗ "О порядке рассмотрения обращений граждан Российской Федерации"'
HTML = '''<!doctype html><html><head><title>Portal</title>
<style>.W9{vertical-align:super}</style></head><body>
<p id="h1">РОССИЙСКАЯ ФЕДЕРАЦИЯ</p><p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>
<p>О порядке рассмотрения обращений граждан Российской Федерации</p>
<p><span class="markx">(Особенности применения закона)</span></p>
<p id="a1">Статья 1. Учебная статья</p>
<p id="part">1.\u00a0Не &lt;менять&gt; число 30\r\n дней.<span class="mark"> (Примечание: не отменено)</span></p>
<p>1) Первый пункт;</p><p>а) Вложенный подпункт.</p>
<p>1<span class="W9">1</span>. Дополнительная часть.</p>
<p id="a2">Статья 2. Другая статья</p><p>Ненумерованный абзац.</p>
<p>Президент Российской Федерации</p><p>2 мая 2006 года</p><p>№ 59-ФЗ</p>
</body></html>'''


class NativeTextTest(unittest.TestCase):
    def prepare(self, root, html=HTML, *, locator="$.redtext", response=None):
        payload = json_bytes({"redtext": html, "error": None} if response is None else response)
        digest = hashlib.sha256(payload).hexdigest()
        source = root / "fixture.json"
        metadata_path = root / "fixture-metadata.json"
        root.mkdir(parents=True)
        source.write_bytes(payload)
        metadata = {"adapter_version": "fixture/1", "captured_at": "2026-10-12T00:00:00Z",
                    "declared_act_identity": IDENTITY, "declared_edition_label": "synthetic-native",
                    "expected_sha256": digest, "external_id": "native-59", "media_type": "application/json",
                    "rights_status": "Project-authored synthetic fixture; redistribution permitted",
                    "source_system": "fixture", "source_url": "https://example.invalid/native-59"}
        metadata_path.write_bytes(json_bytes(metadata))
        acquire_fixture(source, metadata_path, root)
        permission = {"schema_version": "processing-permission/1", "decision": "allowed",
                      "scope": "diagnostic", "act_identity": IDENTITY, "source_asset_sha256s": [digest],
                      "authorized_by": "synthetic-author", "authorized_at": "2026-10-12T00:00:00Z",
                      "rights_basis": metadata["rights_status"]}
        permission_path = root / "reviews/permission.json"
        permission_path.parent.mkdir()
        permission_path.write_bytes(json_bytes(permission))
        manifest = {"schema_version": "corpus-input/1", "kind": "official_consolidated",
                    "act_identity_claim": {"declared_identity": IDENTITY}, "target_dates": ["2026-10-01"],
                    "archive_root": ".", "admission_status": "unresolved",
                    "admission_blockers": ["case_law_sensitive_effect_unresolved"], "unresolved_questions": [],
                    "processing_permission": {"path": "reviews/permission.json",
                                              "sha256": hashlib.sha256(permission_path.read_bytes()).hexdigest()},
                    "assets": [{"sha256": digest, "source_item": "fixture:native-59",
                                "source_url": metadata["source_url"], "role": "consolidated",
                                "declared_identity": IDENTITY,
                                "evidence": {"source_asset_sha256": digest, "source_url": metadata["source_url"],
                                             "locator": locator}}]}
        manifest["manifest_hash"] = manifest_digest(manifest)
        path = root / "input.json"
        path.write_bytes(json_bytes(manifest))
        return path

    def run_cli(self, path, output, target="2026-10-01"):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["compile", "--input", str(path), "--target-date", target, "--output-dir", str(output)])
        return code, json.loads(stdout.getvalue() or stderr.getvalue())

    @staticmethod
    def snapshot(root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def test_native_golden_tree_repeat_and_original_locators(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            path = self.prepare(root)
            before = self.snapshot(root)
            output = Path(temporary) / "derived"
            code, result = self.run_cli(path, output)
            self.assertEqual(code, 0, result)
            draft = json.loads(Path(result["draft"]).read_bytes())
            tree = draft["content"]["trees"][0]
            addresses = [(n["kind"], n["address"]) for n in tree["nodes"]]
            self.assertEqual(addresses, [
                ("header", "act/header/1"), ("header", "act/header/2"), ("header", "act/header/3"),
                ("note", "act/note/1"), ("article", "act/article/1"),
                ("part", "act/article/1/part/1"), ("note", "act/article/1/part/1/note/1"),
                ("item", "act/article/1/part/1/item/1"), ("subitem", "act/article/1/part/1/item/1/subitem/а"),
                ("part", "act/article/1/part/1.1"), ("article", "act/article/2"),
                ("paragraph", "act/article/2/paragraph/1"), ("header", "act/header/4"),
                ("header", "act/header/5"), ("header", "act/header/6")])
            self.assertEqual(tree["identity_decision"]["status"], "claim_matches_header")
            self.assertFalse(tree["unresolved_blocks"])
            part = next(n for n in tree["nodes"] if n["address"] == "act/article/1/part/1")
            self.assertEqual(part["text"], "1. Не <менять> число 30 дней.")
            extraction = json.loads((output / "extractions" / (tree["extraction_id"] + ".json")).read_bytes())
            tokens = extraction["text_nodes"]
            for token in tokens:
                span = token["source_span"]
                self.assertEqual(span["json_pointer"], "/redtext")
                self.assertEqual(HTML[span["char_start"]:span["char_end"]], token["raw_text"])
                self.assertNotIn("byte_start", span)
            self.assertEqual(tree["accounting"]["total_source_chars"], sum(len(t["raw_text"]) for t in tokens))
            self.assertEqual(tree["accounting"]["total_source_chars"], sum(tree["accounting"][k + "_source_chars"]
                             for k in ("parsed", "unresolved", "excluded")))
            blocks = [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]
            self.assertEqual(sorted(t["text_node_id"] for t in tokens),
                             sorted(i for b in blocks for i in b["text_node_ids"]))
            mapped = next(b for b in extraction["pages"][0]["blocks"] if b["text"] == part["text"])
            cursor = 0
            for mapping in mapped["cleanup_mapping"]:
                self.assertEqual(mapping["decoded_start"], cursor)
                cursor = mapping["decoded_end"]
            self.assertEqual(cursor, len(mapped["original_text"]))
            self.assertEqual("".join(m["after"] for m in mapped["cleanup_mapping"]), mapped["text"])
            self.assertTrue(any(t["raw_text"] == "&lt;" and t["decoded_text"] == "<" for t in tokens))
            self.assertIn("case_law_sensitive_effect_unresolved", draft["blockers"])
            self.assertEqual(draft["legal_admission"], "not_requested")
            report = Path(result["report"]).read_text("utf-8")
            self.assertIn("<details", report)
            self.assertIn("<summary>Excluded source tokens and reasons</summary>", report)
            self.assertIn("&amp;lt;", report)
            self.assertIn("/redtext", report)
            self.assertEqual(self.snapshot(root), before)
            retained = self.snapshot(output)
            code, repeated = self.run_cli(path, output)
            self.assertEqual(code, 0, repeated)
            self.assertEqual(repeated, {**result, "result": "unchanged"})
            self.assertEqual(self.snapshot(output), retained)

    def test_profile_refuses_wrong_field_response_error_and_historical_target(self):
        cases = [("wrong_locator", {"locator": "$.another"}),
                 ("missing_redtext", {"response": {"another": HTML, "error": None}}),
                 ("response_error", {"response": {"redtext": HTML, "error": "failed"}}),
                 ("empty", {"html": ""}), ("malformed", {"html": "<html><body><p>broken"}),
                 ("historical", {})]
        for name, options in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "archive"
                path = self.prepare(root, **options)
                before = self.snapshot(root)
                output = Path(temporary) / "derived"
                code, result = self.run_cli(path, output, "2025-01-01" if name == "historical" else "2026-10-01")
                self.assertEqual(code, 2, result)
                self.assertFalse(output.exists())
                self.assertEqual(self.snapshot(root), before)

    def test_unknown_identity_duplicate_and_structure_stay_unresolved(self):
        cases = [("identity", HTML.replace("№ 59-ФЗ", "№ 60-ФЗ"), "identity_unresolved"),
                 ("duplicate", HTML.replace('Статья 2.', 'Статья 1.'), "unresolved_structure"),
                 ("unknown", HTML.replace("Ненумерованный абзац.", "Приложение А"), "unresolved_structure")]
        for name, html, blocker in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "archive"
                path = self.prepare(root, html)
                code, result = self.run_cli(path, Path(temporary) / "derived")
                self.assertEqual(code, 0, result)
                self.assertIn(blocker, result["blockers"])
                tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
                self.assertTrue(tree["unresolved_blocks"])
                self.assertEqual(len({n["address"] for n in tree["nodes"]}), len(tree["nodes"]))
                if name == "identity":
                    self.assertFalse(any(n["kind"] == "article" for n in tree["nodes"]))

    def test_br_entities_plain_paragraphs_and_unknown_context(self):
        html = HTML.replace("Ненумерованный абзац.", "Текст. Не менять число &#51;&#48;.<br>Вторая строка.")
        html = html.replace("1) Первый пункт;", "Приложение А</p><p>1) Не угадывать родителя;")
        with tempfile.TemporaryDirectory() as temporary:
            path = self.prepare(Path(temporary) / "archive", html)
            code, result = self.run_cli(path, Path(temporary) / "derived")
            self.assertEqual(code, 0, result)
            tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
            paragraphs = [n["text"] for n in tree["nodes"] if n["kind"] == "paragraph"]
            self.assertIn("Текст. Не менять число 30. Вторая строка.", paragraphs)
            self.assertTrue(any(n["text"] == "1) Не угадывать родителя;" for n in tree["unresolved_blocks"]))

    def test_header_identity_cannot_be_borrowed_from_body(self):
        title_in_body = HTML.replace("<p>О порядке рассмотрения обращений граждан Российской Федерации</p>", "")
        title_in_body = title_in_body.replace("Ненумерованный абзац.", "О порядке рассмотрения обращений граждан Российской Федерации")
        number_in_body = HTML.replace("№ 59-ФЗ", "№ 60-ФЗ").replace("Ненумерованный абзац.</p>", "Ненумерованный абзац.</p><p>№ 59-ФЗ</p>")
        for html in (title_in_body, number_in_body):
            with self.subTest(html=html[:20]), tempfile.TemporaryDirectory() as temporary:
                path = self.prepare(Path(temporary) / "archive", html)
                code, result = self.run_cli(path, Path(temporary) / "derived")
                self.assertEqual(code, 0, result)
                self.assertIn("identity_unresolved", result["blockers"])

    def test_sibling_paragraphs_and_split_superscript_number(self):
        html = HTML.replace("Ненумерованный абзац.</p>", "Ненумерованный абзац.</p><p>Другой абзац.</p>")
        html = html.replace('1<span class="W9">1</span>.', '1<sup>1&#50;</sup>.')
        with tempfile.TemporaryDirectory() as temporary:
            path = self.prepare(Path(temporary) / "archive", html)
            code, result = self.run_cli(path, Path(temporary) / "derived")
            self.assertEqual(code, 0, result)
            nodes = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]["nodes"]
            self.assertIn("act/article/1/part/1.12", [n["address"] for n in nodes])
            self.assertEqual([n["address"] for n in nodes if n["kind"] == "paragraph"],
                             ["act/article/2/paragraph/1", "act/article/2/paragraph/2"])

    def test_unrecognized_numbering_and_table_stop_targeting(self):
        cases = [(label, HTML.replace("1) Первый пункт;", label + " Неизвестная нумерация.</p><p>1) Не продолжать старую часть;"))
                 for label in ("0.", "1.0.", "1.0)")]
        cases.append(("table", HTML.replace("<p>1) Первый пункт;</p>", "<table><tr><td><p>1) Первый пункт;</p></td></tr></table>")))
        cases.append(("two_parts_after_br", HTML.replace("1) Первый пункт;", "2. Первая часть.<br>3. Вторая часть.</p><p>1) Не угадывать часть;")))
        for name, html in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                path = self.prepare(Path(temporary) / "archive", html)
                code, result = self.run_cli(path, Path(temporary) / "derived")
                self.assertEqual(code, 0, result)
                tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
                self.assertFalse(any(n["kind"] == "item" for n in tree["nodes"]))
                self.assertIn("unresolved_structure", result["blockers"])

    def test_portal_script_is_accounted_as_service_text(self):
        html = HTML.replace("<body>", "<body><script>Статья 99. Не правовая норма</script>")
        with tempfile.TemporaryDirectory() as temporary:
            path = self.prepare(Path(temporary) / "archive", html)
            code, result = self.run_cli(path, Path(temporary) / "derived")
            self.assertEqual(code, 0, result)
            tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
            self.assertFalse(tree["unresolved_blocks"])
            self.assertTrue(any(n["text"] == "Статья 99. Не правовая норма" and n["reason"] == "non_document_text"
                                for n in tree["excluded_blocks"]))

    def test_nontext_region_alone_blocks_structure_and_is_visible_in_report(self):
        html = HTML.replace('<p id="a2">', '<img src="formula.png"/><p id="a2">')
        with tempfile.TemporaryDirectory() as temporary:
            path = self.prepare(Path(temporary) / "archive", html)
            code, result = self.run_cli(path, Path(temporary) / "derived")
            self.assertEqual(code, 0, result)
            tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
            self.assertFalse(tree["unresolved_blocks"])
            self.assertEqual(len(tree["unresolved_regions"]), 1)
            self.assertIn("unresolved_structure", result["blockers"])
            self.assertIn("formula.png", Path(result["report"]).read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
