"""Re-normalize every saved M1-04A OCR run and compare its extraction_id with the recorded one.

Run from the repository root after a change to `pdf_extraction.py`:
    .venv/Scripts/python.exe docs/assets/check_m1_04a_ocr_replay.py --output <experiment>/replay-check.json
Each `<root>/<slug>/<run>-extract-result.json` names the extraction and its native evidence; the
evidence is read as saved (no Docker) and normalized by the current code. Exit 1 on any difference.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from legal_rag.corpus.compiler import _read, content_hash  # noqa: E402
from legal_rag.corpus.ocr_runtime import _read_ocr_output  # noqa: E402
from legal_rag.corpus.pdf_extraction import normalize_dotsmocr  # noqa: E402


def replay(result_path):
    result = json.loads(result_path.read_text(encoding="utf-8"))
    (digest, entry), = result["extractions"].items()
    evidence = Path(result["native_evidence"][digest])
    if not evidence.is_absolute():
        evidence = result_path.parent / evidence
    document, run = _read_ocr_output(evidence)
    if (evidence / "provider-runtime.json").exists():  # As in ocr_runtime.extract_input.
        run = {**run, "runtime_fingerprint": content_hash(_read(evidence / "provider-runtime.json"))}
    extraction = normalize_dotsmocr(document, run, digest)
    return entry["extraction_id"], extraction["extraction_id"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, action="append",
                        help="Folder holding <slug>/<run>-extract-result.json (default: data/m1/m1-04a/ocr)")
    parser.add_argument("--output", type=Path, required=True, help="New JSON report; never overwritten")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"{args.output} exists; not overwritten")
    roots = args.root or [Path("data/m1/m1-04a/ocr")]
    rows = {}
    for root in roots:
        for path in sorted(root.glob("*/*-extract-result.json")):
            key = path.relative_to(root).as_posix()
            try:
                recorded, again = replay(path)
                rows[f"{root.as_posix()}/{key}"] = {"recorded": recorded, "replayed": again, "equal": recorded == again}
            except Exception as error:  # A saved run that no longer normalizes is a regression too.
                rows[f"{root.as_posix()}/{key}"] = {"equal": False, "error": f"{type(error).__name__}: {error}"}
    differ = sorted(key for key, row in rows.items() if not row["equal"])
    report = {"schema": "m1-04a-ocr-replay-check/1", "runs": len(rows), "equal": len(rows) - len(differ),
              "differ": differ, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("runs", "equal", "differ")}, ensure_ascii=False))
    return 1 if differ else 0


if __name__ == "__main__":
    raise SystemExit(main())
