"""Check the external classifier integration without starting dots.mocr: script <OCR-Lab>."""
import importlib.util
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

CLIENT_PATH = Path(__file__).resolve().parents[3] / "ocr/dotsmocr/scripts/new_ocr_pdf.py"
spec = importlib.util.spec_from_file_location("legal_rag_dots_client", CLIENT_PATH)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class PageOrientationTests(unittest.TestCase):
    def test_four_angles_preserve_marked_source_pixels_and_boxes(self):
        source = Image.new("L", (280, 420), 255)
        source.paste(0, (30, 50, 90, 70))
        original = source.tobytes()
        for angle in (0, 90, 180, 270):
            with self.subTest(angle=angle):
                image, record = client.orient_page(source, lambda image: (str(angle), 0.99))
                bbox = list(Image.eval(image, lambda v: 255-v).getbbox())
                self.assertEqual(client.unorient_bbox(bbox, angle, source.size), [30, 50, 90, 70])
                self.assertEqual(record, {"angle": angle, "predicted_angle": angle, "confidence": 0.99,
                                          "image_size": list(image.size)})
                self.assertEqual(source.tobytes(), original)

    def test_unknown_classifier_label_is_an_error(self):
        with self.assertRaises(ValueError):
            client.orient_page(Image.new("RGB", (280, 420)), lambda image: ("45", 0.01))

    def test_low_confidence_never_turns_a_sparse_page(self):
        source = Image.new("RGB", (280, 420))
        for confidence in (0.2669, 0.84999, 0.85):
            image, record = client.orient_page(source, lambda image: ("180", confidence))
            self.assertEqual(record['angle'], 180 if confidence >= 0.85 else 0)
            self.assertEqual(record['predicted_angle'], 180)
            if confidence < 0.85:
                self.assertIs(image, source)

    def test_pipeline_recognizes_turned_image_and_saves_source_pixels(self):
        source = Image.new("L", (280, 420), 255)
        source.paste(0, (30, 50, 90, 70))
        turned_bbox = list(Image.eval(source.rotate(270, expand=True), lambda v: 255-v).getbbox())

        def recognize(image):
            self.assertEqual(image.size, (420, 280))
            self.assertEqual(list(Image.eval(image, lambda v: 255-v).getbbox()), turned_bbox)
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps([
                {"category": "Text", "bbox": turned_bbox, "text": "1. Условия"}])}}]}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "input.pdf"
            pdf.write_bytes(b"%PDF-1.7\nfixture")
            with (patch.object(client, "model_manifest", return_value={}),
                  patch.object(client, "load_page_orientation", return_value=(lambda image: ("270", 0.99), {})),
                  patch.object(client, "create_runtime", return_value=(recognize, {})),
                  patch.object(client, "recognize_picture_text"),
                  patch.object(client, "open_pdf", return_value=nullcontext([None])),
                  patch.object(client, "render_page", return_value=source)):
                client.parse_pdf("dotsmocr", pdf, root / "output", workers=1, page_orientation=True)
            output = root / "output"
            page = json.loads((output / "pages/page_0001.json").read_text())
            sidecar = json.loads((output / "native/page_0001.json").read_text())
            self.assertEqual(Image.open(output / "pages/page_0001.png").tobytes(), source.tobytes())
            self.assertEqual(page["image_size"], [280, 420])
            self.assertEqual(page["layout"][0]["bbox"], [30, 50, 90, 70])
            self.assertEqual(page["layout"][0]["oriented_bbox"], turned_bbox)
            self.assertEqual(page["page_orientation"], sidecar["page_orientation"])
