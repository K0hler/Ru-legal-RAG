"""Compare complete source/image annotations with OCR trees; keep proposals separate from parsed nodes."""

from collections import Counter
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_ocr_owner_gold import (  # noqa: E402
    attached_count, attached_ordinal_heads, canonical, number_single_annex,
    ordinal_single_annex_documents, rename_head, single_annex_documents,
)
from validate_ocr_structure import require, unique, validate_source  # noqa: E402


def verify_annotation(packet, controls):
    require(controls["schema_version"] == "m1-04a-independent-source-controls/1", "wrong annotation schema")
    require(all(controls[k] == packet[k] for k in ("source_asset_sha256", "extraction_id", "assigned_pages")),
            "annotation source/pages mismatch")
    require(controls["independence"]["candidate_outputs_used"] is False
            and controls["independence"]["previous_gold_used"] is False, "annotation is not independent")
    rows = [r for r in packet["regions"] if r["page"] in packet["assigned_pages"]]
    source = unique(rows, "key", "source key")
    actual = unique(controls["regions"], "key", "annotation key")
    require(list(source) == list(actual), "incomplete/unordered annotation coverage")
    for key, row in actual.items():
        status = row["status"]
        require(status in {"evaluated", "picture", "noise", "ambiguous"}, "unknown annotation status")
        require(isinstance(row["continuation"], bool), "continuation must be boolean")
        require((source[key]["category"] == "Picture") == (status == "picture"), "incorrect picture exclusion")
        if status == "evaluated":
            require(isinstance(row["owner"], str) and bool(row["owner"]), "missing expected owner")
        else:
            require(row["owner"] is None, "unscored/ambiguous owner must be explicit null")
        if status == "noise":
            require(source[key]["category"] in {"Page-header", "Page-footer"} and bool(row.get("reason")), "unsupported noise exclusion")
        if status == "ambiguous":
            require(bool(row.get("reason")) and bool(row.get("candidates")) and bool(controls["uncertainties"]), "unexplained ambiguity")
    images = unique(controls["image_reviews"], "page", "image review")
    inventory = unique(packet["pages"], "page", "source image inventory")
    require(set(packet["assigned_pages"]) <= set(inventory), "incomplete source image inventory")
    require(all(re.fullmatch(r"[a-f0-9]{64}", p["sha256"]) for p in inventory.values()), "invalid source image hash")
    expected_images = {page: inventory[page]["sha256"] for page in packet["assigned_pages"]}
    require(set(images) == set(expected_images), "incomplete image review coverage")
    require(all(r["image_sha256"] == expected_images[p] and bool(r["observed_structure"].strip()) for p, r in images.items()),
            "image review hash or observation missing")
    unique(controls["units"], "owner_path", "expected unit")
    for unit in controls["units"]:
        start = unit["start_key"]
        require(start in source or start is None and unit["owner_path"] == "A" and 1 in packet["assigned_pages"], "unit start outside assigned source")
        require(all(k in source for k in unit["evidence_keys"]), "unit evidence outside assigned source")
        require(unit["printed_number"] is None or isinstance(unit["printed_number"], str) and bool(unit["printed_number"]), "invalid printed number")


def number_fields(printed):
    """Mechanical source-number encoding; no marker or owner inference."""
    if printed is None:
        return {"number_canonical": None, "number_display": None, "number_components": None, "number_is_explicit": False}
    raised = re.search(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+$", printed)
    base, superscript = printed, None
    if raised:
        base = printed[:raised.start()]
        superscript = raised[0].translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-"))
    return {"number_canonical": base + "." + superscript if superscript is not None else base,
            "number_display": printed, "number_components": {"base": base, "superscript": superscript}, "number_is_explicit": True}


def compare_controls(extraction, tree, packet, controls):
    require(all(packet[k] == extraction[k] for k in ("source_asset_sha256", "extraction_id")), "packet binds another extraction")
    physical = [(f"{p['page']}.{i}", p["page"], r["region_id"], r["category"])
                for p in extraction["pages"] for i, r in enumerate(p["regions"])]
    require([(r["key"], r["page"], r["region_id"], r["category"]) for r in packet["regions"]] == physical
            and packet["assigned_pages"] == [p["page"] for p in extraction["pages"]], "packet must cover the full actual extraction")
    verify_annotation(packet, controls)
    validate_source(extraction, tree)
    gold = {r["key"]: {"owners": [r["owner"]]} for r in controls["regions"] if r["status"] == "evaluated"}
    bindings = {f"{b['page']}.{b['index']}": b for b in tree["region_bindings"]}
    unit_gold = {**gold, **{"unit:" + u["owner_path"]: {"owners": [u["owner_path"]]} for u in controls["units"]}}
    attached, single = attached_count(unit_gold), single_annex_documents(unit_gold)
    heads = attached_ordinal_heads(gold, {key: value["owner_path"] for key, value in bindings.items()}, attached, single)
    renamed_single = ordinal_single_annex_documents(unit_gold, heads[0], attached, single)

    def normal(path, which):
        result = rename_head(canonical(path, attached, single), heads[which])
        return number_single_annex(result, renamed_single) if result is not None else None

    def expected_norm(path):
        return normal(path, 0)

    def actual_norm(path):
        return normal(path, 1)
    region_errors, continuation_errors = [], []
    proposals_passed = canonical_passed = 0
    for expected in controls["regions"]:
        if expected["status"] != "evaluated":
            continue
        binding = bindings[expected["key"]]
        proposal = actual_norm(binding["owner_path"]) == expected_norm(expected["owner"])
        parsed = proposal and binding["disposition"] == "parsed"
        proposals_passed += proposal
        canonical_passed += parsed
        if not parsed:
            region_errors.append({"key": expected["key"], "expected_owner": expected["owner"],
                                  "actual_owner": binding["owner_path"], "disposition": binding["disposition"], "proposal_matches": proposal})
        if binding["continuation"] != expected["continuation"]:
            continuation_errors.append({"key": expected["key"], "expected": expected["continuation"], "actual": binding["continuation"]})
    nodes = {n["address"]: n for n in tree["nodes"]}
    containers = [n for n in tree["nodes"] if not n.get("source_region_ids")]
    by_owner = {}
    duplicate_units = []
    for unit in containers:
        path = actual_norm(unit["owner_path"])
        if path in by_owner:
            duplicate_units.append(path)
        by_owner[path] = unit
    source_regions = {r["key"]: r["region_id"] for r in packet["regions"]}
    unit_errors = []
    for expected in controls["units"]:
        unit = by_owner.get(expected_norm(expected["owner_path"]))
        failures = []
        if unit is None:
            failures.append("missing")
        else:
            parent = unit["parent_address"]
            actual_parent = (None if expected["owner_path"] == "A" else "A") if parent == tree["namespace"] else nodes[parent]["owner_path"]
            if actual_norm(actual_parent) != expected_norm(expected["parent_owner_path"]):
                failures.append("parent")
            kinds = {"annex", "approved_text"} if expected["kind"] == "attached_document" else {expected["kind"]}
            if unit["kind"] not in kinds:
                failures.append("kind")
            if any(unit[k] != value for k, value in number_fields(expected["printed_number"]).items()):
                failures.append("number")
            if expected["start_key"] is not None:
                start = expected["start_key"]
                anchored = source_regions[start] in unit["anchor_region_ids"]
                if expected["kind"] == "act":
                    # The abstract act root has no printed marker; its header is retained as act-owned content.
                    binding = bindings[start]
                    anchored = anchored or (binding["disposition"] == "parsed"
                        and actual_norm(binding["owner_path"]) == expected_norm(expected["owner_path"])
                        and nodes[binding["address"]]["parent_address"] == unit["address"])
                if not anchored:
                    failures.append("anchor")
        if failures:
            unit_errors.append({"owner_path": expected["owner_path"], "start_key": expected["start_key"],
                                "printed_number": expected["printed_number"], "failures": failures,
                                "actual": {k: unit[k] for k in ("owner_path", "kind", "number_canonical", "number_display", "number_components")} if unit else None})
    expected_paths = {expected_norm(u["owner_path"]) for u in controls["units"]}
    extra_units = sorted(set(by_owner) - expected_paths)
    status_counts = Counter(r["status"] for r in controls["regions"])
    return {"regions": {k: status_counts[k] for k in ("evaluated", "picture", "noise", "ambiguous")},
            "owner_proposals_passed": proposals_passed, "canonical_regions_passed": canonical_passed,
            "region_errors": region_errors, "continuation_errors": continuation_errors, "expected_units": len(expected_paths),
            "unit_errors": unit_errors, "extra_units": extra_units, "duplicate_units": duplicate_units,
            "unit_order_matches": [actual_norm(u["owner_path"]) for u in containers] == [expected_norm(u["owner_path"]) for u in controls["units"]],
            "structural_issues": tree["structural_issues"], "identity": tree["identity_decision"]["status"]}
