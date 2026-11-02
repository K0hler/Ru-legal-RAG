"""Authored controls for source classes exposed by official-tree sets2–5."""
import copy

import pytest

from legal_rag.corpus import ocr_owner_structure as parser
from test_ocr_logical_structure import extraction, owners


@pytest.mark.parametrize("text, kind, label", [
    ("4²⁻¹. Дополнительное правило.", "int", "4²⁻¹"),
    ("4²⁻¹) дополнительный пункт;", "paren", "4²⁻¹"),
    ("б²⁻¹) дополнительный подпункт;", "letter", "б²⁻¹"),
])
def test_compound_superscript_marker_keeps_the_whole_printed_index(text, kind, label):
    marker = parser.parse_marker(text, "Text")
    assert (marker.kind, marker.label) == (kind, label)


def test_compound_superscript_parent_keeps_its_children_and_ast_number():
    from legal_rag.corpus.ocr_owner_ast import build_owner_tree
    from test_ocr_structure import extraction as normalized, CLAIM
    text = [('Section-header', 'Статья 8'), '4. Предыдущее правило.',
            '4²⁻¹. Перечень требований:', '1) первое требование;',
            '2) второе требование.', '5. Следующее правило.']
    source = extraction([[('Text', t) if isinstance(t, str) else t for t in text]])
    before = copy.deepcopy(source)
    got = owners(parser.build(source))
    assert got['1.2'] == 'A/ст8/ч4²⁻¹'
    assert got['1.3'] == 'A/ст8/ч4²⁻¹/1'
    assert got['1.5'] == 'A/ст8/ч5'
    assert source == before
    tree = build_owner_tree(normalized(text), CLAIM, 'original')
    unit = next(n for n in tree['nodes'] if n.get('marker_label') == '4²⁻¹')
    assert unit['number_components'] == {'base': '4', 'superscript': '2-1'}
    assert unit['number_display'] == '4²⁻¹'


@pytest.mark.parametrize("marker", ["5.3¹", "5.3²⁻¹"])
def test_inserted_decimal_is_a_full_number_and_a_peer_of_the_base_point(marker):
    result = parser.build(extraction([[('Text', t) for t in [
        '5. Условия', '5.3. Перечень:', 'а) первое условие;',
        f'{marker}. Дополнительное условие.', '5.4. Следующее условие.',
    ]]]))
    assert owners(result)['1.3'] == f'A/5/{marker}'
    assert owners(result)['1.4'] == 'A/5/5.4'


def test_long_numeric_list_continues_past_999():
    result = parser.build(extraction([[('Text', t) for t in [
        '998. Первая запись.', '999. Вторая запись.', '1000. Третья запись.', '1001. Последняя запись.',
    ]]]))
    assert list(owners(result).values()) == ['A/998', 'A/999', 'A/1000', 'A/1001']


def test_editorial_note_glued_to_the_number_still_opens_its_point():
    result = parser.build(extraction([[('Text', t) for t in [
        '12. Предыдущее правило.', '13.(Пункт утратил силу)', '14. Следующее правило.',
    ]]]))
    assert owners(result)['1.1'] == 'A/13'


def test_styled_roman_heading_glued_to_uppercase_title_closes_the_previous_section():
    result = parser.build(extraction([[('Section-header', 'РАЗДЕЛ IV. Положения'),
        ('Text', '1. Последнее правило.'), ('Section-header', 'РАЗДЕЛ IV¹ТРЕБОВАНИЯ К ДЕЯТЕЛЬНОСТИ'),
        ('Text', '1. Новое правило.')]]))
    assert owners(result)['1.2'] == 'A/IV¹'
    assert owners(result)['1.3'] == 'A/IV¹/1'


@pytest.mark.parametrize("caption", [
    'ПРИЛОЖЕНИЕ к Правилам предоставления сведений ' + 'о требованиях к оценке ' * 18,
    'ПРИЛОЖЕНИЕ № 1 к стратегическому направлению развития ' + 'новых технологий ' * 6,
    'ПРИЛОЖЕНИЕ к проекту Соглашения о сотрудничестве ' + 'в области науки ' * 7,
], ids=['long-upper-reference', 'numbered-lower-reference', 'unnumbered-draft-reference'])
def test_long_explicit_annex_reference_opens_its_own_document(caption):
    result = parser.build(extraction([[('Text', t.strip()) for t in [
        '1. Утвердить Правила.', 'УТВЕРЖДЕНЫ постановлением Правительства Российской Федерации',
        'Правила предоставления сведений', '1. Основное правило.', caption,
        'Перечень показателей', '1. Показатель приложения.',
    ]]]))
    expected = 'S/AN1' if '№ 1' in caption else 'S/AN'
    assert owners(result)['1.4'] == expected
    assert owners(result)['1.6'] == expected + '/1'


def test_styled_conclusion_after_numbered_narrative_sections_returns_to_root():
    result = parser.build(extraction([[('Section-header', '3. Положение дел'),
        ('Section-header', '3.2. Достигнутые результаты'), ('Text', 'Рассмотренные вопросы завершены.'),
        ('Section-header', 'ЗАКЛЮЧЕНИЕ'), ('Text', 'Общие выводы изложены здесь.')]]))
    assert owners(result)['1.3'] == owners(result)['1.4'] == 'A'


def test_plain_date_with_an_earlier_inserted_index_is_body_not_a_footnote():
    source = extraction([[('Section-header', 'Статья 2'), ('Text', '4. Уточнить подпункт «ц¹».'),
                           ('Text', '1 апреля 2022 года')]])
    source['pages'][0]['regions'][-1]['bbox'][1:4:2] = [1900, 2000]
    result = parser.build(source)
    date = next(p for p in result['paragraphs'] if p['text_preview'] == '1 апреля 2022 года')
    assert date['flow'] == 'body' and date['owner'] == 'A'


def test_editorial_note_naming_a_point_closes_its_parenthesised_subpoints():
    result = parser.build(extraction([[('Text', t) for t in [
        '6¹. Перечень включает:', '1) первое условие;', '2) последнее условие.',
        '(Дополнение пунктом - Постановление от 01.01.2020 № 1)',
    ]]]))
    assert owners(result)['1.3'] == 'A/6¹'


def test_templated_agreement_closing_formula_and_signature_table_belong_to_root():
    pages = [[('Text', t) for t in [
        'Статья 2. Сроки', '1. Последнее условие.',
        'Совершено________"__"_________________199 г. в двух экземплярах.',
    ]]]
    pages.append([('Table', 'За Правительство первой стороны | За Правительство второй стороны')])
    result = parser.build(extraction(pages))
    got = owners(result)
    assert got['1.2'] == got['2.0'] == 'A'


@pytest.mark.parametrize('note', [False, True])
def test_centred_rubric_and_its_editorial_note_belong_to_the_enclosing_section(note):
    body = [('Section-header', 'II. Условия'), ('Text', '17. Предыдущее правило.'),
            ('Text', 'Учет рисков', 500)]
    if note:
        body.append(('Text', '(Наименование подраздела в редакции Постановления Правительства от 01.01.2020 № 1)'))
    body.append(('Text', '18. Новое правило.'))
    got = owners(parser.build(extraction([body])))
    assert got['1.2'] == 'A/II'
    if note:
        assert got['1.3'] == 'A/II'


def test_removed_range_keeps_its_numbers_in_text_without_opening_a_single_point():
    from legal_rag.corpus.ocr_owner_ast import build_owner_tree
    from test_ocr_structure import extraction as normalized, CLAIM
    text = [('Section-header', 'III. Условия'), '13. Действующее правило.',
            '14. - 61. (Пункты утратили силу - Постановление от 01.01.2020 № 1)',
            '62. Следующее действующее правило.']
    source = extraction([[('Text', t) if isinstance(t, str) else t for t in text]])
    result = parser.build(source)
    got = owners(result)
    assert got['1.2'] == 'A/III'
    assert got['1.3'] == 'A/III/62'
    tree = build_owner_tree(normalized(text), CLAIM, 'original')
    assert not any(n.get('marker_label') == '14' for n in tree['nodes'])


@pytest.mark.parametrize('heading, prefix', [
    ('Глава 14⁴⁻¹. Документация', 'гл14⁴⁻¹'),
    ('Раздел II²⁻¹. Документация', 'II²⁻¹'),
    ('§ 5²⁻¹. Документация', '§5²⁻¹'),
])
def test_named_division_keeps_its_complete_compound_index(heading, prefix):
    result = parser.build(extraction([[('Section-header', heading),
        ('Section-header', 'Статья 8. Правило'), ('Text', '1. Условие.')]]))
    assert owners(result)['1.1'] == f'A/{prefix}/ст8'


def test_numbered_rubric_under_a_paragraph_sign_contains_the_following_articles():
    from legal_rag.corpus.ocr_owner_ast import build_owner_tree
    from test_ocr_structure import extraction as normalized, CLAIM
    text = [('Section-header', '§ 5. Патентное право'), ('Section-header', 'Статья 8. Правила'),
            '1. Последняя часть статьи.', ('Section-header', '1. Заявка и ее отзыв'),
            ('Section-header', 'Статья 9. Подача заявки'), '1. Заявка подается заявителем.']
    result = parser.build(extraction([[('Text', t) if isinstance(t, str) else t for t in text]]))
    assert owners(result)['1.3'] == 'A/§5/1'
    assert owners(result)['1.4'] == 'A/§5/1/ст9'
    tree = build_owner_tree(normalized(text), CLAIM, 'original')
    assert any(n['owner_path'] == 'A/§5/1' and n['kind'] == 'subchapter' for n in tree['nodes'])


def test_centred_heading_after_a_separate_editorial_note_closes_the_preceding_point():
    source = extraction([[('Section-header', 'II. Условия'), ('Text', '17. Предыдущее правило.'),
        ('Text', '(Дополнение пунктом - Постановление Правительства от 01.01.2020 № 1)'),
        ('Text', 'Контрольная закупка', 500),
        ('Text', '(Дополнение подразделом - Постановление Правительства от 01.01.2020 № 1)'),
        ('Text', '18. Новое правило.')]])
    got = owners(parser.build(source))
    assert got['1.3'] == got['1.4'] == 'A/II'


def test_centred_rubrics_do_not_license_an_unstyled_body_continuation_as_a_heading():
    source = extraction([[('Section-header', 'II. Условия'), ('Text', '1. Орган осуществляет контроль.'),
        ('Text', 'Федеральная служба и ее территориальные органы в части соблюдения требований ' * 4),
        ('Text', '2. Следующее правило.'), ('Text', 'Учет рисков', 500), ('Text', '3. Оценка рисков.'),
        ('Text', 'Порядок контроля', 500), ('Text', '4. Порядок применяется ежегодно.')]])
    assert owners(parser.build(source))['1.2'] == 'A/II/1'


def test_four_digit_zero_padded_form_list_stays_a_form_list():
    result = parser.build(extraction([[('Text', t) for t in [
        'Сведения формы', '0999. Предыдущая запись.', '1000. Последующая запись.',
    ]]]))
    assert set(owners(result).values()) == {'A'}


def test_a_styled_complete_article_part_is_not_a_subparagraph_heading():
    result = parser.build(extraction([[('Section-header', '§ 5. Условия'),
        ('Section-header', 'Статья 8. Правила'), ('Text', '2. Предыдущее условие.'),
        ('Section-header', '3. Последнее условие.'), ('Section-header', 'Статья 9. Новые правила')]]))
    assert owners(result)['1.3'] == 'A/§5/ст8/ч3'


def test_point_vocabulary_remap_still_finds_a_parenthesised_subpoint():
    result = parser.build(extraction([[('Text', t) for t in [
        'Статья 8. Требования', '1. По правилам пункта 1 настоящей статьи:',
        '1) требования включают:', 'а) первое условие;', 'б) второе условие;',
        '(Дополнение подпунктом - Федеральный закон от 01.01.2020 № 1-ФЗ)',
    ]]]))
    assert owners(result)['1.5'] == 'A/ст8/ч1/1'


def test_word_starting_with_cyrillic_ha_does_not_invent_a_roman_section():
    result = parser.build(extraction([[('Section-header', 'РАЗДЕЛ ХРАНЕНИЯ ДОКУМЕНТОВ'),
                                      ('Text', '1. Новое правило.')]]))
    assert owners(result)['1.1'] == 'A/1'


def test_inserted_decimal_does_not_take_children_of_the_preceding_base_point():
    result = parser.build(extraction([[('Text', t) for t in [
        '5. Требования', '5.3. Перечень', '5.3.1. Первое условие.',
        '5.3¹. Вставленный соседний пункт.', '5.3.2. Второе условие.',
    ]]]))
    assert owners(result)['1.4'] == 'A/5/5.3/5.3.2'


def test_inserted_decimal_keeps_its_own_printed_prefix_children():
    result = parser.build(extraction([[('Text', t) for t in [
        '5. Требования', '5.3. Перечень', '5.3¹. Вставленный перечень:',
        '5.3¹.1. Первое условие.', '5.3¹.2. Второе условие.',
    ]]]))
    assert owners(result)['1.4'] == 'A/5/5.3¹/5.3¹.2'


def test_centred_rubric_follows_a_finished_provision_with_an_inline_editorial_note():
    result = parser.build(extraction([[('Section-header', 'II. Условия'),
        ('Text', '17. Перечень включает:'),
        ('Text', 'Условие выполнено. (Дополнение абзацем - Постановление от 01.01.2020 № 1)'),
        ('Text', 'Мониторинговая закупка', 500),
        ('Text', '(Дополнение подразделом - Постановление от 01.01.2020 № 1)'),
        ('Text', '18. Новое правило.')]]))
    assert owners(result)['1.3'] == owners(result)['1.4'] == 'A/II'


def test_a_split_article_part_before_another_article_is_not_a_numbered_rubric():
    result = parser.build(extraction([[('Section-header', '§ 5. Условия'),
        ('Section-header', 'Статья 8. Правила'), ('Section-header', '1. Правила применяются'),
        ('Text', 'к заявителю и всем иным заинтересованным лицам.'),
        ('Section-header', 'Статья 9. Новые правила')]]))
    assert owners(result)['1.2'] == owners(result)['1.3'] == 'A/§5/ст8/ч1'
    assert owners(result)['1.4'] == 'A/§5/ст9'


def test_a_point_under_an_article_part_remains_a_point_without_vocabulary_remap():
    result = parser.build(extraction([[('Text', t) for t in [
        'Статья 8. Требования', '9. Перечень требований:', '14) предыдущее требование;',
        '15¹) дополнительные требования:', 'а) первое условие;', 'б) последнее условие;',
        '(Пункт введен - Федеральный конституционный закон от 01.01.2020 № 1-ФКЗ)',
    ]]]))
    assert owners(result)['1.6'] == 'A/ст8/ч9/15¹'
