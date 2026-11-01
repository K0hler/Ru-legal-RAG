"""Full source annotations retain independent expectations and explicit unscored regions."""
import copy
import importlib.util
from pathlib import Path

import pytest

from test_ocr_structure_controls import authored_case


def checker():
    path = Path(__file__).resolve().parents[3] / "docs/assets/check_m1_04a_source_controls.py"
    assert path.exists(), "source annotation checker missing"
    spec = importlib.util.spec_from_file_location("source_control_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_case():
    extraction, tree, old = authored_case()
    expected = {r["region_id"]: r for r in old["regions"]}
    rows = [{"key": f"{p['page']}.{i}", "page": p["page"], "region_id": r["region_id"],
             "category": r["category"]} for p in extraction["pages"] for i, r in enumerate(p["regions"])]
    packet = {"source_asset_sha256": extraction["source_asset_sha256"], "extraction_id": extraction["extraction_id"],
              "assigned_pages": [1, 2], "regions": rows,
              "pages": [{"page": i, "sha256": str(i) * 64} for i in (1, 2)]}
    key_by_id = {r["region_id"]: r["key"] for r in rows}
    controls = {"schema_version": "m1-04a-independent-source-controls/1",
                "source_asset_sha256": packet["source_asset_sha256"], "extraction_id": packet["extraction_id"],
                "assigned_pages": [1, 2], "regions": [], "units": [], "uncertainties": [],
                "image_reviews": [{"page": i, "image_sha256": str(i) * 64, "observed_structure": "authored image review fixture"} for i in (1, 2)],
                "independence": {"candidate_outputs_used": False, "previous_gold_used": False}}
    for row in rows:
        e = expected[row["region_id"]]
        status = "picture" if row["category"] == "Picture" else "noise" if e["owner_path"] is None else "evaluated"
        controls["regions"].append({"key": row["key"], "status": status,
                                    "owner": e["owner_path"] if status == "evaluated" else None,
                                    "continuation": e["continuation"], "reason": "page number" if status == "noise" else ""})
    for unit in old["units"]:
        controls["units"].append({"owner_path": unit["owner_path"],
            "parent_owner_path": "A" if unit["owner_path"] == "S" else unit["parent_owner_path"],
            "kind": "attached_document" if unit["kind"] == "approved_text" else unit["kind"],
            "printed_number": "1" if unit["owner_path"] == "S/AN1" else unit["number_display"],
            "start_key": key_by_id[unit["anchor_region_ids"][0]] if unit["anchor_region_ids"] else None,
            "evidence_keys": [key_by_id[r] for r in unit["anchor_region_ids"]]})
    return extraction, tree, packet, controls


def test_full_source_coverage_and_explicit_picture_exclusion():
    source, tree, packet, controls = source_case()
    checker().verify_annotation(packet, controls)
    report = checker().compare_controls(source, tree, packet, controls)
    assert report["regions"] == {"evaluated": 15, "picture": 2, "noise": 1, "ambiguous": 0}
    assert report["owner_proposals_passed"] == report["canonical_regions_passed"] == 15
    assert not report["unit_errors"]


def test_numbered_annex_cannot_lose_its_printed_metadata():
    source, tree, packet, controls = source_case()
    annex = next(n for n in tree["nodes"] if n["owner_path"] == "S/AN1" and not n.get("source_region_ids"))
    annex.update(number_canonical=None, number_display=None, number_components=None, number_is_explicit=False)
    report = checker().compare_controls(source, tree, packet, controls)
    assert [r["owner_path"] for r in report["unit_errors"]] == ["S/AN1"]
    assert report["unit_errors"][0]["failures"] == ["number"]


@pytest.mark.parametrize("damage", ["missing_region", "duplicate_region", "missing_image", "image_hash", "not_independent",
                                    "hidden_text", "missing_owner", "outside_unit", "ambiguous_without_reason"])
def test_incomplete_or_invalid_source_annotation_is_rejected(damage):
    _, _, packet, controls = source_case()
    if damage == "missing_region":
        controls["regions"].pop()
    elif damage == "duplicate_region":
        controls["regions"].append(copy.deepcopy(controls["regions"][0]))
    elif damage == "missing_image":
        controls["image_reviews"].pop()
    elif damage == "image_hash":
        controls["image_reviews"][0]["image_sha256"] = "wrong"
    elif damage == "not_independent":
        controls["independence"]["candidate_outputs_used"] = True
    elif damage == "hidden_text":
        controls["regions"][0].update(status="picture", owner=None)
    elif damage == "missing_owner":
        controls["regions"][0]["owner"] = None
    elif damage == "outside_unit":
        controls["units"][1]["start_key"] = "3.1"
    else:
        controls["regions"][0].update(status="ambiguous", owner=None)
    with pytest.raises(ValueError):
        checker().verify_annotation(packet, controls)


def test_wrong_number_parent_and_missing_units_are_reported():
    source, tree, packet, controls = source_case()
    unit = next(n for n in tree["nodes"] if n.get("owner_path") == "S/I/1" and not n.get("source_region_ids"))
    unit["number_display"] = "99"
    # Rebuild a consistent but legally wrong hierarchy to avoid merely testing graph consistency.
    unit["parent_address"] = "act/owner/A"
    for n in tree["nodes"]:
        n["children"] = [c["address"] for c in tree["nodes"] if c["parent_address"] == n["address"]]
    report = checker().compare_controls(source, tree, packet, controls)
    error = next(e for e in report["unit_errors"] if e["owner_path"] == "S/I/1")
    assert set(error["failures"]) == {"number", "parent"}


def test_unconfirmed_canonical_content_never_passes_from_matching_proposals():
    from legal_rag.corpus.ocr_owner_ast import build_owner_tree
    source, _, packet, controls = source_case()
    tree = build_owner_tree(source, "a different act", "original")
    report = checker().compare_controls(source, tree, packet, controls)
    assert report["owner_proposals_passed"] == 15
    assert report["canonical_regions_passed"] == 0
    assert len(report["unit_errors"]) == len(controls["units"])


def test_legal_unit_order_is_checked_separately_from_physical_content_order():
    source, tree, packet, controls = source_case()
    attached = next(n for n in tree["nodes"] if n["owner_path"] == "S" and not n.get("source_region_ids"))
    point = next(n for n in tree["nodes"] if n["owner_path"] == "A/1" and not n.get("source_region_ids"))
    tree["nodes"].remove(attached)
    tree["nodes"].insert(tree["nodes"].index(point), attached)
    report = checker().compare_controls(source, tree, packet, controls)
    assert not report["unit_order_matches"]


def test_a_numbered_unit_cannot_claim_its_number_is_not_explicit():
    source, tree, packet, controls = source_case()
    point = next(n for n in tree["nodes"] if n["owner_path"] == "A/1" and not n.get("source_region_ids"))
    point["number_is_explicit"] = False
    report = checker().compare_controls(source, tree, packet, controls)
    assert any(e["owner_path"] == "A/1" and "number" in e["failures"] for e in report["unit_errors"])


def test_raised_number_is_encoded_without_losing_its_printed_form():
    assert checker().number_fields("2¹") == {"number_canonical": "2.1", "number_display": "2¹",
        "number_components": {"base": "2", "superscript": "1"}, "number_is_explicit": True}


@pytest.mark.parametrize("damage", ["foreign_identity", "missing_packet_region", "wrong_packet_region", "wrong_packet_category"])
def test_packet_itself_is_bound_to_the_full_actual_extraction(damage):
    source, tree, packet, controls = source_case()
    if damage == "foreign_identity":
        for value in (packet, controls):
            value.update(source_asset_sha256="wrong", extraction_id="wrong")
    elif damage == "missing_packet_region":
        packet["regions"].pop(0)
        controls["regions"].pop(0)
    elif damage == "wrong_packet_region":
        packet["regions"][0]["region_id"] = "wrong"
    else:
        packet["regions"][0]["category"] = "Picture"
        controls["regions"][0].update(status="picture", owner=None)
    with pytest.raises(ValueError, match="packet"):
        checker().compare_controls(source, tree, packet, controls)


def test_container_anchor_spans_must_match_their_physical_regions():
    source, tree, packet, controls = source_case()
    point = next(n for n in tree["nodes"] if n["owner_path"] == "A/1" and not n.get("source_region_ids"))
    point["anchor_source_spans"] = []
    with pytest.raises(ValueError, match="anchor"):
        checker().compare_controls(source, tree, packet, controls)


def test_act_header_evidence_may_live_in_act_owned_content():
    source, tree, packet, controls = source_case()
    controls["units"][0].update(start_key="1.0", evidence_keys=["1.0"])
    report = checker().compare_controls(source, tree, packet, controls)
    assert not any(e["owner_path"] == "A" for e in report["unit_errors"])


def test_point_content_cannot_substitute_for_act_header_evidence():
    source, tree, packet, controls = source_case()
    controls["units"][0].update(start_key="1.4", evidence_keys=["1.4"])
    report = checker().compare_controls(source, tree, packet, controls)
    assert any(e["owner_path"] == "A" and "anchor" in e["failures"] for e in report["unit_errors"])


@pytest.mark.parametrize("damage", ["missing_page", "duplicate_page", "invalid_image_hash"])
def test_image_inventory_cannot_hide_an_unreviewed_page(damage):
    source, tree, packet, controls = source_case()
    if damage == "missing_page":
        packet["pages"].pop()
        controls["image_reviews"].pop()
    elif damage == "duplicate_page":
        packet["pages"].append(copy.deepcopy(packet["pages"][0]))
    else:
        packet["pages"][0]["sha256"] = "not a hash"
        controls["image_reviews"][0]["image_sha256"] = "not a hash"
    with pytest.raises(ValueError, match="image"):
        checker().compare_controls(source, tree, packet, controls)


def test_second_attached_document_uses_the_approved_appearance_equivalence():
    from test_ocr_structure import CLAIM, ISSUER, extraction
    from legal_rag.corpus.ocr_owner_ast import build_owner_tree
    source = extraction(["1. Утвердить прилагаемые правила.",
        f"УТВЕРЖДЕНЫ\nпостановлением {ISSUER}\nот 9 июня 2020 г. № 812",
        ("Title", "Правила учебного контроля"), "1. Первое правило.",
        f"Приложение № 1\nк постановлению {ISSUER}\nот 9 июня 2020 г. № 812",
        ("Title", "Дополнительные показатели"), "1. Первый показатель."])
    tree = build_owner_tree(source, CLAIM, "original")
    annex = next(n for n in tree["nodes"] if not n.get("source_region_ids") and n["owner_path"] == "A/AN1")
    annex.update(number_canonical="1", number_display="1", number_components={"base": "1", "superscript": None}, number_is_explicit=True)
    rows = [{"key": f"1.{i}", "page": 1, "region_id": r["region_id"], "category": r["category"]}
            for i, r in enumerate(source["pages"][0]["regions"])]
    packet = {"source_asset_sha256": source["source_asset_sha256"], "extraction_id": source["extraction_id"],
              "assigned_pages": [1], "regions": rows, "pages": [{"page": 1, "sha256": "1" * 64}]}
    owners = ["A", None, "A", "A", "A/1", "S", "S", "S/1", "S2", "S2", "S2/1"]
    units = [("A", None, "act", None, None), ("A/1", "A", "point", "1", "1.4"),
             ("S", "A", "attached_document", None, "1.5"), ("S/1", "S", "point", "1", "1.7"),
             ("S2", "A", "attached_document", "1", "1.8"), ("S2/1", "S2", "point", "1", "1.10")]
    controls = {"schema_version": "m1-04a-independent-source-controls/1", "source_asset_sha256": packet["source_asset_sha256"],
                "extraction_id": packet["extraction_id"], "assigned_pages": [1], "uncertainties": [],
                "independence": {"candidate_outputs_used": False, "previous_gold_used": False},
                "regions": [{"key": r["key"], "status": "picture" if owner is None else "evaluated",
                             "owner": owner, "continuation": False} for r, owner in zip(rows, owners, strict=True)],
                "units": [{"owner_path": path, "parent_owner_path": parent, "kind": kind, "printed_number": number,
                           "start_key": start, "evidence_keys": [start] if start else []} for path, parent, kind, number, start in units],
                "image_reviews": [{"page": 1, "image_sha256": "1" * 64, "observed_structure": "authored two-document fixture"}]}
    report = checker().compare_controls(source, tree, packet, controls)
    assert report["canonical_regions_passed"] == 10
    assert not report["region_errors"] and not report["unit_errors"] and not report["extra_units"]
    assert report["unit_order_matches"]
