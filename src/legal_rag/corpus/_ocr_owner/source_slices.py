"""Token-relative source slices; physical regions and their geometry never change."""
from copy import deepcopy
from dataclasses import replace
import re

from .markers import parse_marker
from .text import view, page_mark, NOISE_CATEGORIES

BASIS = "concatenated_text_node_raw_text"
DIRECTIVE = re.compile(r"\b(?:изложить\s+в\s+следующ(?:ей|их)\s+редакци[ия]х?|дополнить[^:]*следующ[^:]*)\s*:", re.I)
NEXT = re.compile(r"[.;]\s+(?P<number>[1-9]\d*)\.\s+(?=\S)")


def split_regions(regions):
    """Split only after a directive's outer guillemet closes before its next item.

    All matching takes place on raw source characters. In particular, stripping
    Markdown or collapsing whitespace must never supply a source offset.
    """
    result, expected, depth = [], None, 0
    for region in regions:
        cuts = [0]
        if region.role != "content" or region.category in NOISE_CATEGORIES or page_mark(region) or (region.category == "Footnote" and not (expected is not None and depth == 0 and region.raw.lstrip().startswith("«"))):
            if region.role == "table":
                expected, depth = None, 0
        else:
            marker = parse_marker(region.text, region.category)
            scheduled = None
            if depth == 0 and marker.kind == "int":
                directive = DIRECTIVE.search(region.raw)
                expected = None
                if directive:
                    scheduled = (int(marker.value) + 1, directive.end())
            for i, char in enumerate(region.raw):
                if scheduled and i >= scheduled[1]:
                    expected, scheduled = (scheduled[0] if depth == 0 else None), None
                if char == "«":
                    depth += 1
                elif char == "»" and depth:
                    depth -= 1
                    if depth == 0 and expected is not None:
                        match = NEXT.match(region.raw, i + 1)
                        if match and int(match['number']) == expected:
                            cuts.append(match.start('number'))
                            # A following directive may itself introduce a replacement.
                            tail = region.raw[cuts[-1]:]
                            directive = DIRECTIVE.search(tail)
                            if directive:
                                scheduled = (expected + 1, cuts[-1] + directive.end())
                        expected = None
            if scheduled:
                expected = scheduled[0] if depth == 0 else None
        cuts.append(len(region.raw))
        for start, end in zip(cuts, cuts[1:]):
            result.append(replace(region, order=len(result), source_start=start, source_end=end,
                                  raw=region.raw[start:end], text=view(region.raw[start:end])))
    return result


def slices_for(ids, start, end, tokens):
    """Project a region interval onto its ordered raw tokens (no added separators)."""
    result, offset = [], 0
    for tid in ids:
        length = len(tokens[tid]['raw_text'])
        lo, hi = max(start, offset), min(end, offset + length)
        if lo < hi or length == 0 and (start < offset <= end or start == offset == 0):
            result.append({'text_node_id': tid, 'start': lo - offset, 'end': hi - offset})
        offset += length
    return result


def narrowed_span(token, start, end):
    span = deepcopy(token['source_span'])
    if start == 0 and end == len(token['raw_text']):
        return span
    for prefix in ('', 'ocr_'):
        base = span[prefix + 'char_start']
        span[prefix + 'char_start'], span[prefix + 'char_end'] = base + start, base + end
    span['locator'] = re.sub(r':chars:\d+:\d+$',
                             f":chars:{span['ocr_char_start']}:{span['ocr_char_end']}", span['locator'])
    return span
