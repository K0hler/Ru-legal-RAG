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


TURNED = [{"category": "Text", "bbox": [20, 10, 140, 30], "text": "1. Объем субсидии"},
          {"category": "Table", "bbox": [20, 40, 140, 90], "text": "<table><tr><td>1</td></tr></table>"}]


def rotated_result(attempts=(("cw90", TURNED),)):
    """Page 1 hit the token limit and was retried turned; layout is the accepted turn mapped back."""
    document, run = saved_result()
    page = document["pages"][0]
    page["image_size"] = [100, 150]
    page["native"]["choices"][0].update(finish_reason="length")
    page["native"]["choices"][0]["message"]["content"] = '[{"bbox": [10, 10, 30, 130], "category": "Table", "text": "<tr>'
    page["native"]["orientation_retry"] = {"trigger": "length", "selected": len(attempts) - 1, "attempts": [
        {"rotation": rotation, "image_size": [150, 100],
         "native": {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(cells, ensure_ascii=False)}}]}}
        for rotation, cells in attempts]}
    # cw90 on a 100x150 page: turned (x1, y1, x2, y2) -> (y1, 150 - x2, y2, 150 - x1).
    page["layout"] = [{**cell, "bbox": [cell["bbox"][1], 150 - cell["bbox"][2], cell["bbox"][3], 150 - cell["bbox"][0]],
                       "rotated_bbox": cell["bbox"], "page_rotation": attempts[-1][0]} for cell in attempts[-1][1]]
    return document, run


UPRIGHT = [{"category": "Caption", "bbox": [10, 5, 90, 15], "text": "Форма журнала"},
           {"category": "Table", "bbox": [10, 20, 90, 60], "text": "<table><tr><th>Дата</th></tr><tr><td></td></tr></table>"}]
LOOPED = [{"category": "Table", "bbox": [10, 20, 90, 60], "text": "<table><tr><th>Дата</th></tr><tr><td></td></tr></table>"}] * 2


def looped_result(attempts=(LOOPED, UPRIGHT), primary="length", turns=True):
    """Page 1 looped (token limit or client timeout), both turns failed, the upright retry finished."""
    document, run = saved_result()
    page = document["pages"][0]
    native = page["native"]
    native["choices"][0]["message"]["content"] = '[{"bbox": [10, 20, 90, 60], "category": "Table", "text": "<tr><td></td>'
    if primary == "length":
        native["choices"][0]["finish_reason"] = "length"
    else:
        native["choices"][0].update(finish_reason=None, message={"role": "assistant", "content": None})
        native.update(client_error="TimeoutError: timed out", client_timeout_seconds=900)
    if turns:
        native["orientation_retry"] = {"trigger": "length", "selected": None, "attempts": [
            {"rotation": rotation, "image_size": [100, 100],
             "native": {"choices": [{"finish_reason": "length", "message": {"content": "[{"}}]}}
            for rotation in pdf.ROTATIONS]}
    native["loop_retry"] = {"trigger": primary, "selected": len(attempts) - 1, "attempts": [
        {"penalties": settings, "native": {"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(cells, ensure_ascii=False)}}]}}
        for settings, cells in zip(pdf.LOOP_SETTINGS, attempts)]}
    page["layout"] = copy.deepcopy(list(attempts[-1]))
    return document, run


class PdfExtractionTest(unittest.TestCase):
    def test_timed_out_rotation_with_stop_is_not_an_accepted_retry(self):
        document, run = rotated_result()
        document["pages"][0]["native"]["orientation_retry"]["attempts"][0]["native"].update(
            client_error="TimeoutError: deadline exceeded")
        with self.assertRaises(ValueError):
            pdf.normalize_dotsmocr(document, run, DIGEST)

    def test_early_cancelled_primary_requires_a_retained_successful_retry(self):
        document, run = looped_result(turns=False)
        page = document["pages"][0]
        page["native"]["choices"][0]["finish_reason"] = None
        page["native"]["local_stop_reason"] = "tail_repetition"
        page["native"]["loop_retry"]["trigger"] = "tail_repetition"
        extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
        self.assertIn("page_loop_retry", extraction["uncertainties"])
        del page["native"]["loop_retry"]
        with self.assertRaises(ValueError):
            pdf.normalize_dotsmocr(document, run, DIGEST)

    def test_loop_retry_layout_is_accepted_only_from_its_retained_attempt(self):
        # Observed: blank form rows (sanpin-20-2015 p. 24) and repeated last regions (sanpin-6-2025 p. 106).
        for primary, attempts, turns in (("length", (LOOPED, UPRIGHT), True), ("timeout", (UPRIGHT,), True),
                                          ("length", (UPRIGHT,), False)):
            with self.subTest(primary=primary, attempts=len(attempts), turns=turns):
                document, run = looped_result(attempts, primary, turns)
                extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
                page = extraction["pages"][0]
                self.assertEqual(page["loop_retry"], pdf.LOOP_SETTINGS[len(attempts) - 1])
                self.assertEqual([r["category"] for r in page["regions"]], ["Caption", "Table"])
                self.assertIn("page_loop_retry", extraction["uncertainties"])
                self.assertNotIn("loop_retry", extraction["pages"][1])
                tree = pdf.pdf_tree(extraction, "Неустановленный акт", "original")
                self.assertTrue(tree["accounting"]["exactly_once"])

    def test_loop_retry_mutations_are_rejected(self):
        sideways = [{"category": "Text", "bbox": [10, 10, 20, 90], "text": "боком"}]
        for mutation in ("text", "bbox", "extra_region", "rotated_bbox", "settings", "order", "no_selection",
                         "not_last", "earlier_accepted", "duplicate_regions", "sideways", "unfinished_attempt",
                         "primary_stop", "turn_accepted", "turn_missing", "third_attempt", "page_error"):
            with self.subTest(mutation=mutation):
                document, run = looped_result()
                page = document["pages"][0]
                retry = page["native"]["loop_retry"]
                last = retry["attempts"][-1]["native"]["choices"][0]
                if mutation == "text":
                    page["layout"][0]["text"] = "Иная форма"
                elif mutation == "bbox":
                    page["layout"][0]["bbox"] = [10, 5, 90, 16]
                elif mutation == "extra_region":
                    page["layout"].append({"category": "Text", "bbox": [1, 1, 2, 2], "text": "x"})
                elif mutation == "rotated_bbox":
                    page["layout"][0]["rotated_bbox"] = [5, 10, 15, 90]
                elif mutation == "settings":
                    retry["attempts"][-1]["penalties"] = {"frequency_penalty": 1.0}
                elif mutation == "order":
                    retry["attempts"].reverse()
                elif mutation == "no_selection":
                    retry["selected"] = None
                elif mutation == "not_last":
                    retry["selected"] = 0
                elif mutation == "earlier_accepted":
                    retry["attempts"][0]["native"] = copy.deepcopy(retry["attempts"][1]["native"])
                elif mutation == "duplicate_regions":
                    last["message"]["content"] = json.dumps(UPRIGHT + UPRIGHT[1:], ensure_ascii=False)
                    page["layout"] = copy.deepcopy(UPRIGHT + UPRIGHT[1:])
                elif mutation == "sideways":
                    last["message"]["content"] = json.dumps(sideways, ensure_ascii=False)
                    page["layout"] = copy.deepcopy(sideways)
                elif mutation == "unfinished_attempt":
                    last["finish_reason"] = "length"
                elif mutation == "primary_stop":
                    page["native"]["choices"][0]["finish_reason"] = "stop"
                elif mutation == "turn_accepted":
                    page["native"]["orientation_retry"]["attempts"][1]["native"] = {"choices": [{
                        "finish_reason": "stop", "message": {"content": json.dumps(UPRIGHT, ensure_ascii=False)}}]}
                elif mutation == "turn_missing":
                    del page["native"]["orientation_retry"]["attempts"][1]
                elif mutation == "third_attempt":
                    retry["attempts"].append(copy.deepcopy(retry["attempts"][-1]) | {"penalties": {"seed": 2}})
                    retry["selected"] = 2
                else:
                    page["error"] = "ValueError: incomplete"
                with self.assertRaises(ValueError):
                    pdf.normalize_dotsmocr(document, run, DIGEST)

    def test_turns_are_skipped_only_after_an_upright_partial_answer(self):
        upright = '[{"bbox": [10, 5, 90, 15], "category": "Text", "text": "1. Форма"}, {"bbox": [10, 20, 90, 60], "category": "Table", "text": "<tr>'
        sideways = '[{"bbox": [10, 5, 20, 90], "category": "Text", "text": "1. Форма"}, {"bbox": [10, 20, 90, 60], "category": "Table", "text": "<tr>'
        for partial, skipped, rotation_on, accepted in ((upright, True, True, True), (sideways, True, True, False),
                                                        (upright, True, False, False), (upright, False, True, False),
                                                        ('[{"bbox": [10, 20, 90, 60], "category": "Table"', True, True, False)):
            with self.subTest(partial=partial[:40], skipped=skipped, rotation_on=rotation_on):
                document, run = looped_result(turns=False)
                native = document["pages"][0]["native"]
                native["choices"][0]["message"]["content"] = partial
                if skipped:
                    native["loop_retry"]["turns_skipped"] = "upright_partial"
                if rotation_on:
                    run["config"]["rotation_retry"] = {"trigger": "length", "rotations": list(pdf.ROTATIONS)}
                if accepted:
                    self.assertIn("page_loop_retry", pdf.normalize_dotsmocr(document, run, DIGEST)["uncertainties"])
                else:
                    with self.assertRaises(ValueError):
                        pdf.normalize_dotsmocr(document, run, DIGEST)

    def test_timeout_without_loop_retry_fails(self):
        document, run = looped_result()
        del document["pages"][0]["native"]["loop_retry"]
        document["pages"][0]["native"].update(client_error="TimeoutError: timed out")
        with self.assertRaises(ValueError):
            pdf.normalize_dotsmocr(document, run, DIGEST)

    def test_rotated_retry_layout_is_accepted_only_from_its_retained_attempt(self):
        document, run = rotated_result()
        extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
        page = extraction["pages"][0]
        self.assertEqual(page["orientation_retry"], "cw90")
        self.assertEqual(page["regions"][0]["bbox"], [10, 10, 30, 130])
        self.assertEqual(page["regions"][0]["source_record"]["rotated_bbox"], [20, 10, 140, 30])
        self.assertIn("page_orientation_retry", extraction["uncertainties"])
        self.assertNotIn("orientation_retry", extraction["pages"][1])
        sideways = [{"category": "Text", "bbox": [10, 10, 30, 140], "text": "боком"}]
        second = rotated_result((("cw90", sideways), ("ccw90", TURNED)))[0]
        second["pages"][0]["layout"] = document["pages"][0]["layout"]
        for cell in second["pages"][0]["layout"]:
            cell["page_rotation"] = "ccw90"
        # ccw90 maps differently, so a cw90-shaped layout must not pass as the second turn.
        with self.assertRaises(ValueError):
            pdf.normalize_dotsmocr(second, run, DIGEST)

    def test_rotated_retry_mutations_are_rejected(self):
        for mutation in ("bbox", "text", "category", "rotated_bbox", "rotation_label", "no_selection",
                         "not_last", "sideways", "image_size", "primary_stop", "unknown_rotation",
                         "extra_region", "third_attempt"):
            with self.subTest(mutation=mutation):
                document, run = rotated_result()
                page = document["pages"][0]
                retry = page["native"]["orientation_retry"]
                if mutation == "bbox":
                    page["layout"][0]["bbox"] = [10, 10, 30, 129]
                elif mutation == "text":
                    page["layout"][0]["text"] = "2. Иной текст"
                elif mutation == "category":
                    page["layout"][1]["category"] = "Picture"
                elif mutation == "rotated_bbox":
                    del page["layout"][0]["rotated_bbox"]
                elif mutation == "rotation_label":
                    page["layout"][0]["page_rotation"] = "ccw90"
                elif mutation == "no_selection":
                    retry["selected"] = None
                elif mutation == "not_last":
                    retry["attempts"].append(copy.deepcopy(retry["attempts"][0]) | {"rotation": "ccw90"})
                elif mutation == "sideways":
                    sideways = [{"category": "Text", "bbox": [20, 10, 40, 140], "text": "боком"}]
                    retry["attempts"][0]["native"]["choices"][0]["message"]["content"] = json.dumps(sideways)
                elif mutation == "image_size":
                    retry["attempts"][0]["image_size"] = [100, 150]
                elif mutation == "primary_stop":
                    page["native"]["choices"][0]["finish_reason"] = "stop"
                elif mutation == "unknown_rotation":
                    retry["attempts"][0]["rotation"] = "flip180"
                elif mutation == "extra_region":
                    page["layout"].append({"category": "Text", "bbox": [1, 1, 2, 2], "text": "x"})
                else:
                    retry["attempts"] = [copy.deepcopy(retry["attempts"][0]) for _ in range(3)]
                    retry["selected"] = 2
                with self.assertRaises(ValueError):
                    pdf.normalize_dotsmocr(document, run, DIGEST)

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

    def test_table_nested_in_a_cell_keeps_both_topologies_and_text_once(self):
        # Observed in batch 13 (favt-150-2023 p. 63): a sector table inside a cell of the requirements table.
        html = ('<table><thead><tr><th>Ограничения</th><th>Обоснование</th></tr></thead><tbody><tr>'
                '<td>2. Запрещается:<br><table><tr><th>Сектор</th><th>Высота</th></tr>'
                '<tr><td>A1</td><td>174,93</td></tr></table>после</td><td>Пункт 3</td></tr></tbody></table>')
        document, run = saved_result()
        document["pages"][1]["layout"][0]["text"] = html
        extraction = pdf.normalize_dotsmocr(document, run, DIGEST)
        table = extraction["pages"][1]["regions"][0]["table"]
        self.assertNotIn("grid", table)
        self.assertEqual((table["rows"], table["columns"]), (2, 2))
        outer = table["cells"][2]
        self.assertEqual(outer["text"], "2. Запрещается:\nСектор\nВысота\nA1\n174,93\nпосле")
        inner = outer["tables"][0]
        self.assertEqual((inner["rows"], inner["columns"]), (2, 2))
        self.assertEqual([c["text"] for c in inner["cells"]], ["Сектор", "Высота", "A1", "174,93"])
        self.assertEqual(table["text"].count("174,93"), 1)
        self.assertIn("table_nested", extraction["uncertainties"])
        tree = pdf.pdf_tree(extraction, "Неустановленный акт", "original")
        self.assertTrue(tree["accounting"]["exactly_once"])
        for broken in ('<table><tr><td>1</td></tr></table><table><tr><td>2</td></tr></table>',
                       '<table><tr><table><tr><td>1</td></tr></table></tr></table>',
                       '<table><tr><td><table></table></td></tr></table>',
                       '<table><tr><td><table><tr><td>1</td></tr></td></tr></table>'):
            with self.subTest(html=broken):
                document, run = saved_result()
                document["pages"][1]["layout"][0]["text"] = broken
                with self.assertRaises(ValueError):
                    pdf.normalize_dotsmocr(document, run, DIGEST)

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
