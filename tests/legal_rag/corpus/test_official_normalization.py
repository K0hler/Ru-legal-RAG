import copy

import pytest

from legal_rag.corpus.official_structure import normalized_units


@pytest.mark.parametrize("label,number,display", [
    ("ОБЩАЯ ЧАСТЬ", None, None), ("ОСОБЕННАЯ ЧАСТЬ", None, None),
    ("ЧАСТЬ ПЕРВАЯ", "1", "ПЕРВАЯ"), ("ЧАСТЬ ШЕСТАЯ", "6", "ШЕСТАЯ"),
    ("ЧАСТЬ IV", "IV", "IV"),
])
def test_upper_parts_keep_their_explicit_number_or_name(label, number, display):
    html = f'<p id="part">{label}</p><p id="article">Статья 1. Условия</p><p id="end">Текст.</p>'
    rows = [{"id": "b", "np": "part", "npe": "end", "lvl": 0, "unit": "часть", "caption": label},
            {"id": "b_a1", "np": "article", "npe": "end", "lvl": 1, "unit": "статья", "caption": "Статья 1"}]
    units, checks, _ = normalized_units(html, rows, "code")
    assert units[0]["kind"] == "part"
    assert units[0]["number_canonical"] == number and units[0]["number_display"] == display
    assert units[0]["structural_role"] == "upper_division"
    assert units[1]["parent_source_id"] == "b"
    assert all(c["matches"] for c in checks)


@pytest.mark.parametrize("case", ["word_conflict", "unknown_word", "inside_article"])
def test_upper_part_support_does_not_relax_unknown_or_conflicting_parts(case):
    html = '<p id="part">ЧАСТЬ ВТОРАЯ</p><p id="end">Текст</p>'
    rows = [{"id": "b", "np": "part", "npe": "end", "lvl": 0, "unit": "часть", "caption": "ЧАСТЬ ПЕРВАЯ"}]
    if case == "unknown_word":
        html = html.replace("ВТОРАЯ", "НЕИЗВЕСТНАЯ")
        rows[0]["caption"] = "ЧАСТЬ НЕИЗВЕСТНАЯ"
    if case == "inside_article":
        html = '<p id="a">Статья 1</p>' + html.replace("ЧАСТЬ ВТОРАЯ", "ОБЩАЯ ЧАСТЬ")
        rows[0].update(id="a_b", lvl=1, caption="ОБЩАЯ ЧАСТЬ")
        rows.insert(0, {"id": "a", "np": "a", "npe": "end", "lvl": 0, "unit": "статья", "caption": "Статья 1"})
    with pytest.raises(ValueError):
        normalized_units(html, rows, "code")


@pytest.mark.parametrize("label", ["ПЕРЕЧЕНЬ необходимых мер", "ПОРЯДОК выполнения работ", "ТРЕБОВАНИЯ к объектам"])
def test_approved_container_uses_approval_and_matching_title(label):
    html = ('<p id="stamp">УТВЕРЖДЕН постановлением Правительства Российской Федерации</p>'
            f'<p class="T" id="title">{label}</p><p id="end">Содержание</p>')
    rows = [{"id": "z", "np": "stamp", "npe": "end", "lvl": 0, "unit": "вложение", "caption": label}]
    units, _, _ = normalized_units(html, rows, "government_resolution")
    assert units[0]["kind"] == "approved_text"
    assert units[0]["normalization_evidence"][0]["rule"] == "html-approved-container/1"


@pytest.mark.parametrize("case", ["no_approval", "different_title"])
def test_unknown_attachment_needs_real_approval_evidence(case):
    html = '<p id="stamp">УТВЕРЖДЕНО постановлением Правительства Российской Федерации</p><p class="T">ПЕРЕЧЕНЬ мер</p><p id="end">Текст</p>'
    if case == "no_approval":
        html = html.replace("УТВЕРЖДЕНО", "Справочная информация")
    else:
        html = html.replace("ПЕРЕЧЕНЬ мер", "ДРУГОЙ документ")
    rows = [{"id": "z", "np": "stamp", "npe": "end", "lvl": 0, "unit": "вложение", "caption": "ПЕРЕЧЕНЬ мер"}]
    with pytest.raises(ValueError):
        normalized_units(html, rows, "government_resolution")


@pytest.mark.parametrize("caption,kind", [("Примечание", "normative_note"), ("Примечания", "notes_section")])
def test_plain_note_container_keeps_normative_structure(caption, kind):
    html = f'<p id="n">{caption}.</p><p id="last">1. Содержание.</p>'
    rows = [{"id": "n", "np": "n", "npe": "last", "lvl": 0, "unit": "вложение", "caption": caption}]
    units, _, _ = normalized_units(html, rows, "code")
    assert units[0]["kind"] == kind


@pytest.mark.parametrize("letter,markup", [("б", "б"), ("з.1", "з<sup>1</sup>")])
def test_lettered_point_is_not_required_to_be_called_subpoint(letter, markup):
    html = f'<p id="a">Статья 1</p><p id="letter">{markup}) Условие</p>'
    rows = [{"id": "a1", "np": "a", "npe": "letter", "lvl": 0, "unit": "статья", "caption": "Статья 1"},
            {"id": "a1_b", "np": "letter", "npe": "letter", "lvl": 1, "unit": "пункт", "caption": f'пункт "{markup}"'}]
    units, checks, _ = normalized_units(html, rows, "code")
    assert units[1]["kind"] == "item" and units[1]["number_canonical"] == letter
    assert checks[1]["matches"]


def test_unprinted_article_parts_keep_verified_source_ordinals():
    html = '<p id="a">Статья 1</p><p id="first">Первое правило.</p><p id="second">Второе правило.</p>'
    rows = [{"id": "a1", "np": "a", "npe": "second", "lvl": 0, "unit": "статья", "caption": "Статья 1"},
            {"id": "a1_c1", "np": "first", "npe": "first", "lvl": 1, "unit": "часть", "caption": "часть 1"},
            {"id": "a1_c2", "np": "second", "npe": "second", "lvl": 1, "unit": "часть", "caption": "часть 2"}]
    units, _, _ = normalized_units(html, rows, "code")
    assert [n["number_canonical"] for n in units[1:]] == ["1", "2"]
    assert all(n["number_is_explicit"] is False and n["number_origin"] == "official_sidecar_ordinal" for n in units[1:])
    rows[1]["npe"] = "removed-end-anchor"
    units, _, _ = normalized_units(html, rows, "code")
    assert units[1]["html_end"] <= units[2]["html_start"]
    assert units[1]["source_declared_anchors"]["npe"] == "removed-end-anchor"
    rows[2]["caption"] = "часть 3"
    with pytest.raises(ValueError, match="ordinal"):
        normalized_units(html, rows, "code")


def test_note_heading_and_first_number_can_share_a_paragraph():
    html = '<p id="n">Примечания. 1. Первое правило.</p>'
    rows = [{"id": "n", "np": "n", "npe": "n", "lvl": 0, "unit": "вложение", "caption": "Примечания"},
            {"id": "n_p1", "np": "n", "npe": "n", "lvl": 1, "unit": "пункт", "caption": "пункт 1"}]
    units, checks, _ = normalized_units(html, rows, "code")
    assert units[1]["number_canonical"] == "1" and checks[1]["matches"]


def test_word_part_at_start_of_body_is_not_a_division_heading():
    html = '<p id="a">Статья 1</p><p id="p">Часть отпуска предоставляется позднее.</p>'
    rows = [{"id": "a", "np": "a", "npe": "p", "lvl": 0, "unit": "статья", "caption": "Статья 1"},
            {"id": "a_c1", "np": "p", "npe": "p", "lvl": 1, "unit": "часть", "caption": "часть 1"}]
    assert normalized_units(html, rows, "code")[0][1]["number_is_explicit"] is False


def range_fixture():
    html = ('<p id="a">ПРИЛОЖЕНИЕ № 4</p><p id="s">Раздел II. Формулы</p>'
            '<p id="p">2. Формула</p><p id="last">Продолжение</p>'
            '<p id="next">ПРИЛОЖЕНИЕ № 5</p><p id="end">Другое приложение</p>')
    rows = [{"id": "a4", "np": "a", "npe": "last", "lvl": 0, "unit": "приложение", "caption": "ПРИЛОЖЕНИЕ № 4"},
            {"id": "a4_s2", "np": "s", "npe": "end", "lvl": 1, "unit": "раздел", "caption": "Раздел II"},
            {"id": "a4_s2_p2", "np": "p", "npe": "last", "lvl": 2, "unit": "пункт", "caption": "пункт 2"},
            {"id": "a5", "np": "next", "npe": "end", "lvl": 0, "unit": "приложение", "caption": "ПРИЛОЖЕНИЕ № 5"}]
    return html, rows


def test_overlong_child_end_is_reconciled_at_confirmed_parent_boundary():
    html, rows = range_fixture()
    before = copy.deepcopy(rows)
    units, _, _ = normalized_units(html, rows, "government_resolution")
    assert units[1]["html_end"] == units[0]["html_end"]
    assert units[1]["source_declared_range"][1] > units[1]["html_end"]
    evidence = units[1]["normalization_evidence"][0]
    assert evidence["rule"] == "confirmed-parent-boundary/1" and evidence["next_html_id"] == "next"
    assert units[1]["source_row_index"] == 1 and rows == before


def test_missing_end_anchor_is_recovered_with_an_explicit_next_boundary():
    html, rows = range_fixture()
    rows[1]["npe"] = "removed-end-anchor"
    units, _, _ = normalized_units(html, rows, "government_resolution")
    assert units[1]["html_end"] == units[0]["html_end"]
    assert units[1]["source_declared_anchors"]["npe"] == "removed-end-anchor"
    assert "source_declared_range" not in units[1]


@pytest.mark.parametrize("case", ["no_next", "unknown_next", "gap", "missing_start"])
def test_missing_anchor_does_not_guess_unconfirmed_boundaries(case):
    html, rows = range_fixture()
    rows[1]["npe"] = "removed"
    if case == "no_next":
        rows.pop()
    elif case == "unknown_next":
        html = html.replace("ПРИЛОЖЕНИЕ № 5", "Справка")
    elif case == "gap":
        html = html.replace('<p id="next">', '<p>Неучтённый текст</p><p id="next">')
    else:
        rows[1]["np"] = "removed-start"
    with pytest.raises(ValueError):
        normalized_units(html, rows, "government_resolution")


@pytest.mark.parametrize("case", ["early_parent", "unmarked_next", "unassigned_gap", "image_gap", "empty_table_gap", "crossing_leaf", "wrong_prefix"])
def test_range_reconciliation_refuses_ambiguous_boundaries(case):
    html, rows = range_fixture()
    if case == "early_parent":
        rows[0]["npe"] = "a"
    elif case == "unmarked_next":
        html = html.replace("ПРИЛОЖЕНИЕ № 5", "Справочные материалы")
    elif case == "unassigned_gap":
        html = html.replace('<p id="next">', '<p>Неучтённое правило</p><p id="next">')
    elif case == "image_gap":
        html = html.replace('<p id="next">', '<img src="formula.png"><p id="next">')
    elif case == "empty_table_gap":
        html = html.replace('<p id="next">', '<table><tr><td></td></tr></table><p id="next">')
    elif case == "crossing_leaf":
        rows[2]["npe"] = "end"
    else:
        rows[1]["id"] = "other"
    with pytest.raises(ValueError):
        normalized_units(html, rows, "government_resolution")
