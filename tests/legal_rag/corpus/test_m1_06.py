"""Full-bundle accounting must not be mistaken for independent structure acceptance."""

import copy
import importlib.util
from pathlib import Path

import pytest

from legal_rag.corpus.compiler import content_hash
from test_ocr_source_controls import source_case


def verifier():
    path = Path(__file__).resolve().parents[3] / "docs/assets/verify_m1_06.py"
    assert path.exists(), "M1-06 bundle verifier missing"
    spec = importlib.util.spec_from_file_location("verify_m1_06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bundle():
    extraction, tree, packet, controls = source_case()
    sha = extraction["source_asset_sha256"]
    manifest = {"manifest_hash": "a" * 64, "kind": "original_amendments", "target_dates": ["2026-10-01"],
                "assets": [{"sha256": sha, "role": "original"}]}
    draft = {"input_hash": manifest["manifest_hash"], "validated_input_hash": content_hash(manifest),
             "target_date": "2026-10-01",
             "content": {"trees": [tree], "target_date": "2026-10-01", "kind": "original_amendments"}}
    seal(draft)
    return manifest, {sha: extraction}, draft, copy.deepcopy(draft), {sha: (packet, controls)}


def seal(draft):
    draft.pop("draft_id", None)
    draft["content_hash"] = content_hash(draft["content"])
    draft["draft_id"] = content_hash(draft)


def test_complete_bundle_requires_full_independent_controls_and_equal_repeated_build():
    args = bundle()
    report = verifier().verify_bundle(*args, target_date="2026-10-01")
    assert report["status"] == "pass"
    assert report["accounting"] == {"documents": 1, "pages": 2, "regions": 18, "tables": 1}
    assert report["documents"][0]["structure"]["status"] == "pass"
    packet, controls = next(iter(args[-1].values()))
    assert report["documents"][0]["structure"]["controls_hash"] == content_hash(controls)
    assert report["documents"][0]["structure"]["packet_hash"] == content_hash(packet)
    assert report["legal_admission"] == "not_requested"


def test_missing_controls_leave_structure_unaccepted_despite_complete_accounting():
    args = list(bundle())
    args[-1] = {}
    report = verifier().verify_bundle(*args, target_date="2026-10-01")
    assert report["status"] == "incomplete"
    assert report["documents"][0]["structure"]["status"] == "missing_controls"


@pytest.mark.parametrize("damage", ["missing_document", "duplicate_document", "foreign_document", "input_binding",
                                    "partial_pages", "repeat", "text", "locator", "table"])
def test_corrupt_or_partial_bundle_cannot_pass(damage):
    manifest, extractions, first, second, controls = bundle()
    tree = first["content"]["trees"][0]
    if damage == "missing_document":
        manifest["assets"].append({"sha256": "b" * 64, "role": "amendment"})
    elif damage == "duplicate_document":
        first["content"]["trees"].append(copy.deepcopy(tree))
    elif damage == "foreign_document":
        tree["source_asset_sha256"] = "b" * 64
    elif damage == "input_binding":
        first["input_hash"] = "b" * 64
    elif damage == "partial_pages":
        next(iter(extractions.values()))["coverage"]["all_source_pages"] = False
    elif damage == "repeat":
        second["extra"] = "different repeated build"
        seal(second)
    elif damage in {"text", "locator"}:
        leaf = next(n for n in tree["nodes"] if n.get("text_node_ids"))
        if damage == "text":
            leaf["original_text"] += "invented"
        else:
            leaf["source_spans"][0]["locator"] += "invented"
    else:
        next(n for n in tree["nodes"] if n.get("table_cells"))["table_cells"][0]["colspan"] += 1
    if damage != "repeat":
        seal(first)
        second = copy.deepcopy(first)
    with pytest.raises(ValueError):
        verifier().verify_bundle(manifest, extractions, first, second, controls, target_date="2026-10-01")


@pytest.mark.parametrize("damage", ["missing_region", "wrong_owner", "derived_controls", "missing_image"])
def test_independent_control_failures_are_reported_as_failed_structure(damage):
    args = bundle()
    _, controls = next(iter(args[-1].values()))
    if damage == "missing_region":
        controls["regions"].pop()
    elif damage == "wrong_owner":
        next(r for r in controls["regions"] if r["owner"] == "S/I/1")["owner"] = "S/I/2"
    elif damage == "derived_controls":
        controls["independence"]["candidate_outputs_used"] = True
    else:
        controls["image_reviews"].pop()
    report = verifier().verify_bundle(*args, target_date="2026-10-01")
    assert report["status"] == "fail"
    assert report["documents"][0]["structure"]["status"] == "fail"


def test_valid_other_date_draft_cannot_be_relabelled_as_requested_date():
    manifest, extractions, first, second, controls = bundle()
    manifest["target_dates"].append("2025-01-01")
    for draft in (first, second):
        draft["validated_input_hash"] = content_hash(manifest)
        draft["target_date"] = draft["content"]["target_date"] = "2025-01-01"
        seal(draft)
    with pytest.raises(ValueError, match="date"):
        verifier().verify_bundle(manifest, extractions, first, second, controls, target_date="2026-10-01")


@pytest.mark.parametrize("damage", ["role", "namespace", "node_id"])
def test_self_consistent_graph_cannot_change_asset_role_namespace_or_canonical_ids(damage):
    manifest, extractions, first, _, controls = bundle()
    tree = first["content"]["trees"][0]
    if damage == "role":
        tree["role"] = "amendment"
    elif damage == "node_id":
        tree["nodes"][1]["node_id"] = tree["nodes"][0]["node_id"]
    else:
        old = tree["namespace"]
        tree["namespace"] = "foreign"
        for node in tree["nodes"]:
            for key in ("address", "parent_address"):
                node[key] = "foreign" + node[key][len(old):]
            node["children"] = ["foreign" + child[len(old):] for child in node["children"]]
            node["node_id"] = content_hash({"source": tree["source_asset_sha256"], "parser": tree["parser_version"],
                                            "address": node["address"]})
        for binding in tree["region_bindings"]:
            if binding["address"] is not None:
                binding["address"] = "foreign" + binding["address"][len(old):]
    seal(first)
    with pytest.raises(ValueError):
        verifier().verify_bundle(manifest, extractions, first, copy.deepcopy(first), controls, target_date="2026-10-01")
