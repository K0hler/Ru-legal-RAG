"""Explicit external-client checks of the opt-in rotation retry: python check_ocr_lab_rotation.py <OCR-Lab>."""

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


UPRIGHT = [{"category": "Text", "bbox": [10, 20, 300, 60], "text": "1. Объем субсидии"},
           {"category": "Table", "bbox": [10, 80, 300, 160], "text": "<table><tr><td></td></tr></table>"}]
# The same page read sideways: a tall narrow text column.
SIDEWAYS = [{"category": "Text", "bbox": [10, 20, 50, 300], "text": "1. Объем субсидии"}]


class RotationTests(unittest.TestCase):
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

    def test_unrotate_maps_a_marked_box_back_onto_the_page(self):
        page = Image.new("L", (280, 420), 255)
        page.paste(0, (30, 50, 90, 70))  # x 30..90, y 50..70 on the upright page image
        for rotation, angle in client.ROTATIONS.items():
            with self.subTest(rotation=rotation):
                turned = page.rotate(angle, expand=True)
                self.assertEqual(turned.size, (420, 280))
                box = list(Image.eval(turned, lambda v: 255 - v).getbbox())
                self.assertEqual(client.unrotate_bbox(box, rotation, page.size), [30, 50, 90, 70])

    def test_sideways_text_needs_wide_text_regions(self):
        self.assertFalse(client.sideways_text(UPRIGHT))
        self.assertTrue(client.sideways_text(SIDEWAYS))
        self.assertTrue(client.sideways_text([UPRIGHT[1]]))  # no text-bearing region at all
        # A one-digit page number is taller than wide and is not evidence.
        self.assertFalse(client.sideways_text(UPRIGHT + [
            {"category": "Page-header", "bbox": [5, 5, 15, 30], "text": "3"}]))

    def test_first_accepted_turn_wins_and_every_attempt_is_retained(self):
        image = Image.new("RGB", (280, 420), "white")
        for replies, selected in (([native(UPRIGHT)], 0),
                                  ([native("[]", "length"), native(UPRIGHT)], 1),
                                  ([native(SIDEWAYS), native(UPRIGHT)], 1),
                                  ([native("not json"), native(SIDEWAYS)], None),
                                  ([native("x", "length"), native("y", "length")], None)):
            with self.subTest(replies=len(replies), selected=selected):
                primary = native('[{"bbox": [1, 1, 2, 2], "category": "Table", "text": "<tr>', "length")
                calls = iter(replies)
                accepted = client.retry_rotated(primary, image, lambda turned: next(calls))
                retry = primary["orientation_retry"]
                self.assertEqual(accepted, selected is not None)
                self.assertEqual(retry["selected"], selected)
                self.assertEqual([a["rotation"] for a in retry["attempts"]], list(client.ROTATIONS)[:len(replies)])
                self.assertTrue(all(a["image_size"] == [420, 280] for a in retry["attempts"]))
                self.assertEqual(primary["choices"][0]["finish_reason"], "length")
                if selected is None:
                    with self.assertRaises(ValueError):
                        client.decode_native("dotsmocr", primary)
                    continue
                layout = client.decode_native("dotsmocr", primary)["layout"]
                rotation = retry["attempts"][selected]["rotation"]
                self.assertEqual(layout[0]["rotated_bbox"], UPRIGHT[0]["bbox"])
                self.assertEqual(layout[0]["bbox"], client.unrotate_bbox(UPRIGHT[0]["bbox"], rotation, (280, 420)))
                self.assertEqual({cell["page_rotation"] for cell in layout}, {rotation})
                self.assertEqual(layout[0]["text"], UPRIGHT[0]["text"])

    def test_retry_is_opt_in_and_bounded_to_two_turns(self):
        self.assertEqual(len(client.ROTATIONS), 2)
        primary = native(UPRIGHT)
        self.assertNotIn("orientation_retry", primary)
        self.assertNotIn("rotated_bbox", client.decode_native("dotsmocr", primary)["layout"][0])


if __name__ == "__main__":
    lab_root = Path(sys.argv.pop(1)).resolve()
    spec = importlib.util.spec_from_file_location("ocr_lab_client", lab_root / "scripts/new_ocr_pdf.py")
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    unittest.main()
