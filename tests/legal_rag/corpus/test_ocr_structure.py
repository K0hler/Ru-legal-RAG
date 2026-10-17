"""Authored OCR controls: legal scopes must survive physical page boundaries."""

import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from legal_rag.corpus.pdf_extraction import normalize_dotsmocr, pdf_tree  # noqa: E402
from legal_rag.corpus import ocr_structure  # noqa: E402


ISSUER = "Главного государственного санитарного врача Российской Федерации"
CLAIM = f'Постановление {ISSUER} от 09.06.2020 № 812 "Об учебных правилах"'


def extraction(body=None, reference="¹", government=False):
    issuer = "Правительства Российской Федерации" if government else ISSUER
    header = "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ\nПОСТАНОВЛЕНИЕ" if government else "ГЛАВНЫЙ ГОСУДАРСТВЕННЫЙ САНИТАРНЫЙ ВРАЧ\nРОССИЙСКОЙ ФЕДЕРАЦИИ\nПОСТАНОВЛЕНИЕ"
    layouts = [[
        ("Title", header),
        ("Picture", "09.06.2020"), ("Text", "№ 812"), ("Text", "Об учебных правилах"),
        ("Text", "1. Утвердить прилагаемые правила."),
        ("Text", f"УТВЕРЖДЕНЫ\nпостановлением {issuer}\nот 9 июня 2020 г. № 812"),
        ("Title", "Санитарные правила СП 9.9.9999-20"),
        ("Section-header", "## I. Общие положения"),
        ("Text", f"1. Первое правило{reference}."),
    ], [("Page-header", "2"), ("Text", "Продолжение первого правила."),
        ("Footnote", "¹ Источник правила."), ("Text", "2. Табличное правило."),
        ("Table", '<table><tr><td rowspan="2">1. Это ячейка</td><td>+</td></tr><tr><td></td></tr></table>'),
        ("Text", "ПРИЛОЖЕНИЕ № 1\nк СП 9.9.9999-20"), ("Title", "Показатели"),
        ("Text", "1. Правило приложения."), ("Picture", "1. ПУНКТ НА ПЕЧАТИ")]]
    if body is not None:
        layouts = [layouts[0][:4] + [("Text", text) for text in body]]
    pages = []
    for index, layout in enumerate(layouts):
        pages.append({"page_number": index + 1, "image_size": [1000, 2000],
                      "native": {"choices": [{"finish_reason": "stop", "message": {"content": "retained authored layout"}}]},
                      "layout": [{"category": kind, "text": text, "bbox": [10, 10 + n * 100, 900, 90 + n * 100]}
                                 for n, (kind, text) in enumerate(layout)]})
    digest = "a" * 64
    run = {"engine": "dotsmocr", "status": "complete", "source_sha256": digest,
           "source_pages": len(pages), "requested_pages": list(range(1, len(pages) + 1)),
           "completed_pages": list(range(1, len(pages) + 1)),
           "model": {"repo": "dots-studio/dots.mocr", "revision": "authored", "weights_sha256": {"authored": "b" * 64}}}
    return normalize_dotsmocr({"pages": pages}, run, digest)


def test_cross_page_approved_annex_scopes_and_exact_accounting():
    source = extraction()
    tree = pdf_tree(source, CLAIM, "original")
    assert tree["schema_version"] == "legal-ast/2"
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    nodes = {node["address"]: node for node in tree["nodes"]}
    assert nodes["act/point/1"]["parent_address"] == "act"
    assert nodes["act/approved/1/point/1"]["parent_address"] == "act/approved/1/section/I"
    continuation = next(node for node in tree["nodes"] if node["text"] == "Продолжение первого правила.")
    assert continuation["parent_address"] == "act/approved/1/point/1"
    assert nodes["act/approved/1/annex/1"]["parent_address"] == "act/approved/1"
    assert nodes["act/approved/1/annex/1/point/1"]["parent_address"] == "act/approved/1/annex/1"
    assert tree["accounting"]["exactly_once"]
    tokens = {token["text_node_id"]: token for token in source["text_nodes"]}
    for entry in [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]:
        assert entry["original_text"] == "".join(tokens[i]["raw_text"] for i in entry["text_node_ids"])
    assert tree["document_tree"] == source["document_tree"]
    assert "pdf_structure_unqualified" in tree["structural_issues"]


def test_table_and_footnote_ownership_and_seal_noise():
    tree = pdf_tree(extraction(), CLAIM, "original")
    table, = [node for node in tree["nodes"] if node["kind"] == "table"]
    assert table["parent_address"] == "act/approved/1/point/2"
    assert table["table_cells"][-1]["text"] == ""
    assert table["table_cells"][0]["rowspan"] == 2
    footnote, = [node for node in tree["nodes"] if node["kind"] == "footnote"]
    assert footnote["parent_address"] == "act/approved/1/point/1"
    seal = next(entry for entry in tree["nodes"] if entry["text"] == "1. ПУНКТ НА ПЕЧАТИ")
    assert seal["kind"] == "image"


def test_engine_neutral_input_and_heading_category_variation():
    source = extraction()
    other = copy.deepcopy(source)
    other["models"] = [{"provider": "different-authored-provider"}]
    other["runtime_fingerprint"] = "c" * 64
    for page in other["pages"]:
        for region in page["regions"]:
            region.pop("source_record")
            if region["category"] in {"Title", "Section-header"}:
                region["category"] = "Text"
    first = pdf_tree(source, CLAIM, "original")
    second = pdf_tree(other, CLAIM, "original")
    def relationships(tree):
        return [(n["kind"], n["address"], n["parent_address"]) for n in tree["nodes"]]
    assert relationships(first)
    assert relationships(first) == relationships(second)
    assert source == extraction()


def test_quoted_foreign_numbering_keeps_its_own_scope():
    source = extraction(["1. Пункт 7 изложить в следующей редакции:",
                         "«7. Чужой пункт:", "а) Чужой подпункт.»;", "2. Собственный пункт."])
    tree = pdf_tree(source, CLAIM, "amendment")
    prefix = "amendment/" + "a" * 64
    nodes = {node["address"]: node for node in tree["nodes"]}
    assert nodes[prefix + "/point/1/quote/1/point/7/subitem/а"]["parent_address"] == prefix + "/point/1/quote/1/point/7"
    assert nodes[prefix + "/point/2"]["parent_address"] == prefix


@pytest.mark.parametrize("body,reason", [
    (["1. Первый.", "1. Повторный."], "duplicate_address"),
    (["1. Первый.", "1.. Нечёткий номер."], "unknown_numbering"),
    (["1. Первый.", "ПРИЛОЖЕНИЕ № 1 к неизвестному тексту", "2. Нельзя присоединить."], "annex_target_unresolved"),
])
def test_ambiguous_or_missing_scopes_stay_unresolved(body, reason):
    tree = pdf_tree(extraction(body), CLAIM, "original")
    assert reason in {entry["reason"] for entry in tree["unresolved_blocks"]}


def test_wrong_source_identity_cannot_inherit_claim_number():
    tree = pdf_tree(extraction(), CLAIM.replace("812", "813"), "original")
    assert tree["identity_decision"]["status"] == "unresolved"
    assert not any(node["kind"] == "point" for node in tree["nodes"])


def test_unknown_section_blocks_its_scope_and_recovers_at_next_explicit_section():
    source = extraction(["1. Утвердить правила.",
                         "УТВЕРЖДЕНЫ постановлением Главного государственного санитарного врача Российской Федерации от 9 июня 2020 г. № 812",
                         "Санитарные правила СП 9.9.9999-20", "I. Первый раздел", "1. Первое правило.",
                         "Х. Неоднозначный номер", "2. Неустановленная принадлежность.",
                         "XI. Проверенный следующий раздел", "3. Следующее правило."])
    tree = pdf_tree(source, CLAIM, "original")
    assert any(b["reason"] == "unknown_heading" for b in tree["unresolved_blocks"])
    assert not any(n.get("number_canonical") == "2" and n["kind"] == "point" for n in tree["nodes"])
    third = next(n for n in tree["nodes"] if n["kind"] == "point" and n.get("number_canonical") == "3")
    assert third["parent_address"] == "act/approved/1/section/XI"


@pytest.mark.parametrize("fault", ["parent", "text", "dropped_text", "dropped_region", "source_span", "table_cells", "region_owner", "children", "normative_text", "canonical_number"])
def test_corrupt_tree_cannot_pass_source_validation(fault):
    source = extraction()
    tree = pdf_tree(source, CLAIM, "original")
    if fault == "parent":
        next(n for n in tree["nodes"] if n["kind"] == "point")["parent_address"] = "act/missing"
    elif fault == "text":
        tree["nodes"][0]["original_text"] = "Invented text"
    elif fault == "dropped_text":
        tree["nodes"].pop()
    elif fault == "dropped_region":
        tree["region_bindings"].pop()
    elif fault == "source_span":
        tree["nodes"][0]["source_span"]["bbox"] = [0, 0, 1, 1]
    elif fault == "table_cells":
        next(n for n in tree["nodes"] if n["kind"] == "table")["table_cells"][0]["text"] = "Changed cell"
    elif fault == "region_owner":
        tree["region_bindings"][0]["address"] = "act/point/1"
    elif fault == "normative_text":
        next(n for n in tree["nodes"] if n["kind"] == "point")["text"] = "1. Invented norm."
    elif fault == "canonical_number":
        next(n for n in tree["nodes"] if n["kind"] == "point")["number_canonical"] = "999"
    else:
        next(n for n in tree["nodes"] if n["kind"] == "point")["children"].append("act/missing")
    with pytest.raises(ValueError):
        ocr_structure.validate_ocr_tree(source, tree)


def test_unnumbered_amendment_annex_binds_to_its_own_approving_act():
    source = extraction(["1. Внести изменения.",
                         "ПРИЛОЖЕНИЕ к постановлению Главного государственного санитарного врача Российской Федерации от 9 июня 2020 г. № 812",
                         "Изменения в учебных правилах", "1. Изменить правило."])
    tree = pdf_tree(source, CLAIM, "amendment")
    annex, = [node for node in tree["nodes"] if node["kind"] == "annex"]
    assert annex["parent_address"] == "amendment/" + "a" * 64
    assert annex["number_canonical"] is None and not annex["number_is_explicit"]
    assert next(n for n in tree["nodes"] if n["text"] == "1. Изменить правило.")["parent_address"] == annex["address"]


def test_footnote_one_cannot_bind_to_reference_twelve():
    source = extraction(reference="¹²")
    tree = pdf_tree(source, CLAIM, "original")
    note = next(n for n in tree["nodes"] if n["kind"] == "footnote")
    assert note["scope_status"] == "unresolved"
    assert note["parent_address"] == "act"


def test_candidate_mutation_cannot_modify_the_saved_extraction():
    source = extraction()
    before = copy.deepcopy(source)
    tree = pdf_tree(source, CLAIM, "original")
    next(n for n in tree["nodes"] if n["kind"] == "table")["table_cells"][0]["text"] = "Mutated"
    tree["nodes"][0]["source_span"]["bbox"][0] = 0
    tree["document_tree"]["children"].clear()
    assert source == before


def test_decimal_subpoints_require_their_explicit_parent():
    source = extraction(["1. Первый пункт.", "1.1. Подпункт.", "Продолжение подпункта.",
                         "1.2. Следующий подпункт.", "3.1. Родитель отсутствует."])
    tree = pdf_tree(source, CLAIM, "original")
    nodes = {node["address"]: node for node in tree["nodes"]}
    assert nodes["act/point/1/subitem/1.1"]["parent_address"] == "act/point/1"
    assert nodes["act/point/1/subitem/1.2"]["parent_address"] == "act/point/1"
    assert next(n for n in tree["nodes"] if n["text"] == "Продолжение подпункта.")["parent_address"] == "act/point/1/subitem/1.1"
    assert "decimal_parent_unresolved" in {b["reason"] for b in tree["unresolved_blocks"]}


def test_government_ocr_uses_the_same_shared_scope_rules():
    source = extraction(government=True)
    claim = CLAIM.replace(ISSUER, "Правительства Российской Федерации")
    tree = pdf_tree(source, claim, "original")
    assert tree["identity_decision"]["family"] == "government_resolution"
    assert tree["identity_decision"]["status"] == "claim_matches_header"
    assert next(n for n in tree["nodes"] if n["kind"] == "annex")["parent_address"] == "act/approved/1"


def test_numeric_approval_date_and_split_title_keep_one_scope():
    source = extraction(["1. Утвердить правила.",
                         "УТВЕРЖДЕНЫ постановлением Главного государственного санитарного врача Российской Федерации от 09.06.2020 г. № 812",
                         "СП 9.9.9999-20", "Санитарные правила учебного учета",
                         "I. Первый раздел", "1. Правило."])
    tree = pdf_tree(source, CLAIM, "original")
    assert not tree["unresolved_blocks"]
    node = next(n for n in tree["nodes"] if n["kind"] == "approved_text")
    assert node["title"] == "СП 9.9.9999-20 Санитарные правила учебного учета"
    assert next(n for n in tree["nodes"] if n["text"] == "1. Правило.")["parent_address"] == "act/approved/1/section/I"


def test_decimal_section_prefix_and_literal_missing_terminal_dot():
    source = extraction(["1. Утвердить правила.",
                         "УТВЕРЖДЕНЫ постановлением Главного государственного санитарного врача Российской Федерации от 9 июня 2020 г. № 812",
                         "Санитарные правила СП 9.9.9999-20", "II. Второй раздел",
                         "2.1. Первое правило.", "2.2 Следующее правило.",
                         "III. Третий раздел", "2.3. Неверный префикс."])
    tree = pdf_tree(source, CLAIM, "original")
    first = next(n for n in tree["nodes"] if n.get("number_canonical") == "2.1")
    second = next(n for n in tree["nodes"] if n.get("number_canonical") == "2.2")
    assert first["parent_address"] == second["parent_address"] == "act/approved/1/section/II"
    assert second["text"] == "2.2 Следующее правило."
    assert "decimal_parent_unresolved" in {b["reason"] for b in tree["unresolved_blocks"]}


def test_approval_stamp_split_into_distinct_physical_regions():
    source = extraction(["1. Утвердить правила.", "УТВЕРЖДЕНЫ",
                         "постановлением Главного государственного санитарного врача Российской Федерации от 9 июня 2020 г. № 812",
                         "ПРАВИЛА", "учебного учета", "I. Первый раздел", "1. Правило."])
    tree = pdf_tree(source, CLAIM, "original")
    assert not tree["unresolved_blocks"]
    approved = next(n for n in tree["nodes"] if n["kind"] == "approved_text")
    assert approved["title"] == "ПРАВИЛА учебного учета"
    assert len(approved["approval_evidence_block_ids"]) == 2
    assert next(n for n in tree["nodes"] if n["text"] == "1. Правило.")["parent_address"] == "act/approved/1/section/I"


def test_table_cannot_be_reassigned_to_an_earlier_sibling_point():
    source = extraction()
    tree = pdf_tree(source, CLAIM, "original")
    nodes = {n["address"]: n for n in tree["nodes"]}
    table = next(n for n in tree["nodes"] if n["kind"] == "table")
    old = nodes[table["parent_address"]]
    new = nodes["act/approved/1/point/1"]
    old["children"].remove(table["address"])
    new["children"].append(table["address"])
    table["parent_address"] = new["address"]
    with pytest.raises(ValueError):
        ocr_structure.validate_ocr_tree(source, tree)
