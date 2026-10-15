import copy
from pathlib import Path

import pytest

from legal_rag.corpus.structure_audit import audit_tree, scan_html
from test_official_structure import HTML, tree


def test_scanner_reads_html_without_sidecar_or_parser_markers():
    html = '''<html><body><p id="s">РАЗДЕЛ XIV. Название</p>
    <p id="c">Глава 47<span class="WB">3</span>. Глава</p>
    <p id="a">Статья 41<sup>1</sup>. Статья</p>
    <p id="p">17<span class="W9">3</span>. Положение</p>
    <p id="q">47.3. Положение</p><p id="x">§ 2. Подраздел</p>
    <p id="letters">Перечень:<br>а) один;<br>б) два.</p></body></html>'''
    markers = scan_html(html)
    assert [(m["html_id"], m["kind_hint"], m["number_canonical"]) for m in markers] == [
        ("s", "section", "XIV"), ("c", "chapter", "47.3"), ("a", "article", "41.1"),
        ("p", "numbered", "17.3"), ("q", "numbered", "47.3"), ("x", "subchapter", "2"),
        ("letters", "letter", "а"), ("letters", "letter", "б")]
    assert markers[3]["number_display"] == "17³"
    assert markers[-1]["line"] == 2


def test_roman_heading_keeps_its_superscript_component():
    marker = scan_html('<html><body><p>РАЗДЕЛ III<span class="W9">2</span></p></body></html>')[0]
    assert marker["kind_hint"] == "section"
    assert marker["number_canonical"] == "III.2"
    assert marker["number_display"] == "III²"


def test_normative_note_number_is_matched_to_source_caption():
    html = '<html><body><p id="n">2. Нормативное примечание.</p></body></html>'
    span = {"char_start": 12, "char_end": 67, "source_asset_sha256": "a" * 64}
    node = {"block_id": None, "address": "act/note/2", "parent_address": "act", "kind": "normative_note",
            "number_canonical": None, "caption": "примечание 2", "source_span": span}
    block = {"block_id": 0, "address": "act/note/2/paragraph/0", "parent_address": node["address"],
             "paragraph": 1, "kind": "paragraph", "text": "2. Нормативное примечание.",
             "html_start": 12, "source_span": {**span, "char_end": 60}}
    report = audit_tree(scan_html(html), [node, block], [], [])
    assert report["critical_count"] == 0
    assert report["counts_by_status"]["matched"] == 1


def test_scanner_ignores_editorial_control_text_and_body_references():
    html = '''<html><body><p class="A">Статья 99. Редакторский текст</p>
    <p>См. статью 8.</p><p><label>Статья 98. Контрол</label></p>
    <p>Текст<span class="mark"><br>27. Редакторская ссылка</span></p>
    <script>Статья 97. Script</script><p>Внутри обычной строки 3. Не заголовок.</p>
    </body></html>'''
    assert scan_html(html) == []


@pytest.mark.parametrize("marker", ["17<sup>3</sup>. Новый пункт", "47.3. Новый пункт",
    "Статья 41<sup>1</sup>. Новая статья", "Глава XIV. Новая глава", "Раздел V. Новый раздел", "§ 3. Новый подраздел"])
def test_unmatched_markers_block_new_tree_with_source_evidence(marker):
    html = HTML.replace("<table>", f'<p id="future">{marker}</p><table>', 1)
    result = tree(html)
    report = result["structure_audit"]
    finding = next(f for f in report["findings"] if f.get("html_id") == "future")
    assert finding["severity"] == "critical"
    assert finding["code"] == "unmatched_marker"
    assert finding["source_span"]["source_asset_sha256"] == result["source_asset_sha256"]
    assert finding["source_span"]["char_end"] > finding["source_span"]["char_start"]
    assert finding["excerpt"]
    assert "structure_audit_failed" in result["structural_issues"]


def test_number_sequence_does_not_invent_missing_text():
    result = tree()
    assert result["structure_audit"]["critical_count"] == 0
    assert result["structure_audit"]["candidates_checked"] == 3
    assert not any(f.get("number_canonical") == "2.2" for f in result["structure_audit"]["findings"])


@pytest.mark.parametrize("case", ["wrong_kind", "outside_parent", "parent_cycle", "missing_parent"])
def test_audit_checks_result_type_and_containment(case):
    result = tree()
    nodes = copy.deepcopy(result["nodes"])
    article = next(n for n in nodes if n.get("source_id") == "a1")
    part = next(n for n in nodes if n.get("source_id") == "a1_p2")
    if case == "wrong_kind":
        article["kind"] = "part"
    elif case == "outside_parent":
        part["source_span"]["char_end"] = article["source_span"]["char_end"] + 1
    elif case == "parent_cycle":
        article["parent_address"] = part["address"]
    else:
        part["parent_address"] = "act/absent"
    audit = audit_tree(scan_html(HTML), nodes, result["unresolved_blocks"], result["excluded_blocks"])
    assert audit["critical_count"] > 0
    expected = {"wrong_kind": "marker_kind_conflict", "outside_parent": "child_outside_parent", "parent_cycle": "parent_cycle", "missing_parent": "missing_parent"}[case]
    assert any(f["code"] == expected for f in audit["findings"])


def test_report_is_deterministic_and_hashes_the_independent_candidates():
    first, second = tree(), tree()
    assert first["structure_audit"] == second["structure_audit"]
    assert len(first["structure_audit"]["candidates_sha256"]) == 64


def test_compiler_report_shows_audit_findings(tmp_path):
    from legal_rag.corpus.compiler import compile_input
    from test_official_structure import prepare

    path, _ = prepare(tmp_path / "archive")
    result = compile_input(path, "2026-10-15", tmp_path / "derived")
    assert "Независимая проверка структуры" in Path(result["report"]).read_text(encoding="utf-8")
