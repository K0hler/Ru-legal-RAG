import copy
import hashlib

import pytest

from legal_rag.corpus.compiler import json_bytes
from legal_rag.corpus.native_text import extract_native
from legal_rag.corpus.official_structure import build_official_tree
from test_official_structure import HTML, ROWS, tree


@pytest.mark.parametrize("case", ["valid", "gap", "no_colon", "quoted"])
def test_missing_letter_list_requires_a_contiguous_run_after_colon(case):
    html = HTML.replace('<p id="end">Конец.</p>',
        '<p id="intro">Условия:</p><p id="la">а) Первое;</p><p id="lb">б) Второе.</p><p id="end">Конец.</p>')
    if case == "gap":
        html = html.replace('б) Второе', 'в) Второе')
    elif case == "no_colon":
        html = html.replace('Условия:', 'Условия.')
    elif case == "quoted":
        html = html.replace('а) Первое', '"а) Первое')
    rows = copy.deepcopy(ROWS)
    rows[1]["npe"] = "end"
    result = tree(html, rows=rows)
    recovered = [n for n in result["nodes"] if n.get("recovery_evidence", {}).get("rule") == "explicit-letter-list/1"]
    if case == "valid":
        assert [n["number_canonical"] for n in recovered] == ["а", "б"]
        assert len({n["parent_address"] for n in recovered}) == 1
        assert not result["unresolved_blocks"] and not result["structural_issues"]
    else:
        assert not recovered and result["structure_audit"]["critical_count"] > 0


def test_recovered_last_letter_owns_continuation_and_formula_until_parent_end():
    rows = copy.deepcopy(ROWS)
    rows[1]["npe"] = "end"
    html = HTML.replace('<p id="end">Конец.</p>', '<p id="intro">Условия:</p><p id="la">а) Первое;</p>'
        '<p id="lb">б) Платеж рассчитывается по формуле:</p><p id="formula"><img src="formula.png"></p>'
        '<p id="end">Продолжение.</p>')
    result = tree(html, rows=rows)
    letter = next(n for n in result["nodes"] if n.get("recovery_evidence", {}).get("html_id") == "lb")
    assert next(n for n in result["nodes"] if n["kind"] == "image" and 'formula.png' in n["original_html"])["parent_address"] == letter["address"]
    assert next(n for n in result["nodes"] if n.get("html_id") == "end")["parent_address"] == letter["address"]
    assert not result["structural_issues"] and not result["unresolved_blocks"]


def resolution(base=17, exponent=2, parent="section", marker=None, extra=""):
    heading = "Раздел IV. Требования" if parent == "section" else "ПРИЛОЖЕНИЕ № 9"
    caption = heading
    unit = "раздел" if parent == "section" else "приложение"
    html = ('<html><body><p>ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ</p>'
            '<p>ПОСТАНОВЛЕНИЕ</p><p>от 1 января 2020 г. № 987</p>'
            '<p class="Z">Об условиях проверки</p>'
            '<p>Председатель Правительства Российской Федерации</p>'
            '<p>УТВЕРЖДЕНЫ</p><p id="root">ПРАВИЛА</p>'
            f'<p id="container">{heading}</p>'
            f'<p id="old">{base}<sup>{exponent}</sup>. Первое условие.</p>'
            f'<p id="new">{marker or f"{base}<sup>{exponent + 1}</sup>."} Второе условие.</p>'
            f'<p id="formula">Формула:<img src="formula.png">{extra}</p>'
            '<table><tr><td><p>Переменная</p></td><td><p>Значение</p></td></tr></table>'
            '<p id="last">Продолжение<span class="mark"> (В редакции)</span></p>'
            f'<p id="next">{base + 1}. Следующее условие.</p></body></html>')
    rows = [
        {"id": "r", "np": "root", "npe": "next", "unit": "вложение", "caption": "ПРАВИЛА", "lvl": 0},
        {"id": "r_c", "np": "container", "npe": "next", "unit": unit, "caption": caption, "lvl": 1},
        {"id": "r_c_old", "np": "old", "npe": "last", "unit": "пункт", "caption": f"пункт {base}<sup>{exponent}</sup>", "lvl": 2},
        {"id": "r_c_next", "np": "next", "npe": "next", "unit": "пункт", "caption": f"пункт {base + 1}", "lvl": 2},
    ]
    return html, rows


def build(html, rows):
    raw = json_bytes({"redtext": html})
    asset = {"sha256": hashlib.sha256(raw).hexdigest(), "role": "consolidated", "evidence": {"locator": "$.redtext"},
             "declared_identity": 'Постановление Правительства Российской Федерации от 01.01.2020 № 987 "Об условиях проверки"'}
    sidecar = json_bytes({"status": 0, "complete": True, "data": rows})
    return build_official_tree(asset, extract_native(asset, raw), html, sidecar, hashlib.sha256(sidecar).hexdigest(), "actual.pravo.gov.ru")


@pytest.mark.parametrize("base,exponent,parent", [(17, 2, "section"), (47, 1, "annex")])
def test_superscript_sibling_recovery_keeps_full_payload_and_original_evidence(base, exponent, parent):
    html, rows = resolution(base, exponent, parent)
    rows[2]["state"] = 7
    result = build(html, rows)
    recovered = [n for n in result["nodes"] if n.get("structure_origin") == "html_recovery"]
    assert len(recovered) == 1
    new = recovered[0]
    old = next(n for n in result["nodes"] if n.get("source_id") == "r_c_old")
    assert new["number_canonical"] == f"{base}.{exponent + 1}"
    assert new["parent_address"] == old["parent_address"]
    assert not new.get("source_id") and new["recovery_evidence"]["html_id"] == "new"
    assert new["source_state"] is None and old["source_state"] == 7
    assert old["source_declared_span"]["char_end"] > old["source_span"]["char_end"]
    assert old["source_span"]["char_end"] == new["source_span"]["char_start"]
    assert all(n["parent_address"] == new["address"] for n in result["nodes"] if n["kind"] in {"image", "table"})
    assert next(n for n in result["nodes"] if n["kind"] == "note")["parent_address"] == new["address"]
    assert next(n for n in result["nodes"] if n.get("source_id") == "r_c_next")["source_structure_evidence"]["json_pointer"] == "/data/3"
    assert result["accounting"]["source_nodes"] == len(rows)
    assert result["accounting"]["recovered_nodes"] == 1
    assert not result["structural_issues"] and not result["unresolved_blocks"]
    assert result["structure_audit"]["critical_count"] == 0
    assert result["structure_audit"]["info_count"] == 1
    assert build(html, rows) == result


@pytest.mark.parametrize("marker", ["17.3.", "17<sup>4</sup>.", '"17<sup>3</sup>.', "18<sup>3</sup>.", "17<sup>x</sup>.", "17<sup>3a</sup>.", "17³."])
def test_uncertain_markers_are_reported_without_recovery(marker):
    html, rows = resolution(marker=marker)
    result = build(html, rows)
    assert not any(n.get("structure_origin") == "html_recovery" for n in result["nodes"])
    assert result["structure_audit"]["critical_count"] > 0


def test_form_context_is_inherited_through_source_sections():
    html, rows = resolution(parent="annex")
    rows[1]["caption"] += " (форма)"
    html = html.replace('<p id="old">', '<p id="formsection">Раздел IV. Сведения</p><p id="old">')
    for row in rows[2:]:
        row["id"] = row["id"].replace("r_c_", "r_c_sec_")
        row["lvl"] = 3
    rows.insert(2, {"id": "r_c_sec", "np": "formsection", "npe": "next", "unit": "раздел", "caption": "Раздел IV", "lvl": 2})
    result = build(html, rows)
    assert not any(n.get("structure_origin") == "html_recovery" for n in result["nodes"])


@pytest.mark.parametrize("context", ["form", "quote", "different_style", "inside_child", "collision"])
def test_recovery_refuses_conflicting_context(context):
    html, rows = resolution()
    if context == "form":
        html, rows = resolution(parent="annex")
        rows[1]["caption"] += " (форма)"
    elif context == "quote":
        html = html.replace("Первое условие.", 'В следующей редакции: "Текст')
        html = html.replace('id="last">Продолжение', 'id="last">Продолжение";')
    elif context == "different_style":
        html = html.replace('id="new"', 'id="new" class="C"')
    elif context == "inside_child":
        html = html.replace('id="new">', 'id="child">а) Подпункт.</p><p id="new">')
        rows.insert(3, {"id": "r_c_old_a", "np": "child", "npe": "last", "unit": "подпункт", "caption": 'подпункт "а"', "lvl": 3})
    else:
        html = html.replace('id="next">18.', 'id="next">17<sup>3</sup>.')
        rows[-1]["caption"] = "пункт 17<sup>3</sup>"
    result = build(html, rows)
    assert not any(n.get("structure_origin") == "html_recovery" for n in result["nodes"])
    if context not in {"form", "quote"}:
        assert result["structure_audit"]["critical_count"] > 0


@pytest.mark.parametrize("text", [
    '2<sup>1</sup>. Изложить в следующей редакции: "Текст нового положения";',
    '2<sup>1</sup>. Изложить в следующей редакции: "Термин" - это определение термина";',
])
def test_inline_amendment_payload_keeps_whole_paragraph_without_false_quote(text):
    html = HTML.replace('2<sup>1</sup>. Текст.', text)
    result = tree(html)
    assert not any(n["kind"] == "quote" for n in result["nodes"])
    assert not result["structural_issues"] and not result["unresolved_blocks"]
    assert any(f["code"] == "amendment_payload_preserved" for f in result["structure_audit"]["findings"])
    block = next(n for n in result["nodes"] if n.get("html_id") == "p1" and n.get("block_id") is not None)
    assert block["parent_address"].endswith("/part/2.1")


def test_inline_form_list_is_optional_granularity():
    html = HTML.replace('2<sup>1</sup>. Текст.', 'ПРИЛОЖЕНИЕ № 2<br>Приложение к заключению:<br>а) документы;<br>б) акт.')
    rows = [dict(ROWS[0]), {"id": "a1_form", "np": "p1", "npe": "end", "unit": "приложение", "caption": "ПРИЛОЖЕНИЕ № 2 (форма)", "lvl": 1}]
    result = tree(html, rows)
    assert not result["unresolved_blocks"] and not result["structural_issues"]
    assert len([f for f in result["structure_audit"]["findings"] if f.get("html_id") == "p1" and f["code"] == "form_content_preserved"]) == 2


def test_separate_quoted_term_definition_has_no_truncated_quote_node():
    html = HTML.replace('2<sup>1</sup>. Текст.', '2<sup>1</sup>. Изложить в следующей редакции:')
    html = html.replace('а) Первая строка.', '"Определение" - полное содержание определения;";')
    result = tree(html, ROWS[:2])
    assert not any(n["kind"] == "quote" for n in result["nodes"])
    assert not result["structural_issues"] and not result["unresolved_blocks"]
    assert result["accounting"]["exactly_once"]


def test_unclosed_inline_payload_remains_critical():
    html = HTML.replace('2<sup>1</sup>. Текст.', '2<sup>1</sup>. Изложить в следующей редакции: "Незакрытый текст.')
    result = tree(html, ROWS[:2])
    assert "unclosed_or_crossing_amendment_quote" in result["structural_issues"]
    assert result["unresolved_blocks"]
