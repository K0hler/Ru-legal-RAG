import hashlib
import importlib.util
import json
from contextlib import nullcontext
from pathlib import Path
import sys
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from legal_rag.corpus.ocr_runtime import _read_ocr_output  # noqa: E402
from legal_rag.corpus.pdf_extraction import normalize_dotsmocr  # noqa: E402

spec = importlib.util.spec_from_file_location("legal_rag_dots_client", ROOT / "ocr/dotsmocr/scripts/new_ocr_pdf.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def test_client_export_round_trips_through_existing_normalizer(tmp_path):
    source = tmp_path / "synthetic.pdf"
    source.write_bytes(b"%PDF-1.7 synthetic test")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    cells = [{"category": "Text", "bbox": [20, 30, 240, 70], "text": "1. Тестовая строка"}]
    native = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(cells, ensure_ascii=False)}}]}
    model = {"repo": "dots-studio/dots.mocr", "revision": "a" * 40,
             "weights_sha256": {"model.safetensors": "b" * 64}}
    output = tmp_path / "output"
    with (patch.object(client, "model_manifest", return_value=model),
          patch.object(client, "create_runtime", return_value=(lambda image: native, {})),
          patch.object(client, "recognize_picture_text"),
          patch.object(client, "open_pdf", return_value=nullcontext([None])),
          patch.object(client, "render_page", return_value=Image.new("RGB", (280, 420), "white"))):
        client.parse_pdf("dotsmocr", source, output, workers=1)
    document, run = _read_ocr_output(output)
    extraction = normalize_dotsmocr(document, run, digest)
    assert document["pages"][0]["native"] == native
    assert run["export"]["format"] == "dotsmocr-layout/2"
    assert extraction["source_asset_sha256"] == digest
    assert "1. Тестовая строка" in json.dumps(extraction, ensure_ascii=False)
