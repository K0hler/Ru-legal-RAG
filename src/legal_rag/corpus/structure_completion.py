"""Bounded syntax completion inside source-supplied containers."""

from collections import defaultdict
import re

from .structure import NUMBER, ROMAN, _number_fields


INTRO = re.compile(r"(?:следующего\s+содержания|в\s+следующей\s+редакции)\s*:", re.I)
DELIMITERS = {'"': '"', '«': '»', '“': '”'}
LETTER = re.compile(r"^([а-я])\)(?:\s|$)", re.I)


def quote_end(text, opening, balance):
    closing = DELIMITERS[opening]
    for index, character in enumerate(text):
        if character not in {opening, closing}:
            continue
        if opening == closing:
            before, after = text[index - 1:index] if index else "", text[index + 1:index + 2]
            opens = bool((not before or before.isspace() or before in "([=:-") and after
                         and not after.isspace() and after not in '.,;:!?)]')
            closes = bool(before and not before.isspace() and (not after or after.isspace() or after in '.,;:!?)]'))
            if opens == closes:
                return None, -1
            balance += 1 if opens else -1
        else:
            balance += 1 if character == opening else -1
        if balance == 0:
            return index, 0
        if balance < 0:
            return None, -1
    return None, balance


def complete_units(blocks, owners):
    """Return empty-token structural nodes and a lexical-block ownership map."""
    grouped = defaultdict(list)
    for b in blocks:
        if (b["text"] and not b["note"] and not b["exclusion_reason"]
                and not set(b["classes"]) & {"A", "F"} and b["paragraph"] is not None and not b.get("table_cell")):
            grouped[b["paragraph"]].append(b)
    ps = []
    for bs in grouped.values():
        first, last = bs[0], bs[-1]
        ps.append({"blocks": bs, "text": " ".join(b["numbering_text"] for b in bs),
                   "start": first["html_start"], "end": last["html_end"],
                   "owner": owners.find(first["source_span"]["char_start"], last["source_span"]["char_end"])})
    specs, ownership, issues, invalid = [], {}, [], set()

    def spec(kind, address, parent, start, end, **fields):
        entry = {"kind": kind, "address": address, "parent": parent, "start": start, "end": end, **fields}
        specs.append(entry)
        return entry

    consumed = set()
    for i, p in enumerate(ps):
        for intro in INTRO.finditer(p["text"]):
            j, offset = i, intro.end()
            tail = p["text"][offset:]
            offset += len(tail) - len(tail.lstrip())
            tail = tail.lstrip()
            if not tail and i + 1 < len(ps):
                j, offset, tail = i + 1, 0, ps[i + 1]["text"]
            if not tail or tail[0] not in DELIMITERS or j in consumed:
                continue
            owner = owners.by_id.get(ps[j]["owner"])
            if not owner or ps[j]["owner"] != p["owner"]:
                issues.append("amendment_quote_owner_unresolved")
                continue
            balance, finish, finish_offset = 0, None, None
            for k in range(j, len(ps)):
                q = ps[k]
                if q["owner"] != owner["source_id"]:
                    break
                end, balance = quote_end(tail if k == j else q["text"], tail[0], balance)
                if balance < 0:
                    break
                if end is not None:
                    finish, finish_offset = k, end
                    break
            if finish is None:
                issues.append("unclosed_or_crossing_amendment_quote")
                invalid.update(b["block_id"] for q in ps[j:k + 1] for b in q["blocks"])
                continue
            selected = ps[j:finish + 1]
            consumed.update(range(j, finish + 1))
            address = f"{owner['address']}/quote/{selected[0]['blocks'][0]['block_id']}"
            quote = spec("quote", address, owner["address"], selected[0]["start"], selected[-1]["end"],
                span_kind="paragraph_envelope", quote_boundary={"start_block_id": selected[0]["blocks"][0]["block_id"],
                    "start": offset, "end_block_id": selected[-1]["blocks"][-1]["block_id"],
                    "end": finish_offset + (offset if finish == j else 0) + 1,
                    "offset_unit": "unicode_codepoints_in_numbering_text"})
            closing_text = ps[finish]["text"]
            closing_index = finish_offset + (offset if finish == j else 0) + 1
            if offset or not re.fullmatch(r"[\s.;,:!?»”)}\]]*", closing_text[closing_index:]):
                issues.append("mixed_paragraph_amendment_quote_boundary")
            stack, seen = [], set()
            for n, q in enumerate(selected):
                text = tail[1:] if n == 0 else q["text"]
                heading = re.match(rf"^(Статья|Глава|Раздел)\s+({NUMBER}|{ROMAN})(?=[.\s]|$)", text, re.I)
                numeric = re.match(rf"^({NUMBER})([.)])(?:\s|$)", text)
                letter = LETTER.match(text)
                kind = number = level = None
                if heading:
                    kind = {"статья": "article", "глава": "chapter", "раздел": "section"}[heading[1].casefold()]
                    level = {"section": 0, "chapter": 1, "article": 2}[kind]
                    number = heading[2]
                elif numeric:
                    in_article = any(s["kind"] == "article" for s in stack)
                    kind = "part" if numeric[2] == "." and in_article else "point" if numeric[2] == "." else "item"
                    level, number = (3 if numeric[2] == "." else 4), numeric[1]
                elif letter:
                    kind, level, number = "subitem", 5, letter[1].casefold()
                if kind:
                    while stack and stack[-1]["level"] >= level:
                        stack.pop()["end"] = selected[max(0, n - 1)]["end"]
                    parent = stack[-1]["address"] if stack else address
                    child = f"{parent}/{kind}/{number.replace('^', '.')}"
                    if child in seen:
                        issues.append("duplicate_quoted_provision")
                        invalid.update(b["block_id"] for b in q["blocks"])
                        continue
                    seen.add(child)
                    stack.append(spec(kind, child, parent, q["start"], quote["end"],
                                      level=level, **_number_fields(number), number_is_explicit=True))
                parent = stack[-1]["address"] if stack else address
                for b in q["blocks"]:
                    ownership[b["block_id"]] = parent

    forms = defaultdict(list)
    for p in ps:
        owner = owners.by_id.get(p["owner"])
        if owner and owner["kind"] == "annex" and "(форма)" in owner["caption"].casefold():
            forms[owner["source_id"]].append(p)
    for owner_id, paragraphs in forms.items():
        owner = owners.by_id[owner_id]
        section = active = listing = None
        previous_number = 0
        for i, p in enumerate(paragraphs):
            heading = re.match(rf"^({ROMAN})\.\s", p["text"])
            number = re.match(r"^([1-9][0-9]*)\.\s", p["text"])
            if heading and set(p["blocks"][0]["classes"]) & {"C", "T"}:
                for entry in (section, listing, active):
                    if entry:
                        entry["end"] = paragraphs[max(0, i - 1)]["end"]
                section = spec("form_section", owner["address"] + "/form_section/" + heading[1], owner["address"],
                               p["start"], owner["html_end"], number_canonical=heading[1],
                               number_display=heading[1], content_context="form", number_is_explicit=True)
                active = listing = None
            elif number:
                if int(number[1]) != previous_number + 1:
                    issues.append("form_number_sequence_unresolved")
                    invalid.update(b["block_id"] for b in p["blocks"])
                    active = None
                    continue
                previous_number = int(number[1])
                parent = section["address"] if section else owner["address"]
                if listing is None:
                    listing = spec("list", parent + "/list/" + str(p["blocks"][0]["block_id"]), parent,
                                   p["start"], section["end"] if section else owner["html_end"], content_context="form")
                if active:
                    active["end"] = paragraphs[max(0, i - 1)]["end"]
                active = spec("list_item", listing["address"] + "/list_item/" + number[1], listing["address"],
                              p["start"], listing["end"], number_canonical=number[1], number_display=number[1],
                              content_context="form", number_is_explicit=True)
            target = active or section
            if target:
                for b in p["blocks"]:
                    ownership[b["block_id"]] = target["address"]

    for i, p in enumerate(ps):
        owner = owners.by_id.get(p["owner"])
        if (not owner or owner["kind"] != "annex" or "(форма)" not in owner["caption"].casefold()
                or not p["text"].rstrip().endswith(":") or i + 1 >= len(ps)):
            continue
        run = []
        alphabet = "абвгдежзиклмнопрстуфхцчшщэюя"
        for q in ps[i + 1:]:
            marker = LETTER.match(q["text"])
            if q["owner"] != p["owner"] or not marker or marker[1].casefold() != alphabet[len(run)]:
                break
            run.append(q)
        if len(run) < 2:
            continue
        parent = ownership.get(p["blocks"][-1]["block_id"], owner["address"])
        address = f"{parent}/list/{run[0]['blocks'][0]['block_id']}"
        spec("list", address, parent, run[0]["start"], run[-1]["end"], content_context="form")
        for q in run:
            number = LETTER.match(q["text"])[1].casefold()
            child = address + "/list_item/" + number
            spec("list_item", child, address, q["start"], q["end"],
                 number_canonical=number, number_display=number, content_context="form", number_is_explicit=True)
            for b in q["blocks"]:
                ownership[b["block_id"]] = child
    return specs, ownership, sorted(set(issues)), invalid
