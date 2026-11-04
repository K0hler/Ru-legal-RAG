"""Authored source partitions preserve real owners inside a physical OCR region."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

from legal_rag.corpus.ocr_owner_ast import build_owner_tree
from test_ocr_structure import CLAIM, extraction

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "docs/assets"))
from validate_ocr_structure import validate_source  # noqa: E402
from check_m1_04a_source_controls import validate_controls  # noqa: E402


@pytest.mark.parametrize("separator", [" ", "\n", "\n\n"])
def test_outer_quote_split_is_source_exact_across_token_boundaries(separator):
    first = '«Новое правило с названием «Вложенное название» от 01.02.2025, пункт 3.2.». ' 
    second = '13. Сноску 19 исключить.'
    payload = first.rstrip(' ') + separator + second
    source = extraction(['12. Пункт изложить в следующей редакции:', payload])
    before = deepcopy(source)
    tree = build_owner_tree(source, CLAIM, 'original')
    assert tree['schema_version'] == 'legal-ast/3'
    assert tree['parser_version'].startswith('ocr-owner-ast/5+')
    assert tree == build_owner_tree(source, CLAIM, 'original')
    assert source == before
    binding = tree['region_bindings'][-1]
    offset = payload.index(second)
    assert binding['disposition'] == 'partitioned'
    assert binding['owner_path'] is binding['address'] is None
    assert [(f['start'], f['end'], f['owner_path']) for f in binding['fragments']] == [
        (0, offset, 'A/12'), (offset, len(payload), 'A/13')]
    leaves = [n for n in tree['nodes'] if n.get('source_region_ids') and n['source_region_ids'] == [binding['region_id']]]
    assert [n['original_text'] for n in leaves] == [payload[:offset], second]
    assert len({n['address'] for n in leaves}) == 2
    point = next(n for n in tree['nodes'] if n['address'] == 'act/owner/A/13')
    assert point['parent_address'] == 'act/owner/A'
    assert point['marker_label'] == point['number_display'] == '13'
    assert point['anchor_source_spans'] == leaves[1]['source_spans']
    assert point['anchor_source_spans'][0]['ocr_char_start'] == offset
    assert tree['accounting']['basis'] == 'text_node_raw_text_half_open_intervals'
    assert sum(tree['accounting'][k + '_source_chars'] for k in ('parsed', 'excluded', 'unresolved')) == sum(len(t['raw_text']) for t in source['text_nodes'])
    validate_source(source, tree)


@pytest.mark.parametrize('directive,payload', [
    ('12. Обычный перечень:', '«Текст». 13. Это число.'),
    ('12. Пункт изложить в следующей редакции:', '«Текст «Название». 13. Ещё внутри цитаты».'),
    ('12. Пункт изложить в следующей редакции:', '«Правило». 13.02.2025 дата.'),
    ('12. Пункт изложить в следующей редакции:', '«Правило». 13.2. Ссылка.'),
    ('12. Пункт изложить в следующей редакции:', '«Правило 13. Ещё правило».'),
])
def test_quote_date_decimal_and_no_directive_negatives(directive, payload):
    tree = build_owner_tree(extraction([directive, payload]), CLAIM, 'original')
    assert all(b['disposition'] != 'partitioned' for b in tree['region_bindings'])


@pytest.mark.parametrize('damage', ['gap', 'overlap', 'reversal', 'duplicate_token', 'whitespace', 'bbox', 'locator'])
def test_independent_source_checker_rejects_slice_corruption(damage):
    source = extraction(['12. Пункт изложить в следующей редакции:', '«Правило». 13. Исключить сноску.'])
    tree = build_owner_tree(source, CLAIM, 'original')
    leaves = [n for n in tree['nodes'] if n.get('text_slices') and n['source_region_id'] == tree['region_bindings'][-1]['region_id']]
    assert len(leaves) == 2
    first, second = leaves
    if damage == 'gap':
        second['text_slices'][0]['start'] += 1
    elif damage == 'overlap':
        second['text_slices'][0]['start'] -= 1
    elif damage == 'reversal':
        first['text_slices'][0]['start'], first['text_slices'][0]['end'] = first['text_slices'][0]['end'], 0
    elif damage == 'duplicate_token':
        second['text_slices'][0]['start'] = 0
    elif damage == 'whitespace':
        first['original_text'] = first['original_text'].rstrip()
    elif damage == 'bbox':
        second['fragments'][0]['bbox'][0] += 1
    else:
        second['source_spans'][0]['locator'] += 'foreign'
    with pytest.raises(ValueError):
        validate_source(source, tree)


def partition_case():
    payload = '«Правило». 13. Исключить сноску.'
    source = extraction(['12. Пункт изложить в следующей редакции:', payload])
    tree = build_owner_tree(source, CLAIM, 'original')
    rows = [{"key": f"1.{i}", "page": 1, "region_id": r['region_id'], "category": r['category']}
            for i, r in enumerate(source['pages'][0]['regions'])]
    packet = {"source_asset_sha256": source['source_asset_sha256'], "extraction_id": source['extraction_id'],
              "assigned_pages": [1], "regions": rows, "pages": [{"page": 1, "sha256": 'b' * 64}]}
    controls = {"schema_version": "m1-04a-independent-source-controls/2", **{k: packet[k] for k in
                ('source_asset_sha256', 'extraction_id', 'assigned_pages')},
                "independence": {"candidate_outputs_used": False, "previous_gold_used": False},
                "uncertainties": [], "image_reviews": [{"page": 1, "image_sha256": 'b' * 64, "observed_structure": 'Authored two units in the last region.'}],
                "regions": [{"key": f"1.{i}", "status": 'picture' if i == 1 else 'partitioned' if i == 5 else 'evaluated',
                             "owner": None if i in {1, 5} else 'A/12' if i == 4 else 'A',
                             "continuation": None if i == 5 else False} for i in range(6)],
                "units": [{"owner_path": owner, "parent_owner_path": parent, "kind": kind, "printed_number": number,
                           "start_key": key, "evidence_keys": [key], **extra} for owner, parent, kind, number, key, extra in [
                               ('A', None, 'act', None, '1.0', {}),
                               ('A/12', 'A', 'point', '12', '1.4', {}),
                               ('A/13', 'A', 'point', '13', '1.5', {'start_text_offset': 11, 'start_text_quote': '13. Исключить сноску.'})]],
                "region_owner_spans": [{"key": '1.5', "start": start, "end": end, "owner": owner,
                                         "text": payload[start:end], "offset_basis": 'concatenated_text_node_raw_text',
                                         "continuation": False, "disposition": 'parsed'}
                                        for start, end, owner in [(0, 11, 'A/12'), (11, len(payload), 'A/13')]],
                "region_text_projections": {'1.5': {"offset_basis": 'concatenated_text_node_raw_text', 'raw_text': payload,
                                                   'text_node_ids': [source['text_nodes'][-1]['text_node_id']]}}}
    return source, tree, packet, controls


def test_independent_partition_controls_accept_both_real_owners():
    report = validate_controls(*partition_case())
    assert report['canonical_regions_passed'] == 5


@pytest.mark.parametrize('damage', ['missing_span', 'swapped_owners', 'wrong_offset', 'missing_offset', 'wrong_quote', 'projection', 'span_text'])
def test_independent_partition_controls_reject_bad_source_expectations(damage):
    source, tree, packet, controls = partition_case()
    if damage == 'missing_span':
        controls['region_owner_spans'].pop()
    elif damage == 'swapped_owners':
        controls['region_owner_spans'][0]['owner'], controls['region_owner_spans'][1]['owner'] = 'A/13', 'A/12'
    elif damage == 'wrong_offset':
        controls['units'][-1]['start_text_offset'] = 0
    elif damage == 'missing_offset':
        del controls['units'][-1]['start_text_offset']
    elif damage == 'wrong_quote':
        controls['units'][-1]['start_text_quote'] = '12.'
    elif damage == 'projection':
        controls['region_text_projections']['1.5']['raw_text'] += ' '
    else:
        controls['region_owner_spans'][0]['text'] = controls['region_owner_spans'][0]['text'].rstrip()
    with pytest.raises(ValueError):
        validate_controls(source, tree, packet, controls)


def test_multitoken_region_splits_inside_second_token_with_raw_whitespace_offsets():
    payload = '  «Первый\n  абзац с названием «Название»\t».   13. Исключить сноску.'
    source = extraction(['12. Пункт изложить в следующей редакции:', payload])
    before = deepcopy(source)
    tree = build_owner_tree(source, CLAIM, 'original')
    binding = tree['region_bindings'][-1]
    offset = payload.index('13.')
    assert binding['fragments'][1]['start'] == offset
    second = next(n for n in tree['nodes'] if n.get('original_text') == payload[offset:])
    token = source['text_nodes'][-1]
    local = token['raw_text'].index('13.')
    assert second['text_slices'] == [{'text_node_id': token['text_node_id'], 'start': local, 'end': len(token['raw_text'])}]
    assert second['source_spans'][0]['ocr_char_start'] == offset
    assert second['fragments'][0]['bbox'] == source['pages'][0]['regions'][-1]['bbox']
    assert source == before
    validate_source(source, tree)


def test_independent_controls_reject_self_consistent_wrong_owners_and_marker():
    source, tree, packet, controls = partition_case()
    binding = tree['region_bindings'][-1]
    leaves = [n for n in tree['nodes'] if n.get('source_region_id') == binding['region_id']]
    for leaf, fragment, owner in zip(leaves, binding['fragments'], ['A/13', 'A/12'], strict=True):
        leaf.update(owner_path=owner, parent_address='act/owner/' + owner)
        fragment['owner_path'] = owner
    point13 = next(n for n in tree['nodes'] if n['address'] == 'act/owner/A/13')
    point13['anchor_source_spans'] = deepcopy(leaves[0]['source_spans'])
    tree['nodes'].remove(point13)
    tree['nodes'].insert(tree['nodes'].index(leaves[0]), point13)
    for node in tree['nodes']:
        node['children'] = [n['address'] for n in tree['nodes'] if n['parent_address'] == node['address']]
    validate_source(source, tree)
    with pytest.raises(ValueError):
        validate_controls(source, tree, packet, controls)
    source, tree, packet, controls = partition_case()
    next(n for n in tree['nodes'] if n['address'] == 'act/owner/A/13')['marker_label'] = '14'
    with pytest.raises(ValueError):
        validate_controls(source, tree, packet, controls)


def test_empty_raw_token_has_exactly_one_explicit_zero_slice():
    source = extraction(['1. Правило.'])
    token = source['text_nodes'][-1]
    empty = deepcopy(token)
    empty.update(text_node_id=token['text_node_id'] + 1, raw_text='', decoded_text='')
    for prefix in ('', 'ocr_'):
        empty['source_span'][prefix + 'char_start'] = empty['source_span'][prefix + 'char_end']
    source['text_nodes'].append(empty)
    source['blocks'][-1]['text_node_ids'].append(empty['text_node_id'])
    tree = build_owner_tree(source, CLAIM, 'original')
    parts = [s for n in tree['nodes'] for s in n.get('text_slices', []) if s['text_node_id'] == empty['text_node_id']]
    assert parts == [{'text_node_id': empty['text_node_id'], 'start': 0, 'end': 0}]
    validate_source(source, tree)


def test_closed_replacement_does_not_arm_later_unrelated_quotes():
    source = extraction(['12. Пункт изложить в следующей редакции:', '«Правило».', 'Другое «Название». 13. Обычный текст.'])
    tree = build_owner_tree(source, CLAIM, 'original')
    assert all(b['disposition'] != 'partitioned' for b in tree['region_bindings'])


@pytest.mark.parametrize('damage', ['slice_offset', 'token_id', 'source_span_offset', 'binding_offset'])
def test_boolean_values_cannot_impersonate_integer_source_coordinates(damage):
    source, tree, _, _ = partition_case()
    leaf = next(n for n in tree['nodes'] if n.get('text_node_ids'))
    if damage == 'slice_offset':
        leaf['text_slices'][0]['start'] = False
    elif damage == 'token_id':
        assert leaf['text_node_ids'][0] == 0
        leaf['text_slices'][0]['text_node_id'] = False
        leaf['text_node_ids'][0] = False
        leaf['fragments'][0]['text_node_ids'][0] = False
    elif damage == 'source_span_offset':
        leaf['source_spans'][0]['char_start'] = False
    else:
        tree['region_bindings'][-1]['fragments'][0]['start'] = False
    with pytest.raises(ValueError):
        validate_source(source, tree)


def test_self_consistent_reversal_of_tokens_and_text_within_a_leaf_is_rejected():
    source = extraction(['1. Первое правило.\nВторая строка.'])
    tree = build_owner_tree(source, CLAIM, 'original')
    leaf = next(n for n in tree['nodes'] if n.get('source_region_id') == tree['region_bindings'][-1]['region_id'])
    assert len(leaf['text_slices']) == 2
    for key in ('text_slices', 'text_node_ids', 'source_spans'):
        leaf[key].reverse()
    leaf['fragments'][0]['text_node_ids'].reverse()
    tokens = {t['text_node_id']: t for t in source['text_nodes']}
    leaf['original_text'] = ''.join(tokens[t]['raw_text'] for t in leaf['text_node_ids'])
    leaf['text'] = ' '.join(leaf['original_text'].split())
    with pytest.raises(ValueError):
        validate_source(source, tree)


def test_interval_accounting_can_partition_one_token_between_dispositions():
    from legal_rag.corpus.ocr_owner_ast import _accounting
    source, tree, _, _ = partition_case()
    binding = tree['region_bindings'][-1]
    leaf = next(n for n in tree['nodes'] if n.get('source_region_id') == binding['region_id'])
    tree['nodes'].remove(leaf)
    leaf.update(address=None, owner_path=None, kind='unresolved_block')
    tree['unresolved_blocks'].append(leaf)
    binding['fragments'][0].update(address=None, owner_path=None, disposition='unresolved')
    for node in tree['nodes']:
        node['children'] = [n['address'] for n in tree['nodes'] if n['parent_address'] == node['address']]
    tokens = {t['text_node_id']: t for t in source['text_nodes']}
    tree['accounting'] = _accounting(tokens, tree['nodes'], tree['unresolved_blocks'], tree['excluded_blocks'])
    assert tree['accounting']['parsed_text_nodes'] + tree['accounting']['unresolved_text_nodes'] > len(tokens)
    validate_source(source, tree)


def test_table_region_cannot_be_partitioned_by_quoted_cell_text():
    source = extraction(['12. Пункт изложить в следующей редакции:',
                         ('Table', '<table><tr><td>«Правило». 13. Исключить сноску.</td></tr></table>')])
    tree = build_owner_tree(source, CLAIM, 'original')
    assert tree['region_bindings'][-1]['disposition'] != 'partitioned'
    validate_source(source, tree)


def test_a_directive_inside_a_quote_does_not_license_a_new_outer_unit():
    source = extraction(['12. «Пункт изложить в следующей редакции: правило». 13. Ещё внутри текста.'])
    tree = build_owner_tree(source, CLAIM, 'original')
    assert all(b['disposition'] != 'partitioned' for b in tree['region_bindings'])
