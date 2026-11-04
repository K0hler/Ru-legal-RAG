"""Convert the maintained owner parser's decisions into source-bound diagnostic legal-ast/3."""
from collections import Counter, defaultdict
from copy import deepcopy
import re

from .compiler import content_hash
from . import ocr_owner_structure as parser
from ._ocr_owner.text import ANNEX
from ._ocr_owner.audit import prepare_owner_result
from ._ocr_owner.source_slices import BASIS, slices_for, narrowed_span
from .ocr_structure import _identity, prepare
from .structure import _number_fields

VERSION = "ocr-owner-ast/5"
KINDS = {"int": "point", "decimal": "point", "paren": "subitem", "letter": "subitem",
         "article": "article", "chapter": "chapter", "roman": "section", "letter_part": "part",
         "code_part": "part", "section_named": "section", "subsection": "subsection", "paragraph_sign": "subchapter",
         "subparagraph": "subchapter",
         "annex": "annex"}


def _marked(paragraph):
    return paragraph["marker"] and paragraph["marker"][0] != "dash"


def _number(marker):
    if marker is None:
        return {"number_canonical": None, "number_display": None, "number_components": None}
    display = re.sub(r"^(?:подразд|часть|разд|гл|ст|ч|§)", "", marker[1])
    normal = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+", lambda m: "^" + m[0].translate(
        str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")), display)
    return {**_number_fields(normal), "number_display": display}


def _unresolved(paragraph):
    return paragraph["owner"] is None or (paragraph["flow"] == "footnote" and any(
        e.get("footnote_owner") in {"unresolved", "unnumbered"} or "footnote_owner_common" in e
        for e in paragraph["evidence"]))


def _accounting(tokens, nodes, unresolved, excluded):
    result = {"total_text_nodes": len(tokens), "exactly_once": True,
              "basis": "text_node_raw_text_half_open_intervals",
              "total_source_chars": sum(len(t["raw_text"]) for t in tokens.values())}
    coverage = defaultdict(list)
    for label, group in (("parsed", nodes), ("unresolved", unresolved), ("excluded", excluded)):
        slices = [s for e in group for s in e.get("text_slices", [])]
        result[label + "_text_nodes"] = len({s["text_node_id"] for s in slices})
        result[label + "_source_chars"] = sum(s["end"] - s["start"] for s in slices)
        for part in slices:
            coverage[part["text_node_id"]].append((part["start"], part["end"]))
    if set(coverage) != set(tokens):
        raise ValueError("missing source token intervals")
    for tid, token in tokens.items():
        intervals, cursor = sorted(coverage[tid]), 0
        if not token["raw_text"] and intervals != [(0, 0)]:
            raise ValueError("empty token must have one source slice")
        for start, end in intervals:
            if start != cursor or end < start or (start == end and token["raw_text"]):
                raise ValueError("source slice gap or overlap")
            cursor = end
        if cursor != len(token["raw_text"]):
            raise ValueError("incomplete source intervals")
    return result


def _anchors(result, tokens, regions, token_ids):
    anchors, spans = defaultdict(list), defaultdict(list)
    for paragraph in result["paragraphs"]:
        if paragraph["owner"] and (_marked(paragraph) or paragraph["kind"] in {"approval", "annex"}):
            entry = _entry(paragraph["regions"], tokens, regions, token_ids)
            anchors[paragraph["owner"]].extend(entry["source_region_ids"])
            spans[paragraph["owner"]].extend(entry["source_spans"])
    return anchors, spans


def _source(extraction):
    tokens = {t["text_node_id"]: t for t in extraction["text_nodes"]}
    regions, token_ids = {}, defaultdict(list)
    for page in extraction["pages"]:
        for index, region in enumerate(page["regions"]):
            rid = region["region_id"]
            if rid in regions:
                raise ValueError("duplicate physical OCR region")
            regions[rid] = {**region, "page": page["page"], "index": index, "order": len(regions)}
    for block in extraction["blocks"]:
        token_ids[block["source_region_id"]].extend(block["text_node_ids"])
    return tokens, regions, token_ids


def _unit_markers(result, tokens, token_ids):
    markers = {p["owner"]: p["marker"] for p in result["paragraphs"] if _marked(p) and p["owner"]}
    for paragraph in result["paragraphs"]:
        if paragraph["kind"] == "annex" and paragraph["owner"]:
            raw = " ".join("".join(tokens[t]["raw_text"] for t in token_ids[r["region_id"]])
                           for r in paragraph["regions"])
            caption = ANNEX.match(parser.view(raw))
            if caption and caption.group("number") is not None:
                markers[paragraph["owner"]] = ("annex", caption.group("number"))
    return markers


def _entry(parts, tokens, regions, token_ids):
    ids = [r["region_id"] if isinstance(r, dict) else r for r in parts]
    slices, fragments, raw_parts = [], [], []
    for part, rid in zip(parts, ids, strict=True):
        length = sum(len(tokens[t]["raw_text"]) for t in token_ids[rid])
        start, end = (part.get("source_start", 0), part.get("source_end", length)) if isinstance(part, dict) else (0, length)
        selected = slices_for(token_ids[rid], start, end, tokens)
        slices.extend(selected)
        raw_parts.append("".join(tokens[s["text_node_id"]]["raw_text"][s["start"]:s["end"]] for s in selected))
        fragments.append({"region_id": rid, "page": regions[rid]["page"], "index": regions[rid]["index"],
                          "category": regions[rid]["category"], "bbox": deepcopy(regions[rid]["bbox"]),
                          "text_node_ids": [s["text_node_id"] for s in selected],
                          "start": start, "end": end, "offset_basis": BASIS})
    tids = [s["text_node_id"] for s in slices]
    spans = [narrowed_span(tokens[s["text_node_id"]], s["start"], s["end"]) for s in slices]
    raw, text = "".join(raw_parts), parser.view(" ".join(raw_parts))
    return {"block_id": regions[ids[0]]["order"], "source_region_id": ids[0], "source_region_ids": ids,
            "text_node_ids": tids, "text_slices": slices, "original_text": raw, "text": text,
            "cleanup_mapping": [{"operation": "whitespace_view_with_region_boundaries", "separator": " ",
                                  "source_region_ids": ids}] if text != raw else [],
            "source_span": deepcopy(spans[0]) if len(spans) == 1 else None,
            "source_spans": spans, "fragments": fragments}


def build_owner_tree(extraction, declared_identity, role):
    raw = parser.build(extraction)
    tokens, regions, token_ids = _source(extraction)
    result = prepare_owner_result(raw, tokens)
    namespace = "amendment/" + extraction["source_asset_sha256"] if role == "amendment" else "act"
    version = VERSION + "+" + result["parser_version"]
    identity = _identity(prepare(extraction)["blocks"], declared_identity)
    nodes, unresolved, excluded, containers, entries = [], [], [], {}, {}
    issues = {"pdf_structure_unqualified", *result['audit_issues']}
    markers = _unit_markers(result, tokens, token_ids)
    repeated = Counter(p["owner"] for p in result["paragraphs"] if _marked(p) and p["owner"])
    if any(count > 1 for count in repeated.values()):
        issues.add("duplicate_printed_owner")
    captions = {p["owner"]: p["kind"] for p in result["paragraphs"] if p["kind"] in {"approval", "annex"}}
    anchors, anchor_spans = _anchors(result, tokens, regions, token_ids)

    def owner_node(owner):
        if owner in containers:
            return containers[owner]["address"]
        parent_path, _, label = owner.rpartition("/")
        parent = owner_node(parent_path) if parent_path else namespace
        address = namespace + "/owner/" + owner
        marker = markers.get(owner)
        kind = KINDS.get(marker[0], "inferred_unit") if marker else (
            "act" if owner == "A" else "approved_text" if captions.get(owner) == "approval" else
            "annex" if captions.get(owner) == "annex" else "inferred_scope")
        if marker is None and kind in {"inferred_unit", "inferred_scope"}:
            issues.add("owner_scope_without_marker")
        number = _number(marker)
        node = {"kind": kind, "address": address, "parent_address": parent, "owner_path": owner,
                "node_id": content_hash({"source": extraction["source_asset_sha256"], "parser": version, "address": address}),
                "block_id": None, "text": "", "original_text": "", "text_node_ids": [],
                "source_span": None, "source_spans": [], **number,
                "anchor_region_ids": list(anchors[owner]),
                "anchor_source_spans": deepcopy(anchor_spans[owner]),
                "marker_label": marker[1] if marker else None, "number_is_explicit": marker is not None,
                "legal_status": "unverified", "children": []}
        containers[owner] = node
        nodes.append(node)
        return address

    assigned = set()
    for paragraph in result["paragraphs"]:
        ids = [r["region_id"] for r in paragraph["regions"]]
        entry = _entry(paragraph["regions"], tokens, regions, token_ids)
        entry.update(kind=paragraph["kind"], owner_path=paragraph["owner"], evidence=deepcopy(paragraph["evidence"]))
        if _unresolved(paragraph):
            entry.update(kind="unresolved_block", reason="owner_unresolved", address=None)
            unresolved.append(entry)
        else:
            parent = owner_node(paragraph["owner"])
            address = namespace + "/content/" + str(entry["block_id"])
            if sum(r["region_id"] == ids[0] for r in result["regions"]) > 1:
                address += ":" + str(entry["fragments"][0]["start"])
            entry.update(address=address, parent_address=parent, children=[], legal_status="unverified",
                         node_id=content_hash({"source": extraction["source_asset_sha256"], "parser": version, "address": address}))
            nodes.append(entry)
        entry["layout_kind"] = paragraph["kind"]
        if paragraph["kind"] == "table":
            entry["table_topology"] = deepcopy(regions[ids[0]]["table"])
            entry["table_cells"] = deepcopy(regions[ids[0]]["table"]["cells"])
        for rid in ids:
            assigned.add(rid)
            entries.setdefault(rid, []).append(entry)
    for rid, region in regions.items():
        if rid in assigned:
            continue
        entry = _entry([rid], tokens, regions, token_ids)
        entry.update(kind="excluded_block", reason="physical_page_noise", address=None, owner_path=None)
        excluded.append(entry)
        entries[rid] = [entry]
    children = defaultdict(list)
    for node in nodes:
        children[node["parent_address"]].append(node["address"])
    for node in nodes:
        node["children"] = children[node["address"]]
    decisions = {(r["region_id"], r["source_start"], r["source_end"]): r for r in result["regions"]}
    excluded_ids, unresolved_ids = {id(e) for e in excluded}, {id(e) for e in unresolved}
    bindings = []
    for rid, region in regions.items():
        pieces = []
        for entry in entries[rid]:
            fragment = next(f for f in entry["fragments"] if f["region_id"] == rid)
            decision = decisions[(rid, fragment["start"], fragment["end"])]
            pieces.append({"start": fragment["start"], "end": fragment["end"],
                           "owner_path": entry["owner_path"], "address": entry["address"],
                           "disposition": "excluded" if id(entry) in excluded_ids else
                                          "unresolved" if id(entry) in unresolved_ids else "parsed",
                           "continuation": decision["continuation"]})
        partitioned = len(pieces) > 1
        binding = {"region_id": rid, "page": region["page"], "index": region["index"],
                   "address": None if partitioned else pieces[0]["address"],
                   "owner_path": None if partitioned else pieces[0]["owner_path"],
                   "continuation": None if partitioned else pieces[0]["continuation"],
                   "role": decision["role"], "disposition": "partitioned" if partitioned else pieces[0]["disposition"]}
        if partitioned:
            binding.update(fragments=pieces, offset_basis=BASIS)
        bindings.append(binding)
    accounting = _accounting(tokens, nodes, unresolved, excluded)
    tree = {"schema_version": "legal-ast/3", "parser_version": version, "profile_version": "owner-path/2",
            "source_asset_sha256": extraction["source_asset_sha256"], "extraction_id": extraction.get("extraction_id"),
            "role": role, "namespace": namespace, "identity_decision": identity,
            "edition_admission": False, "valid_from": None, "valid_to": None,
            "nodes": nodes, "unresolved_blocks": unresolved, "excluded_blocks": excluded,
            "unresolved_regions": [], "structural_issues": sorted(issues), "cleanup_mapping": [],
            "source_warnings": result['source_warnings'],
            "region_bindings": bindings, "document_tree": deepcopy(extraction["document_tree"]),
            "ocr_uncertainties": deepcopy(extraction.get("uncertainties", [])), "accounting": accounting,
            "owner_parser": {"version": result["parser_version"], "result_sha256": content_hash(raw)}}
    return tree


def validate_owner_tree(extraction, tree):
    """Verify conversion against a fresh deterministic owner conversion.

    This is a producer assertion; the standalone source/control checker performs
    independent interval and semantic validation without calling this parser.
    """
    expected = build_owner_tree(extraction, tree["identity_decision"]["declared_identity"], tree["role"])
    if tree != expected:
        raise ValueError("changed owner conversion: source, grouping, owners, anchors or accounting")
