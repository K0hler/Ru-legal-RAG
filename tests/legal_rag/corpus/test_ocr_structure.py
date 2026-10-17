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
        layouts = [layouts[0][:4] + [text if isinstance(text, tuple) else ("Text", text) for text in body]]
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


@pytest.mark.parametrize("category", ["Picture", "Page-header", "Page-footer", "Footnote"])
def test_physical_metadata_cannot_open_or_close_an_amendment_quote(category):
    source = extraction(["1. Изменить правило.", (category, "«7. ПЕЧАТЬ"),
                         "2. Пункт изложить в следующей редакции:", "«7. Чужой пункт.",
                         (category, "ПЕЧАТЬ»"), "Продолжение чужого пункта.»;", "3. Собственный пункт."])
    tree = pdf_tree(source, CLAIM, "amendment")
    prefix = "amendment/" + "a" * 64
    nodes = {node["address"]: node for node in tree["nodes"]}
    assert nodes[prefix + "/point/2"]["parent_address"] == prefix
    assert nodes[prefix + "/point/3"]["parent_address"] == prefix
    continuation = next(n for n in tree["nodes"] if n["text"] == "Продолжение чужого пункта.»;")
    assert continuation["parent_address"] == prefix + "/point/2/quote/1/point/7"
    assert "unclosed_amendment_quote" not in tree["structural_issues"]


def test_multiple_exact_footnote_references_keep_ownership_unresolved():
    source = extraction(["1. Первое правило¹.", "2. Второе правило¹.", ("Footnote", "¹ Примечание.")])
    tree = pdf_tree(source, CLAIM, "original")
    assert "footnote_scope_ambiguous" in tree["structural_issues"]
    note = next(b for b in tree["unresolved_blocks"] if b["text"] == "¹ Примечание.")
    assert note["reason"] == "footnote_scope_ambiguous"
    assert note["candidate_parent_addresses"] == ["act/point/1", "act/point/2"]


def test_confirmed_independent_scope_recovers_from_unknown_section():
    source = extraction(["1. Начало.", "Х. Неизвестный раздел",
                         f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812",
                         "Санитарные правила СП 9.9.9999-20", "1. Новое правило.",
                         "Х. Ещё неизвестный раздел", "ПРИЛОЖЕНИЕ № 1 к СП 9.9.9999-20",
                         ("Title", "Форма"), "1. Правило приложения."])
    tree = pdf_tree(source, CLAIM, "original")
    nodes = {node["address"]: node for node in tree["nodes"]}
    assert nodes["act/approved/1/point/1"]["parent_address"] == "act/approved/1"
    assert nodes["act/approved/1/annex/1/point/1"]["parent_address"] == "act/approved/1/annex/1"


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


@pytest.mark.parametrize("government", [False, True])
@pytest.mark.parametrize("category", ["Text", "Page-header", "Page-footer"])
@pytest.mark.parametrize("split", [False, True])
def test_explicit_attachment_scope_is_independent_of_ocr_tag_and_fragmentation(government, category, split):
    issuer = "Правительства Российской Федерации" if government else ISSUER
    body = ["1. Утвердить правила.",
            f"УТВЕРЖДЕНЫ постановлением {issuer} от 9 июня 2020 г. № 812",
            ("Title", "Санитарные правила СП 9.9.9999-20"), "1. Правило утверждённого текста."]
    body += ([(category, "ПРИЛОЖЕНИЕ № 7"), (category, "к СП 9.9.9999-20")] if split else
             [(category, "ПРИЛОЖЕНИЕ № 7 к СП 9.9.9999-20")])
    body += [("Title", "Условия учёта"), "1. Правило приложения.",
             ("Table", "<table><tr><td>Допуск</td><td>не более 5</td></tr></table>")]
    source = extraction(body, government=government)
    saved = copy.deepcopy(source)
    tree = pdf_tree(source, CLAIM.replace(ISSUER, issuer), "original")
    nodes = {n["address"]: n for n in tree["nodes"]}
    annex = nodes["act/approved/1/annex/7"]
    assert annex["parent_address"] == "act/approved/1"
    assert len(annex["attachment_evidence_block_ids"]) == (2 if split else 1)
    assert nodes["act/approved/1/annex/7/point/1"]["parent_address"] == annex["address"]
    assert next(n for n in tree["nodes"] if n["kind"] == "table")["parent_address"] == "act/approved/1/annex/7/point/1"
    assert not tree["unresolved_blocks"]
    assert tree["accounting"]["exactly_once"]
    assert source == saved


@pytest.mark.parametrize("government", [False, True])
@pytest.mark.parametrize("date_text", ["9 июня 2020 г.", "09.06.2020", "09.06.2020 г."])
def test_own_act_reference_formats_and_unnumbered_annex_do_not_fabricate_a_number(government, date_text):
    issuer = "Правительства Российской Федерации" if government else ISSUER
    source = extraction(["1. Изменить правила.",
                         f"Приложение к постановлению {issuer} от {date_text} № 812",
                         ("Title", "Изменения"), "1. Новое условие."], government=government)
    tree = pdf_tree(source, CLAIM.replace(ISSUER, issuer), "amendment")
    annex, = [n for n in tree["nodes"] if n["kind"] == "annex"]
    assert annex["parent_address"] == tree["namespace"]
    assert annex["number_canonical"] is None
    assert not annex["number_is_explicit"]
    assert not tree["unresolved_blocks"]


@pytest.mark.parametrize("date_text", ["09.06.2020", "9 июня 2020"])
def test_split_approval_metadata_and_date_notation_resolve_one_identity(date_text):
    source = extraction(["1. Утвердить правила.", ("Page-header", "УТВЕРЖДЕНЫ"),
                         ("Page-header", f"постановлением {ISSUER}"),
                         ("Page-header", f"от {date_text} № 812"),
                         ("Title", "ПРАВИЛА учёта"), "1. Обязанность."])
    tree = pdf_tree(source, CLAIM, "original")
    approved, = [n for n in tree["nodes"] if n["kind"] == "approved_text"]
    assert len(approved["approval_evidence_block_ids"]) == 3
    assert next(n for n in tree["nodes"] if n["text"] == "1. Обязанность.")["parent_address"] == approved["address"]
    assert not tree["unresolved_blocks"]


@pytest.mark.parametrize("target", ["СП 9.9.9999-2", "неизвестным правилам"])
def test_unresolved_semantic_header_cannot_keep_the_previous_owner(target):
    source = extraction(["1. Утвердить правила.",
                         f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812",
                         ("Title", "Санитарные правила СП 9.9.9999-20"), "1. Старое правило.",
                         ("Page-header", f"Приложение № 7 к {target}"),
                         ("Title", "Другие условия"), "2. Неизвестная принадлежность."])
    tree = pdf_tree(source, CLAIM, "original")
    assert "annex_target_unresolved" in {b["reason"] for b in tree["unresolved_blocks"]}
    assert not any(n["text"] == "2. Неизвестная принадлежность." for n in tree["nodes"])


def test_attachment_uses_explicit_reference_among_multiple_approved_texts():
    stamp = f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812"
    source = extraction(["1. Утвердить два документа.", stamp, ("Title", "Правила учёта"), "1. Учёт.",
                         stamp, ("Title", "Правила осмотра"), "1. Осмотр.",
                         "Приложение № 3", "к Правилам учёта", ("Title", "Форма"), "1. Поле."])
    tree = pdf_tree(source, CLAIM, "original")
    annex, = [n for n in tree["nodes"] if n["kind"] == "annex"]
    assert annex["parent_address"] == "act/approved/1"
    assert not tree["unresolved_blocks"]


def test_ambiguous_attachment_reference_does_not_choose_latest_approved_text():
    stamp = f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812"
    source = extraction(["1. Утвердить документы.", stamp, ("Title", "Правила учёта"), "1. Один.",
                         stamp, ("Title", "Правила учёта"), "1. Другой.",
                         "Приложение № 3 к Правилам учёта", ("Title", "Форма"), "2. Неизвестный владелец."])
    tree = pdf_tree(source, CLAIM, "original")
    assert not any(n["kind"] == "annex" for n in tree["nodes"])
    assert "annex_target_unresolved" in {b["reason"] for b in tree["unresolved_blocks"]}


def test_repeated_attachment_running_header_does_not_reopen_or_reset_scope():
    source = extraction(["1. Утвердить правила.",
                         f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812",
                         ("Title", "Санитарные правила СП 9.9.9999-20"),
                         "Приложение № 3 к СП 9.9.9999-20", ("Title", "Форма"), "1. Условие.",
                         ("Page-header", "Приложение № 3 к СП 9.9.9999-20"), "Продолжение условия."])
    tree = pdf_tree(source, CLAIM, "original")
    assert len([n for n in tree["nodes"] if n["kind"] == "annex"]) == 1
    assert next(n for n in tree["nodes"] if n["text"] == "Продолжение условия.")["parent_address"] == "act/approved/1/annex/3/point/1"
    assert not tree["unresolved_blocks"]


@pytest.mark.parametrize("category", ["Text", "Page-header"])
def test_caption_inside_amendment_quote_cannot_open_an_own_document(category):
    source = extraction(["1. Изложить документ в следующей редакции:", "«1. Чужое правило.",
                         (category, f"Приложение к постановлению {ISSUER} от 09.06.2020 № 812"),
                         ("Title", "Форма"), "2. Чужое условие.»;", "2. Собственное правило."])
    tree = pdf_tree(source, CLAIM, "amendment")
    assert not any(n["kind"] == "annex" for n in tree["nodes"])
    assert next(n for n in tree["nodes"] if n["text"] == "2. Собственное правило.")["parent_address"] == tree["namespace"]


def test_unknown_scope_cannot_be_mistaken_for_a_repeated_header():
    source = extraction(["1. Начало.", ("Page-header", "Приложение № 1 к неизвестным правилам"),
                         ("Title", "Неизвестная область"), "2. Неизвестное правило.",
                         ("Page-header", f"Приложение № 2 к постановлению {ISSUER} от 09.06.2020 № 812"),
                         ("Title", "Новая область"), "1. Проверенное правило."])
    tree = pdf_tree(source, CLAIM, "original")
    assert next(n for n in tree["nodes"] if n["text"] == "1. Проверенное правило.")["parent_address"] == "act/annex/2"
    assert not any(n["parent_address"] is None for n in tree["nodes"])


def test_attachment_with_multiple_designations_cannot_choose_the_first_one():
    stamp = f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812"
    source = extraction(["1. Утвердить документы.", stamp, ("Title", "Правила СП 9.9.9999-20"), "1. Первый.",
                         stamp, ("Title", "Правила СП 8.8.8888-21"), "1. Второй.",
                         "Приложение № 3 к СП 9.9.9999-20 и СП 8.8.8888-21", ("Title", "Форма"), "2. Неизвестное правило."])
    tree = pdf_tree(source, CLAIM, "original")
    assert not any(n["kind"] == "annex" for n in tree["nodes"])
    assert "annex_target_unresolved" in {b["reason"] for b in tree["unresolved_blocks"]}


def test_unknown_attachment_owner_cannot_fall_back_to_act_root_for_a_table():
    source = extraction(["1. Старое правило.", "Приложение № 2 к неизвестным правилам",
                         ("Table", "<table><tr><td>не менее 7</td></tr></table>")])
    tree = pdf_tree(source, CLAIM, "original")
    assert not any(n["kind"] == "table" for n in tree["nodes"])
    table, = [b for b in tree["unresolved_blocks"] if b["layout_kind"] == "table"]
    assert table["reason"] == "document_scope_unresolved"
    assert table["table_topology"] == source["pages"][0]["regions"][-1]["table"]


@pytest.mark.parametrize("fault", ["parent", "evidence", "title", "number"])
def test_attachment_validation_rejects_a_valid_graph_with_wrong_source_scope(fault):
    stamp = f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812"
    source = extraction(["1. Утвердить документы.", stamp, ("Title", "Правила учёта"), "1. Один.",
                         stamp, ("Title", "Правила осмотра"), "1. Другой.",
                         "Приложение № 3 к Правилам учёта", ("Title", "Форма"), "1. Поле."])
    tree = pdf_tree(source, CLAIM, "original")
    annex = next(n for n in tree["nodes"] if n["kind"] == "annex")
    if fault == "parent":
        nodes = {n["address"]: n for n in tree["nodes"]}
        nodes[annex["parent_address"]]["children"].remove(annex["address"])
        annex["parent_address"] = "act/approved/2"
        nodes[annex["parent_address"]]["children"].append(annex["address"])
    elif fault == "evidence":
        annex["attachment_evidence_block_ids"] = []
    elif fault == "title":
        next(n for n in tree["nodes"] if n["address"] == "act/approved/1")["title"] = "Вымышленный заголовок"
    else:
        annex["number_canonical"] = None
    with pytest.raises(ValueError, match="scope evidence"):
        ocr_structure.validate_ocr_tree(source, tree)


@pytest.mark.parametrize("target", ["СанПиН 9.9.9999-20", "СП 9.9.9999-20.1", "СП 9.9.9999-20а"])
def test_attachment_designation_needs_the_type_and_entire_identifier(target):
    source = extraction(["1. Утвердить правила.",
                         f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812",
                         ("Title", "Правила СП 9.9.9999-20"), "1. Старое правило.",
                         f"Приложение № 3 к {target}", ("Title", "Форма"), "1. Неизвестное правило."])
    tree = pdf_tree(source, CLAIM, "original")
    assert not any(n["kind"] == "annex" for n in tree["nodes"])
    assert "annex_target_unresolved" in {b["reason"] for b in tree["unresolved_blocks"]}


def test_repeated_approval_and_title_cannot_create_a_second_document():
    stamp = f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812"
    source = extraction(["1. Утвердить правила.", stamp, ("Title", "Правила учёта"), "1. Условие.",
                         ("Page-header", stamp), ("Title", "Правила учёта"), "Продолжение условия."])
    tree = pdf_tree(source, CLAIM, "original")
    assert len([n for n in tree["nodes"] if n["kind"] == "approved_text"]) == 1
    assert next(n for n in tree["nodes"] if n["text"] == "Продолжение условия.")["parent_address"] == "act/approved/1/point/1"


def test_swapped_title_evidence_cannot_reassign_an_attachment():
    stamp = f"УТВЕРЖДЕНЫ постановлением {ISSUER} от 9 июня 2020 г. № 812"
    source = extraction(["1. Утвердить документы.", stamp, ("Title", "Правила учёта"), "1. Один.",
                         stamp, ("Title", "Правила осмотра"), "1. Другой.",
                         "Приложение № 3 к Правилам учёта", ("Title", "Форма"), "1. Поле."])
    tree = pdf_tree(source, CLAIM, "original")
    first, second = [n for n in tree["nodes"] if n["kind"] == "approved_text"]
    for key in ("title", "title_block_ids"):
        first[key], second[key] = second[key], first[key]
    annex = next(n for n in tree["nodes"] if n["kind"] == "annex")
    first["children"].remove(annex["address"])
    second["children"].append(annex["address"])
    annex["parent_address"] = second["address"]
    with pytest.raises(ValueError, match="scope evidence"):
        ocr_structure.validate_ocr_tree(source, tree)
