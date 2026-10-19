"""M1-04A experiment: logical paragraphs + marker-sequence depth over text-extraction/1.

Prototype only (not a compiler entry point). Three passes:

1. physical: drop page numbers / repeated running headers, keep every token;
2. logical paragraphs: join cross-region / cross-page continuations of the body
   and of footnotes, without touching source text, tokens or locators;
3. structure: caption-driven scopes (approving act -> approved text -> annexes)
   and a beam search over marker sequences that picks depths by sequence
   continuity (idea from 18F regparser.tree.depth), not by local regexes.

Output paths use a neutral syntax shared with the hand-made gold:
``A`` approving act, ``S`` approved text, ``S/AN4`` annex 4,
``S/II/4/в`` subpoint в) of point 4 in section II.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

VERSION = "ocr-logical-structure/0-experiment"

SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
SUP_DIGIT = {c: str(i) for i, c in enumerate(SUP)}
LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"  # legal lettering skips ё, й, ъ, ы, ь
ROMAN_CHARS = "IVXLCХІ"  # Cyrillic Х and Ukrainian І appear in OCR
TERMINAL = ".;:!?"
NOISE_CATEGORIES = {"Page-header", "Page-footer"}


def roman_value(text: str) -> int | None:
    text = text.upper().replace("Х", "X").replace("І", "I")
    if not text or any(c not in "IVXLC" for c in text):
        return None
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    for i, c in enumerate(text):
        v = values[c]
        total += -v if i + 1 < len(text) and values[text[i + 1]] > v else v
    return total


def to_roman(n: int) -> str:
    out = ""
    for v, s in ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s
            n -= v
    return out


def view(text: str) -> str:
    """Whitespace/Markdown view for matching only; source text is never replaced."""
    lines = [re.sub(r"^\s*#{1,6}\s+", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def strip_sup(text: str) -> str:
    return re.sub(rf"[{SUP}]+", "", text).rstrip()


# --------------------------------------------------------------------------- pass 1


@dataclass
class Region:
    order: int
    page: int
    index: int
    region_id: str
    category: str
    bbox: list
    page_size: list
    raw: str
    text: str
    text_node_ids: list
    role: str = "content"  # content | noise | picture | table


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
    running = Counter(re.sub(r"\d+", "#", r.text) for r in regions if r.category in NOISE_CATEGORIES and r.text)
    for r in regions:
        if r.category == "Picture":
            r.role = "picture"
        elif r.category == "Table":
            r.role = "table"
        elif r.category in NOISE_CATEGORIES:
            # Running headers/footers are noise only when they carry no caption:
            # a bare page number, or text repeated on three or more pages.
            repeated = (not r.text or re.fullmatch(r"[-–\s]*\d+[-–\s]*", r.text)
                        or running[re.sub(r"\d+", "#", r.text)] >= 3)
            if repeated and not is_caption(r.text):
                r.role = "noise"
    return regions


# --------------------------------------------------------------------------- captions and markers


APPROVAL = re.compile(r"^(УТВЕРЖДЕН[АЫО]?|Утвержден[аыо]?)\b(?:\s|$)")  # case-sensitive capitalised word
ANNEX = re.compile(r"^(?:ПРИЛОЖЕНИЕ|Приложение)(?:\s*№\s*(\d+))?(?:\s+(к\s.+))?$")


def is_caption(text: str) -> bool:
    return bool(APPROVAL.match(text)) or (bool(ANNEX.match(text)) and len(text) <= 120)


@dataclass
class Marker:
    kind: str = "none"  # roman | decimal | int | paren | letter | dash | none
    value: object = None
    label: str = ""


def parse_marker(text: str, category: str) -> Marker:
    m = re.match(rf"^([{ROMAN_CHARS}]+)\.\s+\S", text)
    if m and roman_value(m.group(1)) and heading_like(text, category):
        v = roman_value(m.group(1))
        return Marker("roman", v, to_roman(v))
    m = re.match(r"^(\d{1,3}(?:\.\d{1,3})+)\.?\s+\S", text)
    if m:
        parts = tuple(int(p) for p in m.group(1).split("."))
        return Marker("decimal", parts, ".".join(map(str, parts)))
    if re.match(r"^\d{1,2}\.\s?\d{1,2}\.\s?\d{4}\b", text):
        return Marker("none")  # a date such as "12. 02. 2026", not point 12
    m = re.match(r"^(\d{1,3})\.\s+\S", text)
    if m:
        return Marker("int", int(m.group(1)), m.group(1))
    m = re.match(r"^(\d{1,3})\)\s+\S", text)
    if m:
        return Marker("paren", int(m.group(1)), m.group(1))
    m = re.match(r"^([а-я])\)\s+\S", text)
    if m and m.group(1) in LETTERS:
        return Marker("letter", LETTERS.index(m.group(1)) + 1, m.group(1))
    if re.match(r"^[-–—]\s+\S", text):
        return Marker("dash")
    return Marker("none")


def heading_like(text: str, category: str) -> bool:
    return category in {"Section-header", "Title"} or (len(text) < 250 and not text.rstrip().endswith((".", ";", ":")))


def terminated(text: str) -> bool:
    t = strip_sup(text).rstrip(" »\")")
    return bool(t) and t[-1] in TERMINAL


def starts_continuation(text: str) -> bool:
    return bool(text) and (text[0].islower() or text[0] == "(")


def footnote_number(text: str) -> int | None:
    m = re.match(rf"^([{SUP}]+)", text)
    return int("".join(SUP_DIGIT[c] for c in m.group(1))) if m else None


def signature_like(region: Region) -> bool:
    text = region.text
    right = region.bbox[0] > region.page_size[0] * 0.55
    initials = re.fullmatch(r"[А-ЯЁ]\.\s?(?:[А-ЯЁ]\.\s?)?[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?", text)
    title = re.match(r"^(Председатель|Руководитель|Министр|Главный государственный санитарный врач)\b", text)
    return bool(initials or (title and len(text) < 120) or (right and len(text) < 40 and not is_caption(text)))


# --------------------------------------------------------------------------- pass 2


@dataclass
class Paragraph:
    flow: str  # body | footnote
    regions: list = field(default_factory=list)
    marker: Marker = field(default_factory=Marker)
    kind: str = "text"  # text | heading | approval | annex | table | signature | footnote | picture
    footnote: int | None = None
    owner: str | None = None
    evidence: list = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(r.text for r in self.regions)

    @property
    def first(self) -> Region:
        return self.regions[0]


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
            number = footnote_number(r.text)
            if number is None and open_note and open_note.first.page < r.page and not terminated(open_note.text):
                open_note.regions.append(r)
                open_note.evidence.append({"join": "unnumbered_footnote_after_page_break", "region": r.region_id})
                continue
            p = Paragraph("footnote", [r], kind="footnote", footnote=number)
            paragraphs.append(p)
            open_note = p
            continue
        # Body text. Join a continuation only with an unterminated open paragraph
        # across a page break, never on the same page (OCR keeps those together).
        if starts_continuation(r.text) and parse_marker(r.text, r.category).kind == "none":
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
        open_body = p
    return paragraphs


# --------------------------------------------------------------------------- pass 3


def next_letter_ok(prev: int, new: int) -> bool:
    return new == prev + 1


def transitions(stack: tuple, marker: Marker, last_int: int | None):
    """Yield (new_stack, cost) for one marker. Stack items: (kind, value, label)."""
    item = (marker.kind, marker.value, marker.label)
    depth = len(stack)
    for keep in range(depth, -1, -1):  # keep = number of stack entries retained below the new one
        parent = stack[keep - 1] if keep else None
        sibling = stack[keep] if keep < depth else None
        if sibling is not None:
            # continue the sequence at this level
            if sibling[0] == marker.kind:
                if marker.kind in {"int", "paren", "letter", "roman"}:
                    gap = marker.value - sibling[1]
                    if gap == 1:
                        yield stack[:keep] + (item,), 0.0 + 0.01 * (depth - keep)
                    elif 1 < gap <= 3:
                        yield stack[:keep] + (item,), 2.0 + gap
                elif marker.kind == "decimal":
                    a, b = sibling[1], marker.value
                    if len(a) == len(b) and a[:-1] == b[:-1] and b[-1] == a[-1] + 1:
                        yield stack[:keep] + (item,), 0.0 + 0.01 * (depth - keep)
                    elif len(a) == len(b) and a[:-1] != b[:-1] and b[-1] == 1:
                        yield stack[:keep] + (item,), 1.5  # e.g. 2.4 -> 3.1 under a flat section
            continue
        # open a new child level under `parent`
        if marker.kind == "roman":
            if parent is None:
                yield (item,), 0.0 if marker.value == 1 else 1.0
            continue
        if parent is not None and parent[0] == marker.kind and marker.kind != "decimal":
            continue  # same type nested in itself is implausible
        if marker.kind in {"paren", "letter"}:
            if marker.value == 1:
                yield stack[:keep] + (item,), 0.5 if parent is None or parent[0] == "roman" else 0.0
        elif marker.kind == "int":
            if parent is None or parent[0] == "roman":
                if marker.value == 1 or (last_int is not None and marker.value == last_int + 1):
                    yield stack[:keep] + (item,), 0.0
                elif last_int is None:
                    yield stack[:keep] + (item,), 3.0
        elif marker.kind == "decimal":
            v = marker.value
            child_of_decimal = parent is not None and parent[0] == "decimal" and v[:-1] == parent[1] and v[-1] == 1
            child_of_int = parent is not None and parent[0] == "int" and len(v) == 2 and v[0] == parent[1] and v[1] == 1
            if child_of_decimal or child_of_int:
                yield stack[:keep] + (item,), 0.0
            elif (parent is None or parent[0] == "roman") and len(v) == 2 and v[1] == 1:
                matches = parent is not None and parent[1] == v[0]
                yield stack[:keep] + (item,), 0.0 if matches else 1.0
            elif (parent is None or parent[0] == "roman") and len(v) == 2:
                yield stack[:keep] + (item,), 4.0


def solve_depths(markers: list[Marker], beam: int = 64) -> list[tuple]:
    """Beam search over the whole marker sequence of one scope; returns stacks."""
    states = [(0.0, (), None, [])]  # cost, stack, last_int, history
    for marker in markers:
        if marker.kind in {"none", "dash"}:
            states = [(c, s, li, h + [s]) for c, s, li, h in states]
            continue
        nxt = []
        for cost, stack, last_int, hist in states:
            options = list(transitions(stack, marker, last_int))
            if not options:
                options = [(stack + ((marker.kind, marker.value, marker.label),), 10.0)]  # unexplained: deep penalty
            for new_stack, c in options:
                li = marker.value if marker.kind == "int" and len(new_stack) and new_stack[-1][0] == "int" and \
                    (len(new_stack) == 1 or new_stack[-2][0] == "roman") else last_int
                nxt.append((cost + c, new_stack, li, hist + [new_stack]))
        nxt.sort(key=lambda s: s[0])
        seen, states = set(), []
        for s in nxt:
            if s[1] not in seen:
                seen.add(s[1])
                states.append(s)
            if len(states) >= beam:
                break
    return states[0][3]


def path_of(scope: str, stack: tuple) -> str:
    return "/".join([scope] + [entry[2] for entry in stack])


def build(extraction: dict) -> dict:
    regions = load_regions(extraction)
    paragraphs = logical_paragraphs(regions)

    # scopes: approving act until the first approval caption, then approved text,
    # each annex caption opens an annex scope inside the approved text.
    scope = "A"
    scopes: list[tuple[str, list[Paragraph]]] = [("A", [])]
    pending_annex_caption = None
    approved_opened = False
    approved_count = 0
    approved_scope = "S"
    for i, p in enumerate(paragraphs):
        if p.flow == "footnote" or p.kind in {"picture"}:
            scopes[-1][1].append(p)
            continue
        text = p.text
        if p.kind == "text" and APPROVAL.match(text) and len(text) < 300 and not text.endswith("."):
            p.kind = "approval"
            previous = next((q for q in reversed(paragraphs[:i]) if q.flow == "body" and q.kind != "picture"), None)
            if previous is None or previous.kind != "approval" or previous is pending_annex_caption:
                approved_count += 1
                approved_opened = True
                scope = "S" if approved_count == 1 else f"S{approved_count}"
                approved_scope = scope
                scopes.append((scope, []))
                if pending_annex_caption is not None:
                    scopes[-2][1].remove(pending_annex_caption)
                    scopes[-1][1].append(pending_annex_caption)
                    pending_annex_caption = None
            scopes[-1][1].append(p)
            continue
        m = ANNEX.match(text) if p.kind == "text" else None
        if m and len(text) <= 120:
            p.kind = "annex"
            nxt = next((q for q in paragraphs[i + 1:] if q.flow == "body" and q.kind == "text"), None)
            if nxt is not None and APPROVAL.match(nxt.text) and not approved_opened:
                # "Приложение / УТВЕРЖДЕНЫ ..." on the approved text: part of its approval caption
                p.kind = "approval"
                pending_annex_caption = p
                scopes[-1][1].append(p)
                continue
            number = m.group(1)
            label = f"AN{number}" if number else "AN"
            reference = m.group(2) or (nxt.text if nxt is not None and nxt.text.startswith("к ") else "")
            to_act = bool(re.match(r"^к\s+(?:настоящему\s+)?постановлению", reference))
            base = approved_scope if approved_opened and not to_act else "A"
            scope = f"{base}/{label}"
            p.evidence.append({"annex_reference": reference or None, "attached_to": base,
                               "rule": "reference to the act -> act; otherwise the current approved text"})
            scopes.append((scope, [p]))
            continue
        scopes[-1][1].append(p)

    for scope_path, items in scopes:
        body = [p for p in items if p.flow == "body" and p.kind == "text"]
        for p in body:
            p.marker = parse_marker(p.text, p.first.category)
            if p.marker.kind == "roman":
                p.kind = "heading"
        stacks = solve_depths([p.marker for p in body])
        for p, stack in zip(body, stacks):
            if signature_like(p.first) and p.marker.kind == "none":
                p.kind = "signature"
                p.owner = scope_path
            else:
                p.owner = path_of(scope_path, stack)
        # headings/titles before the first marker belong to the scope root (stack empty);
        # tables, captions, pictures follow the current owner
        current = scope_path
        for p in items:
            if p.flow == "body" and p.kind == "text" or p.kind in {"heading", "signature"}:
                current = p.owner if p.kind != "signature" else current
            elif p.flow == "body":
                p.owner = current
        for p in items:
            if p.kind in {"approval", "annex"}:
                p.owner = scope_path

    # footnotes: owner = latest preceding body paragraph carrying the same superscript marker
    body_seen = []
    for p in paragraphs:
        if p.flow == "body":
            body_seen.append(p)
            continue
        number = p.footnote
        if number is None:
            p.owner = None
            p.evidence.append({"footnote_owner": "unnumbered"})
            continue
        token = "".join(SUP[int(d)] for d in str(number))
        hits = [q for q in body_seen if re.search(rf"(?<![{SUP}]){token}(?![{SUP}])", q.text)]
        p.owner = hits[-1].owner if hits else None
        p.evidence.append({"footnote_owner": "marker" if hits else "unresolved", "candidates": len(hits)})

    region_owner = {}
    region_cont = {}
    for p in paragraphs:
        for k, r in enumerate(p.regions):
            region_owner[r.region_id] = p.owner
            region_cont[r.region_id] = k > 0
    # preservation: every OCR token belongs to exactly one region entry
    covered = Counter(t for r in regions for t in r.text_node_ids)
    expected = Counter(t["text_node_id"] for t in extraction["text_nodes"])
    if covered != expected:
        raise ValueError("token accounting mismatch")
    return {
        "schema": "ocr-logical-structure-experiment/0",
        "parser_version": VERSION,
        "source_asset_sha256": extraction["source_asset_sha256"],
        "paragraphs": [{
            "flow": p.flow, "kind": p.kind, "owner": p.owner,
            "marker": None if p.marker.kind in {"none"} else [p.marker.kind, p.marker.label],
            "regions": [{"page": r.page, "index": r.index, "region_id": r.region_id, "category": r.category}
                        for r in p.regions],
            "text_node_ids": [t for r in p.regions for t in r.text_node_ids],
            "text_preview": p.text[:90], "evidence": p.evidence,
        } for p in paragraphs],
        "regions": [{"page": r.page, "index": r.index, "region_id": r.region_id, "category": r.category,
                     "role": r.role, "owner": region_owner.get(r.region_id),
                     "continuation": region_cont.get(r.region_id, False)} for r in regions],
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
