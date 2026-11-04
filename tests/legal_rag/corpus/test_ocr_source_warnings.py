"""Source-number warnings allow only the alternatives independently inventoried."""

import pytest

from test_ocr_source_controls import checker, source_case
from test_ocr_structure import ISSUER, extraction
from legal_rag.corpus.ocr_owner_ast import _entry, _source


def warning_case(alternative_scope=False, alternative_parent=False, delayed_footnote=False):
    body = ["1. Утвердить правила.",
        f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812",
        ("Title", "Правила учебного контроля"), ("Section-header", "III. Требования"),
        "3.15. Первое правило¹." if delayed_footnote else "3.15. Первое правило.",
        "3.15. Другое правило.", "3.16.1. Правило без родителя.",
        "4. Требования к перевозке:", "4.1. Правило перевозки.", "Продолжение правила."]
    if delayed_footnote:
        body.append(("Footnote", "¹ Источник только первого правила."))
    source = extraction(body)
    rows = [{"key": f"1.{i}", "page": 1, "region_id": r["region_id"], "category": r["category"]}
            for i, r in enumerate(source["pages"][0]["regions"])]
    packet = {"source_asset_sha256": source["source_asset_sha256"], "extraction_id": source["extraction_id"],
              "assigned_pages": [1], "regions": rows, "pages": [{"page": 1, "sha256": "1" * 64}]}
    units = [("A", None, "act", None, None), ("A/1", "A", "point", "1", "1.4"),
             ("S", "A", "attached_document", None, "1.5"), ("S/III", "S", "section", "III", "1.7"),
             ("S/III/3.15", "S/III", "point", "3.15", "1.8"),
             ("S/III/3.15", "S/III", "point", "3.15", "1.9"),
             ("S/III/3.16.1", "S/III", "point", "3.16.1", "1.10"),
             ("S/III/4", "S/III", "point", "4", "1.11"),
             ("S/III/4/4.1", "S/III/4", "point", "4.1", "1.12")]
    owners = ["A", None, "A", "A", "A/1", "S", "S", "S/III", "S/III/3.15", "S/III/3.15",
              "S/III/3.16.1", "S/III/4", "S/III/4/4.1", "S/III/4/4.1"]
    if delayed_footnote:
        owners.append("S/III/3.15")
    candidates = {9: ["S/III/3.15"], 10: ["S/III/3.16.1", "S/III/3.15/3.16.1"],
                  11: ["S/III/4", "S/4"], 12: ["S/III/4/4.1", "S/4/4.1"], 13: ["S/III/4/4.1", "S/4/4.1"]}
    controls = {"schema_version": "m1-04a-independent-source-controls/1", **{k: packet[k] for k in
                ("source_asset_sha256", "extraction_id", "assigned_pages")},
        "independence": {"candidate_outputs_used": False, "previous_gold_used": False},
        "image_reviews": [{"page": 1, "image_sha256": "1" * 64, "observed_structure": "Authored printed-number errors"}],
        "regions": [{"key": row["key"], "status": "ambiguous" if i in candidates else "picture" if owner is None else "evaluated",
                     "owner": None if i in candidates else owner, "continuation": False,
                     **({"candidates": candidates[i], "reason": "Authored source ambiguity"} if i in candidates else {})}
                    for i, (row, owner) in enumerate(zip(rows, owners, strict=True))],
        "units": [{"owner_path": path, "parent_owner_path": parent, "kind": kind, "printed_number": number,
                   "start_key": start, "evidence_keys": [start] if start else []} for path, parent, kind, number, start in units],
        "uncertainties": [
            {"type": "duplicate_printed_number", "keys": ["1.8", "1.9"], "unit_start_keys": ["1.8", "1.9"], "owner_path": "S/III/3.15"},
            {"type": "parent_link_conflict", "keys": ["1.10"], "candidates": candidates[10]},
            {"type": "scope_boundary", "keys": ["1.11", "1.12", "1.13"], "candidates": candidates[11]}]}
    for index, occurrence in ((4, 1), (5, 2)):
        controls["units"][index]["occurrence_index"] = occurrence
    controls["units"][6]["candidate_parent_owner_paths"] = ["S/III", "S/III/3.15"]
    controls["regions"][10]["owner_unit_start_key"] = "1.9"
    for index in (7, 8):
        controls["units"][index]["candidate_owner_paths"] = candidates[index + 4]
    actual_paths = list(owners)
    actual_paths[9] = "S/III/3.15@2"
    if alternative_parent:
        actual_paths[10] = "S/III/3.15@2/3.16.1"
    if alternative_scope:
        actual_paths[11:14] = ["S/4", "S/4/4.1", "S/4/4.1"]
    tokens, regions, token_ids = _source(source)
    nodes = []
    for path, parent, kind, number, start in units:
        if start:
            path = actual_paths[int(start.split(".")[1])]
        if path == "S/III/3.15@2/3.16.1":
            parent = "S/III/3.15@2"
        elif path.startswith("S/4"):
            parent = path.rsplit("/", 1)[0]
        ids = [rows[int(start.split(".")[1])]["region_id"]] if start else []
        nodes.append({"address": "act/owner/" + path, "owner_path": path,
            "parent_address": "act/owner/" + parent if parent else "act", "kind": "approved_text" if kind == "attached_document" else kind,
            "number_canonical": number, "number_display": number,
            "number_components": {"base": number, "superscript": None} if number else None, "number_is_explicit": number is not None,
            "anchor_region_ids": ids, "anchor_source_spans": [tokens[t]["source_span"] for rid in ids for t in token_ids[rid]],
            "text_node_ids": [], "original_text": "", "text": "", "source_spans": []})
    excluded, bindings = [], []
    for row, owner in zip(rows, actual_paths, strict=True):
        entry = {**_entry([row["region_id"]], tokens, regions, token_ids), "address": "act/content/" + row["key"],
                 "owner_path": owner, "parent_address": "act/owner/" + owner if owner else "act", "kind": "image" if owner is None else "paragraph"}
        # This authored historical /2 fixture deliberately retains whole tokens.
        entry.pop("text_slices")
        for fragment in entry["fragments"]:
            for key in ("start", "end", "offset_basis"):
                fragment.pop(key)
        (nodes if owner else excluded).append(entry)
        bindings.append({**row, "index": int(row["key"].split(".")[1]), "address": entry["address"],
                         "owner_path": owner, "disposition": "parsed" if owner else "excluded", "continuation": False})
    for node in nodes:
        node["children"] = [n["address"] for n in nodes if n["parent_address"] == node["address"]]
    tree = {"schema_version": "legal-ast/2", "namespace": "act", "source_asset_sha256": source["source_asset_sha256"],
        "extraction_id": source["extraction_id"], "document_tree": source["document_tree"], "nodes": nodes,
        "excluded_blocks": excluded, "unresolved_blocks": [], "unresolved_regions": [], "region_bindings": bindings,
        "structural_issues": ["pdf_structure_unqualified"], "identity_decision": {"status": "claim_matches_header"},
        "accounting": {"total_text_nodes": len(tokens), "exactly_once": True}, "source_warnings": []}
    for label, group in (("parsed", nodes), ("unresolved", []), ("excluded", excluded)):
        tree["accounting"].update({label + "_text_nodes": sum(len(n["text_node_ids"]) for n in group),
                                   label + "_source_chars": sum(len(n["original_text"]) for n in group)})
    for code, indices in (("duplicate_printed_number", [8, 9]), ("missing_parent_number", [10]), ("scope_boundary", [11, 12, 13])):
        tree["source_warnings"].append({"code": code, "region_ids": [rows[i]["region_id"] for i in indices],
            "owner_paths": list(dict.fromkeys(actual_paths[i] for i in indices)), "message": "Printed source inconsistency retained"})
    return source, tree, packet, controls


def move_delayed_footnote(tree, owner):
    binding = tree["region_bindings"][-1]
    binding["owner_path"] = owner
    leaf = next(node for node in tree["nodes"] if node["address"] == binding["address"])
    leaf.update(owner_path=owner, parent_address="act/owner/" + owner, layout_kind="paragraph")
    for node in tree["nodes"]:
        node["children"] = [n["address"] for n in tree["nodes"] if n["parent_address"] == node["address"]]


def test_delayed_footnote_uses_independently_anchored_occurrence_not_the_last_printed_number():
    source, tree, packet, controls = warning_case(delayed_footnote=True)
    controls["regions"][-1]["owner_unit_start_key"] = "1.8"
    report = checker().validate_controls(source, tree, packet, controls, allow_source_warnings=True)
    assert report["canonical_regions_passed"] == 14
    move_delayed_footnote(tree, "S/III/3.15@2")
    with pytest.raises(ValueError, match="ownership"):
        checker().validate_controls(source, tree, packet, controls, allow_source_warnings=True)


@pytest.mark.parametrize("owner", ["S/III/3.15", "S/III/3.15@2"])
def test_delayed_footnote_without_independent_occurrence_anchor_cannot_accept_either_owner(owner):
    source, tree, packet, controls = warning_case(delayed_footnote=True)
    move_delayed_footnote(tree, owner)
    with pytest.raises(ValueError):
        checker().validate_controls(source, tree, packet, controls, allow_source_warnings=True)


def test_occurrence_anchor_evidence_cannot_include_another_printed_occurrence_start():
    source, tree, packet, controls = warning_case()
    unit = next(n for n in tree["nodes"] if n["owner_path"] == "S/III/3.15@2" and not n.get("source_region_ids"))
    unit["anchor_region_ids"].append(packet["regions"][8]["region_id"])
    tokens, _, token_ids = _source(source)
    unit["anchor_source_spans"] = [tokens[t]["source_span"] for rid in unit["anchor_region_ids"] for t in token_ids[rid]]
    with pytest.raises(ValueError, match="unit_errors"):
        checker().validate_controls(source, tree, packet, controls, allow_source_warnings=True)


@pytest.mark.parametrize("alternative_scope,alternative_parent", [(False, False), (True, True)])
def test_explicit_source_warning_policy_preserves_complete_occurrences_and_original_alternatives(alternative_scope, alternative_parent):
    case = warning_case(alternative_scope, alternative_parent)
    report = checker().validate_controls(*case, allow_source_warnings=True)
    assert report["expected_units"] == 9
    assert report["canonical_regions_passed"] == 13
    assert len(report["source_warnings"]) == 3
    assert not any(report[k] for k in ("region_errors", "unit_errors", "extra_units", "duplicate_units", "continuation_errors"))
    assert report["unit_order_matches"]


def test_source_warning_policy_remains_strict_by_default():
    with pytest.raises(ValueError):
        checker().validate_controls(*warning_case())
    source, tree, packet, controls = source_case()
    tree["source_warnings"] = [{"code": "scope_boundary", "region_ids": [packet["regions"][0]["region_id"]],
                                "owner_paths": ["A"], "message": "Suspicious source scope"}]
    with pytest.raises(ValueError, match="warning"):
        checker().validate_controls(source, tree, packet, controls)


@pytest.mark.parametrize("damage", ["missing_occurrence", "same_start", "wrong_occurrence", "missing_duplicate_uncertainty"])
def test_duplicate_control_paths_need_explicit_source_occurrence_inventory(damage):
    _, _, packet, controls = warning_case()
    if damage == "missing_occurrence":
        controls["units"][5].pop("occurrence_index")
    elif damage == "same_start":
        controls["units"][5]["start_key"] = "1.8"
    elif damage == "wrong_occurrence":
        controls["units"][5]["occurrence_index"] = 3
    else:
        controls["uncertainties"].pop(0)
    with pytest.raises(ValueError):
        checker().verify_annotation(packet, controls, allow_source_warnings=True)


@pytest.mark.parametrize("damage", ["missing_warning", "partial_duplicate_warning", "partial_scope_warning", "foreign_region",
    "wrong_code", "unrelated_uncertainty", "missing_uncertainty", "empty_message", "wrong_warning_owner",
    "ambiguous_continuation", "wrong_region_owner", "wrong_occurrence_region", "unlicensed_suffix", "number", "kind", "parent", "order", "dropped_occurrence", "accounting", "critical"])
def test_source_warnings_never_hide_unrelated_ambiguity_or_structure_damage(damage):
    source, tree, packet, controls = warning_case()
    unit = next(n for n in tree["nodes"] if n["owner_path"] == "S/III/3.15@2" and not n.get("source_region_ids"))
    if damage == "missing_warning":
        tree["source_warnings"].pop()
    elif damage == "partial_duplicate_warning":
        tree["source_warnings"][0]["region_ids"].pop()
    elif damage == "partial_scope_warning":
        tree["source_warnings"][2]["region_ids"].pop()
    elif damage == "foreign_region":
        tree["source_warnings"][0]["region_ids"][0] = "invented"
    elif damage == "wrong_code":
        tree["source_warnings"][0]["code"] = "other"
    elif damage == "unrelated_uncertainty":
        controls["uncertainties"].append({"type": "unknown", "keys": ["1.0"]})
    elif damage == "missing_uncertainty":
        controls["uncertainties"].pop()
    elif damage == "empty_message":
        tree["source_warnings"][0]["message"] = ""
    elif damage == "wrong_warning_owner":
        tree["source_warnings"][0]["owner_paths"] = ["A/1"]
    elif damage == "ambiguous_continuation":
        tree["region_bindings"][9]["continuation"] = True
    elif damage == "wrong_region_owner":
        controls["regions"][9]["candidates"] = ["A/1"]
    elif damage == "wrong_occurrence_region":
        binding = tree["region_bindings"][9]
        binding["owner_path"] = "S/III/3.15"
        leaf = next(n for n in tree["nodes"] if n["address"] == binding["address"])
        leaf.update(owner_path="S/III/3.15", parent_address="act/owner/S/III/3.15")
        for node in tree["nodes"]:
            node["children"] = [n["address"] for n in tree["nodes"] if n["parent_address"] == node["address"]]
        tree["source_warnings"][0]["owner_paths"] = ["S/III/3.15"]
    elif damage == "unlicensed_suffix":
        def rename(value):
            if isinstance(value, str):
                return value.replace("S/III/3.15@2", "S/III/3.15@7")
            if isinstance(value, list):
                return [rename(item) for item in value]
            if isinstance(value, dict):
                return {key: rename(item) for key, item in value.items()}
            return value
        tree = rename(tree)
    elif damage == "number":
        unit["number_display"] = "3.16"
    elif damage == "kind":
        unit["kind"] = "section"
    elif damage == "parent":
        unit["parent_address"] = "act/owner/S"
        for node in tree["nodes"]:
            node["children"] = [n["address"] for n in tree["nodes"] if n["parent_address"] == node["address"]]
    elif damage == "order":
        first = next(n for n in tree["nodes"] if n["owner_path"] == "S/III/3.15" and not n.get("source_region_ids"))
        a, b = tree["nodes"].index(first), tree["nodes"].index(unit)
        tree["nodes"][a], tree["nodes"][b] = tree["nodes"][b], tree["nodes"][a]
        for node in tree["nodes"]:
            node["children"] = [n["address"] for n in tree["nodes"] if n["parent_address"] == node["address"]]
    elif damage == "dropped_occurrence":
        tree["nodes"].remove(unit)
    elif damage == "accounting":
        tree["accounting"]["exactly_once"] = False
    else:
        tree["structural_issues"].append("critical_parser_failure")
    with pytest.raises(ValueError):
        checker().validate_controls(source, tree, packet, controls, allow_source_warnings=True)
