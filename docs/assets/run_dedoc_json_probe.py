"""Explicit offline native dots.mocr JSON -> Dedoc internal API experiment.

Run in the retained dedocproject/dedoc:v2.8 image. No readers, OCR or HTML/TXT
intermediate input is used. Extraction supplies source-bound table topology only.
"""

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path
import re
import time
import traceback


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded(value))


def project(native, extraction, strip_section_header_prefix=False, footnote_view=None):
    """Map literal native scalars, without assigning any semantic heading level."""
    if len(native["pages"]) != len(extraction["pages"]):
        raise ValueError("native page mismatch")
    lines, regions, tables, ledger = [], [], [], []
    for page_index, (page, extracted) in enumerate(zip(native["pages"], extraction["pages"])):
        if page["page_number"] != extracted["page"] or len(page["layout"]) != len(extracted["regions"]):
            raise ValueError("native page/region mismatch")
        for region_index, (region, crosscheck) in enumerate(zip(page["layout"], extracted["regions"])):
            pointer = f"/pages/{page_index}/layout/{region_index}"
            if region != crosscheck["source_record"] or pointer != crosscheck["json_pointer"]:
                raise ValueError("native region mismatch")
            uid = crosscheck["region_id"]
            raw = region.get("text", "")
            common = {"region_id": uid, "json_pointer": pointer + "/text",
                      "page_id": page["page_number"] - 1, "page": page["page_number"],
                      "image_size": page["image_size"], "bbox": region["bbox"],
                      "category": region["category"]}
            regions.append({**common, "native_record": copy.deepcopy(region)})
            if region["category"] == "Table":
                tables.append({**common, "uid": uid, "native_text": raw,
                               "topology": copy.deepcopy(crosscheck["table"])})
                pieces = [""]
            else:
                pieces = raw.splitlines(keepends=True) or [""]
            offset = 0
            for index, native_text in enumerate(pieces):
                prefix = re.match(r"^[ \t]*#{1,6}[ \t]+", native_text) if (
                    strip_section_header_prefix and region["category"] == "Section-header" and index == 0) else None
                removed = prefix.group() if prefix else ""
                text = native_text[len(removed):]
                if removed:
                    ledger.append({"source_uid": f"{uid}:{index}", "json_pointer": pointer + "/text",
                                   "operation": "remove_first_line_markdown_section_prefix",
                                   "native_char_start": offset, "native_char_end": offset + len(removed),
                                   "removed": removed})
                lines.append({**common, "uid": f"{uid}:{index}", "line_id": len(lines), "text": text,
                              "native_text": native_text, "removed_prefix": removed,
                              "char_start": offset + len(removed), "char_end": offset + len(native_text),
                              "table_uid": uid if region["category"] == "Table" else None})
                offset += len(native_text)
    if footnote_view is not None:
        order = footnote_view["region_order"]
        if len(order) != len(regions) or set(order) != {r["json_pointer"] for r in regions}:
            raise ValueError("footnote region order does not match native regions")
        ranks = {pointer: index for index, pointer in enumerate(order)}
        lines.sort(key=lambda line: ranks[line["json_pointer"]])
        for index, line in enumerate(lines):
            line["line_id"] = index
    return {"lines": lines, "regions": regions, "tables": tables,
            "source_asset_sha256": extraction["source_asset_sha256"], "projection_ledger": ledger,
            **({"footnote_view": footnote_view} if footnote_view is not None else {})}


def table_grid(topology):
    """Dedoc requires duplicated merged cells in a rectangular row grid."""
    grid = [[None for _ in range(topology["columns"])] for _ in range(topology["rows"])]
    for index, cell in enumerate(topology["cells"]):
        for row in range(cell["row"], cell["row"] + cell["rowspan"]):
            for col in range(cell["column"], cell["column"] + cell["colspan"]):
                if grid[row][col] is not None:
                    raise ValueError("overlapping table cells")
                grid[row][col] = {**cell, "source_cell_index": index,
                                  "invisible": (row, col) != (cell["row"], cell["column"])}
    for row in grid:
        for col, cell in enumerate(row):
            if cell is None:
                row[col] = {"text": "", "rowspan": 1, "colspan": 1, "invisible": True,
                            "source_cell_index": None, "unsupported": "missing_native_grid_cell"}
    return grid


def make_document(projection, native_bytes):
    from dedoc.data_structures import (Annotation, CellWithMeta, LineMetadata, LineWithMeta,
                                      Table, TableMetadata, UnstructuredDocument)
    from dedoc.data_structures.concrete_annotations import BBoxAnnotation, TableAnnotation
    from dedocutils.data_structures.bbox import BBox

    lines = []
    for line in projection["lines"]:
        x0, y0, x1, y1 = line["bbox"]
        bbox = BBox(x0, y0, x1 - x0, y1 - y0)
        annotations = [BBoxAnnotation(0, len(line["text"]), bbox, *line["image_size"]),
                       Annotation(0, len(line["text"]), "dots_source_uid", line["uid"])]
        if line["table_uid"]:
            annotations.append(TableAnnotation(line["table_uid"], 0, len(line["text"])))
        metadata = LineMetadata(page_id=line["page_id"], line_id=line["line_id"],
                                source_category=line["category"], source_region_id=line["region_id"],
                                source_uid=line["uid"], source_json_pointer=line["json_pointer"])
        lines.append(LineWithMeta(line["text"], metadata, annotations, uid=line["uid"]))
    tables = []
    for table in projection["tables"]:
        cells = []
        for row_index, row in enumerate(table_grid(table["topology"])):
            cell_row = []
            for col_index, cell in enumerate(row):
                cell_uid = f'{table["uid"]}:cell:{cell["source_cell_index"]}'
                metadata = LineMetadata(page_id=table["page_id"], line_id=None,
                                        source_category="Table-cell", source_region_id=table["uid"],
                                        source_cell_index=cell["source_cell_index"],
                                        source_header=cell.get("header", False))
                line = LineWithMeta(cell["text"], metadata,
                                   [Annotation(0, len(cell["text"]), "dots_source_cell_uid", cell_uid)],
                                   uid=f"{cell_uid}:{row_index}:{col_index}")
                cell_row.append(CellWithMeta([line], rowspan=cell["rowspan"], colspan=cell["colspan"],
                                             invisible=cell["invisible"]))
            cells.append(cell_row)
        tables.append(Table(cells, TableMetadata(page_id=table["page_id"], uid=table["uid"])))
    # Required API timestamps are unavailable in native JSON; zero is an explicit
    # sentinel, not an asserted source time. Keep that limitation in the receipt.
    metadata = dict(file_name="native.json", temporary_file_name="native.json", size=len(native_bytes),
                    modified_time=0, created_time=0, access_time=0, file_type="application/json",
                    uid=projection["source_asset_sha256"])
    return UnstructuredDocument(lines=lines, tables=tables, attachments=[], metadata=metadata)


def line_record(line):
    levels = {}
    for key in ("hierarchy_level", "tag_hierarchy_level"):
        value = getattr(line.metadata, key)
        levels[key] = vars(value) if value is not None else None
    return {"uid": line.uid, "text": line.line, "metadata": line.metadata.to_api_schema().model_dump(),
            "annotations": [a.to_api_schema().model_dump() for a in line.annotations], **levels}


def inspect_output(payload, projection):
    nodes, fragments, table_links = [], defaultdict(list), defaultdict(list)

    def walk(node, parent=None):
        references = []
        for ann in node["annotations"]:
            if ann["name"] == "dots_source_uid":
                ref = {"node_id": node["node_id"], "node_start": ann["start"], "node_end": ann["end"],
                       "text": node["text"][ann["start"]:ann["end"]]}
                fragments[ann["value"]].append(ref)
                references.append(ann["value"])
            elif ann["name"] == "table":
                table_links[ann["value"]].append(node["node_id"])
        nodes.append({"id": node["node_id"], "parent": parent, "kind": node["metadata"]["paragraph_type"],
                      "page_id": node["metadata"]["page_id"], "text": node["text"], "source_uids": references})
        for child in node["subparagraphs"]:
            walk(child, node["node_id"])

    walk(payload["content"]["structure"])
    maps, changes = [], []
    for source in projection["lines"]:
        refs = fragments[source["uid"]]
        actual = "".join(r["text"] for r in refs)
        exact = actual == source["text"]
        offset = source["char_start"]
        for ref in refs:
            if exact:
                ref.update(native_char_start=offset, native_char_end=offset + len(ref["text"]))
                offset += len(ref["text"])
        row = {"source_uid": source["uid"], "json_pointer": source["json_pointer"],
               "category": source["category"], "exact_text": exact, "output_fragments": refs,
               "removed_prefix": source.get("removed_prefix", ""),
               "verbatim_native_line": actual == source.get("native_text", source["text"])}
        maps.append(row)
        if not exact:
            changes.append({**row, "expected": source["text"], "actual": actual})
    return {"nodes": nodes, "output_source_map": maps, "changed_or_lost_lines": changes,
            "node_kinds": dict(Counter(n["kind"] for n in nodes)),
            "table_links": dict(table_links),
            "unlinked_table_uids": [t["uid"] for t in projection["tables"] if not table_links[t["uid"]]],
            "empty_regions_retained_only_in_sidecar": [r["region_id"] for r in projection["regions"]
                                                        if not r["native_record"].get("text", "")]}


def outcome_exit_code(rows):
    return 0 if all(row["status"] == "completed" and all(row.get(key) is True for key in (
        "raw_repeat_identical", "content_repeat_identical", "checks_repeat_identical")) for row in rows) else 2


def run(index_path, output, image_id, strip_section_header_prefix=False, stitch_footnotes=False):
    import resource

    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    runner_bytes = Path(__file__).read_bytes()
    (output / "runner.py").write_bytes(runner_bytes)
    stitcher_sha256 = None
    if stitch_footnotes:
        from stitch_ocr_footnotes import stitch
        helper = Path(__file__).with_name("stitch_ocr_footnotes.py").read_bytes()
        (output / "stitch_ocr_footnotes.py").write_bytes(helper)
        stitcher_sha256 = digest(helper)
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    protected = {str(index_path): digest(index_bytes)}
    for entry in index["documents"]:
        for kind in ("native", "extraction"):
            path = index_path.parent / entry["key"] / f"{kind}.json"
            protected[str(path)] = digest(path.read_bytes())
            if protected[str(path)] != entry[f"{kind}_sha256"]:
                raise ValueError(f"input hash mismatch: {path}")
    write(output / "freeze.json", {"schema_version": "dedoc-json-probe/1", "runner_sha256": digest(runner_bytes),
                                  "image_id": image_id, "protected_before": protected,
                                  "input_route": "native JSON -> UnstructuredDocument -> extractor -> TreeConstructor",
                                  "strip_section_header_prefix": strip_section_header_prefix,
                                  "stitch_footnotes": stitch_footnotes, "stitcher_sha256": stitcher_sha256,
                                  "network": "none", "legal_admission": False})
    from dedoc.structure_extractors.concrete_structure_extractors.law_structure_excractor import LawStructureExtractor
    from dedoc.structure_extractors.concrete_structure_extractors.foiv_law_structure_extractor import FoivLawStructureExtractor
    from dedoc.structure_constructors.concrete_structure_constructors.tree_constructor import TreeConstructor
    import dedoc

    rows = []
    for profile, cls in (("law", LawStructureExtractor), ("foiv_law", FoivLawStructureExtractor)):
        extractor = cls()
        for entry in index["documents"]:
            dest = output / profile / entry["key"]
            tick = time.perf_counter()
            row = {"profile": profile, "source_asset_sha256": entry["key"], "group": entry["group"],
                   "pages": entry["pages"], "status": "failed"}
            try:
                source = index_path.parent / entry["key"]
                native_bytes = (source / "native.json").read_bytes()
                native, extraction = json.loads(native_bytes), json.loads((source / "extraction.json").read_bytes())
                projection = project(native, extraction, strip_section_header_prefix=strip_section_header_prefix,
                                     footnote_view=stitch(native) if stitch_footnotes else None)
                dest.mkdir(parents=True, exist_ok=False)
                (dest / "native.json").write_bytes(native_bytes)
                write(dest / "projection-map.json", projection)
                parsed, checks = [], []
                for attempt in (1, 2):
                    document = make_document(projection, native_bytes)
                    write(dest / f"input-{attempt}.json", {"lines": [line_record(x) for x in document.lines],
                                                         "tables": [x.to_api_schema().model_dump() for x in document.tables]})
                    inferred = extractor.extract(document, parameters={"document_type": profile})
                    write(dest / f"inferred-{attempt}.json", {"lines": [line_record(x) for x in inferred.lines]})
                    payload = TreeConstructor().construct(inferred, parameters={"structure_type": "tree"}).to_api_schema().model_dump()
                    write(dest / f"parsed-{attempt}.json", payload)
                    check = inspect_output(payload, projection)
                    write(dest / f"checks-{attempt}.json", check)
                    parsed.append(payload)
                    checks.append(check)
                row.update(status="completed", regions=len(projection["regions"]), lines=len(projection["lines"]),
                           tables=len(projection["tables"]), node_kinds=checks[0]["node_kinds"],
                           mapped_section_prefixes=len(projection["projection_ledger"]),
                           raw_repeat_identical=parsed[0] == parsed[1],
                           content_repeat_identical=parsed[0]["content"] == parsed[1]["content"],
                           checks_repeat_identical=checks[0] == checks[1],
                           changed_or_lost_lines=len(checks[0]["changed_or_lost_lines"]),
                           unlinked_tables=len(checks[0]["unlinked_table_uids"]))
            except Exception:
                row["error"] = traceback.format_exc()
                write(dest / "failure.json", row)
            row["seconds_two_runs"] = time.perf_counter() - tick
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    after = {path: digest(Path(path).read_bytes()) for path in protected}
    write(output / "summary.json", {"schema_version": "dedoc-json-probe/1", "dedoc_version": dedoc.__version__,
                                   "image_id": image_id, "runner_sha256": digest(runner_bytes), "documents": rows,
                                   "strip_section_header_prefix": strip_section_header_prefix,
                                   "stitch_footnotes": stitch_footnotes, "stitcher_sha256": stitcher_sha256,
                                   "protected_after": after, "protected_unchanged": after == protected,
                                   "seconds": time.perf_counter() - started,
                                   "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                                   "legal_admission": False, "qualification": False,
                                   "unsupported": ["No source bold/font size/style or semantic heading levels exist; none fabricated.",
                                                   "Categories are retained metadata, not invented heading tags.",
                                                   "No native pixel data is supplied to Dedoc; empty Pictures remain sidecar regions.",
                                                   "Table cells use source-bound normalized topology; raw native table markup remains sidecar.",
                                                   "Cell bbox is unknown; table region bbox is not claimed as individual cell geometry.",
                                                   "Dedoc drops empty anchors; table ownership is tested and may be absent.",
                                                   "Nonrectangular table grid holes get invisible empty API cells, marked in projection.",
                                                   "Header-cell flags remain sidecar metadata; Dedoc cell API lacks that field.",
                                                   "Native document/page metadata and unknown fields remain in exact native.json sidecar.",
                                                   "Required API timestamp zeroes are unavailable-time sentinels, not source times."]})
    if after != protected:
        raise ValueError("protected inputs changed")
    return outcome_exit_code(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--strip-section-header-prefix", action="store_true")
    parser.add_argument("--stitch-footnotes", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(args.index, args.output_dir, args.image_id,
                         strip_section_header_prefix=args.strip_section_header_prefix,
                         stitch_footnotes=args.stitch_footnotes))
