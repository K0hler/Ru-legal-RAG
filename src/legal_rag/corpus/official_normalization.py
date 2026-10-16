"""Source-shape normalization with explicit, independently checkable evidence."""

import re
from collections import defaultdict

from bs4 import BeautifulSoup


ORDINALS = {word: str(i) for i, word in enumerate(
    "ПЕРВАЯ ВТОРАЯ ТРЕТЬЯ ЧЕТВЕРТАЯ ПЯТАЯ ШЕСТАЯ СЕДЬМАЯ ВОСЬМАЯ ДЕВЯТАЯ ДЕСЯТАЯ".split(), 1)}


def substantive_gap(markup):
    soup = BeautifulSoup(markup, "html.parser")
    return bool(soup.get_text(strip=True) or soup.find(["img", "table", "svg", "math", "object", "iframe", "video", "audio"]))


def upper_part(text):
    text = text.upper().replace("Ё", "Е")
    if re.fullmatch(r"(?:ОБЩАЯ|ОСОБЕННАЯ) ЧАСТЬ", text):
        return {"number_canonical": None, "number_display": None, "label": text}
    match = re.fullmatch(r"ЧАСТЬ ([А-Я]+|[IVXLCDM]+|[1-9][0-9]*)", text)
    if not match:
        return None
    raw = match[1]
    number = ORDINALS.get(raw)
    if number is None and re.fullmatch(r"[IVXLCDM]+|[1-9][0-9]*", raw):
        number = raw
    return {"number_canonical": number, "number_display": raw, "label": text} if number else None


def approval_evidence(p, caption, end, anchors, normalize):
    """An unfamiliar title requires an approval stamp and matching HTML title."""
    stamp = p
    if not re.match(r"^УТВЕРЖД[ЕЁ]Н(?:А|О|Ы)?\b", normalize(str(stamp)), re.I):
        stamp = p.find_previous("p")
        while stamp is not None and not stamp.get_text(strip=True):
            stamp = stamp.find_previous("p")
    if stamp is None or not re.match(r"^УТВЕРЖД[ЕЁ]Н(?:А|О|Ы)?\b", normalize(str(stamp)), re.I):
        return None
    if not re.search(r"постановлением Правительства Российской Федерации", normalize(str(stamp)), re.I):
        return None
    titles, title_ids = [], []
    q = stamp.find_next("p")
    while q is not None:
        if q.get("id") in anchors and anchors[q["id"]]["start"] >= end:
            break
        text = normalize(str(q))
        if text and not set(q.get("class", [])) & {"A", "F"}:
            if "T" not in q.get("class", []):
                break
            titles.append(text)
            title_ids.append(q.get("id"))
            if " ".join(titles).casefold() == caption.casefold():
                return {"rule": "html-approved-container/1", "stamp_html_id": stamp.get("id"),
                        "title_html_ids": title_ids, "title": caption}
        q = q.find_next("p")
    return None


def resolve_missing_ends(nodes, elements, html):
    """A stale end reference requires the first following peer/ancestor boundary."""
    by_id = {n["source_id"]: n for n in nodes}
    for i in range(len(nodes) - 1, -1, -1):
        node = nodes[i]
        if node["html_end"] is not None:
            continue
        following = next((n for n in nodes[i + 1:] if n["level"] <= node["level"]), None)
        ordinal = bool(following and node.get("number_origin") == following.get("number_origin") == "official_sidecar_ordinal"
                       and node["parent_source_id"] == following["parent_source_id"])
        if not following or not (following.get("heading_verified") or ordinal):
            raise ValueError("missing HTML end anchor without a confirmed next boundary")
        boundary = following["html_start"]
        parent = by_id.get(node["parent_source_id"])
        cap = parent.get("html_end") if parent else None
        if cap is not None and cap < boundary:
            if substantive_gap(html[cap:boundary]):
                raise ValueError("unassigned content after missing sidecar end")
            boundary = cap
        ends = [e["end"] for e in elements if e["tag"] in {"p", "table", "tr", "td", "th"}
                and node["html_start"] <= e["start"] < e["end"] <= boundary]
        if not ends:
            raise ValueError("missing HTML end anchor has no complete content")
        end = max(ends)
        if substantive_gap(html[end:boundary]):
            raise ValueError("unassigned content before confirmed boundary")
        node["source_declared_anchors"] = {"np": node["np"], "npe": node["npe"], "end_anchor_resolved": False}
        node.setdefault("normalization_evidence", []).append({"rule": "confirmed-next-boundary/1",
            "declared_end_html_id": node["npe"], "normalized_end": end,
            "next_html_id": following["np"], "next_source_id": following["source_id"],
            "boundary_basis": "verified_source_ordinal_sequence" if ordinal else "printed_heading"})
        node["html_end"] = end


def reconcile_ranges(nodes, html):
    """Clip an overlong child only at a source parent confirmed by the next heading."""
    by_id = {n["source_id"]: n for n in nodes}
    indices = {n["source_id"]: i for i, n in enumerate(nodes)}
    for i, node in enumerate(nodes):
        parent = by_id.get(node["parent_source_id"])
        if not parent or node["html_end"] <= parent["html_end"]:
            continue
        if not parent["html_start"] <= node["html_start"] < parent["html_end"]:
            raise ValueError("invalid or non-nested sidecar range")
        following = next((n for n in nodes[indices[parent["source_id"]] + 1:]
                          if n["level"] <= parent["level"]), None)
        descendants = []
        for n in nodes[i + 1:]:
            if n["level"] <= node["level"]:
                break
            descendants.append(n)
        end = parent["html_end"]
        if (not following or following["parent_source_id"] != parent["parent_source_id"]
                or not following.get("heading_verified") or following["kind"] not in {"annex", "chapter", "section", "article", "part", "approved_text"}
                or following["html_start"] < end or not descendants
                or max(n["html_end"] for n in descendants) != end
                or any(not node["html_start"] <= n["html_start"] < n["html_end"] <= end for n in descendants)
                or substantive_gap(html[end:following["html_start"]])):
            raise ValueError("ambiguous sidecar range conflict")
        node["source_declared_range"] = (node["html_start"], node["html_end"])
        node.setdefault("normalization_evidence", []).append({"rule": "confirmed-parent-boundary/1",
            "declared_end": node["html_end"], "normalized_end": end, "parent_source_id": parent["source_id"],
            "next_html_id": following["np"], "next_source_id": following["source_id"],
            "last_child_source_id": max(descendants, key=lambda n: n["html_end"])["source_id"]})
        node["html_end"] = end
    sibling_end = {}
    for node in nodes:
        parent = by_id.get(node["parent_source_id"])
        start, end = node["html_start"], node["html_end"]
        if start >= end or parent and not parent["html_start"] <= start < end <= parent["html_end"]:
            raise ValueError("invalid or non-nested sidecar range")
        if start < sibling_end.get(node["parent_source_id"], -1):
            raise ValueError("overlapping sibling ranges")
        sibling_end[node["parent_source_id"]] = end


def verify_part_ordinals(nodes):
    groups = defaultdict(list)
    for n in nodes:
        if n["source_unit"] == "часть":
            groups[n["parent_source_id"]].append(n)
    for parts in groups.values():
        if any(n.get("number_origin") == "official_sidecar_ordinal" for n in parts):
            if [n["number_canonical"] for n in parts] != [str(i) for i in range(1, len(parts) + 1)]:
                raise ValueError("unverified source part ordinal sequence")
