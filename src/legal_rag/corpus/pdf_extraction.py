"""Normalize retained OCR evidence without importing an inference runtime."""

from html.parser import HTMLParser
import json
import math
import re

from .compiler import content_hash

VERSION = "dotsmocr-extraction/1"
CATEGORIES = {"Title", "Section-header", "Text", "List-item", "Table", "Picture",
              "Footnote", "Page-header", "Page-footer", "Caption", "Formula"}


class _GridError(ValueError):
    """The cell spans cannot form one grid; the HTML itself is well formed."""


class _Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.cell = None
        self.inside = False
        self.closed = False
        self.events = []
        self.outside = []
        # Enclosing tables of a table nested in a cell (observed: favt-150-2023 p. 63).
        self.parents = []
        self.after_table = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.inside and self.cell is not None:
                self.parents.append((self.rows, self.cell, self.events, self.outside))
                self.rows, self.cell, self.events, self.outside = [], None, [], []
            elif self.inside or self.closed:
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
            if self.after_table and data.strip():
                self.cell["parts"].append("\n")
            self.after_table = False
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
            self.cell, self.after_table = None, False
        elif tag == "table":
            if not self.inside or self.cell is not None:
                raise ValueError("unbalanced OCR table")
            if self.parents:
                # The nested table keeps its own topology; its text stays in the enclosing cell once.
                nested = self._finish()
                self.rows, self.cell, self.events, self.outside = self.parents.pop()
                before = "".join(self.cell["parts"])
                self.cell.setdefault("tables", []).append(nested)
                self.cell["parts"].append(("\n" if before.strip() and not before.endswith("\n") else "")
                                          + nested["text"])
                self.after_table = True
            else:
                self.inside, self.closed = False, True

    def topology(self, html):
        self.feed(html)
        self.close()
        if not self.closed or self.inside or self.cell is not None:
            raise ValueError("incomplete OCR table")
        return self._finish()

    def _finish(self):
        if not self.rows:
            raise ValueError("incomplete OCR table")
        try:
            return self._grid()
        except _GridError as error:
            # Well-formed HTML with an impossible grid: keep every source cell and its text,
            # but claim no column positions instead of failing the whole document.
            cells = [self._cell(source, row, None)
                     for row, source_cells in enumerate(self.rows) for source in source_cells]
            return {"rows": len(self.rows), "columns": None, "cells": cells, "rectangular": False,
                    "grid": "unresolved", "grid_error": str(error),
                    "outside_cell_text": self.outside, "text": "\n".join(self.events)}

    @staticmethod
    def _cell(source, row, column):
        cell = {"row": row, "column": column, "rowspan": source["rowspan"],
                "colspan": source["colspan"], "header": source["header"],
                "text": "".join(source["parts"]), "bbox": None}
        if "tables" in source:
            cell["tables"] = source["tables"]
        return cell

    def _grid(self):
        occupied, cells = set(), []
        for row, source_cells in enumerate(self.rows):
            column = 0
            for source in source_cells:
                while (row, column) in occupied:
                    column += 1
                if row + source["rowspan"] > len(self.rows):
                    raise _GridError("OCR table span exceeds its rows")
                footprint = {(r, c) for r in range(row, row + source["rowspan"])
                             for c in range(column, column + source["colspan"])}
                if occupied & footprint:
                    raise _GridError("overlapping OCR table cells")
                occupied.update(footprint)
                cells.append(self._cell(source, row, column))
                column += source["colspan"]
        columns = max((c for _, c in occupied), default=-1) + 1
        return {"rows": len(self.rows), "columns": columns, "cells": cells,
                "rectangular": len(occupied) == len(self.rows) * columns,
                "outside_cell_text": self.outside, "text": "\n".join(self.events)}


def _positive(value):
    return type(value) is int and value > 0


# The OCR-Lab rotation retry: at most these turns, in this order, after a token-limited page.
ROTATIONS = ("cw90", "ccw90")
UPRIGHT_TEXT = {"Text", "Title", "Section-header", "List-item", "Footnote", "Caption"}


def _unrotate(bbox, rotation, width, height):
    left, top, right, bottom = bbox
    if rotation == "cw90":
        return [top, height - right, bottom, height - left]
    return [width - bottom, left, width - top, right]


def _upright_cells(attempt):
    """Return an attempt's layout if it is complete and reads upright, otherwise None."""
    choices = attempt["native"].get("choices") if isinstance(attempt.get("native"), dict) else None
    if (not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict)
            or choices[0].get("finish_reason") != "stop" or attempt["native"].get("local_stop_reason")
            or attempt["native"].get("client_error")
            or not isinstance(choices[0].get("message"), dict)):
        return None
    try:
        cells = json.loads(choices[0]["message"].get("content") or "")
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(cells, list) or any(
            not isinstance(c, dict) or not isinstance(c.get("bbox"), list) or len(c["bbox"]) != 4
            or any(type(n) not in {int, float} for n in c["bbox"]) or "category" not in c for c in cells):
        return None
    text = [c["bbox"] for c in cells if c["category"] in UPRIGHT_TEXT]
    if not text or any(b[3] - b[1] >= 3 * (b[2] - b[0]) for b in text):
        return None
    return cells


def _check_rotated_layout(native, dimensions, layout):
    """A token-limited page may use the first accepted turned retry, re-derived from its evidence."""
    retry = native.get("orientation_retry")
    attempts = retry.get("attempts") if isinstance(retry, dict) else None
    if (not isinstance(attempts, list) or not 1 <= len(attempts) <= len(ROTATIONS)
            or any(not isinstance(a, dict) for a in attempts)
            or [a.get("rotation") for a in attempts] != list(ROTATIONS[:len(attempts)])
            or any(a.get("image_size") != dimensions[::-1] for a in attempts)
            or retry.get("selected") != len(attempts) - 1
            or any(_upright_cells(a) is not None for a in attempts[:-1])):
        raise ValueError("invalid OCR rotation retry record")
    cells, rotation = _upright_cells(attempts[-1]), attempts[-1]["rotation"]
    if cells is None or not isinstance(layout, list) or len(layout) != len(cells) or any(
            not isinstance(region, dict) or region.get("category") != cell["category"]
            or region.get("rotated_bbox") != cell["bbox"] or region.get("page_rotation") != rotation
            or region.get("bbox") != _unrotate(cell["bbox"], rotation, *dimensions)
            or (region.get("text") != cell.get("text") and region.get("text_source") != "picture_ocr")
            for region, cell in zip(layout, cells)):
        raise ValueError("rotated OCR layout does not match its retained attempt")
    return rotation


# The OCR-Lab loop retry: upright re-reads of an unfinished page with these settings, in this order.
LOOP_SETTINGS = ({"repetition_penalty": 1.1}, {"frequency_penalty": 0.3})


def _unfinished(native, choice):
    """The primary hit a limit, timed out, or was cancelled for a long repeated tail."""
    return (choice.get("finish_reason") == "length" or bool(native.get("client_error"))
            or native.get("local_stop_reason") == "tail_repetition")


def _loop_cells(native):
    """Return a finished upright retry layout without repeated regions, otherwise None."""
    choices = native.get("choices") if isinstance(native, dict) else None
    if (not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict)
            or choices[0].get("finish_reason") != "stop" or native.get("local_stop_reason")
            or native.get("client_error") or not isinstance(choices[0].get("message"), dict)):
        return None
    try:
        cells = json.loads(choices[0]["message"].get("content") or "")
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(cells, list) or not cells or any(
            not isinstance(c, dict) or not isinstance(c.get("bbox"), list) or len(c["bbox"]) != 4
            or any(type(n) not in {int, float} for n in c["bbox"]) or "category" not in c for c in cells):
        return None
    if any(b[3] - b[1] >= 3 * (b[2] - b[0]) for b in (c["bbox"] for c in cells if c["category"] in UPRIGHT_TEXT)):
        return None
    keys = [json.dumps([c["category"], c["bbox"], c.get("text")], ensure_ascii=False) for c in cells]
    return cells if len(set(keys)) == len(keys) else None


PARTIAL_REGION = re.compile(r'\{"bbox": \[(\d+), (\d+), (\d+), (\d+)\], "category": "([A-Za-z-]+)"')


def _upright_partial(native, choice):
    """The unfinished primary already read text regions upright, so the client skipped the turns."""
    content = choice["message"].get("content")
    text = [[int(n) for n in m[:4]] for m in PARTIAL_REGION.findall(content if isinstance(content, str) else "")
            if m[4] in UPRIGHT_TEXT]
    return bool(text) and not any(b[3] - b[1] >= 3 * (b[2] - b[0]) for b in text)


def _check_loop_layout(native, dimensions, layout, turns_expected):
    """An unfinished page may use the first accepted upright retry, re-derived from its evidence."""
    retry = native.get("loop_retry")
    attempts = retry.get("attempts") if isinstance(retry, dict) else None
    if (not isinstance(attempts, list) or not 1 <= len(attempts) <= len(LOOP_SETTINGS)
            or any(not isinstance(a, dict) for a in attempts)
            or [a.get("penalties") for a in attempts] != list(LOOP_SETTINGS[:len(attempts)])
            or retry.get("selected") != len(attempts) - 1
            or any(_loop_cells(a.get("native")) is not None for a in attempts[:-1])):
        raise ValueError("invalid OCR loop retry record")
    turned = native.get("orientation_retry")
    if "turns_skipped" in retry:
        if (retry["turns_skipped"] != "upright_partial" or turned is not None or not turns_expected
                or not _upright_partial(native, native["choices"][0])):
            raise ValueError("invalid OCR loop retry record")
    elif turns_expected and turned is None:
        raise ValueError("invalid OCR loop retry record")
    if turned is not None:
        # The turns come first; the loop retry runs only after both were rejected.
        turns = turned.get("attempts") if isinstance(turned, dict) else None
        if (not isinstance(turns, list) or [t.get("rotation") if isinstance(t, dict) else None for t in turns]
                != list(ROTATIONS) or turned.get("selected") is not None
                or any(t.get("image_size") != dimensions[::-1] or _upright_cells(t) is not None for t in turns)):
            raise ValueError("invalid OCR rotation retry record")
    cells = _loop_cells(attempts[-1]["native"])
    if cells is None or not isinstance(layout, list) or len(layout) != len(cells) or any(
            not isinstance(region, dict) or region.get("category") != cell["category"]
            or region.get("bbox") != cell["bbox"] or "rotated_bbox" in region
            or (region.get("text") != cell.get("text") and region.get("text_source") != "picture_ocr")
            for region, cell in zip(layout, cells)):
        raise ValueError("loop-retry OCR layout does not match its retained attempt")
    return attempts[-1]["penalties"]


def _check_page_orientation(page, policy):
    """Validate source-space boxes, then expose the sent-image boxes to existing retry checks."""
    record, dimensions, layout = page.get("page_orientation"), page["image_size"], page.get("layout")
    if not isinstance(record, dict) or not isinstance(policy, dict):
        raise ValueError("missing OCR page orientation evidence")
    if (policy.get("package") != "rapid-orientation" or policy.get("version") != "0.0.11"
            or policy.get("backend") != "CPUExecutionProvider" or policy.get("direction") != "counterclockwise"
            or policy.get("min_confidence") != 0.85 or policy.get("score") != "minimum_crop_probability"
            or policy.get("model_sha256") != "2f62c9bfb830a0b417241269fde7ef2d0ad5446c0ed2b8af33b1f6543545e8e2"):
        raise ValueError("unsupported OCR page orientation policy")
    angle = record.get("angle")
    if type(angle) is not int or angle not in (0, 90, 180, 270):
        raise ValueError("invalid OCR page orientation angle")
    predicted, confidence = record.get("predicted_angle"), record.get("confidence")
    if (type(predicted) is not int or predicted not in (0, 90, 180, 270)
            or type(confidence) not in {int, float} or not math.isfinite(confidence) or not 0 <= confidence <= 1
            or angle != (predicted if confidence >= policy["min_confidence"] else 0)):
        raise ValueError("invalid OCR page orientation confidence/decision")
    sent_size = dimensions[::-1] if angle in (90, 270) else dimensions
    if record.get("image_size") != sent_size or not isinstance(layout, list):
        raise ValueError("invalid OCR page orientation dimensions/layout")
    sent = []
    width, height = dimensions
    for region in layout:
        if not isinstance(region, dict):
            raise ValueError("invalid oriented OCR region")
        bbox = region.get("oriented_bbox") if angle else region.get("bbox")
        if (not isinstance(bbox, list) or len(bbox) != 4
                or any(type(n) not in {int, float} or not math.isfinite(n) for n in bbox)
                or not 0 <= bbox[0] < bbox[2] <= sent_size[0]
                or not 0 <= bbox[1] < bbox[3] <= sent_size[1]):
            raise ValueError("invalid oriented OCR coordinates")
        left, top, right, bottom = bbox
        original = ([width-right, height-bottom, width-left, height-top] if angle == 180 else
                    _unrotate(bbox, "ccw90" if angle == 90 else "cw90", width, height) if angle else bbox)
        if region.get("bbox") != original or (not angle and "oriented_bbox" in region):
            raise ValueError("oriented OCR coordinates do not match source page")
        sent.append({key: value for key, value in {**region, "bbox": bbox}.items() if key != "oriented_bbox"})
    # Successful primary responses need the same evidence binding as recovered pages.
    native = page.get("native", {})
    choices = native.get("choices", []) if isinstance(native, dict) else []
    if isinstance(choices, list) and len(choices) == 1 and not _unfinished(native, choices[0]):
        try:
            cells = json.loads(choices[0]["message"]["content"])
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError("invalid oriented OCR native layout") from error
        if not isinstance(cells, list) or len(cells) != len(sent) or any(
                not isinstance(cell, dict) or cell.get("bbox") != region["bbox"]
                or cell.get("category") != region.get("category")
                or (cell.get("text") != region.get("text") and region.get("text_source") != "picture_ocr")
                for cell, region in zip(cells, sent)):
            raise ValueError("oriented OCR layout does not match native response")
    return sent_size, sent


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
        layout = source_page.get("layout")
        check_dimensions, check_layout = dimensions, layout
        orientation_policy = (run.get("config") or {}).get("page_orientation")
        if "page_orientation" in source_page or orientation_policy is not None:
            check_dimensions, check_layout = _check_page_orientation(source_page, orientation_policy)
        elif isinstance(layout, list) and any(isinstance(r, dict) and "oriented_bbox" in r for r in layout):
            raise ValueError("oriented OCR layout needs page orientation evidence")
        rotation = loop = None
        if source_page.get("error"):
            raise ValueError("failed or truncated native OCR response")
        if "loop_retry" in native and _unfinished(native, choices[0]):
            loop = _check_loop_layout(native, check_dimensions, check_layout, "rotation_retry" in (run.get("config") or {}))
            uncertainties.add("page_loop_retry")
        elif "orientation_retry" in native and _unfinished(native, choices[0]):
            rotation = _check_rotated_layout(native, check_dimensions, check_layout)
            uncertainties.add("page_orientation_retry")
        elif (choices[0].get("finish_reason") != "stop" or "orientation_retry" in native or "loop_retry" in native
                or native.get("client_error") or native.get("local_stop_reason")
                or not isinstance(content, str) or not content.strip()):
            raise ValueError("failed or truncated native OCR response")
        if not isinstance(layout, list) or not layout:
            raise ValueError("empty OCR layout requires explicit page review")
        page = {"page": requested[page_index], "mode": "ocr", "confidence": None,
                "image_size": dimensions, "coordinate_space": "rendered_image_pixels",
                "regions": [], "blocks": []}
        if "page_orientation" in source_page:
            page["page_orientation"] = source_page["page_orientation"]
        if rotation is not None:
            page["orientation_retry"] = rotation
        if loop is not None:
            page["loop_retry"] = loop
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
                if region["table"].get("grid") == "unresolved":
                    uncertainties.add("table_grid_unresolved")
                if any("tables" in cell for cell in region["table"]["cells"]):
                    uncertainties.add("table_nested")
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
