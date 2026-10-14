import hashlib
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from legal_rag.corpus.html_preparation import prepare_html, prepare_input  # noqa: E402
from legal_rag.corpus.__main__ import main  # noqa: E402
import test_native_text  # noqa: E402


class HTMLPreparationTest(unittest.TestCase):
    def test_preserves_text_boundaries_notes_and_number_typography(self):
        source = '''<html><head><style>.W9,.WB{vertical-align:super}</style></head><body>
<p id="a" class="H" style="text-align:center">Статья 91<span class="W9">10</span>. Не менять.</p>
<p>2<span class="WB">1</span>) &lt;30&gt;&nbsp;дней.<br>Следующая строка.
<span class="mark" style="display:none">(Примечание: не отменено)</span></p>
<p><font color="red">Без номера.</font></p></body></html>'''
        result = prepare_html(source)
        clean = BeautifulSoup(result["html"], "html.parser")
        original = BeautifulSoup(source, "html.parser")
        self.assertEqual(clean.body.get_text(), original.body.get_text())
        self.assertEqual([p.get_text() for p in clean.find_all("p")],
                         [p.get_text() for p in original.find_all("p")])
        self.assertEqual([s.get_text() for s in clean.find_all("sup")], ["10", "1"])
        self.assertEqual(len(clean.find_all("br")), 1)
        self.assertIsNone(clean.find("h1"))
        self.assertEqual(clean.find("p", id="a").name, "p")
        self.assertIn("(Примечание: не отменено)", clean.get_text())
        self.assertEqual(clean.select_one('[data-lr-note="true"]').get_text(),
                         "(Примечание: не отменено)")
        self.assertIsNone(clean.find("font"))
        for tag in clean.find_all(True):
            self.assertNotIn("style", tag.attrs)
            self.assertNotIn("class", tag.attrs)
        row = next(row for row in result["source_map"] if row["attributes"].get("id") == "a")
        self.assertEqual(row["attributes"]["class"], ["H"])
        self.assertEqual(source[row["source_start"]:row["source_end"]],
                         '<p id="a" class="H" style="text-align:center">')
        self.assertIn('id="a"', result["html"][row["output_start"]:row["output_end"]])
        self.assertIsNone(clean.find(attrs={"data-lr-origin": True}))
        self.assertEqual(result["source_html_sha256"], hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(result["accounting"]["retained_text_chars"],
                         len("".join(original.body.find_all(string=True))))

    def test_tables_images_references_standard_headings_and_unknown_markup(self):
        source = '''<h2 id="sec">Раздел</h2><table border="1"><tr>
<td rowspan="2">А</td><td colspan="3"><img src="../formula.gif" alt="F" width="40"></td>
</tr><tr><td>Б</td></tr></table><a href="/?a=1&amp;b=2">ссылка</a>
<span cmdprm="SEARCH &quot;123&quot;">источник</span><custom data-unknown="keep">Не удалять</custom>
<p><span style="vertical-align: sub">2</span><sup>3</sup><sub>4</sub></p>'''
        result = prepare_html(source)
        clean = BeautifulSoup(result["html"], "html.parser")
        original = BeautifulSoup(source, "html.parser")
        self.assertEqual(clean.get_text(), original.get_text())
        self.assertEqual(clean.h2["id"], "sec")
        self.assertEqual(clean.td["rowspan"], "2")
        self.assertEqual(clean.find_all("td")[1]["colspan"], "3")
        self.assertEqual(clean.img["src"], "../formula.gif")
        self.assertEqual(clean.img["alt"], "F")
        self.assertEqual(clean.a["href"], "/?a=1&b=2")
        self.assertEqual(clean.find(attrs={"cmdprm": True})["cmdprm"], 'SEARCH "123"')
        self.assertEqual(clean.custom["data-unknown"], "keep")
        self.assertEqual([s.get_text() for s in clean.find_all("sub")], ["2", "4"])
        self.assertEqual(len(clean.find_all("table")), 1)
        row = next(row for row in result["source_map"] if row["tag"] == "img")
        self.assertEqual(row["attributes"]["width"], "40")
        self.assertEqual(source[row["source_start"]:row["source_end"]],
                         '<img src="../formula.gif" alt="F" width="40">')

    def test_exclusions_are_explicit_and_output_is_deterministic(self):
        source = '''<!doctype html><html><head><title>Portal</title><script>head()</script></head>
<body><p>Не отменено.</p><script>body()</script><style>p{color:red}</style>
<!-- comment --><p style="display:none">Скрытое примечание</p></body></html>'''
        result = prepare_html(source)
        self.assertEqual(prepare_html(source), result)
        clean = BeautifulSoup(result["html"], "html.parser")
        self.assertEqual(clean.get_text(), "\nНе отменено.\nСкрытое примечание")
        self.assertIsNone(clean.head)
        self.assertIsNone(clean.script)
        self.assertIsNone(clean.style)
        self.assertIn("Portal", "".join(row["text"] for row in result["excluded"]))
        self.assertIn("body()", "".join(row["text"] for row in result["excluded"]))
        accounting = result["accounting"]
        self.assertEqual(accounting["source_text_chars"],
                         accounting["retained_text_chars"] + accounting["excluded_text_chars"])

    def test_ambiguous_css_is_retained_as_source_evidence(self):
        source = '''<style>.up{vertical-align:super}.down{vertical-align:sub}
.container .complex{vertical-align:super}</style>
<p><span class="up down">1</span><span class="complex">2</span>
<span style="vertical-align:baseline" class="up">3</span></p>'''
        result = prepare_html(source)
        clean = BeautifulSoup(result["html"], "html.parser")
        self.assertIsNone(clean.sup)
        self.assertIsNone(clean.sub)
        self.assertEqual(len(clean.find_all("span")), 3)
        self.assertTrue(any(row["attributes"].get("class") == ["up", "down"]
                            for row in result["source_map"]))

    def test_opening_tag_offsets_handle_quoted_brackets_and_unicode(self):
        source = '<p>Я</p>\r\n<p title="1 > 0">Не менять &amp; знак.</p>'
        result = prepare_html(source)
        row = next(row for row in result["source_map"] if row["attributes"].get("title"))
        self.assertEqual(source[row["source_start"]:row["source_end"]], '<p title="1 > 0">')
        opening = result["html"][row["output_start"]:row["output_end"]]
        self.assertIn('title="1 &gt; 0"', opening)
        self.assertTrue(opening.startswith("<p "))

    def test_removed_markup_does_not_merge_adjacent_whitespace(self):
        source = '<html>\n<head><title>Portal</title></head>\n<body>\n<!--comment-->\n<p>Не менять.</p></body></html>'
        result = prepare_html(source)
        clean = BeautifulSoup(result["html"], "html.parser")
        self.assertEqual(clean.get_text(), "\n\n\n\nНе менять.")

    def test_legacy_css_inside_html_comments_still_preserves_indices(self):
        source = '<style><!--/*CSS*/\n.W9{vertical-align:super}.WA{vertical-align:sub}/*CSS*/--></style><p>1<span class="W9">2</span><span class="WA">3</span></p>'
        clean = BeautifulSoup(prepare_html(source)["html"], "html.parser")
        self.assertEqual(clean.sup.get_text(), "2")
        self.assertEqual(clean.sub.get_text(), "3")

    def test_media_rules_do_not_override_common_typography_hints(self):
        source = '''<style>.small{vertical-align:super}
@media screen{.small{vertical-align:top}} @media print{.small{vertical-align:bottom}}</style>
<p>1<span class="small">2</span></p>'''
        clean = BeautifulSoup(prepare_html(source)["html"], "html.parser")
        self.assertEqual(clean.sup.get_text(), "2")

    def test_document_content_inside_head_fails_before_exclusion(self):
        examples = ['<html><head><title>Portal</title><body><p>Legal text</p></body></html>',
                    '<html><head><title>Portal</title><p>Legal text</p></html>',
                    '<html><head>Legal text</head><body><p>Other text</p></body></html>']
        for source in examples:
            with self.subTest(source=source), self.assertRaises(ValueError):
                prepare_html(source)

    def test_css_important_priority_across_class_and_inline(self):
        examples = [('baseline!important', 'super', None),
                    ('super!important', 'baseline', 'sup'),
                    ('super!important', 'sub!important', 'sub'),
                    ('baseline', 'super!important;vertical-align:baseline', 'sup')]
        for rule, inline, expected in examples:
            with self.subTest(rule=rule, inline=inline):
                source = '<style>.a{vertical-align:' + rule + '}</style><p>1<span class="a" style="vertical-align:' + inline + '">2</span></p>'
                clean = BeautifulSoup(prepare_html(source)["html"], "html.parser")
                self.assertEqual(clean.p.find(["span", "sup", "sub"]).name, expected or "span")

    def test_cli_contract_replay_immutable_outputs_and_protected_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "archive"
            fixture = test_native_text.NativeTextTest()
            path = fixture.prepare(root)
            before = fixture.snapshot(root)
            output = Path(temporary) / "prepared"
            result = prepare_input(path, "2026-10-01", output)
            self.assertEqual(result["result"], "new")
            manifest = json.loads(Path(result["manifest"]).read_bytes())
            self.assertEqual(manifest["legal_admission"], "not_requested")
            self.assertIn("case_law_sensitive_effect_unresolved", manifest["admission_blockers"])
            self.assertEqual(Path(result["source_html"]).read_bytes().decode("utf-8"), test_native_text.HTML)
            retained = fixture.snapshot(output)
            self.assertEqual(prepare_input(path, "2026-10-01", output), {**result, "result": "unchanged"})
            self.assertEqual(fixture.snapshot(output), retained)
            for folder in ("raw", "assets", "items", "relations", "candidates", "approved"):
                with self.assertRaises(ValueError):
                    prepare_input(path, "2026-10-01", root / folder / "prepared")
            self.assertEqual(fixture.snapshot(root), before)
            Path(result["html"]).write_text("corrupt", "utf-8")
            with self.assertRaises(ValueError):
                prepare_input(path, "2026-10-01", output)
            self.assertEqual(Path(result["html"]).read_text("utf-8"), "corrupt")

    def test_wrappers_and_invalid_input_fail_before_writes(self):
        cases = [("$.other", {"other": "<p>Не угадывать поле.</p>", "error": None}),
                 ("$.redtext", {"redtext": "<p>text</p>", "error": "failed"}),
                 ("$.redtext", {"redtext": "<html><head><body><p>Do not lose</p></body></html>", "error": None}),
                 ("$.redtext", {"redtext": "", "error": None})]
        for locator, response in cases:
            with self.subTest(locator=locator, response=response), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "archive"
                fixture = test_native_text.NativeTextTest()
                path = fixture.prepare(root, locator=locator, response=response)
                before = fixture.snapshot(root)
                output = Path(temporary) / "prepared"
                with self.assertRaises(ValueError):
                    prepare_input(path, "2026-10-01", output)
                self.assertFalse(output.exists())
                self.assertEqual(fixture.snapshot(root), before)
        with tempfile.TemporaryDirectory() as temporary:
            fixture = test_native_text.NativeTextTest()
            path = fixture.prepare(Path(temporary) / "archive", locator="$.doctext",
                                   response={"doctext": "<p>Другой акт.</p>", "error": None})
            result = prepare_input(path, "2026-10-01", Path(temporary) / "prepared")
            self.assertIn("Другой акт.", Path(result["html"]).read_text("utf-8"))

    def test_prepare_html_cli_and_undeclared_date_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = test_native_text.NativeTextTest().prepare(Path(temporary) / "archive")
            output = Path(temporary) / "prepared"
            stdout, stderr = StringIO(), StringIO()
            arguments = ["prepare-html", "--input", str(path), "--target-date", "2026-10-01",
                         "--output-dir", str(output)]
            with redirect_stdout(stdout):
                code = main(arguments)
            self.assertEqual(code, 0)
            self.assertTrue(Path(json.loads(stdout.getvalue())["html"]).is_file())
            arguments[4] = "2025-01-01"
            before = test_native_text.NativeTextTest.snapshot(output)
            with redirect_stderr(stderr):
                code = main(arguments)
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(stderr.getvalue())["result"], "failed")
            self.assertEqual(test_native_text.NativeTextTest.snapshot(output), before)


if __name__ == "__main__":
    unittest.main()
