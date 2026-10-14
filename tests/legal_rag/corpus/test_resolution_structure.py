"""Authored resolution controls: separate approved texts, annexes and assets."""

import hashlib
import json
import sys
from pathlib import Path

import pytest
import test_native_text

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from legal_rag.corpus.housing_html import extract_html, validate  # noqa: E402
from legal_rag.corpus.housing_html import render_report  # noqa: E402
from legal_rag.corpus.native_text import extract_native, native_tree  # noqa: E402
from legal_rag.corpus.structure import build_structure  # noqa: E402


def document(number="812", title="Об учебных правилах"):
    return f'''<html><body><p class="T">ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ</p>
<p class="T">ПОСТАНОВЛЕНИЕ</p><p class="T">от 9 июня 2020 г. № {number}</p>
<p class="Z">{title}</p><p>Правительство Российской Федерации постановляет:</p>
<p>1. Утвердить прилагаемые правила.</p><p>а) Учебный подпункт.</p>
<p class="Y">Председатель Правительства Российской Федерации И.Примеров</p>
<p class="S">УТВЕРЖДЕНЫ постановлением Правительства Российской Федерации от 9 июня 2020 г. № {number}</p>
<p class="T">ПРАВИЛА учебного учета</p><p class="C">I. Общие положения</p>
<p>1. Первый пункт правил.</p><p>а) Подпункт правил.</p>
<p>Продолжение подпункта.</p><p class="C">I<sup>1</sup>. Дополнения</p>
<p>2<sup>1</sup>. Дополнительный пункт.</p>
<p class="S">ПРИЛОЖЕНИЕ № 1<sup>1</sup> к Правилам учебного учета</p>
<p class="T">РАСЧЕТ учебной величины</p><p>1. Величина определяется по формуле:</p>
<p id="formula"><img id="i1" src="data:image/png;base64,YQ==" width="5"/>,</p>
<p>где a - учебная величина.</p>
<p class="S">ПРИЛОЖЕНИЕ № 2 к Правилам учебного учета</p>
<p class="T">ТРЕБОВАНИЯ к учебной величине</p>
<table><tr><td colspan="3"><p>I. Качество</p></td></tr>
<tr><td rowspan="2"><p>1. Требование</p></td><td><p>Предел</p></td><td><p>Последствия</p></td></tr>
<tr><td colspan="2"><p>Продолжение условий</p></td></tr></table>
<p class="N"><sup>1</sup> Пояснение к таблице.</p>
<p class="S">УТВЕРЖДЕНЫ постановлением Правительства Российской Федерации от 9 июня 2020 г. № {number}</p>
<p class="T">ИЗМЕНЕНИЯ в учебных правилах</p>
<p>1. Пункт 13 изложить в следующей редакции:</p>
<p>"13. Учебный цитируемый пункт:</p><p>а) Цитируемый подпункт.".</p>
<p>2. Дополнить пунктами:</p><p>"38<sup>1</sup>. Первый цитируемый пункт.</p>
<p>38<sup>2</sup>. Второй цитируемый пункт.";</p>
<p>3. Следующее изменение.</p><p class="C">____________</p></body></html>'''


def native(html, number="812", title="Об учебных правилах", field="doctext"):
    payload = json.dumps({field: html, "error": None}).encode()
    asset = {"sha256": hashlib.sha256(payload).hexdigest(), "role": "consolidated",
             "declared_identity": f'Постановление Правительства Российской Федерации от 09.06.2020 № {number} "{title}"',
             "evidence": {"locator": "$." + field}}
    extraction = extract_native(asset, payload)
    return extraction, native_tree(asset, extraction)


@pytest.mark.parametrize("number,title", [("812", "Об учебных правилах"), ("937", "О другом учебном порядке")])
def test_resolution_scopes_do_not_merge_restarted_numbers(number, title):
    extraction, tree = native(document(number, title), number, title)
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    assert tree["identity_decision"]["family"] == "government_resolution"
    assert not tree["unresolved_blocks"]
    assert not tree["unresolved_regions"]
    ns = {n["address"]: n for n in tree["nodes"]}
    assert ns["act/point/1/subitem/а"]["parent_address"] == "act/point/1"
    assert ns["act/approved/1/point/1"]["parent_address"] == "act/approved/1/section/I"
    assert ns["act/approved/1/point/2.1"]["parent_address"] == "act/approved/1/section/I.1"
    assert ns["act/approved/1/annex/1.1/point/1"]["parent_address"] == "act/approved/1/annex/1.1"
    assert ns["act/approved/1/annex/2"]["parent_address"] == "act/approved/1"
    assert ns["act/approved/2/point/1/quote/1/point/13/subitem/а"]["kind"] == "subitem"
    assert ns["act/approved/2/point/2/quote/1/point/38.2"]["kind"] == "point"
    assert ns["act/approved/2/point/3"]["parent_address"] == "act/approved/2"
    assert tree["accounting"]["exactly_once"] and tree["accounting"]["regions_exactly_once"]
    assert {t["source_span"]["json_pointer"] for t in extraction["text_nodes"]} == {"/doctext"}


def test_table_topology_and_images_are_explicit_source_objects():
    html = document()
    extraction = extract_html(html.encode())
    tree = build_structure(extraction)
    table, = [n for n in tree["nodes"] if n["kind"] == "table"]
    assert len(table["rows"]) == 3
    assert table["rows"][1]["cells"][0]["rowspan"] == 2
    assert table["rows"][2]["cells"][0]["column"] == 1
    assert table["rows"][2]["cells"][0]["colspan"] == 2
    point = next(n for n in tree["nodes"] if n["address"] == "act/approved/1/annex/2/point/1")
    assert point["parent_address"] == "act/approved/1/annex/2/section/I"
    image, = [n for n in tree["nodes"] if n["kind"] == "image"]
    assert image["attributes"]["src"] == "data:image/png;base64,YQ=="
    assert image["parent_address"].startswith("act/approved/1/annex/1.1/point/1/")
    span = image["source_span"]
    assert html[span["char_start"]:span["char_end"]] == image["original_html"]
    check = validate(extraction, tree, html.encode())
    assert check["integrity_pass"], check["problems"]
    assert check["structure_complete"]


def test_conflicting_resolution_identity_and_annex_reference_remain_unresolved():
    _, tree = native(document(), number="813")
    assert tree["identity_decision"]["status"] == "unresolved"
    assert not tree["nodes"]
    _, tree = native(document().replace("к Правилам учебного учета", "к Правилам другого учета", 1))
    assert any(n["reason"] == "annex_target_unresolved" for n in tree["unresolved_blocks"])
    assert not any(n["address"] == "act/approved/1/annex/1.1" for n in tree["nodes"])


def test_native_field_must_match_evidence_locator():
    payload = json.dumps({"redtext": document(), "error": None}).encode()
    with pytest.raises(ValueError, match="doctext"):
        extract_native({"sha256": hashlib.sha256(payload).hexdigest(), "evidence": {"locator": "/doctext"}}, payload)


def test_unnumbered_section_subitems_and_numbered_normative_notes_have_own_scope():
    html = document().replace("<p>2<sup>1</sup>. Дополнительный пункт.</p>",
                              "<p>Состав включает:</p><p>а) Первый объект.</p><p>б) Второй объект.</p>")
    html = html.replace('<p class="N">', '<p>Примечания:</p><p>1. Единицы измерения:</p><p>а) Метры.</p><p class="N">')
    _, tree = native(html)
    assert not tree["unresolved_blocks"]
    ns = {n["address"]: n for n in tree["nodes"]}
    assert ns["act/approved/1/section/I.1/subitem/а"]["parent_address"] == "act/approved/1/section/I.1"
    assert ns["act/approved/1/annex/2/notes/1/point/1/subitem/а"]["kind"] == "subitem"
    assert ns["act/approved/1/annex/2/notes/1"]["kind"] == "notes_section"


def test_definition_quotes_and_nested_quotation_marks_do_not_change_legal_scope():
    html = document().replace("<p>а) Подпункт правил.</p>",
                              '<p>"учет" - учебное определение.</p><p>а) Подпункт правил.</p>')
    html = html.replace('<p>38<sup>2</sup>.', '<p>По учебному закону "О примере".</p><p>38<sup>2</sup>.')
    _, tree = native(html)
    assert not tree["unresolved_blocks"]
    ns = {n["address"]: n for n in tree["nodes"]}
    assert ns["act/approved/1/point/1/subitem/а"]["parent_address"] == "act/approved/1/point/1"
    assert ns["act/approved/2/point/2/quote/1/point/38.2"]["kind"] == "point"
    assert len([n for n in tree["nodes"] if n["kind"] == "quote"]) == 2


def test_unclosed_amendment_quote_blocks_completion():
    html = document().replace('Второй цитируемый пункт.";', 'Второй цитируемый пункт.;')
    extraction = extract_html(html.encode())
    tree = build_structure(extraction)
    assert tree["structural_issues"] == ["unclosed_amendment_quote"]
    assert not validate(extraction, tree, html.encode())["structure_complete"]


def test_report_displays_embedded_formula_without_executing_source_html():
    _, tree = native(document().replace('width="5"', 'width="5" onload="alert(1)"'))
    report = render_report(tree, {})
    assert '<img src="data:image/png;base64,YQ=="' in report
    assert 'onload="alert(1)"' not in report
    assert 'img-src data:' in report
    assert report.count('id="nNone"') == 0


def test_duplicate_annex_does_not_reuse_old_container():
    html = document().replace('ПРИЛОЖЕНИЕ № 2', 'ПРИЛОЖЕНИЕ № 1<sup>1</sup>')
    _, tree = native(html)
    assert any(n["reason"] == "duplicate_address" for n in tree["unresolved_blocks"])
    assert not any(n["kind"] == "table" for n in tree["nodes"])


@pytest.mark.parametrize("unclosed", [False, True])
def test_resolution_compiles_through_permission_boundary_and_repeats(tmp_path, unclosed):
    fixture = test_native_text.NativeTextTest()
    html = document()
    if unclosed:
        html = html.replace('Второй цитируемый пункт.";', 'Второй цитируемый пункт.;')
    claim = 'Постановление Правительства Российской Федерации от 09.06.2020 № 812 "Об учебных правилах"'
    path = fixture.prepare(tmp_path / "archive", locator="$.doctext",
                           response={"doctext": html, "error": None}, identity=claim)
    before = fixture.snapshot(tmp_path / "archive")
    code, result = fixture.run_cli(path, tmp_path / "result")
    assert code == 0
    draft = json.loads(Path(result["draft"]).read_text("utf-8"))
    assert ("unresolved_structure" in draft["blockers"]) == unclosed
    assert "case_law_sensitive_effect_unresolved" in draft["blockers"]
    assert not draft["content"]["trees"][0]["edition_admission"]
    assert fixture.run_cli(path, tmp_path / "result")[1]["result"] == "unchanged"
    assert fixture.snapshot(tmp_path / "archive") == before


def test_russian_quotation_marks_preserve_amendment_scope():
    html = document().replace('"13.', '«13.').replace('подпункт.".', 'подпункт.».')
    html = html.replace('"38<', '«38<').replace('пункт.";', 'пункт.»;')
    _, tree = native(html)
    ns = {n["address"]: n for n in tree["nodes"]}
    assert ns["act/approved/2/point/1/quote/1/point/13"]["kind"] == "point"
    assert ns["act/approved/2/point/2/quote/1/point/38.2"]["kind"] == "point"
    assert not tree["structural_issues"]


def test_image_only_paragraph_stays_before_its_following_definition():
    html = document().replace('width="5"/>,', 'width="5"/>')
    _, tree = native(html)
    nodes = {n["address"]: n for n in tree["nodes"]}
    for node in nodes.values():
        offsets = [nodes[a]["source_span"]["char_start"] for a in node["children"]]
        assert offsets == sorted(offsets), node["address"]
    extraction = extract_html(html.encode())
    raw = build_structure(extraction)
    parent = next(n for n in raw["nodes"] if len(n["children"]) > 1)
    parent["children"].reverse()
    check = validate(extraction, raw, html.encode())
    assert not check["integrity_pass"]


def test_substantive_annex_note_is_not_an_unscoped_editorial_note():
    html = document().replace('<p class="N">', '<p>Примечание. Используются действующие требования.</p><p class="N">')
    _, tree = native(html)
    note, = [n for n in tree["nodes"] if n["kind"] == "normative_note"]
    assert note["parent_address"] == "act/approved/1/annex/2"
    assert "scope_status" not in note


def test_embedded_table_preserves_owning_point_and_following_continuation():
    html = document().replace('<p>1. Первый пункт правил.</p>',
                              '<p>1. Первый пункт правил.</p><table><tr><td><p>Показатель</p></td><td><p>Значение</p></td></tr></table><p>Продолжение первого пункта.</p>')
    _, tree = native(html)
    assert not tree["unresolved_blocks"]
    table = next(n for n in tree["nodes"] if n["kind"] == "table")
    assert table["parent_address"] == "act/approved/1/point/1"
    paragraph = next(n for n in tree["nodes"] if n["text"] == "Продолжение первого пункта.")
    assert paragraph["parent_address"] == "act/approved/1/point/1"


@pytest.mark.parametrize("children,parents", [
    ('<p>1) Объект.</p><p>а) Условие.</p><p>2) Другой объект.</p><p>б) Другое условие.</p>',
     [("item/1", ""), ("item/1/subitem/а", "item/1"), ("item/2", ""), ("item/2/subitem/б", "item/2")]),
    ('<p>а) Объект.</p><p>1) Условие.</p><p>б) Другой объект.</p><p>2) Другое условие.</p>',
     [("subitem/а", ""), ("subitem/а/item/1", "subitem/а"), ("subitem/б", ""), ("subitem/б/item/2", "subitem/б")]),
])
def test_resolution_nested_numbering_clears_deeper_sibling_context(children, parents):
    _, tree = native(document().replace('<p>а) Подпункт правил.</p>', children))
    assert not tree["unresolved_blocks"]
    ns = {n["address"]: n for n in tree["nodes"]}
    base = "act/approved/1/point/1"
    for address, parent in parents:
        assert ns[base + "/" + address]["parent_address"] == base + ("/" + parent if parent else "")


def test_title_case_and_nested_ascii_quote_across_paragraphs():
    html = document().replace('ИЗМЕНЕНИЯ в учебных правилах', 'Изменения в учебных правилах')
    html = html.replace('<p>а) Цитируемый подпункт.".</p>',
                        '<p>а) Цитируемый подпункт с наименованием "</p><p>учебный объект".".</p>')
    _, tree = native(html)
    assert not tree["unresolved_blocks"] and not tree["structural_issues"]
    continuation = next(n for n in tree["nodes"] if n["text"].startswith('учебный объект'))
    assert continuation["parent_address"] == 'act/approved/2/point/1/quote/1/point/13/subitem/а'
    assert len([n for n in tree["nodes"] if n["kind"] == "quote"]) == 2


def test_amendment_quote_can_close_after_a_colon():
    html = document().replace('<p>"13. Учебный цитируемый пункт:</p><p>а) Цитируемый подпункт.".</p>',
                              '<p>"13. Величина определяется:";</p>')
    _, tree = native(html)
    assert not tree["structural_issues"] and not tree["unresolved_blocks"]
    assert next(n for n in tree["nodes"] if n["address"] == 'act/approved/2/point/2')["parent_address"] == 'act/approved/2'


def test_unsupported_heading_inside_quote_is_an_exception_not_a_crash():
    html = document().replace('<p>"13. Учебный цитируемый пункт:</p>',
                              '<p>"13. Учебный цитируемый пункт:</p><p class="T">ЧУЖОЙ ДОКУМЕНТ</p>')
    _, tree = native(html)
    assert any(n["reason"] == "unknown_heading" for n in tree["unresolved_blocks"])


def test_native_jpg_alias_is_visible_in_offline_report():
    _, tree = native(document().replace('image/png', 'image/jpg'))
    assert '<img src="data:image/jpg;base64,YQ=="' in render_report(tree, {})


def test_unknown_footnote_marker_does_not_become_a_point_continuation():
    _, tree = native(document().replace('<sup>1</sup> Пояснение к таблице.', '* Пояснение к таблице.'))
    assert any(n["reason"] == "unsupported_footnote_marker" for n in tree["unresolved_blocks"])
