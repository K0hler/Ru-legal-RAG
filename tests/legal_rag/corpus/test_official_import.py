"""Source-tree import keeps official granularity and flags only source integrity."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from legal_rag.corpus.compiler import compile_input, json_bytes
from legal_rag.corpus.native_text import extract_native
from test_official_structure import HTML, IDENTITY, ROWS, prepare


def imported(html=HTML, rows=None):
    from legal_rag.corpus.official_import import import_official_tree

    payload = json_bytes({"redtext": html})
    asset = {"sha256": hashlib.sha256(payload).hexdigest(), "evidence": {"locator": "$.redtext"},
             "declared_identity": IDENTITY, "role": "consolidated"}
    raw = json_bytes({"status": 0, "complete": True, "data": ROWS if rows is None else rows})
    return import_official_tree(asset, extract_native(asset, payload), html, raw,
                                hashlib.sha256(raw).hexdigest(), "actual.pravo.gov.ru")


def test_compiler_disables_semantic_adapter_and_repeats_losslessly(tmp_path):
    path, _ = prepare(tmp_path / "archive")
    with patch("legal_rag.corpus.official_structure.build_official_tree", side_effect=AssertionError("disabled")):
        first = compile_input(path, "2026-10-15", tmp_path / "derived")
        repeat = compile_input(path, "2026-10-15", tmp_path / "derived")
    assert repeat == {**first, "result": "unchanged"}
    draft = json.loads(Path(first["draft"]).read_bytes())
    tree = draft["content"]["trees"][0]
    assert tree["parser_version"] == "official-json-import/1"
    assert [n["source_record"] for n in tree["nodes"] if n.get("source_id")] == ROWS
    assert "original_blocker" in draft["blockers"]
    assert draft["legal_admission"] == "not_requested"


@pytest.mark.parametrize("unit,caption", [("подраздел", "ПОДРАЗДЕЛ I. Заголовок"),
    ("часть", "ЧАСТЬ ПЕРВАЯ. ОБЩИЕ ПОЛОЖЕНИЯ"), ("абзац", "*абзац 1"),
    ("новый тип", "Без номера"), ("часть", "часть 99")])
def test_source_types_captions_and_unknown_fields_are_not_reinterpreted(unit, caption):
    rows = copy.deepcopy(ROWS)
    rows[1].update(unit=unit, caption=caption, future_field={"original": True})
    tree = imported(rows=rows)
    units = [n for n in tree["nodes"] if n.get("source_id")]
    assert [n["source_record"] for n in units] == rows
    assert units[1]["source_unit"] == unit
    assert units[1]["caption"] == caption
    assert all(n["number_canonical"] is None for n in units)
    assert units[2]["parent_address"] == units[1]["address"]
    assert not tree["source_integrity"]["findings"]


def test_quoted_articles_and_omitted_markers_remain_source_text():
    html = HTML.replace("Первая строка.", '"Статья 77. Цитата. 6<sup>2</sup>. Самостоятельный текст."')
    tree = imported(html)
    assert len([n for n in tree["nodes"] if n.get("source_id")]) == len(ROWS)
    assert not tree["unresolved_blocks"]
    assert not tree["source_integrity"]["findings"]
    assert "Статья 77" in " ".join(n["text"] for n in tree["nodes"])
    assert tree["accounting"]["exactly_once"] and tree["accounting"]["regions_exactly_once"]


@pytest.mark.parametrize("case", ["missing_start", "missing_end", "parent_range", "sibling_overlap"])
def test_bad_ranges_are_visible_and_never_repaired(case):
    rows = copy.deepcopy(ROWS)
    if case == "missing_start":
        rows[1]["np"] = "absent"
    elif case == "missing_end":
        rows[1]["npe"] = "absent"
    elif case == "parent_range":
        rows[0]["npe"] = "a1"
    else:
        rows[2]["lvl"] = 1
    tree = imported(rows=rows)
    assert tree["source_integrity"]["findings"]
    assert "source_structure_review_required" in tree["structural_issues"]
    assert [n["source_record"] for n in tree["nodes"] if n.get("source_id")] == rows
    assert tree["accounting"]["exactly_once"]
    assert tree["accounting"]["regions_exactly_once"]
    assert not any(n.get("normalization_evidence") for n in tree["nodes"])


@pytest.mark.parametrize("case", ["duplicate", "level_jump", "boolean_level"])
def test_malformed_tree_contract_is_rejected(case):
    rows = copy.deepcopy(ROWS)
    if case == "duplicate":
        rows[1]["id"] = rows[0]["id"]
    elif case == "level_jump":
        rows[1]["lvl"] = 4
    else:
        rows[1]["lvl"] = True
    with pytest.raises(ValueError):
        imported(rows=rows)


def test_children_follow_source_order_including_heading_before_child_unit():
    tree = imported()
    by_address = {n["address"]: n for n in tree["nodes"]}
    for node in tree["nodes"]:
        starts = [by_address[a]["source_span"]["char_start"] for a in node["children"]]
        assert starts == sorted(starts)


def test_missing_sibling_anchor_cannot_hide_other_sibling_overlap():
    rows = copy.deepcopy(ROWS)
    rows[1]["npe"] = "end"
    rows.insert(2, {"id": "opaque", "np": "absent", "npe": "absent", "lvl": 1,
                    "unit": "абзац", "caption": "Без границы"})
    rows[3]["lvl"] = 1
    tree = imported(rows=rows)
    overlap_ids = {f["source_id"] for f in tree["source_integrity"]["findings"]
                   if f["code"] == "overlapping_source_siblings"}
    assert overlap_ids == {rows[1]["id"], rows[3]["id"]}


def test_replay_verifier_checks_full_html_and_independent_text_owner():
    path = Path(__file__).resolve().parents[3] / "docs/assets/validate_official_import.py"
    spec = importlib.util.spec_from_file_location("source_import_verifier", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tree = imported()
    assert module.verify(tree, HTML, ROWS)["full_text"]
    block = next(n for n in tree["nodes"] if n["kind"] == "paragraph" and n["parent_address"] != "act")
    block["parent_address"] = block["source_container_address"] = "act"
    for node in tree["nodes"]:
        node["children"] = [a for a in node["children"] if a != block["address"]]
    with pytest.raises(AssertionError, match="source owner"):
        module.verify(tree, HTML, ROWS)
