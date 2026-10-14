"""Authored cross-act controls for the shared native legal grammar."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from legal_rag.corpus.native_text import extract_native, native_tree  # noqa: E402


def document(title="Об учебном примере", number="731-ФЗ", day="14", month="марта"):
    return f"""<html><body><p>РОССИЙСКАЯ ФЕДЕРАЦИЯ</p>
<p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p><p>{title}</p>
<p>Глава 1. Учебная глава</p><p>Статья 1. Учебная статья</p>
<p>1. Часть.</p><p>1) Пункт.</p><p>а) Подпункт.</p>
<p>Продолжение подпункта.</p>
<p>Статья 2<sup>1</sup>. Дополнительная статья</p>
<p>1<sup>2</sup>. Дополнительная часть.</p>
<p>Президент Российской Федерации</p><p>{day} {month} 2020 года</p>
<p>№ {number}</p></body></html>"""


def native(html, claim):
    payload = json.dumps({"redtext": html, "error": None}).encode()
    asset = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "role": "consolidated",
        "declared_identity": claim,
        "evidence": {"locator": "/redtext"},
    }
    return native_tree(asset, extract_native(asset, payload))


@pytest.mark.parametrize(
    "title,number,date,day,month",
    [
        ("Об учебном примере", "731-ФЗ", "14.03.2020", "14", "марта"),
        ("О другом учебном примере", "912-ФЗ", "09.06.2020", "9", "июня"),
    ],
)
def test_same_native_profile_accepts_different_consistent_identities(
    title, number, date, day, month
):
    claim = f'Федеральный закон от {date} № {number} "{title}"'
    tree = native(document(title, number, day, month), claim)
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    assert not tree["unresolved_blocks"]
    nodes = {n["address"]: n for n in tree["nodes"]}
    assert nodes["act/article/1"]["parent_address"] == "act/chapter/1"
    assert nodes["act/article/2.1/part/1.2"]["parent_address"] == "act/article/2.1"
    assert (
        nodes["act/article/1/part/1/item/1/subitem/а/paragraph/1"]["kind"]
        == "paragraph"
    )


def test_conflicting_claim_cannot_be_repaired_by_body_reference():
    html = document().replace("1. Часть.", "1. Ссылка на № 732-ФЗ.")
    tree = native(html, 'Федеральный закон от 14.03.2020 № 732-ФЗ "Об учебном примере"')
    assert tree["identity_decision"]["status"] == "unresolved"
    assert not tree["nodes"]


def test_decimal_item_uses_the_same_grammar_as_superscript_item():
    claim = 'Федеральный закон от 14.03.2020 № 731-ФЗ "Об учебном примере"'
    tree = native(document().replace("1) Пункт.", "1.1) Пункт."), claim)
    assert any(n["address"] == "act/article/1/part/1/item/1.1" for n in tree["nodes"])
    assert not tree["unresolved_blocks"]


def test_portal_heading_class_does_not_turn_identity_header_into_unknown_provision():
    claim = 'Федеральный закон от 14.03.2020 № 731-ФЗ "Об учебном примере"'
    html = document().replace("<p>ФЕДЕРАЛЬНЫЙ ЗАКОН", '<p class="H">ФЕДЕРАЛЬНЫЙ ЗАКОН')
    tree = native(html, claim)
    assert not tree["unresolved_blocks"]
    assert any(
        n["kind"] == "header" and n["text"] == "ФЕДЕРАЛЬНЫЙ ЗАКОН"
        for n in tree["nodes"]
    )


@pytest.mark.parametrize(
    "title,number,date,day,month",
    [
        ("Учебный кодекс Российской Федерации", "721-ФЗ", "14.03.2020", "14", "марта"),
        ("Другой кодекс Российской Федерации", "932-ФЗ", "09.06.2020", "9", "июня"),
    ],
)
def test_code_profile_retains_hierarchy_superscripts_and_both_adapter_spans(
    title, number, date, day, month
):
    from legal_rag.corpus.housing_html import build_tree, extract_html, validate

    html = document(title, number, day, month).replace("<p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>", "")
    html = html.replace(
        "<p>Глава", "<p>РАЗДЕЛ III<sup>1</sup> Учебный раздел</p><p>Глава"
    )
    claim = f'Кодекс Российской Федерации от {date} № {number} "{title}"'
    raw = extract_html(html.encode())
    raw_tree = build_tree(raw, claim)
    native_result = native(html, claim)
    assert not raw_tree["unresolved_blocks"]
    assert raw_tree["accounting"]["exactly_once"]
    assert validate(raw, raw_tree, html.encode())["structure_complete"]
    assert [(n["address"], n["parent_address"]) for n in raw_tree["nodes"]] == [
        (n["address"], n["parent_address"]) for n in native_result["nodes"]
    ]
    nodes = {n["address"]: n for n in raw_tree["nodes"]}
    assert nodes["act/chapter/1"]["parent_address"] == "act/section/III.1"
    assert nodes["act/article/2.1"]["number_components"] == {
        "base": "2",
        "superscript": "1",
    }
    for token in raw["text_nodes"]:
        span = token["source_span"]
        assert html[span["char_start"] : span["char_end"]] == token["raw_text"]


def test_textual_editorial_note_is_separate_from_normative_paragraphs():
    html = document().replace(
        "<p>1) Пункт.", "<p>(В редакции учебного закона)</p><p>1) Пункт."
    )
    claim = 'Федеральный закон от 14.03.2020 № 731-ФЗ "Об учебном примере"'
    tree = native(html, claim)
    note = next(n for n in tree["nodes"] if n["text"] == "(В редакции учебного закона)")
    assert note["kind"] == "note"
    assert note["parent_address"] == "act"
    assert note["scope_status"] == "unresolved"


def test_textual_table_boundary_stops_provision_targeting():
    html = document().replace(
        "<p>1) Пункт.",
        "<p>Таблица 1. Значения</p><p>2. Строка таблицы.</p><p>1) Пункт.",
    )
    claim = 'Федеральный закон от 14.03.2020 № 731-ФЗ "Об учебном примере"'
    tree = native(html, claim)
    assert any(b["text"] == "Таблица 1. Значения" for b in tree["unresolved_blocks"])
    assert any(b["text"] == "2. Строка таблицы." for b in tree["unresolved_blocks"])
    assert not any(n["address"] == "act/article/1/part/2" for n in tree["nodes"])


def test_hyphenated_superscript_is_preserved_without_guessing_decimal_numbers():
    html = document().replace("2<sup>1</sup>", "2<sup>1-1</sup>")
    claim = 'Федеральный закон от 14.03.2020 № 731-ФЗ "Об учебном примере"'
    tree = native(html, claim)
    assert not tree["unresolved_blocks"]
    article = next(n for n in tree["nodes"] if n["address"] == "act/article/2.1-1")
    assert article["number_components"] == {"base": "2", "superscript": "1-1"}
    assert article["number_display"] == "2¹-¹"
    assert any(n["address"] == "act/article/2.1-1/part/1.2" for n in tree["nodes"])


def test_roman_chapter_and_decorative_title_case_use_the_same_code_profile():
    title = "Учебный кодекс Российской Федерации"
    html = (
        document(title)
        .replace("<p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>", "")
        .replace(title, title.upper())
    )
    html = html.replace("Глава 1.", "Глава IV.1.")
    claim = f'Кодекс Российской Федерации от 14.03.2020 № 731-ФЗ "{title}"'
    tree = native(html, claim)
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    assert not tree["unresolved_blocks"]
    assert (
        next(n for n in tree["nodes"] if n["kind"] == "article")["parent_address"]
        == "act/chapter/IV.1"
    )


def test_invalid_hyphen_component_stops_targeting():
    html = document().replace("1. Часть.", "1-0. Недопустимая нумерация.")
    claim = 'Федеральный закон от 14.03.2020 № 731-ФЗ "Об учебном примере"'
    tree = native(html, claim)
    assert any(b["reason"] == "unknown_numbering" for b in tree["unresolved_blocks"])
    assert not any(n["kind"] == "item" for n in tree["nodes"])


def test_uppercase_roman_chapter_is_a_boundary_before_the_first_article():
    title = "Учебный кодекс Российской Федерации"
    html = document(title).replace("<p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>", "")
    html = html.replace("Глава 1.", "ГЛАВА IV.")
    claim = f'Кодекс Российской Федерации от 14.03.2020 № 731-ФЗ "{title}"'
    tree = native(html, claim)
    assert not tree["unresolved_blocks"]
    assert (
        next(n for n in tree["nodes"] if n["kind"] == "chapter")["address"]
        == "act/chapter/IV"
    )


def test_heading_punctuation_does_not_change_section_or_chapter_level():
    title = "Учебный кодекс Российской Федерации"
    html = document(title).replace("<p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>", "")
    html = html.replace("<p>Глава 1.", "<p>Раздел I. Учебный раздел</p><p>Глава IV")
    claim = f'Кодекс Российской Федерации от 14.03.2020 № 731-ФЗ "{title}"'
    tree = native(html, claim)
    assert not tree["unresolved_blocks"]
    assert (
        next(n for n in tree["nodes"] if n["kind"] == "chapter")["parent_address"]
        == "act/section/I"
    )
    assert (
        next(n for n in tree["nodes"] if n["kind"] == "article")["parent_address"]
        == "act/chapter/IV"
    )


@pytest.mark.parametrize(
    "boundary",
    ["ГЛАВА IV. Другая глава", "СТАТЬЯ 9. Другая статья", "§ 1. Другая группа"],
)
def test_uppercase_boundary_after_break_does_not_merge_into_a_part(boundary):
    html = document().replace("1. Часть.", f"1. Часть.<br/>{boundary}")
    claim = 'Федеральный закон от 14.03.2020 № 731-ФЗ "Об учебном примере"'
    tree = native(html, claim)
    assert any(
        b["reason"] == "multiple_provision_markers" for b in tree["unresolved_blocks"]
    )
    assert not any(n["kind"] == "item" for n in tree["nodes"])


def test_subchapter_numbers_are_scoped_to_their_chapter_and_parent_articles():
    title = "Учебный кодекс Российской Федерации"
    html = document(title).replace("<p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>", "")
    html = html.replace("<p>Статья 1.", "<p>§ 1. Первая группа</p><p>Статья 1.")
    html = html.replace(
        "<p>Статья 2",
        "<p>Глава 2. Другая глава</p><p>§ 1. Другая группа</p><p>Статья 2",
    )
    claim = f'Кодекс Российской Федерации от 14.03.2020 № 731-ФЗ "{title}"'
    tree = native(html, claim)
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    assert not tree["unresolved_blocks"]
    nodes = {n["address"]: n for n in tree["nodes"]}
    assert nodes["act/article/1"]["parent_address"] == "act/chapter/1/subchapter/1"
    assert nodes["act/article/2.1"]["parent_address"] == "act/chapter/2/subchapter/1"
    assert nodes["act/chapter/2/subchapter/1"]["parent_address"] == "act/chapter/2"


def test_code_identity_allows_type_word_before_its_subject():
    title = "Кодекс учебных процедур Российской Федерации"
    html = document(title).replace("<p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>", "")
    claim = f'Кодекс Российской Федерации от 14.03.2020 № 731-ФЗ "{title}"'
    tree = native(html, claim)
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    assert not tree["unresolved_blocks"]
