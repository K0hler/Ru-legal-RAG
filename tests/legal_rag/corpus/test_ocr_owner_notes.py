"""Authored controls for source references, running text and mislabelled notes."""

import copy

import pytest

from legal_rag.corpus import ocr_owner_structure as S
from test_ocr_logical_structure import conts, extraction, owners


@pytest.mark.parametrize("tail,head", [
    ('1. Требования установлены постановлением Правительства от 10.02.2024 № 42',
     '"О правилах ведения учета".'),
    ('1. Проверка проводится в соответствии со статьей 16',
     'Федерального закона "О контроле".'),
    ('1. Изменения утверждены постановлением от',
     '22.03.2024 № 38 (зарегистрировано 11.04.2024).'),
])
def test_explicit_legal_reference_continues_at_next_page_start(tail, head):
    source = extraction([[('Text', tail)], [('Page-header', '2'), ('Text', head)]])
    before = copy.deepcopy(source)
    result = S.build(source)
    assert conts(result)['2.1'] is True
    assert owners(result)['2.1'] == 'A/1'
    assert source == before


@pytest.mark.parametrize("tail,head", [
    ('1. Проверка по статье 16 завершена.', 'Федерального закона "О контроле".'),
    ('1. Заполняется строка 16', 'Федерального закона "О контроле".'),
    ('1. Название документа указано', '"О правилах ведения учета".'),
    ('1. Дата отчета', '22.03.2024 № 38 (зарегистрировано 11.04.2024).'),
])
def test_capital_reference_start_requires_an_explicit_unfinished_reference(tail, head):
    result = S.build(extraction([[('Text', tail)], [('Page-header', '2'), ('Text', head)]]))
    assert conts(result)['2.1'] is False


def test_unmarked_act_reference_continues_its_unfinished_standard_title():
    source = extraction([
        [('Text', '1. Отменить следующие документы:'),
         ('Text', 'постановление государственного органа от 10.02.2024 № 42 «Об утверждении')],
        [('Page-header', '2'),
         ('Text', 'СанПиН 9.8.7654-24 «Санитарные требования» (зарегистрировано 12.03.2024);')],
    ])
    result = S.build(source)
    assert conts(result)['2.1'] is True
    assert owners(result)['2.1'] == 'A/1'


def test_decimal_reference_list_continues_after_its_trailing_comma():
    source = extraction([
        [('Text', '1.3. Требования установлены пунктами 2.1.1, 2.3.4 (абзац первый), 2.4.9,')],
        [('Page-header', '2'), ('Text', '2.4.10, 2.4.11 (абзац второй) для всех организаций.')],
    ])
    result = S.build(source)
    assert conts(result)['2.1'] is True
    assert owners(result)['2.1'] == 'A/1.3'


@pytest.mark.parametrize('tail,head', [
    ('1. Перечень значений: 2.1, 2.4,', '2.5, 2.6 указаны в таблице.'),
    ('1. Требования установлены пунктами 2.1.1, 2.4.9.', '2.4.10, 2.4.11 приведены ниже.'),
    ('постановление государственного органа от 10.02.2024 № 42 «Об утверждении»;',
     'СанПиН 9.8.7654-24 «Санитарные требования».'),
    ('1. Пример «Об утверждении', 'СанПиН 9.8.7654-24 «Санитарные требования».'),
])
def test_numeric_list_or_standard_title_needs_an_unfinished_legal_reference(tail, head):
    result = S.build(extraction([[('Text', tail)], [('Page-header', '2'), ('Text', head)]]))
    assert conts(result)['2.1'] is False


@pytest.mark.parametrize('note', ['6 статья 5 технического регламента.', '6. Статья 5 технического регламента.'])
def test_plain_footnote_number_accepts_lowercase_and_number_dot(note):
    result = S.build(extraction([[('Text', '1. Пищевая продукция соответствует требованиям⁶.'),
                                  ('Text', '2. Прочие требования.'), ('Footnote', note)]]))
    assert owners(result)['1.2'] == 'A/1'


def bottom_notes_source():
    source = extraction([
        [('Text', '1. Проверка соответствует требованиям¹⁷,'),
         ('Footnote', '17. Регламент принят решением (Собрание')],
        [('Page-header', '2'), ('Text', 'изложенным в приложении.'),
         ('Text', '2. Сведения об ингредиентах¹⁸ должны быть доступны.'),
         ('Text', '3. Другое завершенное требование.'),
         ('Text', 'законодательства Российской Федерации, 2024, № 2).'),
         ('Text', '18 Подпункт 3 технического регламента.')],
    ])
    source['pages'][0]['regions'][1]['bbox'] = [180, 2000, 1400, 2150]
    source['pages'][1]['regions'][4]['bbox'] = [180, 2000, 1400, 2100]
    source['pages'][1]['regions'][5]['bbox'] = [180, 2110, 1400, 2150]
    return source


def test_bottom_text_continues_open_citation_note_and_opens_marked_next_note():
    source = bottom_notes_source()
    before = copy.deepcopy(source)
    result = S.build(source)
    got = owners(result)
    assert got['1.1'] == got['2.4'] == 'A/1'
    assert conts(result)['2.4'] is True
    assert got['2.5'] == 'A/2'
    assert conts(result)['2.5'] is False
    assert got['2.3'] == 'A/3'
    assert source == before


@pytest.mark.parametrize('change', ['no_reference', 'not_at_bottom', 'closed_note'])
def test_text_note_inference_requires_a_local_reference_and_bottom_citation(change):
    source = bottom_notes_source()
    if change == 'no_reference':
        block = source['blocks'][4]
        block['original_text'] = '2. Сведения об ингредиентах должны быть доступны.'
        token = next(t for t in source['text_nodes'] if t['text_node_id'] == block['text_node_ids'][0])
        token['raw_text'] = block['original_text']
    elif change == 'not_at_bottom':
        source['pages'][1]['regions'][4]['bbox'] = [180, 400, 1400, 450]
        source['pages'][1]['regions'][5]['bbox'] = [180, 460, 1400, 500]
    else:
        block = source['blocks'][1]
        block['original_text'] = '17. Источник завершен.'
        token = next(t for t in source['text_nodes'] if t['text_node_id'] == block['text_node_ids'][0])
        token['raw_text'] = block['original_text']
    result = S.build(source)
    assert conts(result)['2.4'] is False
    assert owners(result)['2.4'] == 'A/3'
    if change != 'closed_note':
        assert owners(result)['2.5'] == 'A/3'


@pytest.mark.parametrize('text', ['7623401', '7623401.doc', 'Рекомендуемый образец'])
def test_repeated_source_codes_and_sample_captions_remain_content(text):
    category = 'Page-header' if text == 'Рекомендуемый образец' else 'Page-footer'
    source = extraction([[(category, text), ('Text', f'{i}. Требование.')]
                         for i in range(1, 5)])
    result = S.build(source)
    assert all(r['role'] == 'content' for r in result['regions'])
    if category == 'Page-footer':
        assert all(owners(result)[f'{i}.0'] == 'A' for i in range(1, 5))


def test_page_numbers_and_repeated_running_title_stay_noise():
    source = extraction([[('Page-header', str(i)), ('Page-footer', 'Издание органа власти'),
                          ('Text', f'{i}. Требование.')]
                         for i in range(1, 5)])
    result = S.build(source)
    assert all(r['role'] == 'noise' for r in result['regions'] if r['category'].startswith('Page-'))


def test_quoted_contract_fields_and_signatures_keep_the_amending_point():
    source = extraction([[
        ('Text', '1. Форму договора изложить в следующей редакции:'),
        ('Text', '"ДОГОВОР'),
        ('Text', '1. Получатель заполняет сведения.'),
        ('Text', '____________________________'),
        ('Text', '(номер и дата документа)'),
        ('Text', '2. Получатель подтверждает условия.'),
        ('Text', 'Подписи и реквизиты Сторон'),
        ('Text', '____________________________'),
        ('Text', 'М.П. (при наличии)".'),
        ('Text', 'Председатель Правительства'),
        ('Text', 'А.А.Иванов'),
    ]])
    before = copy.deepcopy(source)
    result = S.build(source)
    got = owners(result)
    assert [got[f'1.{k}'] for k in [1, 2, 4, 5, 6, 8]] == ['A/1'] * 6
    # A standalone rule keeps its document owner without moving later quoted text.
    assert got['1.3'] == got['1.7'] == 'A'
    assert got['1.9'] == got['1.10'] == 'A'
    assert source == before


@pytest.mark.parametrize('note', [
    '* Условие относится к указанным значениям".',
    '** При изменении сведений направляется уведомление".',
])
def test_separator_before_quoted_explanatory_note_does_not_end_its_point(note):
    source = extraction([[
        ('Text', '1. Приложение изложить в следующей редакции:'),
        ('Text', '"ФОРМА ОТЧЕТА'),
        ('Table', '<table><tr><td>Сведения*</td><td>Значение**</td></tr></table>'),
        ('Text', '____________________________'),
        ('Text', note),
        ('Text', '____________'),
    ]])
    before = copy.deepcopy(source)
    result = S.build(source)
    got = owners(result)
    assert got['1.2'] == got['1.4'] == 'A/1'
    assert got['1.3'] == 'A'
    assert got['1.5'] == 'A'
    assert source == before


def test_unquoted_blank_after_last_point_still_opens_the_requisite_block():
    result = S.build(extraction([[
        ('Text', '1. Последнее требование.'),
        ('Text', '____________________________'),
        ('Text', 'Председатель Правительства'),
    ]]))
    assert owners(result) == {'1.0': 'A/1', '1.1': 'A', '1.2': 'A'}


def test_quoted_field_before_next_outer_point_keeps_its_owner_and_table():
    result = S.build(extraction([[
        ('Text', '1. Форму изложить в следующей редакции:'),
        ('Text', '"ФОРМА'),
        ('Text', '____________________________'),
        ('Table', '<table><tr><td>Сведения заявителя</td></tr></table>'),
        ('Text', 'Сведения подтверждены".'),
        ('Text', '2. Установить другое требование.'),
    ]]))
    got = owners(result)
    assert got['1.2'] == got['1.3'] == got['1.4'] == 'A/1'
    assert got['1.5'] == 'A/2'
