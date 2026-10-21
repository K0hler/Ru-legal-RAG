"""Authored controls for the logical-text layer (stage 2) over text-extraction/1; no corpus or OCR engine."""

import copy

from legal_rag.corpus import logical_text as L
from legal_rag.corpus.compiler import content_hash


def extraction(pages):
    """pages: list of lists of (category, text[, x]) tuples."""
    out = {
        "schema_version": "text-extraction/1",
        "source_asset_sha256": "0" * 64,
        "coverage": {"requested_pages": list(range(1, len(pages) + 1))},
        "pages": [], "blocks": [], "text_nodes": [],
    }
    for pno, regions in enumerate(pages, start=1):
        page = {"page": pno, "image_size": [1600, 2300], "regions": []}
        for index, item in enumerate(regions):
            category, text = item[0], item[1]
            x = item[2] if len(item) > 2 else 180
            rid = f"r{pno}-{index}"
            page["regions"].append({"region_id": rid, "category": category,
                                    "bbox": [x, 100 + index * 50, 1400, 140 + index * 50]})
            if text:
                tid = f"t{pno}-{index}"
                out["text_nodes"].append({"text_node_id": tid, "raw_text": text})
                out["blocks"].append({"source_region_id": rid, "original_text": text, "text_node_ids": [tid]})
        out["pages"].append(page)
    out["extraction_id"] = content_hash({key: value for key, value in out.items()})
    return out


def roles(extraction_data):
    return {r["region_id"]: (r["role"], r["role_reason"]) for r in L.classify_regions(extraction_data)}


def test_page_number_and_repeated_running_text_are_noise():
    data = extraction([
        [("Text", "Тело."), ("Page-header", "2"), ("Page-footer", "2059534.doc")],
        [("Text", "Тело."), ("Page-footer", "2059534.doc")],
        [("Text", "Тело."), ("Page-footer", "2059534.doc"), ("Page-footer", "")],
    ])
    got = roles(data)
    assert got["r1-1"] == ("noise", "page_number")
    assert got["r1-2"] == ("noise", "repeated_running_text")
    assert got["r2-1"] == ("noise", "repeated_running_text")
    assert got["r3-2"] == ("noise", "empty_running_region")
    assert got["r1-0"] == ("content", None)


def test_caption_in_running_region_stays_content():
    caption = "УТВЕРЖДЕНЫ\nпостановлением Правительства"
    data = extraction([[("Page-header", caption, 900)] for _ in range(3)])
    assert all(r["role"] == "content" for r in L.classify_regions(data))


def test_running_text_on_two_pages_stays_content():
    data = extraction([[("Page-footer", "doc.doc")], [("Page-footer", "doc.doc")]])
    assert all(r["role"] == "content" for r in L.classify_regions(data))


def test_picture_and_table_roles():
    data = extraction([[("Picture", ""), ("Table", "<table></table>")]])
    got = {r["category"]: r["role"] for r in L.classify_regions(data)}
    assert got == {"Picture": "picture", "Table": "table"}


def test_match_view_strips_markdown_prefix_only():
    text = "## I. Общие\n  положения"
    assert L.match_view(text) == "I. Общие положения"
    data = extraction([[("Section-header", text)]])
    region = L.classify_regions(data)[0]
    assert region["text"] == text
    assert region["match_text"] == "I. Общие положения"
    assert region["text_node_ids"] == ["t1-0"]


def test_is_caption_kinds_and_input_not_mutated():
    assert L.is_caption("УТВЕРЖДЕНЫ\nпостановлением") == "approval"
    assert L.is_caption("утверждены") is None
    assert L.is_caption("Приложение № 2") == "annex"
    assert L.is_caption("Приложение " + "к " + "x" * 130) is None
    data = extraction([[("Text", "a")]])
    before = copy.deepcopy(data)
    L.classify_regions(data)
    assert data == before
