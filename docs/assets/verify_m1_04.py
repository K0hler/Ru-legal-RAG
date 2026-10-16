"""Explicit retained OCR qualification; never acquires sources or reads retrieval gold."""

import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from legal_rag.corpus.compiler import content_hash, json_bytes, load_input  # noqa: E402
from legal_rag.corpus.ocr_runtime import load_extractions  # noqa: E402


def read(path):
    return json.loads(path.read_bytes())


def page_changes(first, second):
    result = {"text": [], "categories": [], "geometry": []}
    left, right = {p["page"]: p for p in first}, {p["page"]: p for p in second}
    for page in sorted(left.keys() | right.keys()):
        a, b = left.get(page, {}), right.get(page, {})
        for field, name in (("text", "text"), ("category", "categories"), ("bbox", "geometry")):
            values = [[r["source_record"].get(field) for r in p.get("regions", [])] for p in (a, b)]
            if values[0] != values[1]:
                result[name].append(page)
    return result


def account(extraction, native):
    regions = [r for p in extraction["pages"] for r in p["regions"]]
    expected_regions = [r for p in native["pages"] for r in p["layout"]]
    assert len(regions) == len(expected_regions)
    assert [r["source_record"] for r in regions] == expected_regions
    assert len({r["region_id"] for r in regions}) == len(regions)
    for token in extraction["text_nodes"]:
        span = token["source_span"]
        _, _, page, _, region, _ = span["json_pointer"].split("/")
        source = native["pages"][int(page)]["layout"][int(region)]["text"]
        assert source[span["ocr_char_start"]:span["ocr_char_end"]] == token["raw_text"]
    return {"pages": len(extraction["pages"]), "regions": len(regions),
            "text_nodes": len(extraction["text_nodes"]),
            "tables": sum("table" in r for r in regions), "all_regions_and_text_spans": True}


def conditional_signs(extraction, controls):
    rows = {}
    page = next(p for p in extraction["pages"] if p["page"] == 75)
    for region in page["regions"]:
        table = region.get("table", {})
        for row in range(table.get("rows", 0)):
            expanded = []
            for cell in sorted((c for c in table["cells"] if c["row"] == row), key=lambda c: c["column"]):
                expanded.extend([cell["text"]] * cell["colspan"])
            if expanded and re.fullmatch(r"\s*[0-9]+\s*", expanded[0]):
                number = int(expanded[0])
                if number in rows:
                    rows[number] = []  # Ambiguous duplicate rows cannot pass a positional control.
                else:
                    rows[number] = expanded
    checks = []
    for number, columns in controls["page_75_conditional_cells"]["rows"].items():
        cells = rows.get(int(number), [])
        for column in columns:
            actual = cells[column - 1] if len(cells) == 9 else None
            normalized = re.sub(r"\s+", "", actual or "").translate(str.maketrans({"−": "-", "–": "-", "—": "-", "/": None}))
            checks.append({"row": int(number), "column": column, "expected": "+-", "actual": actual,
                           "row_width": len(cells), "matches": actual is not None and normalized == "+-"})
    return {"matches": sum(c["matches"] for c in checks), "total": len(checks), "checks": checks}


def reference_metrics(extraction, reference, lab):
    sys.path.insert(0, str(lab))
    from benchmark.adapters import candidate_page, page_text, reference_page
    from benchmark.metrics import text_metrics

    actual = {p["page"]: p for p in extraction["pages"]}
    values = []
    for page in reference["pages"]:
        number = page["page_number"]
        candidate = {"layout": [r["source_record"] for r in actual[number]["regions"]]}
        expected_text = page_text(reference_page(page))
        actual_text = page_text(candidate_page("dotsmocr_layout", candidate, number))
        values.append({"page": number, **text_metrics(expected_text, actual_text)})
    totals = {key: sum(v[key] for v in values) for key in ("char_edits", "word_edits", "reference_chars", "reference_words")}
    return {"reference_id": reference["reference_id"], "human_review": reference["provenance"]["human_review"],
            "scope": "OCR-Lab benchmark normalization; excludes Picture text and printed page numbers; no content repair",
            "pages": values, "pooled_cer": totals["char_edits"] / totals["reference_chars"],
            "pooled_wer": totals["word_edits"] / totals["reference_words"], "totals": totals}


def reviewed_sample(path, reference, evidence_dirs, metrics):
    review = read(path)
    page = next((p for p in reference["pages"] if p["page_number"] == review.get("physical_page")), None)
    if (review.get("schema_version") != "ocr-transcription-review/1"
            or review.get("decision") != "accepted" or not review.get("reviewer", "").strip()
            or review.get("source_asset_sha256") != reference["source"]["sha256"] or page is None):
        raise ValueError("transcription review does not bind the reference page")
    if datetime.fromisoformat(review["recorded_at"]).utcoffset() is None:
        raise ValueError("transcription review timestamp needs a timezone")
    if (sha256(page["text"].encode("utf-8")).hexdigest() != review.get("reference_sha256")
            or sha256((path.parent / "reference.txt").read_bytes()).hexdigest()
            != review.get("reference_artifact_sha256")):
        raise ValueError("transcription reference hash mismatch")
    for evidence in evidence_dirs:
        image = evidence / "pages" / f"page_{page['page_number']:04d}.png"
        if sha256(image.read_bytes()).hexdigest() != review.get("image_sha256"):
            raise ValueError("transcription image hash mismatch")
    return {"decision": review, "decision_sha256": sha256(path.read_bytes()).hexdigest(),
            "actual_review_minutes": review.get("actual_review_minutes"),
            "metrics": [next(p for p in m["pages"] if p["page"] == page["page_number"]) for m in metrics]}


def qualification_blockers(documents, has_sample, scope=None, comparison_kind="fresh"):
    excluded, versioned = set(), False
    if scope is not None:
        if (scope.get("schema_version") != "ocr-quality-scope/1" or scope.get("decision") != "accepted"
                or scope.get("reviewer") != "product-owner"
                or datetime.fromisoformat(scope["recorded_at"]).utcoffset() is None):
            raise ValueError("invalid owner OCR quality scope")
        pages = {d["source_sha256"]: d["accounting"][0]["pages"] for d in documents}
        for item in scope.get("excluded_table_pages", []):
            digest, page = item["source_asset_sha256"], item["physical_page"]
            if digest not in pages or type(page) is not int or not 1 <= page <= pages[digest]:
                raise ValueError("OCR quality exclusion is outside the retained source")
            excluded.add((digest, page))
        policy = scope.get("fresh_inference_policy", "identical")
        if policy not in {"identical", "versioned"}:
            raise ValueError("unknown fresh inference policy")
        versioned = policy == "versioned"
    blockers = []
    if not has_sample:
        blockers.append("human_reviewed_transcription_missing")
    if any(not d["runtime_verified"] for d in documents):
        blockers.append("runtime_provenance_missing")
    if any(not d["same_runtime"] or not d["same_settings"] for d in documents):
        blockers.append("runtime_or_model_configuration_changed")
    if any(c["matches"] != c["total"] and (d["source_sha256"], 75) not in excluded
           for d in documents for c in d.get("conditional_signs_page_75", [])):
        blockers.append("critical_ocr_errors_require_review")
    if any("picture_ocr_incomplete_response" in u for d in documents for u in d["uncertainties"]):
        blockers.append("unresolved_picture_ocr")
    if any(not d["identical"] for d in documents):
        if comparison_kind == "saved_replay":
            blockers.append("saved_extraction_replay_drift")
        elif not versioned:
            blockers.append("fresh_ocr_output_drift")
    return blockers


def verify(input_path, first_dir, second_dir, lab, output, transcription_review=None,
           acceptance_scope=None, comparison_kind="fresh"):
    declared = read(input_path)
    manifest, _, _ = load_input(input_path, declared["target_dates"][0])
    indexes = [next(directory.glob("extractions/index-*.json")) for directory in (first_dir, second_dir)]
    extracted = [load_extractions(index, manifest) for index in indexes]
    reference = read(lab / "benchmark/reference/sample_org_v1.json")
    controls = read(lab / "results/comparison/sample_org/controls.json")
    documents, aggregates, sample = [], [Counter(), Counter()], None
    for digest in extracted[0]:
        a, b = extracted[0][digest], extracted[1][digest]
        audits, evidence_dirs = [], []
        for index_path, extraction in zip(indexes, (a, b)):
            index = read(index_path)
            evidence = index_path.parent.parent / "ocr-evidence" / index["extractions"][digest]["native_evidence_id"]
            evidence_dirs.append(evidence)
            audits.append(account(extraction, read(evidence / "document.json")))
        changes = page_changes(a["pages"], b["pages"])
        entry = {"source_sha256": digest, "first_id": a["extraction_id"], "second_id": b["extraction_id"],
                 "identical": a == b, "same_runtime": a["runtime_fingerprint"] == b["runtime_fingerprint"],
                 "runtime_verified": bool(a["runtime_fingerprint"] and b["runtime_fingerprint"]),
                 "same_settings": all(a[key] == b[key] for key in ("extractor_version", "models", "config")),
                 "accounting": audits, "changed_pages": changes,
                 "uncertainties": [a["uncertainties"], b["uncertainties"]]}
        if digest == reference["source"]["sha256"]:
            assert controls["source_sha256"] == digest
            entry["reference_metrics"] = [reference_metrics(e, reference, lab) for e in (a, b)]
            entry["conditional_signs_page_75"] = [conditional_signs(e, controls) for e in (a, b)]
            if transcription_review:
                sample = reviewed_sample(transcription_review, reference, evidence_dirs, entry["reference_metrics"])
        documents.append(entry)
        for aggregate, audit in zip(aggregates, audits):
            aggregate.update({key: value for key, value in audit.items() if key != "all_regions_and_text_spans"})
    scope = read(acceptance_scope) if acceptance_scope is not None else None
    blockers = qualification_blockers(documents, sample is not None, scope, comparison_kind)
    result = {"schema_version": "pdf-ocr-qualification/1", "status": "engineering_evidence_with_open_acceptance",
              "input_hash": manifest["manifest_hash"], "documents": documents,
              "totals_by_pass": [dict(a) for a in aggregates], "blockers": blockers,
              "all_regions_and_text_spans": all(a["all_regions_and_text_spans"] for d in documents for a in d["accounting"]),
              "human_reviewed_sample": sample,
              "legal_admission": "not_requested"}
    if scope is not None:
        result.update(owner_scope=scope, owner_scope_sha256=sha256(acceptance_scope.read_bytes()).hexdigest(),
                      comparison_kind=comparison_kind)
        if not blockers:
            result["status"] = "pass_with_owner_exceptions"
    result["report_id"] = content_hash(result)
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_bytes(json_bytes(result))
    print(json.dumps({"report": str(output / "report.json"), "documents": len(documents), "blockers": blockers}))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--lab-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--transcription-review", type=Path)
    parser.add_argument("--acceptance-scope", type=Path)
    parser.add_argument("--comparison-kind", choices=("fresh", "saved_replay"), default="fresh")
    args = parser.parse_args()
    verify(args.input, args.first, args.second, args.lab_root, args.output_dir, args.transcription_review,
           args.acceptance_scope, args.comparison_kind)
