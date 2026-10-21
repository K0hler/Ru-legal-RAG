"""Authored controls for the logical-text layer (stage 2) over text-extraction/1; no corpus or OCR engine."""

import copy
import json
from pathlib import Path

import pytest

from legal_rag.corpus import logical_text as L
from legal_rag.corpus.__main__ import main as cli_main
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


def build(pages):
    return L.build_logical_text(extraction(pages))


def by_text(result, prefix):
    return next(p for p in result["paragraphs"] if p["text"].startswith(prefix))


def test_body_continuation_joins_across_page_break_and_noise():
    result = build([
        [("Text", "2. Документы передаются в составе, предусмотренном Правилами содержания,")],
        [("Page-header", "2"), ("Text", "утвержденных постановлением Правительства Российской Федерации № 491.")],
    ])
    assert len(result["paragraphs"]) == 1
    p = result["paragraphs"][0]
    assert [f["join"] for f in p["fragments"]] == [None, "body_continuation_after_page_break"]
    assert p["features"]["caption"] is None
    assert result["regions"][1]["paragraph_id"] is None
    assert result["regions"][2]["paragraph_id"] == 0


def test_terminated_or_marked_region_is_not_joined():
    result = build([
        [("Text", "1. Первый пункт;")],
        [("Text", "утвержденный иначе.")],
    ])
    assert len(result["paragraphs"]) == 2
    result = build([
        [("Text", "1. Первый пункт включает")],
        [("Text", "а) подпункт без продолжения")],
    ])
    assert len(result["paragraphs"]) == 2


def test_same_page_lowercase_region_is_not_joined():
    result = build([[("Text", "Первый абзац без точки"), ("Text", "второй абзац со строчной")]])
    assert len(result["paragraphs"]) == 2
    assert result["paragraphs"][1]["features"]["starts_lowercase"] is True


def test_no_join_across_missing_physical_page():
    data = extraction([[("Text", "Начало без точки")], [("Text", "Промежуточная.")], [("Text", "строчное начало")]])
    data["pages"][2]["page"] = 20
    data["pages"].pop(1)
    data["blocks"] = [b for b in data["blocks"] if b["source_region_id"] != "r2-0"]
    data["text_nodes"] = [t for t in data["text_nodes"] if t["text_node_id"] != "t2-0"]
    result = L.build_logical_text(data)
    assert [p["text"] for p in result["paragraphs"]] == ["Начало без точки", "строчное начало"]


def test_empty_region_never_receives_continuation():
    result = build([
        [("Text", "Незаконченный абзац"), ("Text", "")],
        [("Text", "продолжение строчное.")],
    ])
    kinds = [p["kind"] for p in result["paragraphs"]]
    assert kinds == ["text", "empty"]
    assert len(result["paragraphs"][0]["fragments"]) == 2
    assert result["paragraphs"][1]["fragments"][0]["text_node_ids"] == []
    assert result["paragraphs"][1]["text"] == ""


def test_footnote_flow_and_mislabelled_continuation():
    result = build([
        [("Section-header", "I. Общие положения"),
         ("Text", "1. Площадки обустраиваются¹."), ("Text", "2. Срок определяется по оценке²."),
         ("Footnote", "¹ Статья 13.4 закона."), ("Footnote", "² Приказ от 19.07.2007 № 224, от 04.04.2017 № 208")],
        [("Page-header", "2"), ("Text", "3. Сортировка не допускается."),
         ("Text", "4. Расстояние до площадок должно быть не менее 20 метров от зданий организаций"),
         ("Text", "(зарегистрирован Минюстом России 24.04.2017)."),
         ("Footnote", "³ Пункт 1 статьи 16 закона.")],
    ])
    note2 = by_text(result, "² Приказ")
    assert note2["flow"] == "footnote" and note2["kind"] == "footnote"
    assert [f["join"] for f in note2["fragments"]] == [None, "footnote_continuation_after_page_break"]
    assert note2["fragments"][1]["region_id"] == "r2-3"
    assert by_text(result, "¹ Статья")["features"]["footnote_number"] == 1
    assert note2["features"]["footnote_number"] == 2
    assert by_text(result, "³ Пункт")["features"]["footnote_number"] == 3
    assert by_text(result, "1. Площадки")["features"]["footnote_refs"] == [1]
    assert by_text(result, "4. Расстояние")["flow"] == "body"
    assert len(by_text(result, "4. Расстояние")["fragments"]) == 1


def test_fragment_offsets_reproduce_source_text():
    data = extraction([
        [("Text", "Начало без точки")],
        [("Text", "продолжение\nв две строки."), ("Picture", ""), ("Text", "## Заголовок")],
    ])
    originals = {r["region_id"]: r["text"] for r in L.classify_regions(data)}
    result = L.build_logical_text(data)
    seen = 0
    for p in result["paragraphs"]:
        for f in p["fragments"]:
            assert p["text"][f["start"]:f["end"]] == originals[f["region_id"]]
            seen += 1
        assert p["match_text"] == L.match_view(p["text"])
    assert seen == 4
    assert [p["kind"] for p in result["paragraphs"]] == ["text", "picture", "text"]


def test_accounting_determinism_and_no_mutation():
    data = extraction([
        [("Text", "Тело."), ("Page-header", "2"), ("Page-footer", "")],
        [("Text", "Тело 2.")],
    ])
    before = copy.deepcopy(data)
    first = L.build_logical_text(data)
    second = L.build_logical_text(data)
    assert data == before
    assert first == second and first["logical_text_id"] == second["logical_text_id"]
    acc = first["accounting"]
    assert acc["in_paragraphs"] + acc["in_noise"] == acc["text_nodes"] == 3
    assert first["logical_text_id"] == content_hash({k: v for k, v in first.items() if k != "logical_text_id"})
    assert first["schema_version"] == L.SCHEMA and first["builder_version"] == L.BUILDER


def test_rejects_broken_accounting_and_unknown_region():
    data = extraction([[("Text", "Тело.")]])
    broken = copy.deepcopy(data)
    broken["text_nodes"].append({"text_node_id": "orphan", "raw_text": "x"})
    with pytest.raises(ValueError, match="token accounting"):
        L.build_logical_text(broken)
    unknown = copy.deepcopy(data)
    unknown["blocks"].append({"source_region_id": "nope", "original_text": "x", "text_node_ids": []})
    with pytest.raises(ValueError, match="unknown source_region_id"):
        L.build_logical_text(unknown)


# --- CLI and immutable writer ---

def _write_extraction(tmp_path, data):
    path = tmp_path / "extraction.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def _run_cli(path, out):
    return cli_main(["logical-text", "--extraction", str(path), "--output-dir", str(out)])


def test_cli_writes_once_then_reports_unchanged(tmp_path, capsys):
    path = _write_extraction(tmp_path, extraction([[("Text", "Первый абзац.")]]))
    out = tmp_path / "out"
    assert _run_cli(path, out) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["result"] == "new"
    target = out / "logical-text" / f"{first['logical_text_id']}.json"
    assert target.is_file()
    before = target.read_bytes()
    assert _run_cli(path, out) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["result"] == "unchanged"
    assert second["logical_text_id"] == first["logical_text_id"]
    assert target.read_bytes() == before


def test_cli_rejects_tampered_extraction_before_writing(tmp_path, capsys):
    data = extraction([[("Text", "Первый абзац.")]])
    data["blocks"][0]["original_text"] = "Первый абзаЦ."
    path = _write_extraction(tmp_path, data)
    out = tmp_path / "out"
    assert _run_cli(path, out) == 2
    assert "extraction hash mismatch" in capsys.readouterr().err
    assert not (out / "logical-text").exists()


def test_cli_rejects_other_schema(tmp_path, capsys):
    data = extraction([[("Text", "Первый абзац.")]])
    data["schema_version"] = "text-extraction/0"
    path = _write_extraction(tmp_path, data)
    assert _run_cli(path, tmp_path / "out") == 2
    assert "unsupported extraction schema_version" in capsys.readouterr().err
    assert not (tmp_path / "out" / "logical-text").exists()


@pytest.mark.parametrize("missing", ["extraction_id", "source_asset_sha256"])
def test_cli_rejects_missing_identity_fields(tmp_path, missing):
    data = extraction([[("Text", "Первый абзац.")]])
    del data[missing]
    path = _write_extraction(tmp_path, data)
    assert _run_cli(path, tmp_path / "out") == 2
    assert not (tmp_path / "out" / "logical-text").exists()


def test_write_refuses_to_overwrite_different_bytes(tmp_path):
    path = _write_extraction(tmp_path, extraction([[("Text", "Первый абзац.")]]))
    result = L.write_logical_text(path, tmp_path / "out")
    Path(result["path"]).write_bytes(b"{}")
    with pytest.raises(ValueError):
        L.write_logical_text(path, tmp_path / "out")
    assert Path(result["path"]).read_bytes() == b"{}"


def test_digit_normalized_running_text_is_repeated_noise():
    data = extraction([[("Text", "Тело."), ("Page-footer", f"Страница {n}")] for n in (2, 3, 4)])
    got = roles(data)
    assert {got[f"r{p}-1"] for p in (1, 2, 3)} == {("noise", "repeated_running_text")}


def test_annex_caption_in_three_page_running_region_stays_content():
    data = extraction([[("Page-header", "Приложение № 1"), ("Text", "Тело.")] for _ in range(3)])
    got = roles(data)
    assert {got[f"r{p}-0"] for p in (1, 2, 3)} == {("content", None)}


def test_unnumbered_footnote_not_joined_across_missing_page():
    data = extraction([[("Footnote", "¹ Сноска без точки")], [("Footnote", "продолжение сноски.")]])
    data["pages"][1]["page"] = 3
    result = L.build_logical_text(data)
    assert [len(p["fragments"]) for p in result["paragraphs"]] == [1, 1]
    adjacent = build([[("Footnote", "¹ Сноска без точки")], [("Footnote", "продолжение сноски.")]])
    assert [f["join"] for f in adjacent["paragraphs"][0]["fragments"]] == [None, L.JOIN_NOTE_UNNUMBERED]


# --- evaluator: prototype parity and stage-2 metrics ---

def _load_script(name):
    import importlib.util
    import sys
    path = Path(__file__).resolve().parents[3] / f"docs/assets/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their module during class creation
    spec.loader.exec_module(module)
    return module


def test_evaluator_parity_labels_and_metrics(tmp_path):
    evaluator = _load_script("evaluate_logical_text")
    data = extraction([
        [("Section-header", "I. Общие положения"), ("Text", "Абзац без точки")],
        [("Text", "продолжение абзаца.")],
        [("Text", "Ещё абзац без точки")],
        [("Text", "строчное продолжение.")],
    ])
    data["pages"][3]["page"] = 5  # physical page 4 is missing: the prototype joins, we do not (D1)
    inputs, gold = tmp_path / "inputs", tmp_path / "gold"
    inputs.mkdir()
    gold.mkdir()
    (inputs / "doc.extraction.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (gold / "doc.gold.txt").write_text("1.1 A\n2.0 A +\n", encoding="utf-8")
    out = tmp_path / "out"
    assert evaluator.main(["--inputs", str(inputs), "--gold", str(gold), "--output", str(out)]) == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["continuation"] == {"tp": 1, "fp": 0, "fn": 0}
    assert summary["false_exclusion"] == 0 and summary["missed_exclusion"] == 0
    assert summary["parity"] == {"D1": 1, "D2": 0, "unexpected": 0}
    diff = summary["documents"][0]["diffs"][0]
    assert diff["label"] == "D1" and diff["prototype"] == [["r3-0", "r4-0"]]
    with pytest.raises(SystemExit):
        evaluator.main(["--inputs", str(inputs), "--gold", str(gold), "--output", str(out)])


def test_evaluator_labels_empty_region_d2_and_same_page_split_unexpected():
    evaluator = _load_script("evaluate_logical_text")
    pages = {"a": 1, "e": 1, "b": 2, "c": 3, "d": 3}
    d2 = evaluator.label_component([("e", "b")], [("e",), ("b",)], {"e"}, pages)
    assert d2 == "D2"
    unexpected = evaluator.label_component([("c", "d")], [("c",), ("d",)], set(), pages)
    assert unexpected == "unexpected"
    d1 = evaluator.label_component([("a", "c")], [("a",), ("c",)], set(), pages)
    assert d1 == "D1"
    pages = {"a": 1, "b": 2, "c": 4}
    mixed = evaluator.label_component([("a", "b", "c")], [("a",), ("b",), ("c",)], set(), pages)
    assert mixed == "unexpected"  # a|b is an adjacent-page split, not a gap
    gap_only = evaluator.label_component([("a", "b", "c")], [("a", "b"), ("c",)], set(), pages)
    assert gap_only == "D1"


def test_footnote_continued_in_two_unnumbered_regions_on_next_page_is_one_paragraph():
    result = build([[("Footnote", "¹ Сноска без точки")],
                    [("Footnote", "продолжение сноски"), ("Footnote", "и ещё продолжение.")]])
    assert [[f["region_id"] for f in p["fragments"]] for p in result["paragraphs"]] == [["r1-0", "r2-0", "r2-1"]]
    assert [f["join"] for f in result["paragraphs"][0]["fragments"]] == [
        None, L.JOIN_NOTE_UNNUMBERED, L.JOIN_NOTE_UNNUMBERED]


@pytest.mark.parametrize("text,category", [
    ("12. 02. 2026 № 5 приказ", "Text"),
    ("12.02.2026 № 5 приказ", "Text"),
    ("IV. Раздел", "Section-header"),
    ("IV. Раздел", "Text"),
    ("IV. Длинное предложение, которое заканчивается точкой.", "Text"),
    ("IV. Длинное предложение, которое заканчивается точкой.", "Section-header"),
    ("1.2. пункт", "Text"), ("3. пункт", "Text"), ("4) пункт", "Text"), ("а) пункт", "Text"),
    ("ё) пункт", "Text"), ("- пункт", "Text"), ("обычный текст", "Text"),
])
def test_has_marker_agrees_with_prototype_parse_marker(text, category):
    prototype = _load_script("ocr_logical_structure")
    assert L._has_marker(text, category) == (prototype.parse_marker(text, category).kind != "none")
