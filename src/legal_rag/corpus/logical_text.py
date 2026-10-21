"""Stage 2 logical-text layer over OCR ``text-extraction/1`` JSON.

Pass 1 (this slice): classify physical regions as content, running noise,
picture or table. Source text, tokens and locators are never replaced or
mutated; ``match_view`` output is for matching only. Behavior is ported from the
M1-04A prototype ``docs/assets/ocr_logical_structure.py``.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from legal_rag.corpus.compiler import content_hash

SCHEMA = "logical-text/1"
BUILDER = "ocr-logical-text/1"

NOISE_CATEGORIES = {"Page-header", "Page-footer"}
APPROVAL = re.compile(r"^(УТВЕРЖДЕН[АЫО]?|Утвержден[аыо]?)\b(?:\s|$)")  # case-sensitive capitalised word
ANNEX = re.compile(r"^(?:ПРИЛОЖЕНИЕ|Приложение)(?:\s*№\s*(\d+))?(?:\s+(к\s.+))?$")
PAGE_NUMBER = re.compile(r"[-–\s]*\d+[-–\s]*")
REPEAT_THRESHOLD = 3
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
SUP_DIGIT = {c: str(i) for i, c in enumerate(SUP)}
LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"  # legal lettering skips ё, й, ъ, ы, ь
ROMAN_CHARS = "IVXLCХІ"  # Cyrillic Х and Ukrainian І appear in OCR
TERMINAL = ".;:!?"
JOIN_BODY = "body_continuation_after_page_break"
JOIN_NOTE_UNNUMBERED = "unnumbered_footnote_after_page_break"
JOIN_NOTE_CONTINUATION = "footnote_continuation_after_page_break"


def match_view(text: str) -> str:
    """Whitespace/Markdown view for matching only; source text is never replaced."""
    lines = [re.sub(r"^\s*#{1,6}\s+", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def is_caption(text: str) -> str | None:
    """Return ``"approval"`` or ``"annex"`` for caption text, otherwise ``None``."""
    if APPROVAL.match(text):
        return "approval"
    if ANNEX.match(text) and len(text) <= 120:
        return "annex"
    return None


def classify_regions(extraction: dict) -> list[dict]:
    """Region records in page/region order with a content/noise/picture/table role."""
    raw: dict[str, str] = defaultdict(str)
    nodes: dict[str, list] = defaultdict(list)
    for block in extraction["blocks"]:
        raw[block["source_region_id"]] += block["original_text"]
        nodes[block["source_region_id"]].extend(block["text_node_ids"])
    regions = []
    for page in extraction["pages"]:
        for index, region in enumerate(page["regions"]):
            rid = region["region_id"]
            text = raw.get(rid, "")
            regions.append({
                "region_id": rid, "page": page["page"], "index": index, "category": region["category"],
                "bbox": list(region["bbox"]), "text": text, "match_text": match_view(text),
                "text_node_ids": list(nodes.get(rid, [])), "role": "content", "role_reason": None,
            })
    running = Counter(re.sub(r"\d+", "#", r["match_text"])
                      for r in regions if r["category"] in NOISE_CATEGORIES and r["match_text"])
    for r in regions:
        if r["category"] == "Picture":
            r["role"] = "picture"
        elif r["category"] == "Table":
            r["role"] = "table"
        elif r["category"] in NOISE_CATEGORIES:
            # Running text is noise only when it carries no caption: an empty region,
            # a bare page number, or text repeated on three or more regions.
            match_text = r["match_text"]
            if is_caption(match_text):
                continue
            if not match_text:
                reason = "empty_running_region"
            elif PAGE_NUMBER.fullmatch(match_text):
                reason = "page_number"
            elif running[re.sub(r"\d+", "#", match_text)] >= REPEAT_THRESHOLD:
                reason = "repeated_running_text"
            else:
                continue
            r["role"], r["role_reason"] = "noise", reason
    return regions


# --------------------------------------------------------------------------- pass 2


def _roman_value(text: str) -> int | None:
    table = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "Х": 10, "І": 1}
    total = 0
    for i, ch in enumerate(text):
        value = table.get(ch)
        if value is None:
            return None
        if i + 1 < len(text) and table.get(text[i + 1], 0) > value:
            total -= value
        else:
            total += value
    return total or None


def _heading_like(text: str, category: str) -> bool:
    return category in {"Section-header", "Title"} or (len(text) < 250 and not text.rstrip().endswith((".", ";", ":")))


def _has_marker(text: str, category: str) -> bool:
    """True when the text opens with a list/point/heading marker (prototype ``parse_marker`` kind != none)."""
    m = re.match(rf"^([{ROMAN_CHARS}]+)\.\s+\S", text)
    if m and _roman_value(m.group(1)) and _heading_like(text, category):
        return True
    if re.match(r"^(\d{1,3}(?:\.\d{1,3})+)\.?\s+\S", text):
        return True
    if re.match(r"^\d{1,2}\.\s?\d{1,2}\.\s?\d{4}\b", text):
        return False  # a date such as "12. 02. 2026", not point 12
    if re.match(r"^(\d{1,3})\.\s+\S", text) or re.match(r"^(\d{1,3})\)\s+\S", text):
        return True
    m = re.match(r"^([а-я])\)\s+\S", text)
    if m and m.group(1) in LETTERS:
        return True
    return bool(re.match(r"^[-–—]\s+\S", text))


def strip_sup(text: str) -> str:
    return re.sub(rf"[{SUP}]+", "", text).rstrip()


def terminated(text: str) -> bool:
    t = strip_sup(text).rstrip(" »\")")
    return bool(t) and t[-1] in TERMINAL


def starts_continuation(text: str) -> bool:
    return bool(text) and (text[0].islower() or text[0] == "(")


def _sup_int(group: str) -> int:
    return int("".join(SUP_DIGIT[c] for c in group))


def footnote_number(text: str) -> int | None:
    m = re.match(rf"^([{SUP}]+)", text)
    return _sup_int(m.group(1)) if m else None


def _footnote_refs(text: str) -> list[int]:
    groups = re.findall(rf"[{SUP}]+", text)
    if re.match(rf"^[{SUP}]+", text):
        groups = groups[1:]
    return [_sup_int(g) for g in groups]


def _open_paragraphs(regions: list[dict]) -> list[dict]:
    """Group regions into paragraphs (internal: ``regions`` hold region dicts, ``joins`` their join names)."""
    paragraphs: list[dict] = []
    open_body: dict | None = None
    open_note: dict | None = None
    by_page: dict[int, list[dict]] = defaultdict(list)
    for r in regions:
        if r["role"] == "content":
            by_page[r["page"]].append(r)

    def new(flow: str, kind: str, r: dict) -> dict:
        p = {"flow": flow, "kind": kind, "regions": [r], "joins": [None]}
        paragraphs.append(p)
        return p

    def match(p: dict) -> str:
        return match_view("\n".join(x["text"] for x in p["regions"]))

    for r in regions:
        if r["role"] == "noise":
            continue
        if r["role"] in {"picture", "table"}:
            new("body", r["role"], r)
            continue
        if not r["match_text"]:
            new("body", "empty", r)  # D2: never an open paragraph, never joined to
            continue
        page_content = by_page[r["page"]]
        first_on_page = page_content[0] is r
        mt = r["match_text"]
        if r["category"] == "Footnote" or footnote_number(mt) is not None:
            number = footnote_number(mt)
            if (number is None and open_note is not None and open_note["regions"][-1]["page"] == r["page"] - 1
                    and not terminated(match(open_note))):  # D1: adjacent page only
                open_note["regions"].append(r)
                open_note["joins"].append(JOIN_NOTE_UNNUMBERED)
                continue
            open_note = new("footnote", "footnote", r)
            continue
        if starts_continuation(mt) and not _has_marker(mt, r["category"]):
            later = [x for x in page_content if x["region_order"] > r["region_order"]]
            before_notes = all(x["category"] == "Footnote" for x in later)
            body_open_here = (open_body is not None and open_body["regions"][-1]["page"] == r["page"]
                              and not terminated(match(open_body)))
            if (open_note is not None and open_note["regions"][-1]["page"] == r["page"] - 1
                    and not terminated(match(open_note)) and not first_on_page and before_notes
                    and (mt[0] == "(" or body_open_here)):
                open_note["regions"].append(r)
                open_note["joins"].append(JOIN_NOTE_CONTINUATION)
                continue
            if (open_body is not None and open_body["regions"][-1]["page"] == r["page"] - 1
                    and first_on_page and not terminated(match(open_body))):  # D1: adjacent page only
                open_body["regions"].append(r)
                open_body["joins"].append(JOIN_BODY)
                continue
        open_body = new("body", "text", r)
    return paragraphs


def build_logical_text(extraction: dict) -> dict:
    """Logical paragraphs and footnote flow over ``text-extraction/1``; the input is not mutated."""
    regions = classify_regions(extraction)
    known = {r["region_id"] for r in regions}
    for block in extraction["blocks"]:
        if block["source_region_id"] not in known:
            raise ValueError(f"block references unknown source_region_id {block['source_region_id']!r}")
    for order, r in enumerate(regions):
        r["region_order"] = order
    internal = _open_paragraphs(regions)

    paragraphs = []
    owner: dict[str, int] = {}
    for number, p in enumerate(internal):
        fragments, parts, cursor = [], [], 0
        for r, join in zip(p["regions"], p["joins"]):
            if parts:
                cursor += 1  # the "\n" separator
            fragments.append({"region_id": r["region_id"], "page": r["page"], "bbox": list(r["bbox"]),
                              "text_node_ids": list(r["text_node_ids"]), "start": cursor,
                              "end": cursor + len(r["text"]), "join": join})
            parts.append(r["text"])
            cursor += len(r["text"])
            owner[r["region_id"]] = number
        text = "\n".join(parts)
        match_text = match_view(text)
        paragraphs.append({
            "paragraph_id": number, "flow": p["flow"], "kind": p["kind"], "fragments": fragments,
            "text": text, "match_text": match_text,
            "features": {
                "starts_lowercase": starts_continuation(match_text),
                "terminated": terminated(match_text),
                "footnote_number": footnote_number(match_text),
                "footnote_refs": _footnote_refs(match_text),
                "caption": is_caption(p["regions"][0]["match_text"]),
            },
        })

    in_paragraphs = sorted(t for p in paragraphs for f in p["fragments"] for t in f["text_node_ids"])
    in_noise = sorted(t for r in regions if r["role"] == "noise" for t in r["text_node_ids"])
    expected = sorted(t["text_node_id"] for t in extraction["text_nodes"])
    if sorted(in_paragraphs + in_noise) != expected:
        raise ValueError("token accounting: text nodes are not covered exactly once by paragraphs and noise")
    result = {
        "schema_version": SCHEMA, "builder_version": BUILDER,
        "extraction_id": extraction.get("extraction_id"),
        "source_asset_sha256": extraction.get("source_asset_sha256"),
        "regions": [{"region_id": r["region_id"], "page": r["page"], "index": r["index"],
                     "category": r["category"], "role": r["role"], "role_reason": r["role_reason"],
                     "paragraph_id": owner.get(r["region_id"])} for r in regions],
        "paragraphs": paragraphs,
        "accounting": {"text_nodes": len(expected), "in_paragraphs": len(in_paragraphs), "in_noise": len(in_noise)},
    }
    result["logical_text_id"] = content_hash(result)
    return result
