"""Shared, source-bound native federal-law/code grammar; no edition admission."""

import re
from collections import Counter
from datetime import date, datetime

from .compiler import content_hash

PARSER_VERSION = "legal-structure/4"
PROFILE_VERSIONS = {"federal_law": "federal-law/4", "code": "code/4"}
NUMBER = r"[1-9][0-9]*(?:[.^-][1-9][0-9]*)*"
ROMAN = r"[IVXLCDM]+(?:[.^-][1-9][0-9]*)*"
SUP_DIGITS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
MONTHS = "января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split()


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
    matches = bool(family and title and number and signing_date)
    if declared_identity is not None:
        claim = " ".join(declared_identity.split())
        claimed = re.fullmatch(
            r'(Федеральный закон|Кодекс Российской Федерации) от (\d{2}\.\d{2}\.\d{4}) № ([1-9][0-9]*-ФЗ) "([^"]+)"',
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
            and (claimed[1] == "Федеральный закон") == (family == "federal_law")
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
    extraction: dict, declared_identity: str | None = None, role: str = "consolidated"
) -> dict:
    """Build source-bound diagnostic addresses; never infer an effective edition."""
    source_blocks = extraction.get(
        "blocks", extraction.get("pages", [{}])[0].get("blocks", [])
    )
    blocks = [{"classes": [], "display_text": b["text"], **b} for b in source_blocks]
    identity = _identity(blocks, declared_identity)
    namespace = (
        "act"
        if role != "amendment"
        else "amendment/" + extraction["source_asset_sha256"]
    )
    profile = PROFILE_VERSIONS.get(identity["family"], "unsupported")
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
    last = last_paragraph = None
    regions = extraction.get("unsupported_regions", [])
    unresolved_regions: list[dict] = []
    region_paragraphs = {r["paragraph"] for r in regions if r["paragraph"] is not None}
    signing_ids = set(identity["signature_block_ids"])
    first_article = next(
        (
            b["block_id"]
            for b in blocks
            if re.match(r"Статья\s+\d", b["text"], re.I)
            and not b["exclusion_reason"]
            and not _is_note(b)
        ),
        len(blocks),
    )

    def numbered(parent, kind):
        counters[(parent, kind)] += 1
        return f"{parent}/{kind}/{counters[(parent, kind)]}"

    events = sorted([*blocks, *regions], key=lambda e: e["source_span"]["char_start"])
    for block in events:
        if "region_id" in block:
            unresolved_regions.append(block)
            article = part = item = subitem = last = None
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
        if block["exclusion_reason"] or not block["text"]:
            excluded.append(
                {**entry, "reason": block["exclusion_reason"] or "whitespace"}
            )
            continue
        text, numbering = block["text"], block["numbering_text"]
        classes = set(block["classes"])
        kind = address = parent = None
        fields = {}
        reason = "unsupported_or_ambiguous_structure"
        if identity["status"] == "unresolved":
            reason = "identity_unresolved"
        elif block["html_id"] in duplicate_anchors:
            reason = "duplicate_html_id"
        elif block["unsupported_structure"]:
            reason = "unsupported_table_or_list"
        elif block["paragraph"] in region_paragraphs:
            reason = "unsupported_nontext_or_structure"
        elif block["paragraph"] is None:
            reason = "unaddressed_document_text"
        elif block["paragraph"] in ambiguous_paragraphs:
            reason = "multiple_provision_markers"
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
        if address in addresses:
            if kind == "section":
                section = chapter = subchapter = None
            elif kind == "chapter":
                chapter = subchapter = None
            elif kind == "subchapter":
                subchapter = None
            reason, kind = "duplicate_address", None
        if kind:
            addresses.add(address)
            nodes.append(
                {
                    **entry,
                    **fields,
                    "kind": kind,
                    "address": address,
                    "parent_address": parent,
                    "node_id": content_hash(
                        {
                            "source": extraction["source_asset_sha256"],
                            "profile": PARSER_VERSION + "+" + profile,
                            "address": address,
                        }
                    ),
                    "legal_status": "unverified",
                }
            )
            if kind != "note":
                last, last_paragraph = address, block["paragraph"]
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
        "regions_exactly_once": Counter(r["region_id"] for r in unresolved_regions)
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
        "excluded_blocks": excluded,
        "cleanup_mapping": [
            {"block_id": b["block_id"], "mapping": b["cleanup_mapping"]} for b in blocks
        ],
        "accounting": accounting,
    }
