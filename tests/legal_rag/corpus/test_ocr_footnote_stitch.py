"""Authored continuation controls; no OCR engines or private corpus files."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def load_script(name):
    path = Path(__file__).resolve().parents[3] / f"docs/assets/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def region(text, category="Text", bbox=None):
    return {"text": text, "category": category, "bbox": bbox or [10, 820, 190, 870]}


def document(continuation_category="Text"):
    return {"opaque": {"keep": True}, "pages": [
        {"page_number": 4, "image_size": [200, 1000], "layout": [
            region("7. Основной текст⁹.", bbox=[10, 100, 190, 750]),
            region("⁸ Законченная сноска.", "Footnote"),
            region("⁹ Длинная сноска, приказ от 03.04.2020 № 123", "Footnote"),
        ]},
        {"page_number": 5, "image_size": [200, 1000], "layout": [
            region("8. Следующий пункт.", bbox=[10, 100, 190, 800]),
            region("(зарегистрирован 05.06.2020).", continuation_category),
            region("¹⁰ Новая сноска.", "Footnote", [10, 870, 160, 920]),
        ]},
    ]}


@pytest.mark.parametrize("category", ["Footnote", "Text"])
def test_joins_last_previous_note_and_preserves_physical_fragments(category):
    script = load_script("stitch_ocr_footnotes")
    native = document(category)
    original = copy.deepcopy(native)
    result = script.stitch(native)
    assert native == original
    assert result == script.stitch(native)
    assert result["region_order"] == [
        "/pages/0/layout/0/text", "/pages/0/layout/1/text", "/pages/0/layout/2/text",
        "/pages/1/layout/1/text", "/pages/1/layout/0/text", "/pages/1/layout/2/text",
    ]
    note, = result["footnotes"]
    assert note["text"] == "⁹ Длинная сноска, приказ от 03.04.2020 № 123\n(зарегистрирован 05.06.2020)."
    assert [f["page"] for f in note["fragments"]] == [4, 5]
    assert [f["category"] for f in note["fragments"]] == ["Footnote", category]
    for fragment in note["fragments"]:
        pi, ri = map(int, fragment["json_pointer"].split("/")[2:5:2])
        source = native["pages"][pi]["layout"][ri]
        assert fragment["bbox"] == source["bbox"]
        assert note["text"][fragment["start"]:fragment["end"]] == source["text"]


@pytest.mark.parametrize("case", ["gap", "no_previous_note", "body", "bottom_body", "non_citation",
                                 "far_from_notes", "finished", "new_number", "letter_list", "table", "after_new_note"])
def test_does_not_join_body_new_notes_or_nonadjacent_pages(case):
    script = load_script("stitch_ocr_footnotes")
    native = document()
    pages = native["pages"]
    candidate = pages[1]["layout"][1]
    if case == "gap":
        pages[1]["page_number"] = 6
    elif case == "no_previous_note":
        pages[0]["layout"] = pages[0]["layout"][:1]
    elif case == "body":
        candidate["bbox"] = [10, 500, 190, 600]
    elif case == "bottom_body":
        candidate["text"] = "Обычный законченный абзац внизу страницы."
    elif case == "non_citation":
        pages[0]["layout"][-1]["text"] = "⁹ Незавершённая фраза"
    elif case == "far_from_notes":
        candidate["bbox"] = [10, 780, 190, 830]
    elif case == "finished":
        pages[0]["layout"][-1]["text"] += "."
    elif case == "new_number":
        candidate["text"] = "[10] Новая сноска."
        candidate["category"] = "Footnote"
    elif case == "letter_list":
        candidate["text"] = "а) Обычный элемент списка;"
    elif case == "table":
        candidate["category"] = "Table"
    elif case == "after_new_note":
        candidate["category"] = "Footnote"
        pages[1]["layout"][1:3] = list(reversed(pages[1]["layout"][1:3]))
    assert script.stitch(native)["footnotes"] == []


def test_does_not_walk_back_into_adjacent_lower_body_paragraphs():
    script = load_script("stitch_ocr_footnotes")
    native = document()
    native["pages"][1]["layout"].insert(1, region("Обычный нижний абзац.", bbox=[10, 800, 190, 820]))
    note, = script.stitch(native)["footnotes"]
    assert len(note["fragments"]) == 2


def test_numberless_tagged_note_does_not_require_neighboring_numbered_notes():
    script = load_script("stitch_ocr_footnotes")
    native = document("Footnote")
    native["pages"][1]["layout"].pop()
    assert len(script.stitch(native)["footnotes"]) == 1
    native["pages"][1]["layout"][1]["category"] = "Text"
    assert script.stitch(native)["footnotes"] == []


def test_three_page_note_keeps_one_anchor():
    script = load_script("stitch_ocr_footnotes")
    native = document("Footnote")
    native["pages"][1]["layout"].pop()
    native["pages"].append({"page_number": 6, "image_size": [200, 1000],
                            "layout": [region("Окончание.", "Footnote")]})
    note, = script.stitch(native)["footnotes"]
    assert [f["page"] for f in note["fragments"]] == [4, 5, 6]
    assert len(set(script.stitch(native)["region_order"])) == 6


def test_cli_retains_input_hash_and_refuses_overwrite(tmp_path):
    script = load_script("stitch_ocr_footnotes")
    source, output = tmp_path / "native.json", tmp_path / "joined.json"
    raw = json.dumps(document(), ensure_ascii=False).encode("utf-8")
    source.write_bytes(raw)
    script.run(source, output)
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert len(result["footnotes"]) == 1
    with pytest.raises(FileExistsError):
        script.run(source, output)
    assert source.read_bytes() == raw


def test_dedoc_projection_consumes_join_order_without_faking_source_page_or_bbox():
    script = load_script("stitch_ocr_footnotes")
    probe = load_script("run_dedoc_json_probe")
    native = document()
    extraction = {"source_asset_sha256": "a" * 64, "pages": [
        {"page": p["page_number"], "regions": [
            {"region_id": f"r{pi}-{ri}", "json_pointer": f"/pages/{pi}/layout/{ri}", "source_record": r}
            for ri, r in enumerate(p["layout"])]}
        for pi, p in enumerate(native["pages"])]}
    plain = probe.project(native, extraction)
    joined = probe.project(native, extraction, footnote_view=script.stitch(native))
    assert [x["uid"] for x in joined["lines"]] == ["r0-0:0", "r0-1:0", "r0-2:0", "r1-1:0", "r1-0:0", "r1-2:0"]
    assert joined["lines"][3]["page"] == 5
    assert joined["lines"][3]["bbox"] == [10, 820, 190, 870]
    assert sorted(({k: v for k, v in x.items() if k != "line_id"} for x in plain["lines"]), key=str) == sorted(
        ({k: v for k, v in x.items() if k != "line_id"} for x in joined["lines"]), key=str)
    invalid = script.stitch(native)
    invalid["region_order"].pop()
    with pytest.raises(ValueError, match="region order"):
        probe.project(native, extraction, footnote_view=invalid)
