"""Physical region accounting and logical body/footnote paragraph joining."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from .markers import (
    parse_marker,
)
from .model import (
    Paragraph,
    Region,
)
from .text import (
    BARCODE_EVIDENCE,
    NOISE_CATEGORIES,
    PAGE_CODE_LINE,
    PAGE_MARK_EVIDENCE,
    REPEAT_THRESHOLD,
    barcode_like,
    final_char,
    footnote_number,
    is_caption,
    page_mark,
    region_footnote_number,
    starts_continuation,
    terminated,
    view,
)

ROW_LEFT_TEXT_MIN = 40  # a left cell this long is a row of a card or table, not a signer's title


def mark_row_cells(regions: list[Region]) -> None:
    """Cycle 10 B3: a body region whose printed row (vertical overlap of at least half the lower height) also holds
    a table or a long text («Контроль технического состояния … оборудования» | «Код» | «А/01.4»; «Код оригинала» |
    «Регистрационный номер профессионального стандарта» in a professional standard's card) is a cell of that row:
    its right position is no signature evidence. Page headers/footers are never cells."""
    by_page = defaultdict(list)
    for r in regions:
        by_page[r.page].append(r)
    for page in by_page.values():
        for r in page:
            if r.category in NOISE_CATEGORIES:
                continue
            for q in page:
                if q is r or q.category in NOISE_CATEGORIES:
                    continue
                overlap = min(r.bbox[3], q.bbox[3]) - max(r.bbox[1], q.bbox[1])
                height = min(r.bbox[3] - r.bbox[1], q.bbox[3] - q.bbox[1])
                wide = q.category == "Table" or len(q.text) > ROW_LEFT_TEXT_MIN
                if height > 0 and overlap * 2 >= height and wide:
                    r.row_cell = True
                    break


def load_regions(extraction: dict) -> list[Region]:
    raw = defaultdict(str)
    nodes = defaultdict(list)
    for block in extraction["blocks"]:
        raw[block["source_region_id"]] += block["original_text"]
        nodes[block["source_region_id"]].extend(block["text_node_ids"])
    regions = []
    for page in extraction["pages"]:
        for index, region in enumerate(page["regions"]):
            rid = region["region_id"]
            regions.append(Region(len(regions), page["page"], index, rid, region["category"], region["bbox"],
                                  page["image_size"], raw.get(rid, ""), view(raw.get(rid, "")), nodes.get(rid, [])))
    mark_row_cells(regions)
    running = Counter(re.sub(r"\d+", "#", r.text) for r in regions if r.category in NOISE_CATEGORIES and r.text)
    # Exact repeats (not digit-normalised): «Приложение № 1 …» and «Приложение № 2 …»
    # are different captions, while the same caption on every page is a running header.
    exact = Counter(r.text for r in regions if r.category in NOISE_CATEGORIES and r.text)
    seen: Counter = Counter()
    for r in regions:
        if r.category in NOISE_CATEGORIES and r.text:
            r.repeats = exact[r.text]
            r.repeat_index = seen[r.text]
            seen[r.text] += 1
        if r.category == "Picture":
            r.role = "picture"
        elif r.category == "Table":
            r.role = "table"
        elif r.category in NOISE_CATEGORIES:
            # Running headers/footers are noise only when they carry no caption:
            # a bare page number, or text repeated on three or more pages.
            repeated = (not r.text or re.fullmatch(r"[-–\s]*\d+[-–\s]*", r.text)
                        or running[re.sub(r"\d+", "#", r.text)] >= REPEAT_THRESHOLD)
            if repeated and not is_caption(r.text):
                r.role = "noise"
    return regions


def logical_paragraphs(regions: list[Region]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    open_body: Paragraph | None = None
    open_note: Paragraph | None = None
    by_page = defaultdict(list)
    for r in regions:
        if r.role == "content":
            by_page[r.page].append(r)
    for r in regions:
        if r.role == "noise":
            continue
        if r.role in {"picture", "table"}:
            paragraphs.append(Paragraph("body", [r], kind=r.role))
            continue
        page_content = by_page[r.page]
        first_on_page = page_content and page_content[0] is r
        if r.category == "Footnote" or footnote_number(r.text) is not None:
            number = region_footnote_number(r)
            if number is None and open_note and open_note.first.page < r.page and not terminated(open_note.text):
                open_note.regions.append(r)
                open_note.evidence.append({"join": "unnumbered_footnote_after_page_break", "region": r.region_id})
                continue
            if (number is None and r.category == "Footnote" and open_note and open_note.regions[-1].page == r.page
                    and final_char(open_note.text) in ":;"):
                # step 21.2 A: «⁸ … следующие постоянные времени:» then «а) 1 с …;» — the list goes on in the footnote
                open_note.regions.append(r)
                open_note.evidence.append({"join": "footnote_list_item", "region": r.region_id})
                continue
            p = Paragraph("footnote", [r], kind="footnote", footnote=number)
            paragraphs.append(p)
            open_note = p
            continue
        # Body text. Join a continuation only with an unterminated open paragraph
        # across a page break, never on the same page (OCR keeps those together).
        if starts_continuation(r.text) and parse_marker(r.text, r.category).kind == "none" and not page_mark(r):
            # A footnote continued on the next page, mislabelled as Text: it sits
            # after the page body, directly before the page's footnotes (or at the end),
            # the previous page's last footnote is unterminated, and it cannot be a
            # body continuation because body continuations open the page.
            later = [x for x in page_content if x.order > r.order]
            before_notes = all(x.category == "Footnote" for x in later)
            body_open_here = open_body is not None and open_body.regions[-1].page == r.page and not terminated(open_body.text)
            if (open_note is not None and open_note.regions[-1].page == r.page - 1 and not terminated(open_note.text)
                    and not first_on_page and before_notes and (r.text[0] == "(" or body_open_here)):
                open_note.regions.append(r)
                open_note.evidence.append({"join": "footnote_continuation_after_page_break", "region": r.region_id})
                continue
            if open_body and open_body.regions[-1].page < r.page and first_on_page and not terminated(open_body.text):
                open_body.regions.append(r)
                open_body.evidence.append({"join": "body_continuation_after_page_break", "region": r.region_id})
                continue
        p = Paragraph("body", [r])
        paragraphs.append(p)
        if page_mark(r) or PAGE_CODE_LINE.fullmatch(r.text.strip()):
            # a file code in the footer belongs to the scope root and never opens a continuation
            p.evidence.append(dict(PAGE_MARK_EVIDENCE))
            continue
        body_here = [x for x in page_content if x.category != "Footnote" and footnote_number(x.text) is None]
        if barcode_like(r.text) and body_here and body_here[-1] is r:
            # a barcode as the last body line of its page is a page requisite, not open text:
            # the next page continues the paragraph before it
            p.evidence.append(dict(BARCODE_EVIDENCE))
            continue
        open_body = p
    return paragraphs
