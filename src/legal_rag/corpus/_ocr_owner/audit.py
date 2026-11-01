"""Source-bound unit occurrences and warnings, independent of corpus admission."""
from collections import defaultdict
from copy import deepcopy
import re

from .text import roman_value
from .markers import UNIT_RANK


def prepare_owner_result(raw, tokens):
    """Keep repeated printed numbers distinct without correcting the source."""
    result = deepcopy(raw)
    aliases, starts, repeats = {}, defaultdict(list), {}
    warnings, issues = [], set()
    referenced_owners = {}
    original_owners = {r['region_id']: r['owner'] for r in raw['regions']}

    def mapped(path):
        parts = path.split('/')
        for size in range(len(parts), 0, -1):
            prefix = '/'.join(parts[:size])
            if prefix in aliases:
                return '/'.join([aliases[prefix], *parts[size:]])
        return path

    for p in result['paragraphs']:
        if not p['owner']:
            continue
        original = p['owner']
        if p['marker'] and p['marker'][0] != 'dash':
            parent, _, label = original.rpartition('/')
            base = mapped(parent) + '/' + label
            starts[base].append(p['regions'][0]['region_id'])
            count = len(starts[base])
            p['owner'] = base if count == 1 else base + '@' + str(count)
            aliases[original] = p['owner']
            if count > 1:
                if base not in repeats:
                    repeats[base] = {'code': 'duplicate_printed_number', 'region_ids': starts[base],
                                     'owner_paths': [base], 'message': 'Обозначение «' + p['marker'][1]
                                     + '» повторяется в исходнике; фрагменты сохранены отдельно.'}
                    warnings.append(repeats[base])
                repeats[base]['owner_paths'].append(p['owner'])
        else:
            p['owner'] = mapped(original)
            if p['flow'] == 'footnote':
                references = [rid for e in p['evidence'] for rid in e.get('footnote_reference_region_ids', [])]
                candidates = set()
                for rid in references:
                    before, after = original_owners.get(rid), referenced_owners.get(rid)
                    if before and after and (before == original or before.startswith(original + '/')):
                        candidates.add('/'.join(after.split('/')[:len(original.split('/'))]))
                if len(candidates) == 1:
                    p['owner'] = candidates.pop()
                elif candidates:
                    p['owner'] = None
                    p['evidence'].append({'footnote_owner': 'unresolved', 'candidate_owners': sorted(candidates)})
        for region in p['regions']:
            referenced_owners[region['region_id']] = p['owner']
    owners = {r['region_id']: p['owner'] for p in result['paragraphs'] for r in p['regions']}
    for r in result['regions']:
        if r['region_id'] in owners:
            r['owner'] = owners[r['region_id']]

    marked = [p for p in result['paragraphs'] if p['marker'] and p['marker'][0] != 'dash' and p['owner']]
    markers = {p['owner']: p['marker'] for p in marked}

    def scope(path):
        parts = path.split('/')
        result = parts[0]
        for n in range(1, len(parts)):
            prefix = '/'.join(parts[:n + 1])
            if parts[n].startswith('AN') or markers.get(prefix, [None])[0] in UNIT_RANK:
                result = prefix
        return result

    for i, p in enumerate(marked):
        kind, label = p['marker']
        parent = p['owner'].rpartition('/')[0]
        ancestors = p['owner'].split('/')[:-1]
        if kind in {'roman', 'section_named'} and any(
                markers.get('/'.join(ancestors[:n + 1]), [None])[0] in {'int', 'decimal', 'paren', 'letter'}
                or re.fullmatch(r'\d+(?:\.\d+)*(?:@\d+)?', s) for n, s in enumerate(ancestors)):
            issues.add('section_inside_point')
        if kind == 'decimal' and label.count('.') >= 2:
            prefix = label.rpartition('.')[0]
            if not any(markers.get('/'.join(ancestors[:n]), [None, None])[1] == prefix
                       for n in range(1, len(ancestors) + 1)):
                if any(m[0] == 'decimal' and m[1] == prefix and scope(path) == scope(p['owner'])
                       for path, m in markers.items()):
                    issues.add('number_parent_mismatch')
                else:
                    warnings.append({'code': 'missing_parent_number', 'region_ids': [p['regions'][0]['region_id']],
                                     'owner_paths': [p['owner']], 'message': 'Для номера «' + label
                                     + '» не найден напечатанный родитель «' + prefix + '»; номер не исправлялся.'})
        text = ' '.join(tokens[t]['raw_text'] for t in p['text_node_ids'])
        if kind != 'int' or i == 0 or not text.rstrip().endswith(':'):
            continue
        section = markers.get(parent)
        previous = marked[i - 1]
        following = marked[i + 1] if i + 1 < len(marked) else None
        if not section or section[0] not in {'roman', 'section_named'} or previous['marker'][0] != 'decimal':
            continue
        section_label = re.sub(r'^разд', '', section[1])
        section_number = int(section_label) if section_label.isdigit() else roman_value(section_label)
        if (section_number is not None and label.isdigit() and int(label) == section_number + 1
                and previous['marker'][1].split('.')[0] == str(section_number)
                and previous['owner'].rpartition('/')[0] == parent and previous['marker'][1].count('.') >= 2
                and following and following['marker'][0] == 'decimal'
                and following['marker'][1].startswith(label + '.')):
            ids = [r['region_id'] for r in result['regions'] if r['owner'] == p['owner']
                   or (r['owner'] and r['owner'].startswith(p['owner'] + '/'))]
            affected = list(dict.fromkeys(r['owner'] for r in result['regions'] if r['region_id'] in ids))
            warnings.append({'code': 'scope_boundary', 'region_ids': ids, 'owner_paths': affected,
                             'message': 'Группа «' + label + '» начинает новую нумерацию внутри раздела; '
                             'неоднозначность исходного оформления отмечена.'})
    result['source_warnings'] = warnings
    result['audit_issues'] = sorted(issues)
    return result
