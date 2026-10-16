"""Import the official tree verbatim; do not reconstruct legal provisions."""

from collections import Counter
import copy
import hashlib
import json
from urllib.parse import quote

from .compiler import content_hash
from .official_structure import Anchors, Owners
from .structure import _identity

VERSION = "official-json-import/1"


def import_official_tree(asset, extraction, html, sidecar, structure_sha256, source_system):
    if hashlib.sha256(sidecar).hexdigest() != structure_sha256:
        raise ValueError("structure hash mismatch")
    response = json.loads(sidecar)
    statuses = {"actual.pravo.gov.ru": 0, "pravo.gov.ru/legislation-russia": 200}
    if source_system not in statuses:
        raise ValueError("unsupported official structure source")
    if (not isinstance(response, dict) or response.get("error") is not None
            or type(response.get("status")) is not int or response["status"] != statuses[source_system]
            or not isinstance(response.get("data"), list) or not response["data"]
            or source_system == "actual.pravo.gov.ru" and response.get("complete") is not True):
        raise ValueError("invalid official structure response")
    blocks = extraction["pages"][0]["blocks"]
    identity = _identity(blocks, asset["declared_identity"])
    if identity["status"] != "claim_matches_header":
        raise ValueError("official structure requires resolved source identity")
    anchors = Anchors(html).ids
    offsets = [0]
    for char in html:
        offsets.append(offsets[-1] + len(char.encode("utf-8")))

    def span(start, end):
        pointer = extraction["config"]["json_pointer"]
        return {"source_asset_sha256": asset["sha256"], "json_pointer": pointer,
                "char_start": start, "char_end": end,
                "offset_unit": "unicode_codepoints_in_decoded_json_scalar",
                "utf8_byte_start": offsets[start], "utf8_byte_end": offsets[end],
                "byte_offset_unit": "utf8_bytes_in_decoded_html_scalar",
                "locator": f"{pointer}:chars:{start}:{end}"}

    units, stack, by_id, siblings, findings = [], [], {}, {}, []

    def flag(unit, code):
        unit["range_status"] = "unresolved"
        findings.append({"code": code, "source_id": unit["source_id"],
                         "source_structure_evidence": unit["source_structure_evidence"],
                         "source_span": unit["source_span"]})

    for index, row in enumerate(response["data"]):
        if (not isinstance(row, dict) or type(row.get("lvl")) is not int or row["lvl"] < 0
                or any(not isinstance(row.get(k), str) for k in ("id", "unit", "caption", "np", "npe"))
                or not row["id"] or row["id"] in by_id):
            raise ValueError("invalid or duplicate official source node")
        while stack and stack[-1]["level"] >= row["lvl"]:
            stack.pop()
        parent = stack[-1] if stack else None
        if row["lvl"] != (parent["level"] + 1 if parent else 0):
            raise ValueError("sidecar level jump")
        pid = parent["source_id"] if parent else None
        start = anchors[row["np"]]["start"] if row["np"] in anchors else None
        end = anchors[row["npe"]]["end"] if row["npe"] in anchors else None
        unit = {"source_id": row["id"], "parent_source_id": pid, "level": row["lvl"],
                "source_unit": row["unit"], "source_state": row.get("state"), "caption": row["caption"],
                "source_record": copy.deepcopy(row), "html_start": start, "html_end": end,
                "source_span": span(start, end) if start is not None and end is not None else None,
                "source_structure_evidence": {"source_asset_sha256": structure_sha256,
                                               "json_pointer": f"/data/{index}"},
                "range_status": "source_declared", "number_canonical": None, "number_display": None,
                "number_is_explicit": None,
                "address": (parent["address"] if parent else "act") + "/source/" + quote(row["id"], safe="")}
        if start is None or end is None:
            flag(unit, "missing_source_anchor")
        elif start >= end:
            flag(unit, "reversed_source_range")
        else:
            if parent and parent["source_span"] and not (
                    parent["html_start"] <= start < end <= parent["html_end"]):
                flag(unit, "child_outside_parent")
            previous = siblings.get(pid)
            if previous and previous["source_span"] and previous["html_end"] > start:
                flag(previous, "overlapping_source_siblings")
                flag(unit, "overlapping_source_siblings")
        previous = siblings.get(pid)
        if start is not None and end is not None and start < end and (previous is None or end > previous["html_end"]):
            siblings[pid] = unit
        by_id[row["id"]] = unit
        units.append(unit)
        stack.append(unit)
    # Uncertain source ranges stay recorded, but cannot supply a precise text owner.
    for unit in units:
        parent = by_id.get(unit["parent_source_id"])
        if parent and parent["range_status"] == "unresolved" and unit["range_status"] != "unresolved":
            flag(unit, "unresolved_parent_range")
    owners = Owners([u for u in units if u["range_status"] != "unresolved"])
    nodes, excluded, parsed_regions, unresolved_regions = [], [], [], []

    def add(entry, kind, address, parent, **fields):
        node = {"text": "", "display_text": "", "original_text": "", "block_id": None,
                "text_node_ids": [], **entry, **fields, "kind": kind, "address": address,
                "parent_address": parent, "children": [], "status_claims": [], "legal_status": "unverified",
                "node_id": content_hash({"source": asset["sha256"], "structure": structure_sha256,
                                         "version": VERSION, "address": address})}
        nodes.append(node)
        return node

    for unit in units:
        parent = by_id.get(unit["parent_source_id"])
        add({k: v for k, v in unit.items() if k not in {"html_start", "html_end"}},
            "source_unit", unit["address"], parent["address"] if parent else "act")

    def owner_address(source_span):
        owner = owners.by_id.get(owners.find(source_span["char_start"], source_span["char_end"]))
        return owner["address"] if owner else "act"

    tables = []
    for region in extraction["unsupported_regions"]:
        start, end = (region["source_span"][k] for k in ("char_start", "char_end"))
        if html[start:end] != region["original_html"]:
            raise ValueError("region locator mismatch")
        if region["tag"] not in {"table", "img"}:
            unresolved_regions.append(copy.deepcopy(region))
            continue
        parent = owner_address(region["source_span"])
        kind = "table" if region["tag"] == "table" else "image"
        address = f"{parent}/{kind}/{region['region_id']}"
        add(copy.deepcopy(region), kind, address, parent,
            transcription_status="source_image_only" if kind == "image" else None)
        parsed_regions.append({**copy.deepcopy(region), "owner_address": parent})
        if kind == "table":
            tables.append((start, end, address))

    for block in blocks:
        if block["exclusion_reason"] or not block["text"]:
            excluded.append({**copy.deepcopy(block), "reason": block["exclusion_reason"] or "whitespace"})
            continue
        container = owner_address(block["source_span"])
        start, end = (block["source_span"][k] for k in ("char_start", "char_end"))
        table = min((t for t in tables if t[0] <= start < end <= t[1]),
                    key=lambda t: t[1] - t[0], default=None)
        parent = table[2] if table else container
        kind = "table_cell" if table else "paragraph"
        add(copy.deepcopy(block), kind, f"{parent}/{kind}/{block['block_id']}", parent,
            source_container_address=container)
    addresses = {n["address"]: n for n in nodes}
    for node in nodes:
        if node["parent_address"] in addresses:
            addresses[node["parent_address"]]["children"].append(node["address"])
    for node in nodes:
        node["children"].sort(key=lambda a: (addresses[a].get("source_span") or {}).get("char_start", -1))
    assigned = [i for n in [*nodes, *excluded] for i in n["text_node_ids"]]
    accounting = {"exactly_once": Counter(assigned) == Counter(t["text_node_id"] for t in extraction["text_nodes"]),
                  "regions_exactly_once": Counter(r["region_id"] for r in [*parsed_regions, *unresolved_regions])
                      == Counter(r["region_id"] for r in extraction["unsupported_regions"]),
                  "source_nodes": len(units), "counts_by_kind": dict(Counter(n["kind"] for n in nodes)),
                  "total_text_nodes": len(extraction["text_nodes"]), "total_chars": sum(len(b["text"]) for b in blocks),
                  "total_unsupported_regions": len(extraction["unsupported_regions"]), "unresolved_blocks": 0,
                  "excluded_blocks": len(excluded)}
    for name, entries in (("parsed", nodes), ("unresolved", []), ("excluded", excluded)):
        accounting[name + "_text_nodes"] = sum(len(n["text_node_ids"]) for n in entries)
        accounting[name + "_chars"] = sum(len(n["text"]) for n in entries)
    if not accounting["exactly_once"] or not accounting["regions_exactly_once"]:
        raise ValueError("official import accounting failed")
    return {"schema_version": "legal-ast/2", "extraction_id": extraction["extraction_id"], "role": asset["role"],
            "namespace": "act", "profile_version": VERSION, "parser_version": VERSION,
            "source_asset_sha256": asset["sha256"], "structure_asset_sha256": structure_sha256,
            "identity_decision": identity, "edition_admission": False, "valid_from": None, "valid_to": None,
            "nodes": nodes, "unresolved_blocks": [], "unresolved_regions": unresolved_regions,
            "structural_issues": ["source_structure_review_required"] if findings else [],
            "parsed_regions": parsed_regions, "excluded_blocks": excluded,
            "cleanup_mapping": [{"block_id": b["block_id"], "mapping": b["cleanup_mapping"]} for b in blocks],
            "accounting": accounting, "structure_mode": "official_source_verbatim",
            "source_integrity": {"schema_version": "official-source-integrity/1", "findings": findings,
                                 "source_nodes_checked": len(units), "semantic_validation": False}}
