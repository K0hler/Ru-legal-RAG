"""Source numbering conflicts preserve separate units and visible evidence."""
import copy

import pytest

from legal_rag.corpus import ocr_owner_ast as A
from test_ocr_structure import extraction, CLAIM


def conflict_source():
    return extraction([('Section-header', 'III. Требования'),
                       '3.15. При размещении соблюдаются требования:', 'Требование о размещении.',
                       '3.15. При мероприятиях соблюдаются требования:',
                       '3.16.1. Организатор сообщает сведения.',
                       '4. При перевозке соблюдаются следующие требования:',
                       '4.1. Организатор обеспечивает сопровождение.', 'Сведения передаются заблаговременно.'])


def test_duplicate_numbers_have_distinct_source_bound_occurrences():
    source = conflict_source()
    before = copy.deepcopy(source)
    tree = A.build_owner_tree(source, CLAIM, 'original')
    units = [n for n in tree['nodes'] if not n.get('source_region_ids')]
    repeated = [n for n in units if n['number_display'] == '3.15']
    assert len(repeated) == 2
    assert repeated[0]['address'] != repeated[1]['address']
    assert repeated[0]['anchor_region_ids'] != repeated[1]['anchor_region_ids']
    assert {n['number_canonical'] for n in repeated} == {'3.15'}
    assert {w['code'] for w in tree['source_warnings']} == {
        'duplicate_printed_number', 'missing_parent_number', 'scope_boundary'}
    assert any(n['owner_path'] == 'A/III/4/4.1' for n in units)
    assert not any(n['number_display'] == '3.16' for n in units)
    assert set(tree['structural_issues']) == {'pdf_structure_unqualified'}
    assert source == before


def test_warning_evidence_cannot_be_deleted_or_rebound():
    source = conflict_source()
    tree = A.build_owner_tree(source, CLAIM, 'original')
    for change in ('remove', 'region', 'message'):
        damaged = copy.deepcopy(tree)
        if change == 'remove':
            damaged['source_warnings'].clear()
        else:
            damaged['source_warnings'][0]['region_ids' if change == 'region' else 'message'] = [] if change == 'region' else 'forged'
        with pytest.raises(ValueError):
            A.validate_owner_tree(source, damaged)


def test_ordinary_numbered_groups_inside_a_section_do_not_raise_source_warnings():
    source = extraction([('Section-header', 'I. Требования'), '1. Первая группа:',
                         '1.1. Первое требование.', '2. Вторая группа:', '2.1. Второе требование.'])
    assert A.build_owner_tree(source, CLAIM, 'original')['source_warnings'] == []


def test_delayed_note_uses_the_marked_occurrence_not_the_latest_duplicate():
    source = extraction([('Section-header', 'III. Требования'), '3.15. Первое правило¹.',
                         '3.15. Второе правило.', ('Footnote', '¹ Сноска первого правила.')])
    tree = A.build_owner_tree(source, CLAIM, 'original')
    note, = [n for n in tree['nodes'] if n['kind'] == 'footnote']
    assert note['parent_address'] == 'act/owner/A/III/3.15'


def test_marks_on_two_duplicate_occurrences_do_not_silently_choose_one():
    source = extraction([('Section-header', 'III. Требования'), '3.15. Первое правило¹.',
                         '3.15. Второе правило¹.', ('Footnote', '¹ Общая или неоднозначная сноска.')])
    tree = A.build_owner_tree(source, CLAIM, 'original')
    assert any('неоднозначная' in n['text'] for n in tree['unresolved_blocks'])


def test_page_note_owner_override_keeps_the_final_occurrence_evidence():
    from legal_rag.corpus._ocr_owner.audit import prepare_owner_result
    from legal_rag.corpus import ocr_owner_structure as S
    from test_ocr_logical_structure import extraction as pages

    source = pages([[('Section-header', 'III. Требования'), ('Text', '3.15. Первое правило¹.')],
                    [('Text', '3.15. Второе правило².'), ('Footnote', '² Сноска второго правила.'),
                     ('Footnote', '¹ Сноска страницы.')]])
    raw = S.build(source)
    tokens = {t['text_node_id']: t for t in source['text_nodes']}
    result = prepare_owner_result(raw, tokens)
    notes = [p for p in result['paragraphs'] if p['flow'] == 'footnote']
    assert len(notes) == 2
    assert {p['owner'] for p in notes} == {'A/III/3.15@2'}
    assert all([rid for e in p['evidence'] for rid in e.get('footnote_reference_region_ids', [])]
               == ['r2-0'] for p in notes)


@pytest.mark.parametrize('mode', ['superscript_parent', 'existing_decimal_parent'])
def test_a_parser_error_cannot_be_hidden_as_a_source_number_warning(monkeypatch, mode):
    body = ([('Section-header', 'III. Требования'), '3.15. Печатный родитель.', '3.15.1. Дочерний пункт.']
            if mode == 'existing_decimal_parent' else ['1. Первый пункт.', '2¹. Вставленный пункт.',
                 ('Section-header', 'III. Требования'), '3.1. Правило.'])
    source = extraction(body)
    original = A.parser.build

    def corrupted(value):
        result = original(value)
        target = ('A/III/3.15/3.15.1', 'A/III/3.15.1') if mode == 'existing_decimal_parent' else ('A/III', 'A/2¹/III')
        for item in [*result['paragraphs'], *result['regions']]:
            if item['owner'] == target[0]:
                item['owner'] = target[1]
        return result

    monkeypatch.setattr(A.parser, 'build', corrupted)
    tree = A.build_owner_tree(source, CLAIM, 'original')
    expected = 'number_parent_mismatch' if mode == 'existing_decimal_parent' else 'section_inside_point'
    assert expected in tree['structural_issues']
    assert not any(w['code'] == 'missing_parent_number' for w in tree['source_warnings'])


def test_a_section_inside_a_point_is_reported_as_a_parser_problem(monkeypatch):
    source = extraction([('Section-header', 'III. Требования'), '3.1. Правило.'])
    original = A.parser.build

    def corrupted(value):
        result = original(value)
        for paragraph in result['paragraphs']:
            if paragraph['owner'] == 'A/III':
                paragraph['owner'] = 'A/99/III'
        for region in result['regions']:
            if region['owner'] == 'A/III':
                region['owner'] = 'A/99/III'
        return result

    monkeypatch.setattr(A.parser, 'build', corrupted)
    tree = A.build_owner_tree(source, CLAIM, 'original')
    assert 'section_inside_point' in tree['structural_issues']
    tree['structural_issues'].remove('section_inside_point')
    with pytest.raises(ValueError):
        A.validate_owner_tree(source, tree)


def test_numbering_warning_is_visible_in_the_normal_compiler_report():
    from legal_rag.corpus.compiler import _report
    tree = A.build_owner_tree(conflict_source(), CLAIM, 'original')
    manifest = {'assets': [{'sha256': tree['source_asset_sha256'], 'source_url': 'local-source',
                            'evidence': {'locator': 'pdf:whole-document'}}],
                'act_identity_claim': {'declared_identity': CLAIM}, 'kind': 'original_amendments',
                'source_statuses': [], 'unresolved_questions': [], 'processing_permission': {}}
    draft = {'content': {'trees': [tree]}, 'blockers': [], 'target_date': '2026-11-01',
             'admission_status': 'unresolved', 'draft_id': 'authored', 'input_hash': 'authored', 'content_hash': 'authored'}
    report = _report(manifest, draft)
    assert 'Особенности нумерации исходника' in report
    assert '3.15' in report and 'повторяется' in report
