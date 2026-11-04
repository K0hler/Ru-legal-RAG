"""Quoted amendment payloads keep their paragraph and explicit footnote owner."""
import copy

import pytest

from legal_rag.corpus import ocr_owner_structure as S
from test_ocr_logical_structure import conts, extraction, owners


def test_open_quoted_list_continues_after_semicolon_on_next_page():
    source = extraction([[('Text', '1. В строке заменить значения:'),
                          ('Text', 'в графе слова «не установлено» заменить словами «горох – 1;')],
                         [('Page-header', '2'), ('Text', 'нут – 2; соя – 3».'),
                          ('Text', '2. Следующее изменение.')]])
    before = copy.deepcopy(source)
    result = S.build(source)
    assert conts(result)['2.1'] is True
    assert owners(result)['2.1'] == 'A/1'
    assert source == before


@pytest.mark.parametrize('tail,intervening', [
    ('перечень: горох – 1;', []),
    ('перечень «горох – 1»;', []),
    ('перечень «горох – 1;', [('Table', '<table><tr><td>Данные</td></tr></table>')]),
])
def test_semicolon_without_an_uninterrupted_open_quote_does_not_join(tail, intervening):
    source = extraction([[('Text', '1. Перечень значений:'), ('Text', tail), *intervening],
                         [('Page-header', '2'), ('Text', 'нут – 2; соя – 3».')]])
    assert conts(S.build(source))['2.1'] is False


def test_second_quoted_replacement_footnote_uses_the_explicit_introducing_point():
    source = extraction([[('Text', '1. Сноски 2 и 3 к пункту 4 изложить в следующей редакции:'),
                          ('Text', '«² Новое содержание первой сноски.'),
                          ('Footnote', '³ Новое содержание второй сноски.».'),
                          ('Text', '2. Следующее изменение.')]])
    before = copy.deepcopy(source)
    result = S.build(source)
    assert owners(result)['1.2'] == 'A/1'
    paragraph = next(p for p in result['paragraphs'] if p['regions'][0]['index'] == 2)
    assert any(e.get('footnote_owner') == 'quoted_replacement' for e in paragraph['evidence'])
    assert source == before


@pytest.mark.parametrize('intro,payload,intervening', [
    ('1. Сноску 2 к пункту 4 изложить в следующей редакции:', '«² Первая сноска.', []),
    ('1. Сноски 2 и 3 к пункту 4 изложить в следующей редакции:', '«² Первая сноска».', []),
    ('1. Сноски 2 и 3 к пункту 4 изложить в следующей редакции:', '«² Первая сноска.',
     [('Text', '2. Самостоятельное следующее изменение.')]),
])
def test_replacement_owner_requires_the_named_number_and_its_open_quotation(intro, payload, intervening):
    result = S.build(extraction([[('Text', intro), ('Text', payload), *intervening,
                                 ('Footnote', '³ Вторая сноска.')]]))
    note = result['paragraphs'][-1]
    assert not any(e.get('footnote_owner') == 'quoted_replacement' for e in note['evidence'])
