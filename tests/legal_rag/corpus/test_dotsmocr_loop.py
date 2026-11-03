"""Explicit external-client checks of the opt-in loop retry: python check_ocr_lab_loop.py <OCR-Lab>."""

import importlib.util
import http.client
import io
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

    def test_layout_stream_retains_partial_timeout_and_cancels_a_long_repeated_tail(self):
        def event(text="", finish=None):
            return b"data: " + json.dumps({"id": "authored", "choices": [
                {"delta": {"content": text}, "finish_reason": finish}]}).encode() + b"\n"

        for error in (TimeoutError("timed out"), ConnectionResetError("reset"), http.client.IncompleteRead(b"", 1)):
            def interrupted():
                yield event("retained partial page")
                raise error

            partial = client.read_layout_stream(interrupted())
            self.assertEqual(partial["choices"][0]["message"]["content"], "retained partial page")
            self.assertEqual(client.retry_trigger(partial), "timeout")
        row = "<tr>" + "<td></td>" * 7 + "</tr>"

        def repeated():
            yield event(row * 220)
            raise AssertionError("cancel the abandoned stream before reading more")

        stopped = client.read_layout_stream(repeated())
        self.assertEqual(stopped["local_stop_reason"], "tail_repetition")
        self.assertEqual(client.retry_trigger(stopped), "tail_repetition")
        self.assertIsNone(client.loop_cells(stopped))
        finite = client.read_layout_stream(iter([event(row * 20), event(finish="stop"), b"data: [DONE]\n"]))
        self.assertEqual(finite["choices"][0]["message"]["content"], row * 20)
        self.assertIsNone(finite["local_stop_reason"])

    def test_expired_stream_is_rejected_even_when_its_last_chunk_says_stop(self):
        reply = b'data: {"choices": [{"delta": {"content": "[]"}, "finish_reason": "stop"}]}\n'
        with patch.object(client.time, "monotonic", side_effect=[179, 181]):
            result = client.read_layout_stream(iter([reply]), deadline=180)
        self.assertIn("client_error", result)
        with self.assertRaises(ValueError):
            client.decode_native("dotsmocr", result)

    def test_real_http_stall_keeps_the_received_event_with_a_short_deadline(self):
        import threading
        import time
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'data: {"choices": [{"delta": {"content": "partial"}, "finish_reason": null}]}\n')
                self.wfile.flush()
                time.sleep(1.5)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        real_open = client.urllib.request.urlopen

        def local_open(request, **kwargs):
            request.full_url = f"http://127.0.0.1:{server.server_port}/"
            return real_open(request, **kwargs)

        try:
            with patch.object(client, "LAYOUT_TIMEOUT", 0.75), \
                    patch.object(client.urllib.request, "urlopen", side_effect=local_open):
                result = client.request_image("dotsmocr", Image.new("RGB", (28, 28)), 24000,
                                              prompt="OCR", layout_stream=True)
            self.assertEqual(result["choices"][0]["message"]["content"], "partial")
            self.assertIn("client_error", result)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_loop_profile_streams_and_closes_connection_without_changing_sampling(self):
        class Response(io.BytesIO):
            def __iter__(self):
                return iter([b'data: {"choices": [{"delta": {"content": "[]"}, "finish_reason": "stop"}]}\n',
                             b'data: [DONE]\n'])

        response = Response()
        with patch.object(client.urllib.request, "urlopen", return_value=response) as call:
            result = client.request_image("dotsmocr", Image.new("RGB", (28, 28)), 24000,
                                          prompt="OCR", layout_stream=True, **client.DOTS_SAMPLING)
        payload = json.loads(call.call_args.args[0].data)
        self.assertTrue(payload["stream"])
        self.assertEqual((payload["temperature"], payload["seed"], payload["max_tokens"]), (0, 1, 24000))
        self.assertEqual(call.call_args.kwargs["timeout"], 180)
        self.assertTrue(response.closed)
        self.assertEqual(result["choices"][0]["finish_reason"], "stop")

    def test_loop_profile_finishes_later_pages_after_an_unrecoverable_page(self):
        from contextlib import nullcontext

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pdf = root / "source.pdf"
            pdf.write_bytes(b"authored PDF")
            replies = iter([native("x", "length") for _ in range(3)] + [native(UPRIGHT)])
            model = {"repo": "dots-studio/dots.mocr", "revision": "a" * 40}
            with patch.object(client, "create_runtime", return_value=(lambda image, **kw: next(replies), {})), \
                    patch.object(client, "model_manifest", return_value=model), \
                    patch.object(client, "open_pdf", return_value=nullcontext([0, 1])), \
                    patch.object(client, "render_page", return_value=Image.new("RGB", (320, 420))):
                with self.assertRaises(ValueError):
                    client.parse_pdf("dotsmocr", pdf, root / "output", workers=1, loop_retry=True)
            run = json.loads((root / "output/run.json").read_text())
            self.assertEqual(run["completed_pages"], [2], run)
            self.assertEqual(run["failed_pages"], [1])
            self.assertEqual(run["status"], "failed")
            self.assertTrue((root / "output/native/page_0001.json").exists())
            self.assertTrue((root / "output/pages/page_0002.json").exists())
