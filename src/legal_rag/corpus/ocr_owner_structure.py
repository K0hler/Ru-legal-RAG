"""Maintained owner hierarchy promoted from the post-П23 M1-04A prototype.

Source: experiment SHA-256 ea7f4d95d7553b10cf34bd6f3ee52ace2ef9714038ea99abbe0991b16f1d3d38.
The retained experiment is a historical baseline; production uses this module through ocr_owner_ast.
Independent Task 3 qualification is still required. Three passes:

1. physical: drop page numbers / repeated running headers, keep every token;
2. logical paragraphs: join cross-region / cross-page continuations of the body
   and of footnotes, without touching source text, tokens or locators;
3. structure: caption-driven scopes (approving act -> approved text -> annexes)
   and a beam search over marker sequences that picks depths by sequence
   continuity (idea from 18F regparser.tree.depth), not by local regexes.

Output paths use a neutral syntax shared with the hand-made gold:
``A`` approving act, ``S`` approved text, ``S/AN4`` annex 4,
``S/II/4/в`` subpoint в) of point 4 in section II; named law units use typed
segments: ``A/гл2/ст5/ч1/3`` point 3) of part 1. of article 5 in chapter 2.

Requisites: after the last numbered or named element of a scope, the first short
unterminated requisite line (signer, «Москва, Кремль», date, number, registration,
«Совершено в …», «За …», barcode) opens a requisite block; its paragraphs get kind
``requisite`` with evidence ``requisite_block`` and, with everything after them in the
scope, belong to the scope root. A barcode that is the last body line of its page is
a ``signature`` paragraph of the root (evidence ``barcode``) anywhere in the scope.
"""

from __future__ import annotations

# Keep direct script execution and file-based prototype loading supported.
if not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import hashlib
import json
from collections import Counter

from legal_rag.corpus._ocr_owner.markers import (
    ABANDON_ARTICLE,
    ROMAN_TEXT_MAX,
    abandons_article,
    continues_list,
    leading_zero_list,
    parse_marker,
    transitions,
)
from legal_rag.corpus._ocr_owner.model import (
    Marker,
    Paragraph,
    Region,
)
from legal_rag.corpus._ocr_owner.ownership import (
    SUBHEADING_STYLED_MAX,
    assign_body_owners,
    assign_footnote_owners,
    points_are_article_parts,
)
from legal_rag.corpus._ocr_owner.paragraphs import (
    load_regions,
    logical_paragraphs,
)
from legal_rag.corpus._ocr_owner.scopes import (
    partition_scopes,
)
from legal_rag.corpus._ocr_owner.tables import (
    TABLE_TITLE_MAX,
)
from legal_rag.corpus._ocr_owner.text import (
    ASTERISK_NOTE,
    CAPTION_BLOCK_MAX,
    EDITORIAL_NOTE,
    annex_caption,
    fill_in_line,
    is_project_caption,
    page_mark,
    provision_final,
    requisite_like,
    starts_continuation,
    strip_emphasis,
    to_roman,
    toc_line,
    view,
)

# Compatibility helpers used by the existing authored owner-rule checks.
__all__ = (
    "VERSION", "build", "main", "ABANDON_ARTICLE", "ROMAN_TEXT_MAX", "abandons_article",
    "continues_list", "leading_zero_list", "parse_marker", "transitions", "Marker", "Paragraph",
    "Region", "SUBHEADING_STYLED_MAX", "TABLE_TITLE_MAX", "ASTERISK_NOTE", "CAPTION_BLOCK_MAX",
    "EDITORIAL_NOTE", "annex_caption", "fill_in_line", "is_project_caption", "page_mark",
    "provision_final", "requisite_like", "starts_continuation", "strip_emphasis", "to_roman",
    "toc_line", "view",
)

VERSION = "ocr-logical-structure/23-experiment+m1-06/1"


def build(extraction: dict) -> dict:
    regions = load_regions(extraction)
    points_are_parts = points_are_article_parts([r.text for r in regions])
    paragraphs = logical_paragraphs(regions)

    scopes = partition_scopes(paragraphs)
    for scope_path, items in scopes:
        assign_body_owners(scope_path, items, points_are_parts)
    assign_footnote_owners(paragraphs, scopes)

    region_owner = {}
    region_cont = {}
    for p in paragraphs:
        for k, r in enumerate(p.regions):
            region_owner[(r.region_id, r.source_start, r.source_end)] = p.owner
            region_cont[(r.region_id, r.source_start, r.source_end)] = k > 0
    # preservation: every OCR token belongs to exactly one region entry
    covered = Counter(t for r in regions if r.source_start == 0 for t in r.text_node_ids)
    expected = Counter(t["text_node_id"] for t in extraction["text_nodes"])
    if covered != expected:
        raise ValueError("token accounting mismatch")
    return {
        "schema": "ocr-logical-structure-experiment/0",
        "parser_version": VERSION,
        "source_asset_sha256": extraction["source_asset_sha256"],
        "paragraphs": [{
            "flow": p.flow, "kind": p.kind, "owner": p.owner,
            "marker": None if p.marker.kind in {"none", "section_reset", "retired_range"} else [p.marker.kind, p.marker.label],
            "regions": [{"page": r.page, "index": r.index, "region_id": r.region_id, "category": r.category,
                         "source_start": r.source_start, "source_end": r.source_end,
                         "text_node_ids": r.text_node_ids}
                        for r in p.regions],
            "text_node_ids": [t for r in p.regions for t in r.text_node_ids],
            "text_preview": p.text[:90], "evidence": p.evidence,
        } for p in paragraphs],
        "regions": [{"page": r.page, "index": r.index, "region_id": r.region_id, "category": r.category,
                     "source_start": r.source_start, "source_end": r.source_end,
                     "role": r.role, "owner": region_owner.get((r.region_id, r.source_start, r.source_end)),
                     "continuation": region_cont.get((r.region_id, r.source_start, r.source_end), False)} for r in regions],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    with open(args.input, "rb") as handle:
        raw = handle.read()
    result = build(json.loads(raw))
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
