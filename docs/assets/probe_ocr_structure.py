"""Explicit saved-OCR baseline and source-bound inputs for isolated parser trials."""

import argparse
from collections import Counter
import hashlib
from html import escape
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from legal_rag.corpus.compiler import content_hash, json_bytes, load_input  # noqa: E402
from legal_rag.corpus.ocr_runtime import load_extractions  # noqa: E402
from legal_rag.corpus.pdf_extraction import pdf_tree  # noqa: E402


def retain(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable experiment conflict: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(payload)


def prepare_html(lines):
    """Expose generic layout hints; retain a map for literal Markdown prefixes."""
    output, mapping = [], []
    for line in lines:
        text, category = line["text"], line["category"]
        clean = re.sub(r"^\s*#{1,6}\s+", "", text) if category in {"Title", "Section-header"} else text
        if clean != text:
            mapping.append({"uid": line["uid"], "before": text, "after": clean,
                            "operation": "remove_explicit_markdown_heading_prefix_for_classification_only"})
        tag = {"Title": "h1", "Section-header": "h2", "Footnote": "small",
               "Page-header": "small", "Page-footer": "small"}.get(category, "p")
        output.append(text if category == "Table" else f'<{tag} data-source-block-id="{line["uid"]}">{escape(clean)}</{tag}>')
    return '<!doctype html><html><meta charset="utf-8"><body>' + "".join(output) + '</body></html>', mapping


def probe(input_path, index_path, output):
    manifest, _, _ = load_input(input_path, "2025-01-01")
    extractions = load_extractions(index_path, manifest)
    rows = []
    for asset in manifest["assets"]:
        digest = asset["sha256"]
        extraction = extractions[digest]
        first = pdf_tree(extraction, asset["declared_identity"], asset["role"])
        second = pdf_tree(extraction, asset["declared_identity"], asset["role"])
        if first != second or not first["accounting"]["exactly_once"]:
            raise ValueError("nonrepeatable or incomplete baseline")
        dest = output / digest
        retain(dest / "baseline-tree.json", json_bytes(first))
        # All literal OCR strings and physical metadata survive this projection.
        lines = [{"uid": str(b["block_id"]), "text": b["original_text"],
                  "page": b["source_span"]["page"], "bbox": b["bbox"],
                  "source_span": b["source_span"],
                  "category": next(r["category"] for p in extraction["pages"]
                                   for r in p["regions"] if r["region_id"] == b["source_region_id"])}
                 for b in extraction["blocks"]]
        retain(dest / "lines.json", json_bytes({"extraction_id": extraction["extraction_id"],
                                               "source_asset_sha256": digest, "lines": lines}))
        retain(dest / "source.txt", "\n".join(b["text"] for b in lines).encode())
        prepared, mapping = prepare_html(lines)
        retain(dest / "prepared.html", prepared.encode())
        retain(dest / "projection-map.json", json_bytes(mapping))
        rows.append({"source_asset_sha256": digest, "identity_claim": asset["declared_identity"],
                     "role": asset["role"], "pages": len(extraction["pages"]),
                     "regions": sum(len(p["regions"]) for p in extraction["pages"]),
                     "blocks": len(lines), "extraction_id": extraction["extraction_id"],
                     "identity_status": first["identity_decision"]["status"],
                     "nodes": len(first["nodes"]), "unresolved": len(first["unresolved_blocks"]),
                     "node_kinds": dict(Counter(n["kind"] for n in first["nodes"])),
                     "categories": dict(Counter(line["category"] for line in lines)),
                     "structural_issues": first["structural_issues"],
                     "exactly_once": True, "repeat_identical": True,
                     "tree_sha256": hashlib.sha256(json_bytes(first)).hexdigest()})
    report = {"schema_version": "ocr-structure-baseline/1", "legal_admission": False,
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "input_hash": manifest["manifest_hash"], "index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
              "documents": rows, "total_pages": sum(row["pages"] for row in rows),
              "meaning": "Preservation/repeat baseline, not independent hierarchy qualification."}
    report["report_id"] = content_hash(report)
    retain(output / "baseline.json", json_bytes(report))
    print(json.dumps({"documents": len(rows), "pages": report["total_pages"],
                      "nodes": sum(r["nodes"] for r in rows), "unresolved": sum(r["unresolved"] for r in rows),
                      "report": str(output / "baseline.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--extraction-index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    probe(args.input.resolve(), args.extraction_index.resolve(), args.output_dir.resolve())
