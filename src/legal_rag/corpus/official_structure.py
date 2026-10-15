"""Typed official hierarchy adapter. Raw assets and applicability stay separate."""

from bisect import bisect_right
from collections import Counter
import copy
import hashlib
from html.parser import HTMLParser
import json
import re

from bs4 import BeautifulSoup

from .compiler import content_hash
from .structure import _identity, _note_fields

VERSION = "official-structure/4"
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
KINDS = {"раздел": "section", "глава": "chapter", "статья": "article",
         "часть": "part", "пункт": "item", "подпункт": "subitem", "приложение": "annex"}
SUPERSCRIPT = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
MARKER = re.compile(r'^["«]?(?:Статья\s+\d|Глава\s+\d|\d+(?:[.\-^]\d+)*[.)]\s|[а-яa-z]\)\s)', re.I)


class Anchors(HTMLParser):
    """Full raw element spans, independently of the existing text extractor."""

    def __init__(self, html):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.lines = [0, *(m.end() for m in re.finditer("\n", html))]
        self.stack, self.ids = [], {}
        self.feed(html)
        self.close()
        if self.stack:
            raise ValueError("unclosed HTML elements")

    def scalar_offset(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        row = {"tag": tag, "start": self.scalar_offset(),
               "end": self.scalar_offset() + len(self.get_starttag_text())}
        if attrs.get("id"):
            if attrs["id"] in self.ids:
                raise ValueError("duplicate HTML id")
            self.ids[attrs["id"]] = row
        if tag not in VOID:
            self.stack.append(row)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1]["tag"] != tag:
            raise ValueError("unbalanced HTML")
        row = self.stack.pop()
        row["end"] = self.html.index(">", self.scalar_offset()) + 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)


def numbering_markup(markup):
    soup = BeautifulSoup(markup, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for note in list(soup.select(".mark, .markx, label, script, style")):
        note.decompose()
    for sup in list(soup.select("sup, .W9, .WB")):
        sup.replace_with("^" + sup.get_text().strip())
    return " ".join(soup.get_text("", strip=False).split()).lstrip("$")


def explicit_number(text, unit):
    patterns = {
        "статья": r"^Статья\s+(\d+(?:[.\-^]\d+)*)",
        "часть": r"^часть\s+(\d+(?:[.\-^]\d+)*)",
        "пункт": r"^пункт\s+(\d+(?:[.\-^]\d+)*)",
        "подпункт": r'^(?:подпункт\s+)["«]?([а-яa-z0-9]+(?:[.\-^]\d+)*)',
        "глава": r"^Глава\s+([0-9IVXLCDM]+(?:[.\-^]\d+)*)",
        "раздел": r"^(?:РАЗДЕЛ\s+)?([0-9IVXLCDM]+(?:[.\-^]\d+)*)(?=[.\s]|$)",
        "приложение": r"^ПРИЛОЖЕНИЕ\s+(?:№\s*)?(\d+(?:[.\-^]\d+)*)",
    }
    m = re.match(patterns.get(unit, r"(?!)"), text, re.I)
    return m[1] if m else None


def source_marker_number(text, unit):
    if unit in {"пункт", "часть", "подпункт"}:
        m = re.match(r'^["«]?([0-9]+(?:[.\-^]\d+)*|[а-яa-z](?:\^\d+)?)[.)](?:\s|$)', text, re.I)
        return m[1] if m else None
    return explicit_number(text, unit)


def normalized_units(html, rows, family):
    anchors = Anchors(html).ids
    soup = BeautifulSoup(html, "html.parser")
    dom = {p["id"]: p for p in soup.find_all(id=True)}
    nodes, stack, seen = [], [], set()
    sibling_end = {}
    marker_checks = []
    for row_index, row in enumerate(rows):
        if (not isinstance(row, dict) or type(row.get("lvl")) is not int or row["lvl"] < 0
                or any(not isinstance(row.get(k), str) or not row[k] for k in ("id", "np", "npe", "caption", "unit"))):
            raise ValueError("invalid sidecar node fields")
        if row["id"] in seen:
            raise ValueError("duplicate sidecar id")
        seen.add(row["id"])
        if row["np"] not in anchors or row["npe"] not in anchors:
            raise ValueError("missing HTML anchor")
        if any(anchors[key]["tag"] not in {"p", "table", "tr", "td", "th"} for key in (row["np"], row["npe"])):
            raise ValueError("unsupported inline structure anchor")
        while stack and stack[-1]["level"] >= row["lvl"]:
            stack.pop()
        parent = stack[-1] if stack else None
        if row["lvl"] != (parent["level"] + 1 if parent else 0):
            raise ValueError("sidecar level jump")
        if parent and not row["id"].startswith(parent["source_id"] + "_"):
            raise ValueError("sidecar parent prefix conflict")
        start, end = anchors[row["np"]]["start"], anchors[row["npe"]]["end"]
        if start >= end or parent and not parent["html_start"] <= start < end <= parent["html_end"]:
            raise ValueError("invalid or non-nested sidecar range")
        pid = parent["source_id"] if parent else None
        if start < sibling_end.get(pid, -1):
            raise ValueError("overlapping sibling ranges")
        sibling_end[pid] = end
        caption = numbering_markup(row["caption"])
        source_text = numbering_markup(str(dom[row["np"]]))
        kind = KINDS.get(row["unit"], "unresolved_attachment")
        if row["unit"] == "вложение":
            if re.fullmatch(r"Примечания\s*[:.]?", caption, re.I):
                kind = "notes_section"
            elif re.fullmatch(r"примечание\s+\d+", caption, re.I):
                kind = "normative_note"
            elif row["lvl"] == 0 and re.match(r"^(ПРАВИЛА|ПОЛОЖЕНИЕ|ИЗМЕНЕНИЯ)\b", caption):
                kind = "approved_text"
        if family == "government_resolution" and row["unit"] == "пункт":
            kind = "item" if re.match(r"^\d+(?:[.\-^]\d+)*\)\s", source_text) else "point"
        number = explicit_number(caption, row["unit"])
        if row["unit"] not in {"вложение", "приложение"} and number is None:
            raise ValueError("numbered source unit has no explicit number")
        if number and number[0].isdigit() and any(int(n) == 0 for n in re.split(r"[.\-^]", number)):
            raise ValueError("zero provision number component")
        canonical = number.replace("^", ".") if number else None
        base, _, exponent = (number or "").partition("^")
        display = base + exponent.translate(SUPERSCRIPT) if number else None
        source_number = source_marker_number(source_text, row["unit"])
        mismatch = number is not None and (source_number or "").replace("^", ".") != canonical
        marker_checks.append({"source_id": row["id"], "html_id": row["np"],
                              "expected_number": canonical,
                              "dom_number": source_number.replace("^", ".") if source_number else None,
                              "matches": not mismatch,
                              "source_prefix": source_text[:160]})
        path = [*(parent["provision_path"] if parent else []),
                {"kind": kind, "number": canonical, "source_id": row["id"]}]
        n = {"source_id": row["id"], "source_row_index": row_index, "parent_source_id": pid,
             "kind": kind, "number_canonical": canonical, "number_display": display,
             "caption": row["caption"], "level": row["lvl"], "source_state": row.get("state"),
             "source_unit": row["unit"], "np": row["np"], "npe": row["npe"],
             "html_start": start, "html_end": end, "provision_path": path,
             "own_block_ids": [], "region_ids": []}
        if mismatch or kind.startswith("unresolved"):
            raise ValueError("sidecar number or unit conflicts with source HTML")
        nodes.append(n)
        stack.append(n)
    return nodes, marker_checks, soup


class Owners:
    """Resolve raw spans to the deepest containing unit; report crossing boundaries."""

    def __init__(self, nodes):
        self.rows = sorted(nodes, key=lambda n: (n["html_start"], n["level"]))
        self.starts = [n["html_start"] for n in self.rows]
        self.by_id = {n["source_id"]: n for n in nodes}

    def find(self, start, end):
        i = bisect_right(self.starts, start) - 1
        if i < 0:
            return None
        n = self.rows[i]
        while n:
            if n["html_start"] <= start and end <= n["html_end"]:
                return n["source_id"]
            n = self.by_id.get(n["parent_source_id"])
        return None

    def in_form(self, source_id):
        node = self.by_id.get(source_id)
        while node:
            if node["kind"] == "annex" and "(форма)" in node["caption"].casefold():
                return True
            node = self.by_id.get(node["parent_source_id"])
        return False


def build_official_tree(asset, extraction, html, sidecar, structure_sha256, source_system):
    if hashlib.sha256(sidecar).hexdigest() != structure_sha256:
        raise ValueError("structure hash mismatch")
    response = json.loads(sidecar)
    if not isinstance(response, dict):
        raise ValueError("invalid official structure object")
    actual = source_system == "actual.pravo.gov.ru"
    if source_system not in {"actual.pravo.gov.ru", "pravo.gov.ru/legislation-russia"}:
        raise ValueError("unsupported official structure source")
    if (response.get("error") is not None or type(response.get("status")) is not int
            or response["status"] != (0 if actual else 200) or not isinstance(response.get("data"), list)
            or not response["data"] or actual and response.get("complete") is not True):
        raise ValueError("invalid official structure response")
    blocks = extraction["pages"][0]["blocks"]
    identity = _identity(blocks, asset["declared_identity"])
    if identity["status"] != "claim_matches_header":
        raise ValueError("official structure requires resolved source identity")
    units, checks, soup = normalized_units(html, response["data"], identity["family"])
    owners = Owners(units)
    for unit in units:
        parent = owners.by_id.get(unit["parent_source_id"])
        number = unit["number_canonical"]
        suffix = f"{unit['kind']}/{number}" if number else f"source/{unit['source_id']}"
        unit["address"] = (parent["address"] if parent else "act") + "/" + suffix
    from .structure_audit import audit_tree, scan_html
    from .structure_completion import complete_units
    from .structure_recovery import recover_siblings

    candidates = scan_html(html)
    _, preliminary_owners, _, preliminary_invalid, preliminary_coarse = complete_units(blocks, owners)
    recovered = recover_siblings(candidates, units, owners, blocks,
        set(preliminary_owners) | preliminary_invalid | preliminary_coarse, soup)
    owners = Owners(units)
    nodes, unresolved, excluded, issues = [], [], [], []
    parsed_regions, unresolved_regions = [], []
    addresses = set()
    byte_offsets = [0]
    for char in html:
        byte_offsets.append(byte_offsets[-1] + len(char.encode("utf-8")))

    def span(start, end):
        pointer = extraction["config"]["json_pointer"]
        return {"source_asset_sha256": asset["sha256"], "json_pointer": pointer,
                "char_start": start, "char_end": end,
                "offset_unit": "unicode_codepoints_in_decoded_json_scalar",
                "utf8_byte_start": byte_offsets[start], "utf8_byte_end": byte_offsets[end],
                "byte_offset_unit": "utf8_bytes_in_decoded_html_scalar",
                "locator": f"{pointer}:chars:{start}:{end}"}

    def add(entry, kind, address, parent, **fields):
        if address in addresses:
            raise ValueError("duplicate official provision address")
        addresses.add(address)
        node = {"text": "", "display_text": "", "original_text": "", "block_id": None,
                "text_node_ids": [], **entry, **fields, "kind": kind, "address": address,
                "parent_address": parent, "children": [], "status_claims": [],
                "legal_status": "unverified", "node_id": content_hash(
                    {"source": asset["sha256"], "structure": structure_sha256, "version": VERSION, "address": address})}
        nodes.append(node)
        return node

    for unit in units:
        parent = owners.by_id.get(unit["parent_source_id"])
        parent_address = parent["address"] if parent else "act"
        number = unit["number_canonical"]
        suffix = f"{unit['kind']}/{number}" if number else f"source/{unit['source_id']}"
        unit["address"] = parent_address + "/" + suffix
        fields = ({"structure_origin": "html_recovery", "recovery_evidence": unit["recovery_evidence"]}
                  if unit.get("structure_origin") else {"source_id": unit["source_id"],
                      "source_structure_evidence": {"source_asset_sha256": structure_sha256,
                          "json_pointer": "/data/" + str(unit["source_row_index"])}})
        if "source_declared_range" in unit:
            fields["source_declared_span"] = span(*unit["source_declared_range"])
        add({"source_span": span(unit["html_start"], unit["html_end"])}, unit["kind"], unit["address"], parent_address,
            source_unit=unit["source_unit"], source_state=unit["source_state"], **fields,
            number_canonical=number, number_display=unit["number_display"], number_is_explicit=number is not None,
            caption=unit["caption"])

    completion, completed_owners, completion_issues, invalid_blocks, coarse_blocks = complete_units(blocks, owners)
    issues.extend(completion_issues)
    for node in completion:
        fields = {key: value for key, value in node.items() if key not in {"kind", "address", "parent", "start", "end", "level"}}
        add({"source_span": span(node["start"], node["end"]), "original_html": html[node["start"]:node["end"]]},
            node["kind"], node["address"], node["parent"], **fields)

    def completed_parent(start, end, fallback):
        containing = [n for n in completion if n["start"] <= start < end <= n["end"]
                      and n["address"].startswith(fallback + "/")]
        return max(containing, key=lambda n: n["address"].count("/"))["address"] if containing else fallback

    region_addresses = {}
    for region in extraction["unsupported_regions"]:
        start, end = (region["source_span"][key] for key in ("char_start", "char_end"))
        if html[start:end] != region["original_html"]:
            raise ValueError("region locator mismatch")
        owner = owners.by_id.get(owners.find(start, end))
        parent = owner["address"] if owner else "act"
        parent = completed_parent(start, end, parent)
        if region.get("nested") or region["tag"] not in {"table", "img"}:
            unresolved_regions.append(copy.deepcopy(region))
            continue
        kind = "image" if region["tag"] == "img" else "table"
        address = f"{parent}/{kind}/{region['region_id']}"
        add({"source_span": span(start, end), "original_html": region["original_html"]}, kind, address, parent,
            region_id=region["region_id"], transcription_status="source_image_only" if kind == "image" else None)
        region_addresses[region["region_id"]] = address
        parsed_regions.append({**copy.deepcopy(region), "owner_address": parent})

    unit_starts = {u["np"] for u in units}
    row_addresses = {}
    for region in parsed_regions:
        if region["tag"] != "table":
            continue
        previous = 0
        for row_index, row in enumerate(region["rows"]):
            if not row["cells"]:
                continue
            first = row["cells"][0]["source_span"]
            first_blocks = [b for b in blocks if first["char_start"] <= b["source_span"]["char_start"] < first["char_end"]]
            marker = re.match(r"^([1-9][0-9]*)\.\s", " ".join(b["numbering_text"] for b in first_blocks))
            if not marker or int(marker[1]) != previous + 1:
                continue
            previous = int(marker[1])
            parent = region_addresses[region["region_id"]]
            address = parent + "/row_item/" + marker[1]
            start, end = (row["source_span"][k] for k in ("char_start", "char_end"))
            add({"source_span": span(start, end), "original_html": html[start:end]}, "table_row_item", address, parent,
                number_canonical=marker[1], number_display=marker[1], number_is_explicit=True)
            row_addresses[(region["region_id"], row_index)] = address
    normative_paragraphs = {b["paragraph"] for b in blocks if b["text"] and not b["note"]
                            and not b["exclusion_reason"] and not set(b["classes"]) & {"A", "F"}}
    paragraph_text = {}
    for b in blocks:
        if not b["note"] and not set(b["classes"]) & {"A", "F"}:
            paragraph_text[b["paragraph"]] = paragraph_text.get(b["paragraph"], "") + b["original_text"]
    ambiguous_paragraphs = {key for key, text in paragraph_text.items() if re.search(
        r"[\r\n]\s*(?:Статья\s+\d|Глава\s+[IVXLCDM\d]|Раздел\s+[IVXLCDM\d]|\d+(?:[.^-]\d+)*[.)]\s|[а-я]\)\s)", text, re.I)}
    for original in blocks:
        block = copy.deepcopy(original)
        start, end = (block["source_span"][key] for key in ("char_start", "char_end"))
        block["source_span"] = {**block["source_span"], **span(start, end)}
        owner = owners.by_id.get(owners.find(start, end))
        parent = owner["address"] if owner else "act"
        if block["exclusion_reason"] or not block["text"]:
            excluded.append({**block, "reason": block["exclusion_reason"] or "whitespace"})
            continue
        note = bool(block["note"] or set(block["classes"]) & {"A", "F"})
        if note:
            same_paragraph = block["paragraph"] in normative_paragraphs
            paragraph_targets = {completed_owners[b["block_id"]] for b in blocks if b["paragraph"] == block["paragraph"]
                                 and b["block_id"] in completed_owners}
            if same_paragraph and len(paragraph_targets) == 1:
                parent = paragraph_targets.pop()
            add(block, "note", f"{parent}/note/{block['block_id']}", parent if same_paragraph else "act",
                **_note_fields(block), scope_status="same_paragraph" if same_paragraph else "unresolved",
                source_container_address=parent)
            continue
        table = next((r for r in parsed_regions if r["tag"] == "table"
                      and r["source_span"]["char_start"] <= start < end <= r["source_span"]["char_end"]), None)
        if table:
            parent = row_addresses.get((table["region_id"], block.get("table_cell", {}).get("row")),
                                       region_addresses[table["region_id"]])
        parent = completed_owners.get(block["block_id"], parent)
        kind = "table_cell" if table else "paragraph"
        form = owner and owners.in_form(owner["source_id"])
        if block["block_id"] in coarse_blocks:
            block["content_context"] = "amendment_payload"
        if (block["paragraph"] in ambiguous_paragraphs and not form) or block["block_id"] in invalid_blocks or (not form and block["block_id"] not in completed_owners
                and not (table and parent in row_addresses.values())
                and block["html_id"] not in unit_starts and MARKER.match(block["numbering_text"])
                and (owner is None or owner["kind"] not in {"normative_note", "notes_section"}) and "N" not in block["classes"]):
            reason = "multiple_provision_markers" if block["paragraph"] in ambiguous_paragraphs else "incomplete_quote_scope" if block["block_id"] in invalid_blocks else "numbered_unit_without_sidecar_node"
            unresolved.append({**block, "kind": "unresolved_block", "reason": reason,
                               "source_container_address": parent})
        else:
            add(block, kind, f"{parent}/{kind}/{block['block_id']}", parent)
    audit = audit_tree(candidates, nodes, unresolved, excluded)
    audit["source_asset_sha256"] = asset["sha256"]
    if audit["critical_count"]:
        issues.append("structure_audit_failed")
        critical_ids = {f.get("block_id") for f in audit["findings"] if f["severity"] == "critical" and f.get("block_id") is not None}
        for node in nodes[:]:
            if node.get("block_id") in critical_ids:
                nodes.remove(node)
                unresolved.append({**node, "kind": "unresolved_block", "reason": "structure_audit_failed"})
    by_address = {n["address"]: n for n in nodes}
    for node in nodes:
        if node["parent_address"] in by_address:
            by_address[node["parent_address"]]["children"].append(node["address"])
    nodes.sort(key=lambda n: (n["source_span"]["char_start"], n["block_id"] is not None))
    assigned = [i for b in [*nodes, *unresolved, *excluded] for i in b["text_node_ids"]]
    accounting = {"exactly_once": Counter(assigned) == Counter(t["text_node_id"] for t in extraction["text_nodes"]),
                  "regions_exactly_once": Counter(r["region_id"] for r in [*parsed_regions, *unresolved_regions])
                    == Counter(r["region_id"] for r in extraction["unsupported_regions"]),
                  "total_text_nodes": len(extraction["text_nodes"]), "total_chars": sum(len(b["text"]) for b in blocks),
                  "total_unsupported_regions": len(extraction["unsupported_regions"]),
                  "counts_by_kind": dict(Counter(n["kind"] for n in nodes)), "source_nodes": len(response["data"]),
                  "recovered_nodes": len(recovered),
                  "number_checks": sum(c["expected_number"] is not None for c in checks),
                  "unresolved_blocks": len(unresolved), "excluded_blocks": len(excluded)}
    for name, entries in (("parsed", nodes), ("unresolved", unresolved), ("excluded", excluded)):
        accounting[name + "_text_nodes"] = sum(len(n["text_node_ids"]) for n in entries)
        accounting[name + "_chars"] = sum(len(n["text"]) for n in entries)
    if not accounting["exactly_once"] or not accounting["regions_exactly_once"]:
        raise ValueError("official structure accounting failed")
    return {"schema_version": "legal-ast/2", "extraction_id": extraction["extraction_id"], "role": asset["role"],
            "namespace": "act", "profile_version": VERSION, "parser_version": VERSION,
            "source_asset_sha256": asset["sha256"], "structure_asset_sha256": structure_sha256,
            "identity_decision": identity, "edition_admission": False, "valid_from": None, "valid_to": None,
            "nodes": nodes, "unresolved_blocks": unresolved, "unresolved_regions": unresolved_regions,
            "structural_issues": issues, "parsed_regions": parsed_regions, "excluded_blocks": excluded,
            "cleanup_mapping": [{"block_id": b["block_id"], "mapping": b["cleanup_mapping"]} for b in blocks],
            "accounting": accounting, "structure_audit": audit}

