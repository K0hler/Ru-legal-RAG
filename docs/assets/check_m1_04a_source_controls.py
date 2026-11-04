"""Compare complete source/image annotations with OCR trees; keep proposals separate from parsed nodes."""

from collections import Counter, defaultdict
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_ocr_owner_gold import (  # noqa: E402
    attached_count, attached_ordinal_heads, canonical, number_single_annex,
    ordinal_single_annex_documents, rename_head, single_annex_documents,
)
from validate_ocr_structure import require, unique, validate_source  # noqa: E402


WARNING_CODES = {"duplicate_printed_number": "duplicate_printed_number",
                 "parent_link_conflict": "missing_parent_number", "scope_boundary": "scope_boundary"}


def validate_controls(extraction, tree, packet, controls, *, allow_source_warnings=False):
    """Require complete structural acceptance; OCR requisites are a separate task."""
    report = compare_controls(extraction, tree, packet, controls, allow_source_warnings=allow_source_warnings)
    require(not tree["unresolved_blocks"] and not tree["unresolved_regions"], "unresolved structure")
    bindings = {f"{b['page']}.{b['index']}": b for b in tree["region_bindings"]}
    require(all(bindings[r["key"]]["disposition"] == "excluded" for r in controls["regions"]
                if r["status"] == "noise"), "source page noise included in structure")
    require(report["regions"]["evaluated"] > 0 and report["expected_units"] > 0, "empty structural controls")
    require(allow_source_warnings or not tree.get("source_warnings"), "source warnings require explicit policy")
    require(allow_source_warnings or not controls["uncertainties"] and report["regions"]["ambiguous"] == 0,
            "ambiguous source controls")
    expected_regions = report["regions"]["evaluated"] + (report["regions"]["ambiguous"] if allow_source_warnings else 0)
    require(report["canonical_regions_passed"] == expected_regions, "unconfirmed region ownership")
    for key in ("region_errors", "unit_errors", "continuation_errors", "extra_units", "duplicate_units", "source_warning_errors"):
        require(not report[key], "structural failure: " + key)
    require(report["unit_order_matches"], "wrong unit order")
    require(set(report["structural_issues"]) == {"pdf_structure_unqualified"}, "critical structure or missing qualification flag")
    return report


def verify_annotation(packet, controls, *, allow_source_warnings=False):
    require(controls["schema_version"] in {"m1-04a-independent-source-controls/1", "m1-04a-independent-source-controls/2"}, "wrong annotation schema")
    require(all(controls[k] == packet[k] for k in ("source_asset_sha256", "extraction_id", "assigned_pages")),
            "annotation source/pages mismatch")
    require(controls["independence"]["candidate_outputs_used"] is False
            and controls["independence"]["previous_gold_used"] is False, "annotation is not independent")
    rows = [r for r in packet["regions"] if r["page"] in packet["assigned_pages"]]
    source = unique(rows, "key", "source key")
    actual = unique(controls["regions"], "key", "annotation key")
    require(list(source) == list(actual), "incomplete/unordered annotation coverage")
    for key, row in actual.items():
        status = row["status"]
        require(status in {"evaluated", "picture", "noise", "ambiguous", "partitioned"}, "unknown annotation status")
        require(isinstance(row["continuation"], bool) or status == "partitioned" and row["continuation"] is None,
                "continuation must be boolean (or null for partitions)")
        if status == "partitioned":
            require(controls["schema_version"].endswith("/2") and source[key]["category"] not in {"Table", "Picture"}, "partition requires /2 text controls")
        require((source[key]["category"] == "Picture") == (status == "picture"), "incorrect picture exclusion")
        if status == "evaluated":
            require(isinstance(row["owner"], str) and bool(row["owner"]), "missing expected owner")
        else:
            require(row["owner"] is None, "unscored/ambiguous owner must be explicit null")
        if status == "noise":
            require(source[key]["category"] in {"Page-header", "Page-footer"} and bool(row.get("reason")), "unsupported noise exclusion")
        if status == "ambiguous":
            require(bool(row.get("reason")) and bool(row.get("candidates")) and bool(controls["uncertainties"]), "unexplained ambiguity")
    images = unique(controls["image_reviews"], "page", "image review")
    inventory = unique(packet["pages"], "page", "source image inventory")
    require(set(packet["assigned_pages"]) <= set(inventory), "incomplete source image inventory")
    require(all(re.fullmatch(r"[a-f0-9]{64}", p["sha256"]) for p in inventory.values()), "invalid source image hash")
    expected_images = {page: inventory[page]["sha256"] for page in packet["assigned_pages"]}
    require(set(images) == set(expected_images), "incomplete image review coverage")
    require(all(r["image_sha256"] == expected_images[p] and bool(r["observed_structure"].strip()) for p, r in images.items()),
            "image review hash or observation missing")
    if not allow_source_warnings:
        unique(controls["units"], "owner_path", "expected unit")
    else:
        uncertainties = controls["uncertainties"]
        for item in uncertainties:
            require(isinstance(item, dict) and item.get("type") in WARNING_CODES, "unsupported source uncertainty")
            require(bool(item.get("keys")) and len(set(item["keys"])) == len(item["keys"])
                    and all(key in source for key in item["keys"]), "uncertainty outside source")
        covered = {key for item in uncertainties for key in item["keys"]}
        require(all(row["key"] in covered for row in actual.values() if row["status"] == "ambiguous"),
                "unrelated ambiguous source region")
        grouped = defaultdict(list)
        for unit in controls["units"]:
            grouped[unit["owner_path"]].append(unit)
        for path, units in grouped.items():
            if len(units) < 2:
                continue
            starts = [u["start_key"] for u in units]
            require(len(set(starts)) == len(starts) and None not in starts
                    and all(start in source for start in starts)
                    and starts == sorted(starts, key=list(source).index)
                    and [u.get("occurrence_index") for u in units] == list(range(1, len(units) + 1))
                    and len({u["printed_number"] for u in units}) == 1,
                    "duplicate unit requires distinct source occurrence inventory")
            require(any(item["type"] == "duplicate_printed_number" and item.get("owner_path") == path
                        and item.get("unit_start_keys") == starts and set(item["keys"]) == set(starts)
                        for item in uncertainties), "duplicate unit lacks source uncertainty")
    for unit in controls["units"]:
        start = unit["start_key"]
        require(start in source or start is None and unit["owner_path"] == "A" and 1 in packet["assigned_pages"], "unit start outside assigned source")
        require(all(k in source for k in unit["evidence_keys"]), "unit evidence outside assigned source")
        require(unit["printed_number"] is None or isinstance(unit["printed_number"], str) and bool(unit["printed_number"]), "invalid printed number")
        if allow_source_warnings and (unit.get("candidate_owner_paths") or unit.get("candidate_parent_owner_paths")):
            row = actual.get(start, {})
            require(row.get("status") == "ambiguous" and start in covered, "unsupported unit alternatives")
            alternatives = [*unit.get("candidate_owner_paths", []),
                            *(parent + "/" + unit["owner_path"].rsplit("/", 1)[-1]
                              for parent in unit.get("candidate_parent_owner_paths", []))]
            require(all(path in row["candidates"] for path in alternatives), "unit alternative outside original candidates")
    for row in actual.values():
        if "owner_unit_start_key" in row:
            start = row["owner_unit_start_key"]
            owners = row.get("candidates", []) if row["status"] == "ambiguous" else [row["owner"]]
            require(start in source and list(source).index(start) <= list(source).index(row["key"])
                    and any(unit["start_key"] == start and any(owner == unit["owner_path"]
                        or owner and owner.startswith(unit["owner_path"] + "/") for owner in owners)
                        for unit in controls["units"]), "invalid independently anchored owner occurrence")


def verify_source_intervals(extraction, packet, controls):
    """Validate source-authored projections/ranges before comparing candidate owners."""
    source = {r["key"]: r for r in packet["regions"]}
    rows = {r["key"]: r for r in controls["regions"]}
    tokens = {t["text_node_id"]: t for t in extraction["text_nodes"]}
    grouped = defaultdict(list)
    projections = controls.get("region_text_projections", {})
    for span in controls.get("region_owner_spans", []):
        require(controls["schema_version"].endswith("/2"), "source intervals require versioned /2 controls")
        key = span["key"]
        require(key in source and key in projections, "source span lacks explicit raw-token projection")
        rid = source[key]["region_id"]
        tids = [tid for block in extraction["blocks"] if block["source_region_id"] == rid for tid in block["text_node_ids"]]
        raw = "".join(tokens[t]["raw_text"] for t in tids)
        require(all(type(t) is int for t in projections[key]["text_node_ids"]), "projection token IDs must be integers")
        require(projections[key] == {"offset_basis": "concatenated_text_node_raw_text", "text_node_ids": tids, "raw_text": raw},
                "changed source interval projection")
        start, end = span["start"], span["end"]
        require(type(start) is int and type(end) is int and 0 <= start < end <= len(raw)
                and span["offset_basis"] == "concatenated_text_node_raw_text" and span["text"] == raw[start:end],
                "invalid source owner interval or text")
        require(isinstance(span["owner"], str) and bool(span["owner"]) and span["disposition"] == "parsed"
                and isinstance(span["continuation"], bool), "invalid source interval owner")
        grouped[key].append(span)
    require(set(projections) == set(grouped), "unused source projection")
    for key, row in rows.items():
        if row["status"] != "partitioned":
            continue
        spans, cursor = grouped[key], 0
        require(len(spans) > 1, "incomplete partition owner controls")
        for span in spans:
            require(span["start"] == cursor, "source owner partition gap/overlap/order")
            cursor = span["end"]
        require(cursor == len(projections[key]["raw_text"]), "incomplete source owner partition")
        for unit in controls["units"]:
            if unit["start_key"] == key:
                require("start_text_offset" in unit and "start_text_quote" in unit, "partition unit needs precise source marker")
    for unit in controls["units"]:
        if "start_text_offset" in unit or "start_text_quote" in unit:
            require("start_text_offset" in unit and "start_text_quote" in unit, "incomplete source marker anchor")
            key, offset, quote = unit["start_key"], unit["start_text_offset"], unit["start_text_quote"]
            require(key in source and type(offset) is int and offset >= 0 and isinstance(quote, str) and bool(quote), "invalid source marker anchor")
            rid = source[key]["region_id"]
            raw = "".join(tokens[tid]["raw_text"] for block in extraction["blocks"] if block["source_region_id"] == rid for tid in block["text_node_ids"])
            require(raw[offset:].startswith(quote), "source marker quote/offset mismatch")
            if unit["printed_number"] is not None:
                require(re.match(re.escape(unit["printed_number"]) + r"[.)]\s", quote) is not None, "source anchor does not start at printed marker")
    return grouped


def source_warning_errors(tree, packet, controls):
    """Bind each accepted uncertainty to a visible warning and the actual affected owners."""
    source = {row["key"]: row["region_id"] for row in packet["regions"]}
    bindings = {row["region_id"]: row for row in tree["region_bindings"]}
    expected = [(WARNING_CODES[item["type"]], {source[key] for key in item["keys"]})
                for item in controls["uncertainties"]]
    warnings = tree.get("source_warnings", [])
    errors = []
    for warning in warnings:
        ids, owners = warning.get("region_ids", []), warning.get("owner_paths", [])
        valid = (warning.get("code") in WARNING_CODES.values() and bool(ids) and len(ids) == len(set(ids))
                 and all(rid in bindings for rid in ids) and bool(owners) and len(owners) == len(set(owners))
                 and isinstance(warning.get("message"), str) and bool(warning["message"].strip()))
        if valid:
            valid = (set(owners) == {bindings[rid]["owner_path"] for rid in ids}
                     and any(code == warning["code"] and regions == set(ids) for code, regions in expected))
        if not valid:
            errors.append({"failure": "unrelated or invalid source warning", "warning": warning})
    for code, ids in expected:
        if not any(w.get("code") == code and set(w.get("region_ids", [])) == ids for w in warnings):
            errors.append({"failure": "missing source warning coverage", "code": code, "region_ids": sorted(ids)})
    return errors


def number_fields(printed):
    """Mechanical source-number encoding; no marker or owner inference."""
    if printed is None:
        return {"number_canonical": None, "number_display": None, "number_components": None, "number_is_explicit": False}
    raised = re.search(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+$", printed)
    base, superscript = printed, None
    if raised:
        base = printed[:raised.start()]
        superscript = raised[0].translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-"))
    return {"number_canonical": base + "." + superscript if superscript is not None else base,
            "number_display": printed, "number_components": {"base": base, "superscript": superscript}, "number_is_explicit": True}


def compare_controls(extraction, tree, packet, controls, *, allow_source_warnings=False):
    require(all(packet[k] == extraction[k] for k in ("source_asset_sha256", "extraction_id")), "packet binds another extraction")
    physical = [(f"{p['page']}.{i}", p["page"], r["region_id"], r["category"])
                for p in extraction["pages"] for i, r in enumerate(p["regions"])]
    require([(r["key"], r["page"], r["region_id"], r["category"]) for r in packet["regions"]] == physical
            and packet["assigned_pages"] == [p["page"] for p in extraction["pages"]], "packet must cover the full actual extraction")
    verify_annotation(packet, controls, allow_source_warnings=allow_source_warnings)
    validate_source(extraction, tree)
    source_spans = verify_source_intervals(extraction, packet, controls)
    gold = {r["key"]: {"owners": [r["owner"]]} for r in controls["regions"] if r["status"] == "evaluated"}
    bindings = {f"{b['page']}.{b['index']}": b for b in tree["region_bindings"]}
    unit_gold = {**gold, **{"unit:" + u["owner_path"]: {"owners": [u["owner_path"]]} for u in controls["units"]}}
    attached, single = attached_count(unit_gold), single_annex_documents(unit_gold)
    heads = attached_ordinal_heads(gold, {key: value["owner_path"] for key, value in bindings.items()}, attached, single)
    renamed_single = ordinal_single_annex_documents(unit_gold, heads[0], attached, single)

    def normal(path, which):
        result = rename_head(canonical(path, attached, single), heads[which])
        return number_single_annex(result, renamed_single) if result is not None else None

    def expected_norm(path):
        return normal(path, 0)

    def actual_norm(path):
        # Occurrence suffixes identify source instances, never printed legal numbers.
        return normal(re.sub(r"@\d+(?=/|$)", "", path) if allow_source_warnings and path else path, 1)

    physical_order = {row["key"]: i for i, row in enumerate(packet["regions"])}
    region_controls = {row["key"]: row for row in controls["regions"]}
    occurrences = defaultdict(list)
    if allow_source_warnings:
        for unit in controls["units"]:
            if unit.get("occurrence_index"):
                occurrences[expected_norm(unit["owner_path"])].append(
                    (physical_order[unit["start_key"]], unit["occurrence_index"]))

    def expected_instance(path, key):
        path = expected_norm(path)
        if path is None or key is None:
            return path
        parts, result = path.split("/"), []
        for index, part in enumerate(parts):
            starts = occurrences.get("/".join(parts[:index + 1]), [])
            previous = [(start, occurrence) for start, occurrence in starts if start <= physical_order[key]]
            explicit = region_controls[key].get("owner_unit_start_key")
            selected = [occurrence for start, occurrence in previous if start == physical_order[key]]
            if not selected and explicit is not None:
                selected = [occurrence for start, occurrence in previous if start == physical_order[explicit]]
            if not selected and len(previous) == 1:
                selected = [previous[0][1]]
            if starts and len(selected) != 1:
                return None
            occurrence = selected[0] if selected else 1
            result.append(part + (f"@{occurrence}" if occurrence > 1 else ""))
        return "/".join(result)
    region_errors, continuation_errors = [], []
    proposals_passed = canonical_passed = 0
    for expected in controls["regions"]:
        if expected["status"] == "partitioned":
            binding = bindings[expected["key"]]
            spans = source_spans[expected["key"]]
            actual = binding.get("fragments", [])
            matches = binding["disposition"] == "partitioned" and len(actual) == len(spans) and all(
                fragment["start"] == span["start"] and fragment["end"] == span["end"]
                and actual_norm(fragment["owner_path"]) == expected_norm(span["owner"])
                and fragment["disposition"] == span["disposition"]
                and fragment["continuation"] == span["continuation"]
                for fragment, span in zip(actual, spans))
            proposals_passed += matches
            canonical_passed += matches
            if not matches:
                region_errors.append({"key": expected["key"], "failure": "source owner intervals", "expected": spans, "actual": actual})
            continue
        if expected["status"] != "evaluated" and not (allow_source_warnings and expected["status"] == "ambiguous"):
            continue
        binding = bindings[expected["key"]]
        owners = expected["candidates"] if expected["status"] == "ambiguous" else [expected["owner"]]
        proposal = normal(binding["owner_path"], 1) in [expected_instance(path, expected["key"]) for path in owners]
        parsed = proposal and binding["disposition"] == "parsed"
        proposals_passed += proposal
        canonical_passed += parsed
        if not parsed:
            region_errors.append({"key": expected["key"], "expected_owner": expected["owner"],
                                  "actual_owner": binding["owner_path"], "disposition": binding["disposition"], "proposal_matches": proposal})
        if binding["continuation"] != expected["continuation"]:
            continuation_errors.append({"key": expected["key"], "expected": expected["continuation"], "actual": binding["continuation"]})
    for key, spans in source_spans.items():
        if region_controls[key]["status"] == "partitioned":
            continue
        binding = bindings[key]
        for span in spans:
            if (actual_norm(binding["owner_path"]) != expected_norm(span["owner"])
                    or binding["disposition"] != span["disposition"] or binding["continuation"] != span["continuation"]):
                region_errors.append({"key": key, "failure": "supplemental source owner interval"})
    nodes = {n["address"]: n for n in tree["nodes"]}
    containers = [n for n in tree["nodes"] if not n.get("source_region_ids")]
    by_owner = defaultdict(list)
    duplicate_units = []
    for unit in containers:
        path = actual_norm(unit["owner_path"])
        if any(old["anchor_region_ids"] == unit["anchor_region_ids"] for old in by_owner[path]):
            duplicate_units.append(path)
        by_owner[path].append(unit)
    source_regions = {r["key"]: r["region_id"] for r in packet["regions"]}
    unit_errors, matched = [], []
    for expected in controls["units"]:
        paths = [expected["owner_path"]]
        if allow_source_warnings:
            paths += expected.get("candidate_owner_paths", [])
            paths += [parent + "/" + expected["owner_path"].rsplit("/", 1)[-1]
                      for parent in expected.get("candidate_parent_owner_paths", [])]
        candidates = [unit for path in dict.fromkeys(expected_norm(p) for p in paths) for unit in by_owner[path]]
        start = expected["start_key"]
        anchored_candidates = [unit for unit in candidates if start is not None
                               and unit["anchor_region_ids"] and unit["anchor_region_ids"][0] == source_regions[start]]
        unit = next((u for u in anchored_candidates if u["address"] not in matched), None)
        if unit is None and len(candidates) == 1 and candidates[0]["address"] not in matched:
            unit = candidates[0]
        failures = []
        if unit is None:
            failures.append("missing")
        else:
            matched.append(unit["address"])
            if normal(unit["owner_path"], 1) not in [expected_instance(path, start) for path in paths]:
                failures.append("occurrence")
            parent = unit["parent_address"]
            actual_parent = (None if expected["owner_path"] == "A" else "A") if parent == tree["namespace"] else nodes[parent]["owner_path"]
            parents = [expected["parent_owner_path"]]
            if allow_source_warnings:
                parents += expected.get("candidate_parent_owner_paths", [])
                if actual_norm(unit["owner_path"]) != expected_norm(expected["owner_path"]):
                    # A listed scope alternative carries its own explicitly listed path prefix.
                    parents = [path.rsplit("/", 1)[0] for path in paths
                               if expected_norm(path) == actual_norm(unit["owner_path"])]
            if normal(actual_parent, 1) not in [expected_instance(path, start) for path in parents]:
                failures.append("parent")
            kinds = {"annex", "approved_text"} if expected["kind"] == "attached_document" else {expected["kind"]}
            if unit["kind"] not in kinds:
                failures.append("kind")
            if any(unit[k] != value for k, value in number_fields(expected["printed_number"]).items()):
                failures.append("number")
            printed_marker = re.sub(r"^(?:подразд|часть|разд|гл|ст|ч|§)", "", unit.get("marker_label") or "") or None
            if tree["schema_version"] == "legal-ast/3" and printed_marker != expected["printed_number"]:
                failures.append("marker")
            if (len(occurrences.get(expected_norm(expected["owner_path"]), [])) > 1
                    and unit["anchor_region_ids"] != [source_regions[k] for k in expected["evidence_keys"]]):
                failures.append("anchor_evidence")
            if expected["start_key"] is not None:
                start = expected["start_key"]
                anchored = source_regions[start] in unit["anchor_region_ids"]
                if expected["kind"] == "act":
                    # The abstract act root has no printed marker; its header is retained as act-owned content.
                    binding = bindings[start]
                    anchored = anchored or (binding["disposition"] == "parsed"
                        and actual_norm(binding["owner_path"]) == expected_norm(expected["owner_path"])
                        and nodes[binding["address"]]["parent_address"] == unit["address"])
                if not anchored:
                    failures.append("anchor")
            if "start_text_offset" in expected:
                offset, quote = expected["start_text_offset"], expected["start_text_quote"]
                rid = source_regions[expected["start_key"]]
                tids = [tid for block in extraction["blocks"] if block["source_region_id"] == rid for tid in block["text_node_ids"]]
                tokens = {t["text_node_id"]: t for t in extraction["text_nodes"]}
                end_offset = sum(len(tokens[t]["raw_text"]) for t in tids)
                expected_parts = [p for p in source_spans.get(expected["start_key"], [])
                                  if p["start"] == offset and expected_norm(p["owner"]) == expected_norm(expected["owner_path"])]
                if expected_parts:
                    end_offset = expected_parts[0]["end"]
                cursor, spans = 0, []
                for tid in tids:
                    token = tokens[tid]
                    length = len(token["raw_text"])
                    if cursor + length > offset and cursor < end_offset:
                        span = dict(token["source_span"])
                        start, end = max(0, offset - cursor), min(length, end_offset - cursor)
                        if start or end != length:
                            for prefix in ("", "ocr_"):
                                base = span[prefix + "char_start"]
                                span[prefix + "char_start"], span[prefix + "char_end"] = base + start, base + end
                            span["locator"] = re.sub(r":chars:\d+:\d+$", f":chars:{span['ocr_char_start']}:{span['ocr_char_end']}", span["locator"])
                        spans.append(span)
                    cursor += length
                if unit["anchor_source_spans"] != spans:
                    failures.append("anchor_text_offset")
                projection = "".join(tokens[t]["raw_text"] for t in tids)
                if not projection[offset:].startswith(quote):
                    failures.append("anchor_text_quote")
        if failures:
            unit_errors.append({"owner_path": expected["owner_path"], "start_key": expected["start_key"],
                                "printed_number": expected["printed_number"], "failures": failures,
                                "actual": {k: unit[k] for k in ("owner_path", "kind", "number_canonical", "number_display", "number_components")} if unit else None})
    extra_units = [actual_norm(u["owner_path"]) for u in containers if u["address"] not in matched]
    status_counts = Counter(r["status"] for r in controls["regions"])
    status_counts["evaluated"] += status_counts["partitioned"]
    return {"regions": {k: status_counts[k] for k in ("evaluated", "picture", "noise", "ambiguous")},
            "owner_proposals_passed": proposals_passed, "canonical_regions_passed": canonical_passed,
            "region_errors": region_errors, "continuation_errors": continuation_errors, "expected_units": len(controls["units"]),
            "unit_errors": unit_errors, "extra_units": extra_units, "duplicate_units": duplicate_units,
            "unit_order_matches": [u["address"] for u in containers] == matched,
            "source_warnings": tree.get("source_warnings", []),
            "source_warning_errors": source_warning_errors(tree, packet, controls) if allow_source_warnings else [],
            "structural_issues": tree["structural_issues"], "identity": tree["identity_decision"]["status"]}
