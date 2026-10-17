"""Offline, direct saved dots.mocr JSON mapping and native Docling stage experiment.

The adapter supplies categories, regions and table cells; Docling supplies reading
order, generic relations/merges and, separately, optional heading levels. No legal
parser, HTML/TXT importer, OCR, model download or PDF backend is used.
"""

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time
import traceback


LABELS = {"Caption": "caption", "Footnote": "footnote", "Formula": "formula",
          "List-item": "list_item", "Page-footer": "page_footer", "Page-header": "page_header",
          "Picture": "picture", "Section-header": "section_header", "Table": "table",
          "Text": "text", "Title": "title"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def project(native, extraction, source_sha256):
    """Bind native regions to retained topology without reading normalized block text."""
    if extraction["source_asset_sha256"] != source_sha256:
        raise ValueError("source binding mismatch")
    pages, regions = [], []
    if len(native["pages"]) != len(extraction["pages"]):
        raise ValueError("physical page binding mismatch")
    for pi, (page, normalized) in enumerate(zip(native["pages"], extraction["pages"], strict=True)):
        if (page["page_number"] != normalized["page"]
                or page["image_size"] != normalized["image_size"]
                or len(page["layout"]) != len(normalized["regions"])):
            raise ValueError("physical page binding mismatch")
        pages.append({"page_no": page["page_number"], "image_size": page["image_size"]})
        for ri, (region, norm) in enumerate(zip(page["layout"], normalized["regions"], strict=True)):
            pointer = f"/pages/{pi}/layout/{ri}"
            if norm["source_record"] != region or norm["json_pointer"] != pointer:
                raise ValueError("native region binding mismatch at " + pointer)
            record = {"page_no": page["page_number"], "image_size": page["image_size"],
                      "native_pointer": pointer, "region_id": norm["region_id"],
                      "source_record": region, "label": LABELS.get(region["category"], "text")}
            if region["category"] == "Table":
                record["table"] = norm["table"]
            regions.append(record)
    return copy.deepcopy({"source_asset_sha256": source_sha256, "pages": pages, "regions": regions})


def runtime():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    # Make accidental network use fail before any connection can be opened.
    def deny_network(event, args):
        if event == "socket.connect":
            raise RuntimeError("network forbidden in saved-JSON probe")
    sys.addaudithook(deny_network)
    from docling.backend.json.docling_json_backend import DoclingJSONBackend
    from docling.backend.noop_backend import NoOpBackend
    from docling.datamodel.base_models import AssembledUnit, Cluster, FigureElement, InputFormat, Page, Table, TextElement
    from docling.datamodel.document import ConversionResult, InputDocument
    from docling.datamodel.pipeline_options import HeadingHierarchyOptions
    from docling.models.stages.heading_hierarchy.heading_hierarchy_model import HeadingHierarchyModel
    from docling.models.stages.reading_order.readingorder_model import ReadingOrderModel, ReadingOrderOptions
    from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, DoclingDocument, DocumentOrigin, ProvenanceItem, Size, TableCell, TableData
    return dict(DoclingJSONBackend=DoclingJSONBackend, NoOpBackend=NoOpBackend,
                AssembledUnit=AssembledUnit, Cluster=Cluster, FigureElement=FigureElement,
                InputFormat=InputFormat, Page=Page, Table=Table, TextElement=TextElement,
                ConversionResult=ConversionResult, InputDocument=InputDocument,
                HeadingHierarchyOptions=HeadingHierarchyOptions, HeadingHierarchyModel=HeadingHierarchyModel,
                ReadingOrderModel=ReadingOrderModel, ReadingOrderOptions=ReadingOrderOptions,
                BoundingBox=BoundingBox, CoordOrigin=CoordOrigin, DocItemLabel=DocItemLabel,
                DoclingDocument=DoclingDocument, DocumentOrigin=DocumentOrigin, ProvenanceItem=ProvenanceItem,
                Size=Size, TableCell=TableCell, TableData=TableData)


def bbox(record, api):
    left, top, right, bottom = record["source_record"]["bbox"]
    return api["BoundingBox"](l=left, t=top, r=right, b=bottom, coord_origin=api["CoordOrigin"].TOPLEFT)


def table_data(record, api):
    table = record["table"]
    cells = [api["TableCell"](
        row_span=c["rowspan"], col_span=c["colspan"],
        start_row_offset_idx=c["row"], end_row_offset_idx=c["row"] + c["rowspan"],
        start_col_offset_idx=c["column"], end_col_offset_idx=c["column"] + c["colspan"],
        text=c["text"], column_header=c["header"], bbox=None,
    ) for c in table["cells"]]
    return api["TableData"](num_rows=table["rows"], num_cols=table["columns"], table_cells=cells)


def schema_document(projected, entry, api):
    """A literal, flat schema conversion; it performs no structural inference."""
    doc = api["DoclingDocument"](name=entry["key"], origin=api["DocumentOrigin"](
        mimetype="application/json", filename="native.json", binary_hash=entry["native_sha256"]))
    for page in projected["pages"]:
        doc.add_page(page_no=page["page_no"], size=api["Size"](width=page["image_size"][0], height=page["image_size"][1]))
    for record in projected["regions"]:
        text = record["source_record"].get("text", "")
        prov = api["ProvenanceItem"](page_no=record["page_no"], charspan=(0, len(text)),
                                    bbox=bbox(record, api).to_bottom_left_origin(record["image_size"][1]))
        label = api["DocItemLabel"](record["label"])
        if record["label"] == "table":
            doc.add_table(data=table_data(record, api), prov=prov)
        elif record["label"] == "picture":
            picture = doc.add_picture(prov=prov)
            if text:
                doc.add_text(label=api["DocItemLabel"].TEXT, text=text, prov=prov, parent=picture)
        elif record["label"] == "section_header":
            doc.add_heading(text=text, prov=prov)
        elif record["label"] == "list_item":
            doc.add_list_item(text=text, prov=prov)
        else:
            doc.add_text(label=label, text=text, prov=prov)
    return doc


def conversion(projected, path, api):
    in_doc = api["InputDocument"](path_or_stream=path, format=api["InputFormat"].JSON_DOCLING,
                                  backend=api["NoOpBackend"])
    if not in_doc.valid:
        raise ValueError("NoOp input context is invalid")
    in_doc.page_count = len(projected["pages"])
    pages = [api["Page"](page_no=p["page_no"], size=api["Size"](width=p["image_size"][0], height=p["image_size"][1]))
             for p in projected["pages"]]
    elements = []
    for index, record in enumerate(projected["regions"]):
        label = api["DocItemLabel"](record["label"])
        cluster = api["Cluster"](id=index, label=label, bbox=bbox(record, api))
        values = {"id": index, "label": label, "page_no": record["page_no"], "cluster": cluster,
                  "text": record["source_record"].get("text", "")}
        if record["label"] == "table":
            data = table_data(record, api)
            element = api["Table"](**values, otsl_seq=[], num_rows=data.num_rows, num_cols=data.num_cols,
                                   table_cells=data.table_cells)
        elif record["label"] == "picture":
            element = api["FigureElement"](**values)
        else:
            element = api["TextElement"](**values)
        elements.append(element)
    return api["ConversionResult"](input=in_doc, pages=pages,
                                    assembled=api["AssembledUnit"](elements=elements))


def import_json(path, api):
    in_doc = api["InputDocument"](path_or_stream=path, format=api["InputFormat"].JSON_DOCLING,
                                  backend=api["NoOpBackend"])
    backend = api["DoclingJSONBackend"](in_doc=in_doc, path_or_stream=path)
    try:
        imported = backend.convert()
        return {"accepted": True, "document": imported.export_to_dict(exclude_none=False)}
    except Exception as error:
        details = error.errors(include_url=False, include_input=False) if hasattr(error, "errors") else str(error)
        return {"accepted": False, "error_type": type(error).__name__, "details": details}


def inspect_output(projected, payload):
    """Reconcile real output fields, not the retained source copy or cached counters."""
    by_box = defaultdict(list)
    items = payload["texts"] + payload["tables"] + payload["pictures"]
    for item in items:
        for prov in item.get("prov", []):
            box = prov["bbox"]
            by_box[(prov["page_no"], box["l"], box["t"], box["r"], box["b"])].append((item, prov))
    rows = []
    for record in projected["regions"]:
        raw = record["source_record"]
        left, top, right, bottom = raw["bbox"]
        candidates = by_box.get((record["page_no"], left, record["image_size"][1] - top,
                                 right, record["image_size"][1] - bottom), [])
        found = []
        for item, prov in candidates:
            start, end = prov["charspan"]
            found.append({"ref": item["self_ref"], "parent": item.get("parent"), "label": item["label"],
                          "level": item.get("level"), "text": item.get("text"), "orig": item.get("orig"),
                          "charspan": [start, end], "segment": item.get("text", "")[start:end],
                          "orig_segment": item.get("orig", "")[start:end],
                          "merged_provenance_count": len(item.get("prov", []))})
        scalar = raw.get("text", "")
        row = {"region_id": record["region_id"], "native_pointer": record["native_pointer"],
               "page_no": record["page_no"], "source_category": raw["category"], "supplied_label": record["label"],
               "source_text": scalar, "bbox_mapped": bool(found), "outputs": found,
               "exact_scalar_text": any(f["segment"] == scalar for f in found),
               "exact_scalar_orig": any(f["orig_segment"] == scalar for f in found),
               "label_preserved": any(f["label"] == record["label"] for f in found)}
        if record["label"] == "table":
            expected = table_data_fields(record["table"])
            table_items = [item for item, _ in candidates if item["label"] == "table"]
            row["expected_table"] = expected
            row["table_cells_exact"] = any(
                table_fields(item["data"]) == expected for item in table_items)
            row["source_html_is_sidecar_only"] = True
        rows.append(row)
    scalar_rows = [r for r in rows if r["source_category"] != "Table"]
    return {"pages_exact": sorted(map(int, payload["pages"])) == sorted(p["page_no"] for p in projected["pages"]),
            "page_sizes_exact": all(payload["pages"][str(p["page_no"])]["size"] ==
                                    {"width": p["image_size"][0], "height": p["image_size"][1]} for p in projected["pages"]),
            "regions": len(rows), "bbox_mapped": sum(r["bbox_mapped"] for r in rows),
            "labels_preserved": sum(r["label_preserved"] for r in rows),
            "scalar_regions": len(scalar_rows), "scalar_text_exact": sum(r["exact_scalar_text"] for r in scalar_rows),
            "scalar_orig_exact": sum(r["exact_scalar_orig"] for r in scalar_rows),
            "tables": sum("table_cells_exact" in r for r in rows),
            "tables_exact": sum(r.get("table_cells_exact", False) for r in rows),
            "kinds": dict(Counter(i["label"] for i in items)),
            "parents": dict(Counter((i.get("parent") or {}).get("$ref", "none") for i in items)),
            "heading_levels": dict(Counter(str(i.get("level")) for i in items if i["label"] == "section_header")),
            "rows": rows}


def table_data_fields(table):
    return {"rows": table["rows"], "columns": table["columns"], "cells": [
        {"row": c["row"], "column": c["column"], "rowspan": c["rowspan"], "colspan": c["colspan"],
         "text": c["text"], "header": c["header"], "bbox": c["bbox"]} for c in table["cells"]]}


def table_fields(data):
    return {"rows": data["num_rows"], "columns": data["num_cols"], "cells": [
        {"row": c["start_row_offset_idx"], "column": c["start_col_offset_idx"], "rowspan": c["row_span"],
         "colspan": c["col_span"], "text": c["text"], "header": c["column_header"], "bbox": c["bbox"]}
        for c in data["table_cells"]]}


def heading_prefix(text):
    match = re.match(r"^#{2,3}[ \t]+", text)
    return (match.group(), text[match.end():]) if match else ("", text)


def run_entry(entry, output, api, strip_heading_prefix):
    path = Path(entry["native_path"])
    extraction_path = Path(entry["extraction_path"])
    if digest(path) != entry["native_sha256"] or digest(extraction_path) != entry["extraction_sha256"]:
        raise ValueError("input bytes changed")
    native, extraction = json.loads(path.read_text(encoding="utf-8")), json.loads(extraction_path.read_text(encoding="utf-8"))
    projected = project(native, extraction, entry["source_asset_sha256"])
    write(output / "source-mapping.json", projected)
    write(output / "raw-native-import.json", import_json(path, api))
    results, repeated = {}, {}
    for attempt in (1, 2):
        docs = {"schema": schema_document(projected, entry, api)}
        conv_res = conversion(projected, path, api)
        write(output / f"assembled-{attempt}.json", conv_res.assembled.model_dump(mode="json"))
        conv_res.document = api["ReadingOrderModel"](api["ReadingOrderOptions"]())(conv_res)
        docs["reading-order"] = conv_res.document.model_copy(deep=True)
        ledger = []
        if strip_heading_prefix:
            for item in conv_res.document.texts:
                if item.label.value != "section_header":
                    continue
                removed, after = heading_prefix(item.text)
                if removed:
                    ledger.append({"ref": item.self_ref, "raw_text": item.text, "removed_prefix": removed,
                                   "source_character_range": [0, len(removed)], "after_text": after,
                                   "orig_retained": item.orig, "provenance_retained": [p.model_dump(mode="json") for p in item.prov]})
                    item.text = after
        write(output / f"heading-prefix-ledger-{attempt}.json", ledger)
        conv_res.document = api["HeadingHierarchyModel"](api["HeadingHierarchyOptions"](
            enabled=True, use_numbering=True, use_style=False, use_bookmarks=False))(conv_res)
        docs["heading-hierarchy"] = conv_res.document
        for kind, document in docs.items():
            payload = document.export_to_dict(exclude_none=False)
            out_path = output / f"{kind}-{attempt}.json"
            write(out_path, payload)
            if attempt == 1:
                results[kind] = inspect_output(projected, payload)
                write(output / f"{kind}-mapping.json", results[kind])
                repeated[kind] = payload
            else:
                results[kind]["identical_repeat"] = repeated[kind] == payload
        write(output / f"schema-import-{attempt}.json", {"accepted": import_json(output / f"schema-{attempt}.json", api)["accepted"]})
    controls = {kind: [r for r in result["rows"] if "Приложение" in r["source_text"]
                      or r["page_no"] in (8, 9, 64, 65)] for kind, result in results.items()}
    write(output / "source-controls.json", controls)
    return {"key": entry["key"], "group": entry["group"], "native_sha256": entry["native_sha256"],
            "heading_prefixes_removed": len(ledger),
            "heading_level_changes": sum(a.get("level") != b.get("level") for a, b in zip(
                repeated["reading-order"]["texts"], repeated["heading-hierarchy"]["texts"], strict=True)),
            "raw_native_import_accepted": json.loads((output / "raw-native-import.json").read_text(encoding="utf-8"))["accepted"],
            "stages": {key: {k: v for k, v in value.items() if k != "rows"} for key, value in results.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--strip-heading-markdown-prefix", action="store_true",
                        help="Separate bounded profile: remove only leading ##/### plus spaces before heading-level inference.")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, args.output_dir / "runner.py")
    index_path = args.input_dir / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    protected = {path: digest(path) for path in index["protected_sha256"]}
    if protected != index["protected_sha256"]:
        raise ValueError("protected source bytes changed before run")
    api = runtime()
    modules = [api[name].__module__ for name in ("ReadingOrderModel", "HeadingHierarchyModel", "DoclingJSONBackend")]
    modules += ["docling.models.postprocessing.reading_order_rb"]
    code = {module: {"path": sys.modules[module].__file__, "sha256": digest(sys.modules[module].__file__)} for module in modules}
    write(args.output_dir / "freeze.json", {"runner_sha256": digest(__file__), "input_index_sha256": digest(index_path),
          "python": sys.executable, "python_version": platform.python_version(), "argv": sys.argv,
          "versions": {name: version(name) for name in ("docling", "docling-core", "pydantic")}, "code": code,
          "offline": True, "socket_connect_denied": True, "protected_before": protected,
          "reading_order_options": api["ReadingOrderOptions"]().model_dump(),
          "heading_options": {"enabled": True, "use_numbering": True, "use_style": False, "use_bookmarks": False},
          "heading_strip_markdown_prefix": args.strip_heading_markdown_prefix,
          "limits": ["adapter supplies source categories, table cells and regions", "schema conversion is not inference",
                     "Cluster confidence=1.0 is the library default, not measured OCR confidence",
                     "table header flag maps to column_header; row_header is unknown and defaults false",
                     "optional heading prefix projection changes text only, retaining raw orig/provenance and exact ledger",
                     "reading-order stage receives native assembled objects, no PDF pipeline",
                     "picture text stays in sidecar if native stage does not materialize it",
                     "reading-order origin mimetype application/pdf is library default; actual input remains native JSON",
                     "no inferred legal parents, no production parser, no reserved inputs or gold"]})
    results = []
    for entry in index["documents"]:
        started = time.perf_counter()
        output = args.output_dir / entry["key"]
        try:
            result = run_entry(entry, output, api, args.strip_heading_markdown_prefix)
            result["seconds"] = time.perf_counter() - started
            results.append(result)
            print(json.dumps({"key": entry["key"], "status": "complete", "seconds": result["seconds"]}), flush=True)
        except Exception:
            failure = {"key": entry["key"], "error": traceback.format_exc()}
            write(output / "failure.json", failure)
            results.append(failure)
            print(json.dumps({"key": entry["key"], "status": "failed"}), flush=True)
    protected_after = {path: digest(path) for path in protected}
    write(args.output_dir / "results.json", {"documents": results, "protected_unchanged": protected_after == protected,
                                           "protected_after": protected_after})
    if any("error" in result for result in results) or protected_after != protected:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
