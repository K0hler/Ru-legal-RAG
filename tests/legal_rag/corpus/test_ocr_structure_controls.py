"""Independent, authored expectations must reject even internally consistent wrong trees."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from test_ocr_structure import CLAIM, ISSUER, extraction
from legal_rag.corpus.ocr_owner_ast import build_owner_tree


SCRIPT = Path(__file__).resolve().parents[3] / "docs/assets/validate_ocr_structure.py"


def validator():
    assert SCRIPT.exists(), "the independent OCR structure validator is missing"
    spec = importlib.util.spec_from_file_location("independent_ocr_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authored_case():
    source = extraction()
    physical = [r for p in source["pages"] for r in p["regions"]]
    # Positions and owners are specified from the authored source above, never from its result.
    owners = ["A", "A", "A", "A", "A/1", "S", "S", "S/I", "S/I/1",
              None, "S/I/1", "S/I/1", "S/I/2", "S/I/2", "S/AN1", "S/AN1", "S/AN1/1", "S/AN1/1"]
    units = [("A", None, "act", None, []), ("A/1", "A", "point", "1", [4]),
             ("S", None, "approved_text", None, [5]), ("S/I", "S", "section", "I", [7]),
             ("S/I/1", "S/I", "point", "1", [8]), ("S/I/2", "S/I", "point", "2", [12]),
             ("S/AN1", "S", "annex", "1", [14]), ("S/AN1/1", "S/AN1", "point", "1", [16])]
    controls = {
        "schema_version": "ocr-independent-controls/1", "coverage": "full_document",
        "independence": {"candidate_outputs_used": False, "method": "Authored source fixture and explicit source positions"},
        "source_asset_sha256": source["source_asset_sha256"], "extraction_id": source["extraction_id"],
        "identity": {"family": "sanitary_rules", "issuer": ISSUER, "number": "812", "signing_date": "2020-06-09"},
        "regions": [{"region_id": r["region_id"], "owner_path": owner,
                     "disposition": "excluded" if owner is None else "parsed", "continuation": False}
                    for r, owner in zip(physical, owners, strict=True)],
        "units": [{"owner_path": owner, "parent_owner_path": parent, "kind": kind, "number_canonical": number,
                   "anchor_region_ids": [physical[i]["region_id"] for i in anchors], "number_display": number,
                   "number_components": {"base": number, "superscript": None} if number is not None else None,
                   "number_is_explicit": number is not None}
                  for owner, parent, kind, number, anchors in units],
    }
    return source, build_owner_tree(source, CLAIM, "original"), controls


def test_full_authored_source_controls_pass_without_calling_the_candidate(monkeypatch):
    source, tree, controls = authored_case()
    from legal_rag.corpus import ocr_owner_structure
    monkeypatch.setattr(ocr_owner_structure, "build", lambda *_: pytest.fail("validator called the candidate"))
    assert validator().validate_structure(source, tree, controls) == {"regions": 18, "units": 8, "text_nodes": len(source["text_nodes"])}


@pytest.mark.parametrize("damage", ["parent", "number", "order", "missing_region", "duplicate_text", "text", "view", "span", "block_id",
                                    "table", "table_kind", "footnote_owner", "anchor", "identity", "critical", "unresolved",
                                    "document_tree", "accounting", "control_coverage", "control_independence", "number_display", "number_components", "number_is_explicit"])
def test_independent_controls_reject_corruption(damage):
    source, tree, controls = authored_case()
    point = next(n for n in tree["nodes"] if n.get("owner_path") == "S/I/1" and not n.get("source_region_ids"))
    leaf = next(n for n in tree["nodes"] if n.get("source_region_ids"))
    if damage == "parent":
        point["parent_address"] = "act/owner/A"
    elif damage == "number":
        point["number_canonical"] = "99"
    elif damage in {"number_display", "number_components"}:
        point[damage] = "wrong"
    elif damage == "number_is_explicit":
        point[damage] = False
    elif damage == "order":
        tree["region_bindings"].reverse()
    elif damage == "missing_region":
        tree["region_bindings"].pop()
    elif damage == "duplicate_text":
        leaf["text_node_ids"].append(leaf["text_node_ids"][0])
    elif damage == "text":
        leaf["original_text"] += "invented"
    elif damage == "view":
        leaf["text"] += "invented"
    elif damage == "block_id":
        leaf["block_id"] += 1
    elif damage == "span":
        leaf["source_spans"][0]["locator"] += "invented"
    elif damage in {"table", "table_kind"}:
        table = next(n for n in tree["nodes"] if n["kind"] == "table")
        table["table_cells"][0]["text"] = "invented"
        if damage == "table_kind":
            table.update(kind="paragraph", layout_kind="paragraph")
    elif damage == "footnote_owner":
        binding = next(b for b in tree["region_bindings"] if b["page"] == 2 and b["index"] == 2)
        binding["owner_path"] = "S/I/2"
    elif damage == "anchor":
        point["anchor_region_ids"] = []
    elif damage == "identity":
        tree["identity_decision"]["number"] = "99"
    elif damage == "critical":
        tree["structural_issues"].append("unsupported_critical_shape")
    elif damage == "unresolved":
        tree["unresolved_blocks"].append(copy.deepcopy(leaf))
    elif damage == "document_tree":
        tree["document_tree"] = {}
    elif damage == "accounting":
        tree["accounting"]["exactly_once"] = False
    elif damage == "control_coverage":
        controls["regions"].pop()
    elif damage == "control_independence":
        controls["independence"]["candidate_outputs_used"] = True
    with pytest.raises(ValueError):
        validator().validate_structure(source, tree, controls)


def test_consistent_wrong_numbered_scope_is_not_accepted_as_its_own_gold():
    source, tree, controls = authored_case()
    # Change addresses, children and bindings together, retaining a self-consistent wrong scope.
    def rename(value):
        if isinstance(value, str):
            return value.replace("S/I/1", "S/I/9")
        if isinstance(value, list):
            return [rename(x) for x in value]
        if isinstance(value, dict):
            return {k: rename(v) for k, v in value.items()}
        return value
    with pytest.raises(ValueError, match="control"):
        validator().validate_structure(source, rename(tree), controls)


@pytest.mark.parametrize("damage", ["content_order", "content_parent", "table_kind_only"])
def test_consistent_graph_corruption_is_rejected(damage):
    source, tree, controls = authored_case()
    leaves = [n for n in tree["nodes"] if n.get("source_region_ids") and n["owner_path"] == "A"]
    if damage == "content_order":
        a, b = [tree["nodes"].index(n) for n in leaves[:2]]
        tree["nodes"][a], tree["nodes"][b] = tree["nodes"][b], tree["nodes"][a]
    elif damage == "content_parent":
        leaves[1]["parent_address"] = leaves[0]["address"]
    else:
        next(n for n in tree["nodes"] if n["kind"] == "table")["kind"] = "paragraph"
    for node in tree["nodes"]:
        node["children"] = [n["address"] for n in tree["nodes"] if n["parent_address"] == node["address"]]
    with pytest.raises(ValueError):
        validator().validate_structure(source, tree, controls)


@pytest.mark.parametrize("kind", ["text", "table"])
def test_unresolved_kind_cannot_be_hidden_in_parsed_nodes(kind):
    source, tree, controls = authored_case()
    node = next(n for n in tree["nodes"] if n.get("source_region_ids") and (n["kind"] == "table") == (kind == "table"))
    node["kind"] = "unresolved_block"
    with pytest.raises(ValueError, match="unresolved"):
        validator().validate_structure(source, tree, controls)


def test_consistent_reversed_fragments_in_one_leaf_are_rejected():
    from legal_rag.corpus.ocr_owner_ast import _entry, _source
    source, tree, controls = authored_case()
    first, second = [n for n in tree["nodes"] if n.get("source_region_ids") and n["owner_path"] == "S/I/1"][:2]
    ids = [*second["source_region_ids"], *first["source_region_ids"]]
    first.update(_entry(ids, *_source(source)))
    tree["nodes"].remove(second)
    for binding in tree["region_bindings"]:
        if binding["region_id"] in ids:
            binding["address"] = first["address"]
    for node in tree["nodes"]:
        node["children"] = [n["address"] for n in tree["nodes"] if n["parent_address"] == node["address"]]
    with pytest.raises(ValueError, match="order"):
        validator().validate_structure(source, tree, controls)


def frozen_case(root, split="reserved"):
    files = {"code": {}, "source": {}, "permission": {}, "extraction": {}, "controls": {}, "split": {}}
    digest = hashlib.sha256(b"%PDF-authored").hexdigest()
    source = {"source_asset_sha256": digest, "extraction_id": "authored"}
    controls = {**source, "identity": {"family": "sanitary_rules", "number": "812", "signing_date": "2020-06-09"}}
    values = {"code": ("src/legal_rag/corpus/_ocr_owner/text.py", b"# pinned rules\n"),
              "source": ("source.pdf", b"%PDF-authored"), "permission": ("permission.json", b"{}"),
              "extraction": ("extraction.json", json.dumps(source).encode()), "controls": ("controls.json", json.dumps(controls).encode()),
              "split": ("split.json", json.dumps({"documents": [{"key": "new-act", "split": split,
                         "family": "sanitary_rules", "date": "2020-06-09", "number": "812"}]}).encode())}
    for category, (name, raw) in values.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        files[category][name] = hashlib.sha256(raw).hexdigest()
    checker = root / "docs/assets/validate_ocr_structure.py"
    checker.parent.mkdir(parents=True)
    checker.write_bytes(b"# pinned independent checker\n")
    files["code"][checker.relative_to(root).as_posix()] = hashlib.sha256(checker.read_bytes()).hexdigest()
    return {"schema_version": "ocr-structure-freeze/1", "files": files,
            "documents": [{"key": "new-act", "source_asset_sha256": files["source"]["source.pdf"],
                           "source": "source.pdf", "permission": "permission.json",
                           "extraction": "extraction.json", "controls": "controls.json"}]}


def test_frozen_files_and_reserved_split_are_bound(tmp_path):
    freeze = frozen_case(tmp_path)
    validator().validate_freeze(tmp_path, freeze)


@pytest.mark.parametrize("category", ["code", "source", "permission", "extraction", "controls", "split"])
def test_changed_frozen_file_is_rejected(tmp_path, category):
    freeze = frozen_case(tmp_path)
    path = tmp_path / next(iter(freeze["files"][category]))
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="hash"):
        validator().validate_freeze(tmp_path, freeze)


def test_development_act_cannot_be_presented_as_reserved(tmp_path):
    with pytest.raises(ValueError, match="reserved"):
        validator().validate_freeze(tmp_path, frozen_case(tmp_path, "development"))


def test_unfrozen_new_private_rule_module_is_rejected(tmp_path):
    freeze = frozen_case(tmp_path)
    (tmp_path / "src/legal_rag/corpus/_ocr_owner/new.py").write_text("# new rules\n")
    with pytest.raises(ValueError, match="code inventory"):
        validator().validate_freeze(tmp_path, freeze)


def test_unfrozen_source_dependency_is_rejected(tmp_path):
    freeze = frozen_case(tmp_path)
    path = tmp_path / "src/legal_rag/sources/handoff.py"
    path.parent.mkdir(parents=True)
    path.write_text("# source dependency\n")
    with pytest.raises(ValueError, match="code inventory"):
        validator().validate_freeze(tmp_path, freeze)


def test_checker_itself_must_be_frozen(tmp_path):
    freeze = frozen_case(tmp_path)
    del freeze["files"]["code"]["docs/assets/validate_ocr_structure.py"]
    with pytest.raises(ValueError, match="checker"):
        validator().validate_freeze(tmp_path, freeze)


@pytest.mark.parametrize("field", ["source_asset_sha256", "extraction_id", "identity"])
def test_rehashed_controls_for_another_source_or_reserved_identity_are_rejected(tmp_path, field):
    freeze = frozen_case(tmp_path)
    path = tmp_path / "controls.json"
    controls = json.loads(path.read_bytes())
    controls[field] = {"family": "sanitary_rules", "number": "999", "signing_date": "2020-06-09"} if field == "identity" else "wrong"
    path.write_text(json.dumps(controls), encoding="utf-8")
    freeze["files"]["controls"]["controls.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="binding"):
        validator().validate_freeze(tmp_path, freeze)


def test_same_act_in_development_under_another_key_is_not_reserved(tmp_path):
    freeze = frozen_case(tmp_path)
    path = tmp_path / "split.json"
    split = json.loads(path.read_bytes())
    split["documents"].append({**split["documents"][0], "key": "known-act", "split": "development", "pilot": True})
    path.write_text(json.dumps(split), encoding="utf-8")
    freeze["files"]["split"]["split.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="reserved"):
        validator().validate_freeze(tmp_path, freeze)
