"""Source-bound inserted peers, editorial notes and explicit heading boundaries."""
import copy

import pytest

from legal_rag.corpus import ocr_owner_structure as S
from test_ocr_logical_structure import extraction, owners


def test_inserted_parenthesised_peer_closes_the_preceding_letter_list():
    source = extraction([[('Text', t) for t in [
        'Статья 8. Требования', '1) первый перечень:', 'а) один;', 'б) два;',
        'в) три;', 'г) четыре;', '1¹) вставленный пункт;', '2) следующий пункт;', '3) последний пункт.',
    ]]])
    before = copy.deepcopy(source)
    got = owners(S.build(source))
    assert got['1.6'] == 'A/ст8/1¹'
    assert got['1.7'] == 'A/ст8/2' and got['1.8'] == 'A/ст8/3'
    assert source == before


@pytest.mark.parametrize('explicit_part, expected', [(False, 'A/ст8'), (True, 'A/ст8/ч1')])
def test_part_editorial_note_keeps_the_article_when_part_number_is_unprinted(explicit_part, expected):
    intro = '1. Перечень включает:' if explicit_part else 'Перечень включает:'
    result = S.build(extraction([[('Text', t) for t in [
        'Статья 8. Требования', intro, '1) первый пункт;', '2) второй пункт.',
        '(Часть в редакции Федерального закона от 01.01.2020 № 1-ФЗ)',
    ]]]))
    assert owners(result)['1.4'] == expected


def test_two_terminal_closing_quotes_do_not_open_a_new_amendment_quote():
    result = S.build(extraction([[('Text', t) for t in [
        'Статья 6', '1) изменить положения:', 'б) изложить в следующей редакции:',
        '"5. Решение принимается по пунктам "а" и "б" и пункту "в".";";',
        '2) дополнить следующее положение.', 'Требование сохраняется.',
    ]]]))
    assert owners(result)['1.4'] == 'A/ст6/2'
    assert owners(result)['1.5'] == 'A/ст6'


def test_note_naming_a_point_does_not_use_the_unnumbered_part_fallback():
    result = S.build(extraction([[('Text', t) for t in [
        'Статья 8. Доходы', 'Доходы по правилам пункта 3 настоящей статьи:',
        '1) первый доход;', '(Пункт в редакции Федерального закона от 01.01.2020 № 1-ФЗ)',
        '2) второй доход.',
    ]]]))
    assert owners(result)['1.3'] == 'A/ст8/1'


def test_quoted_punctuation_literal_does_not_close_the_outer_amendment():
    result = S.build(extraction([[('Text', t) for t in [
        'Статья 6', '1) изложить в следующей редакции:',
        '\"5. Знак конца предложения обозначается символом \".\";',
        '6. Применяются другие символы.\";', '2) Изменить следующее положение.',
    ]]]))
    assert owners(result)['1.3'] == 'A/ст6/1'


def test_word_numbered_section_keeps_the_explicit_outer_code_part():
    result = S.build(extraction([[
        ('Section-header', 'ЧАСТЬ ПЕРВАЯ. Общие положения'),
        ('Section-header', 'Статья 8'), ('Text', '1. Последнее правило.'),
        ('Section-header', 'РАЗДЕЛ ВТОРОЙ'), ('Text', '1. Новое правило.'),
    ]]))
    assert owners(result)['1.3'] == 'A/разд1'
    assert owners(result)['1.4'] == 'A/разд1/1'


@pytest.mark.parametrize('heading', ['РАЗДЕЛ ВТОРОЙ', 'РАЗДЕЛ ТРЕТИЙ. Дополнительные положения'])
def test_explicit_word_numbered_section_closes_the_previous_article(heading):
    source = extraction([[('Section-header', 'Статья 8'), ('Text', '1. Последнее правило.'),
                          ('Section-header', heading), ('Text', '1. Новое правило.'),
                          ('Text', '2. Следующее правило.')]])
    before = copy.deepcopy(source)
    got = owners(S.build(source))
    assert got['1.2'] == 'A'
    assert got['1.3'] == 'A/1' and got['1.4'] == 'A/2'
    assert source == before


def test_word_numbered_section_reference_in_body_does_not_reset_the_article():
    result = S.build(extraction([[('Section-header', 'Статья 8'), ('Text', '1. Правило.'),
                                  ('Text', 'Раздел второй договора применяется при проверке.')]]))
    assert owners(result)['1.2'] == 'A/ст8/ч1'


def test_centred_conclusion_after_narrative_chapters_returns_to_document_root():
    source = extraction([[('Section-header', 'Глава 1. Описание'), ('Text', '1.1. Исходные данные'),
                          ('Text', 'Описание завершено.'), ('Text', 'Заключение', 500),
                          ('Text', 'Итоговые выводы изложены здесь.')]])
    got = owners(S.build(source))
    assert got['1.3'] == got['1.4'] == 'A'


@pytest.mark.parametrize('article, centred', [(True, True), (False, False)])
def test_conclusion_word_without_narrative_heading_context_keeps_the_unit(article, centred):
    middle = [('Section-header', 'Статья 8'), ('Text', '1. Правило.')] if article else [('Text', '1.1. Описание')]
    result = S.build(extraction([[('Section-header', 'Глава 1. Положения'), *middle,
                                  ('Text', 'Заключение', 500 if centred else 180)]]))
    got = owners(result)
    assert got[f'1.{len(middle) + 1}'] == got[f'1.{len(middle)}']
