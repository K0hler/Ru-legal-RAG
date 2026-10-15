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


def tree(html=HTML, rows=None):
    payload = json_bytes({"redtext": html})
    asset = {"sha256": hashlib.sha256(payload).hexdigest(), "evidence": {"locator": "$.redtext"},
             "declared_identity": IDENTITY, "role": "consolidated"}
    extraction = extract_native(asset, payload)
    sidecar = json_bytes({"status": 0, "complete": True, "data": ROWS if rows is None else rows})
    return build_official_tree(asset, extraction, html, sidecar, hashlib.sha256(sidecar).hexdigest(), "actual.pravo.gov.ru")


def prepare(root):
    fixture = json.loads((Path(__file__).parent.parent / "sources/fixtures/actual_pravo_59_fz.json").read_bytes())
    fixture["redtext"] = {"redtext": HTML, "error": None}
    bodies = [json_bytes(fixture[k]) for k in ("card", "redactions", "redtext")]
    bodies.append(json_bytes({"status": 0, "complete": True, "data": ROWS}))
    base = ActualPravoConnector()
    calls = []

    def get(url):
        calls.append(url)
        return bodies[len(calls) - 1], {"request_url": url, "response_url": url}

    with patch.object(base, "_get", side_effect=get):
        result = acquire_bundle(StructureConnector(base), fixture["document_hash"], root)
    item = "actual.pravo.gov.ru:" + fixture["document_hash"]
    url = fixture["provenance"]["source_url"]
    bundle_path = Path(result["structure_bundle"])
    bundle = json.loads(bundle_path.read_bytes())
    permission = {"schema_version": "processing-permission/1", "decision": "allowed", "scope": "diagnostic",
                  "act_identity": IDENTITY, "source_asset_sha256s": [bundle["text_sha256"], bundle["structure_sha256"]],
                  "authorized_by": "synthetic-author", "authorized_at": "2026-10-15T00:00:00Z", "rights_basis": "authored fixture"}
    permission_path = root / "permission.json"
    permission_path.write_bytes(json_bytes(permission))
    manifest = {"schema_version": "corpus-input/2", "kind": "official_consolidated", "archive_root": ".",
                "act_identity_claim": {"declared_identity": IDENTITY}, "target_dates": ["2026-10-15"],
                "admission_status": "unresolved", "admission_blockers": ["original_blocker"], "unresolved_questions": [],
                "processing_permission": {"path": "permission.json", "sha256": hashlib.sha256(permission_path.read_bytes()).hexdigest()},
                "structure_bundle": {"path": bundle_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest()},
                "assets": [{"sha256": bundle[field], "source_item": item, "source_url": url, "role": role,
                            "declared_identity": IDENTITY, "evidence": {"source_asset_sha256": bundle[field], "source_url": url, "locator": locator}}
                           for field, role, locator in [("text_sha256", "consolidated", "$.redtext"),
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


@pytest.mark.parametrize("case", ["permission", "corrupt", "edition", "text_binding", "transport", "v1", "missing_bundle"])
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
    elif case == "transport":
        metadata_path = root / "assets" / (bundle["structure_sha256"] + ".json")
        metadata = json.loads(metadata_path.read_bytes())
        metadata["transport_metadata"]["request_url"] = "http://actual.pravo.gov.ru:8000/api/ebpi/getcontent/?bpa=ebpi&rdk=1"
        metadata_path.write_bytes(json_bytes(metadata))
    elif case == "v1":
        manifest["schema_version"] = "corpus-input/1"
    else:
        del manifest["structure_bundle"]
    write_manifest(path, manifest)
    with pytest.raises(ValueError):
        compile_input(path, "2026-10-15", tmp_path / "derived")
    assert not (tmp_path / "derived").exists()
