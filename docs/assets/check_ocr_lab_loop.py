"""Explicit external-client checks of the opt-in loop retry: python check_ocr_lab_loop.py <OCR-Lab>."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


def native(cells, finish="stop"):
    text = cells if isinstance(cells, str) else json.dumps(cells)
    return {"choices": [{"message": {"content": text}, "finish_reason": finish}]}


UPRIGHT = [{"category": "Caption", "bbox": [10, 5, 300, 20], "text": "Форма журнала"},
           {"category": "Table", "bbox": [10, 30, 300, 160], "text": "<table><tr><th>Дата</th></tr></table>"}]
SIDEWAYS = [{"category": "Text", "bbox": [10, 20, 50, 300], "text": "Форма журнала"}]
# Greedy decoding repeated the last regions (sanpin-6-2025 p. 106) but this time stopped.
REPEATED = UPRIGHT + UPRIGHT[1:]


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        lab = Path(self.temporary.name)
        (lab / "config").mkdir()
        (lab / "config/dotsmocr_picture_ocr.json").write_text(json.dumps({"enabled": False}))
        self.lab = patch.object(client, "LAB", lab)
        self.lab.start()

    def tearDown(self):
        self.lab.stop()
        self.temporary.cleanup()

    def test_loop_cells_needs_a_finished_upright_layout_without_repeats(self):
        self.assertEqual(client.loop_cells(native(UPRIGHT)), UPRIGHT)
        self.assertEqual(client.loop_cells(native([UPRIGHT[1]])), [UPRIGHT[1]])  # a table-only page is upright
        for reply in (native(UPRIGHT, "length"), native(SIDEWAYS), native(REPEATED), native("[]"),
                      native("not json"), client.timed_out(TimeoutError("timed out"))):
            self.assertIsNone(client.loop_cells(reply))

    def test_first_accepted_setting_wins_and_every_attempt_is_retained(self):
        image = Image.new("RGB", (320, 420), "white")
        for replies, selected in (([native(UPRIGHT)], 0),
                                  ([native("[", "length"), native(UPRIGHT)], 1),
                                  ([native(REPEATED), native(UPRIGHT)], 1),
                                  ([TimeoutError("timed out"), native(UPRIGHT)], 1),
                                  ([native(SIDEWAYS), native("x", "length")], None)):
            for primary_kind in ("length", "timeout"):
                with self.subTest(replies=len(replies), selected=selected, primary=primary_kind):
                    primary = (native('[{"bbox": [1, 1, 2, 2], "category": "Table", "text": "<tr>', "length")
                               if primary_kind == "length" else client.timed_out(TimeoutError("timed out")))
                    calls, settings = iter(replies), []

                    def recognize(page, penalties=None):
                        settings.append(penalties)
                        reply = next(calls)
                        if isinstance(reply, Exception):
                            raise reply
                        return reply

                    accepted = client.retry_loop(primary, image, recognize)
                    retry = primary["loop_retry"]
                    self.assertEqual(accepted, selected is not None)
                    self.assertEqual((retry["trigger"], retry["selected"]), (primary_kind, selected))
                    self.assertEqual(settings, list(client.LOOP_SETTINGS)[:len(replies)])
                    self.assertEqual([a["penalties"] for a in retry["attempts"]], settings)
                    if selected is None:
                        with self.assertRaises(ValueError):
                            client.decode_native("dotsmocr", primary)
                        continue
                    decoded = client.decode_native("dotsmocr", primary)
                    self.assertEqual(decoded["layout"], UPRIGHT)
                    self.assertEqual(decoded["loop_retry"], client.LOOP_SETTINGS[selected])

    def test_turns_survive_a_timed_out_attempt(self):
        image = Image.new("RGB", (280, 420), "white")
        replies = iter([TimeoutError("timed out"), native("x", "length")])

        def recognize(page):
            reply = next(replies)
            if isinstance(reply, Exception):
                raise reply
            return reply

        primary = client.timed_out(TimeoutError("timed out"))
        self.assertFalse(client.retry_rotated(primary, image, recognize))
        attempts = primary["orientation_retry"]["attempts"]
        self.assertEqual(primary["orientation_retry"]["trigger"], "timeout")
        self.assertEqual(attempts[0]["native"]["client_error"], "TimeoutError: timed out")

    def test_upright_partial_answer_needs_wide_text_regions(self):
        head = '[{"bbox": [10, 5, 300, 20], "category": "Text", "text": "1. Форма"}, {"bbox": [10, 30, 300, 160], "category": "Table", "text": "<tr>'
        self.assertTrue(client.upright_partial(native(head, "length")))
        self.assertFalse(client.upright_partial(native(head.replace("[10, 5, 300, 20]", "[10, 5, 30, 300]"), "length")))
        self.assertFalse(client.upright_partial(native('[{"bbox": [10, 30, 300, 160], "category": "Table"', "length")))
        self.assertFalse(client.upright_partial(client.timed_out(TimeoutError("timed out"))))
        primary = native(head, "length")
        client.retry_loop(primary, Image.new("RGB", (320, 420), "white"),
                          lambda page, penalties=None: native(UPRIGHT), turns_skipped=True)
        self.assertEqual(primary["loop_retry"]["turns_skipped"], "upright_partial")

    def test_retry_is_opt_in_and_bounded(self):
        self.assertEqual(len(client.LOOP_SETTINGS), 2)
        primary = native(UPRIGHT)
        self.assertIsNone(client.retry_trigger(primary))
        self.assertNotIn("loop_retry", client.decode_native("dotsmocr", primary))
        self.assertEqual(client.request_image.__defaults__[-1], None)  # no penalties unless asked


if __name__ == "__main__":
    lab_root = Path(sys.argv.pop(1)).resolve()
    spec = importlib.util.spec_from_file_location("ocr_lab_client", lab_root / "scripts/new_ocr_pdf.py")
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    unittest.main()
