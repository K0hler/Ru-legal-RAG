"""Map physical OCR paragraphs to the shared grammar without changing evidence."""

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, date
import re

from .compiler import content_hash
from .structure import MONTHS, NUMBER, _attachment_targets, _number_fields, _resolution_reference, build_structure

VERSION = "ocr-layout-structure/7"
ISSUERS = {"government_resolution": "Правительства Российской Федерации",
           "sanitary_rules": "Главного государственного санитарного врача Российской Федерации"}
HEADERS = {"government_resolution": "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ",
           "sanitary_rules": "ГЛАВНЫЙ ГОСУДАРСТВЕННЫЙ САНИТАРНЫЙ ВРАЧ РОССИЙСКОЙ ФЕДЕРАЦИИ"}


def _view(text):
    return re.sub(r"\s+", " ", re.sub(r"^\s*#{1,6}\s+", "", text)).strip()


def _title_key(text):
    return " ".join(re.findall(r"\w+", text.casefold()))


def _identity(blocks, claim):
    visible = [b for b in blocks if b["text"] and b["layout_kind"] not in {"table", "page_header", "page_footer"}]
    title_index = next((i for i, b in enumerate(visible) if re.match(r"^Об?\s", b["text"])), len(visible))
    lead = " ".join(b["text"] for b in visible[:title_index])
    family = next((key for key, header in HEADERS.items() if _title_key(header) in _title_key(lead)), None)
    numbers = re.findall(r"№\s*([1-9][0-9]*)\b", lead)
    dates = re.findall(r"\b(\d{2}\.\d{2}\.\d{4})\b", lead)
    for day, month, year in re.findall(r"\b(\d{1,2}) ([а-я]+) (\d{4})\b", lead, re.I):
        if month.casefold() in MONTHS:
            try:
                dates.append(date(int(year), MONTHS.index(month.casefold()) + 1, int(day)).strftime("%d.%m.%Y"))
            except ValueError:
                pass
    signing_date = None
    if len(set(dates)) == 1:
        try:
            signing_date = datetime.strptime(dates[0], "%d.%m.%Y").date().isoformat()
        except ValueError:
            pass
    number = numbers[0] if len(numbers) == 1 else None
    title_blocks = []
    for block in visible[title_index:]:
        if re.match(r"^(?:[1-9][0-9]*[.)]|В соответствии|На основании|Правительство .*постановляет)", block["text"], re.I):
            break
        if block["layout_kind"] != "image":
            title_blocks.append(block)
    title = " ".join(b["text"] for b in title_blocks)
    matched = bool(family and number and signing_date and title and "ПОСТАНОВЛЕНИЕ" in lead.upper())
    claimed = re.match(r"^Постановление (.+?) от (\d{2}\.\d{2}\.\d{4}) № ([1-9][0-9]*)\s+\"(.*)\"$", _view(claim or ""))
    if claim is not None:
        matched = bool(matched and claimed and claimed[1] == ISSUERS[family]
                       and claimed[2] in dates and claimed[3] == number
                       and _title_key(claimed[4]) == _title_key(title))
    return {"status": ("claim_matches_header" if claim is not None else "source_identity_matches") if matched else "unresolved",
            "family": family, "issuer": ISSUERS.get(family), "number": number, "signing_date": signing_date,
            "title": title, "declared_identity": claim,
            "act_id": content_hash({"family": family, "number": number, "date": signing_date, "title": title}),
            "signature_block_ids": [], "evidence_block_ids": [b["block_id"] for b in visible[:title_index] + title_blocks],
            "meaning": "source OCR identity comparison only; not legal admission"}


def prepare(extraction):
    """A paragraph view keeps all original tokens and their separate exact spans."""
    extraction = deepcopy(extraction)
    regions = {r["region_id"]: r for page in extraction["pages"] for r in page["regions"]}
    grouped = defaultdict(list)
    for block in extraction["blocks"]:
        grouped[block["source_region_id"]].append(block)
    blocks = []
    previous = ""
    for region_id, source in grouped.items():
        region = regions[region_id]
        raw = "".join(b["original_text"] for b in source)
        text = _view(raw)
        kind = {"Table": "table", "Picture": "image", "Footnote": "footnote",
                "Page-header": "page_header", "Page-footer": "page_footer"}.get(region["category"], "text")
        span = {**source[0]["source_span"], "char_end": source[-1]["source_span"]["char_end"],
                "ocr_char_end": source[-1]["source_span"]["ocr_char_end"]}
        span["locator"] = f"ocr:{span['json_pointer']}:chars:{span['ocr_char_start']}:{span['ocr_char_end']}"
        classes = ["T"] if (region["category"] in {"Title", "Section-header"}
                                or re.match(r"^(?:УТВЕРЖДЕН|ПРИЛОЖЕНИЕ)", previous, re.I)
                                or re.fullmatch(r"ПРАВИЛА|СТАНДАРТЫ|ТРЕБОВАНИЯ|ПОЛОЖЕНИЕ", previous, re.I)
                                or re.match(r"^(?:[IVXLCDMХ]+\.\s|Санитарные правила|ПРАВИЛА\b|СТАНДАРТЫ\b)", text, re.I)) else []
        blocks.append({**source[0], "block_id": len(blocks), "paragraph": len(blocks) + 1,
                       "text": text, "display_text": raw, "original_text": raw, "numbering_text": text,
                       "source_span": span, "source_spans": [b["source_span"] for b in source],
                       "source_block_ids": [b["block_id"] for b in source], "layout_kind": kind,
                       "text_node_ids": [i for b in source for i in b["text_node_ids"]],
                       "table_cells": region.get("table", {}).get("cells", []),
                       "table_topology": region.get("table"), "classes": classes,
                       "unsupported_structure": False,
                       "exclusion_reason": "physical_page_number" if kind in {"page_header", "page_footer"} and re.fullmatch(r"\d+", text) else None,
                       "cleanup_mapping": [{"operation": "whitespace_and_explicit_markdown_heading_view",
                                            "original": raw, "view": text}] if raw != text else []})
        if text and kind not in {"page_header", "page_footer", "image"}:
            previous = text
    return {**extraction, "blocks": blocks}


def build_ocr_structure(extraction, declared_identity, role):
    prepared = prepare(extraction)
    identity = _identity(prepared["blocks"], declared_identity)
    if identity["family"] is None:
        return None
    tree = build_structure(prepared, declared_identity, role, identity_decision=identity)
    tree["schema_version"] = "legal-ast/2"
    tree["parser_version"] = VERSION + "+" + tree["parser_version"]
    for node in tree["nodes"]:
        node["node_id"] = content_hash({"source": extraction["source_asset_sha256"],
                                        "parser": tree["parser_version"], "address": node["address"]})
        if not node["text_node_ids"]:
            node["anchor_source_spans"] = node["source_spans"]
            node["source_spans"] = []
    entries = [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]
    region_entries = {b["source_region_id"]: b for b in entries}
    tree["region_bindings"] = [
        {"region_id": region["region_id"], "page": page["page"],
         "address": region_entries.get(region["region_id"], {}).get("address"),
         "disposition": ("parsed" if region_entries[region["region_id"]].get("address") else "unresolved_or_excluded")
         if region["region_id"] in region_entries else "empty_region_retained"}
        for page in extraction["pages"] for region in page["regions"]]
    validate_ocr_tree(extraction, tree)
    return tree


def validate_ocr_tree(extraction, tree):
    """Reject ownership/data corruption independently of cached accounting flags."""
    nodes = tree["nodes"]
    addresses = {node["address"] for node in nodes}
    if len(addresses) != len(nodes):
        raise ValueError("duplicate OCR legal address")
    order = {node["address"]: index for index, node in enumerate(nodes)}
    by_address = {node["address"]: node for node in nodes}
    for index, node in enumerate(nodes):
        parent = node["parent_address"]
        if parent != tree["namespace"] and (parent not in order or order[parent] >= index):
            raise ValueError("invalid OCR parent or source order")
        if node["children"] != [n["address"] for n in nodes if n["parent_address"] == node["address"]]:
            raise ValueError("invalid OCR children")
        number = node.get("number_canonical")
        if number is not None and not node["address"].endswith("/" + number):
            raise ValueError("OCR legal address and number disagree")
        if node["kind"] in {"paragraph", "table"} and parent in order:
            for boundary in nodes[order[parent] + 1:index]:
                if boundary["kind"] not in {"point", "item", "subitem", "section", "chapter", "annex", "approved_text"}:
                    continue
                ancestor = boundary["parent_address"]
                while ancestor in by_address and ancestor != parent:
                    ancestor = by_address[ancestor]["parent_address"]
                if ancestor != parent:
                    raise ValueError("OCR owner crosses an intervening legal scope")
    tokens = {t["text_node_id"]: t for t in extraction["text_nodes"]}
    entries = [*nodes, *tree["unresolved_blocks"], *tree["excluded_blocks"]]
    assigned = [i for entry in entries for i in entry["text_node_ids"]]
    if Counter(assigned) != Counter(tokens.keys()):
        raise ValueError("dropped or duplicated OCR text")
    for entry in entries:
        expected = [tokens[i] for i in entry["text_node_ids"]]
        raw = "".join(t["raw_text"] for t in expected)
        if (entry["original_text"] != raw or entry["text"] != _view(raw)
                or entry["source_spans"] != [t["source_span"] for t in expected]):
            raise ValueError("changed OCR source text or locator")
        if expected:
            span = {**expected[0]["source_span"], "char_end": expected[-1]["source_span"]["char_end"],
                    "ocr_char_end": expected[-1]["source_span"]["ocr_char_end"]}
            span["locator"] = f"ocr:{span['json_pointer']}:chars:{span['ocr_char_start']}:{span['ocr_char_end']}"
            if entry["source_span"] != span:
                raise ValueError("changed OCR aggregate locator")
    by_block = {entry["block_id"]: entry for entry in entries if entry["block_id"] is not None}
    titles = {}
    for node in nodes:
        if node["kind"] not in {"approved_text", "annex"}:
            continue
        evidence = node.get("approval_evidence_block_ids" if node["kind"] == "approved_text" else "attachment_evidence_block_ids", [])
        if (not evidence or evidence[0] != node["block_id"] or evidence != sorted(set(evidence))
                or any(i not in by_block for i in evidence)):
            raise ValueError("invalid OCR scope evidence blocks")
        if any(by_block[i].get("parent_address") != node["address"] for i in evidence[1:]):
            raise ValueError("invalid OCR scope evidence ownership")
        caption = " ".join(by_block[i]["text"] for i in evidence)
        title_ids = node.get("title_block_ids", [])
        if (any(i not in by_block for i in title_ids)
                or title_ids != sorted(set(title_ids))
                or any(by_block[i].get("parent_address") != node["address"] or i <= evidence[-1] for i in title_ids)
                or (" ".join(by_block[i]["text"] for i in title_ids) or None) != node.get("title")):
            raise ValueError("invalid OCR scope evidence title")
        identity = tree["identity_decision"]
        if node["kind"] == "approved_text":
            reference = re.sub(r"^УТВЕРЖДЕН[АЫО]?\s+", "", caption, flags=re.I)
            if (node["parent_address"] != tree["namespace"] or
                    _resolution_reference(reference, identity["issuer"]) != (identity["signing_date"], identity["number"])):
                raise ValueError("invalid OCR approval scope evidence")
            titles[node["address"]] = node["title"]
        else:
            match = re.fullmatch(rf"ПРИЛОЖЕНИЕ(?: (?:№ )?({NUMBER}))? к (.+)", caption, re.I)
            if not match or _attachment_targets(match[2], titles, identity, tree["namespace"]) != [node["parent_address"]]:
                raise ValueError("invalid OCR attachment scope evidence")
            if (node.get("number_canonical") != (_number_fields(match[1])["number_canonical"] if match[1] else None)
                    or node.get("number_is_explicit") != (match[1] is not None)):
                raise ValueError("invalid OCR attachment scope evidence number")
    expected_regions = [r["region_id"] for p in extraction["pages"] for r in p["regions"]]
    if Counter(b["region_id"] for b in tree["region_bindings"]) != Counter(expected_regions):
        raise ValueError("dropped or duplicated physical OCR region")
    region_entries = {e["source_region_id"]: e for e in entries if e["text_node_ids"]}
    for binding in tree["region_bindings"]:
        if binding["address"] != region_entries.get(binding["region_id"], {}).get("address"):
            raise ValueError("wrong physical OCR region owner")
    regions = {r["region_id"]: r for p in extraction["pages"] for r in p["regions"]}
    for node in entries:
        if node.get("layout_kind") == "table" and (node["table_topology"] != regions[node["source_region_id"]]["table"]
                or node["table_cells"] != regions[node["source_region_id"]]["table"]["cells"]):
            raise ValueError("changed OCR table cells or topology")
    if tree.get("document_tree", extraction["document_tree"]) != extraction["document_tree"]:
        raise ValueError("changed physical OCR document tree")
