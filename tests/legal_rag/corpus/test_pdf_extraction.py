import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from legal_rag.corpus import pdf_extraction as pdf  # noqa: E402


DIGEST = "a" * 64


def saved_result():
    layouts = [[
        {"category": "Title", "bbox": [1, 2, 90, 20], "text": "Приложение 1", "future": 7},
        {"category": "Text", "bbox": [2, 22, 95, 45], "text": "1. Первая строка\nПродолжение"},
    ], [
        {"category": "Table", "bbox": [1, 2, 95, 80], "text":
         '<table><caption>Допустимые значения</caption><tr><th rowspan="2">Вид</th><th colspan="2">Условия</th></tr>'
         '<tr><td>+</td><td></td></tr></table>'},
        {"category": "Picture", "bbox": [1, 81, 50, 99]},
    ]]
    document = {"pages": [{"page_number": i + 1, "image_size": [100, 100],
                  "layout": layout, "coordinate_space": "native model image pixels",
                  "native": {"choices": [{"finish_reason": "stop", "message": {
                      "content": json.dumps(layout, ensure_ascii=False)}}]}}
                 for i, layout in enumerate(layouts)]}
    run = {"engine": "dotsmocr", "source_sha256": DIGEST, "status": "complete",
           "source_pages": 2, "requested_pages": [1, 2], "completed_pages": [1, 2],
           "config": {"image_dpi": 200, "max_pixels": 4014080, "workers": 16},
           "model": {"repo": "dots-studio/dots.mocr", "revision": "b" * 40,
                     "weights_sha256": {"model.safetensors": "c" * 64}}}
    return document, run


class PdfExtractionTest(unittest.TestCase):
    def test_preserves_physical_tree_text_coordinates_and_merged_empty_cells(self):
        document, run = saved_result()
        extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
        self.assertTrue(extraction["coverage"]["all_source_pages"])
        self.assertEqual([p["page"] for p in extraction["pages"]], [1, 2])
        self.assertEqual(extraction["pages"][0]["regions"][0]["source_record"]["future"], 7)
        table = extraction["pages"][1]["regions"][0]
        self.assertEqual((table["table"]["rows"], table["table"]["columns"]), (2, 3))
        self.assertEqual([(c["row"], c["column"], c["rowspan"], c["colspan"], c["text"])
                          for c in table["table"]["cells"]],
                         [(0, 0, 2, 1, "Вид"), (0, 1, 1, 2, "Условия"),
                          (1, 1, 1, 1, "+"), (1, 2, 1, 1, "")])
        self.assertIsNone(table["table"]["cells"][0]["bbox"])
        self.assertIn("Допустимые значения", extraction["blocks"][-1]["text"])
        block = extraction["blocks"][2]
        self.assertEqual(block["text"], "Продолжение")
        self.assertEqual(block["source_span"]["page"], 1)
        self.assertEqual(block["source_span"]["bbox"], [2, 22, 95, 45])
        self.assertEqual(block["source_span"]["json_pointer"], "/pages/0/layout/1/text")
        self.assertEqual(block["source_span"]["ocr_char_start"], 17)
        self.assertEqual(extraction["document_tree"]["kind"], "document")
        self.assertEqual(len(extraction["document_tree"]["children"]), 2)
        self.assertIn("image_without_transcription", extraction["uncertainties"])
        tree = pdf.pdf_tree(extraction, "Неустановленный акт", "original")
        self.assertEqual(tree["identity_decision"]["status"], "unresolved")
        self.assertTrue(tree["accounting"]["exactly_once"])
        self.assertEqual(tree["accounting"]["total_text_nodes"], len(extraction["text_nodes"]))

    def test_content_identity_excludes_api_ids_timings_paths_and_keeps_source_immutable(self):
        document, run = saved_result()
        before = copy.deepcopy((document, run))
        first = pdf.normalize_dotsmocr(document, run, DIGEST)
        self.assertEqual((document, run), before)
        run.update(elapsed_seconds=42, source="C:/another.pdf")
        document["pages"][0]["native"]["id"] = "new-api-request-id"
        self.assertEqual(pdf.normalize_dotsmocr(document, run, DIGEST), first)
        document["pages"][0]["layout"][0]["bbox"][0] = 2
        second = pdf.normalize_dotsmocr(document, run, DIGEST)
        self.assertNotEqual(first["extraction_id"], second["extraction_id"])

    def test_invalid_or_incomplete_native_results_are_rejected(self):
        for mutation in ("hash", "missing", "duplicate", "failed", "truncated", "bbox",
                         "model", "requested", "empty", "table", "infinite", "region_type", "page_type",
                         "native_type", "choice_type", "message_type"):
            with self.subTest(mutation=mutation):
                document, run = saved_result()
                if mutation == "hash":
                    run["source_sha256"] = "d" * 64
                elif mutation == "missing":
                    document["pages"].pop()
                elif mutation == "duplicate":
                    document["pages"][1]["page_number"] = 1
                elif mutation == "failed":
                    run["status"] = "failed"
                elif mutation == "truncated":
                    document["pages"][0]["native"]["choices"][0]["finish_reason"] = "length"
                elif mutation == "bbox":
                    document["pages"][0]["layout"][0]["bbox"] = [0, 0, 101, 5]
                elif mutation == "model":
                    run["model"] = {}
                elif mutation == "requested":
                    run["requested_pages"] = [1, 1]
                elif mutation == "empty":
                    document["pages"][0]["layout"] = []
                elif mutation == "table":
                    document["pages"][1]["layout"][0]["text"] = '<table><tr><td rowspan="0">x</td></tr></table>'
                elif mutation == "infinite":
                    document["pages"][0]["layout"][0]["bbox"][0] = float("nan")
                elif mutation == "region_type":
                    document["pages"][0]["layout"][0] = []
                elif mutation == "page_type":
                    document["pages"][0] = []
                elif mutation == "native_type":
                    document["pages"][0]["native"] = None
                elif mutation == "choice_type":
                    document["pages"][0]["native"]["choices"] = [None]
                else:
                    document["pages"][0]["native"]["choices"][0]["message"] = None
                with self.assertRaises(ValueError):
                    pdf.normalize_dotsmocr(document, run, DIGEST)

    def test_impossible_table_grid_degrades_only_that_table(self):
        # Observed in batch 5: a rowspan continuing onto the next page, and a rowspan crossed by a colspan row.
        for name, html, error in (
                ("span_past_rows", '<table><tr><th>Вид</th><th>Рыба</th></tr>'
                 '<tr><td rowspan="3">Прудовая</td><td>Карп</td></tr><tr><td>Сазан</td></tr></table>',
                 "OCR table span exceeds its rows"),
                ("overlap", '<table><tr><td>1</td><td rowspan="2">9</td></tr>'
                 '<tr><td colspan="2">в том числе</td></tr></table>',
                 "overlapping OCR table cells")):
            with self.subTest(name=name):
                document, run = saved_result()
                document["pages"][1]["layout"][0]["text"] = html
                extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
                table = extraction["pages"][1]["regions"][0]["table"]
                self.assertEqual((table["grid"], table["grid_error"]), ("unresolved", error))
                self.assertFalse(table["rectangular"])
                self.assertIsNone(table["columns"])
                self.assertTrue(all(cell["column"] is None for cell in table["cells"]))
                self.assertEqual([c["row"] for c in table["cells"]][:2], [0, 0])
                self.assertIn("table_grid_unresolved", extraction["uncertainties"])
                block = next(b for b in extraction["blocks"] if b["table_cells"])
                self.assertEqual(block["original_text"], html)
                for cell in table["cells"]:
                    self.assertIn(cell["text"], block["text"])
                tree = pdf.pdf_tree(extraction, "Неустановленный акт", "original")
                self.assertTrue(tree["accounting"]["exactly_once"])

    def test_resolved_table_output_is_unchanged_by_grid_degradation(self):
        document, run = saved_result()
        table = pdf.normalize_dotsmocr(document, run, DIGEST)["pages"][1]["regions"][0]["table"]
        self.assertNotIn("grid", table)
        self.assertEqual(table["columns"], 3)

    def test_partial_selection_is_explicit_and_unknown_categories_survive(self):
        document, run = saved_result()
        document["pages"] = document["pages"][:1]
        document["pages"][0]["layout"][0]["category"] = "FutureCategory"
        run.update(requested_pages=[1], completed_pages=[1])
        extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
        self.assertFalse(extraction["coverage"]["all_source_pages"])
        self.assertIn("unknown_category:FutureCategory", extraction["uncertainties"])

    def test_matched_law_uses_source_order_independently_of_source_hash(self):
        for digest in ("e" * 64, "f" * 64):
            document, run = saved_result()
            document["pages"] = document["pages"][:1]
            document["pages"][0]["layout"] = [{"category": "Text", "bbox": [1, 1, 99, 99],
                "text": "ФЕДЕРАЛЬНЫЙ ЗАКОН\nО тесте\nСтатья 1. Содержание\n1. Правило.\n"
                        "Президент Российской Федерации\n16 октября 2026 года\n№ 1-ФЗ"}]
            run.update(source_pages=1, requested_pages=[1], completed_pages=[1], source_sha256=digest)
            extraction = pdf.normalize_dotsmocr(document, run, digest)
            tree = pdf.pdf_tree(extraction, 'Федеральный закон от 16.10.2026 № 1-ФЗ "О тесте"', "original")
            self.assertNotEqual(tree["identity_decision"]["status"], "unresolved")
            node = next(node for node in tree["nodes"] if node["text"] == "1. Правило.")
            self.assertEqual(node["kind"], "part")
            self.assertEqual(node["parent_address"], "act/article/1")

    def test_failed_optional_picture_pass_remains_an_explicit_uncertainty(self):
        document, run = saved_result()
        document["pages"][1]["layout"][1]["ocr_issue"] = {
            "stage": "picture_ocr", "reason": "incomplete_response", "finish_reason": "length"}
        extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
        self.assertIn("picture_ocr_incomplete_response", extraction["uncertainties"])
        self.assertNotIn("text", extraction["pages"][1]["regions"][1]["source_record"])


if __name__ == "__main__":
    unittest.main()
