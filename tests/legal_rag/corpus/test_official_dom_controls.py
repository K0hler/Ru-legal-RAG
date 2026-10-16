"""Fault injection for the separate diagnostic verifier, not parser mirrors."""

import copy
import importlib.util
from pathlib import Path

import pytest

from test_official_structure import HTML, ROWS, tree


path = Path(__file__).resolve().parents[3] / "docs/assets/official_json_dom_controls.py"
spec = importlib.util.spec_from_file_location("independent_dom_controls", path)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


@pytest.mark.parametrize("fault,expected", [
    ("normative_text", "normative_text_mismatch"),
    ("raw_text", "paragraph_text_mismatch"),
    ("media_html", "ast_media_source_mismatch"),
    ("consistent_coordinate_shift", "lexical_source_span_mismatch"),
    ("heading_number", "printed_heading_number_conflict"),
    ("outside_table_cell", "outside_paragraph_owner_conflict"),
])
def test_independent_verifier_rejects_mutated_downstream_content(fault, expected):
    html = HTML.replace('<p><img', '<p id="imageholder"><img').replace('<td><p>', '<td>Прямой текст<p>')
    rows = copy.deepcopy(ROWS)
    rows[0]["npe"] = "imageholder"
    controls = reader.prepare(html, "federal_law", rows)
    result = tree(html, rows=rows)
    assert reader.compare(result, controls, html, rows)["errors"] == []
    paragraph = next(n for n in result["nodes"] if n.get("html_id") == "end")
    if fault == "normative_text":
        paragraph["text"] = "CORRUPTED NORMATIVE TEXT"
    elif fault == "raw_text":
        paragraph["original_text"] = "CORRUPTED RAW TEXT"
    elif fault == "media_html":
        next(n for n in result["nodes"] if n["kind"] == "image")["original_html"] = '<img src="WRONG.png">'
    elif fault == "heading_number":
        next(n for n in result["nodes"] if n.get("source_id") == "a1")["number_canonical"] = "99"
    elif fault == "outside_table_cell":
        next(n for n in result["nodes"] if n["kind"] == "table_cell" and n.get("paragraph") is None)["source_container_address"] = "act"
    else:
        span = paragraph["source_span"]
        start = span["char_start"]
        span["char_start"] += 1
        span["utf8_byte_start"] += len(html[start].encode("utf-8"))
        span["locator"] = f"{span['json_pointer']}:chars:{span['char_start']}:{span['char_end']}"
    errors = reader.compare(result, controls, html, rows)["errors"]
    assert any(e["kind"] == expected for e in errors), errors
