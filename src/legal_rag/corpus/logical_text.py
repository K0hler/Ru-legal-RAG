"""Stage 2 logical-text layer over OCR ``text-extraction/1`` JSON.

Pass 1 (this slice): classify physical regions as content, running noise,
picture or table. Source text, tokens and locators are never replaced or
mutated; ``match_view`` output is for matching only. Behavior is ported from the
M1-04A prototype ``docs/assets/ocr_logical_structure.py``.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

SCHEMA = "logical-text/1"
BUILDER = "ocr-logical-text/1"

NOISE_CATEGORIES = {"Page-header", "Page-footer"}
APPROVAL = re.compile(r"^(УТВЕРЖДЕН[АЫО]?|Утвержден[аыо]?)\b(?:\s|$)")  # case-sensitive capitalised word
ANNEX = re.compile(r"^(?:ПРИЛОЖЕНИЕ|Приложение)(?:\s*№\s*(\d+))?(?:\s+(к\s.+))?$")
PAGE_NUMBER = re.compile(r"[-–\s]*\d+[-–\s]*")
REPEAT_THRESHOLD = 3


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
