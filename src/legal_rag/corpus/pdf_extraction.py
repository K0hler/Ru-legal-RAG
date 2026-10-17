"""Normalize retained OCR evidence without importing an inference runtime."""

from html.parser import HTMLParser
import math
import re

from .compiler import content_hash

VERSION = "dotsmocr-extraction/1"
CATEGORIES = {"Title", "Section-header", "Text", "List-item", "Table", "Picture",
              "Footnote", "Page-header", "Page-footer", "Caption", "Formula"}


class _Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.cell = None
        self.inside = False
        self.closed = False
        self.events = []
        self.outside = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.inside or self.closed:
                raise ValueError("nested or multiple OCR tables")
            self.inside = True
        elif tag == "tr":
            if not self.inside or self.cell is not None:
                raise ValueError("invalid OCR table row")
            self.rows.append([])
        elif tag in {"td", "th"}:
            if not self.inside or not self.rows or self.cell is not None:
                raise ValueError("invalid OCR table cell")
            attrs = dict(attrs)
            spans = [attrs.get(name, "1") for name in ("rowspan", "colspan")]
            if any(not re.fullmatch(r"[1-9][0-9]{0,2}", value) for value in spans):
                raise ValueError("invalid OCR table span")
            self.cell = {"rowspan": int(spans[0]), "colspan": int(spans[1]),
                         "header": tag == "th", "parts": []}
        elif tag == "br" and self.cell is not None:
            self.cell["parts"].append("\n")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["parts"].append(data)
        elif data.strip():
            self.outside.append(data)
            self.events.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"}:
            if self.cell is None:
                raise ValueError("unbalanced OCR table cell")
            self.rows[-1].append(self.cell)
            self.events.append("".join(self.cell["parts"]))
            self.cell = None
        elif tag == "table":
            if not self.inside or self.cell is not None:
                raise ValueError("unbalanced OCR table")
            self.inside, self.closed = False, True

    def topology(self, html):
        self.feed(html)
        self.close()
        if not self.closed or self.inside or self.cell is not None or not self.rows:
            raise ValueError("incomplete OCR table")
        occupied, cells = set(), []
        for row, source_cells in enumerate(self.rows):
            column = 0
            for source in source_cells:
                while (row, column) in occupied:
                    column += 1
                if row + source["rowspan"] > len(self.rows):
                    raise ValueError("OCR table span exceeds its rows")
                footprint = {(r, c) for r in range(row, row + source["rowspan"])
                             for c in range(column, column + source["colspan"])}
                if occupied & footprint:
                    raise ValueError("overlapping OCR table cells")
                occupied.update(footprint)
                cells.append({"row": row, "column": column, "rowspan": source["rowspan"],
                              "colspan": source["colspan"], "header": source["header"],
                              "text": "".join(source["parts"]), "bbox": None})
                column += source["colspan"]
        columns = max((c for _, c in occupied), default=-1) + 1
        return {"rows": len(self.rows), "columns": columns, "cells": cells,
                "rectangular": len(occupied) == len(self.rows) * columns,
                "outside_cell_text": self.outside, "text": "\n".join(self.events)}


def _positive(value):
    return type(value) is int and value > 0


def normalize_dotsmocr(document: dict, run: dict, source_sha256: str) -> dict:
    """Keep native layout claims, exact OCR-string locators and all physical pages."""
    if not isinstance(document, dict) or not isinstance(run, dict):
        raise ValueError("OCR document and run must be objects")
    if (not re.fullmatch(r"[0-9a-f]{64}", source_sha256)
            or run.get("source_sha256") != source_sha256 or run.get("engine") != "dotsmocr"):
        raise ValueError("OCR source hash or engine mismatch")
    if run.get("status") != "complete" or run.get("failed_pages"):
        raise ValueError("OCR run is incomplete; inspect retained run.json")
    total, requested = run.get("source_pages"), run.get("requested_pages")
    if (not _positive(total) or not isinstance(requested, list) or not requested
            or any(not _positive(n) or n > total for n in requested)
            or len(set(requested)) != len(requested)
            or run.get("completed_pages") != requested):
        raise ValueError("invalid OCR physical-page coverage")
    model = run.get("model", {})
    if (not isinstance(model, dict) or model.get("repo") != "dots-studio/dots.mocr" or not model.get("revision")
            or not model.get("weights_sha256")):
        raise ValueError("OCR model revision and weight hashes are required")
    source_pages = document.get("pages")
    if (not isinstance(source_pages, list)
            or any(not isinstance(p, dict) for p in source_pages)
            or [p.get("page_number") for p in source_pages] != requested):
        raise ValueError("missing, duplicate or out-of-order OCR pages")
    pages, blocks, tokens, uncertainties = [], [], [], set()
    offset = 0
    for page_index, source_page in enumerate(source_pages):
        dimensions = source_page.get("image_size")
        if not isinstance(dimensions, list) or len(dimensions) != 2 or not all(map(_positive, dimensions)):
            raise ValueError("invalid OCR image dimensions")
        native = source_page.get("native", {})
        if not isinstance(native, dict):
            raise ValueError("native OCR response must be an object")
        choices = native.get("choices", [])
        if (not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict)
                or not isinstance(choices[0].get("message"), dict)):
            raise ValueError("native OCR choice/message must be objects")
        content = choices[0]["message"].get("content")
        if (source_page.get("error") or choices[0].get("finish_reason") != "stop"
                or not isinstance(content, str) or not content.strip()):
            raise ValueError("failed or truncated native OCR response")
        layout = source_page.get("layout")
        if not isinstance(layout, list) or not layout:
            raise ValueError("empty OCR layout requires explicit page review")
        page = {"page": requested[page_index], "mode": "ocr", "confidence": None,
                "image_size": dimensions, "coordinate_space": "rendered_image_pixels",
                "regions": [], "blocks": []}
        for region_index, source_region in enumerate(layout):
            if not isinstance(source_region, dict):
                raise ValueError("OCR regions must be objects")
            bbox, category = source_region.get("bbox"), source_region.get("category")
            if (not isinstance(bbox, list) or len(bbox) != 4
                    or any(type(n) not in {int, float} or not math.isfinite(n) for n in bbox)
                    or not 0 <= bbox[0] < bbox[2] <= dimensions[0]
                    or not 0 <= bbox[1] < bbox[3] <= dimensions[1] or not isinstance(category, str)):
                raise ValueError("invalid OCR region category or coordinates")
            pointer = f"/pages/{page_index}/layout/{region_index}"
            region_id = content_hash({"source": source_sha256, "page": page["page"], "region": region_index})
            region = {"region_id": region_id, "category": category, "bbox": bbox,
                      "json_pointer": pointer, "source_record": source_region}
            page["regions"].append(region)
            if category not in CATEGORIES:
                uncertainties.add("unknown_category:" + category)
            if source_region.get("ocr_issue"):
                uncertainties.add("picture_ocr_incomplete_response")
            text = source_region.get("text", "")
            if not isinstance(text, str):
                raise ValueError("OCR region text must be a string")
            if category == "Table":
                region["table"] = _Table().topology(text)
                if not region["table"]["rectangular"]:
                    uncertainties.add("nonrectangular_table")
                pieces = [region["table"]["text"]]
                if region["table"]["outside_cell_text"]:
                    uncertainties.add("table_text_outside_cells")
                uncertainties.add("table_content_unverified")
            else:
                pieces = text.splitlines(keepends=True)
            if not text.strip():
                uncertainties.add("image_without_transcription" if category == "Picture" else "empty_region")
            local_offset = 0
            for line_index, piece in enumerate(pieces):
                raw = text if category == "Table" else piece
                token_id = len(tokens)
                span = {"source_asset_sha256": source_sha256, "page": page["page"], "bbox": bbox,
                        "json_pointer": pointer + "/text", "ocr_char_start": local_offset,
                        "ocr_char_end": local_offset + len(raw), "char_start": offset,
                        "char_end": offset + len(raw), "offset_unit": "unicode_codepoints_in_ocr_projection",
                        "locator": f"ocr:{pointer}/text:chars:{local_offset}:{local_offset + len(raw)}"}
                block = {"block_id": token_id,
                         "source_block_id": content_hash({"region": region_id, "line": line_index}),
                         "source_region_id": region_id, "text": piece.strip(), "display_text": piece,
                         "original_text": raw, "original_html": text if category == "Table" else "",
                         "source_span": span, "text_node_ids": [token_id], "paragraph": token_id + 1,
                         "html_id": None, "html_start": None, "html_end": None,
                         "classes": ["mark"] if category == "Footnote" else [],
                         "note": category == "Footnote",
                         "exclusion_reason": None, "unsupported_structure": category == "Table",
                         "numbering_text": piece.strip(), "cleanup_mapping": [], "bbox": bbox,
                         "locator": span["locator"], "table_cells": region.get("table", {}).get("cells", [])}
                blocks.append(block)
                page["blocks"].append(block)
                tokens.append({"text_node_id": token_id, "raw_text": raw, "decoded_text": piece,
                               "source_span": span, "superscript": False, "kind": "ocr_text"})
                offset += len(raw)
                local_offset += len(raw)
        pages.append(page)
    identity = {key: model[key] for key in ("repo", "revision", "source_revision", "weights_sha256",
                                           "sha256", "license", "quantization") if key in model}
    extraction = {"schema_version": "text-extraction/1", "extractor_version": VERSION,
                  "source_asset_sha256": source_sha256, "models": [identity],
                  "config": {**run.get("config", {}), "picture_ocr": run.get("picture_ocr_config")},
                  "runtime_fingerprint": run.get("runtime_fingerprint"), "pages": pages, "blocks": blocks,
                  "text_nodes": tokens, "unsupported_regions": [], "uncertainties": sorted(uncertainties),
                  "coverage": {"source_pages": total, "requested_pages": requested,
                               "all_source_pages": sorted(requested) == list(range(1, total + 1))},
                  "document_tree": {"kind": "document", "children": [
                      {"kind": "page", "page": p["page"], "children": [
                          {"kind": "region", "region_id": r["region_id"], "category": r["category"],
                           "children": [{"kind": "cell", **cell} for cell in r.get("table", {}).get("cells", [])]}
                          for r in p["regions"]]} for p in pages]}}
    # Freeze independent copies: callers must not be able to mutate retained source records.
    import json

    extraction = json.loads(json.dumps(extraction, ensure_ascii=False, allow_nan=False))
    extraction["extraction_id"] = content_hash(extraction)
    return extraction


def pdf_tree(extraction: dict, declared_identity: str, role: str) -> dict:
    from copy import deepcopy

    from .ocr_structure import build_ocr_structure
    from .structure import build_structure

    tree = build_ocr_structure(extraction, declared_identity, role)
    if tree is None:
        tree = build_structure(extraction, declared_identity, role)
    tree["structural_issues"] = sorted(set(tree["structural_issues"] + ["pdf_structure_unqualified"]))
    tree["document_tree"] = deepcopy(extraction["document_tree"])
    tree["ocr_uncertainties"] = list(extraction["uncertainties"])
    return tree
