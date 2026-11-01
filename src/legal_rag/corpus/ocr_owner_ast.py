"""Convert the maintained owner parser's decisions into source-bound diagnostic legal-ast/2."""
from collections import Counter, defaultdict
from copy import deepcopy
import re

from .compiler import content_hash
from . import ocr_owner_structure as parser
from ._ocr_owner.text import ANNEX
from .ocr_structure import _identity, prepare
from .structure import _number_fields

VERSION = "ocr-owner-ast/3"
KINDS = {"int": "point", "decimal": "point", "paren": "subitem", "letter": "subitem",
         "article": "article", "chapter": "chapter", "roman": "section", "letter_part": "part",
         "code_part": "part", "section_named": "section", "subsection": "subsection", "paragraph_sign": "subchapter",
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
    result = {"total_text_nodes": len(tokens), "exactly_once": True}
    for label, group in (("parsed", nodes), ("unresolved", unresolved), ("excluded", excluded)):
        result[label + "_text_nodes"] = sum(len(e["text_node_ids"]) for e in group)
        result[label + "_source_chars"] = sum(len(e["original_text"]) for e in group)
    return result


def _anchors(result):
    anchors = defaultdict(list)
    for paragraph in result["paragraphs"]:
        if paragraph["owner"] and (_marked(paragraph) or paragraph["kind"] in {"approval", "annex"}):
            anchors[paragraph["owner"]].extend(r["region_id"] for r in paragraph["regions"])
    return anchors


def _anchor_spans(ids, tokens, token_ids):
    return [deepcopy(tokens[t]["source_span"]) for rid in ids for t in token_ids[rid]]


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


def _entry(ids, tokens, regions, token_ids):
    tids = [t for rid in ids for t in token_ids[rid]]
    spans = [deepcopy(tokens[t]["source_span"]) for t in tids]
    raw = "".join(tokens[t]["raw_text"] for t in tids)
    text = parser.view(" ".join("".join(tokens[t]["raw_text"] for t in token_ids[rid]) for rid in ids))
    fragments = [{"region_id": rid, "page": regions[rid]["page"], "index": regions[rid]["index"],
                  "category": regions[rid]["category"], "bbox": deepcopy(regions[rid]["bbox"]),
                  "text_node_ids": list(token_ids[rid])} for rid in ids]
    return {"block_id": regions[ids[0]]["order"], "source_region_id": ids[0], "source_region_ids": list(ids),
            "text_node_ids": tids, "original_text": raw, "text": text,
            "cleanup_mapping": [{"operation": "whitespace_view_with_region_boundaries", "separator": " ",
                                  "source_region_ids": list(ids)}] if text != raw else [],
            "source_span": deepcopy(spans[0]) if len(spans) == 1 else None,
            "source_spans": spans, "fragments": fragments}


def build_owner_tree(extraction, declared_identity, role):
    result = parser.build(extraction)
    tokens, regions, token_ids = _source(extraction)
    namespace = "amendment/" + extraction["source_asset_sha256"] if role == "amendment" else "act"
    version = VERSION + "+" + result["parser_version"]
    identity = _identity(prepare(extraction)["blocks"], declared_identity)
    nodes, unresolved, excluded, containers, entries = [], [], [], {}, {}
    issues = {"pdf_structure_unqualified"}
    markers = _unit_markers(result, tokens, token_ids)
    repeated = Counter(p["owner"] for p in result["paragraphs"] if _marked(p) and p["owner"])
    if any(count > 1 for count in repeated.values()):
        issues.add("duplicate_printed_owner")
    captions = {p["owner"]: p["kind"] for p in result["paragraphs"] if p["kind"] in {"approval", "annex"}}
    anchors = _anchors(result)

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
                "anchor_source_spans": _anchor_spans(anchors[owner], tokens, token_ids),
                "marker_label": marker[1] if marker else None, "number_is_explicit": marker is not None,
                "legal_status": "unverified", "children": []}
        containers[owner] = node
        nodes.append(node)
        return address

    assigned = set()
    for paragraph in result["paragraphs"]:
        ids = [r["region_id"] for r in paragraph["regions"]]
        entry = _entry(ids, tokens, regions, token_ids)
        entry.update(kind=paragraph["kind"], owner_path=paragraph["owner"], evidence=deepcopy(paragraph["evidence"]))
        if _unresolved(paragraph):
            entry.update(kind="unresolved_block", reason="owner_unresolved", address=None)
            unresolved.append(entry)
        else:
            parent = owner_node(paragraph["owner"])
            address = namespace + "/content/" + str(entry["block_id"])
            entry.update(address=address, parent_address=parent, children=[], legal_status="unverified",
                         node_id=content_hash({"source": extraction["source_asset_sha256"], "parser": version, "address": address}))
            nodes.append(entry)
        entry["layout_kind"] = paragraph["kind"]
        if paragraph["kind"] == "table":
            entry["table_topology"] = deepcopy(regions[ids[0]]["table"])
            entry["table_cells"] = deepcopy(regions[ids[0]]["table"]["cells"])
        for rid in ids:
            if rid in assigned:
                raise ValueError("duplicated OCR paragraph region")
            assigned.add(rid)
            entries[rid] = entry
    for rid, region in regions.items():
        if rid in assigned:
            continue
        entry = _entry([rid], tokens, regions, token_ids)
        entry.update(kind="excluded_block", reason="physical_page_noise", address=None, owner_path=None)
        excluded.append(entry)
        entries[rid] = entry
    children = defaultdict(list)
    for node in nodes:
        children[node["parent_address"]].append(node["address"])
    for node in nodes:
        node["children"] = children[node["address"]]
    expected = {r["region_id"]: r for r in result["regions"]}
    excluded_ids = {id(e) for e in excluded}
    bindings = [{"region_id": rid, "page": region["page"], "index": region["index"],
                 "address": entries[rid]["address"], "owner_path": expected[rid]["owner"],
                 "continuation": expected[rid]["continuation"], "role": expected[rid]["role"],
                 "disposition": "excluded" if id(entries[rid]) in excluded_ids else
                                "unresolved" if entries[rid]["address"] is None else "parsed"}
                for rid, region in regions.items()]
    accounting = _accounting(tokens, nodes, unresolved, excluded)
    tree = {"schema_version": "legal-ast/2", "parser_version": version, "profile_version": "owner-path/2",
            "source_asset_sha256": extraction["source_asset_sha256"], "extraction_id": extraction.get("extraction_id"),
            "role": role, "namespace": namespace, "identity_decision": identity,
            "edition_admission": False, "valid_from": None, "valid_to": None,
            "nodes": nodes, "unresolved_blocks": unresolved, "excluded_blocks": excluded,
            "unresolved_regions": [], "structural_issues": sorted(issues), "cleanup_mapping": [],
            "region_bindings": bindings, "document_tree": deepcopy(extraction["document_tree"]),
            "ocr_uncertainties": deepcopy(extraction.get("uncertainties", [])), "accounting": accounting,
            "owner_parser": {"version": result["parser_version"], "result_sha256": content_hash(result)}}
    validate_owner_tree(extraction, tree)
    return tree


def validate_owner_tree(extraction, tree):
    """Check conversion against source and parser decisions; independent semantic review belongs to Task 3."""
    tokens, regions, token_ids = _source(extraction)
    expected = parser.build(extraction)
    identity = _identity(prepare(extraction)["blocks"], tree["identity_decision"]["declared_identity"])
    if tree["identity_decision"] != identity:
        raise ValueError("changed OCR identity decision")
    if (tree["source_asset_sha256"] != extraction["source_asset_sha256"]
            or tree["extraction_id"] != extraction.get("extraction_id")
            or tree["document_tree"] != extraction["document_tree"]
            or tree["owner_parser"]["result_sha256"] != content_hash(expected)):
        raise ValueError("changed OCR input or owner decisions")
    nodes = {n["address"]: n for n in tree["nodes"]}
    if len(nodes) != len(tree["nodes"]):
        raise ValueError("duplicate owner AST address")
    order = {n["address"]: k for k, n in enumerate(tree["nodes"])}
    children = defaultdict(list)
    for node in tree["nodes"]:
        children[node["parent_address"]].append(node["address"])
    markers = _unit_markers(expected, tokens, token_ids)
    anchors = _anchors(expected)
    entries = [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]
    if Counter(t for e in entries for t in e["text_node_ids"]) != Counter(tokens.keys()):
        raise ValueError("dropped or duplicated OCR text")
    leaf_regions = {}
    for entry in entries:
        ids = entry.get("source_region_ids", [])
        if not ids:
            if entry["text"] or entry["original_text"] or entry["source_spans"] or entry["text_node_ids"]:
                raise ValueError("owner container duplicates source text")
            continue
        original = _entry(ids, tokens, regions, token_ids)
        if any(entry[k] != original[k] for k in original):
            raise ValueError("changed OCR source text, fragments or locators")
        for rid in ids:
            if rid in leaf_regions:
                raise ValueError("duplicate OCR region assignment")
            leaf_regions[rid] = entry
        if entry.get("layout_kind") == "table" and (entry.get("table_topology") != regions[ids[0]]["table"]
                                         or entry.get("table_cells") != regions[ids[0]]["table"]["cells"]):
            raise ValueError("changed OCR table topology")
    if set(leaf_regions) != set(regions):
        raise ValueError("missing physical OCR region")
    for node in tree["nodes"]:
        parent = node["parent_address"]
        if parent != tree["namespace"] and (parent not in order or order[parent] >= order[node["address"]]):
            raise ValueError("invalid owner AST parent")
        if node["children"] != children[node["address"]]:
            raise ValueError("invalid owner AST children")
        if node.get("source_region_ids") and nodes[parent]["owner_path"] != node["owner_path"]:
            raise ValueError("content attached to another owner")
        if not node.get("source_region_ids"):
            path = node["owner_path"]
            prefix = path.rpartition("/")[0]
            expected_parent = tree["namespace"] + "/owner/" + prefix if prefix else tree["namespace"]
            marker = markers.get(path)
            number = _number(marker)
            if (parent != expected_parent or node["address"] != tree["namespace"] + "/owner/" + path
                    or any(node[k] != v for k, v in number.items()) or node["number_is_explicit"] != (marker is not None)):
                raise ValueError("wrong owner container parent or number")
            if (node["anchor_region_ids"] != anchors[path]
                    or node["anchor_source_spans"] != _anchor_spans(anchors[path], tokens, token_ids)):
                raise ValueError("changed owner marker anchors")
        if node["node_id"] != content_hash({"source": extraction["source_asset_sha256"],
                                            "parser": tree["parser_version"], "address": node["address"]}):
            raise ValueError("changed owner node identity")
    bindings = tree["region_bindings"]
    if Counter(b["region_id"] for b in bindings) != Counter(regions.keys()):
        raise ValueError("missing or duplicated physical OCR binding")
    decisions = {r["region_id"]: r for r in expected["regions"]}
    paragraphs = {r["region_id"]: p for p in expected["paragraphs"] for r in p["regions"]}
    excluded_ids = {id(e) for e in tree["excluded_blocks"]}
    unresolved_ids = {id(e) for e in tree["unresolved_blocks"]}
    for binding in bindings:
        rid = binding["region_id"]
        paragraph = paragraphs.get(rid)
        disposition = "excluded" if paragraph is None else "unresolved" if _unresolved(paragraph) else "parsed"
        actual = "excluded" if id(leaf_regions[rid]) in excluded_ids else (
            "unresolved" if id(leaf_regions[rid]) in unresolved_ids else "parsed")
        entry = leaf_regions[rid]
        kind = "excluded_block" if paragraph is None else "unresolved_block" if disposition == "unresolved" else paragraph["kind"]
        expected_ids = [r["region_id"] for r in paragraph["regions"]] if paragraph else [rid]
        if (entry["kind"] != kind or entry["source_region_ids"] != expected_ids
                or (paragraph is not None and entry["layout_kind"] != paragraph["kind"])):
            raise ValueError("changed OCR paragraph grouping or kind")
        if (binding["owner_path"] != decisions[rid]["owner"] or binding["address"] != leaf_regions[rid]["address"]
                or leaf_regions[rid]["owner_path"] != binding["owner_path"]
                or binding["continuation"] != decisions[rid]["continuation"]
                or binding["page"] != regions[rid]["page"] or binding["index"] != regions[rid]["index"]
                or binding["role"] != decisions[rid]["role"] or binding["disposition"] != disposition
                or actual != disposition):
            raise ValueError("wrong physical OCR owner")
    if tree["accounting"] != _accounting(tokens, tree["nodes"], tree["unresolved_blocks"], tree["excluded_blocks"]):
        raise ValueError("changed OCR accounting")
