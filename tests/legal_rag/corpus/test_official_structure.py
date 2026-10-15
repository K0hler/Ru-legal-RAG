import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from legal_rag.corpus.compiler import compile_input, json_bytes, manifest_digest
from legal_rag.corpus.native_text import extract_native
from legal_rag.corpus.official_structure import build_official_tree
from legal_rag.sources.actual_pravo import ActualPravoConnector
from legal_rag.sources.legislation_russia import LegislationRussiaConnector
from legal_rag.sources.structure_bundle import StructureConnector, acquire_bundle


IDENTITY = 'Федеральный закон от 02.05.2006 № 59-ФЗ "О порядке рассмотрения обращений граждан Российской Федерации"'
HTML = '''<html><head><title>Portal</title></head><body>
<p>РОССИЙСКАЯ ФЕДЕРАЦИЯ</p><p>ФЕДЕРАЛЬНЫЙ ЗАКОН</p>
<p>О порядке рассмотрения обращений граждан Российской Федерации</p>
<p id="a1">Статья 1. Проверка</p><p id="p1">2<sup>1</sup>. Текст.</p>
<p id="s1">а) Первая строка.<span class="mark"> (В редакции закона)</span></p>
<p class="A" id="note">(В редакции другого закона)</p>
<p id="end">Конец.</p><table><tr><td><p>Ячейка.</p></td></tr></table>
<p><img src="data:image/png;base64,AA=="></p>
<p>Президент Российской Федерации</p><p>2 мая 2006 года</p><p>№ 59-ФЗ</p>
</body></html>'''
ROWS = [
    {"id": "a1", "np": "a1", "npe": "end", "unit": "статья", "caption": "Статья 1. Проверка", "lvl": 0},
    {"id": "a1_p2", "np": "p1", "npe": "s1", "unit": "часть", "caption": "$часть 2<sup>1</sup>", "lvl": 1},
    {"id": "a1_p2_s1", "np": "s1", "npe": "s1", "unit": "подпункт", "caption": '$подпункт "а"', "lvl": 2},
]


def tree(html=HTML, rows=None, response=None):
    payload = json_bytes({"redtext": html})
    asset = {"sha256": hashlib.sha256(payload).hexdigest(), "evidence": {"locator": "$.redtext"},
             "declared_identity": IDENTITY, "role": "consolidated"}
    extraction = extract_native(asset, payload)
    sidecar = json_bytes({"status": 0, "complete": True, "data": ROWS if rows is None else rows} if response is None else response)
    return build_official_tree(asset, extraction, html, sidecar, hashlib.sha256(sidecar).hexdigest(), "actual.pravo.gov.ru")


def prepare(root, bank="actual"):
    actual = bank == "actual"
    filename = "actual_pravo_59_fz.json" if actual else "legislation_russia_pp354.json"
    fixture = json.loads((Path(__file__).parent.parent / "sources/fixtures" / filename).read_bytes())
    if actual:
        fixture["redtext"] = {"redtext": HTML, "error": None}
    else:
        fixture["documenttext"]["doctext"] = HTML
    fields = ("card", "redactions", "redtext") if actual else ("card", "documenttext")
    bodies = [json_bytes(fixture[k]) for k in fields]
    bodies.append(json_bytes({"status": 0 if actual else 200, "complete": True, "data": ROWS}))
    base = ActualPravoConnector() if actual else LegislationRussiaConnector()
    calls = []

    def get(url):
        calls.append(url)
        return bodies[len(calls) - 1], {"request_url": url, "response_url": url}

    with patch.object(base, "_get", side_effect=get):
        result = acquire_bundle(StructureConnector(base), fixture["document_hash"], root)
    item = base.source_system + ":" + fixture["document_hash"]
    identity = IDENTITY if actual else fixture["card"]["adoption"] + ' "' + fixture["card"]["name"] + '"'
    url = fixture["provenance"]["source_url"]
    bundle_path = Path(result["structure_bundle"])
    bundle = json.loads(bundle_path.read_bytes())
    permission = {"schema_version": "processing-permission/1", "decision": "allowed", "scope": "diagnostic",
                  "act_identity": identity, "source_asset_sha256s": [bundle["text_sha256"], bundle["structure_sha256"]],
                  "authorized_by": "synthetic-author", "authorized_at": "2026-10-15T00:00:00Z", "rights_basis": "authored fixture"}
    permission_path = root / "permission.json"
    permission_path.write_bytes(json_bytes(permission))
    manifest = {"schema_version": "corpus-input/2", "kind": "official_consolidated", "archive_root": ".",
                "act_identity_claim": {"declared_identity": identity}, "target_dates": ["2026-10-15"],
                "admission_status": "unresolved", "admission_blockers": ["original_blocker"], "unresolved_questions": [],
                "processing_permission": {"path": "permission.json", "sha256": hashlib.sha256(permission_path.read_bytes()).hexdigest()},
                "structure_bundle": {"path": bundle_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest()},
                "assets": [{"sha256": bundle[field], "source_item": item, "source_url": url, "role": role,
                            "declared_identity": identity, "evidence": {"source_asset_sha256": bundle[field], "source_url": url, "locator": locator}}
                           for field, role, locator in [("text_sha256", "consolidated", "$.redtext" if actual else "$.doctext"),
                                                       ("structure_sha256", "official_structure", "$.data")]]}
    path = root / "input.json"
    write_manifest(path, manifest)
    return path, manifest


def write_manifest(path, manifest):
    manifest["manifest_hash"] = manifest_digest(manifest)
    path.write_bytes(json_bytes(manifest))


def test_numbers_parentage_notes_and_exact_accounting():
    result = tree()
    source = [n for n in result["nodes"] if n.get("source_id")]
    assert [(n["kind"], n["number_canonical"]) for n in source] == [("article", "1"), ("part", "2.1"), ("subitem", "а")]
    assert source[1]["number_display"] == "2¹"
    assert source[2]["parent_address"] == source[1]["address"]
    assert result["accounting"]["exactly_once"]
    assert result["accounting"]["regions_exactly_once"]
    notes = [n for n in result["nodes"] if n["kind"] == "note"]
    assert [n["scope_status"] for n in notes] == ["same_paragraph", "unresolved"]
    assert notes[1]["parent_address"] == "act"
    assert notes[1]["source_container_address"] == source[0]["address"]
    assert len(result["parsed_regions"]) == 2
    assert tree() == result


@pytest.mark.parametrize("case", ["number", "anchor", "prefix", "level", "overlap", "duplicate", "unknown_unit", "zero", "no_number", "row_type"])
def test_invalid_source_structure_cannot_be_silently_accepted(case):
    rows = copy.deepcopy(ROWS)
    if case == "number":
        rows[1]["caption"] = "часть 99"
    elif case == "anchor":
        rows[1]["np"] = "absent"
    elif case == "prefix":
        rows[1]["id"] = "wrong"
    elif case == "level":
        rows[1]["lvl"] = 3
    elif case == "overlap":
        rows[1]["npe"] = "note"
        rows[2]["lvl"] = 1
    elif case == "duplicate":
        rows[1]["id"] = "a1"
    elif case == "unknown_unit":
        rows[1]["unit"] = "неизвестно"
    elif case == "zero":
        rows[1]["caption"] = "часть 0"
    elif case == "no_number":
        rows[1]["caption"] = "часть без номера"
    elif case == "row_type":
        rows[1]["lvl"] = True
    with pytest.raises(ValueError):
        tree(rows=rows)


def test_v2_full_compiler_repeat_preserves_archive(tmp_path):
    root = tmp_path / "archive"
    path, _ = prepare(root)
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    output = tmp_path / "derived"
    first = compile_input(path, "2026-10-15", output)
    second = compile_input(path, "2026-10-15", output)
    assert second == {**first, "result": "unchanged"}
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    draft = json.loads(Path(first["draft"]).read_bytes())
    assert len(draft["content"]["trees"]) == 1
    assert draft["content"]["trees"][0]["schema_version"] == "legal-ast/2"
    assert "original_blocker" in draft["blockers"]
    assert draft["legal_admission"] == "not_requested"


@pytest.mark.parametrize("case", ["permission", "corrupt", "edition", "text_binding", "transport", "response_transport", "v1", "missing_bundle", "bundle_identity_type", "capture_type"])
def test_v2_rejects_bad_binding_before_writes(case, tmp_path):
    root = tmp_path / "archive"
    path, manifest = prepare(root)
    bundle_path = root / manifest["structure_bundle"]["path"]
    bundle = json.loads(bundle_path.read_bytes())
    if case == "permission":
        permission_path = root / "permission.json"
        permission = json.loads(permission_path.read_bytes())
        permission["source_asset_sha256s"].pop()
        permission_path.write_bytes(json_bytes(permission))
        manifest["processing_permission"]["sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest()
    elif case == "corrupt":
        (root / "raw" / bundle["structure_sha256"]).write_bytes(b"broken")
    elif case in {"edition", "text_binding"}:
        if case == "edition":
            bundle["selector"]["edition_id"] += 1
        else:
            bundle["text_sha256"] = "0" * 64
        bundle_path.write_bytes(json_bytes(bundle))
        manifest["structure_bundle"]["sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    elif case in {"transport", "response_transport"}:
        key = "request_url" if case == "transport" else "response_url"
        bundle["transport_evidence"]["structure"][key] = "http://actual.pravo.gov.ru:8000/api/ebpi/getcontent/?bpa=ebpi&rdk=1"
        bundle_path.write_bytes(json_bytes(bundle))
        manifest["structure_bundle"]["sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    elif case == "v1":
        manifest["schema_version"] = "corpus-input/1"
    elif case in {"bundle_identity_type", "capture_type"}:
        if case == "bundle_identity_type":
            bundle["source_item"] = []
        else:
            bundle["transport_evidence"]["structure"] = []
        bundle_path.write_bytes(json_bytes(bundle))
        manifest["structure_bundle"]["sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    else:
        del manifest["structure_bundle"]
    write_manifest(path, manifest)
    with pytest.raises(ValueError):
        compile_input(path, "2026-10-15", tmp_path / "derived")
    assert not (tmp_path / "derived").exists()


@pytest.mark.parametrize("opening,closing", [('"', '"'), ('«', '»')])
def test_quoted_article_is_scoped_to_amending_item(opening, closing):
    replacement = ('<p id="p1">1) дополнить статьей следующего содержания:</p>'
                   f'<p id="q1">{opening}Статья 9.16. Чужая статья</p>'
                   '<p id="q2">1. Первый текст.</p><p id="q3">а) Подпункт.</p>'
                   f'<p id="q4">Продолжение{closing};</p><p id="end">Конец.</p>')
    html = HTML[:HTML.index('<p id="p1">')] + replacement + HTML[HTML.index('<table>'):]
    rows = [dict(ROWS[0]), {"id": "a1_p1", "np": "p1", "npe": "q4", "unit": "пункт", "caption": "пункт 1", "lvl": 1}]
    result = tree(html, rows)
    quote = next(n for n in result["nodes"] if n["kind"] == "quote")
    article = next(n for n in result["nodes"] if n["kind"] == "article" and n.get("number_canonical") == "9.16")
    assert quote["parent_address"].endswith("/item/1")
    assert article["parent_address"] == quote["address"]
    assert any(n["kind"] == "part" and n["parent_address"] == article["address"] for n in result["nodes"])
    assert not result["unresolved_blocks"]
    assert not result["structural_issues"]
    assert result["accounting"]["exactly_once"]


def test_unclosed_quote_never_spills_into_next_source_item():
    html = HTML.replace('<p id="p1">2<sup>1</sup>. Текст.</p>', '<p id="p1">2<sup>1</sup>. В следующей редакции:</p>')
    html = html.replace('а) Первая строка.', '"Статья 9.16. Незакрытая цитата.')
    result = tree(html, ROWS[:2])
    assert "unclosed_or_crossing_amendment_quote" in result["structural_issues"]
    assert any(b["html_id"] == "s1" for b in result["unresolved_blocks"])
    assert not any(n.get("number_canonical") == "9.16" for n in result["nodes"])


def test_form_list_is_not_promoted_to_article_items():
    html = HTML.replace('<p id="p1">2<sup>1</sup>. Текст.</p>', '<p id="p1">Приложение к акту:</p>')
    html = html.replace('а) Первая строка.', 'а) Результаты испытаний;')
    html = html.replace('<p class="A" id="note">', '<p id="letter_b">б) Заключения экспертов.</p><p class="A" id="note">')
    rows = [{"id": "form", "np": "a1", "npe": "end", "unit": "вложение", "caption": "ПРАВИЛА проверки", "lvl": 0},
            {"id": "form_u2", "np": "p1", "npe": "end", "unit": "приложение", "caption": "ПРИЛОЖЕНИЕ № 2. АКТ (форма)", "lvl": 1}]
    html = html.replace('<p id="p1">Приложение к акту:</p>', '<p id="p1">ПРИЛОЖЕНИЕ № 2</p><p>Приложение к акту:</p>')
    result = tree(html, rows)
    items = [n for n in result["nodes"] if n["kind"] == "list_item"]
    assert [n["number_canonical"] for n in items] == ["а", "б"]
    assert all(n["content_context"] == "form" for n in items)
    assert items[0]["parent_address"] == items[1]["parent_address"]
    assert not result["unresolved_blocks"]


def test_form_numeric_items_keep_section_and_continuation_scope():
    html = HTML.replace('<p id="p1">2<sup>1</sup>. Текст.</p>', '<p id="p1">ПРИЛОЖЕНИЕ № 2</p><p class="C">I. Предмет</p><p id="f1">1. Условие.</p>')
    html = html.replace('а) Первая строка.', 'Продолжение условия.')
    html = html.replace('<p id="end">Конец.</p>', '<p id="f2">2. Другое условие.</p><p id="end">Конец.</p>')
    rows = [{"id": "a1", "np": "a1", "npe": "end", "unit": "статья", "caption": "Статья 1", "lvl": 0},
            {"id": "a1_u2", "np": "p1", "npe": "end", "unit": "приложение", "caption": "ПРИЛОЖЕНИЕ № 2 (форма)", "lvl": 1}]
    result = tree(html, rows)
    items = [n for n in result["nodes"] if n["kind"] == "list_item"]
    assert [n["number_canonical"] for n in items] == ["1", "2"]
    section = next(n for n in result["nodes"] if n["kind"] == "form_section")
    assert items[0]["parent_address"].startswith(section["address"] + "/")
    continuation = next(n for n in result["nodes"] if n.get("html_id") == "s1" and n["kind"] == "paragraph")
    assert continuation["parent_address"] == items[0]["address"]


def test_numbered_table_row_keeps_other_cells_with_it():
    html = HTML.replace('<td><p>Ячейка.</p></td>', '<td><p>1. Условие</p></td><td><p>Требование</p></td>')
    result = tree(html)
    row = next(n for n in result["nodes"] if n["kind"] == "table_row_item")
    assert row["number_canonical"] == "1"
    cells = [n for n in result["nodes"] if n["kind"] == "table_cell"]
    assert len(cells) == 2 and all(n["parent_address"] == row["address"] for n in cells)


def test_quote_media_and_inline_note_keep_quoted_part_scope():
    replacement = ('<p id="p1">1) дополнить статьей следующего содержания:</p>'
                   '<p id="q1">«Статья 9.16. Чужая статья</p>'
                   '<p id="q2">1. Текст<img src="x"><span class="mark"> (В редакции закона)</span>»;</p>'
                   '<p id="end">Конец.</p>')
    html = HTML[:HTML.index('<p id="p1">')] + replacement + HTML[HTML.index('<table>'):]
    rows = [dict(ROWS[0]), {"id": "a1_p1", "np": "p1", "npe": "q2", "unit": "пункт", "caption": "пункт 1", "lvl": 1}]
    result = tree(html, rows)
    part = next(n for n in result["nodes"] if n["kind"] == "part")
    image = next(n for n in result["nodes"] if n["kind"] == "image" and n["original_html"] == '<img src="x">')
    note = next(n for n in result["nodes"] if n["kind"] == "note")
    assert image["parent_address"] == part["address"]
    assert note["parent_address"] == part["address"]


def test_quote_closing_paragraph_with_outside_text_is_blocked():
    replacement = ('<p id="p1">1) дополнить статьей следующего содержания:</p>'
                   '<p id="q1">«Статья 9.16. Чужая статья</p>'
                   '<p id="q2">1. Текст». Вне цитаты самостоятельное правило.</p><p id="end">Конец.</p>')
    html = HTML[:HTML.index('<p id="p1">')] + replacement + HTML[HTML.index('<table>'):]
    rows = [dict(ROWS[0]), {"id": "a1_p1", "np": "p1", "npe": "q2", "unit": "пункт", "caption": "пункт 1", "lvl": 1}]
    result = tree(html, rows)
    assert "mixed_paragraph_amendment_quote_boundary" in result["structural_issues"]


def test_marker_outside_all_sidecar_ranges_is_unresolved():
    html = HTML.replace('<p id="end">Конец.</p>', '<p id="end">Конец.</p><p id="a2">Статья 2. Выпавшая статья</p><p>1. Содержание.</p>')
    result = tree(html)
    assert any(b["html_id"] == "a2" for b in result["unresolved_blocks"])


def test_inline_source_anchors_cannot_leave_empty_legal_children():
    html = HTML.replace('<p id="a1">Статья 1. Проверка</p>', '<p id="a1">Статья 1. Проверка <span id="ch1">1. Первая часть.</span><span id="ch2">2. Вторая часть.</span></p>')
    rows = [dict(ROWS[0]), {"id": "a1_ch1", "np": "ch1", "npe": "ch1", "unit": "часть", "caption": "часть 1", "lvl": 1},
            {"id": "a1_ch2", "np": "ch2", "npe": "ch2", "unit": "часть", "caption": "часть 2", "lvl": 1}]
    with pytest.raises(ValueError):
        tree(html, rows)


def test_ips_text_body_must_match_the_transport_selector(tmp_path):
    from legal_rag.corpus.compiler import load_input

    path, manifest = prepare(tmp_path / "archive", "ips")
    root = path.parent
    load_input(path, "2026-10-15")
    asset = manifest["assets"][0]
    old_digest = asset["sha256"]
    body = json.loads((root / "raw" / old_digest).read_bytes())
    body["rdk"] += 1
    payload = json_bytes(body)
    digest = hashlib.sha256(payload).hexdigest()
    (root / "raw" / digest).write_bytes(payload)
    metadata = json.loads((root / "assets" / (old_digest + ".json")).read_bytes())
    metadata.update(sha256=digest, archive_key="raw/" + digest, byte_length=len(payload))
    (root / "assets" / (digest + ".json")).write_bytes(json_bytes(metadata))
    item_path = root / "items" / (hashlib.sha256(asset["source_item"].encode()).hexdigest() + ".json")
    item = json.loads(item_path.read_bytes())
    item["asset_sha256s"].append(digest)
    item_path.write_bytes(json_bytes(item))
    asset["sha256"] = asset["evidence"]["source_asset_sha256"] = digest
    for key, field in (("processing_permission", "source_asset_sha256s"), ("structure_bundle", "text_sha256")):
        record_path = root / manifest[key]["path"]
        record = json.loads(record_path.read_bytes())
        record[field] = [digest, manifest["assets"][1]["sha256"]] if key == "processing_permission" else digest
        record_path.write_bytes(json_bytes(record))
        manifest[key]["sha256"] = hashlib.sha256(record_path.read_bytes()).hexdigest()
    write_manifest(path, manifest)
    with pytest.raises(ValueError, match="text body edition mismatch"):
        compile_input(path, "2026-10-15", tmp_path / "derived")
    assert not (tmp_path / "derived").exists()


@pytest.mark.parametrize("response", [[], "invalid", 7])
def test_invalid_sidecar_root_is_a_controlled_failure(response):
    with pytest.raises(ValueError):
        tree(response=response)


def test_two_provision_markers_in_one_paragraph_stay_unresolved():
    html = HTML.replace('2<sup>1</sup>. Текст.', '2<sup>1</sup>. Текст.<br>3. Выпавшая часть.')
    result = tree(html)
    assert any(b["html_id"] == "p1" for b in result["unresolved_blocks"])
