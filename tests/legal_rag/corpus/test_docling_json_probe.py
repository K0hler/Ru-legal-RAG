"""Authored JSON mapping checks; Docling is an explicit external experiment only."""

import copy
import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location(
    "docling_json_probe",
    Path(__file__).resolve().parents[3] / "docs/assets/run_docling_json_probe.py",
)
probe = importlib.util.module_from_spec(SPEC)


def authored():
    regions = [
        {"category": "Section-header", "bbox": [1, 2, 80, 10], "text": "## I. Правила"},
        {"category": "Unknown-tag", "bbox": [1, 12, 80, 20], "text": "  а\u00adб\nв  "},
        {"category": "Table", "bbox": [1, 22, 80, 40], "text": "<table>source</table>"},
    ]
    native = {"pages": [{"page_number": 8, "image_size": [100, 200], "layout": regions},
                        {"page_number": 9, "image_size": [100, 200], "layout": []}]}
    table = {"rows": 1, "columns": 2, "cells": [
        {"row": 0, "column": 0, "rowspan": 1, "colspan": 2, "text": "+", "header": False,
         "bbox": None}], "outside_cell_text": []}
    extraction = {"source_asset_sha256": "a" * 64, "pages": [
        {"page": 8, "image_size": [100, 200], "regions": [
            {"region_id": str(i), "source_record": copy.deepcopy(region),
             "json_pointer": f"/pages/0/layout/{i}", **({"table": table} if i == 2 else {})}
            for i, region in enumerate(regions)]},
        {"page": 9, "image_size": [100, 200], "regions": []}]}
    return native, extraction


def test_mapping_is_literal_preserves_empty_pages_and_table_topology():
    SPEC.loader.exec_module(probe)
    native, extraction = authored()
    projected = probe.project(native, extraction, "a" * 64)
    assert [page["page_no"] for page in projected["pages"]] == [8, 9]
    assert projected["regions"][0]["label"] == "section_header"
    assert projected["regions"][0]["source_record"]["text"] == "## I. Правила"
    assert projected["regions"][1]["source_record"] == native["pages"][0]["layout"][1]
    assert projected["regions"][1]["label"] == "text"
    assert projected["regions"][2]["table"] == extraction["pages"][0]["regions"][2]["table"]
    projected["regions"][0]["source_record"]["text"] = "changed"
    assert native["pages"][0]["layout"][0]["text"] == "## I. Правила"


@pytest.mark.parametrize("mutation", ["text", "page", "bbox", "source"])
def test_mapping_refuses_unbound_source_fields(mutation):
    SPEC.loader.exec_module(probe)
    native, extraction = authored()
    if mutation == "source":
        extraction["source_asset_sha256"] = "b" * 64
    elif mutation == "page":
        extraction["pages"][0]["page"] = 7
    else:
        extraction["pages"][0]["regions"][0]["source_record"][mutation] = "changed"
    with pytest.raises(ValueError, match="binding"):
        probe.project(native, extraction, "a" * 64)


def test_retention_refuses_overwrite(tmp_path):
    SPEC.loader.exec_module(probe)
    path = tmp_path / "attempt.json"
    probe.write(path, {"failed": True})
    with pytest.raises(FileExistsError):
        probe.write(path, {"replacement": True})


@pytest.mark.parametrize(("raw", "expected"), [
    ("## I. Правила", ("## ", "I. Правила")),
    ("###\t1.1. Раздел", ("###\t", "1.1. Раздел")),
    ("#### I. Правила", ("", "#### I. Правила")),
    (" ## I. Правила", ("", " ## I. Правила")),
    ("##I. Правила", ("", "##I. Правила")),
    ("I. Правила", ("", "I. Правила")),
])
def test_bounded_heading_prefix_projection_is_exact(raw, expected):
    SPEC.loader.exec_module(probe)
    removed, after = probe.heading_prefix(raw)
    assert (removed, after) == expected
    assert removed + after == raw
