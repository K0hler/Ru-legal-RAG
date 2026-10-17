"""Authored preservation checks for the explicit OCR parser experiment tools."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "ocr_probe", Path(__file__).resolve().parents[3] / "docs/assets/probe_ocr_structure.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def test_projection_keeps_tables_and_maps_only_explicit_heading_markup():
    lines = [{"uid": "0", "category": "Section-header", "text": "## I. Правила"},
             {"uid": "1", "category": "Text", "text": "1. Буквально < > & # знак."},
             {"uid": "2", "category": "Table", "text": '<table><tr><td>+</td><td></td></tr></table>'}]
    html, mapping = probe.prepare_html(lines)
    assert '<h2 data-source-block-id="0">I. Правила</h2>' in html
    assert "1. Буквально &lt; &gt; &amp; # знак." in html
    assert '<table><tr><td>+</td><td></td></tr></table>' in html
    assert [(m["uid"], m["before"], m["after"]) for m in mapping] == [("0", "## I. Правила", "I. Правила")]


def test_experiment_retention_refuses_to_overwrite_prior_failure(tmp_path):
    path = tmp_path / "trial.json"
    probe.retain(path, b"original failed trial")
    probe.retain(path, b"original failed trial")
    with pytest.raises(ValueError, match="immutable"):
        probe.retain(path, b"replacement success")
    assert path.read_bytes() == b"original failed trial"
