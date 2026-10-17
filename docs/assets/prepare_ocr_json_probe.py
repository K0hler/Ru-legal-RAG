"""Freeze permitted development OCR JSON for direct library API experiments."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from legal_rag.corpus.compiler import json_bytes, load_input  # noqa: E402
from legal_rag.corpus.ocr_runtime import load_extractions  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(cohort_dir, output):
    output.mkdir(parents=True, exist_ok=False)
    documents, protected = [], {}
    for receipt in sorted(cohort_dir.glob("*/repeats.json")):
        previous = json.loads(receipt.read_bytes())
        input_path, index_path = Path(previous["input"]), Path(previous["extraction_index"])
        target = json.loads(input_path.read_bytes())["target_dates"][0]
        manifest, _, _ = load_input(input_path, target)
        extractions = load_extractions(index_path, manifest)
        index = json.loads(index_path.read_bytes())
        for asset in manifest["assets"]:
            source = asset["sha256"]
            entry = index["extractions"][source]
            native = index_path.parent.parent / "ocr-evidence" / entry["native_evidence_id"] / "document.json"
            extraction = index_path.parent / entry["path"]
            payload = json.loads(native.read_bytes())
            normalized = extractions[source]
            assert len(payload["pages"]) == len(normalized["pages"])
            destination = output / source
            destination.mkdir()
            for original, name in ((native, "native.json"), (extraction, "extraction.json")):
                shutil.copyfile(original, destination / name)
                assert sha(original) == sha(destination / name)
                protected[str(original)] = sha(original)
            pages = payload["pages"]
            categories = Counter(r["category"] for p in pages for r in p["layout"])
            documents.append({"key": source, "source_asset_sha256": source,
                "group": receipt.parent.name, "input_manifest": str(input_path),
                "target_date": target, "role": asset["role"], "declared_identity": asset["declared_identity"],
                "native_path": str((destination / "native.json").resolve()),
                "extraction_path": str((destination / "extraction.json").resolve()),
                "native_sha256": sha(native), "extraction_sha256": sha(extraction),
                "extraction_id": normalized["extraction_id"], "pages": len(pages),
                "regions": sum(len(p["layout"]) for p in pages), "categories": dict(categories)})
        for p in (input_path, index_path):
            protected[str(p)] = sha(p)
    assert documents and len({d["source_asset_sha256"] for d in documents}) == len(documents)
    result = {"schema_version": "ocr-json-probe-input/1", "documents": documents,
        "protected_sha256": protected, "source": "unchanged native dots.mocr JSON, no HTML projection",
        "reserved_bodies_read": False, "closed_gold_access": False, "legal_admission": False}
    (output / "index.json").write_bytes(json_bytes(result))
    assert all(sha(Path(p)) == digest for p, digest in protected.items())
    print(json.dumps({"documents": len(documents), "pages": sum(d["pages"] for d in documents),
                      "index": str(output / "index.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.cohort_dir, args.output_dir)
