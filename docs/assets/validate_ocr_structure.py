"""Validate a frozen OCR tree against full, independently authored source controls.

This checker never calls a structure parser. A passing document check is one input
to Task 3, not a replacement for full compiler replay and source-image review.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(rows, key, label):
    indexed = {row[key]: row for row in rows}
    require(len(indexed) == len(rows), f"duplicate {label}")
    return indexed


def _validate_source_v2(extraction, tree):
    """Check complete physical/text accounting independently of inferred owners."""
    require(tree["schema_version"] == "legal-ast/2", "unsupported tree schema")
    require(tree["source_asset_sha256"] == extraction["source_asset_sha256"]
            and tree["extraction_id"] == extraction["extraction_id"], "wrong source identity")
    require(tree["document_tree"] == extraction["document_tree"], "changed physical document tree")
    tokens = unique(extraction["text_nodes"], "text_node_id", "source text node")
    physical = [{**region, "page": page["page"], "index": index}
                for page in extraction["pages"] for index, region in enumerate(page["regions"])]
    regions = unique(physical, "region_id", "source region")
    region_order = {rid: i for i, rid in enumerate(regions)}
    region_tokens = defaultdict(list)
    for block in extraction["blocks"]:
        region_tokens[block["source_region_id"]].extend(block["text_node_ids"])
    groups = [tree["nodes"], tree["unresolved_blocks"], tree["excluded_blocks"]]
    entries = [entry for group in groups for entry in group]
    require(Counter(t for entry in entries for t in entry["text_node_ids"]) == Counter(tokens.keys()),
            "dropped or duplicated source text")
    leaves = {}
    dispositions = {}
    for disposition, group in zip(("parsed", "unresolved", "excluded"), groups, strict=True):
        starts = [entry["block_id"] for entry in group if entry.get("source_region_ids")]
        require(starts == sorted(starts), "changed source content order")
        for entry in group:
            require(disposition != "parsed" or entry["kind"] != "unresolved_block", "unresolved kind in parsed nodes")
            ids = entry.get("source_region_ids", [])
            if not ids:
                require(not any(entry[k] for k in ("text_node_ids", "original_text", "text", "source_spans")),
                        "container duplicates source content")
                anchors = entry.get("anchor_region_ids", [])
                require(len(set(anchors)) == len(anchors) and all(rid in regions for rid in anchors), "invalid source anchor regions")
                anchor_spans = [tokens[t]["source_span"] for rid in anchors for t in region_tokens[rid]]
                require(entry.get("anchor_source_spans", []) == anchor_spans, "changed source anchor locators")
                continue
            require(all(r in regions and r not in leaves for r in ids), "missing or duplicated source region")
            require([region_order[rid] for rid in ids] == sorted(region_order[rid] for rid in ids), "changed fragment order")
            tids = [t for rid in ids for t in region_tokens[rid]]
            spans = [tokens[t]["source_span"] for t in tids]
            joined = " ".join("".join(tokens[t]["raw_text"] for t in region_tokens[rid]) for rid in ids)
            view = re.sub(r"\s+", " ", " ".join(re.sub(r"^\s*#{1,6}\s+", "", line) for line in joined.splitlines())).strip()
            require(entry["text_node_ids"] == tids
                    and entry["original_text"] == "".join(tokens[t]["raw_text"] for t in tids)
                    and entry["text"] == view
                    and entry["block_id"] == region_order[ids[0]] and entry["source_region_id"] == ids[0]
                    and entry["source_spans"] == spans
                    and entry["source_span"] == (spans[0] if len(spans) == 1 else None),
                    "changed source text or locators")
            fragments = [{"region_id": rid, "page": regions[rid]["page"], "index": regions[rid]["index"],
                          "category": regions[rid]["category"], "bbox": regions[rid]["bbox"],
                          "text_node_ids": region_tokens[rid]} for rid in ids]
            require(entry["fragments"] == fragments, "changed physical source fragments")
            for rid in ids:
                region = regions[rid]
                if region["category"] == "Table":
                    require(entry.get("layout_kind") == "table" and entry["kind"] in {"table", "unresolved_block"}
                            and entry.get("table_topology") == region["table"]
                            and entry.get("table_cells") == region["table"]["cells"], "changed source table")
                leaves[rid], dispositions[rid] = entry, disposition
    require(set(leaves) == set(regions), "missing physical source region")
    bindings = tree["region_bindings"]
    require([b["region_id"] for b in bindings] == list(regions), "changed source region order or coverage")
    for binding in bindings:
        rid = binding["region_id"]
        leaf, region = leaves[rid], regions[rid]
        require(binding["address"] == leaf["address"] and binding["owner_path"] == leaf["owner_path"]
                and binding["disposition"] == dispositions[rid]
                and binding["page"] == region["page"] and binding["index"] == region["index"],
                "inconsistent physical binding")
    nodes = unique(tree["nodes"], "address", "AST address")
    positions = {address: i for i, address in enumerate(nodes)}
    children = defaultdict(list)
    for node in nodes.values():
        parent = node["parent_address"]
        require(parent == tree["namespace"] or parent in nodes and positions[parent] < positions[node["address"]],
                "invalid parent or node order")
        children[parent].append(node["address"])
        if node.get("source_region_ids"):
            require(parent == tree["namespace"] + "/owner/" + node["owner_path"]
                    and parent in nodes and not nodes[parent].get("source_region_ids"), "wrong content parent")
    for node in nodes.values():
        require(node["children"] == children[node["address"]], "invalid children order")
    accounting = {"total_text_nodes": len(tokens), "exactly_once": True}
    for label, group in zip(("parsed", "unresolved", "excluded"), groups, strict=True):
        accounting[label + "_text_nodes"] = sum(len(e["text_node_ids"]) for e in group)
        accounting[label + "_source_chars"] = sum(len(e["original_text"]) for e in group)
    require(tree["accounting"] == accounting, "incorrect accounting receipt")
    return regions, tokens


def validate_source(extraction, tree):
    """Read historical /2 proofs or independently check /3 source intervals."""
    if tree.get("schema_version") == "legal-ast/2":
        return _validate_source_v2(extraction, tree)
    require(tree.get("schema_version") == "legal-ast/3", "unsupported tree schema")
    require(tree["source_asset_sha256"] == extraction["source_asset_sha256"]
            and tree["extraction_id"] == extraction["extraction_id"], "wrong source identity")
    require(tree["document_tree"] == extraction["document_tree"], "changed physical document tree")
    tokens = unique(extraction["text_nodes"], "text_node_id", "source token")
    regions = unique([{**r, "page": p["page"], "index": i} for p in extraction["pages"]
                      for i, r in enumerate(p["regions"])], "region_id", "source region")
    order = {rid: i for i, rid in enumerate(regions)}
    region_tokens, token_region = defaultdict(list), {}
    for block in extraction["blocks"]:
        rid = block["source_region_id"]
        region_tokens[rid].extend(block["text_node_ids"])
        for tid in block["text_node_ids"]:
            require(tid not in token_region, "duplicated source token membership")
            token_region[tid] = rid
    coverage, parts = defaultdict(list), defaultdict(list)
    basis = "concatenated_text_node_raw_text"
    groups = [tree["nodes"], tree["unresolved_blocks"], tree["excluded_blocks"]]
    accounting = {"basis": "text_node_raw_text_half_open_intervals", "exactly_once": True,
                  "total_text_nodes": len(tokens), "total_source_chars": sum(len(t["raw_text"]) for t in tokens.values())}
    for disposition, group in zip(("parsed", "unresolved", "excluded"), groups, strict=True):
        starts, group_tokens, chars = [], set(), 0
        for entry in group:
            ids = entry.get("source_region_ids", [])
            if not ids:
                require(not any(entry.get(k) for k in ("text_node_ids", "text_slices", "original_text", "text", "source_spans")),
                        "container duplicates source content")
                continue
            require(len(set(ids)) == len(ids) and all(r in regions for r in ids), "invalid source regions")
            require(all(type(t) is int for t in entry["text_node_ids"]), "noninteger source token ID")
            require(all(set(part) == {"text_node_id", "start", "end"} and all(type(part[k]) is int
                        for k in ("text_node_id", "start", "end")) for part in entry.get("text_slices", [])),
                    "source slice IDs and offsets must be exact integers")
            require([order[r] for r in ids] == sorted(order[r] for r in ids), "changed fragment order")
            require(type(entry["block_id"]) is int and entry["block_id"] == order[ids[0]] and entry["source_region_id"] == ids[0], "changed source block")
            fragments = entry["fragments"]
            require([f["region_id"] for f in fragments] == ids, "changed source fragments")
            expected_slices, raw_parts = [], []
            for fragment in fragments:
                rid = fragment["region_id"]
                region, tids = regions[rid], region_tokens[rid]
                start, end = fragment["start"], fragment["end"]
                length = sum(len(tokens[t]["raw_text"]) for t in tids)
                require(type(start) is int and type(end) is int and 0 <= start <= end <= length
                        and (start < end or length == 0), "invalid region interval")
                require(fragment["offset_basis"] == basis and all(fragment[k] == region[k]
                        for k in ("page", "index", "category", "bbox")), "changed physical source fragment")
                local, selected, cursor = [], [], 0
                for tid in tids:
                    raw = tokens[tid]["raw_text"]
                    lo, hi = max(start, cursor), min(end, cursor + len(raw))
                    empty = not raw and (start < cursor <= end or start == cursor == 0)
                    if lo < hi or empty:
                        part = {"text_node_id": tid, "start": lo - cursor, "end": hi - cursor}
                        selected.append(part)
                        local.append(raw[part["start"]:part["end"]])
                    cursor += len(raw)
                require(all(type(t) is int for t in fragment["text_node_ids"])
                        and fragment["text_node_ids"] == [s["text_node_id"] for s in selected], "changed fragment tokens")
                expected_slices.extend(selected)
                raw_parts.append("".join(local))
                parts[rid].append({"start": start, "end": end, "address": entry["address"],
                                   "owner_path": entry["owner_path"], "disposition": disposition,
                                   "continuation": ids.index(rid) > 0})
                if region["category"] == "Table":
                    require(start == 0 and end == length and entry.get("layout_kind") == "table"
                            and entry["kind"] in {"table", "unresolved_block"}
                            and entry.get("table_topology") == region["table"]
                            and entry.get("table_cells") == region["table"]["cells"], "changed source table")
            require(entry.get("text_slices") == expected_slices
                    and entry["text_node_ids"] == [p["text_node_id"] for p in expected_slices], "changed source slices")
            spans = []
            for part in expected_slices:
                tid, start, end = part["text_node_id"], part["start"], part["end"]
                span = dict(tokens[tid]["source_span"])
                if start != 0 or end != len(tokens[tid]["raw_text"]):
                    for prefix in ("", "ocr_"):
                        base = span[prefix + "char_start"]
                        span[prefix + "char_start"], span[prefix + "char_end"] = base + start, base + end
                    span["locator"] = re.sub(r":chars:\d+:\d+$", f":chars:{span['ocr_char_start']}:{span['ocr_char_end']}", span["locator"])
                spans.append(span)
                coverage[tid].append((start, end))
                group_tokens.add(tid)
                chars += end - start
            joined = " ".join(raw_parts)
            view = re.sub(r"\s+", " ", " ".join(re.sub(r"^\s*#{1,6}\s+", "", line) for line in joined.splitlines())).strip()
            require(all(all(type(span[k]) is int for k in ("char_start", "char_end", "ocr_char_start", "ocr_char_end"))
                        for span in entry["source_spans"]), "source offsets must be exact integers")
            require(entry["source_span"] is None or all(type(entry["source_span"][k]) is int
                        for k in ("char_start", "char_end", "ocr_char_start", "ocr_char_end")), "source offsets must be integers")
            require(entry["original_text"] == "".join(raw_parts) and entry["text"] == view
                    and entry["source_spans"] == spans and entry["source_span"] == (spans[0] if len(spans) == 1 else None),
                    "changed source text or locators")
            require(disposition != "parsed" or entry["kind"] != "unresolved_block", "unresolved kind in parsed nodes")
            starts.append((entry["block_id"], fragments[0]["start"]))
        require(starts == sorted(starts), "changed source content order")
        accounting[disposition + "_text_nodes"], accounting[disposition + "_source_chars"] = len(group_tokens), chars
    require(set(coverage) == set(tokens), "missing source token coverage")
    for tid, token in tokens.items():
        intervals, cursor = sorted(coverage[tid]), 0
        require(token["raw_text"] or intervals == [(0, 0)], "duplicated empty source token")
        for start, end in intervals:
            require(start == cursor and end >= start and (end > start or not token["raw_text"]), "source interval gap or overlap")
            cursor = end
        require(cursor == len(token["raw_text"]), "incomplete source token")
    require(tree["accounting"] == accounting, "incorrect interval accounting receipt")
    require([b["region_id"] for b in tree["region_bindings"]] == list(regions), "changed physical region coverage")
    for binding in tree["region_bindings"]:
        rid = binding["region_id"]
        fragments = sorted(parts[rid], key=lambda f: (f["start"], f["end"]))
        require(all(type(binding[k]) is int for k in ("page", "index")), "invalid physical page/index")
        require(fragments and all(binding[k] == regions[rid][k] for k in ("page", "index")), "changed physical binding")
        length = sum(len(tokens[t]["raw_text"]) for t in region_tokens[rid])
        require(length > 0 or len(fragments) == 1, "duplicated empty physical region")
        cursor = 0
        for fragment in fragments:
            require(fragment["start"] == cursor, "source region interval gap, overlap or order")
            cursor = fragment["end"]
        require(cursor == sum(len(tokens[t]["raw_text"]) for t in region_tokens[rid]), "incomplete physical source")
        if len(fragments) > 1:
            require(all(type(f["start"]) is int and type(f["end"]) is int for f in binding.get("fragments", [])),
                    "binding interval offsets must be exact integers")
            require(binding["disposition"] == "partitioned" and binding["owner_path"] is None
                    and binding["address"] is None and binding["continuation"] is None
                    and binding["offset_basis"] == basis and binding["fragments"] == fragments, "inconsistent source partition")
        else:
            require(all(binding[k] == fragments[0][k] for k in ("address", "owner_path", "disposition", "continuation")), "inconsistent physical binding")
    nodes = unique(tree["nodes"], "address", "AST address")
    positions, children = {a: i for i, a in enumerate(nodes)}, defaultdict(list)
    for node in nodes.values():
        parent = node["parent_address"]
        require(parent == tree["namespace"] or parent in nodes and positions[parent] < positions[node["address"]], "invalid parent or node order")
        children[parent].append(node["address"])
        if node.get("source_region_ids"):
            require(parent == tree["namespace"] + "/owner/" + node["owner_path"] and parent in nodes
                    and not nodes[parent].get("source_region_ids"), "wrong content parent")
        else:
            anchors = node["anchor_region_ids"]
            require(len(set(anchors)) == len(anchors) and all(r in regions for r in anchors), "invalid source anchors")
            spans = [span for leaf in nodes.values() if leaf.get("source_region_ids") and leaf["owner_path"] == node["owner_path"]
                     for fragment in leaf["fragments"] if fragment["region_id"] in anchors
                     for part, span in zip(leaf["text_slices"], leaf["source_spans"], strict=True)
                     if token_region[part["text_node_id"]] == fragment["region_id"]]
            require(all(all(type(span[k]) is int for k in ("char_start", "char_end", "ocr_char_start", "ocr_char_end"))
                        for span in node["anchor_source_spans"])
                    and node["anchor_source_spans"] == spans, "changed source anchor locators")
    for node in nodes.values():
        require(node["children"] == children[node["address"]], "invalid children order")
    return regions, tokens


def validate_structure(extraction, tree, controls):
    require(controls["schema_version"] == "ocr-independent-controls/1"
            and controls["coverage"] == "full_document", "full independent controls required")
    require(controls["independence"]["candidate_outputs_used"] is False
            and bool(controls["independence"]["method"]), "independent source controls required")
    require(controls["source_asset_sha256"] == extraction["source_asset_sha256"]
            and controls["extraction_id"] == extraction["extraction_id"], "controls bind another extraction")
    regions, tokens = validate_source(extraction, tree)
    require(not tree["unresolved_blocks"] and not tree["unresolved_regions"], "unresolved structure")
    require(set(tree["structural_issues"]) == {"pdf_structure_unqualified"}, "unsupported critical structure or missing qualification flag")
    expected_regions = unique(controls["regions"], "region_id", "region control")
    require(list(expected_regions) == list(regions), "incomplete or unordered region controls")
    for binding in tree["region_bindings"]:
        expected = expected_regions[binding["region_id"]]
        require(all(binding[k] == expected[k] for k in ("owner_path", "disposition", "continuation")),
                f"region control mismatch: {binding['page']}.{binding['index']}")
    units = [n for n in tree["nodes"] if not n.get("source_region_ids")]
    require([n["owner_path"] for n in units] == [c["owner_path"] for c in controls["units"]], "unit control order or coverage mismatch")
    unique(controls["units"], "owner_path", "unit control")
    for unit, expected in zip(units, controls["units"], strict=True):
        parent = expected["parent_owner_path"]
        parent_address = tree["namespace"] + "/owner/" + parent if parent else tree["namespace"]
        require(unit["address"] == tree["namespace"] + "/owner/" + expected["owner_path"]
                and unit["parent_address"] == parent_address
                and all(unit[k] == expected[k] for k in ("kind", "number_canonical", "number_display", "number_components", "number_is_explicit", "anchor_region_ids")),
                f"unit control mismatch: {expected['owner_path']}")
        require(all(r in regions for r in unit["anchor_region_ids"]), "control anchor outside source")
        spans = [tokens[t]["source_span"] for rid in unit["anchor_region_ids"]
                 for block in extraction["blocks"] if block["source_region_id"] == rid for t in block["text_node_ids"]]
        require(unit["anchor_source_spans"] == spans, "changed control anchor locators")
    return {"regions": len(regions), "units": len(units), "text_nodes": len(tokens)}


def validate_freeze(root, freeze):
    """Verify bound files and reserved membership; compiler permission checks remain mandatory."""
    root = root.resolve()
    require(freeze["schema_version"] == "ocr-structure-freeze/1", "unsupported freeze schema")
    files = freeze["files"]
    require(set(files) == {"code", "source", "permission", "extraction", "controls", "split"}
            and all(files.values()), "incomplete frozen files")
    for category in files.values():
        for name, digest in category.items():
            path = (root / name).resolve()
            require(path.is_relative_to(root), "frozen path outside root")
            require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                    f"frozen file hash mismatch: {name}")
    current = {p.relative_to(root).as_posix() for p in (root / "src").rglob("*.py")}
    frozen = {p for p in files["code"] if p.startswith("src/") and p.endswith(".py")}
    require(current and current == frozen, "changed code inventory")
    require("docs/assets/validate_ocr_structure.py" in files["code"], "independent checker is not frozen")
    require(len(files["split"]) == 1, "one frozen split required")
    split_path, = files["split"]
    split = unique(json.loads((root / split_path).read_bytes())["documents"], "key", "split act")
    documents = unique(freeze["documents"], "key", "evaluated act")
    require(bool(documents), "empty evaluation")
    identities = set()
    for key, document in documents.items():
        require(key in split and split[key]["split"] == "reserved" and not split[key].get("pilot", False),
                f"act is not reserved: {key}")
        row = split[key]
        identity = (row["family"], row["date"], row["number"])
        require(all((s["family"], s["date"], s["number"]) != identity
                    or s["split"] == "reserved" and not s.get("pilot", False) for s in split.values()),
                f"reserved act exposed in development/pilot: {key}")
        require(identity not in identities, "same act used twice")
        identities.add(identity)
        for category in ("source", "permission", "extraction", "controls"):
            require(document[category] in files[category], f"unbound {category}: {key}")
        require(files["source"][document["source"]] == document["source_asset_sha256"], "source hash binding mismatch")
        extraction = json.loads((root / document["extraction"]).read_bytes())
        controls = json.loads((root / document["controls"]).read_bytes())
        require(extraction["source_asset_sha256"] == document["source_asset_sha256"]
                and controls["source_asset_sha256"] == document["source_asset_sha256"]
                and controls["extraction_id"] == extraction["extraction_id"], "extraction/control binding mismatch")
        require((controls["identity"]["family"], controls["identity"]["signing_date"], controls["identity"]["number"]) == identity,
                "reserved identity control binding mismatch")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", required=True, type=Path)
    cli.add_argument("--freeze", required=True, type=Path)
    cli.add_argument("--act", required=True)
    cli.add_argument("--tree", required=True, type=Path)
    args = cli.parse_args()
    freeze = json.loads(args.freeze.read_bytes())
    validate_freeze(args.root, freeze)
    document = next(d for d in freeze["documents"] if d["key"] == args.act)
    extraction = json.loads((args.root / document["extraction"]).read_bytes())
    controls = json.loads((args.root / document["controls"]).read_bytes())
    require(extraction["source_asset_sha256"] == document["source_asset_sha256"], "extraction source binding mismatch")
    result = validate_structure(extraction, json.loads(args.tree.read_bytes()), controls)
    print(json.dumps({"act": args.act, "status": "pass", "checks": result,
                      "scope": "document controls only; compiler replay and image review required"}))


if __name__ == "__main__":
    main()
