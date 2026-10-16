"""Explicit external-client checks: python check_ocr_lab_recovery.py <OCR-Lab>."""

import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


def native(text, finish="stop"):
    return {"choices": [{"message": {"content": text}, "finish_reason": finish}]}


def event(text="", finish=None, usage=None):
    data = {"id": "authored", "model": "dotsmocr", "choices": [
        {"delta": {"content": text}, "finish_reason": finish}], "usage": usage}
    return b"data: " + json.dumps(data).encode() + b"\n"


class Image:
    size = (1000, 1000)

    def crop(self, box):
        result = Image()
        result.size = (box[2] - box[0], box[3] - box[1])
        return result

    def save(self, stream, format):
        stream.write(b"authored image")


class RecoveryTests(unittest.TestCase):
    def test_retry_error_preserves_the_first_native_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            lab = Path(temporary)
            (lab / "config").mkdir()
            (lab / "config/dotsmocr_picture_ocr.json").write_text(json.dumps({
                "enabled": True, "padding_pixels": 28, "max_tokens": 512, "temperature": 0,
                "prompt": "OCR", "recover_repetitions": True}))
            original = native(json.dumps([{"category": "Picture", "bbox": [300, 300, 500, 500]}]))
            failed = native("raw repeated response", "length")
            with patch.object(client, "LAB", lab), patch.object(client, "request_image", side_effect=[failed, OSError("retry failed")]):
                with self.assertRaises(OSError):
                    client.recognize_picture_text(original, Image())
            self.assertEqual(len(original["picture_ocr"]), 1)
            self.assertIs(original["picture_ocr"][0]["attempts"][0]["native"], failed)

    def test_repeated_stream_stops_before_consuming_the_rest(self):
        def lines():
            yield event("unverified seal ")
            yield event("0" * 160)
            raise AssertionError("repetition must stop the stream early")

        response = client.read_picture_stream(lines())
        self.assertEqual(response["local_stop_reason"], "tail_repetition")
        self.assertEqual(len(response["stream_chunks"]), 2)
        self.assertNotEqual(response["choices"][0]["finish_reason"], "stop")

    def test_normal_stream_keeps_exact_text_finish_and_usage(self):
        response = client.read_picture_stream(iter([
            event("28."), event("01.2021"), event(finish="stop"),
            b'data: {"choices": [], "usage": {"completion_tokens": 5}}\n', b"data: [DONE]\n"]))
        self.assertEqual(response["choices"][0]["message"]["content"], "28.01.2021")
        self.assertEqual(response["choices"][0]["finish_reason"], "stop")
        self.assertEqual(response["usage"]["completion_tokens"], 5)
        self.assertIsNone(response["local_stop_reason"])

    def test_only_failed_picture_retries_once_and_retains_both_attempts(self):
        for replies in ([native("readable date")], [native("000", "length"), native("seal text")],
                        [native("000", "length"), native("111", "length")]):
            with self.subTest(attempts=len(replies)), tempfile.TemporaryDirectory() as temporary:
                lab = Path(temporary)
                (lab / "config").mkdir()
                settings = {"enabled": True, "padding_pixels": 28, "max_tokens": 512,
                            "temperature": 0, "prompt": "OCR", "failure_policy": "retain_unresolved",
                            "recover_repetitions": True}
                (lab / "config/dotsmocr_picture_ocr.json").write_text(json.dumps(settings))
                original = native(json.dumps([
                    {"category": "Picture", "bbox": [300, 300, 500, 500]},
                    {"category": "Text", "bbox": [10, 10, 100, 100], "text": "primary body"}]))
                with patch.object(client, "LAB", lab), patch.object(client, "request_image", side_effect=replies) as call:
                    client.recognize_picture_text(original, Image())
                self.assertEqual(call.call_count, len(replies))
                record = original["picture_ocr"][0]
                self.assertEqual(len(record["attempts"]), len(replies))
                self.assertEqual(record["attempts"][0]["image_size"], [256, 256])
                if len(replies) == 2:
                    self.assertEqual(record["image_size"], [456, 456])
                    self.assertIs(record["attempts"][0]["native"], replies[0])
                self.assertTrue(all(args.kwargs["picture_ocr"] for args in call.call_args_list))
                layout = client.decode_native("dotsmocr", original)["layout"]
                self.assertEqual(layout[1]["text"], "primary body")
                if replies[-1]["choices"][0]["finish_reason"] == "stop":
                    self.assertEqual(layout[0]["text"], replies[-1]["choices"][0]["message"]["content"])
                else:
                    self.assertNotIn("text", layout[0])
                    self.assertIn("ocr_issue", layout[0])

    def test_picture_flag_uses_stream_and_closes_connection(self):
        class Response(io.BytesIO):
            def __iter__(self):
                return iter([event("authored text"), event(finish="stop"), b"data: [DONE]\n"])

        response = Response()
        with patch.object(client.urllib.request, "urlopen", return_value=response) as call:
            result = client.request_image("dotsmocr", Image(), 512, prompt="OCR", temperature=0, picture_ocr=True)
        self.assertTrue(json.loads(call.call_args.args[0].data)["stream"])
        self.assertTrue(response.closed)
        self.assertEqual(result["choices"][0]["message"]["content"], "authored text")


if __name__ == "__main__":
    lab_root = Path(sys.argv.pop(1)).resolve()
    spec = importlib.util.spec_from_file_location("ocr_lab_client", lab_root / "scripts/new_ocr_pdf.py")
    client = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(client)
    unittest.main()
