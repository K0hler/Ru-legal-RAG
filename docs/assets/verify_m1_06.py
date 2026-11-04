"""Audit complete retained PDF bundles; source accounting is not structure acceptance."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from legal_rag.corpus.compiler import content_hash, json_bytes, load_input  # noqa: E402
from legal_rag.corpus.ocr_runtime import load_extractions  # noqa: E402
from check_m1_04a_source_controls import compare_controls, validate_controls  # noqa: E402
from validate_ocr_structure import require, unique, validate_source  # noqa: E402


def verify_bundle(manifest, extractions, first, second, controls, *, target_date):
    assets = unique(manifest["assets"], "sha256", "input asset")
    require(assets and set(extractions) == set(assets), "extraction coverage differs from full input")
    for draft in (first, second):
        require(target_date in manifest["target_dates"]
                and draft["target_date"] == draft["content"]["target_date"] == target_date,
                "draft target date mismatch")
        require(draft["content"]["kind"] == manifest["kind"], "draft source route mismatch")
        require(draft["input_hash"] == manifest["manifest_hash"]
                and draft["validated_input_hash"] == content_hash(manifest), "draft input binding mismatch")
        require(draft["content_hash"] == content_hash(draft["content"]), "draft content hash mismatch")
        require(draft["draft_id"] == content_hash({k: v for k, v in draft.items() if k != "draft_id"}),
                "draft identity mismatch")
    require(first == second, "repeated full compilation differs")
    trees = unique(first["content"]["trees"], "source_asset_sha256", "compiled source")
    require(set(trees) == set(assets), "compiled document coverage differs from full input")
    require(set(controls) <= set(assets), "controls contain a foreign source")
    documents = []
    for sha, asset in assets.items():
        extraction, tree = extractions[sha], trees[sha]
        require(extraction["source_asset_sha256"] == sha, "extraction binds a different PDF")
        require(tree["role"] == asset["role"], "tree role differs from selected asset")
        namespace = "amendment/" + sha if asset["role"] == "amendment" else "act"
        require(tree["namespace"] == namespace, "tree namespace differs from selected asset")
        for node in tree["nodes"]:
            require(node["node_id"] == content_hash({"source": sha, "parser": tree["parser_version"],
                                                      "address": node["address"]}), "canonical node identity mismatch")
        coverage = extraction["coverage"]
        require(coverage["all_source_pages"] and coverage["requested_pages"] == list(range(1, coverage["source_pages"] + 1))
                and [p["page"] for p in extraction["pages"]] == coverage["requested_pages"], "incomplete PDF pages")
        validate_source(extraction, tree)
        structure = {"status": "missing_controls"}
        if sha in controls:
            packet, annotation = controls[sha]
            structure.update(packet_hash=content_hash(packet), controls_hash=content_hash(annotation))
            try:
                structure["comparison"] = compare_controls(extraction, tree, packet, annotation)
                validate_controls(extraction, tree, packet, annotation)
                structure["status"] = "pass"
            except ValueError as error:
                structure.update(status="fail", reason=str(error))
        documents.append({"source_asset_sha256": sha, "role": asset["role"],
                          "extraction_id": extraction["extraction_id"], "parser_version": tree["parser_version"],
                          "pages": len(extraction["pages"]), "regions": len(tree["region_bindings"]),
                          "tables": sum("table" in r for p in extraction["pages"] for r in p["regions"]),
                          "accounting": tree["accounting"], "structure": structure})
    statuses = {d["structure"]["status"] for d in documents}
    status = "fail" if "fail" in statuses else "incomplete" if "missing_controls" in statuses else "pass"
    return {"schema_version": "m1-06-bundle-review/1", "status": status, "scope": "source_accounting_and_structure_only",
            "input_hash": manifest["manifest_hash"], "draft_id": first["draft_id"],
            "content_hash": first["content_hash"], "repeat": "identical",
            "accounting": {"documents": len(documents), **{k: sum(d[k] for d in documents) for k in ("pages", "regions", "tables")}},
            "documents": documents, "legal_admission": "not_requested",
            "limitations": ["OCR transcription/table accuracy and G13 transfer require separate evidence."]}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "extraction-index", "first", "second", "controls", "output"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument("--date", required=True)
    args = cli.parse_args()
    manifest, _, _ = load_input(args.input, args.date)
    extractions = load_extractions(args.extraction_index, manifest)
    index = json.loads(args.extraction_index.read_bytes())
    controls = {}
    for sha, reference in index["extractions"].items():
        packet_path, annotation_path = args.controls / sha / "packet.json", args.controls / sha / "controls.json"
        if not annotation_path.exists():
            continue
        packet = json.loads(packet_path.read_bytes())
        evidence = args.extraction_index.parent.parent / "ocr-evidence" / reference["native_evidence_id"]
        for page in packet["pages"]:
            image = evidence / "pages" / f"page_{page['page']:04d}.png"
            require(hashlib.sha256(image.read_bytes()).hexdigest() == page["sha256"], "control image differs from selected OCR evidence")
        controls[sha] = packet, json.loads(annotation_path.read_bytes())
    result = verify_bundle(manifest, extractions, json.loads(args.first.read_bytes()), json.loads(args.second.read_bytes()),
                           controls, target_date=args.date)
    payload = json_bytes(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        require(args.output.read_bytes() == payload, "immutable review conflict")
    else:
        with args.output.open("xb") as stream:
            stream.write(payload)
    print(json.dumps({k: result[k] for k in ("status", "accounting", "repeat", "legal_admission")}))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
