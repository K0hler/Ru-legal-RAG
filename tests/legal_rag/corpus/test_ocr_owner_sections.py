"""Source-numbered section boundaries and malformed numbering cannot cascade."""
import copy

from legal_rag.corpus import ocr_owner_structure as S
from test_ocr_logical_structure import extraction, owners


def test_numeric_section_followed_by_roman_sections_keeps_printed_number():
    source = extraction([[('Section-header', '1. Область применения'),
                          ('Text', '1.1. Настоящие правила применяются.'),
                          ('Text', '1.12. Последнее правило.'),
                          ('Section-header', 'II. Общие требования'), ('Text', '2.1. Другое правило.'),
                          ('Section-header', 'III. Специальные требования'), ('Text', '3.1. Последнее правило.')]])
    before = copy.deepcopy(source)
    result = S.build(source)
    assert owners(result) == {'1.0': 'A/разд1', '1.1': 'A/разд1/1.1', '1.2': 'A/разд1/1.12',
                              '1.3': 'A/II', '1.4': 'A/II/2.1', '1.5': 'A/III', '1.6': 'A/III/3.1'}
    assert result['paragraphs'][0]['marker'] == ['roman', 'разд1']
    assert source == before


def test_a_numbered_point_is_not_promoted_without_heading_and_section_sequence():
    for category, text, following in [('Text', '1. Пункт о применении.', 'II. Следующая глава'),
                                      ('Section-header', '1. Общие требования', '2. Обычный пункт.')]:
        result = S.build(extraction([[(category, text), ('Text', '1.1. Детали.'), ('Section-header', following)]]))
        assert result['paragraphs'][0]['marker'] == ['int', '1']


def test_a_styled_point_inside_an_established_section_is_not_a_new_section():
    result = S.build(extraction([[('Section-header', 'I. Общие положения'),
                                 ('Section-header', '1. Термины и определения'),
                                 ('Text', '1.1. Содержание первого термина.'),
                                 ('Section-header', 'II. Особенности применения'),
                                 ('Text', '2.1. Другое правило.')]]))
    assert owners(result) == {'1.0': 'A/I', '1.1': 'A/I/1', '1.2': 'A/I/1/1.1',
                              '1.3': 'A/II', '1.4': 'A/II/2.1'}


def test_repeated_footer_approval_captions_still_open_attached_documents():
    caption = 'УТВЕРЖДЕН постановлением Правительства Российской Федерации от 01.02.2024 № 12'
    result = S.build(extraction([[('Text', '1. Утвердить прилагаемые правила.'), ('Page-footer', caption)],
                                 [('Text', '1. Первое правило.'), ('Page-footer', caption)],
                                 [('Text', '1. Второе правило.')]]))
    assert owners(result)['2.0'] == 'S/1'
    assert owners(result)['3.0'] == 'S2/1'


def test_repeated_decimal_number_is_a_peer_and_an_orphan_does_not_nest_in_it():
    result = S.build(extraction([[('Section-header', 'III. Требования'),
                                 ('Text', '3.15. При размещении соблюдаются требования:'),
                                 ('Text', 'Требование о размещении.'),
                                 ('Text', '3.15. При мероприятиях соблюдаются требования:'),
                                 ('Text', '3.16.1. Организация информирует уполномоченный орган.')]]))
    actual = owners(result)
    assert actual['1.1'] == actual['1.3'] == 'A/III/3.15'
    assert actual['1.4'] == 'A/III/3.16.1'
    assert all(p['marker'][1] == '3.15' for p in result['paragraphs'] if p['marker'] and p['marker'][1] == '3.15')


def test_kept_file_footer_does_not_break_a_quote_introduced_before_the_page_end():
    result = S.build(extraction([[('Text', '1. Приложение изложить в следующей редакции:'),
                                  ('Page-footer', '1234567.doc')],
                                 [('Text', '"Приложение № 3 к Правилам'), ('Text', 'Текст новой редакции.".')]]))
    assert owners(result)['2.0'] == owners(result)['2.1'] == 'A/1'
    assert owners(result)['1.1'] == 'A'


def test_file_footers_do_not_consume_the_quote_safety_budget(monkeypatch):
    from legal_rag.corpus._ocr_owner import scopes
    monkeypatch.setattr(scopes, 'QUOTE_MAX_PARAGRAPHS', 3)
    result = S.build(extraction([[('Text', '1. Приложения изложить в следующей редакции:'),
                                  ('Section-header', '"ПРИЛОЖЕНИЕ № 6 к Правилам'),
                                  ('Page-footer', '1234567.doc')],
                                 [('Text', 'Первая часть текста.'), ('Page-footer', '1234567.doc')],
                                 [('Text', 'Вторая часть текста.'),
                                  ('Section-header', 'ПРИЛОЖЕНИЕ № 7 к Правилам'),
                                  ('Text', 'Последняя часть текста.";')]]))
    assert owners(result)['3.1'] == 'A/1'
