"""Explicit offline Docling check on prepared saved OCR, not another OCR pass."""

import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import time

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.document_converter import DocumentConverter  # noqa: E402


def write(path, value):
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    converter = DocumentConverter(allowed_formats=[InputFormat.HTML])
    options = converter.format_to_options[InputFormat.HTML].backend_options
    assert not any((options.render_page, options.fetch_images, options.enable_remote_fetch, options.enable_local_fetch))
    rows = []
    for path in sorted(args.input_dir.glob("*/prepared.html")):
        started = time.perf_counter()
        payloads = []
        for attempt in (1, 2):
            result = converter.convert(path)
            assert result.status.value == "success", result.errors
            payload = result.document.export_to_dict(exclude_none=False)
            write(args.output_dir / path.parent.name / f"parsed-{attempt}.json", payload)
            payloads.append(payload)
        kinds = Counter(str(item.get("label")) for item in payloads[0]["texts"])
        rows.append({"source_asset_sha256": path.parent.name, "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "kinds": dict(kinds), "tables": len(payloads[0]["tables"]),
                     "identical_repeat": payloads[0] == payloads[1], "seconds_two_runs": time.perf_counter() - started})
        print(json.dumps(rows[-1]), flush=True)
    write(args.output_dir / "summary.json", {"schema_version": "docling-ocr-probe/1", "version": version("docling"),
          "documents": rows, "legal_admission": False, "ocr": False, "llm": False,
          "backend_options": options.model_dump(mode="json")})


if __name__ == "__main__":
    main()
