"""Independent source controls. No production parser, scanner or AST imports.

Printed ancestor contexts come from HTML. Unprinted part ordinals are source
claims: their starts must be distinct physical paragraphs inside that article;
their complete sequence is checked separately and is never called printed.
"""

from collections import defaultdict
import copy
import hashlib
from functools import lru_cache
import re

from bs4 import BeautifulSoup, Comment, NavigableString


def compact(text):
    return "".join(text.split())


@lru_cache(maxsize=32768)
def decoded_fragment(markup):
    return compact(BeautifulSoup(markup, "html.parser").get_text())


@lru_cache(maxsize=2)
def byte_offsets(html):
    positions = [0]
    for character in html:
        positions.append(positions[-1] + len(character.encode("utf-8")))
    return positions


def prepare(html, family, source_rows):
    soup = BeautifulSoup(html, "html.parser")
    for tag in list(soup.select("script, style, label")):
        tag.decompose()
    rows, context = [], {}
    words = "ПЕРВАЯ ВТОРАЯ ТРЕТЬЯ ЧЕТВЕРТАЯ ПЯТАЯ ШЕСТАЯ СЕДЬМАЯ ВОСЬМАЯ ДЕВЯТАЯ ДЕСЯТАЯ".split()
    number = r"[0-9]+(?:[.\-][0-9]+)*"
    for ordinal, source in enumerate(soup.find_all("p"), 1):
        p = copy.copy(source)
        for tag in list(p.select(".mark, .markx")):
            tag.decompose()
        normative = not set(p.get("class", [])) & {"A", "F", "N"}
        original = compact(source.get_text())
        for tag in list(p.find_all("br")):
            tag.replace_with(" ")
        normative_compact = compact(p.get_text())
        for tag in list(p.select("sup, .W9, .WB")):
            if tag.parent is not None:
                tag.replace_with("." + tag.get_text())
        text = " ".join(p.get_text().split())
        kind = value = None
        in_table = source.find_parent("table") is not None
        if normative and not in_table:
            if re.fullmatch(r"[_–—-]+", text):
                context = {}
            if re.match(r"^(?:Президент|Председатель Правительства) Российской Федерации", text):
                context = {}
            if re.match(r"^УТВЕРЖД[ЕЁ]Н(?:А|О|Ы)?\b", text):
                context = {"approved_text": ordinal}
                kind = "approved_text"
            elif re.match(r"^ПРИЛОЖЕНИЕ(?:\s|$)", text, re.I):
                context = {k: v for k, v in context.items() if k == "approved_text"}
                kind = "annex"
                match = re.match(rf"^ПРИЛОЖЕНИЕ\s+(?:№\s*)?({number})", text, re.I)
                value = match[1] if match else None
                context[kind] = ordinal
            elif text.upper() in {"ОБЩАЯ ЧАСТЬ", "ОСОБЕННАЯ ЧАСТЬ"} or re.fullmatch(r"ЧАСТЬ (?:[А-Я]+|[IVXLCDM]+|[0-9]+)", text.upper()):
                kind = "upper_part"
                raw = text.upper().removeprefix("ЧАСТЬ ")
                value = str(words.index(raw) + 1) if raw in words else raw if re.fullmatch(r"[IVXLCDM]+|[0-9]+", raw) else None
                context = {kind: ordinal}
            elif match := re.match(rf"^(Статья|Глава|Раздел|§)\s+({number}|[IVXLCDM]+(?:\.[0-9]+)*)(?=[.\s]|$)", text, re.I):
                if match[1].islower() and not text[match.end():].startswith("."):
                    rows.append({"paragraph": ordinal, "html_id": source.get("id"), "text_compact": original,
                                 "normative_compact": normative_compact, "normative": bool(text), "in_table": False,
                                 "kind": None, "number": None, "context": dict(context), "excerpt": text[:240]})
                    continue
                kind = {"статья": "article", "глава": "chapter", "раздел": "section", "§": "subchapter"}[match[1].lower()]
                value = match[2]
                rank = {"upper_part": 0, "approved_text": 0, "annex": 1, "section": 2, "chapter": 3, "subchapter": 4, "article": 5}
                context = {k: v for k, v in context.items() if rank.get(k, 99) < rank[kind]}
                context[kind] = ordinal
            elif family == "government_resolution" and (match := re.match(r"^([IVXLCDM]+(?:\.[0-9]+)*)\.\s", text)):
                kind, value = "section", match[1]
                context = {k: v for k, v in context.items() if k in {"approved_text", "annex"}}
                context[kind] = ordinal
            elif re.match(r"^Примечания?\s*[.:]", text, re.I):
                kind = "notes_section" if text.lower().startswith("примечания") else "normative_note"
                context.pop("leaf", None)
                if family == "government_resolution":
                    context.pop("section", None)
                context["normative_note"] = ordinal
            elif match := re.match(rf'^({number})([.)])(?:\s|$)', text):
                kind = "numeric"
                value = match[1]
                context["leaf"] = ordinal
            elif match := re.match(r"^([а-яa-z](?:\.[0-9]+)?)\)(?:\s|$)", text, re.I):
                kind, value = "letter", match[1].lower()
        rows.append({"paragraph": ordinal, "html_id": source.get("id"), "text_compact": original,
                     "normative_compact": normative_compact, "normative": normative and bool(text),
                     "in_table": in_table, "kind": kind, "number": value,
                     "context": dict(context), "excerpt": text[:240]})
    return {"schema_version": "official-dom-controls/2", "html_sha256": hashlib.sha256(html.encode()).hexdigest(),
            "method": "Raw HTML-only printed heading contexts and all paragraph/media inventory; hidden ordinals separately verified as sidecar claims.",
            "rows": rows, "ownership": source_claim_ownership(html, source_rows, rows),
            "images": [i.get("src") for i in soup.find_all("img")],
            "table_counts": [len(soup.find_all("table")), len(soup.find_all("tr")), len(soup.find_all(["td", "th"]))]}


def source_claim_ownership(html, rows, printed):
    """Independent DOM-event replay of source claims, prepared before any AST.

This is explicitly not an HTML-only oracle for hidden legal part ordinals.
No normalized ranges, AST parents, production regexes or audit results are read.
"""
    soup = BeautifulSoup(html, "html.parser")
    positions, ends = {}, {}
    cursor = 0
    def visit(tag):
        nonlocal cursor
        positions[id(tag)] = cursor
        cursor += 1
        for child in getattr(tag, "contents", []):
            visit(child)
        cursor += 1
        ends[id(tag)] = cursor
    visit(soup)
    ids = {tag["id"]: tag for tag in soup.find_all(id=True)}
    ps = soup.find_all("p")
    claims, stack = [], []
    for row in rows:
        while stack and stack[-1]["level"] >= row["lvl"]:
            stack.pop()
        claim = {"id": row["id"], "parent": stack[-1]["id"] if stack else None, "level": row["lvl"],
                 "unit": row["unit"], "np": row["np"], "start": positions[id(ids[row["np"]])],
                 "end": ends[id(ids[row["npe"]])] if row["npe"] in ids else None}
        claims.append(claim)
        stack.append(claim)
    by_id = {c["id"]: c for c in claims}
    source_parents = {c["id"]: c["parent"] for c in claims}
    for i in range(len(claims) - 1, -1, -1):
        c = claims[i]
        parent = by_id.get(c["parent"])
        if c["end"] is None:
            following = next((n for n in claims[i + 1:] if n["level"] <= c["level"]), None)
            if not following:
                raise ValueError("independent claim replay has no end boundary")
            c["end"] = following["start"]
        if parent and parent["end"] is not None:
            c["end"] = min(c["end"], parent["end"])
    # Fill parent caps again after missing ancestor ends have been resolved.
    for c in claims:
        parent = by_id.get(c["parent"])
        if parent:
            c["end"] = min(c["end"], parent["end"])
    def owner(start, end):
        eligible = [c for c in claims if c["start"] <= start < end <= c["end"]]
        return max(eligible, key=lambda c: c["level"]) if eligible else None
    starts = {c["np"] for c in claims}
    # HTML-only missing letters; the source parent is checked separately against
    # printed article/part contexts. A printed comma/dash closes the list scope.
    alphabet = "абвгдежзиклмнопрстуфхцчшщэюя"
    for i, r in enumerate(printed):
        if not r["excerpt"].endswith(":") or not r["normative"]:
            continue
        p = ps[i]
        parent = owner(positions[id(p)], ends[id(p)])
        if not parent or parent["unit"] not in {"часть", "пункт"}:
            continue
        run = []
        for j in range(i + 1, len(printed)):
            q = printed[j]
            if not q["normative"]:
                continue
            if q["kind"] != "letter" or q["number"] != alphabet[len(run)] or q["html_id"] in starts:
                break
            run.append(j)
        if len(run) < 2:
            continue
        for k, j in enumerate(run):
            q, tag = printed[j], ps[j]
            end = positions[id(ps[run[k + 1]])] if k + 1 < len(run) else parent["end"]
            if k + 1 == len(run) and re.search(r",\s*[-–—]\s*$", q["excerpt"]):
                end = ends[id(tag)]
            claims.append({"id": "html:" + q["html_id"], "parent": parent["id"], "level": parent["level"] + 1,
                           "unit": "html_letter", "np": q["html_id"], "start": positions[id(tag)], "end": end})
    paragraphs = []
    for p in ps:
        c = owner(positions[id(p)], ends[id(p)])
        paragraphs.append(c["id"] if c else None)
    media = []
    for tag in soup.find_all(["table", "img"]):
        c = owner(positions[id(tag)], ends[id(tag)])
        media.append({"tag": tag.name, "owner": c["id"] if c else None})
    outside = []
    for text in soup.descendants:
        if (not isinstance(text, NavigableString) or isinstance(text, Comment) or not compact(str(text))
                or not text.find_parent("body") or text.find_parent(["p", "script", "style", "label"])
                or any(set(tag.get("class", [])) & {"mark", "markx"} for tag in text.parents if tag.name)):
            continue
        c = owner(positions[id(text)], ends[id(text)])
        outside.append({"text": compact(str(text)), "owner": c["id"] if c else None})
    return {"paragraphs": paragraphs, "outside_paragraphs": outside, "media": media, "source_parents": source_parents,
            "method": "DOM event positions from raw np/npe, separate level stack and source-claim boundary replay; missing letters from HTML. Not an independent legal interpretation of sidecar nesting."}


def compare(tree, control, html, source_rows):
    errors = []
    nodes = tree["nodes"]
    by_address = {n["address"]: n for n in nodes}
    lexical = [*nodes, *tree["unresolved_blocks"], *tree["excluded_blocks"]]
    lexical = [n for n in lexical if n.get("block_id") is not None]
    blocks = defaultdict(list)
    for n in lexical:
        blocks[n.get("paragraph")].append(n)
    starts = {p: min(n["html_start"] for n in ns) for p, ns in blocks.items() if p is not None}
    containers = [n for n in nodes if n.get("source_id") or n.get("structure_origin") == "html_recovery"]
    start_nodes = defaultdict(list)
    for n in containers:
        start_nodes[n["source_span"]["char_start"]].append(n)
    for row in control["rows"]:
        ps = sorted(blocks[row["paragraph"]], key=lambda n: n["block_id"])
        if compact("".join(b["original_text"] for b in ps)) != row["text_compact"]:
            errors.append({"kind": "paragraph_text_mismatch", "paragraph": row["paragraph"]})
        if not row["normative"]:
            continue
        normative_text = compact("".join(b["text"] for b in ps if b.get("kind") != "note" and not b.get("exclusion_reason")))
        if normative_text != row["normative_compact"]:
            errors.append({"kind": "normative_text_mismatch", "paragraph": row["paragraph"]})
        if row["number"] is not None and row["kind"] in {"article", "chapter", "section", "subchapter", "annex", "upper_part"}:
            kind = "part" if row["kind"] == "upper_part" else row["kind"]
            matches = [n for n in start_nodes.get(starts.get(row["paragraph"]), []) if n["kind"] == kind]
            if len(matches) != 1 or matches[0].get("number_canonical") != row["number"]:
                errors.append({"kind": "printed_heading_number_conflict", "paragraph": row["paragraph"]})
        for b in ps:
            if b.get("kind") == "note" or b.get("exclusion_reason") or not b["text"]:
                continue
            chain, addr, seen = [], b.get("source_container_address", b.get("parent_address", "act")), set()
            while addr in by_address and addr not in seen:
                seen.add(addr)
                n = by_address[addr]
                chain.append(n)
                addr = n["parent_address"]
            for kind, para in row["context"].items():
                if kind in {"leaf", "normative_note", "approved_text"}:
                    continue
                expected_kind = "part" if kind == "upper_part" else kind
                matches = [n for n in chain if n["kind"] == expected_kind
                           and (kind != "upper_part" or n.get("structural_role") == "upper_division")]
                # Within an annex, an earlier article/section context is cleared by the reader.
                if not matches or matches[0]["source_span"]["char_start"] != starts.get(para):
                    errors.append({"kind": "printed_ancestor_conflict", "paragraph": row["paragraph"],
                                   "block_id": b["block_id"], "expected_kind": kind, "expected_paragraph": para,
                                   "observed": matches[0]["address"] if matches else None})
            if row["kind"] in {"numeric", "letter"} and not row["in_table"]:
                own = [n for n in chain if n.get("number_canonical") == row["number"]
                       and n["source_span"]["char_start"] == starts.get(row["paragraph"])]
                if not own:
                    errors.append({"kind": "printed_marker_owner_conflict", "paragraph": row["paragraph"], "block_id": b["block_id"]})
    source = [n for n in containers if n.get("source_id")]
    if [n["source_id"] for n in source] != [r["id"] for r in source_rows]:
        errors.append({"kind": "source_node_order"})
    if any(n["source_structure_evidence"]["json_pointer"] != f"/data/{i}" for i, n in enumerate(source)):
        errors.append({"kind": "source_pointer"})
    def actual_owner(address):
        seen = set()
        while address in by_address and address not in seen:
            seen.add(address)
            n = by_address[address]
            if n.get("source_id"):
                return n["source_id"]
            if n.get("structure_origin") == "html_recovery":
                return "html:" + n["recovery_evidence"]["html_id"]
            address = n["parent_address"]
        return None
    for n in source:
        if actual_owner(n["parent_address"]) != control["ownership"]["source_parents"][n["source_id"]]:
            errors.append({"kind": "source_parent_claim_conflict", "source_id": n["source_id"]})
    outside = sorted([b for b in nodes if b.get("block_id") is not None and not b.get("paragraph")
                      and b["kind"] != "note" and b["text"]], key=lambda b: b["block_id"])
    expected_outside = control["ownership"]["outside_paragraphs"]
    expected_text = "".join(p["text"] for p in expected_outside)
    if ("".join(compact(b["text"]) for b in outside) != expected_text
            or "".join(compact(b["original_text"]) for b in outside) != expected_text):
        errors.append({"kind": "outside_paragraph_text_mismatch"})
    ranges, cursor = [], 0
    for p in expected_outside:
        ranges.append((cursor, cursor + len(p["text"]), p["owner"]))
        cursor += len(p["text"])
    cursor = 0
    for b in outside:
        end = cursor + len(compact(b["original_text"]))
        expected = {p[2] for p in ranges if p[0] < end and cursor < p[1]}
        if expected != {actual_owner(b.get("source_container_address", b["parent_address"]))}:
            errors.append({"kind": "outside_paragraph_owner_conflict", "block_id": b["block_id"]})
        cursor = end
    ownership_checked = 0
    byte_positions = byte_offsets(html)
    for b in lexical:
        span = b["source_span"]
        start, end = span["char_start"], span["char_end"]
        if (not 0 <= start <= end <= len(html)
                or (html[start:end] != b["original_text"] if b.get("exclusion_reason") == "non_document_text"
                    else decoded_fragment(html[start:end]) != compact(b["original_text"]))
                or span.get("utf8_byte_start") != byte_positions[start] or span.get("utf8_byte_end") != byte_positions[end]):
            errors.append({"kind": "lexical_source_span_mismatch", "block_id": b["block_id"]})
    for b in nodes:
        if b.get("block_id") is None or b["kind"] == "note" or not b["text"]:
            continue
        if not b.get("paragraph"):
            continue
        actual = actual_owner(b.get("source_container_address", b["parent_address"]))
        expected = control["ownership"]["paragraphs"][b["paragraph"] - 1]
        if actual != expected:
            errors.append({"kind": "payload_owner_conflict", "block_id": b["block_id"],
                           "paragraph": b["paragraph"], "expected": expected, "actual": actual})
        ownership_checked += 1
    media_nodes = sorted([n for n in nodes if n["kind"] in {"image", "table"}], key=lambda n: n["source_span"]["char_start"])
    expected_media = control["ownership"]["media"]
    if len(media_nodes) != len(expected_media):
        errors.append({"kind": "media_node_count"})
    for n, expected in zip(media_nodes, expected_media):
        actual = actual_owner(n["parent_address"])
        if actual != expected["owner"]:
            errors.append({"kind": "media_owner_conflict", "address": n["address"], "expected": expected["owner"], "actual": actual})
        span = n["source_span"]
        if n["original_html"] != html[span["char_start"]:span["char_end"]]:
            errors.append({"kind": "ast_media_source_mismatch", "address": n["address"]})
    regions = tree["parsed_regions"]
    if [r["attributes"].get("src") for r in regions if r["tag"] == "img"] != control["images"]:
        errors.append({"kind": "images_mismatch"})
    tables = [r for r in regions if r["tag"] == "table"]
    if [len(tables), sum(len(t["rows"]) for t in tables), sum(len(r["cells"]) for t in tables for r in t["rows"])] != control["table_counts"]:
        errors.append({"kind": "table_counts"})
    return {"errors": errors, "paragraphs_checked": len(control["rows"]), "payloads_checked": ownership_checked,
            "source_nodes": len(source), "images": len(control["images"]), "table_counts": control["table_counts"],
            "limits": "Printed ancestor controls are HTML-only; hidden part ordinals and inner payload scopes are cross-checked source claims, not an independent legal interpretation."}
