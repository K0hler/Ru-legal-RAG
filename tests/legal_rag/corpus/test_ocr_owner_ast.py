"""The maintained owner parser reaches PDF compilation without losing source evidence."""
import copy
import importlib.util
import json
from pathlib import Path
from collections import Counter

import pytest

from test_ocr_structure import extraction, CLAIM
from legal_rag.corpus.compiler import compile_input
from legal_rag.corpus import ocr_runtime


def adapter():
    from legal_rag.corpus import ocr_owner_ast
    return ocr_owner_ast


def prototype():
    path = Path(__file__).resolve().parents[3] / "docs/assets/ocr_logical_structure.py"
    spec = importlib.util.spec_from_file_location("retained_owner_prototype", path)
    import sys
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compile_pdf_uses_the_maintained_owner_parser_and_keeps_blockers(tmp_path):
    from test_ocr_runtime import OcrRuntimeTest
    path, mapping, output, _ = OcrRuntimeTest().prepare(tmp_path)
    saved = ocr_runtime.extract_input(path, output, results_path=mapping)
    result = compile_input(path, "2025-01-01", output / "compiled", extraction_index=Path(saved["index"]))
    tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
    assert tree["parser_version"].startswith("ocr-owner-ast/")
    assert tree["identity_decision"]["status"] == "unresolved"
    assert tree["nodes"] and "identity_unresolved" in result["blockers"]
    assert tree["edition_admission"] is False
    assert "pdf_structure_unqualified" in result["blockers"] or "pdf_structure_unqualified" in tree["structural_issues"]
    assert "ocr_review_required" in result["blockers"]
    assert compile_input(path, "2025-01-01", output / "compiled", extraction_index=Path(saved["index"]))["result"] == "unchanged"
    again = compile_input(path, "2025-01-01", output / "separate", extraction_index=Path(saved["index"]))
    assert again["draft_id"] == result["draft_id"]


def test_owner_ast_preserves_prototype_owners_text_tables_and_physical_regions():
    source = extraction()
    before = copy.deepcopy(source)
    expected = prototype().build(source)
    tree = adapter().build_owner_tree(source, CLAIM, "original")
    assert source == before
    assert tree["schema_version"] == "legal-ast/2"
    assert tree["document_tree"] == source["document_tree"]
    point = next(n for n in tree["nodes"] if n["address"] == "act/owner/S/I/1")
    region = next(r for p in source["pages"] for r in p["regions"] if r["region_id"] == point["anchor_region_ids"][0])
    assert region["category"] == "Text"
    assert point["anchor_source_spans"]
    assert {r["region_id"]: r["owner_path"] for r in tree["region_bindings"]} == {
        r["region_id"]: r["owner"] for r in expected["regions"]}
    entries = [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]
    assert Counter(i for n in entries for i in n["text_node_ids"]) == Counter(t["text_node_id"] for t in source["text_nodes"])
    tokens = {t["text_node_id"]: t for t in source["text_nodes"]}
    for entry in entries:
        assert entry["original_text"] == "".join(tokens[i]["raw_text"] for i in entry["text_node_ids"])
        assert entry["source_spans"] == [tokens[i]["source_span"] for i in entry["text_node_ids"]]
    table, = [n for n in tree["nodes"] if n["kind"] == "table"]
    original = next(r for p in source["pages"] for r in p["regions"] if r["category"] == "Table")
    assert table["table_topology"] == original["table"]
    table["table_topology"]["cells"][0]["text"] = "changed returned data"
    assert source == before


@pytest.mark.parametrize("caption", ["Приложение № 7\nк СП 9.9.9999-20",
                                     "Приложение 7\nк СП 9.9.9999-20",
                                     "Приложение\n№ 7\nк СП 9.9.9999-20"])
def test_printed_annex_number_is_source_bound_metadata(caption):
    from test_ocr_structure import ISSUER
    source = extraction(["1. Утвердить прилагаемые правила.",
        f"УТВЕРЖДЕНЫ\nпостановлением {ISSUER}\nот 9 июня 2020 г. № 812",
        ("Title", "Санитарные правила СП 9.9.9999-20"), caption,
        ("Title", "Показатели"), "1. Правило приложения."])
    before = copy.deepcopy(source)
    tree = adapter().build_owner_tree(source, CLAIM, "original")
    annex = next(n for n in tree["nodes"] if n["owner_path"] == "S/AN7" and not n.get("source_region_ids"))
    assert annex["number_canonical"] == annex["number_display"] == "7"
    assert annex["number_components"] == {"base": "7", "superscript": None}
    assert annex["number_is_explicit"] and annex["marker_label"] == "7"
    assert annex["anchor_region_ids"] and annex["anchor_source_spans"]
    assert source == before
    annex["number_canonical"] = "8"
    with pytest.raises(ValueError):
        adapter().validate_owner_tree(source, tree)


def test_unnumbered_annex_does_not_take_number_from_its_reference():
    from test_ocr_structure import ISSUER
    source = extraction(["1. Утвердить прилагаемые правила.",
        f"УТВЕРЖДЕНЫ\nпостановлением {ISSUER}\nот 9 июня 2020 г. № 812",
        ("Title", "Санитарные правила СП 9.9.9999-20"), "Приложение\nк СП 9.9.9999-20",
        ("Title", "Изменения"), "1. Новое правило."])
    tree = adapter().build_owner_tree(source, CLAIM, "original")
    annex = next(n for n in tree["nodes"] if n["kind"] == "annex" and not n.get("source_region_ids"))
    assert annex["number_canonical"] is annex["number_display"] is annex["number_components"] is None
    assert annex["number_is_explicit"] is False


def test_unconfirmed_identity_keeps_structure_but_unbound_footnote_stays_unresolved():
    source = extraction(["1. Правило.", ("Footnote", "² Сноска без знака в тексте.")])
    tree = adapter().build_owner_tree(source, "Другой акт", "original")
    assert tree["identity_decision"]["status"] == "unresolved"
    assert any(n["text"] == "1. Правило." for n in tree["nodes"])
    assert tree["edition_admission"] is False
    assert all(n["legal_status"] == "unverified" for n in tree["nodes"])
    assert tree["unresolved_blocks"]
    assert any(e["original_text"] == "² Сноска без знака в тексте." for e in tree["unresolved_blocks"])
    assert "pdf_structure_unqualified" in tree["structural_issues"]


@pytest.mark.parametrize("damage", ["text", "span", "owner", "table", "region", "parent", "number",
                                    "exclusion", "container_parent", "accounting", "binding_page", "anchor", "table_kind"])
def test_owner_ast_validator_rejects_corrupted_conversion(damage):
    source = extraction()
    tree = adapter().build_owner_tree(source, CLAIM, "original")
    leaf = next(n for n in tree["nodes"] if n["text_node_ids"])
    if damage == "text":
        leaf["original_text"] += "lost provenance"
    elif damage == "span":
        leaf["source_spans"][0]["locator"] = "foreign source"
    elif damage == "owner":
        tree["region_bindings"][0]["owner_path"] = "S/999"
    elif damage == "table":
        next(n for n in tree["nodes"] if n["kind"] == "table")["table_topology"]["cells"].clear()
    elif damage == "region":
        tree["region_bindings"].pop()
    elif damage == "parent":
        leaf["parent_address"] = "foreign/document"
    elif damage == "number":
        next(n for n in tree["nodes"] if n.get("number_is_explicit"))["number_canonical"] = "999"
    elif damage == "container_parent":
        node = next(n for n in tree["nodes"] if n.get("owner_path") == "S/I" and not n["text_node_ids"])
        node["parent_address"] = "act/owner/A"
        for n in tree["nodes"]:
            n["children"] = [c["address"] for c in tree["nodes"] if c["parent_address"] == n["address"]]
    elif damage == "accounting":
        tree["accounting"]["parsed_text_nodes"] = 0
    elif damage == "binding_page":
        tree["region_bindings"][0]["page"] = 999
    elif damage == "anchor":
        next(n for n in tree["nodes"] if n.get("number_is_explicit"))["anchor_source_spans"] = []
    elif damage == "table_kind":
        table = next(n for n in tree["nodes"] if n["kind"] == "table")
        table["kind"] = "text"
        del table["table_topology"], table["table_cells"]
    else:
        tree["nodes"].remove(leaf)
        leaf["address"] = None
        tree["excluded_blocks"].append(leaf)
        for n in tree["nodes"]:
            n["children"] = [c["address"] for c in tree["nodes"] if c["parent_address"] == n["address"]]
        for b in tree["region_bindings"]:
            if b["region_id"] in leaf["source_region_ids"]:
                b["address"] = None
                b["disposition"] = "excluded"
    with pytest.raises(ValueError):
        adapter().validate_owner_tree(source, tree)


def test_page_continuation_view_separates_words_and_keeps_raw_fragments():
    from test_pdf_extraction import saved_result
    from legal_rag.corpus.pdf_extraction import normalize_dotsmocr
    document, run = saved_result()
    for page in document["pages"]:
        page["image_size"] = [1000, 2000]
    document["pages"][0]["layout"] = [{"category": "Text", "text": "1. Information about", "bbox": [0, 0, 400, 40]}]
    document["pages"][1]["layout"] = [{"category": "Text", "text": "service is provided here.", "bbox": [0, 0, 400, 40]}]
    source = normalize_dotsmocr(document, run, run["source_sha256"])
    tree = adapter().build_owner_tree(source, None, "original")
    entry, = [e for e in [*tree["nodes"], *tree["unresolved_blocks"]] if e["text_node_ids"]]
    assert entry["original_text"] == "1. Information aboutservice is provided here."
    assert entry["text"] == "1. Information about service is provided here."
    assert len(entry["fragments"]) == 2 and len(entry["source_spans"]) >= 2


@pytest.mark.parametrize("heading,kind", [("РАЗДЕЛ I. Общие положения", "section"),
                                         ("ЧАСТЬ ПЕРВАЯ. Общие положения", "part"),
                                         ("Подраздел I. Общие положения", "subsection"),
                                         ("§ 1. Общие положения", "subchapter")])
def test_explicit_named_units_keep_their_legal_kind(heading, kind):
    tree = adapter().build_owner_tree(extraction(["1. Утвердить правила.", ("Section-header", heading),
                                                "Статья 1. Общие положения", "1. Правило."]), CLAIM, "original")
    assert any(n["kind"] == kind and n.get("number_is_explicit") for n in tree["nodes"])


def test_dash_items_do_not_replace_the_point_marker_and_repeated_numbers_are_visible():
    tree = adapter().build_owner_tree(extraction(["1. Перечень:", "- первый элемент;", "- второй элемент."]), CLAIM, "original")
    point = next(n for n in tree["nodes"] if n["address"] == "act/owner/A/1")
    assert point["kind"] == "point" and point["number_canonical"] == "1"
    tree = adapter().build_owner_tree(extraction(["1. Пункт акта.", ("Section-header", "Статья 1. Первая статья"),
                                                ("Section-header", "Статья 1. Повторенный заголовок")]), CLAIM, "original")
    assert any(w['code'] == 'duplicate_printed_number' for w in tree['source_warnings'])
    articles = [n for n in tree['nodes'] if n['kind'] == 'article']
    assert len(articles) == 2 and len({n['address'] for n in articles}) == 2
    assert all(n['number_display'] == '1' for n in articles)


def test_current_owner_export_uses_the_compiler_route():
    from test_ocr_logical_structure import load_script
    exporter = load_script("export_owner_maps")
    owners, meta = exporter.export_current(extraction(), CLAIM, "original")
    assert meta["parser_version"].startswith("ocr-owner-ast/")
    assert owners["1.8"] == "S/I/1"


def test_inserted_article_number_uses_the_existing_ast_number_contract():
    tree = adapter().build_owner_tree(extraction(["1. Пункт акта.", ("Section-header", "Статья 2¹. Правило"),
                                                "1. Текст части."]), CLAIM, "original")
    article = next(n for n in tree["nodes"] if n["kind"] == "article")
    assert article["number_canonical"] == "2.1"
    assert article["number_display"] == "2¹"
    assert article["number_components"] == {"base": "2", "superscript": "1"}


def test_report_keeps_a_multiregion_paragraph_in_source_order():
    from legal_rag.corpus.compiler import _report
    from test_pdf_extraction import saved_result
    from legal_rag.corpus.pdf_extraction import normalize_dotsmocr
    document, run = saved_result()
    for page in document["pages"]:
        page["image_size"] = [1000, 2000]
    document["pages"][0]["layout"] = [
        {"category": "Text", "text": "1. First rule.", "bbox": [0, 0, 400, 40]},
        {"category": "Text", "text": "2. Information about", "bbox": [0, 1800, 400, 1840]}]
    document["pages"][1]["layout"] = [
        {"category": "Text", "text": "service is provided here.", "bbox": [0, 0, 400, 40]}]
    tree = adapter().build_owner_tree(normalize_dotsmocr(document, run, run["source_sha256"]), None, "original")
    paragraph = next(n for n in tree["nodes"] if n["text"].startswith("2. Information"))
    assert len(paragraph["source_region_ids"]) == 2 and paragraph["source_span"] is None
    manifest = {"assets": [{"sha256": tree["source_asset_sha256"], "source_url": "https://example.test/source",
                            "evidence": {"locator": "authored"}}],
                "act_identity_claim": {"declared_identity": CLAIM}, "kind": "authored",
                "source_statuses": [], "unresolved_questions": [], "processing_permission": {}}
    draft = {"content": {"trees": [tree]}, "blockers": [], "target_date": "2025-01-01",
             "admission_status": "diagnostic", "draft_id": "authored", "input_hash": "authored", "content_hash": "authored"}
    html = _report(manifest, draft)
    assert html.index("<pre>1. First rule.") < html.index("<pre>" + paragraph["text"])
    assert all(span["locator"] in html for span in paragraph["source_spans"])
