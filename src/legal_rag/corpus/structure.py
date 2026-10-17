"""Shared source-bound legal grammar; no edition admission."""

import re
from collections import Counter
from datetime import date, datetime

from .compiler import content_hash

PARSER_VERSION = "legal-structure/7"
PROFILE_VERSIONS = {"federal_law": "federal-law/5", "code": "code/5",
                    "government_resolution": "government-resolution/3", "sanitary_rules": "sanitary-rules/1"}
NUMBER = r"[1-9][0-9]*(?:[.^-][1-9][0-9]*)*"
ROMAN = r"[IVXLCDM]+(?:[.^-][1-9][0-9]*)*"
SUP_DIGITS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
MONTHS = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()


def _roman_decimal(number):
    if not number or not re.fullmatch(r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})", number):
        return None
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    return sum(-values[c] if i + 1 < len(number) and values[c] < values[number[i + 1]] else values[c]
               for i, c in enumerate(number))


def _identity(blocks: list[dict], declared_identity: str | None) -> dict:
    visible = [
        b for b in blocks if b["text"] and not _is_note(b) and not b["exclusion_reason"]
    ]
    indices = [
        i for i, b in enumerate(visible) if re.match(r"Статья\s+\d", b["text"], re.I)
    ]
    preamble = visible[: indices[0]] if indices else []
    signatures = [
        i
        for i, b in enumerate(visible)
        if indices
        and i > indices[-1]
        and b["text"].startswith("Президент Российской Федерации")
    ]
    signature = visible[signatures[0] :] if len(signatures) == 1 else []
    numbers = [b for b in signature if re.match(r"№\s*\d", b["text"])]
    dates = [b for b in signature if re.fullmatch(r"\d+ [а-я]+ \d{4} года", b["text"])]
    code_titles = [
        b
        for b in preamble
        if re.fullmatch(r"(?:.+ )?кодекс(?: .+)? Российской Федерации", b["text"], re.I)
    ]
    law_headers = [
        i for i, b in enumerate(preamble) if b["text"] == "ФЕДЕРАЛЬНЫЙ ЗАКОН"
    ]
    family = title = None
    title_blocks = []
    if len(code_titles) == 1:
        family, title_blocks = "code", code_titles
    elif not code_titles and len(law_headers) == 1:
        family = "federal_law"
        for block in preamble[law_headers[0] + 1 :]:
            if re.match(r"Принят|Одобрен|Глава|Раздел", block["text"], re.I):
                break
            title_blocks.append(block)
    if title_blocks:
        title = " ".join(b["text"] for b in title_blocks)
    signing_date = number = None
    if len(numbers) == 1 and (
        match := re.fullmatch(r"№\s*([1-9][0-9]*-ФЗ)", numbers[0]["text"])
    ):
        number = match[1]
    if len(dates) == 1:
        day, month, year, _ = dates[0]["text"].split()
        try:
            signing_date = date(
                int(year), MONTHS.index(month) + 1, int(day)
            ).isoformat()
        except ValueError:
            pass
    government_header = [b for b in visible[:5]
                         if b["text"] == "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ"]
    if government_header:
        boundary = next((i for i, b in enumerate(visible)
                         if re.match(r"УТВЕРЖДЕН", b["text"], re.I)), len(visible))
        root = visible[:boundary]
        types = [b for b in root if b["text"] == "ПОСТАНОВЛЕНИЕ"]
        requisites = [(b, re.fullmatch(r"от (\d+) ([а-я]+) (\d{4}) г\. № ([1-9][0-9]*)", b["text"]))
                      for b in root]
        requisites = [(b, m) for b, m in requisites if m]
        title_blocks = [b for b in root if "Z" in b["classes"]]
        signature = [b for b in root if b["text"].startswith("Председатель Правительства Российской Федерации")]
        family, title, number, signing_date = "government_resolution", None, None, None
        if len(types) == len(requisites) == len(title_blocks) == len(signature) == 1:
            title = title_blocks[0]["text"]
            match = requisites[0][1]
            number = match[4]
            try:
                signing_date = date(int(match[3]), MONTHS.index(match[2]) + 1, int(match[1])).isoformat()
            except ValueError:
                pass
        preamble = [*government_header, *types, *(b for b, _ in requisites)]
        law_headers = list(range(len(preamble)))
    matches = bool(family and title and number and signing_date)
    if declared_identity is not None:
        claim = " ".join(declared_identity.split())
        claimed = re.fullmatch(
            r'(Федеральный закон|Кодекс Российской Федерации|Постановление Правительства Российской Федерации) от (\d{2}\.\d{2}\.\d{4}) № ([1-9][0-9]*(?:-ФЗ)?) "([^"]+)"',
            claim,
        )
        try:
            claimed_date = (
                datetime.strptime(claimed[2], "%d.%m.%Y").date().isoformat()
                if claimed
                else None
            )
        except ValueError:
            claimed_date = None
        matches = bool(
            matches
            and claimed
            and claimed_date == signing_date
            and claimed[3] == number
            and claimed[4].casefold() == title.casefold()
            and {"Федеральный закон": "federal_law", "Кодекс Российской Федерации": "code",
                 "Постановление Правительства Российской Федерации": "government_resolution"}[claimed[1]] == family
        )
    return {
        "status": (
            "claim_matches_header"
            if declared_identity is not None
            else "source_identity_matches"
        )
        if matches
        else "unresolved",
        "act_id": content_hash(
            {
                "family": family,
                "number": number,
                "signing_date": signing_date,
                "title": title,
            }
        ),
        "declared_identity": declared_identity,
        "family": family,
        "title": title,
        "number": number,
        "signing_date": signing_date,
        "signature_block_ids": [b["block_id"] for b in signature],
        "evidence_block_ids": [
            b["block_id"]
            for b in [*[preamble[i] for i in law_headers], *title_blocks, *signature]
        ],
        "meaning": "source identity only; no authenticity, edition coverage or legal admission",
    }


def _number_fields(number: str) -> dict:
    base, separator, exponent = number.partition("^")
    return {
        "number_canonical": number.replace("^", "."),
        "number_display": base + (exponent.translate(SUP_DIGITS) if separator else ""),
        "number_components": {"base": base, "superscript": exponent or None},
    }


def _is_note(block: dict) -> bool:
    return bool(
        block["note"]
        or set(block["classes"]) & {"A", "F"}
        or block["text"].startswith(
            ("Примечание", "(В редакции", "(Особенности", "(С учетом")
        )
    )


def _note_fields(block: dict) -> dict:
    text = block["text"]
    date = re.search(r"\bс\s+(\d{2}\.\d{2}\.\d{4})", text)
    effective = None
    if date:
        try:
            effective = datetime.strptime(date[1], "%d.%m.%Y").date().isoformat()
        except ValueError:
            pass
    if "F" in block["classes"]:
        kind = "future_change"
    elif re.search(r"утратил[аои]?\s+силу", text, re.I):
        kind = "repeal_notice"
    elif "несоответствии Конституции" in text:
        kind = "constitutional_application"
    elif "Особенности применения" in text:
        kind = "application"
    elif re.search(r"В редакции|Дополнение|изменяющих", text, re.I):
        kind = "amendment_history"
    else:
        kind = "editorial"
    return {"note_type": kind, "effective_date_claim": effective}


def build_structure(
    extraction: dict, declared_identity: str | None = None, role: str = "consolidated", *, identity_decision: dict | None = None
) -> dict:
    """Build source-bound diagnostic addresses; never infer an effective edition."""
    source_blocks = extraction.get(
        "blocks", extraction.get("pages", [{}])[0].get("blocks", [])
    )
    blocks = [{"classes": [], "display_text": b["text"], **b} for b in source_blocks]
    identity = identity_decision if identity_decision is not None else _identity(blocks, declared_identity)
    namespace = (
        "act"
        if role != "amendment"
        else "amendment/" + extraction["source_asset_sha256"]
    )
    profile = PROFILE_VERSIONS.get(identity["family"], "unsupported")
    resolution = identity["family"] in {"government_resolution", "sanitary_rules"}
    nodes: list[dict] = []
    unresolved: list[dict] = []
    excluded: list[dict] = []
    counters: Counter = Counter()
    addresses = set()
    anchor_paragraphs: dict[str, set[int]] = {}
    for block in blocks:
        if block["html_id"]:
            anchor_paragraphs.setdefault(block["html_id"], set()).add(
                block["paragraph"]
            )
    duplicate_anchors = {
        key for key, values in anchor_paragraphs.items() if len(values) > 1
    }
    paragraph_text: dict[int, str] = {}
    for block in blocks:
        if block["paragraph"] is not None:
            # Notes cannot supply markers, but their breaks still separate norms.
            text = block["original_text"]
            if _is_note(block):
                text = re.sub(r"\S", "", text)
            paragraph_text[block["paragraph"]] = (
                paragraph_text.get(block["paragraph"], "") + text
            )
    ambiguous_paragraphs = {
        paragraph
        for paragraph, text in paragraph_text.items()
        if re.search(
            r"[\r\n]\s*(?:Статья\s+\d|§\s+\d|Глава\s+[IVXLCDM\d]|Раздел\s+"
            r"[IVXLCDM\d]|\d+(?:[.^-]\d+)*[.)](?:\s|$)|[а-я]\)(?:\s|$))",
            text,
            re.I,
        )
    }
    section = chapter = subchapter = article = part = item = subitem = None
    container = namespace
    list_order = None
    active_table = table_context = None
    approved_titles = {}
    quote = None
    quote_context = None
    quote_parity = 0
    quote_delimiters = None
    structural_issues = []
    unresolved_section = False
    last = last_paragraph = None
    regions = extraction.get("unsupported_regions", [])
    unresolved_regions: list[dict] = []
    parsed_regions = []
    image_events = []
    paragraph_parents = {}
    table_addresses = {}
    following_title_ids = {}
    approval_metadata = {}
    region_paragraphs = {r["paragraph"] for r in regions if r["paragraph"] is not None
                         and not (resolution and r["tag"] == "img")}
    signing_ids = set(identity["signature_block_ids"])
    first_article = next(
        (
            b["block_id"]
            for b in blocks
            if re.match(r"\d+\.(?:\s|$)" if resolution else r"Статья\s+\d", b["text"], re.I)
            and not b["exclusion_reason"]
            and not _is_note(b)
        ),
        len(blocks),
    )

    def numbered(parent, kind):
        counters[(parent, kind)] += 1
        return f"{parent}/{kind}/{counters[(parent, kind)]}"

    def add_node(entry, fields, kind, address, parent):
        addresses.add(address)
        nodes.append({**entry, **fields, "kind": kind, "address": address,
                      "parent_address": parent,
                      "node_id": content_hash({"source": extraction["source_asset_sha256"],
                                               "profile": PARSER_VERSION + "+" + profile,
                                               "address": address}),
                      "legal_status": "unverified"})

    def region_entry(region):
        return {**region, "block_id": None, "text": "", "display_text": "", "original_text": "",
                "html_start": region["source_span"]["char_start"],
                "html_end": region["source_span"]["char_end"],
                "html_id": region.get("attributes", {}).get("id"), "text_node_ids": []}

    def following_title(block):
        titles = []
        for candidate in blocks[block["block_id"] + 1:]:
            if candidate["text"] and not _is_note(candidate) and not candidate["exclusion_reason"]:
                if "T" in candidate["classes"] and not (identity_decision is not None and re.match(rf"{ROMAN}\.\s", candidate["numbering_text"], re.I)):
                    titles.append(candidate)
                    if identity_decision is None:
                        break
                    continue
                if candidate["text"] != "(форма)":
                    break
        following_title_ids[block["block_id"]] = [b["block_id"] for b in titles]
        return " ".join(b["text"] for b in titles) or None

    events = sorted([*blocks, *regions], key=lambda e: e["source_span"]["char_start"])
    for block in events:
        if active_table and block["source_span"]["char_start"] >= active_table["source_span"]["char_end"]:
            section, article, part, item, subitem, last, last_paragraph, list_order = table_context
            active_table = table_context = None
        if "region_id" in block:
            if resolution and identity["status"] != "unresolved" and container:
                if block["tag"] == "img":
                    image_events.append((block, subitem or item or part or section or container))
                    continue
                if block["tag"] == "table" and not block["nested"]:
                    parent = subitem or item or part or section or container
                    address = numbered(parent, "table")
                    add_node(region_entry(block), {}, "table", address, parent)
                    parsed_regions.append(block)
                    table_addresses[block["region_id"]] = address
                    table_context = section, article, part, item, subitem, last, last_paragraph, list_order
                    active_table = block
                    part = item = subitem = last = None
                    continue
            unresolved_regions.append(block)
            article = part = item = subitem = last = None
            if resolution:
                container = None
            continue
        entry = {
            k: block[k]
            for k in (
                "block_id",
                "text",
                "display_text",
                "original_text",
                "original_html",
                "html_start",
                "html_end",
                "html_id",
                "source_span",
                "text_node_ids",
                "paragraph",
            )
        }
        entry["table_cell"] = block.get("table_cell")
        if block.get("layout_kind"):
            entry.update({k: block[k] for k in ("source_spans", "source_block_ids", "source_region_id", "layout_kind")})
        if block["exclusion_reason"] or not block["text"]:
            excluded.append(
                {**entry, "reason": block["exclusion_reason"] or "whitespace"}
            )
            continue
        text, numbering = block["text"], block["numbering_text"]
        classes = set(block["classes"])
        table = next((r for r in regions if r["tag"] == "table"
                      and r["source_span"]["char_start"] < block["source_span"]["char_start"]
                      < r["source_span"]["char_end"]), None)
        supported_cell = resolution and table and table["region_id"] in table_addresses and block.get("table_cell")
        if supported_cell:
            entry["table_address"] = table_addresses[table["region_id"]]
        close_quote = False
        amending = resolution and (identity_decision is not None and role == "amendment" or any(container and container.startswith(a)
                                      and title.casefold().startswith("изменения") for a, title in approved_titles.items()))
        if amending and not _is_note(block):
            if numbering.startswith(('"', '«', '“')) and quote is None and (part or item or subitem):
                parent = subitem or item or part
                quote_context = (container, section, part, item, subitem, list_order)
                quote = numbered(parent, "quote")
                quote_delimiters = {'"': ('"', '"'), '«': ('«', '»'), '“': ('“', '”')}[numbering[0]]
                anchor = {**entry, "anchor_block_id": entry["block_id"], "block_id": None,
                          "text": "", "display_text": "", "original_text": "", "text_node_ids": []}
                add_node(anchor, {}, "quote", quote, parent)
                container, section, part, item, subitem = quote, None, None, None, None
                list_order = None
                numbering = numbering[1:]
            if quote:
                opening, closing = quote_delimiters
                if opening == closing:
                    for i, character in enumerate(text):
                        if character != opening:
                            continue
                        before, after = text[i - 1:i] if i else "", text[i + 1:i + 2]
                        opens = not before or before.isspace() or (before in "([=:-" and after
                                and not after.isspace() and after not in '.,;:!?)]')
                        closes = bool(before and not before.isspace() and
                                      (not after or after.isspace() or after in '.,;:!?)]'))
                        if opens == closes:
                            structural_issues.append("ambiguous_amendment_quote")
                        else:
                            quote_parity += 1 if opens else -1
                else:
                    quote_parity += text.count(opening) - text.count(closing)
                close_quote = quote_parity == 0
        kind = address = parent = None
        fields = {}
        reason = "unsupported_or_ambiguous_structure"
        if identity["status"] == "unresolved":
            reason = "identity_unresolved"
        elif block["html_id"] in duplicate_anchors:
            reason = "duplicate_html_id"
        elif block["unsupported_structure"] and not supported_cell:
            reason = "unsupported_table_or_list"
        elif block["paragraph"] in region_paragraphs:
            reason = "unsupported_nontext_or_structure"
        elif block["paragraph"] is None:
            reason = "unaddressed_document_text"
        elif block["paragraph"] in ambiguous_paragraphs:
            reason = "multiple_provision_markers"
        elif block["block_id"] in approval_metadata:
            kind, parent = "metadata", approval_metadata[block["block_id"]]
            address = numbered(parent, kind)
        elif unresolved_section and not re.match(rf"^(?:{ROMAN}\.\s|ПРИЛОЖЕНИЕ\b|УТВЕРЖДЕН)", numbering, re.I):
            reason = "document_scope_unresolved"
        elif block.get("layout_kind") == "table":
            kind, parent = "table", subitem or item or part or section or container or namespace
            address = numbered(parent, kind)
            fields = {"table_cells": block["table_cells"], "table_topology": block["table_topology"]}
        elif block.get("layout_kind") in {"image", "page_header", "page_footer"}:
            kind, parent = "image" if block["layout_kind"] == "image" else "metadata", namespace
            address = numbered(parent, kind)
            fields = {"transcription_status": "unverified", "scope_status": "physical_metadata"}
        elif block.get("layout_kind") == "footnote":
            match = re.match(r"^([⁰¹²³⁴⁵⁶⁷⁸⁹]+|[1-9][0-9]*)[.)]?\s+", text)
            if match:
                number = match[1].translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))
                marker = number.translate(SUP_DIGITS)
                reference = re.compile(r"(?<![⁰¹²³⁴⁵⁶⁷⁸⁹])" + marker + r"(?![⁰¹²³⁴⁵⁶⁷⁸⁹])")
                owners = [n for n in nodes if n["kind"] in {"point", "part", "item", "subitem", "paragraph"}
                          and reference.search(n["text"])]
                parent = owners[-1]["address"] if owners else namespace
                kind, address = "footnote", f"{parent}/footnote/{number}"
                fields = {**_number_fields(number), "scope_status": "explicit_marker" if owners else "unresolved"}
                if not owners:
                    structural_issues.append("footnote_scope_unresolved")
            else:
                reason = "unsupported_footnote_marker"
        elif resolution and container and re.fullmatch(r"Примечани[ея]:?", text, re.I):
            kind, parent = "notes_section", container
            address = numbered(parent, "notes")
            container, section, part, item, subitem = address, None, None, None, None
        elif resolution and container and not block["note"] and not classes & {"A", "F"} and re.match(r"Примечани[ея][.:]\s", text):
            kind, parent = "normative_note", container
            address = numbered(parent, kind)
            part = item = subitem = None
        elif _is_note(block):
            parent = (
                last if last and last_paragraph == block["paragraph"] else namespace
            )
            kind, address = "note", numbered(parent, "note")
            fields = {
                **_note_fields(block),
                "scope_status": "same_paragraph"
                if parent != namespace
                else "unresolved",
            }
        elif resolution and re.fullmatch(r"_{3,}", text) and "C" in classes:
            excluded.append({**entry, "reason": "typographic_separator"})
            continue
        elif resolution and re.match(r"УТВЕРЖДЕН", text, re.I):
            approval_anchor, approval_text, approval_blocks = block, text, [block]
            if identity_decision is not None and re.fullmatch(r"УТВЕРЖДЕН[АЫО]?", text, re.I):
                for candidate in blocks[block["block_id"] + 1:]:
                    if candidate["exclusion_reason"] or not candidate["text"]:
                        continue
                    if len(approval_blocks) == 1 and not candidate["text"].casefold().startswith("постановлением "):
                        break
                    approval_blocks.append(candidate)
                    approval_text += " " + candidate["text"]
                    approval_anchor = candidate
                    if re.search(r"№\s*[1-9][0-9]*$", candidate["text"]) or len(approval_blocks) == 5:
                        break
            title = following_title(approval_anchor)
            issuer = identity.get("issuer") or "Правительства Российской Федерации"
            match = re.fullmatch(r"УТВЕРЖДЕН[АЫО]? постановлением " + re.escape(issuer) + r" от (\d+) ([а-я]+) (\d{4}) г\. № ([1-9][0-9]*)", approval_text, re.I)
            approved_date = None
            approved_number = None
            if match:
                approved_number = match[4]
                try:
                    approved_date = date(int(match[3]), MONTHS.index(match[2]) + 1, int(match[1])).isoformat()
                except ValueError:
                    pass
            elif identity_decision is not None:
                numeric = re.fullmatch(r"УТВЕРЖДЕН[АЫО]? постановлением " + re.escape(issuer)
                                      + r" от (\d{2}\.\d{2}\.\d{4}) г\. № ([1-9][0-9]*)", approval_text, re.I)
                if numeric:
                    try:
                        approved_date = datetime.strptime(numeric[1], "%d.%m.%Y").date().isoformat()
                        approved_number = numeric[2]
                    except ValueError:
                        pass
            if title and approved_number == identity["number"] and approved_date == identity["signing_date"]:
                kind, parent = "approved_text", namespace
                address = numbered(parent, "approved")
                fields = {"title": title}
                if identity_decision is not None:
                    fields["title_block_ids"] = following_title_ids[approval_anchor["block_id"]]
                    fields["approval_evidence_block_ids"] = [b["block_id"] for b in approval_blocks]
                    approval_metadata.update({b["block_id"]: address for b in approval_blocks[1:]})
                approved_titles[address] = title
                container = address
            else:
                reason, container = "approval_identity_or_title_unresolved", None
            section = chapter = subchapter = article = part = item = subitem = None
            list_order = None
        elif resolution and re.match(r"ПРИЛОЖЕНИЕ(?:\s|$)", text, re.I):
            marker = rf"(?: (?:№ )?({NUMBER}))?" if identity_decision is not None else rf"(?: № ({NUMBER}))?"
            match = re.fullmatch(rf"ПРИЛОЖЕНИЕ{marker} к (.+)", numbering, re.I)
            targets = []
            if match:
                target = re.sub(r"^Правилам\b", "Правила", match[2], flags=re.I)
                targets = [a for a, title in approved_titles.items() if title.casefold() == target.casefold()]
                if identity_decision is not None and not targets:
                    designation = re.search(r"\b(?:СП|СанПиН)\s+(\d+(?:[./]\d+)+(?:-\d+)?)", target, re.I)
                    if designation:
                        targets = [a for a, title in approved_titles.items() if designation[1] in title]
            own_act = False
            if identity_decision is not None and match and not targets:
                reference = re.fullmatch(r"постановлению " + re.escape(identity["issuer"])
                    + r" от (\d+) ([а-я]+) (\d{4}) г\. № ([1-9][0-9]*)", match[2], re.I)
                if reference:
                    try:
                        own_act = (reference[4] == identity["number"] and
                                   date(int(reference[3]), MONTHS.index(reference[2].casefold()) + 1,
                                        int(reference[1])).isoformat() == identity["signing_date"])
                    except ValueError:
                        pass
                if own_act:
                    targets = [namespace]
            if len(targets) == 1 and following_title(block):
                kind, parent = "annex", targets[0]
                fields = {**(_number_fields(match[1] or "1") if not own_act or match[1] else {"number_canonical": None}), "title": following_title(block),
                          "number_is_explicit": match[1] is not None}
                if identity_decision is not None:
                    fields["title_block_ids"] = following_title_ids[block["block_id"]]
                address = (numbered(parent, "unnumbered_annex") if own_act and not match[1]
                           else f"{parent}/annex/{fields['number_canonical']}")
                container = address
            else:
                reason, container = "annex_target_unresolved", None
            section = chapter = subchapter = article = part = item = subitem = None
            list_order = None
        elif resolution and not container:
            reason = "document_scope_unresolved"
        elif resolution and "T" in classes and container != namespace and any(
            n["address"] == container and (text == n.get("title") or block["block_id"] in n.get("title_block_ids", [])) for n in nodes):
            kind, parent = "heading", container
            address = numbered(parent, kind)
        elif resolution and "N" in classes and (match := re.match(r"^\^([1-9][0-9]*)\s", numbering)):
            kind, parent = "footnote", container
            fields = _number_fields(match[1])
            address = f"{parent}/footnote/{match[1]}"
        elif resolution and "N" in classes:
            reason = "unsupported_footnote_marker"
        elif supported_cell and active_table and any(table_context[2:5]):
            kind, parent = "table_cell", entry["table_address"]
            address = numbered(parent, kind)
        elif resolution and (match := re.fullmatch(rf"({ROMAN})\.\s+(.+)", numbering)):
            kind, parent = "section", container
            fields = {**_number_fields(match[1]), "title": match[2]}
            address = f"{parent}/section/{fields['number_canonical']}"
            section, part, item, subitem = address, None, None, None
            list_order = None
            unresolved_section = False
        elif resolution and supported_cell and block["table_cell"]["column"] > 0:
            kind, parent = "table_cell", part or entry["table_address"]
            address = numbered(parent, kind)
        elif resolution and (match := re.match(rf"^({NUMBER})\.(?:\s|$)", numbering)
                             or (identity_decision is not None and re.match(r"^([1-9][0-9]*(?:\.[1-9][0-9]*)+)\s+(?=[А-ЯA-Z])", numbering))):
            kind, parent = "point", section or container
            fields = _number_fields(match[1])
            address = f"{container}/point/{fields['number_canonical']}"
            if identity_decision is not None and "." in match[1]:
                prefix = match[1].rsplit(".", 1)[0]
                parents = [n for n in nodes if n["kind"] in {"point", "subitem"}
                           and n.get("number_canonical") == prefix and n["address"].startswith(container + "/")]
                if parents:
                    kind, parent = "subitem", parents[-1]["address"]
                    address = f"{parent}/subitem/{fields['number_canonical']}"
                else:
                    section_number = next((n.get("number_canonical") for n in nodes if n["address"] == section), None)
                    if str(_roman_decimal(section_number)) != prefix:
                        kind, reason = None, "decimal_parent_unresolved"
            part, item, subitem = address, None, None
            list_order = None
        elif resolution and (part or quote) and (match := re.match(rf"^({NUMBER})\)(?:\s|$)", numbering)):
            list_order = list_order or "numeric_first"
            kind, parent = "item", (subitem if list_order == "alpha_first" else None) or part or container
            fields = _number_fields(match[1])
            address = f"{parent}/item/{fields['number_canonical']}"
            item = address
            if list_order == "numeric_first":
                subitem = None
        elif resolution and (part or quote or section) and (match := re.match(r"^([а-яa-z](?:\^[1-9][0-9]*)?)\)\s", numbering)):
            list_order = list_order or "alpha_first"
            kind, parent = "subitem", (item if list_order == "numeric_first" else None) or part or section or container
            fields = _number_fields(match[1])
            address = f"{parent}/subitem/{fields['number_canonical']}"
            subitem = address
            if list_order == "alpha_first":
                item = None
        elif (
            block["block_id"] < first_article
            and (
                not classes & {"H", "T"}
                or block["block_id"] in identity["evidence_block_ids"]
            )
            and not re.match(
                r"^(?:Глава|Раздел|Приложение|Таблица|§)(?:\s|$)", text, re.I
            )
            or block["block_id"] in signing_ids
        ):
            kind, parent = "header", namespace
            address = numbered(parent, kind)
            article = part = item = subitem = None
        elif match := re.fullmatch(rf"Раздел ({ROMAN})\.?\s+(.+)", numbering, re.I):
            kind, parent = "section", namespace
            fields = {**_number_fields(match[1]), "title": match[2]}
            address = f"{namespace}/section/{fields['number_canonical']}"
            section, chapter, subchapter, article, part, item, subitem = (
                address,
                None,
                None,
                None,
                None,
                None,
                None,
            )
        elif match := re.fullmatch(
            rf"Глава ({NUMBER}|{ROMAN})\.?\s+(.+)", numbering, re.I
        ):
            kind, parent = "chapter", section or namespace
            fields = {**_number_fields(match[1]), "title": match[2]}
            address = f"{namespace}/chapter/{fields['number_canonical']}"
            chapter, subchapter, article, part, item, subitem = (
                address,
                None,
                None,
                None,
                None,
                None,
            )
        elif chapter and (match := re.fullmatch(rf"§ ({NUMBER})\.\s+(.+)", numbering)):
            kind, parent = "subchapter", chapter
            fields = {**_number_fields(match[1]), "title": match[2]}
            address = f"{chapter}/subchapter/{fields['number_canonical']}"
            subchapter, article, part, item, subitem = address, None, None, None, None
        elif match := re.fullmatch(
            rf"Статья ({NUMBER})\.(?:\s+(.+))?", numbering, re.I
        ):
            kind, parent = "article", subchapter or chapter or section or namespace
            fields = {**_number_fields(match[1]), "title": match[2]}
            address = f"{namespace}/article/{fields['number_canonical']}"
            article, part, item, subitem = address, None, None, None
        elif classes & {"H", "T"} or re.match(
            r"^(?:Статья|Глава|Раздел|Приложение|Таблица|§)(?:\s|$)", text, re.I
        ):
            reason = "unknown_heading"
            if resolution:
                if identity_decision is not None and container and re.match(r"^[IVXLCDMХ]+\.\s", numbering, re.I):
                    unresolved_section = True
                else:
                    container = None
            if "T" in classes or text.casefold().startswith("раздел"):
                section = chapter = subchapter = None
            elif text.casefold().startswith("глава"):
                chapter = subchapter = None
            elif text.startswith("§"):
                subchapter = None
        elif article and (match := re.match(rf"^({NUMBER})\.(?:\s|$)", numbering)):
            kind, parent = "part", article
            fields = _number_fields(match[1])
            address = f"{parent}/part/{fields['number_canonical']}"
            part, item, subitem = address, None, None
        elif article and (match := re.match(rf"^({NUMBER})\)(?:\s|$)", numbering)):
            kind, parent = "item", part or article
            fields = _number_fields(match[1])
            address = f"{parent}/item/{fields['number_canonical']}"
            item, subitem = address, None
        elif (
            article
            and (item or part)
            and (match := re.match(r"^([а-яa-z])\)\s", numbering))
        ):
            kind, parent = "subitem", item or part
            fields = _number_fields(match[1])
            address = f"{parent}/subitem/{fields['number_canonical']}"
            subitem = address
        elif article and re.match(
            r"^(?:\d+(?:[.^-]\d+)*[.)]|[а-яa-zA-ZА-Я][.)]\s)", numbering
        ):
            reason = "unknown_numbering"
        elif article:
            kind, parent = "paragraph", subitem or item or part or article
            address = numbered(parent, kind)
            fields = {
                "ordinal": counters[(parent, kind)],
                "ordinal_is_diagnostic": True,
            }
        elif resolution and re.match(r"^(?:\d+(?:[.^-]\d+)*[.)]|[а-яa-zA-ZА-Я][.)]\s)", numbering):
            reason = "unknown_numbering"
        elif resolution and container:
            kind, parent = "paragraph", subitem or item or part or section or container
            if supported_cell:
                kind, parent = "table_cell", part or entry["table_address"]
            address = numbered(parent, kind)
            fields = {"ordinal": counters[(parent, kind)], "ordinal_is_diagnostic": True}
        if address in addresses:
            if resolution and kind in {"annex", "approved_text"}:
                container = None
            if kind == "section":
                section = chapter = subchapter = None
            elif kind == "chapter":
                chapter = subchapter = None
            elif kind == "subchapter":
                subchapter = None
            reason, kind = "duplicate_address", None
        if kind:
            add_node(entry, fields, kind, address, parent)
            if kind != "note":
                last, last_paragraph = address, block["paragraph"]
                paragraph_parents[block["paragraph"]] = address
        else:
            unresolved.append({**entry, "kind": "unresolved_block", "reason": reason})
            # Rejected boundaries still invalidate old parents, regardless of
            # which earlier guard rejected them; never establish a new parent.
            boundary_text = paragraph_text.get(block["paragraph"], text)
            if not _is_note(block):
                if "T" in classes or re.search(
                    r"(?:^|[\r\n])\s*Раздел(?:\s|$)", boundary_text, re.I
                ):
                    section = chapter = subchapter = None
                elif re.search(r"(?:^|[\r\n])\s*Глава(?:\s|$)", boundary_text, re.I):
                    chapter = subchapter = None
                elif re.search(r"(?:^|[\r\n])\s*§(?:\s|$)", boundary_text):
                    subchapter = None
            article = part = item = subitem = last = None
            list_order = None
        if close_quote:
            container, section, part, item, subitem, list_order = quote_context
            quote = quote_context = None
    for region, fallback in image_events:
        if any(b["paragraph"] == region["paragraph"] for b in unresolved):
            unresolved_regions.append(region)
            continue
        parent = paragraph_parents.get(region["paragraph"], fallback)
        add_node(region_entry(region), {"transcription_status": "source_image_only"},
                 "image", numbered(parent, "image"), parent)
        parsed_regions.append(region)
    nodes.sort(key=lambda n: n["source_span"]["char_start"])
    by_address = {n["address"]: n for n in nodes}
    for node in nodes:
        node["status_claims"] = []
        node["children"] = []
    for node in nodes:
        parent_node = by_address.get(node["parent_address"])
        if parent_node:
            parent_node["children"].append(node["address"])
            if node["kind"] == "note" and node["note_type"] == "repeal_notice":
                parent_node["status_claims"].append("repeal_notice")
    assigned = [i for b in [*nodes, *unresolved, *excluded] for i in b["text_node_ids"]]
    expected = [t["text_node_id"] for t in extraction["text_nodes"]]
    accounting = {
        "total_text_nodes": len(expected),
        "total_unsupported_regions": len(regions),
        "regions_exactly_once": Counter(r["region_id"] for r in [*unresolved_regions, *parsed_regions])
        == Counter(r["region_id"] for r in regions),
        "exactly_once": Counter(assigned) == Counter(expected),
        "counts_by_kind": dict(Counter(n["kind"] for n in nodes)),
        "unresolved_blocks": len(unresolved),
        "excluded_blocks": len(excluded),
    }
    for name, entries in (
        ("parsed", nodes),
        ("unresolved", unresolved),
        ("excluded", excluded),
    ):
        accounting[name + "_text_nodes"] = sum(len(b["text_node_ids"]) for b in entries)
        accounting[name + "_chars"] = sum(len(b["text"]) for b in entries)
    token_sizes = {
        t["text_node_id"]: len(t["raw_text"]) for t in extraction["text_nodes"]
    }
    accounting["total_source_chars"] = sum(token_sizes.values())
    accounting["total_chars"] = sum(len(b["text"]) for b in blocks)
    for name, entries in (
        ("parsed", nodes),
        ("unresolved", unresolved),
        ("excluded", excluded),
    ):
        accounting[name + "_source_chars"] = sum(
            token_sizes[i] for b in entries for i in b["text_node_ids"]
        )
    return {
        "schema_version": "legal-ast/1",
        "extraction_id": extraction.get("extraction_id"),
        "role": role,
        "namespace": namespace,
        "profile_version": profile,
        "parser_version": PARSER_VERSION + "+" + profile,
        "source_asset_sha256": extraction["source_asset_sha256"],
        "identity_decision": identity,
        "edition_admission": False,
        "valid_from": None,
        "valid_to": None,
        "nodes": nodes,
        "unresolved_blocks": unresolved,
        "unresolved_regions": unresolved_regions,
        "structural_issues": sorted(set(structural_issues + (["unclosed_amendment_quote"] if quote else []))),
        "parsed_regions": parsed_regions,
        "excluded_blocks": excluded,
        "cleanup_mapping": [
            {"block_id": b["block_id"], "mapping": b["cleanup_mapping"]} for b in blocks
        ],
        "accounting": accounting,
    }
