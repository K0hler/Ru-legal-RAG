"""Write the per-act OCR summary of an M1-04A check-pool batch (write-once).

Reproduces ``experiments/20261021-batch-01-ocr/summary.json`` from the raw output
of ``run_m1_04a_ocr.ps1`` and the saved run folders: timings and extraction ids
from the extraction pass (``summary.raw-first-pass.json`` for batch 1), replay ids
from the replay pass, and page coverage, uncertainties and unsupported regions
from each extraction. ``logical_text_id`` keeps batch 1's recorded form
``logical-text\\<id>`` (a Windows relative path without ``.json``).

    python docs/assets/summarize_m1_04a_ocr.py --experiment data/m1/m1-04a/experiments/20261021-batch-01-ocr \
        --extraction-raw summary.raw-first-pass.json --replay-raw summary.raw.json --output summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OCR = ROOT / "data" / "m1" / "m1-04a" / "ocr"


def summarize(extraction_raw: dict, replay_raw: dict, ocr_root: Path = OCR) -> dict:
    acts = {}
    for slug, act in extraction_raw["acts"].items():
        ext = json.loads((ROOT / act["extraction"]).read_text(encoding="utf-8"))
        (lt,) = sorted((ocr_root / slug / "run-01" / "logical-text").glob("*.json"))
        logical_text_id = json.loads(lt.read_text(encoding="utf-8"))["logical_text_id"]
        replay = replay_raw["replays"][slug]
        kinds = ext["uncertainties"]
        acts[slug] = {
            "pages": ext["coverage"]["source_pages"], "seconds": act["seconds"],
            "extraction_id": act["extraction_id"],
            "replay_extraction_id": replay["replay_extraction_id"], "replay_match": replay["replay_match"],
            "uncertainty_count": len(kinds), "uncertainty_by_kind": dict(Counter(kinds)),
            "picture_ocr_incomplete_responses": kinds.count("picture_ocr_incomplete_response"),
            "logical_text_id": "logical-text\\" + logical_text_id,
            "unsupported_regions": len(ext["unsupported_regions"]),
            "all_source_pages": ext["coverage"]["all_source_pages"],
        }
    return {"schema": "m1-04a-batch-ocr-summary/1", "health_wait_seconds": extraction_raw["health_wait_seconds"],
            "engine": "dotsmocr", "acts": acts}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--extraction-raw", required=True, help="raw summary of the extraction pass")
    parser.add_argument("--replay-raw", required=True, help="raw summary of the replay pass")
    parser.add_argument("--output", required=True, help="new file name inside --experiment")
    args = parser.parse_args(argv)
    exp = Path(args.experiment)

    def read(name):  # PowerShell 5 may have written a BOM
        return json.loads((exp / name).read_text(encoding="utf-8-sig"))

    record = summarize(read(args.extraction_raw), read(args.replay_raw))
    # Batch 1's file: indent 2, CRLF, no final newline.
    with (exp / args.output).open("x", encoding="utf-8", newline="\r\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
