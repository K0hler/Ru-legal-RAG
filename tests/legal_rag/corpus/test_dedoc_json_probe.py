"""Authored checks for the direct saved-JSON Dedoc experiment, without Dedoc."""

import importlib.util
from pathlib import Path

import pytest


def load_probe():
    path = Path(__file__).resolve().parents[3] / "docs/assets/run_dedoc_json_probe.py"
    spec = importlib.util.spec_from_file_location("dedoc_json_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authored_input():
    regions = [
        {"bbox": [1, 2, 40, 20], "category": "Unfamiliar", "text": "## I. Текст\n2. Ещё", "extra": 7},
        {"bbox": [2, 25, 30, 40], "category": "Picture", "opaque": {"x": True}},
        {"bbox": [3, 45, 70, 80], "category": "Table", "text": "<table>literal source</table>"},
    ]
    native = {"extra": "native", "pages": [{"page_number": 2, "image_size": [100, 200], "layout": regions}]}
    extraction = {"source_asset_sha256": "a" * 64, "pages": [{"page": 2, "regions": [
        {"region_id": f"r{i}", "json_pointer": f"/pages/0/layout/{i}", "source_record": r}
        for i, r in enumerate(regions)
    ]}]}
    extraction["pages"][0]["regions"][2]["table"] = {
        "rows": 2, "columns": 2, "rectangular": True, "outside_cell_text": [], "cells": [
            {"row": 0, "column": 0, "rowspan": 2, "colspan": 1, "header": True, "text": "A"},
            {"row": 0, "column": 1, "rowspan": 1, "colspan": 1, "header": False, "text": ""},
            {"row": 1, "column": 1, "rowspan": 1, "colspan": 1, "header": False, "text": "+"},
        ],
    }
    return native, extraction


def test_native_projection_keeps_exact_text_categories_empty_regions_and_cell_topology():
    probe = load_probe()
    native, extraction = authored_input()
    result = probe.project(native, extraction)
    assert [(x["text"], x["category"], x["page_id"], x["char_start"], x["char_end"])
            for x in result["lines"]] == [
        ("## I. Текст\n", "Unfamiliar", 1, 0, 12),
        ("2. Ещё", "Unfamiliar", 1, 12, 18),
        ("", "Picture", 1, 0, 0),
        ("", "Table", 1, 0, 0),
    ]
    assert result["lines"][0]["bbox"] == [1, 2, 40, 20]
    assert result["lines"][0]["json_pointer"] == "/pages/0/layout/0/text"
    assert result["regions"][1]["native_record"] == native["pages"][0]["layout"][1]
    assert result["tables"][0]["native_text"] == "<table>literal source</table>"
    grid = probe.table_grid(result["tables"][0]["topology"])
    assert [[(x["text"], x["invisible"], x["rowspan"], x["colspan"]) for x in row] for row in grid] == [
        [("A", False, 2, 1), ("", False, 1, 1)],
        [("A", True, 2, 1), ("+", False, 1, 1)],
    ]
    assert {x["uid"] for x in result["lines"]} == {"r0:0", "r0:1", "r1:0", "r2:0"}


def test_projection_refuses_an_extraction_whose_source_record_changed():
    probe = load_probe()
    native, extraction = authored_input()
    extraction["pages"][0]["regions"][0]["source_record"] = {"text": "changed"}
    with pytest.raises(ValueError, match="native region mismatch"):
        probe.project(native, extraction)


def test_optional_section_header_view_removes_only_first_line_prefix_and_maps_raw_offset():
    probe = load_probe()
    native, extraction = authored_input()
    native["pages"][0]["layout"][0]["category"] = "Section-header"
    native["pages"][0]["layout"][0]["text"] = "## I. Текст\n## II. Буквально"
    result = probe.project(native, extraction, strip_section_header_prefix=True)
    assert [(x["text"], x["char_start"], x["char_end"]) for x in result["lines"][:2]] == [
        ("I. Текст\n", 3, 12), ("## II. Буквально", 12, 28),
    ]
    assert result["lines"][0]["native_text"] == "## I. Текст\n"
    assert result["projection_ledger"] == [{"source_uid": "r0:0", "json_pointer": "/pages/0/layout/0/text",
                                            "operation": "remove_first_line_markdown_section_prefix",
                                            "native_char_start": 0, "native_char_end": 3, "removed": "## "}]


def test_retention_rejects_even_identical_overwrite(tmp_path):
    probe = load_probe()
    path = tmp_path / "failed.json"
    probe.write(path, {"failed": True})
    with pytest.raises(FileExistsError):
        probe.write(path, {"failed": True})
    assert path.read_text(encoding="utf-8").strip() == '{\n  "failed": true\n}'


def test_output_map_uses_native_offsets_only_when_fragments_reconstruct_literal_source():
    probe = load_probe()
    projection = {"lines": [{"uid": "u", "json_pointer": "/pages/0/layout/0/text",
                              "category": "Text", "char_start": 7, "text": "1. Абв"}],
                  "regions": [], "tables": [{"uid": "unattached"}]}
    node = {"node_id": "0", "metadata": {"paragraph_type": "root", "page_id": 0},
            "text": "1.", "annotations": [{"name": "dots_source_uid", "value": "u", "start": 0, "end": 2}],
            "subparagraphs": [{"node_id": "0.0", "metadata": {"paragraph_type": "raw_text", "page_id": 0},
                               "text": " Абв", "subparagraphs": [],
                               "annotations": [{"name": "dots_source_uid", "value": "u", "start": 0, "end": 4}]}]}
    payload = {"content": {"structure": node}}
    result = probe.inspect_output(payload, projection)
    assert result["changed_or_lost_lines"] == []
    assert [(r["native_char_start"], r["native_char_end"]) for r in result["output_source_map"][0]["output_fragments"]] == [(7, 9), (9, 13)]
    assert result["unlinked_table_uids"] == ["unattached"]
    node["subparagraphs"][0]["text"] = " Иное"
    changed = probe.inspect_output(payload, projection)["changed_or_lost_lines"][0]
    assert changed["expected"] == "1. Абв"
    assert changed["actual"] == "1. Ино"
    assert all("native_char_start" not in r for r in changed["output_fragments"])


def test_failed_or_unstable_library_run_produces_nonzero_exit_code():
    probe = load_probe()
    completed = {"status": "completed", "raw_repeat_identical": True,
                 "content_repeat_identical": True, "checks_repeat_identical": True}
    assert probe.outcome_exit_code([completed]) == 0
    assert probe.outcome_exit_code([{"status": "failed"}]) == 2
    assert probe.outcome_exit_code([{**completed, "content_repeat_identical": False}]) == 2
