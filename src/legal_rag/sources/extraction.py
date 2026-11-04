"""Read the shared PDF text contract without importing the corpus runtime."""

from pathlib import Path
import re

from .acquisition import _read_json
from .relations import _stable_id


def read_pdf_extraction(index_path: Path | None, digest: str, page_count: int) -> dict:
    if index_path is None:
        raise ValueError("Run corpus extract separately, then replay with --extraction-index <index.json>.")
    index = _read_json(index_path)
    if (not isinstance(index, dict) or index.get("schema_version") != "extraction-index/1"
            or not isinstance(index.get("extractions"), dict)
            or index.get("index_id") != _stable_id({k: v for k, v in index.items() if k != "index_id"})):
        raise ValueError("corrupt shared extraction index; rerun corpus extract")
    reference = index["extractions"].get(digest)
    if not isinstance(reference, dict):
        raise ValueError(f"no shared extraction for PDF {digest}; run corpus extract and replay")
    extraction_id = reference.get("extraction_id")
    if (not isinstance(extraction_id, str) or not re.fullmatch(r"[0-9a-f]{64}", extraction_id)
            or reference.get("path") != extraction_id + ".json"):
        raise ValueError("invalid shared extraction reference")
    extraction = _read_json(index_path.parent / reference["path"])
    if (not isinstance(extraction, dict) or extraction.get("schema_version") != "text-extraction/1"
            or extraction.get("source_asset_sha256") != digest
            or extraction.get("extraction_id") != extraction_id
            or extraction_id != _stable_id({k: v for k, v in extraction.items() if k != "extraction_id"})):
        raise ValueError("corrupt or misbound shared PDF extraction")
    coverage = extraction.get("coverage")
    pages = extraction.get("pages")
    expected = list(range(1, page_count + 1))
    if (not isinstance(coverage, dict) or not isinstance(pages, list)
            or any(not isinstance(page, dict) or type(page.get("page")) is not int for page in pages)
            or coverage.get("all_source_pages") is not True
            or coverage.get("source_pages") != page_count
            or sorted(coverage["requested_pages"]) != expected
            or [page["page"] for page in pages] != expected):
        raise ValueError("shared extraction must cover every official PDF page exactly once")
    for page_index, page in enumerate(pages):
        blocks = page.get("blocks")
        if not isinstance(blocks, list) or any(not isinstance(block, dict) for block in blocks):
            raise ValueError("shared extraction page blocks must be objects")
        for block in blocks:
            span = block["source_span"]
            if (not isinstance(span, dict) or span.get("source_asset_sha256") != digest
                    or span.get("page") != page["page"]
                    or not isinstance(block.get("text"), str)
                    or not re.fullmatch(rf"/pages/{page_index}/layout/[0-9]+/text", span.get("json_pointer", ""))
                    or span.get("locator") != (
                        f"ocr:{span.get('json_pointer')}:chars:{span.get('ocr_char_start')}:{span.get('ocr_char_end')}")):
                raise ValueError("shared extraction has missing or misbound page/text locators")
            region_index = int(span["json_pointer"].split("/")[4])
            regions = page["regions"]
            start, end = span.get("ocr_char_start"), span.get("ocr_char_end")
            if region_index >= len(regions) or type(start) is not int or type(end) is not int:
                raise ValueError("shared extraction text span has no source region or character bounds")
            region = regions[region_index]
            if not isinstance(region, dict) or not isinstance(region.get("source_record"), dict):
                raise ValueError("shared extraction source region must be an object")
            source_text = region["source_record"].get("text", "")
            if (region["json_pointer"] + "/text" != span["json_pointer"]
                    or not isinstance(source_text, str)
                    or not 0 <= start <= end <= len(source_text)
                    or block.get("original_text") != source_text[start:end]):
                raise ValueError("shared extraction text span does not identify its retained source text")
            projected = region["table"]["text"] if region["category"] == "Table" else source_text[start:end]
            if not isinstance(projected, str) or block["text"] != projected.strip():
                raise ValueError("shared extraction block text differs from its source span")
    return extraction
