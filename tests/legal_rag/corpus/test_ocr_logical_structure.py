"""Authored controls for the M1-04A logical-paragraph experiment; no corpus or OCR engine."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest


def load_script(name):
    path = Path(__file__).resolve().parents[3] / f"docs/assets/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their module during class creation
    spec.loader.exec_module(module)
    return module


S = load_script("ocr_logical_structure")
EVAL = load_script("evaluate_ocr_owner_gold")


def extraction(pages):
    """pages: list of lists of (category, text[, x]) tuples."""
    out = {"source_asset_sha256": "0" * 64, "pages": [], "blocks": [], "text_nodes": []}
    for pno, regions in enumerate(pages, start=1):
        page = {"page": pno, "image_size": [1600, 2300], "regions": []}
        for index, item in enumerate(regions):
            category, text = item[0], item[1]
            x = item[2] if len(item) > 2 else 180
            rid = f"r{pno}-{index}"
            page["regions"].append({"region_id": rid, "category": category, "bbox": [x, 100 + index * 50, 1400, 140 + index * 50]})
            if text:
                tid = f"t{pno}-{index}"
                out["text_nodes"].append({"text_node_id": tid, "raw_text": text})
                out["blocks"].append({"source_region_id": rid, "original_text": text, "text_node_ids": [tid]})
        out["pages"].append(page)
    return out


def owners(result):
    return {f"{r['page']}.{r['index']}": r["owner"] for r in result["regions"]}


def conts(result):
    return {f"{r['page']}.{r['index']}": r["continuation"] for r in result["regions"]}


RESOLUTION = [
    [("Title", "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ"), ("Title", "ПОСТАНОВЛЕНИЕ"),
     ("Text", "от 15 мая 2013 г. № 416"),
     ("Text", "Правительство Российской Федерации постановляет:"),
     ("Text", "1. Утвердить прилагаемые Правила."),
     ("Text", "Д.Медведев", 1250), ("Page-footer", "2059534.doc")],
    [("Page-header", "УТВЕРЖДЕНЫ\nпостановлением Правительства\nРоссийской Федерации\nот 15 мая 2013 г. № 416", 900),
     ("Title", "# ПРАВИЛА"), ("Section-header", "## I. Общие положения"),
     ("Text", "1. Правила устанавливают:"), ("Text", "а) первое;"), ("Text", "б) второе;"),
     ("Text", "2. Документы передаются в составе, предусмотренном Правилами содержания,"),
     ("Page-footer", "2059534.doc")],
    [("Page-header", "2"),
     ("Text", "утвержденных постановлением Правительства Российской Федерации от 13 августа 2006 г. № 491."),
     ("Section-header", "II. Порядок передачи"),
     ("Text", "3. Передача осуществляется по акту."),
     ("Page-footer", "2059534.doc")],
]


def test_continuation_starting_with_approval_word_does_not_open_scope():
    result = S.build(extraction(RESOLUTION))
    got = owners(result)
    assert got["3.1"] == "S/I/2"          # lowercase continuation of point 2, not an approval caption
    assert conts(result)["3.1"] is True
    assert got["3.2"] == "S/II" and got["3.3"] == "S/II/3"  # global point numbering continues under II
    assert got["2.0"] == "S" and got["2.1"] == "S"
    assert got["2.4"] == "S/I/1/а" and got["2.5"] == "S/I/1/б"
    assert got["1.4"] == "A/1" and got["1.5"] == "A"   # signature belongs to the act root
    roles = {f"{r['page']}.{r['index']}": r["role"] for r in result["regions"]}
    assert roles["3.0"] == "noise" and roles["1.6"] == "noise" and roles["2.7"] == "noise"


def test_terminated_paragraph_is_not_joined_with_lowercase_list_abzac():
    pages = [[("Text", "4. Стандарты включают:"), ("Text", "а) подготовку, в том числе:")],
             [("Page-header", "2"), ("Text", "разработку перечня работ;"), ("Text", "расчет потребностей;")]]
    result = S.build(extraction(pages))
    assert conts(result)["2.1"] is False and conts(result)["2.2"] is False
    assert owners(result)["2.1"] == "A/4/а" and owners(result)["2.2"] == "A/4/а"


def test_decimal_nesting_dash_items_and_point_after_subpoints():
    pages = [[("Text", "УТВЕРЖДЕНЫ постановлением от 22.05.2020 № 15", 900),
              ("Section-header", "III. Диагностика"),
              ("Text", "3.1. Исследования проводятся по приоритетам:"),
              ("Text", "3.1.1. К приоритету 1-го уровня относится:"),
              ("Text", "- лиц с симптомами;"),
              ("Text", "3.1.2. К приоритету 2-го уровня относится:"),
              ("Text", "3.2. Первичные исследования проводятся лабораториями."),
              ("Section-header", "IV. Мероприятия"),
              ("Text", "4.1. Мероприятия включают комплекс мер.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.3"] == "S/III/3.1/3.1.1"
    assert got["1.4"] == "S/III/3.1/3.1.1"
    assert got["1.5"] == "S/III/3.1/3.1.2"
    assert got["1.6"] == "S/III/3.2"
    assert got["1.8"] == "S/IV/4.1"


def test_date_is_not_a_point_and_annex_to_act_stays_in_act():
    pages = [[("Title", "ГЛАВНЫЙ ГОСУДАРСТВЕННЫЙ САНИТАРНЫЙ ВРАЧ\nПОСТАНОВЛЕНИЕ"), ("Text", "12. 02. 2026"),
              ("Text", "постановляю: внести изменения согласно приложению.")],
             [("Text", "Приложение\nк постановлению Главного государственного\nсанитарного врача\nот 12.02.2026 № 2", 980),
              ("Text", "1. В санитарных правилах:"), ("Text", "а) в пункте 282:"),
              ("Text", "абзац второй дополнить словами «, не менее 700 метров»;"),
              ("Text", "«⁴ Пункты 272, 280 санитарных правил.».")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A" and got["1.2"] == "A"
    assert got["2.0"] == "A/AN" and got["2.1"] == "A/AN/1"
    assert got["2.3"] == "A/AN/1/а" and got["2.4"] == "A/AN/1/а"  # quoted payload is not a footnote


def test_second_approval_caption_opens_second_approved_text_and_its_annex():
    pages = [[("Text", "1. Утвердить Правила."), ("Text", "2. Утвердить форму договора.")],
             [("Text", "УТВЕРЖДЕНЫ", 1000), ("Text", "постановлением Правительства", 900),
              ("Section-header", "I. Общие положения"), ("Text", "1. Правила устанавливают порядок."),
              ("Text", "2. Понятия:"), ("Text", "а) первое;")],
             [("Text", "УТВЕРЖДЕНА\nпостановлением Правительства", 900), ("Title", "ФОРМА ДОГОВОРА"),
              ("Section-header", "I. Предмет договора"), ("Text", "1. По договору оператор обязуется."),
              ("Section-header", "ПРИЛОЖЕНИЕ", 1000), ("Text", "к типовому договору", 860),
              ("Section-header", "I. Объем отходов")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "S/I/1" and got["2.5"] == "S/I/2/а"
    assert got["3.0"] == "S2" and got["3.1"] == "S2"
    assert got["3.3"] == "S2/I/1"
    assert got["3.4"] == "S2/AN" and got["3.5"] == "S2/AN" and got["3.6"] == "S2/AN/I"


def test_footnote_owner_by_marker_and_cross_page_footnote_continuation():
    pages = [[("Section-header", "I. Общие положения"),
              ("Text", "1. Площадки обустраиваются¹."), ("Text", "2. Срок определяется по оценке²."),
              ("Footnote", "¹ Статья 13.4 закона."), ("Footnote", "² Приказ от 19.07.2007 № 224, от 04.04.2017 № 208")],
             [("Page-header", "2"), ("Text", "3. Сортировка не допускается."),
              ("Text", "4. Расстояние до площадок должно быть не менее 20 метров от зданий организаций"),
              ("Text", "(зарегистрирован Минюстом России 24.04.2017)."),
              ("Footnote", "³ Пункт 1 статьи 16 закона.")]]
    result = S.build(extraction(pages))
    got, cont = owners(result), conts(result)
    assert got["1.3"] == "A/I/1" and got["1.4"] == "A/I/2"
    assert got["2.3"] == "A/I/2" and cont["2.3"] is True     # continuation of footnote 2, not of point 4
    assert got["2.4"] == "A"  # step 21.3 F: no mark -> the document of its page (gold never leaves a footnote ownerless)


def test_every_token_is_accounted_and_input_is_not_mutated():
    data = extraction(RESOLUTION)
    original = copy.deepcopy(data)
    result = S.build(data)
    assert data == original
    in_paragraphs = [t for p in result["paragraphs"] for t in p["text_node_ids"]]
    noise_regions = {r["region_id"] for r in result["regions"] if r["role"] == "noise"}
    in_noise = [t for b in data["blocks"] if b["source_region_id"] in noise_regions for t in b["text_node_ids"]]
    assert sorted(in_paragraphs + in_noise) == sorted(t["text_node_id"] for t in data["text_nodes"])
    assert len(set(in_paragraphs)) == len(in_paragraphs)
    broken = copy.deepcopy(data)
    broken["text_nodes"].append({"text_node_id": "orphan", "raw_text": "x"})
    with pytest.raises(ValueError, match="token accounting"):
        S.build(broken)


def test_evaluator_variants_and_alternatives(tmp_path):
    gold_file = tmp_path / "g.txt"
    gold_file.write_text("# c\n1.1 R/I/1\n1.2 S/AN4/2|S/AN4 +\n", encoding="utf-8")
    gold = EVAL.load_gold(gold_file)
    result = EVAL.evaluate(gold, {"1.1": "S/1", "1.2": "S/AN4"}, {"1.2": True})
    assert result["strict"]["correct"] == 1 and result["no_section"]["correct"] == 2
    assert result["continuation"] == {"tp": 1, "fp": 0, "fn": 0}


def test_owner_path_v2_typed_segments():
    assert EVAL.norm("R/гл2/ст5/ч2/3") == "S/гл2/ст5/ч2/3"
    assert EVAL.norm("A/гл2/ст5/ч2/3") != EVAL.norm("A/гл2/ст5/ч3/3")
    assert EVAL.variant("A/гл2/ст5/ч2/3", "strict") != EVAL.variant("A/гл2/ст5/ч3/3", "strict")
    assert EVAL.variant("S/I/разд3/2.1/абз1", "no_section") == "S/2.1/абз1"
    assert EVAL.variant("S/разд3/гл2", "no_section") == "S/гл2"
    # scope dropping: letter scopes, attached documents and annex scopes
    assert EVAL.variant("A/AN2/разд1/4", "numbers") == "AN2/4"
    assert EVAL.variant("S2/II/4", "numbers") == "S2/4"
    assert EVAL.variant("S/AN4/2", "numbers") == EVAL.variant("A/AN4/2", "numbers")


def test_single_attached_document_equivalence():
    assert EVAL.equivalent("S/4", "A/AN/4", 1)
    assert EVAL.equivalent("A/AN1/4", "S/4", 1)
    assert EVAL.equivalent("R/4", "A/AN1/4", 1)
    assert EVAL.equivalent("S", "A/AN", 1)
    assert not EVAL.equivalent("S/4", "A/AN/4", 2)
    assert not EVAL.equivalent("S/4", "A/AN2/4", 1)
    assert not EVAL.equivalent("A/4", "S/4", 1)
    assert EVAL.equivalent("A/2", "A/2", 2)
    gold = {
        "1.1": {"owners": ["S/4"], "continuation": False},
        "1.2": {"owners": ["A/1"], "continuation": False},
    }
    assert EVAL.attached_count(gold) == 1
    assert EVAL.evaluate(gold, {"1.1": "A/AN/4", "1.2": "A/1"})["strict"]["correct"] == 2
    gold["1.3"] = {"owners": ["A/AN2/1"], "continuation": False}
    assert EVAL.attached_count(gold) == 2
    assert EVAL.evaluate(gold, {"1.1": "A/AN1/4", "1.2": "A/1", "1.3": "A/AN2/1"})["strict"]["correct"] == 2


def test_existing_gold_results_unchanged(tmp_path):
    gold_file = tmp_path / "old.txt"
    gold_file.write_text("1.1 A/1\n1.2 R/II/2.1\n1.3 S/AN4/2|S/AN4 +\n1.4 S/3/а\n", encoding="utf-8")
    gold = EVAL.load_gold(gold_file)
    assert EVAL.attached_count(gold) == 1
    predicted = {"1.1": "A/1", "1.2": "S/2.1", "1.3": "S/AN4", "1.4": "S/3/б"}
    result = EVAL.evaluate(gold, predicted, {"1.3": True})
    assert (result["strict"]["correct"], result["no_section"]["correct"], result["numbers"]["correct"]) == (2, 3, 3)
    assert result["continuation"] == {"tp": 1, "fp": 0, "fn": 0}


def test_attached_count_dedupes_annex_one_and_approved_text():
    def gold_of(*paths):
        return {f"1.{i}": {"owners": [p], "continuation": False} for i, p in enumerate(paths)}

    assert EVAL.attached_count(gold_of("S/4", "A/AN1/4")) == 1
    assert EVAL.attached_count(gold_of("S/4", "A/AN/4")) == 1
    assert EVAL.attached_count(gold_of("S/4", "A/AN2/4")) == 2
    assert EVAL.attached_count(gold_of("S/4", "S2/4")) == 2


def test_equivalence_applies_in_all_variants():
    gold = {"1.1": {"owners": ["S/II/4"], "continuation": False}}
    result = EVAL.evaluate(gold, {"1.1": "A/AN/4"})
    assert (result["strict"]["correct"], result["no_section"]["correct"], result["numbers"]["correct"]) == (0, 1, 1)
    gold["1.2"] = {"owners": ["A/AN2/1"], "continuation": False}
    result = EVAL.evaluate(gold, {"1.1": "A/AN1/4", "1.2": "A/AN2/1"})
    assert result["no_section"]["correct"] == 1 and result["numbers"]["correct"] == 1


def gold_lines(*paths):
    return {f"1.{i}": {"owners": p.split("|"), "continuation": False} for i, p in enumerate(paths)}


def test_single_annex_documents_counted_per_document_from_gold():
    assert EVAL.single_annex_documents(gold_lines("S/1", "S/AN1/2", "S/AN1")) == {"S"}
    assert EVAL.single_annex_documents(gold_lines("S/AN/2", "S/AN1/3")) == {"S"}       # AN and AN1: one annex
    assert EVAL.single_annex_documents(gold_lines("S/AN1/2", "S/AN2/3")) == set()      # two annexes
    assert EVAL.single_annex_documents(gold_lines("S/AN4/2")) == set()                 # only annex 4 seen
    assert EVAL.single_annex_documents(gold_lines("A/1|S/AN2", "S/AN1")) == set()      # alternatives count
    assert EVAL.single_annex_documents(gold_lines("A/AN/1", "S2/AN1", "S3/AN1", "S3/AN2")) == {"A", "S2"}


def test_single_annex_equivalence_only_with_exactly_one_annex():
    # One annex of the attached document: S/AN == S/AN1 in every variant, only with the flag.
    gold = gold_lines("S/I/1", "S/AN1/II/2", "S/AN1")
    predicted = {"1.0": "S/I/1", "1.1": "S/AN/II/2", "1.2": "S/AN"}
    for name in ("strict", "no_section", "numbers"):
        assert EVAL.evaluate(gold, predicted, single_annex=True)[name]["correct"] == 3
        assert EVAL.evaluate(gold, predicted)[name]["correct"] == 1
    result = EVAL.evaluate(gold, predicted, single_annex=True)
    assert result["single_annex_documents"] == ["S"] and result["errors"] == []
    assert "single_annex_documents" not in EVAL.evaluate(gold, predicted)
    # The other direction (gold unnumbered, prediction numbered) as well.
    assert EVAL.evaluate(gold_lines("S/AN/2"), {"1.0": "S/AN1/2"}, single_annex=True)["strict"]["correct"] == 1
    # Two annexes: numbering must match exactly.
    two = gold_lines("S/AN1/2", "S/AN2/3")
    assert EVAL.evaluate(two, {"1.0": "S/AN/2", "1.1": "S/AN2/3"}, single_annex=True)["strict"]["correct"] == 1
    # S<k>/AN == S<k>/AN1, and A/AN/... == A/AN1/... inside the act (two attached documents, no S alias).
    many = gold_lines("S/1", "S2/AN1/4", "A/AN1/5")
    assert EVAL.attached_count(many) == 2      # first_scope counts A/AN1 as S
    got = EVAL.evaluate(many, {"1.0": "S/1", "1.1": "S2/AN/4", "1.2": "A/AN/5"}, single_annex=True)
    assert got["strict"]["correct"] == 3
    # Equivalence is per document: S has one annex, S2 has two.
    mixed = gold_lines("S/AN1/1", "S2/AN1/1", "S2/AN2/1")
    got = EVAL.evaluate(mixed, {"1.0": "S/AN/1", "1.1": "S2/AN/1", "1.2": "S2/AN2/1"}, single_annex=True)
    assert got["strict"]["correct"] == 2 and [e["region"] for e in got["errors"]] == ["1.1"]
    # The single-attached-document alias still applies on top.
    assert EVAL.equivalent("S/4", "A/AN/4", 1, single=frozenset({"A"}))


def test_scope_v2_catches_transfers_between_body_and_annexes():
    assert [EVAL.scope_v2(p) for p in ("A", "A/ст1/2", "A/AN3/1", "S", "S/II/4", "S/AN1/2", "S2/AN/2")] == [
        "A", "A", "A/AN3", "S", "S", "S/AN1", "S2/AN"]
    assert EVAL.scope_v2(None) is None
    # Annex of the attached document -> its body, and back; between annexes; between documents.
    assert EVAL.cross_scope_v2("S/AN1/3", "S/3", 1)
    assert EVAL.cross_scope_v2("S/3", "S/AN1/3", 1)
    assert EVAL.cross_scope_v2("S/AN1/2", "S/AN2/2", 1)
    assert EVAL.cross_scope_v2("A/AN2/1", "A/1", 2)
    assert EVAL.cross_scope_v2("S2/1", "S/1", 2)
    # Same scope, no owner, and the evaluator's equivalences are not transfers.
    assert not EVAL.cross_scope_v2("S/II/2", "S/II/3", 1)
    assert not EVAL.cross_scope_v2("S/AN1/2", None, 1)
    assert not EVAL.cross_scope_v2("S/4", "A/AN1/5", 1)
    assert not EVAL.cross_scope_v2("S/AN1/2", "S/AN/3", 1, frozenset({"S"}))
    assert EVAL.cross_scope_v2("S/AN1/2", "S/AN/3", 1)
    # The old first_scope does not see a unit inside the approved text as its own scope.
    assert EVAL.first_scope("S/AN1/3") == EVAL.first_scope("S/3") == "S"


# ---- cycle 4 / A1: ordinal equivalence of attached documents (owner decision 23.10.2026)


def test_ordinal_heads_by_first_appearance_and_renaming():
    assert EVAL.ordinal_heads(["A", "S/1", "A/AN/2", "S/3", "A/AN1/1"]) == {"S": "S", "A/AN": "S2", "A/AN1": "S3"}
    assert EVAL.ordinal_heads(["A/AN2/1", "S2", "S/AN1/4", None, "A/5"]) == {"A/AN2": "S", "S2": "S2", "S": "S3"}
    heads = {"A/AN": "S2", "S": "S"}
    assert EVAL.rename_head("A/AN/II/3", heads) == "S2/II/3"
    assert EVAL.rename_head("A/AN", heads) == "S2"
    assert EVAL.rename_head("S/AN1/5", heads) == "S/AN1/5"           # S/AN<n>: the tail keeps its name
    assert EVAL.rename_head("A/ст2", heads) == "A/ст2" and EVAL.rename_head(None, heads) is None
    assert EVAL.rename_head("S/AN1/5", {"S": "S2"}) == "S2/AN1/5"    # renamed head, annex tail kept


def test_attached_ordinal_second_document_named_as_annex_matches():
    # Gold S, S2; the prototype names the second attached document A/AN: equal only with the flag.
    gold = gold_lines("A/1", "S", "S/1", "S2", "S2/1", "S2/2")
    predicted = {"1.0": "A/1", "1.1": "S", "1.2": "S/1", "1.3": "A/AN", "1.4": "A/AN/1", "1.5": "A/AN/2"}
    plain = EVAL.evaluate(gold, predicted, single_annex=True)
    assert plain["strict"]["correct"] == 3 and "attached_ordinal" not in plain
    got = EVAL.evaluate(gold, predicted, single_annex=True, attached_ordinal=True)
    for name in ("strict", "no_section", "numbers"):
        assert got[name]["correct"] == 6
    assert got["errors"] == []
    assert got["attached_ordinal"] == {"gold": {"S": "S", "S2": "S2"}, "predicted": {"S": "S", "A/AN": "S2"}}
    # The same with A/AN<n> and when the gold itself calls the second document A/AN2.
    numbered = {k: v.replace("A/AN", "A/AN1") for k, v in predicted.items()}
    assert EVAL.evaluate(gold, numbered, attached_ordinal=True)["strict"]["correct"] == 6
    gold_an = gold_lines("A/1", "S", "S/1", "A/AN2", "A/AN2/1", "A/AN2/2")
    assert EVAL.evaluate(gold_an, {**predicted, "1.3": "S2", "1.4": "S2/1", "1.5": "S2/2"},
                         attached_ordinal=True)["strict"]["correct"] == 6


def test_attached_ordinal_merged_or_moved_documents_stay_errors_and_transfers():
    gold = gold_lines("S", "S/1", "S2", "S2/1")
    merged = {"1.0": "S", "1.1": "S/1", "1.2": "S", "1.3": "S/2"}        # second document merged into the first
    got = EVAL.evaluate(gold, merged, attached_ordinal=True)
    assert got["strict"]["correct"] == 2 and [e["region"] for e in got["errors"]] == ["1.2", "1.3"]
    heads = (got["attached_ordinal"]["gold"], got["attached_ordinal"]["predicted"])
    assert all(EVAL.cross_scope_v2(e["gold"], e["predicted"], got["attached_count"], heads=heads)
               for e in got["errors"])
    # Text moved from the second document back into the first stays a transfer.
    moved = {"1.0": "S", "1.1": "S/1", "1.2": "A/AN", "1.3": "S/1"}
    got = EVAL.evaluate(gold, moved, attached_ordinal=True)
    assert [e["region"] for e in got["errors"]] == ["1.3"]
    heads = (got["attached_ordinal"]["gold"], got["attached_ordinal"]["predicted"])
    (error,) = got["errors"]
    assert EVAL.cross_scope_v2(error["gold"], error["predicted"], got["attached_count"], heads=heads)
    assert not EVAL.cross_scope_v2("S2/1", "A/AN/1", 2, heads=({"S2": "S2"}, {"A/AN": "S2"}))


def test_attached_ordinal_leaves_annexes_of_attached_documents_and_single_document_alone():
    # S/AN1 is an annex of the attached document, not an attached document of its own.
    gold = gold_lines("S/1", "S/AN1", "S/AN1/1", "S2/1")
    predicted = {"1.0": "S/1", "1.1": "S/AN1", "1.2": "S/AN1/1", "1.3": "A/AN/1"}
    got = EVAL.evaluate(gold, predicted, attached_ordinal=True)
    assert got["strict"]["correct"] == 4 and got["attached_ordinal"]["gold"] == {"S": "S", "S2": "S2"}
    wrong = {**predicted, "1.1": "A/AN", "1.2": "A/AN/1", "1.3": "S2/1"}   # annex of S read as a document
    assert EVAL.evaluate(gold, wrong, attached_ordinal=True)["strict"]["correct"] == 1
    # One attached document: S == A/AN == A/AN1 as before, with and without the flag.
    one = gold_lines("A/1", "S/1", "S/2")
    for p in ({"1.0": "A/1", "1.1": "A/AN/1", "1.2": "A/AN/2"}, {"1.0": "A/1", "1.1": "A/AN1/1", "1.2": "S/2"}):
        assert EVAL.evaluate(one, p)["strict"]["correct"] == 3
        assert EVAL.evaluate(one, p, attached_ordinal=True)["strict"]["correct"] == 3
    # The act's own text is never renamed, and documents seen in the same order score as before.
    same = gold_lines("A/1", "S/1", "S2/1")
    p = {"1.0": "A/1", "1.1": "S/1", "1.2": "S2/2"}
    assert (EVAL.evaluate(same, p, attached_ordinal=True)["strict"]
            == EVAL.evaluate(same, p)["strict"])


LAW = [
    [("Title", "РОССИЙСКАЯ ФЕДЕРАЦИЯ\nФЕДЕРАЛЬНЫЙ ЗАКОН"), ("Text", "Об упразднении некоторых судов"),
     ("Text", "Принят Государственной Думой"),
     ("Section-header", "Статья 1"),
     ("Text", "В соответствии со статьей 17 Федерального конституционного закона:"),
     ("Text", "1) упразднить:"),
     ("Text", "Первый районный суд, передав относящиеся к его ведению вопросы;"),
     ("Text", "2) установить, что юрисдикция суда распространяется на район;")],
    [("Page-header", "2"), ("Section-header", "## Статья 2"),
     ("Text", "1. Часть первая вступает в силу со дня опубликования."),
     ("Text", "2. Пункты 1 - 3 статьи 1 вступают в силу через три месяца.")],
]


def test_article_headings_and_parts():
    got = owners(S.build(extraction(LAW)))
    assert got["1.0"] == "A" and got["1.2"] == "A"
    assert got["1.3"] == "A/ст1"
    assert got["1.4"] == "A/ст1"          # unmarked text after the heading belongs to the article
    assert got["1.5"] == "A/ст1/1" and got["1.6"] == "A/ст1/1"
    assert got["1.7"] == "A/ст1/2"
    assert got["2.1"] == "A/ст2"          # a new article closes the previous one and its points
    assert got["2.2"] == "A/ст2/ч1" and got["2.3"] == "A/ст2/ч2"


def test_chapter_contains_articles():
    pages = [[("Section-header", "Глава 1. Общие положения"),
              ("Section-header", "Статья 1. Предмет регулирования"),
              ("Text", "Настоящий Федеральный закон регулирует отношения."),
              ("Section-header", "Статья 2. Основные понятия"),
              ("Text", "1. Для целей настоящего закона используются понятия:"),
              ("Text", "1) первое понятие;"),
              ("Text", "а) его вид;"),
              ("Section-header", "Глава 2. Порядок"),
              ("Section-header", "Статья 3. Порядок действий"),
              ("Text", "Порядок устанавливается Правительством."),
              ("Section-header", "§ 1. Особенности"),
              ("Section-header", "Статья 4"),
              ("Text", "Текст статьи четыре.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.0"] == "A/гл1"
    assert got["1.1"] == "A/гл1/ст1" and got["1.2"] == "A/гл1/ст1"
    assert got["1.3"] == "A/гл1/ст2"
    assert got["1.4"] == "A/гл1/ст2/ч1"
    assert got["1.5"] == "A/гл1/ст2/ч1/1" and got["1.6"] == "A/гл1/ст2/ч1/1/а"
    assert got["1.7"] == "A/гл2"          # chapter 2 closes chapter 1 and its articles
    assert got["1.8"] == "A/гл2/ст3" and got["1.9"] == "A/гл2/ст3"   # article numbers run through chapters
    assert got["1.10"] == "A/гл2/§1" and got["1.11"] == "A/гл2/§1/ст4"


def test_sections_contain_chapters():
    pages = [[("Section-header", "Раздел I. Общая часть"), ("Section-header", "Глава 1"),
              ("Section-header", "Статья 1"), ("Text", "Текст."),
              ("Section-header", "Раздел 2. Особенная часть"), ("Section-header", "Глава 2"),
              ("Section-header", "Статья 2"), ("Text", "Текст.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.0"] == "A/I" and got["1.1"] == "A/I/гл1" and got["1.3"] == "A/I/гл1/ст1"
    assert got["1.4"] == "A/разд2" and got["1.5"] == "A/разд2/гл2" and got["1.7"] == "A/разд2/гл2/ст2"


def test_uppercase_section_heading_closes_previous_section_and_nests_chapters():
    """Review Focus 4: «РАЗДЕЛ I ОБЩИЕ ПОЛОЖЕНИЯ» (uppercase, no dot, OCR «ІХ») is the level
    above chapters; the next section heading closes the previous section's chapter and
    article stack instead of being absorbed by the last article."""
    pages = [[("Section-header", "РАЗДЕЛ I ОБЩИЕ ПОЛОЖЕНИЯ"), ("Section-header", "Глава 1. Основные положения"),
              ("Section-header", "Статья 1. Предмет"), ("Text", "1. Настоящий Кодекс регулирует порядок."),
              ("Text", "2. Вторая часть статьи."),
              ("Section-header", "РАЗДЕЛ II МЕРЫ ПРОЦЕССУАЛЬНОГО ПРИНУЖДЕНИЯ"),
              ("Section-header", "Глава 2. Меры принуждения"), ("Section-header", "Статья 2. Виды мер"),
              ("Text", "1. Мерами являются:"), ("Text", "1) привод;"),
              ("Section-header", "РАЗДЕЛ ІХ ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ"),
              ("Section-header", "Глава 3. Порядок введения"), ("Section-header", "Статья 3. Вступление в силу"),
              ("Text", "Настоящий Кодекс вступает в силу.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.0"] == "A/I" and got["1.1"] == "A/I/гл1" and got["1.2"] == "A/I/гл1/ст1"
    assert got["1.3"] == "A/I/гл1/ст1/ч1" and got["1.4"] == "A/I/гл1/ст1/ч2"
    assert got["1.5"] == "A/II"                     # not A/I/гл1/ст1/ч2
    assert got["1.6"] == "A/II/гл2" and got["1.8"] == "A/II/гл2/ст2/ч1" and got["1.9"] == "A/II/гл2/ст2/ч1/1"
    assert got["1.10"] == "A/IX"                    # OCR Ukrainian І + Cyrillic Х
    assert got["1.11"] == "A/IX/гл3" and got["1.13"] == "A/IX/гл3/ст3"


def test_section_word_forms_and_sentences():
    for text in ("РАЗДЕЛ I", "РАЗДЕЛ II. ОБЩИЕ ПОЛОЖЕНИЯ", "Раздел IV Требования", "РАЗДЕЛ 3"):
        assert S.parse_marker(text, "Section-header").kind == "section_named", text
    assert S.parse_marker("РАЗДЕЛ ІХ ЗАКЛЮЧИТЕЛЬНЫЕ ПОЛОЖЕНИЯ", "Section-header").label == "IX"
    assert S.parse_marker("РАЗДЕЛ 3", "Section-header").label == "разд3"
    # a sentence that starts with the word is not a heading
    assert S.parse_marker("Раздел II настоящего Порядка применяется к организациям.", "Text").kind == "none"
    assert S.parse_marker("РАЗДЕЛЫ I и II применяются.", "Text").kind == "none"


def test_roman_sections_without_the_word_still_open_sections():
    """SanPiN-like approved texts: «I. Общие положения» without «Раздел» stays a section."""
    pages = [[("Section-header", "I. Общие положения"), ("Text", "1. Первый пункт."),
              ("Section-header", "II. Требования"), ("Text", "2. Второй пункт."), ("Text", "а) подпункт;")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.0"] == "A/I" and got["1.1"] == "A/I/1"
    assert got["1.2"] == "A/II" and got["1.3"] == "A/II/2" and got["1.4"] == "A/II/2/а"


def test_inline_article_reference_is_not_a_heading():
    pages = [[("Section-header", "Статья 1"),
              ("Text", "1. Порядок определяется в соответствии со статьей 17 настоящего закона."),
              ("Text", "Статья 17 Федерального закона от 1 мая 2010 года № 5-ФЗ применяется в части, не урегулированной."),
              ("Text", "Глава 3 Кодекса применяется к отношениям по договору."),
              ("Text", "2. Вторая часть статьи.")]]
    result = S.build(extraction(pages))
    got = owners(result)
    assert got["1.1"] == "A/ст1/ч1"
    assert got["1.2"] == "A/ст1/ч1" and got["1.3"] == "A/ст1/ч1"   # sentences, not headings
    assert got["1.4"] == "A/ст1/ч2"
    assert S.parse_marker("в соответствии со статьей 17", "Text").kind == "none"


def test_superscript_and_decimal_article_numbers():
    assert S.parse_marker("Статья 5¹", "Section-header").label == "ст5¹"
    assert S.parse_marker("Статья 12.1. Особенности", "Section-header").label == "ст12.1"
    assert S.parse_marker("Статья 7.", "Section-header").label == "ст7"
    pages = [[("Section-header", "Статья 5"), ("Text", "Текст пятой."),
              ("Section-header", "Статья 5¹"), ("Text", "1. Часть первая."),
              ("Section-header", "Статья 12.1. Особенности"), ("Text", "Текст."),
              ("Section-header", "Статья 13"), ("Text", "Текст тринадцатой.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A/ст5¹" and got["1.3"] == "A/ст5¹/ч1"
    assert got["1.4"] == "A/ст12.1" and got["1.5"] == "A/ст12.1"
    assert got["1.6"] == "A/ст13" and got["1.7"] == "A/ст13"


def test_inserted_chapter_section_and_paragraph_sign_numbers():
    """Cycle 8 C1: «Глава 24¹», «Раздел I¹», «§ 2¹» are headings like «Статья 5¹»; the inserted chapter
    closes the previous one, so its articles leave it."""
    assert S.parse_marker("Глава 24¹. Исполнение судебных актов", "Section-header").label == "гл24¹"
    assert S.parse_marker("РАЗДЕЛ I¹ ОБЩИЕ", "Section-header").label == "I¹"
    assert S.parse_marker("§ 2¹. Особенности", "Section-header").label == "§2¹"
    pages = [[("Section-header", "Глава 24. Порядок"), ("Section-header", "Статья 241"), ("Text", "Текст."),
              ("Section-header", "Глава 24¹. Исполнение"), ("Section-header", "Статья 242¹"),
              ("Text", "1. Часть первая."), ("Section-header", "Глава 25. Иное"), ("Section-header", "Статья 243"),
              ("Text", "Текст.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A/гл24/ст241"
    assert got["1.3"] == "A/гл24¹" and got["1.4"] == "A/гл24¹/ст242¹" and got["1.5"] == "A/гл24¹/ст242¹/ч1"
    assert got["1.8"] == "A/гл25/ст243"


def test_editorial_note_belongs_to_the_unit_it_names():
    """Cycle 8 C2: «(Статья в редакции …)», «(Дополнение частью …)», «(Особенности применения статьи …)»
    after the last part or point go to the named unit; a note naming no open unit, an ordinary
    parenthesis and «(В редакции …)» without a unit keep their owner."""
    pages = [[("Section-header", "Статья 5. Порядок"), ("Text", "1. Первая часть."),
              ("Text", "2. Вторая часть содержит:"), ("Text", "1) первый пункт;"), ("Text", "2) второй пункт."),
              ("Text", "(Дополнение частью - Федеральный закон от 01.01.2020 № 1-ФЗ)"),
              ("Text", "(Статья в редакции Федерального закона от 02.02.2021 № 2-ФЗ)"),
              ("Section-header", "Статья 6. Иное"), ("Text", "1. Часть первая содержит:"),
              ("Text", "1) пункт первый."),
              ("Text", "(Особенности применения статьи 6 - Федеральный закон от 03.03.2022 № 3-ФЗ)"),
              ("Section-header", "Статья 7. Другое"), ("Text", "1. Часть первая содержит:"),
              ("Text", "1) пункт первый."), ("Text", "(В редакции Федерального закона от 04.04.2023 № 4-ФЗ)"),
              ("Text", "(Глава в редакции Федерального закона от 05.05.2024 № 5-ФЗ)"),
              ("Text", "(далее - Правила) применяются с 2025 года.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.5"] == "A/ст5/ч2"            # «Дополнение частью» -> the part, not its point 2)
    assert got["1.6"] == "A/ст5"               # «Статья в редакции» -> the article
    assert got["1.10"] == "A/ст6"
    assert got["1.14"] == "A/ст7/ч1/1"         # no unit named: unchanged
    assert got["1.15"] == "A/ст7/ч1/1"         # no open chapter: unchanged
    assert got["1.16"] == "A/ст7/ч1/1"         # not an editorial note
    assert S.EDITORIAL_NOTE.match("(Дополнение статьей - Федеральный закон от 26.04.2007 № 63-ФЗ)")
    assert not S.EDITORIAL_NOTE.match("(Пункт 3 настоящих Правил применяется с 2025 года.)")


def test_list_closed_by_a_sentence_restarts_at_its_level():
    """Cycle 8 C3: after «4) ….» an unmarked capitalised sentence closes the list; the next «1)» starts
    a new list at the level of «4)» (not inside it) and the sentence returns to the article. A list
    that goes on, a «;» item, a lowercase continuation or a quotation keep the old reading."""
    pages = [[("Section-header", "Статья 158. Лицензия"), ("Text", "Для получения лицензии нужно:"),
              ("Text", "1) иметь специалиста;"), ("Text", "2) иметь договор;"), ("Text", "4) иметь учет."),
              ("Text", "Порядок выдачи лицензии определяется Правительством."),
              ("Text", "Лицензия может быть отозвана в случаях:"), ("Text", "1) неоднократного нарушения;"),
              ("Text", "2) причинения ущерба.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.4"] == "A/ст158/4"
    assert got["1.5"] == "A/ст158" and got["1.6"] == "A/ст158"
    assert got["1.7"] == "A/ст158/1" and got["1.8"] == "A/ст158/2"
    pages = [[("Section-header", "Статья 9. Порядок"), ("Text", "Применяются меры:"),
              ("Text", "1) первая;"), ("Text", "2) вторая;"),
              ("Text", "Указанные меры применяются совместно;"), ("Text", "3) третья.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.5"] == "A/ст9/3"             # «;» does not close: the list goes on
    pages = [[("Section-header", "Статья 10. Изменения"), ("Text", "Внести изменения:"),
              ("Text", "1) пункт 3 изложить в следующей редакции:"),
              ("Text", "«3. Порядок устанавливается.»;"), ("Text", "2) пункт 4 признать утратившим силу."),
              ("Text", "«Новая редакция начинается здесь."), ("Text", "1) первый подпункт.»")]]
    result = S.build(extraction(pages))
    assert not any("closing sentence" in str(e) for p in result["paragraphs"] for e in p["evidence"])


def test_inserted_points_and_subpoints_are_siblings():
    """Cycle 8 C4: «2¹.», «3¹)», «е¹)» are inserted units: siblings after «2.», «3)», «е)», not text of
    them; «3.» after «2¹.» continues the numbering."""
    assert S.parse_marker("2¹. Совет Федерации", "Text").label == "2¹"
    assert S.parse_marker("е²) объекты", "Text").sup == 2
    pages = [[("Section-header", "Статья 3. Полномочия"), ("Text", "1. Первая часть."), ("Text", "2. Вторая часть."),
              ("Text", "2¹. Вставленная часть."), ("Text", "2². Ещё одна."), ("Text", "3. Третья часть включает:"),
              ("Text", "3) третий пункт;"), ("Text", "3¹) вставленный пункт;"), ("Text", "4) четвёртый пункт.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.3"] == "A/ст3/ч2¹" and got["1.4"] == "A/ст3/ч2²" and got["1.5"] == "A/ст3/ч3"
    assert got["1.7"] == "A/ст3/ч3/3¹" and got["1.8"] == "A/ст3/ч3/4"
    pages = regulation(("Text", "1. Состав определяется:"), ("Text", "е) земельный участок;"),
                       ("Text", "е¹) системы учета;"), ("Text", "ж) иное."))
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "S/I/1/е¹" and got["2.5"] == "S/I/1/ж"


def test_multi_paragraph_amending_quotation_is_text_of_the_introducing_unit():
    """Cycle 8 C5: after «… изложить в следующей редакции:» the quoted «"5) …», «6) …», «7) …";» are text
    of the introducing subpoint; «б)» after the closing quote is structure again. A quotation whose
    closing quote is lost in a quoted form ends at the next number of an outer list («2.» after «1.»)."""
    pages = [[("Section-header", "Статья 1"), ("Text", "Внести в Кодекс следующие изменения:"),
              ("Text", "1) в статье 34:"), ("Text", "а) пункт 5 изложить в следующей редакции:"),
              ("Text", "\"5) в виде расходов на приобретение;"), ("Text", "6) в виде процентов;"),
              ("Text", "7) в виде средств.\";"), ("Text", "б) пункт 8 признать утратившим силу;"),
              ("Text", "2) статью 35 дополнить словами \"и иных\".")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.4"] == got["1.5"] == got["1.6"] == "A/ст1/1/а"
    assert got["1.7"] == "A/ст1/1/б" and got["1.8"] == "A/ст1/2"
    pages = regulation(("Text", "1. В Правилах:"), ("Text", "раздел VIII изложить в следующей редакции:"),
                       ("Text", "\"VIII. Адреса и реквизиты Сторон"), ("Text", "Орган власти ______________ (наименование)"),
                       ("Text", "2. В постановлении № 1078 изменения не вносятся."), ("Text", "а) пункт 28 исключить."))
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "S/I/1" and got["2.5"] == "S/I/1"
    assert got["2.6"] == "S/I/2" and got["2.7"] == "S/I/2/а"


def test_editorial_tail_does_not_hide_the_final_dot_of_a_list_item():
    """Cycle 8 C6: «…Кодекса). (В редакции … № 90-ФЗ)» ends with a dot for the list-closing rules, and a
    standalone note between the last item and the closing sentence is skipped."""
    pages = [[("Section-header", "Статья 77. Основания"), ("Text", "Основаниями являются:"),
              ("Text", "1) соглашение сторон;"),
              ("Text", "2) иные обстоятельства (статья 84 настоящего Кодекса). (В редакции Федерального закона от "
                       "30.06.2006 № 90-ФЗ)"),
              ("Text", "(Часть в редакции Федерального закона от 30.06.2006 № 90-ФЗ)"),
              ("Text", "Трудовой договор может быть прекращен и по другим основаниям."),
              ("Section-header", "Статья 99. Сверхурочная работа"), ("Text", "Допускается в случаях:"),
              ("Text", "1) первом;"), ("Text", "3) третьем. (В редакции Федерального закона от 14.07.2022 № 273-ФЗ)"),
              ("Text", "В других случаях привлечение допускается с согласия работника.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.3"] == "A/ст77/2" and got["1.5"] == "A/ст77"
    assert got["1.10"] == "A/ст99"
    assert S.provision_final("Кодекса). (В редакции Федерального закона от 30.06.2006 № 90-ФЗ)") == "."


def test_endorsed_agreement_and_long_uppercase_annex_caption():
    """Cycle 8 C7: «ОДОБРЕН распоряжением …» opens the endorsed agreement like «УТВЕРЖДЕН»; an uppercase
    «ПРИЛОЖЕНИЕ № 1 к Договору <long title>» (over 300 characters) opens its annex. The law requisite
    «Одобрен Советом Федерации» stays the act's text."""
    title = "об уступке прав на получение доходов в натуральной форме " * 6
    pages = [[("Title", "РАСПОРЯЖЕНИЕ"), ("Text", "1. Одобрить проект договора."), ("Text", "2. Иное."),
              ("Text", "В.Путин", 1200)],
             [("Text", "ОДОБРЕН\nраспоряжением Правительства\nРоссийской Федерации", 1000),
              ("Section-header", "ДОГОВОР " + title), ("Text", "1. Цедент уступает права."),
              ("Text", f"ПРИЛОЖЕНИЕ № 1\nк Договору {title}", 1000), ("Text", "Отчет цессионария.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.0"] == "S" and got["2.2"] == "S/1"
    assert got["2.3"] == "S/AN1" and got["2.4"] == "S/AN1"
    law = [[("Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"), ("Text", "Одобрен Советом Федерации 25 ноября 2016 года"),
            ("Section-header", "Статья 1"), ("Text", "Текст.")]]
    assert owners(S.build(extraction(law)))["1.1"] == "A"


def test_note_vocabulary_follows_the_act():
    """Cycle 8 C8: in an act that cites «пункт 3 настоящей статьи» (Budget Code style) «(Дополнение пунктом
    …)» and «(Положения пункта 2 …)» name the «N.» part, not the «N)» subpoint; in a «часть» act they name
    the «N)» point."""
    article = [("Section-header", "Статья 20. Доходы"), ("Text", "1. Доходы включают:"),
               ("Text", "1) налоги;"), ("Text", "2) сборы."),
               ("Text", "(Дополнение пунктом - Федеральный закон от 07.05.2013 № 104-ФЗ)"),
               ("Text", "(Положения пункта 1 применяются с 2025 года - Федеральный закон от 01.01.2024 № 1-ФЗ)")]
    budget = [[*article, ("Text", "2. Согласно пункту 1 настоящей статьи и пункту 3 настоящей статьи иное.")]]
    got = owners(S.build(extraction(budget)))
    assert got["1.4"] == "A/ст20/ч1" and got["1.5"] == "A/ст20/ч1"
    labour = [[*article, ("Text", "2. Согласно части 1 настоящей статьи иное.")]]
    got = owners(S.build(extraction(labour)))
    assert got["1.4"] == "A/ст20/ч1/2"


def test_quoted_term_at_line_end_does_not_close_the_quotation():
    """Cycle 8 C9: inside a quoted article a line ending with a quoted term («… "налоговый агент";») pairs its
    own quotes and does not close the quotation; the closing line has an unpaired quote. A one-paragraph
    quotation whose nested closing quote OCR lost («… «Об особенностях …».;») opens nothing."""
    pages = [[("Section-header", "Статья 1"), ("Text", "Внести в Кодекс следующие изменения:"),
              ("Text", "1) статью 21 изложить в следующей редакции:"),
              ("Text", "\"Статья 21. Налоговые агенты"),
              ("Text", "1. Для целей настоящей статьи используется понятие \"налоговый агент\";"),
              ("Text", "2. Налоговым агентом признается оператор.\";"),
              ("Text", "2) статью 22 признать утратившей силу.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.3"] == got["1.4"] == got["1.5"] == "A/ст1/1"
    assert got["1.6"] == "A/ст1/2"
    pages = [[("Section-header", "Статья 13"), ("Text", "Внести изменения:"),
              ("Text", "6) статью 39 дополнить подпунктом 7 следующего содержания:"),
              ("Text", "«7) гражданам в соответствии с Федеральным законом «Об особенностях предоставления».;"),
              ("Text", "7) пункт 6 статьи 71 дополнить подпунктом 4.")]]
    assert owners(S.build(extraction(pages)))["1.4"] == "A/ст13/7"


def test_compound_inserted_article_number():
    """Cycle 8 C10: «Статья 115¹⁻¹» (Budget Code) is an article heading of its own, not text of «Статья 115¹»."""
    assert S.parse_marker("Статья 115¹⁻¹. Особенности гарантий", "Section-header").label == "ст115¹⁻¹"
    pages = [[("Section-header", "Статья 115¹. Гарантии"), ("Text", "1. Часть первая."),
              ("Section-header", "Статья 115¹⁻¹. Особенности"), ("Text", "1. Допускается предоставление.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A/ст115¹⁻¹" and got["1.3"] == "A/ст115¹⁻¹/ч1"


def test_editorial_note_at_page_top_and_unit_named_inside():
    """Cycle 8 C11: a note at the top of a page is no continuation of the last point; a note citing an act
    names its unit inside («… действие части 1 - Федеральный закон …», «… статьи 7 - Постановление
    Конституционного Суда …»). A parenthesis without a cited act stays a continuation."""
    pages = [[("Section-header", "Статья 7. Порядок"), ("Text", "1. Порядок включает:"), ("Text", "1) первое;"),
              ("Text", "2) второе.")],
             [("Text", "(Статья в редакции Федерального закона от 26.04.2007 № 63-ФЗ)"),
              ("Text", "(Приостановлено с 1 января 2026 года действие части 1 - Федеральный закон от 01.01.2025 № 1-ФЗ)"),
              ("Text", "(О несоответствии Конституции Российской Федерации статьи 7 - Постановление Конституционного "
                       "Суда Российской Федерации от 01.02.2020 № 5-П)")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.0"] == "A/ст7"
    assert got["2.1"] == "A/ст7/ч1" and got["2.2"] == "A/ст7"
    assert not S.starts_continuation("(Статья в редакции Федерального закона от 26.04.2007 № 63-ФЗ)")
    assert S.starts_continuation("(далее - Правила) применяются с 2025 года.")


def test_code_parts_subsections_and_notes_before_a_closing_sentence():
    """Cycle 8 C12: «ЧАСТЬ ВТОРАЯ. …» is a code division above sections and closes the previous one's
    articles; «ПОДРАЗДЕЛ II» sits between a section and its chapters; a note «(Особенности применения …)»
    between the last list item and a closing sentence does not hide the item's final dot."""
    assert S.parse_marker("ЧАСТЬ ВТОРАЯ. БЮДЖЕТНАЯ СИСТЕМА", "Section-header").label == "разд2"
    assert S.parse_marker("часть 2 статьи 5 применяется", "Text").kind == "none"
    pages = [[("Section-header", "ЧАСТЬ ПЕРВАЯ. ОБЩИЕ ПОЛОЖЕНИЯ"), ("Section-header", "Раздел I. Основы"),
              ("Section-header", "Статья 1. Предмет"), ("Text", "1. Текст."),
              ("Section-header", "ЧАСТЬ ВТОРАЯ. ПРОЦЕСС"), ("Section-header", "Раздел II. Производство"),
              ("Section-header", "ПОДРАЗДЕЛ I. ПРИКАЗНОЕ ПРОИЗВОДСТВО"), ("Section-header", "Глава 11. Приказ"),
              ("Section-header", "Статья 121. Приказ"), ("Text", "Текст статьи.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.4"] == "A/разд2" and got["1.5"] == "A/разд2/II"
    assert got["1.6"] == "A/разд2/II/I" and got["1.8"] == "A/разд2/II/I/гл11/ст121"
    pages = [[("Section-header", "Статья 4. Меры"), ("Text", "Меры применяются при проживании:"),
              ("Text", "1) в зоне отселения;"), ("Text", "3) в иной зоне."),
              ("Text", "(Особенности применения части 2 - Федеральный закон от 29.12.2015 № 388-ФЗ)"),
              ("Text", "Меры поддержки предоставляются при проживании:"), ("Text", "1) в зоне отселения.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.5"] == "A/ст4" and got["1.6"] == "A/ст4/1"


def test_standalone_project_caption_opens_attached_document():
    pages = [[("Title", "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ"), ("Title", "РАСПОРЯЖЕНИЕ"),
              ("Text", "Одобрить представленный проект Соглашения."),
              ("Text", "Д.Медведев", 1250)],
             [("Page-header", "Проект", 1330), ("Section-header", "СОГЛАШЕНИЕ"),
              ("Text", "Стороны согласились о нижеследующем:"),
              ("Section-header", "Статья 1"),
              ("Text", "1. Граждане освобождаются от визовых требований."),
              ("Text", "2. Граждане соблюдают законодательство, указанное в пункте 1 настоящей статьи."),
              ("Section-header", "Статья 2"), ("Text", "Соглашение вступает в силу.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A" and got["1.3"] == "A"
    assert got["2.0"] == "S" and got["2.1"] == "S" and got["2.2"] == "S"
    # controller ruling: «1.» inside an article of an attached document is a point, not a part
    assert got["2.3"] == "S/ст1" and got["2.4"] == "S/ст1/1" and got["2.5"] == "S/ст1/2"
    assert got["2.6"] == "S/ст2" and got["2.7"] == "S/ст2"
    # an annex caption followed by «Проект» is one caption of the attached document
    pages = [[("Text", "1. Одобрить проект Соглашения."), ("Text", "2. Поручить МИДу подписать Соглашение.")],
             [("Text", "Приложение\nк распоряжению Правительства", 1000), ("Text", "ПРОЕКТ", 1300),
              ("Section-header", "СОГЛАШЕНИЕ"), ("Section-header", "Статья 1"), ("Text", "1. Первый пункт.")],
             [("Text", "Проект", 1300), ("Section-header", "ПРОТОКОЛ"), ("Text", "1. Пункт протокола.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/2"
    assert got["2.0"] == "S" and got["2.1"] == "S" and got["2.2"] == "S"
    assert got["2.3"] == "S/ст1" and got["2.4"] == "S/ст1/1"
    assert got["3.0"] == "S2" and got["3.1"] == "S2" and got["3.2"] == "S2/1"


def test_act_article_parts_stay_parts_in_act_scope():
    pages = [[("Section-header", "Статья 1"), ("Text", "1. Часть первая."), ("Text", "2. Часть вторая."),
              ("Section-header", "Статья 2"), ("Text", "1. Часть первая второй статьи.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/ст1/ч1" and got["1.2"] == "A/ст1/ч2" and got["1.4"] == "A/ст2/ч1"
    # the choice is explicit, not an order-dependent tie: a point that leaves an open
    # article without a new heading costs more than the same point inside the article
    article = (("article", "1", "ст1"),)
    assert list(S.transitions(article, S.Marker("int", 1, "1"), None)) == [(article + (("int", 1, "ч1"),), 0.0)]
    assert S.ABANDON_ARTICLE > 0
    assert S.abandons_article((("article", "1", "ст1"), ("int", 1, "ч1")), 0)
    assert not S.abandons_article((("article", "1", "ст1"), ("int", 1, "ч1")), 1)


def test_project_word_inside_sentence_is_not_a_caption():
    pages = [[("Text", "1. Утвердить порядок."),
              ("Text", "Проект постановления подлежит размещению на официальном сайте."),
              ("Text", "Проект вносится в Правительство Российской Федерации в установленном порядке"),
              ("Text", "2. Контроль оставляю за собой.")],
             [("Page-header", "2"), ("Text", "проект"), ("Text", "3. Приказ вступает в силу.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/1" and got["1.2"] == "A/1" and got["1.3"] == "A/2"
    assert got["2.1"] == "A/2" and got["2.2"] == "A/3"


LONG_ANNEX = ("ПРИЛОЖЕНИЕ\nк приказу Министерства цифрового развития, связи и массовых\nкоммуникаций\n"
              "Российской Федерации\nот 25.03.2021 г. № 173")


def test_annex_caption_in_page_header_opens_scope():
    assert len(S.view(LONG_ANNEX)) > 120
    pages = [[("Text", "ПРИКАЗЫВАЮ:"), ("Text", "1. Определить виды имущества согласно приложению."),
              ("Text", "2. Направить приказ на регистрацию."), ("Text", "М.И. Шадаев", 1340)],
             [("Page-header", LONG_ANNEX, 888), ("Section-header", "ВИДЫ особо ценного движимого имущества"),
              ("Text", "1. Транспортные средства."), ("Text", "2. Объекты нематериальных активов.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A/2"
    assert got["2.0"] == "A/AN" and got["2.1"] == "A/AN"
    assert got["2.2"] == "A/AN/1" and got["2.3"] == "A/AN/2"
    # a caption repeated as a running header on three or more pages does not reopen the annex
    running = ("Page-header", "Приложение № 2 к Порядку", 1000)
    pages = [[("Text", "1. Утвердить Порядок."), ("Text", "Приложение № 2\nк Порядку", 1000),
              ("Text", "1. Перечень включает:"), ("Text", "а) первое;")],
             [running, ("Text", "б) второе;"), ("Text", "2. Второй пункт.")],
             [running, ("Text", "3. Третий пункт.")],
             [running, ("Text", "4. Четвертый пункт.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/AN2" and got["1.3"] == "A/AN2/1/а"
    assert got["2.1"] == "A/AN2/1/б" and got["2.2"] == "A/AN2/2"
    assert got["3.1"] == "A/AN2/3" and got["4.1"] == "A/AN2/4"
    # captions that differ only in their numbers are not a running header: each opens its annex
    pages = [[("Text", "1. Правила применяются."), ("Text", "2. Контроль осуществляется.")]]
    pages += [[("Page-header", f"Приложение № {n} к СП 2.1.3684-21", 1000), ("Text", "1. Первый пункт.")]
              for n in range(1, 5)]
    got = owners(S.build(extraction(pages)))
    assert [got[f"{n}.0"] for n in range(2, 6)] == ["A/AN1", "A/AN2", "A/AN3", "A/AN4"]
    assert got["5.1"] == "A/AN4/1"


def test_dated_body_annex_caption_opens_annex():
    caption = "Приложение\nк приказу Министерства\nот 12 мая 2020 г."
    pages = [[("Text", "1. Утвердить перечень."), ("Text", "2. Контроль оставляю за собой.")],
             [("Text", caption, 1000), ("Text", "1. Первая позиция."), ("Text", "2. Вторая позиция.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.0"] == "A/AN" and got["2.1"] == "A/AN/1" and got["2.2"] == "A/AN/2"
    # the long page-header path accepts a final «г.» but not a sentence dot
    long_dated = LONG_ANNEX.replace(" г. № 173", " г.")
    assert len(S.view(long_dated)) > 120
    pages[1][0] = ("Page-header", long_dated, 888)
    assert owners(S.build(extraction(pages)))["2.1"] == "A/AN/1"
    pages[1][0] = ("Page-header", long_dated[:-2] + "утверждается министром.", 888)
    got = owners(S.build(extraction(pages)))
    assert not got["2.0"].startswith("A/AN") and not got["2.1"].startswith("A/AN")


def test_first_running_caption_opens_scope():
    annex = ("Page-header", "Приложение № 1 к Порядку", 1000)
    pages = [[("Text", "1. Утвердить Порядок."), ("Text", "2. Контроль.")],
             [annex, ("Text", "1. Перечень включает:"), ("Text", "а) первое;")],
             [annex, ("Text", "б) второе;"), ("Text", "2. Второй пункт.")],
             [annex, ("Text", "3. Третий пункт.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.0"] == "A/AN1" and got["2.1"] == "A/AN1/1" and got["2.2"] == "A/AN1/1/а"
    assert got["3.1"] == "A/AN1/1/б" and got["3.2"] == "A/AN1/2" and got["4.1"] == "A/AN1/3"
    approval = ("Page-header", "УТВЕРЖДЕНЫ приказом Министерства", 1000)
    pages = [[("Text", "1. Утвердить Правила."), ("Text", "2. Контроль.")],
             [approval, ("Text", "1. Правила устанавливают:"), ("Text", "а) первое;")],
             [approval, ("Text", "б) второе;"), ("Text", "2. Второй пункт.")],
             [approval, ("Text", "3. Третий пункт.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/2"
    assert got["2.0"] == "S" and got["2.1"] == "S/1" and got["2.2"] == "S/1/а"
    assert got["3.1"] == "S/1/б" and got["3.2"] == "S/2" and got["4.1"] == "S/3"
    # the same caption on only two pages is not running: two approved texts open S and S2
    pages = [[("Text", "1. Утвердить Правила и Критерии.")],
             [approval, ("Text", "1. Правила устанавливают порядок."), ("Text", "2. Второй пункт.")],
             [approval, ("Title", "КРИТЕРИИ"), ("Text", "1. Первый критерий.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.0"] == "S" and got["2.2"] == "S/2"
    assert got["3.0"] == "S2" and got["3.2"] == "S2/1"


def test_project_caption_allows_one_naming_word_only():
    assert S.is_project_caption("Проект") and S.is_project_caption("ПРОЕКТ")
    assert S.is_project_caption("Проект соглашения")
    assert not S.is_project_caption("Проект решения рассмотрен")
    assert not S.is_project_caption("Проект постановления подлежит размещению.")
    pages = [[("Text", "1. Утвердить порядок."), ("Text", "Проект решения рассмотрен"),
              ("Text", "2. Контроль оставляю за собой.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/1" and got["1.2"] == "A/2"


def test_abandon_article_penalty_applies_to_points_only():
    # Named headings close every point, so a real stack never keeps a point below an
    # article; a synthetic one shows the penalty on a point that would drop the article.
    stack = (("int", 1, "1"), ("article", "1", "ст1"))
    options = dict(S.transitions(stack, S.Marker("int", 2, "2"), 1))
    assert options[(("int", 2, "2"),)] == pytest.approx(0.02 + S.ABANDON_ARTICLE)
    assert options[stack + (("int", 2, "ч2"),)] == pytest.approx(3.0)
    # an explicit Roman section heading closes the article without a penalty
    stack = (("roman", 1, "I"), ("article", "1", "ст1"))
    options = dict(S.transitions(stack, S.Marker("roman", 2, "II"), None))
    assert options[(("roman", 2, "II"),)] == pytest.approx(0.02)


def test_signature_block_after_last_point_owned_by_scope_root():
    # a law: signer, place/date/number after the last part of the last article
    pages = [[("Section-header", "Статья 1"), ("Text", "1. Часть первая."),
              ("Section-header", "Статья 2"), ("Text", "1. Закон вступает в силу."),
              ("Text", "2. Пункт 1 статьи 1 вступает в силу позднее."),
              ("Text", "Президент Российской Федерации В.Путин", 580),
              ("Text", "Москва, Кремль 19 февраля 2018 года № 22-ФЗ"),
              ("Text", "Зарегистрировано в Минюсте России 1 марта 2018 г. N 50123")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.4"] == "A/ст2/ч2"
    assert got["1.5"] == "A" and got["1.6"] == "A" and got["1.7"] == "A"
    # an order: a short signer title opens the block; later certification lines follow it
    pages = [[("Text", "1. Утвердить перечень."), ("Text", "2. Контроль оставляю за собой."),
              ("Text", "Министр"), ("Text", "Верно", 800),
              ("Text", "Ведущий специалист 3-го разряда отдела делопроизводства", 800),
              ("Text", "28.08.2015"), ("Text", "№ 901")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/2"
    assert [got[f"1.{k}"] for k in range(2, 7)] == ["A"] * 5
    # an attached agreement: closing formula and signature places belong to S
    pages = [[("Text", "Одобрить проект Соглашения.")],
             [("Page-header", "Проект", 1330), ("Section-header", "СОГЛАШЕНИЕ"),
              ("Section-header", "Статья 1"), ("Text", "1. Граждане освобождаются от виз."),
              ("Section-header", "Статья 2"), ("Text", "Настоящее Соглашение вступает в силу."),
              ("Text", "Совершено в г. Москве в двух экземплярах, каждый на русском и английском языках."),
              ("Text", "За Правительство Российской Федерации"), ("Text", "За Правительство Ямайки", 980)]]
    got = owners(S.build(extraction(pages)))
    assert got["2.5"] == "S/ст2"
    assert got["2.6"] == "S" and got["2.7"] == "S" and got["2.8"] == "S"


def test_unmarked_continuation_text_stays_with_last_point():
    pages = [[("Text", "1. Утвердить Правила."), ("Text", "2. Установить, что:"),
              ("Text", "Министерство обеспечивает исполнение в пределах ассигнований."),
              ("Text", "Расходы осуществляются за счет бюджета.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A/2" and got["1.3"] == "A/2"
    # requisite words inside a sentence of the last point do not open a requisite block
    pages = [[("Text", "1. Утвердить Правила."),
              ("Text", "2. Министерству обеспечить исполнение:"),
              ("Text", "Министерство юстиции регистрирует Правила в установленном порядке и публикует их "
                       "на официальном интернет-портале правовой информации в течение десяти дней."),
              ("Text", "Москва и Санкт-Петербург применяют Правила с 1 января 2019 года в полном объеме "
                       "наравне с другими субъектами Российской Федерации без изъятий.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A/2" and got["1.3"] == "A/2"
    assert not S.requisite_like("Министерство юстиции регистрирует Правила в установленном порядке.")


def test_barcode_digits_line_is_requisite():
    assert S.requisite_like("2 100039 06205 0") and S.requisite_like("2100030523895")
    assert not S.requisite_like("15") and not S.requisite_like("1. Первый пункт.")
    # a barcode at the bottom of a page in the middle of the act belongs to the root and does
    # not swallow the continuation of the interrupted paragraph on the next page
    pages = [[("Section-header", "Статья 1"), ("Text", "1) упразднить:"),
              ("Text", "Первый районный суд, передав относящиеся к его ведению вопросы в"),
              ("Text", "2 100039 06204 3", 690)],
             [("Page-header", "2"), ("Text", "юрисдикцию Второго районного суда;"),
              ("Text", "2) установить срок.")]]
    result = S.build(extraction(pages))
    got, cont = owners(result), conts(result)
    assert got["1.3"] == "A"
    assert got["2.1"] == "A/ст1/1" and cont["2.1"] is True
    assert got["2.2"] == "A/ст1/2"


def test_requisite_block_opens_only_on_short_unterminated_lines():
    base = [("Text", "1. Утвердить Правила."), ("Text", "2. Установить, что:")]
    tail = ("Text", "Расходы осуществляются за счет бюджета.")
    for line in [("Text", "Руководитель органа обеспечивает исполнение."),
                 ("Text", "Руководитель органа обеспечивает исполнение настоящего пункта."),
                 ("Text", "Председатель комиссии утверждает состав рабочей группы."),
                 ("Text", "в пределах ассигнований;", 900),
                 ("Text", "2019 2020 2021")]:
        got = owners(S.build(extraction([base + [line, tail]])))
        assert got["1.2"] == "A/2" and got["1.3"] == "A/2", line
    for text in ("Председатель комиссии утверждает состав рабочей группы.", "Министр вправе изменить сроки.",
                 "2019 2020 2021", "123456789"):
        assert not S.requisite_like(text), text
    # an agreement signature place is a requisite from text alone
    assert S.requisite_like("За Правительство Российской Федерации")
    assert S.requisite_like("За Российскую Федерацию")
    pages = [[("Section-header", "Статья 1"), ("Text", "Соглашение вступает в силу."),
              ("Text", "За Правительство Российской Федерации"), ("Text", "Подпись")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/ст1" and got["1.2"] == "A" and got["1.3"] == "A"
    # a barcode-like digit line that is not the last line of its page stays with its point
    pages = [[("Text", "1. Утвердить Правила."), ("Text", "2 100039 06204 3"), ("Text", "2. Второй.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/1"


LAW_TITLE = '"О бюджете Фонда социального страхования Российской Федерации на 2019 год и на плановый период 2020 и 2021 годов"'


def test_law_annex_caption_opens_annex_of_the_act():
    # «Приложение N к Федеральному закону "…"»: a long body caption (no «УТВЕРЖДЕН») after the
    # signer block opens annex N of the act; the signer block stays with the act root.
    caption = f"Приложение {{n}}\nк Федеральному закону\n{LAW_TITLE}"
    assert len(S.view(caption.format(n=1))) > 120
    pages = [[("Section-header", "Статья 1"), ("Text", "1. Утвердить перечень согласно приложению 1 "
                                                       "к настоящему Федеральному закону."),
              ("Text", "2. Утвердить источники согласно приложению 2 к настоящему Федеральному закону."),
              ("Text", "Президент Российской Федерации В.Путин", 580),
              ("Text", "Москва, Кремль 28 ноября 2018 года № 431-ФЗ")],
             [("Text", caption.format(n=1), 900), ("Section-header", "Перечень главных администраторов"),
              ("Table", "<table><tr><td>100</td></tr></table>")],
             [("Text", caption.format(n=2), 900), ("Section-header", "Источники финансирования"),
              ("Text", "(тыс. рублей)"), ("Table", "<table><tr><td>394</td></tr></table>")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/ст1/ч1" and got["1.3"] == "A" and got["1.4"] == "A"
    assert [got[f"2.{k}"] for k in range(3)] == ["A/AN1"] * 3
    assert [got[f"3.{k}"] for k in range(4)] == ["A/AN2"] * 4


def test_annex_caption_to_attached_document_opens_its_annex():
    # «Приложение к Порядку …» after the approved Порядок: annex of the attached document
    # (S/AN), with no «УТВЕРЖДЕН»; a later «Приложение № 2 к приказу …» is an annex of the act.
    caption = ("Приложение\nк Порядку составления и утверждения\nплана финансово-хозяйственной деятельности\n"
               "федеральных государственных учреждений\nнаходящихся в ведении Федеральной службы\n"
               "по надзору в сфере образования и науки,\nутвержденному приказом Рособрнадзора")
    assert len(S.view(caption)) > 120
    pages = [[("Text", "1. Утвердить прилагаемый Порядок."), ("Text", "2. Контроль оставляю за собой."),
              ("Text", "Министр", 1200)],
             [("Page-header", "Приложение", 1100), ("Text", "УТВЕРЖДЕН\nприказом Федеральной службы", 1000),
              ("Title", "Порядок составления плана"), ("Section-header", "I. Общие положения"),
              ("Text", "1. Рекомендуемый образец Плана приведен в приложении к настоящему Порядку."),
              ("Text", "2. План утверждается руководителем.")],
             [("Text", caption, 900), ("Text", 'от "___" ______ 2020 г. № ______'),
              ("Text", "Рекомендуемый образец"), ("Section-header", "Раздел I. Поступления и выплаты"),
              ("Table", "<table><tr><td>1</td></tr></table>")],
             [("Text", "Приложение № 2\nк приказу Федеральной службы\nот 12 мая 2020 г.", 900),
              ("Text", "1. Первая позиция.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "S/I/1" and got["2.5"] == "S/I/2"
    assert got["3.0"] == "S/AN" and got["3.1"] == "S/AN" and got["3.2"] == "S/AN"
    assert got["3.3"] == "S/AN/I" and got["3.4"] == "S/AN/I"
    assert got["4.0"] == "A/AN2" and got["4.1"] == "A/AN2/1"


ORDER_CAPTION = "Приложение № {n}\nк приказу Министерства\nот 11 февраля 2019 г. № 90"
RULES_CAPTION = "Приложение № {n}\nк Правилам проведения испытаний\nгенерирующего оборудования"


def order_with_rules_annexes():
    """An order approving Rules («Приложение № 1 к приказу») with their own annexes («Приложение № 1-2 к
    Правилам …») and a second attached document («Приложение № 2 к приказу»)."""
    return [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить прилагаемые Правила и изменения."),
             ("Text", "2. Настоящий приказ вступает в силу."), ("Text", "Министр", 1200)],
            [("Page-header", ORDER_CAPTION.format(n=1), 1000), ("Section-header", "ПРАВИЛА проведения испытаний"),
             ("Section-header", "I. Общие положения"), ("Text", "1. Правила устанавливают порядок."),
             ("Text", "2. Термины приведены в приложении № 1 к настоящим Правилам.")],
            [("Page-header", RULES_CAPTION.format(n=1), 1000), ("Section-header", "Термины и определения"),
             ("Text", "1. Испытание - проверка оборудования.")],
            [("Text", RULES_CAPTION.format(n=2), 1000), ("Text", "Форма"), ("Text", "Акт испытаний"),
             ("Text", "Подписи членов комиссии:")],
            [("Page-header", ORDER_CAPTION.format(n=2), 1000), ("Section-header", "ИЗМЕНЕНИЯ"),
             ("Text", "1. Пункт 5 изложить в новой редакции.")]]


def test_annexes_of_rules_attached_as_an_order_annex_belong_to_the_rules():
    """Cycle 7 B1 (Review Focus 1): Rules attached as «Приложение № 1 к приказу» have their own annexes «Приложение
    № N к Правилам …» (`<rules>/AN<n>`), not act annexes with the same numbers; «Приложение № 2 к приказу» after
    them opens the next attached document as before."""
    result = S.build(extraction(order_with_rules_annexes()))
    got = owners(result)
    assert got["2.0"] == got["2.1"] == "A/AN1" and got["2.3"] == "A/AN1/I/1" and got["2.4"] == "A/AN1/I/2"
    assert got["3.0"] == got["3.1"] == "A/AN1/AN1" and got["3.2"] == "A/AN1/AN1/1"
    assert [got[f"4.{k}"] for k in range(4)] == ["A/AN1/AN2"] * 4
    assert got["5.0"] == got["5.1"] == "A/AN2" and got["5.2"] == "A/AN2/1"
    # gold names the Rules `S` and the changes `S2`: under the attached ordinal both match, no transfer
    gold = {"2.0": "S", "2.3": "S/I/1", "3.0": "S/AN1", "3.2": "S/AN1/1", "4.0": "S/AN2", "4.3": "S/AN2",
            "5.0": "S2", "5.2": "S2/1", "1.1": "A/1"}
    gold = {k: {"owners": [v], "continuation": False} for k, v in gold.items()}
    res = EVAL.evaluate(gold, got, None, single_annex=True, attached_ordinal=True)
    assert res["strict"]["correct"] == len(gold)


def test_act_annexes_and_document_annexes_without_an_order_annex_are_unchanged():
    """Negative controls: annexes «к приказу» stay act annexes in sequence; a document annex opened directly in the
    act («Приложение № 1 к СП …», no «к приказу» annex before it) does not make the next one nested; a bare
    «Приложение № 3» after a Rules annex is an act annex as before."""
    pages = order_with_rules_annexes()
    pages[2][0] = ("Page-header", ORDER_CAPTION.format(n=2), 1000)
    pages[3][0] = ("Text", ORDER_CAPTION.format(n=3), 1000)
    pages[4][0] = ("Page-header", ORDER_CAPTION.format(n=4), 1000)
    got = owners(S.build(extraction(pages)))
    assert [got[f"{n}.0"] for n in range(2, 6)] == ["A/AN1", "A/AN2", "A/AN3", "A/AN4"]
    pages = [[("Text", "1. Правила применяются.")]]
    pages += [[("Page-header", f"Приложение № {n} к СП 2.1.3684-21", 1000), ("Text", "1. Первый пункт.")]
              for n in range(1, 4)]
    got = owners(S.build(extraction(pages)))
    assert [got[f"{n}.0"] for n in range(2, 5)] == ["A/AN1", "A/AN2", "A/AN3"]
    pages = order_with_rules_annexes()
    pages[4][0] = ("Page-header", "Приложение № 3", 1000)
    got = owners(S.build(extraction(pages)))
    assert got["3.0"] == "A/AN1/AN1" and got["5.0"] == "A/AN3" and got["5.2"] == "A/AN3/1"



def test_act_annex_inside_an_approved_text_does_not_take_the_approved_text_annexes():
    """Cycle 7 final review: after «УТВЕРЖДЕН … ПОРЯДОК» an act annex (a form «Приложение № 1 к приказу») does not
    make the next «Приложение № 1 к Порядку …» its annex: that one is an annex of the approved text (`S/AN1`, as
    v5); only an act annex opened before any approved text nests the document annexes after it."""
    pages = ordered_porydok(("Text", "2. Второй пункт."))
    pages.append([("Page-header", ORDER_CAPTION.format(n=1), 1000), ("Text", "(форма)"), ("Text", "Заявление")])
    pages.append([("Page-header", "Приложение № 1\nк Порядку проведения проверки", 1000),
                  ("Text", "1. Позиция приложения.")])
    got = owners(S.build(extraction(pages)))
    assert got["3.0"] == "A/AN1"
    assert got["4.0"] == "S/AN1" and got["4.1"] == "S/AN1/1"


COORDINATES = ("Table", "<table><tr><th>Номера точек</th><th>X</th></tr><tr><td>1</td><td></td></tr></table>")


def form_with_numbered_lines(*lines):
    """Requirements with a form annex: a sentence, numbered lines ``lines``, then a caption, tables, a scheme line,
    a stamp and a list of the form's plans on the next page."""
    return [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить прилагаемые Требования."), ("Text", "Руководитель", 1200)],
            [("Text", "УТВЕРЖДЕНЫ\nприказом Федеральной службы", 1000), ("Title", "ТРЕБОВАНИЯ"),
             ("Text", "1. Требования устанавливают форму акта.")],
            [("Text", "Приложение № 1\nк Требованиям к содержанию проекта", 1000), ("Text", "(форма)"),
             ("Section-header", "ГОРНООТВОДНЫЙ АКТ"),
             ("Text", "Пользователь недр несет ответственность за соблюдение требований:"), *lines,
             ("Caption", "Координаты угловых точек горного отвода"), COORDINATES,
             ("Text", "План (схема) границ горного отвода:"), COORDINATES, ("Text", "М.П.")],
            [("Text", "Приложения:"), ("Text", "План горного отвода, масштаб: ____________"),
             ("Text", "Разрезы (профили), масштаб: ____________")]]


def test_text_after_numbered_fill_in_lines_of_a_form_belongs_to_the_form():
    """Cycle 7 B2 (Review Focus 2, batch-7 gold): the blank lines «1. ___», «2. ___» of a form are its points, but
    they hold no text, so the caption, tables, scheme line, stamp and the list «Приложения: …» after them belong to
    the form itself, not to the last blank line."""
    got = owners(S.build(extraction(form_with_numbered_lines(("Text", "1. __________"), ("Text", "2. __________")))))
    assert got["3.0"] == got["3.3"] == "S/AN1"
    assert got["3.4"] == "S/AN1/1" and got["3.5"] == "S/AN1/2"
    assert [got[f"3.{k}"] for k in range(6, 11)] == ["S/AN1"] * 5
    assert [got[f"4.{k}"] for k in range(3)] == ["S/AN1"] * 3
    assert S.fill_in_line("2. __________") and S.fill_in_line("3) ....... ") and S.fill_in_line("4. _____ ______")
    assert not S.fill_in_line("2. Координаты: ______") and not S.fill_in_line("__________")


def test_text_after_a_numbered_point_with_its_own_text_stays_in_the_point():
    """Negative controls: a numbered line with text keeps the caption, tables and lines after it; a blank line followed
    by a point with text does not move that point's tables."""
    pages = form_with_numbered_lines(("Text", "1. __________"), ("Text", "2. Координаты определяются в системе МСК."))
    got = owners(S.build(extraction(pages)))
    assert got["3.4"] == "S/AN1/1" and got["3.5"] == "S/AN1/2"
    assert [got[f"3.{k}"] for k in range(6, 10)] == ["S/AN1/2"] * 4
    # step 13 B3: the stamp «М.П.» opens the form's requisite block; what follows it belongs to the form
    assert got["3.10"] == "S/AN1" and [got[f"4.{k}"] for k in range(3)] == ["S/AN1"] * 3


GEO_TABLE = ("Table", "<table><tr><th>Номера точек</th><th>Северная широта *</th><th>Восточная долгота**</th></tr>"
                      "<tr><td>1</td><td></td><td></td></tr></table>")


def test_asterisk_footnotes_belong_to_the_marked_table_on_their_page():
    """Cycle 7 B3 (Review Focus 3): footnotes «*- …», «**- …» under a table whose header prints «*», «**» belong to
    that table's owner (the form), not to nobody."""
    pages = form_with_numbered_lines(("Text", "1. __________"))
    pages[2][-1:] = [GEO_TABLE, ("Footnote", "*- с точностью до 10 см;"),
                     ("Footnote", "**- с точностью до 2-х знаков после запятой.")]
    got = owners(S.build(extraction(pages)))
    assert got["3.9"] == got["3.10"] == got["3.11"] == "S/AN1"
    assert S.ASTERISK_NOTE.match("*- с точностью") and S.ASTERISK_NOTE.match("** Сноска")
    assert not S.ASTERISK_NOTE.match("****") and not S.ASTERISK_NOTE.match("*")


def test_asterisk_footnote_without_its_mark_on_the_page_stays_unowned():
    """Negative controls: «*» only inside «**», or a mark only on an earlier page, owns no footnote «* …»."""
    pages = form_with_numbered_lines(("Text", "1. __________"))
    pages[2][-1:] = [("Table", "<table><tr><th>Восточная долгота**</th></tr></table>"),
                     ("Footnote", "* с точностью до 10 см;")]
    assert owners(S.build(extraction(pages)))["3.10"] == "S/AN1"  # step 21.3 F: no mark -> the document of its page (gold never leaves a footnote ownerless)
    pages = form_with_numbered_lines(("Text", "1. __________"))
    pages[2][-1:] = [GEO_TABLE]
    pages[3].append(("Footnote", "*- с точностью до 10 см;"))
    assert owners(S.build(extraction(pages)))["4.3"] is not None  # step 21.3 F: no mark -> the document of its page (gold never leaves a footnote ownerless)



def test_markdown_emphasis_is_not_an_asterisk_footnote_mark():
    """Cycle 7 final review: OCR markdown emphasis («*курсив*», «**Примечание**») is not an asterisk mark: an italic
    body line owns no «* …» footnote, and a bold «**Примечание**» footnote stays unowned."""
    pages = form_with_numbered_lines(("Text", "1. __________"))
    pages[2][-1:] = [("Text", "*Заполняется заявителем*"), ("Footnote", "* с точностью до 10 см;")]
    assert owners(S.build(extraction(pages)))["3.10"] == "S/AN1"  # step 21.3 F: no mark -> the document of its page (gold never leaves a footnote ownerless)
    pages = form_with_numbered_lines(("Text", "1. __________"))
    pages[2][-1:] = [GEO_TABLE, ("Footnote", "**Примечание**: координаты приводятся в МСК.")]
    assert owners(S.build(extraction(pages)))["3.10"] is not None  # step 21.3 F: no mark -> the document of its page (gold never leaves a footnote ownerless)
    assert S.strip_emphasis("*Заполняется* заявителем**") == "Заполняется заявителем**"
    assert S.strip_emphasis("Северная широта *") == "Северная широта *"


def form_with_signatures(last):
    return [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить прилагаемые Правила."), ("Text", "Министр", 1200)],
            [("Text", "УТВЕРЖДЕНЫ\nприказом Министерства", 1000), ("Title", "ПРАВИЛА"),
             ("Text", "1. Правила устанавливают форму акта.")],
            [("Text", "Приложение № 1\nк Правилам проведения испытаний", 1000), ("Text", "ФОРМА"),
             ("Section-header", "Акт о результатах опробования"), ("Text", "1. Основание назначения комиссии:"),
             ("Text", "2. Решение рабочей комиссии:"), ("Text", "Генерирующее оборудование"),
             ("Text", "успешно прошло комплексное опробование"), ("Text", last)]]


def test_signature_heading_of_a_form_after_its_last_point_belongs_to_the_form():
    """Cycle 7 B3 (Review Focus 3): «Подписи членов рабочей комиссии:» after the last point of a form opens its
    signature block (form root), as the agreement heading «Подписи и реквизиты Сторон» does."""
    got = owners(S.build(extraction(form_with_signatures("Подписи членов рабочей комиссии:"))))
    assert got["3.4"] == "S/AN1/2" and got["3.6"] == "S/AN1/2" and got["3.7"] == "S/AN1"
    assert S.requisite_like("Подписи членов комиссии:") and S.requisite_like("Подпись руководителя:")


def test_sentence_about_signatures_in_the_last_point_stays_in_the_point():
    """Negative controls: a sentence about signatures, or a long colon line, stays in the last point."""
    for line in ("Подписи членов комиссии ставятся на каждом листе акта.",
                 "Подписи членов комиссии, а также их должности и фамилии, приводятся в акте в следующем порядке:"):
        got = owners(S.build(extraction(form_with_signatures(line))))
        assert got["3.7"] == "S/AN1/2", line
        assert not S.requisite_like(line), line


def test_annex_reference_inside_a_sentence_opens_no_annex():
    pages = [[("Text", "1. Утвердить Порядок."), ("Text", "2. Контроль оставляю за собой.")],
             [("Text", "УТВЕРЖДЕН\nприказом Федеральной службы", 1000), ("Section-header", "I. Общие положения"),
              ("Text", "1. Образец приведен в приложении к настоящему Порядку."),
              ("Text", "согласно приложению 1 к Федеральному закону, и в приложении к Правилам."),
              ("Text", f"Приложение 1 к Федеральному закону {LAW_TITLE} применяется в части, "
                       "не противоречащей настоящему Порядку."),
              ("Text", "Приложение к Порядку утверждается руководителем учреждения."),
              ("Text", "2. План утверждается руководителем.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.2"] == "S/I/1"
    assert got["2.3"] == "S/I/1" and got["2.4"] == "S/I/1" and got["2.5"] == "S/I/1"
    assert got["2.6"] == "S/I/2"
    assert not any(owner and "/AN" in owner for owner in got.values())


def ordered_porydok(*tail, approved_by="приказом Министерства"):
    return [[("Text", "1. Утвердить прилагаемый Порядок."), ("Text", "Министр", 1200)],
            [("Text", f"УТВЕРЖДЕН\n{approved_by}", 1000), ("Section-header", "I. Общие положения"),
             ("Text", "1. Первый пункт."), *tail]]


def test_act_word_referent_names_the_act_only_for_its_own_kind():
    # R1a: in a resolution, «к приказу Минфина …» names a foreign act: annex of the attached document
    pages = ordered_porydok(("Text", "Приложение № 2 к приказу Минфина России от 12 мая 2020 г. № 5н", 900),
                            ("Text", "1. Позиция формы."), approved_by="постановлением Правительства")
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "S/AN2" and got["2.4"] == "S/AN2/1"
    # the act kind can also come from the act header line
    pages[0].insert(0, ("Title", "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ\nПОСТАНОВЛЕНИЕ"))
    pages[1][0] = ("Text", "УТВЕРЖДЕН", 1000)
    assert owners(S.build(extraction(pages)))["2.3"] == "S/AN2"
    # R1b: in an order, «к приказу …» names the act itself
    pages = ordered_porydok(("Text", "Приложение № 1\nк приказу Министерства\nот 12 мая 2020 г. № 5", 900),
                            ("Text", "1. Позиция."))
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "A/AN1" and got["2.4"] == "A/AN1/1"
    # «к настоящему постановлению» names the act whatever the approval caption says
    pages = ordered_porydok(("Text", "Приложение № 3 к настоящему постановлению", 900), ("Text", "1. Позиция."))
    assert owners(S.build(extraction(pages)))["2.3"] == "A/AN3"


def test_bare_annex_number_needs_evidence():
    # R2a: a bare «Приложение 2» line between points opens nothing
    got = owners(S.build(extraction(ordered_porydok(("Text", "Приложение 2"), ("Text", "2. Второй пункт.")))))
    assert got["2.3"] == "S/I/1" and got["2.4"] == "S/I/2"
    # R2b: a broken sentence starting with a caption-like phrase opens nothing
    sentence = ("Text", "Приложение 3 к настоящему Порядку содержит перечень форм, которые")
    got = owners(S.build(extraction(ordered_porydok(sentence, ("Text", "2. Второй пункт.")))))
    assert got["2.3"] == "S/I/1" and got["2.4"] == "S/I/2"
    # evidence: the reference in the next paragraph, or the first body line of a page
    pages = ordered_porydok(("Text", "Приложение 2", 1000), ("Text", "к Порядку", 1000), ("Text", "1. Строка."))
    assert owners(S.build(extraction(pages)))["2.5"] == "S/AN2/1"
    pages = ordered_porydok() + [[("Text", "Приложение 2", 1000), ("Title", "ФОРМА"), ("Text", "1. Строка.")]]
    assert owners(S.build(extraction(pages)))["3.2"] == "S/AN2/1"
    # a number sign is evidence enough: «№», Latin «N», Cyrillic «Н»
    for sign in ("№ ", "N ", "Н "):
        pages = ordered_porydok(("Text", f"Приложение {sign}2"), ("Text", "1. Строка."))
        assert owners(S.build(extraction(pages)))["2.4"] == "S/AN2/1", sign


def test_caption_final_dot_after_number_or_numeric_date():
    # R5: a caption may end in «№ 5н.» or a DD.MM.YYYY date with a dot
    for caption in ("Приложение № 1 к Порядку, утв. приказом от 01.02.2020 № 5н.",
                    "Приложение № 1 к Порядку, утвержденному приказом от 01.02.2020."):
        got = owners(S.build(extraction(ordered_porydok(("Text", caption, 900), ("Text", "1. Строка.")))))
        assert got["2.3"] == "S/AN1" and got["2.4"] == "S/AN1/1", caption


def regulation(*body):
    """An order approving a regulation; ``body`` follows the section heading «I. Общие положения»."""
    return [[("Text", "1. Утвердить прилагаемый Административный регламент."), ("Text", "Министр", 1200)],
            [("Text", "УТВЕРЖДЕН\nприказом Министерства", 1000), ("Section-header", "I. Общие положения"), *body]]


def test_unnumbered_subheading_inside_section_belongs_to_the_section():
    """Review Focus 5: an unmarked unterminated capitalised line after a finished paragraph and
    right before a numbered point is a subheading of the enclosing section, not text of the
    previous point or subpoint. Body-text (Text) subheadings of up to 200 characters count when the
    scope has two header-category ones; a Section-header subheading may be up to 500 characters."""
    long_heading = ("Исчерпывающий перечень документов, необходимых в соответствии с нормативными правовыми "
                    "актами для предоставления государственной услуги и услуг, которые являются необходимыми "
                    "и обязательными для предоставления государственной услуги, подлежащих представлению "
                    "заявителем, способы их получения заявителем, в том числе в электронной форме")
    assert len(long_heading) > 250
    pages = regulation(("Section-header", "Предмет регулирования"), ("Text", "1. Регламент устанавливает порядок."),
                       ("Section-header", "Круг заявителей"), ("Text", "2. Заявителями являются:"),
                       ("Text", "1) юридические лица;"), ("Text", "2) индивидуальные предприниматели."),
                       ("Text", "Требования к порядку информирования"), ("Text", "3. Информация размещается."),
                       ("Section-header", "II. Стандарт"), ("Text", "4. Услугой является ведение реестра."),
                       ("Section-header", long_heading), ("Text", "5. Для получения услуги представляются:"),
                       ("Text", "а) заявление;"), ("Text", "б) договор."),
                       ("Text", "Сроки рассмотрения"), ("Text", "Порядок обжалования"),
                       ("Text", "6. Срок составляет 5 дней."))
    got = owners(S.build(extraction(pages)))
    assert got["2.2"] == "S/I" and got["2.3"] == "S/I/1"
    assert got["2.4"] == "S/I" and got["2.5"] == "S/I/2"            # not S/I/1
    assert got["2.6"] == "S/I/2/1" and got["2.7"] == "S/I/2/2"
    assert got["2.8"] == "S/I" and got["2.9"] == "S/I/3"            # not S/I/2/2
    assert got["2.10"] == "S/II" and got["2.11"] == "S/II/4"
    assert got["2.12"] == "S/II" and got["2.13"] == "S/II/5"        # a long subheading
    assert got["2.16"] == "S/II" and got["2.17"] == "S/II"          # two subheading lines in a row
    assert got["2.18"] == "S/II/6"
    # a body-text line over 200 characters is not a subheading without heading evidence (here the scope has only
    # one header-category subheading run before a point, so it is not corroborated; step 13 B1 needs both)
    pages[1][12] = ("Text", long_heading)
    assert owners(S.build(extraction(pages)))["2.12"] == "S/II/4"
    # without two header-category subheadings in the scope a body-text line stays with its point
    pages = regulation(("Text", "1. Регламент устанавливает порядок."), ("Text", "Круг заявителей"),
                       ("Text", "2. Заявителями являются юридические лица."))
    assert owners(S.build(extraction(pages)))["2.3"] == "S/I/1"


def test_unterminated_line_is_not_a_subheading_without_its_evidence():
    """Negative controls: a terminated sentence, a line after «:», a line before a table or before a
    subpoint stay with the open point."""
    pages = regulation(("Text", "1. Регламент устанавливает порядок."),
                       ("Text", "Количество взаимодействий ограничивается режимом работы."),   # terminated
                       ("Text", "2. Сведения указываются по форме:"),
                       ("Text", "Наименование организации"),                                   # after «:»
                       ("Text", "3. Показатели приведены ниже."),
                       ("Text", "Таблица 1"), ("Table", "<table><tr><td>1</td></tr></table>"),  # before a table
                       ("Text", "4. Документы представляются."),
                       ("Text", "Перечень документов"), ("Text", "1) заявление;"),             # before a subpoint
                       ("Text", "5. Графическое изображение приведено на схеме 1."),
                       ("Caption", "Схема 1"), ("Text", "6. Графическое изображение приведено на схеме 2."),
                       ("Text", "Схема 2"), ("Picture", ""), ("Text", "7. Последний пункт."))   # before a picture
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "S/I/1"
    assert got["2.5"] == "S/I/2"
    assert got["2.7"] == "S/I/3" and got["2.8"] == "S/I/3"
    assert got["2.10"] == "S/I/4" and got["2.11"] == "S/I/4/1"
    assert got["2.13"] == "S/I/5"                                    # an OCR Caption region
    assert got["2.15"] == "S/I/6"
    # without an enclosing section the line stays with the open point (an OCR-cut sentence)
    pages = [[("Text", "1. Утвердить порядок."), ("Text", "Проект вносится в Правительство в установленном порядке"),
              ("Text", "2. Контроль оставляю за собой.")]]
    assert owners(S.build(extraction(pages)))["1.1"] == "A/1"


def test_paragraph_after_last_subpoint_returns_to_the_point():
    """A capitalised paragraph after the last subpoint that does not continue the enumeration
    belongs to the point: the subpoint ended with «.», or it ended with «;» and the paragraph is a
    sentence of its own; later unmarked paragraphs stay with the point."""
    pages = regulation(("Text", "1. Должностные лица сообщают:"), ("Text", "1) о сроках;"),
                       ("Text", "2) об исполнителе."),
                       ("Text", "Время разговора не должно превышать 5 минут."),
                       ("Text", "Иные вопросы рассматриваются на основании обращения."),
                       ("Text", "2. Показатели формируются:"), ("Text", "а) по доходам;"),
                       ("Text", "б) по выплатам:"), ("Text", "по расходам;"), ("Text", "по налогам;"),
                       ("Text", "По решению руководителя показатели формируются с детализацией."),
                       ("Section-header", "II. Реорганизация"),
                       ("Text", "3. При реорганизации:"), ("Text", "а) в форме слияния;"),
                       ("Text", "б) в форме выделения."),
                       ("Text", "После завершения реорганизации показатели утверждаются."))
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "S/I/1/1" and got["2.4"] == "S/I/1/2"
    assert got["2.5"] == "S/I/1" and got["2.6"] == "S/I/1"
    assert got["2.9"] == "S/I/2/б" and got["2.10"] == "S/I/2/б" and got["2.11"] == "S/I/2/б"
    assert got["2.12"] == "S/I/2"
    assert got["2.17"] == "S/II/3"                 # the last subpoint before the end of the scope


def test_continued_enumeration_stays_in_the_subpoint():
    """Negative controls: a lowercase paragraph, a «;»-terminated item, text after «:» and a
    paragraph before the next subpoint of the same list stay in the subpoint."""
    pages = regulation(("Text", "1. Заявление содержит:"), ("Text", "1) сведения о заявителе;"),
                       ("Text", "в том числе его адрес;"),                                     # lowercase
                       ("Text", "2) сведения о туроператоре;"),
                       ("Text", "Сведения о членстве в объединении;"),                         # «;» item after «;»
                       ("Text", "3) реквизиты:"),
                       ("Text", "Наименование банка и номер счета."),                          # after «:»
                       ("Text", "4) подпись."),
                       ("Text", "Подпись проставляется руководителем."),                       # list continues
                       ("Text", "5) дату."),
                       ("Text", "2. Следующий пункт."))
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "S/I/1/1"
    assert got["2.6"] == "S/I/1/2"
    assert got["2.8"] == "S/I/1/3"
    assert got["2.10"] == "S/I/1/4" and got["2.11"] == "S/I/1/5"


def test_dotted_point_closes_an_open_subpoint():
    """«8.1» after subpoint «4)» of point 8 is subpoint 8.1 of point 8, not a child of «4)»."""
    pages = regulation(("Text", "8. Должностные лица сообщают:"), ("Text", "1) о сроках;"),
                       ("Text", "2) об исполнителе."), ("Text", "8.1 При предоставлении информации:"),
                       ("Text", "1) по письменному обращению;"), ("Text", "а) почтой;"),
                       ("Text", "8.2. Второй подпункт."))
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "S/I/8/2"
    assert got["2.5"] == "S/I/8/8.1" and got["2.6"] == "S/I/8/8.1/1" and got["2.7"] == "S/I/8/8.1/1/а"
    assert got["2.8"] == "S/I/8/8.2"


@pytest.mark.parametrize(("text", "kind", "label"), [
    ("ГЛАВА 1. ОБЩИЕ ПОЛОЖЕНИЯ", "chapter", "гл1"),
    ("ГЛАВА 2", "chapter", "гл2"),
    ("Глава ІХ. Заключительные положения", "chapter", "гл9"),
    ("ГЛАВА Х", "chapter", "гл10"),
    ("СТАТЬЯ 5. Предмет регулирования", "article", "ст5"),
    ("СТАТЬЯ 12.1", "article", "ст12.1"),
    ("ГЛАВА 3 настоящего Кодекса применяется к спорам.", "none", ""),
    ("СТАТЬЯ 17 закона применяется к отношениям.", "none", ""),
])
def test_uppercase_chapter_and_article_headings(text, kind, label):
    """Controller ruling (B3 review): uppercase «ГЛАВА»/«СТАТЬЯ» and OCR Roman letters (Х, І) in
    chapter numbers; a sentence that starts with the word stays text (heading_like)."""
    marker = S.parse_marker(text, "Text")
    assert (marker.kind, marker.label) == (kind, label)


def styled_regulation(*body):
    """A regulation whose subheading style is established by two Section-header subheadings."""
    return regulation(("Text", "1. Регламент устанавливает порядок."), ("Section-header", "Круг заявителей"),
                      ("Text", "2. Заявителями являются юридические лица."),
                      ("Section-header", "Требования к информированию"), ("Text", "3. Информация размещается."),
                      *body)


@pytest.mark.parametrize("line", ["Схема 2", "Рисунок 1 - Знак доступности", "Рис. 3", "Таблица 3",
                                  "Форма N 2", "Форма № 4", "Диаграмма 1", "График 2 - Динамика показателей"])
def test_figure_and_form_captions_by_text_are_not_subheadings(line):
    """Fix round 1: a caption recognised by its text (category Text, no Picture region) stays with
    the point that refers to it, even in a scope with an established subheading style."""
    got = owners(S.build(extraction(styled_regulation(("Text", "4. Изображение приведено ниже."), ("Text", line),
                                                      ("Text", "5. Следующий пункт.")))))
    assert got["2.2"] == "S/I/1" and got["2.4"] == "S/I/2"     # the style is there
    assert got["2.8"] == "S/I/4", line


def test_long_body_text_subheading_in_a_corroborated_scope():
    """Step 13 B1: with the subheading style established (two Section-header subheadings) a body-text rubric of
    an administrative regulation longer than 200 characters (FSB regulation: 206-892) is a subheading too, up to
    SUBHEADING_STYLED_MAX; longer, or without the style, it stays with the open point."""
    rubric = ("Показатели доступности и качества государственной услуги, в том числе количество взаимодействий "
              "заявителя с должностными лицами при предоставлении государственной услуги и их продолжительность, "
              "возможность получения информации о ходе предоставления государственной услуги, в том числе с "
              "использованием информационно-коммуникационных технологий")
    assert 200 < len(rubric) <= S.SUBHEADING_STYLED_MAX
    body = (("Text", "4. Помещения оборудуются пандусами."), ("Text", rubric),
            ("Text", "5. Показателями доступности являются:"))
    got = owners(S.build(extraction(styled_regulation(*body))))
    assert got["2.8"] == "S/I" and got["2.9"] == "S/I/5"
    too_long = rubric + ", " + "в том числе с учетом особенностей предоставления услуги " * 12 + "в электронной форме"
    assert len(too_long) > S.SUBHEADING_STYLED_MAX
    got = owners(S.build(extraction(styled_regulation(body[0], ("Text", too_long), body[2]))))
    assert got["2.8"] == "S/I/4"
    got = owners(S.build(extraction(regulation(("Text", "1. Регламент устанавливает порядок."), *body))))
    assert got["2.3"] == "S/I/4"                                    # no style in the scope


def test_cut_sentence_and_labelled_line_stay_with_the_point():
    """Fix round 1: an OCR-cut sentence (lost final dot, 130 characters) and a labelled value line
    («Адрес: …») before the next point stay with the open point."""
    cut = ("Жалоба подается в письменной форме на бумажном носителе или в электронной форме в орган, "
           "предоставляющий государственную услугу")
    got = owners(S.build(extraction(regulation(("Text", "1. Заявитель вправе подать жалобу."), ("Text", cut),
                                               ("Text", "2. Следующий пункт.")))))
    assert got["2.3"] == "S/I/1"
    for label in ("Адрес: г. Москва, ул. Тверская, д. 7", "Почтовый адрес: 101000, Москва",
                  "Телефон: 8 (495) 123-45-67"):
        got = owners(S.build(extraction(styled_regulation(("Text", "4. Справочные сведения приведены ниже."),
                                                          ("Text", label), ("Text", "5. Следующий пункт.")))))
        assert got["2.8"] == "S/I/4", label


def test_no_subpoint_closing_inside_a_quotation():
    """Fix round 1: amending text quoted inside a subpoint («изложить в следующей редакции: «3. …»»)
    stays in the subpoint, including its capitalised last paragraph ending «.».»."""
    pages = regulation(("Text", "1. Внести изменения:"), ("Text", "а) пункт 3 изложить в следующей редакции:"),
                       ("Text", "«3. Порядок утверждается министерством."),
                       ("Text", "Положение применяется с 1 января.»."), ("Text", "2. Следующий пункт."))
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "S/I/1/а" and got["2.5"] == "S/I/1/а" and got["2.6"] == "S/I/2"
    # a paragraph ending a quotation does not close even when the quotation opened in it
    pages = regulation(("Text", "1. Внести изменения:"), ("Text", "а) в пункте 2 слова заменить."),
                       ("Text", "Пункт 4 дополнить словами «и иные документы»."), ("Text", "2. Следующий пункт."))
    assert owners(S.build(extraction(pages)))["2.4"] == "S/I/1/а"


def test_split_proper_noun_and_dash_items_after_a_closed_subpoint():
    """Pinned behaviour: a subpoint cut before «Российской Федерации.» (unterminated previous line)
    stays in the subpoint; dash items after a closing paragraph follow the point."""
    pages = regulation(("Text", "1. Заявление содержит:"), ("Text", "а) сведения о заявителе;"),
                       ("Text", "б) сведения, предусмотренные законодательством"), ("Text", "Российской Федерации."),
                       ("Text", "2. Состав:"), ("Text", "а) первый;"), ("Text", "б) второй."),
                       ("Text", "Кроме того, включаются следующие лица."), ("Text", "- эксперты;"),
                       ("Text", "3. Следующий пункт."))
    got = owners(S.build(extraction(pages)))
    assert got["2.5"] == "S/I/1/б"
    assert got["2.9"] == "S/I/2" and got["2.10"] == "S/I/2"


def test_known_limitations_are_pinned():
    """Known limitations (docs/AGENTS.md): a subheading after a table or after an editorial note
    stays with the previous point; a capitalised second paragraph of the last subpoint goes to the point."""
    got = owners(S.build(extraction(styled_regulation(
        ("Text", "4. Показатели приведены в таблице."), ("Table", "<table><tr><td>1</td></tr></table>"),
        ("Section-header", "Сроки предоставления услуги"), ("Text", "5. Срок составляет 5 дней."),
        ("Text", "(в ред. Приказа Минкультуры России от 01.02.2020 N 5)"),
        ("Section-header", "Порядок обжалования"), ("Text", "6. Жалоба подается в письменной форме.")))))
    assert got["2.9"] == "S/I/4" and got["2.12"] == "S/I/5"
    pages = regulation(("Text", "1. Заявление содержит:"), ("Text", "а) сведения о заявителе;"),
                       ("Text", "б) сведения о документе."), ("Text", "Российской Федерации гражданам выдается справка."),
                       ("Text", "2. Следующий пункт."))
    assert owners(S.build(extraction(pages)))["2.5"] == "S/I/1"


TABLE = ("Table", "<table><tr><td>Шифр</td><td>Затраты</td></tr></table>")


def estimate_norms(*body):
    """An order approving estimate norms: general points, then «РАЗДЕЛ 1.» with tables."""
    return [[("Text", "1. Утвердить прилагаемые нормативы."), ("Text", "Министр", 1200)],
            [("Text", "УТВЕРЖДЕНЫ\nприказом Министерства", 1000), ("Section-header", "Сметные нормативы"),
             ("Text", "1. Нормативы применяются при ремонте."), ("Text", "2. Нормативы определены в ценах 2014 г."),
             ("Section-header", "РАЗДЕЛ 1. Ремонт земляного полотна"), *body]]


@pytest.mark.parametrize("text", ["01. Планировка грунта.", "02) Разборка конструкций.", "001. Прием грунта."])
def test_leading_zero_marker_is_a_list_line(text):
    assert S.parse_marker(text, "List-item").kind == "none"
    assert S.leading_zero_list(text)


@pytest.mark.parametrize("text, kind", [("1. Пункт.", "int"), ("10. Пункт.", "int"), ("2) подпункт;", "paren"),
                                        ("1.1 Подпункт.", "decimal")])
def test_ordinary_markers_are_unchanged(text, kind):
    assert S.parse_marker(text, "Text").kind == kind and not S.leading_zero_list(text)


def test_leading_zero_lists_under_tables_stay_in_the_section():
    """Review Focus 3 (owner decision 23.10.2026: no table node): «Состав работ: 01., 02.» under each
    table is text of the enclosing unit; a later list does not nest into the previous one, and «10.»
    right after «09.» continues the zero-padded list."""
    pages = estimate_norms(
        ("Section-header", "Таблица 01-01-001"), ("Text", "Устройство подстилающего слоя"),
        ("Text", "Состав работ:"), ("Text", "01. Планировка земляного полотна."),
        ("Text", "02. Распределение песка."), ("Text", "Измеритель: 100 м³"), TABLE,
        ("Section-header", "Таблица 01-01-002"), ("Text", "Состав работ:"),
        *[("List-item", f"{n:02d}. Операция {n}.") for n in range(1, 13)], TABLE,
        ("Text", "Стоимостные показатели"))
    got = owners(S.build(extraction(pages)))
    assert got["2.2"] == "S/1" and got["2.3"] == "S/2" and got["2.4"] == "S/разд1"
    for key in ["2.5", "2.6", "2.7", "2.8", "2.9", "2.10", "2.11", "2.12", "2.13"]:
        assert got[key] == "S/разд1", key
    for index in range(14, 26):            # 01. … 09., then 10. 11. 12.
        assert got[f"2.{index}"] == "S/разд1", index
    assert got["2.26"] == "S/разд1"        # the table after the list
    # ordinary numbering still works in the same document: «3.» after «2.» before the section
    pages[1].insert(4, ("Text", "3. Нормативы отражают среднеотраслевой уровень."))
    assert owners(S.build(extraction(pages)))["2.4"] == "S/3"


def test_ten_after_a_non_list_line_stays_a_point():
    pages = regulation(("Text", "9. Девятый пункт."), ("Text", "10. Десятый пункт."),
                       ("Text", "Состав работ:"), ("Text", "01. Планировка."), ("Text", "Измеритель: 1 м³"),
                       ("Text", "11. Одиннадцатый пункт."))
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "S/I/10" and got["2.5"] == "S/I/10" and got["2.7"] == "S/I/11"


def test_next_point_after_a_short_zero_padded_list_stays_a_point():
    """v3.1: only a digit rollover («10.» after «09.») continues a zero-padded list; «5.» after a list
    «01.»…«04.» inside point «4.» is the next point, not a list line."""
    points = [("Text", f"{n}. Пункт {n}.") for n in range(1, 5)]
    listed = [("Text", f"{n:02d}. Операция {n}.") for n in range(1, 5)]
    pages = regulation(*points, *listed, ("Text", "5. Пункт"), ("Text", "6. Пункт шестой."))
    got = owners(S.build(extraction(pages)))
    assert [got[f"2.{k}"] for k in range(6, 10)] == ["S/I/4"] * 4
    assert got["2.10"] == "S/I/5" and got["2.11"] == "S/I/6"
    assert S.continues_list((".", 10), (".", 9, False)) and S.continues_list((".", 11), (".", 10, True))
    assert S.continues_list((".", 100), (".", 99, False))
    assert not S.continues_list((".", 5), (".", 4, False)) and not S.continues_list((")", 10), (".", 9, False))


@pytest.mark.parametrize("separator", [TABLE, ("Section-header", "Порядок расчета")])
def test_restarted_numbering_takes_the_level_of_the_last_point(separator):
    """Review Focus 4: «1.» after «N.» (N > 1) of the same scope, with a table or an unmarked heading
    between them, restarts at the level of «N.» instead of nesting into it."""
    pages = estimate_norms(("Text", "5. Затраты учтены в таблицах."), ("Text", "6. Показатели приведены ниже."),
                           separator, ("Text", "1. Первый показатель."), ("Text", "2. Второй показатель."))
    got = owners(S.build(extraction(pages)))
    assert got["2.5"] == "S/разд1/5" and got["2.6"] == "S/разд1/6"
    assert got["2.8"] == "S/разд1/1" and got["2.9"] == "S/разд1/2"
    pages = regulation(("Text", "1. Первый."), ("Text", "2. Второй."), ("Text", "3. Третий."), separator,
                       ("Text", "1. Снова первый."), ("Text", "2. Снова второй."))
    got = owners(S.build(extraction(pages)))
    assert got["2.6"] == "S/I/1" and got["2.7"] == "S/I/2"


def test_restart_needs_a_break_and_leaves_subpoints_nested():
    """Negative controls: without a table or heading «1.» after «3.» keeps the old reading; real «1)»
    subpoints and «3.1» after a table stay inside the point; «1.» after «1.» is not a restart."""
    pages = regulation(("Text", "1. Первый."), ("Text", "2. Второй."), ("Text", "3. Третий:"),
                       ("Text", "1. вложенный."))
    assert owners(S.build(extraction(pages)))["2.5"] == "S/I/3/1"
    pages = regulation(("Text", "1. Первый."), ("Text", "2. Показатели:"), TABLE, ("Text", "1) первый;"),
                       ("Text", "2) второй."), ("Text", "3. Третий:"), TABLE, ("Text", "3.1. Подпункт."))
    got = owners(S.build(extraction(pages)))
    assert got["2.5"] == "S/I/2/1" and got["2.6"] == "S/I/2/2"
    assert got["2.9"] == "S/I/3/3.1"
    pages = regulation(("Text", "1. Первый."), TABLE, ("Text", "1. Снова первый."))
    result = S.build(extraction(pages))
    assert not any("restart" in e for p in result["paragraphs"] for e in p["evidence"])


def test_right_aligned_line_between_tables_is_not_a_signature():
    """A short right-aligned line between two tables («Стоимостные показатели») labels the table part and
    follows the current unit; the same line after the last table or before text is still a signature."""
    pages = estimate_norms(("Text", "Состав работ:"), ("Text", "01. Планировка."), TABLE,
                           ("Text", "Стоимостные показатели", 1100), TABLE,
                           ("Text", "Норма расхода ресурсов", 1100), ("Picture", ""), TABLE)
    got = owners(S.build(extraction(pages)))
    assert got["2.8"] == "S/разд1" and got["2.9"] == "S/разд1"
    assert got["2.10"] == "S/разд1" and got["2.12"] == "S/разд1"     # a picture in between does not count
    pages = regulation(("Text", "1. Первый пункт."), TABLE, ("Text", "Подпись", 1100), ("Text", "2. Второй пункт."))
    assert owners(S.build(extraction(pages)))["2.4"] == "S"


@pytest.mark.parametrize("text, owner", [("200716A9.doc", "S"), ("Proekt_2020.DOCX", "S"),
                                         ("Подкомиссия собирается ежегодно", "S/ст2")])
def test_file_code_in_a_page_footer_belongs_to_the_scope_root(text, owner):
    """A file code printed once or twice in a footer is a page mark of the scope root, not text of the
    article it follows, and opens no continuation; other footer text is unchanged."""
    pages = [[("Text", "1. Подписать Протокол."), ("Text", "Председатель Правительства", 1100)],
             [("Page-header", "Проект", 1200), ("Section-header", "ПРОТОКОЛ"), ("Section-header", "Статья 1"),
              ("Text", "Стороны сотрудничают."), ("Section-header", "Статья 2"), ("Text", "Подкомиссия проводит"),
              ("Page-footer", text)],
             [("Text", "заседания поочередно."), ("Section-header", "Статья 3"), ("Text", "Протокол вступает в силу.")]]
    result = S.build(extraction(pages))
    got = owners(result)
    assert got["2.6"] == owner
    assert got["3.0"] == "S/ст2" and conts(result)["3.0"] is True   # joins the article text, not the footer


def program_with_table_annex(*annex):
    """An order approving a programme whose annex 1 is the table of measures given by ``annex``."""
    return [[("Text", "1. Утвердить прилагаемую Программу."), ("Text", "Председатель Правительства", 1100)],
            [("Text", "УТВЕРЖДЕНА\nраспоряжением Правительства", 1000), ("Title", "ПРОГРАММА развития"),
             ("Text", "1. Программа определяет цели."), ("Text", "2. Мероприятия приведены в приложении № 1.")],
            [("Section-header", "ПРИЛОЖЕНИЕ № 1\nк Программе развития отрасли", 900),
             ("Section-header", "ПЕРЕЧЕНЬ мероприятий Программы"), ("Text", "(млрд. рублей)"), *annex]]


MEASURES = ("Table", "<table><thead><tr><th>Наименование мероприятия</th><th>Исполнитель</th></tr></thead></table>")


def test_rubrics_and_row_numbers_inside_a_table_annex_are_annex_text():
    """Cycle 5 B1 (owner decision 23.10.2026, convention v2 §6): in an annex that opens with a table, the
    rubrics «I. Подпрограмма …» and row numbers «1.», «1.1» that OCR cut out of the table (Section-header,
    List-item or Text regions between table parts), with their continuation rows, are text of the annex,
    not sections and points. A row number inside a Table region was never a marker."""
    pages = program_with_table_annex(
        MEASURES, ("Section-header", 'I. Подпрограмма "Развитие сырьевой базы"'),
        ("List-item", "1. Геолого-разведочные работы - всего"), ("Text", "Минприроды России 23,7 3,5 7,2"),
        ("Text", "1.1. Поисковые работы"), MEASURES,
        ("Section-header", 'II. Подпрограмма "Развитие производственного потенциала"'),
        ("Table", "<table><tr><td>4. Создание новых центров угледобычи</td><td>частные инвесторы</td></tr></table>"),
        ("Text", "5. Строительство обогатительных фабрик"), ("Text", "частные инвесторы 1,3 0,35"), MEASURES)
    result = S.build(extraction(pages))
    got = owners(result)
    for index in range(0, 14):
        assert got[f"3.{index}"] == "S/AN1", index
    rows = [p for p in result["paragraphs"] if any("table_row" in e for e in p["evidence"])]
    assert [p["text_preview"][:3] for p in rows] == ["I. ", "1. ", "1.1", "II.", "5. "]
    assert all(p["marker"] is None and p["kind"] == "text" for p in rows)


def test_points_around_a_table_keep_their_numbering():
    """Negative controls: points of ordinary text before and after a table still open points: «2.» after a
    table continues the numbering, in the approved text and in an annex whose first marker precedes the
    table; a marker after the last table of a table annex is a point as before."""
    pages = regulation(("Text", "1. Показатели приведены в таблице:"), TABLE, ("Text", "2. Второй пункт."),
                       TABLE, ("Text", "3. Третий пункт."))
    got = owners(S.build(extraction(pages)))
    assert got["2.2"] == "S/I/1" and got["2.4"] == "S/I/2" and got["2.6"] == "S/I/3"
    pages = program_with_table_annex(("Text", "1. Показатели приведены в таблице:"), MEASURES,
                                     ("Text", "2. Второй пункт."), MEASURES)
    got = owners(S.build(extraction(pages)))
    assert got["3.3"] == "S/AN1/1" and got["3.5"] == "S/AN1/2" and got["3.6"] == "S/AN1/2"
    pages = program_with_table_annex(MEASURES, ("Text", "1. Средства уточняются ежегодно."))
    result = S.build(extraction(pages))
    assert owners(result)["3.4"] == "S/AN1/1"
    assert not any("table_row" in e for p in result["paragraphs"] for e in p["evidence"])


def test_approved_text_opening_with_a_table_reads_its_row_numbers_as_rows():
    """Step 21.7 H (owner 29.10.2026 «Часть таблицы», rp-2728-2020 and rp-1431-2014): an approved text that is itself a
    table (an address distribution of subsidies under «УТВЕРЖДЕНО») is read like a table annex: the row «1.» cut out
    between the table parts is text of the document (`S`); so is a last row «4.15. Контрольное событие 4.15.» after
    the last table, while a «1.» there still opens a point."""
    pages = [[("Text", "1. Утвердить прилагаемое распределение."), ("Text", "Председатель Правительства", 1100)],
             [("Text", "УТВЕРЖДЕНО\nраспоряжением Правительства", 1000), ("Section-header", "РАСПРЕДЕЛЕНИЕ"),
              MEASURES, ("Text", 'Подпрограмма "Создание условий"'), ("List-item", "1. Реконструкция маршрута"),
              ("Text", "мощность - 4,68 км; 2319900 83700"), MEASURES]]
    result = S.build(extraction(pages))
    got = owners(result)
    assert got["2.4"] == "S" and got["2.5"] == "S" and got["2.6"] == "S"
    head = [[("Text", "1. Утвердить прилагаемый план."), ("Text", "Председатель Правительства", 1100)],
            [("Text", "УТВЕРЖДЕН\nраспоряжением Правительства", 1000), ("Section-header", "ПЛАН"), MEASURES]]
    got = owners(S.build(extraction(head[:1] + [head[1] + [("List-item", "4.15. Контрольное событие 4.15. Субсидии")]])))
    assert got["2.3"] == "S"
    got = owners(S.build(extraction(head[:1] + [head[1] + [("Text", "1. Средства уточняются ежегодно.")]])))
    assert got["2.3"] == "S/1"
    # an approved text with sections after its opening table (a Mintrud professional standard) keeps its points
    got = owners(S.build(extraction(head[:1] + [head[1] + [("Section-header", "I. Общие сведения"), MEASURES,
                                                           ("Text", "3.1. Обобщенная трудовая функция"), MEASURES]])))
    assert got["2.3"] == "S/I" and got["2.5"] == "S/I/3.1"


def two_lists_with_footnotes(second_table, notes):
    """An order with two annex lists that both number their footnotes from «¹»."""
    return [[("Text", "1. Утвердить прилагаемые перечни."), ("Text", "Председатель Правительства", 1100)],
            [("Page-header", "ПРИЛОЖЕНИЕ № 1\nк распоряжению Правительства", 900), ("Section-header", "ПЕРЕЧЕНЬ товаров"),
             ("Table", "<table><tr><td>Наименование товара¹</td><td>Код²</td></tr><tr><td>Шины³</td></tr></table>"),
             ("Footnote", "¹ Наименования приводятся по классификатору."), ("Footnote", "² Код товарной позиции."),
             ("Footnote", "³ Только новые шины.")],
            [("Page-header", "ПРИЛОЖЕНИЕ № 2\nк распоряжению Правительства", 900), ("Section-header", "ПЕРЕЧЕНЬ упаковки"),
             ("Table", second_table), *notes]]


@pytest.mark.parametrize("second_table", [
    "<table><tr><td>Материал упаковки<sup>1</sup></td><td>Код<sup>2</sup></td></tr><tr><td>Поддоны<sup>3</sup></td></tr></table>",
    "<table><tr><td>Материал упаковки¹</td><td>Код²</td></tr><tr><td>Поддоны³</td></tr></table>"])
def test_footnote_goes_to_the_area_of_the_last_mark_before_it(second_table):
    """Cycle 5 B2 (Review Focus 2): two lists number their footnotes «¹ ² ³»; the footnotes after the second list
    belong to it, where their mark last occurred, not to the first list. A table may print the mark as HTML
    «<sup>1</sup>» instead of «¹»."""
    notes = [("Footnote", "¹ Идентификация материала по маркировке."), ("Text", "² Буквенное обозначение упаковки."),
             ("Text", "³ За исключением поддонов.")]
    got = owners(S.build(extraction(two_lists_with_footnotes(second_table, notes))))
    assert [got[f"2.{k}"] for k in (2, 3, 4, 5)] == ["A/AN1"] * 4
    assert [got[f"3.{k}"] for k in (2, 3, 4, 5)] == ["A/AN2"] * 4


def test_footnote_without_a_found_mark_stays_unowned():
    """Negative controls: a footnote whose mark occurs nowhere before it has no owner, as before; a
    superscript <sup> with another number or a bare digit is not its mark."""
    second = "<table><tr><td>Материал<sup>2</sup></td><td>Код 4</td></tr></table>"
    notes = [("Footnote", "⁴ Сноска без значка в тексте.")]
    result = S.build(extraction(two_lists_with_footnotes(second, notes)))
    assert owners(result)["3.3"] == "A/AN2"  # step 21.3 F: no mark -> the document of its page (gold never leaves a footnote ownerless)
    note = next(p for p in result["paragraphs"] if p["flow"] == "footnote" and p["text_preview"].startswith("⁴"))
    assert {"footnote_owner": "unresolved", "candidates": 0} in note["evidence"]


LONG_V = ("V. Согласование проекта объема контрольных цифр приема для обучения по программам бакалавриата, программам "
          "специалитета и программам магистратуры федеральными органами исполнительной власти, осуществляющими функции "
          "по выработке государственной политики и нормативно-правовому регулированию в установленных сферах "
          "деятельности, и иными организациями, осуществляющими деятельность в соответствующей сфере")


def sections_up_to(last):
    """Points under Section-header sections «I.» … ``last``, two points each."""
    body, n = [], 0
    for value in range(2, last + 1):
        body.append(("Section-header", f"{S.to_roman(value)}. Раздел {value}"))
        for _ in range(2):
            n += 1
            body.append(("Text", f"{n + 2}. Пункт {n + 2}."))
    return regulation(("Text", "1. Первый пункт."), ("Text", "2. Второй пункт."), *body)


def test_section_heading_read_by_ocr_as_text_opens_the_next_section():
    """Cycle 5 B3 (Review Focus 3): «V. …» that OCR gave the category Text (and that is too long to look like
    a heading) opens section V when sections I–IV already exist in the same scope."""
    assert len(LONG_V) > 250 and S.parse_marker(LONG_V, "Text").kind == "none"
    pages = sections_up_to(4)
    pages[1] += [("Text", LONG_V), ("Text", "9. Перечень органов определяется Правилами."), ("Text", "а) первое;")]
    result = S.build(extraction(pages))
    got = owners(result)
    assert got["2.12"] == "S/IV/8"
    assert got["2.13"] == "S/V" and got["2.14"] == "S/V/9" and got["2.15"] == "S/V/9/а"
    heading = next(p for p in result["paragraphs"] if p["text_preview"].startswith("V. "))
    assert heading["marker"] == ["roman", "V"] and heading["kind"] == "heading"
    assert any("roman_sequence" in e for e in heading["evidence"])


@pytest.mark.parametrize("last", [1, 3])
def test_text_roman_without_the_previous_sections_opens_nothing(last):
    """Negative controls: «V.» of category Text without sections up to IV before it (only I, or I–III) is not a
    section heading; it stays with the open point."""
    pages = sections_up_to(last)
    pages[1] += [("Text", LONG_V), ("Text", "Перечень органов определяется Правилами.")]
    got = owners(S.build(extraction(pages)))
    point = 2 * (last - 1) + 2
    assert got[f"2.{len(pages[1]) - 2}"] == got[f"2.{len(pages[1]) - 1}"]
    assert got[f"2.{len(pages[1]) - 2}"].endswith(f"/{point}")


def test_roman_number_inside_a_sentence_opens_no_section():
    """«V.» after the start of a paragraph, or at the start of a paragraph that continues an unterminated sentence
    of the previous one («… в соответствии с разделом» / «V. Порядка …», a region cut by OCR), opens nothing."""
    pages = sections_up_to(4)
    pages[1] += [("Text", "Согласование по разделу V. Порядок проводится органами власти в установленные сроки")]
    got = owners(S.build(extraction(pages)))
    assert got["2.13"] == "S/IV/8"
    pages = sections_up_to(4)
    pages[1] += [("Text", "Согласование проводится органами власти в сроки, установленные в соответствии с разделом"),
                 ("Text", LONG_V)]
    got = owners(S.build(extraction(pages)))
    assert got["2.13"] == got["2.14"] == "S/IV/8"


@pytest.mark.parametrize("text", [
    "V. Согласование проекта осуществляется органами власти в течение десяти рабочих дней;",
    LONG_V + ", указанными в пункте 3,",  # long: a short line ending «,» is already a heading (heading_like)
    "V. Согласование проекта осуществляется органами власти в установленные сроки.",
    LONG_V + " и " + LONG_V[3:] + " и " + LONG_V[3:],
], ids=["semicolon", "comma", "dot", "too-long"])
def test_text_roman_that_reads_like_a_running_sentence_opens_no_section(text):
    """Guard of the cycle 5 B3 rule: after sections I–IV a Text «V. …» that ends like a sentence or a list item
    («.», «;» as ``heading_like``, or «,») or is longer than ``ROMAN_TEXT_MAX`` stays with the open point."""
    assert len(LONG_V) <= S.ROMAN_TEXT_MAX < len(LONG_V + " и " + LONG_V[3:] + " и " + LONG_V[3:])
    pages = sections_up_to(4)
    pages[1] += [("Text", text), ("Text", "Перечень органов определяется Правилами.")]
    got = owners(S.build(extraction(pages)))
    assert got["2.13"] == got["2.14"] == "S/IV/8"


def costing(*body, annex=False):
    """An order approving a costing procedure; ``body`` follows points «1.»–«4.» (or opens annex № 5)."""
    pages = [[("Text", "1. Утвердить прилагаемый Порядок."), ("Text", "Министр", 1200)],
             [("Text", "УТВЕРЖДЕН\nприказом Министерства", 1000), ("Title", "ПОРЯДОК определения цены"),
              ("Text", "1. Порядок применяется к договорам."), ("Text", "2. Цена определяется по калькуляции."),
              ("Text", "3. Индексы публикуются ежегодно."), ("Text", "4. Расчет приведен в приложении № 5.")]]
    if annex:
        return pages + [[("Section-header", "Приложение № 5\nк Порядку определения цены", 900), *body]]
    return [pages[0], pages[1] + list(body)]


GAP_BLOCK = (("Section-header", "Пусковые расходы"), ("Text", "Расходы учитываются при освоении производства."))


def test_dotted_number_after_a_skipped_number_is_a_sibling_not_a_subpoint():
    """Cycle 6 B1 (Review Focus 1): after «5.1» and an unnumbered block comes «5.3» («5.2» is not printed). The
    parent of «N.M» is «N.», so «5.3» and the following «5.4»–«5.6» are points of «5.», not subpoints of «5.1»;
    without a point «5.» in the annex they stay flat at its root."""
    tail = [("Text", f"5.{m}. Статья затрат {m}.") for m in (3, 4, 5, 6)]
    pages = costing(("Text", "5. Затраты группируются по статьям калькуляции:"), ("Text", "5.1. Статьи калькуляции."),
                    *GAP_BLOCK, *tail)
    got = owners(S.build(extraction(pages)))
    assert got["2.7"] == "S/5/5.1"
    assert [got[f"2.{k}"] for k in (10, 11, 12, 13)] == ["S/5/5.3", "S/5/5.4", "S/5/5.5", "S/5/5.6"]
    got = owners(S.build(extraction(costing(("Text", "5.1. Статьи калькуляции."), *GAP_BLOCK, *tail, annex=True))))
    assert got["3.1"] == "S/AN5/5.1"
    assert [got[f"3.{k}"] for k in (4, 5, 6, 7)] == ["S/AN5/5.3", "S/AN5/5.4", "S/AN5/5.5", "S/AN5/5.6"]


def test_dotted_gap_over_the_limit_stays_nested():
    """Cycle 7 B4 (v5 review): the sibling reading covers a gap of 2-3 numbers only; «5.5» after «5.1» (three numbers
    missing) keeps the earlier unexplained nesting into «5.1», while «5.4» after «5.1» is still a sibling."""
    for number, expected in ((5, "S/5/5.1/5.5"), (4, "S/5/5.4")):
        pages = costing(("Text", "5. Затраты группируются по статьям калькуляции:"),
                        ("Text", "5.1. Статьи калькуляции."), *GAP_BLOCK, ("Text", f"5.{number}. Статья затрат."))
        got = owners(S.build(extraction(pages)))
        assert got["2.7"] == "S/5/5.1" and got["2.10"] == expected, number


def test_dotted_subpoints_and_unbroken_sequences_are_unchanged():
    """Negative controls: a real subpoint «5.1.1» still nests in «5.1», and an unbroken «5.1, 5.2, 5.3» keeps its
    siblings under «5.»."""
    pages = costing(("Text", "5. Затраты группируются:"), ("Text", "5.1. Статьи калькуляции."),
                    ("Text", "5.1.1. Сырье и материалы."), ("Text", "5.1.2. Топливо."), ("Text", "5.2. Пусковые расходы."),
                    ("Text", "5.3. Затраты на освоение."))
    got = owners(S.build(extraction(pages)))
    assert [got[f"2.{k}"] for k in range(7, 12)] == ["S/5/5.1", "S/5/5.1/5.1.1", "S/5/5.1/5.1.2", "S/5/5.2",
                                                     "S/5/5.3"]


def test_footnote_goes_to_the_point_of_its_last_mark_before_it_not_to_a_later_page():
    """Cycle 6 B2 (Review Focus 2): point 2 continues on the next page and carries the mark «¹» there. The
    footnote «¹» printed under page 2 belongs to point 1, whose mark is the last one before it; the text of
    point 2 on page 3 comes after that footnote. The footnote under page 3 belongs to point 2."""
    pages = costing(("Text", "5. Индексы применяются с оговоркой¹."),
                    ("Text", "6. При определении прогнозных цен используются индексы"),
                    ("Footnote", "¹ Сноска к пункту 5."))
    pages.append([("Text", "по видам деятельности, указанным в оговорке¹."), ("Text", "7. Седьмой пункт."),
                  ("Footnote", "¹ Сноска к пункту 6.")])
    result = S.build(extraction(pages))
    got = owners(result)
    assert got["2.6"] == "S/5" and got["2.7"] == got["3.0"] == "S/6"
    assert got["2.8"] == "S/5" and got["3.2"] == "S/6"


def test_footnote_whose_mark_is_only_on_an_earlier_page_keeps_it():
    """Negative control: a footnote whose mark occurs only on an earlier page still goes to that point."""
    pages = costing(("Text", "5. Индексы применяются с оговоркой¹."), ("Text", "6. Шестой пункт."))
    pages.append([("Text", "7. Седьмой пункт."), ("Footnote", "¹ Сноска к пункту 5.")])
    assert owners(S.build(extraction(pages)))["3.1"] == "S/5"


@pytest.mark.parametrize("intro, owner", [("5. Индексы применяются к ценам¹:", "S/5"),
                                          ("5. Индексы применяются к ценам:", "S/5/1")])
def test_mark_repeated_on_the_footnote_page_gives_the_common_owner(intro, owner):
    """Cycle 6 B2: the same mark printed twice on the footnote's page, in point 5 and in its subpoint 1), refers
    to one footnote: it belongs to their common owner, point 5. With the mark only in the subpoint the footnote
    stays with the subpoint."""
    pages = costing(("Text", intro), ("Text", "1) на сырье по регулируемым ценам¹;"), ("Text", "2) на изделия."),
                    ("Footnote", "¹ Перечень регулируемых цен утвержден Правительством."))
    assert owners(S.build(extraction(pages)))["2.9"] == owner


def order_with_agreement(*signatures):
    """An order approving a draft agreement whose last article ends with ``signatures``."""
    return [[("Title", "РАСПОРЯЖЕНИЕ"), ("Text", "1. Одобрить проект Соглашения."),
             ("Text", "2. Заместителю Председателя Правительства подписать Соглашение."),
             ("Text", "Председатель Правительства\nРоссийской Федерации"), ("Text", "И.Иванов", 1220)],
            [("Page-header", "Проект", 1320), ("Section-header", "СОГЛАШЕНИЕ"),
             ("Section-header", "Статья 4"), ("Section-header", "Прочие условия"),
             ("Text", "1. Соглашение вступает в силу со дня его подписания."),
             ("Text", "2. Соглашение составлено в двух экземплярах."), *signatures]]


def test_signature_heading_and_signature_places_after_the_last_point_belong_to_the_agreement():
    """Cycle 6 B3 (Review Focus 3): after the last point of an attached agreement the signature block — the heading
    «Подписи и реквизиты Сторон», a signature place «От Правительства …», a signer title and initials with a
    surname — belongs to the agreement itself, not to its last point; the act's own signer belongs to the act."""
    pages = order_with_agreement(("Section-header", "Подписи и реквизиты Сторон"),
                                 ("Text", "От Правительства\nРоссийской Федерации", 300),
                                 ("Text", "Заместитель Председателя\nПравительства Российской\nФедерации", 280),
                                 ("Text", "____________ И.И.Петров\nМ.П.", 190),
                                 ("Text", "От Государственной корпорации", 870), ("Text", "Генеральный директор", 930))
    got = owners(S.build(extraction(pages)))
    assert got["1.1"] == "A/1" and got["1.2"] == "A/2" and got["1.3"] == got["1.4"] == "A"
    assert got["2.5"] == "S/ст4/2"
    assert [got[f"2.{k}"] for k in range(6, 12)] == ["S"] * 6
    for text in ("Подписи и реквизиты Сторон", "Адреса и реквизиты сторон", "Реквизиты и подписи Сторон",
                 "От Правительства Российской Федерации", "От Государственной корпорации"):
        assert S.requisite_like(text), text


def test_text_of_the_last_point_that_starts_like_a_signer_stays_in_the_point():
    """Negative controls: an ordinary sentence of the last point that begins with «Председатель» or «От», or that
    mentions the parties' requisites, stays in the point."""
    for line in ("Председатель комиссии утверждает состав рабочей группы.",
                 "От имени Сторон Соглашение подписывают уполномоченные лица.",
                 "От Сторон требуется уведомлять друг друга об изменении реквизитов.",
                 "Подписи и реквизиты Сторон приводятся в конце Соглашения."):
        got = owners(S.build(extraction(order_with_agreement(("Text", line)))))
        assert got["2.6"] == "S/ст4/2", line


def test_unterminated_from_the_parties_line_stays_in_the_point():
    """Cycle 7 B4 (v5 review): «От Сторон …» without a final dot names both parties, not one signature place, so it
    opens no signature block; «От Правительства …» still does."""
    for line in ("От Сторон требуется уведомлять друг друга об изменении реквизитов",
                 "От Сторон", "от Сторон Соглашения"):
        got = owners(S.build(extraction(order_with_agreement(("Text", line)))))
        assert got["2.6"] == "S/ст4/2", line
        assert not S.requisite_like(line), line
    got = owners(S.build(extraction(order_with_agreement(("Text", "От Правительства Российской Федерации", 300)))))
    assert got["2.6"] == "S"


LONG_III = ("III. Объем финансирования мероприятий подпрограмм за счет средств федерального бюджета и внебюджетных "
            "источников уточняется ежегодно при формировании проекта федерального бюджета на очередной финансовый год "
            "и плановый период с учетом результатов реализации мероприятий предыдущего года и прогноза")


def test_rubrics_of_a_table_annex_do_not_count_as_roman_sections():
    """Cycle 6 B4 (Review Focus 4, v4 §4.7): the rubrics «I.», «II.» between the tables of a table annex are annex
    text, so they are not sections I and II: a long Text «III. …» after the last table opens no section III and
    stays annex text. A long Text «II. …» between the tables (v4 promoted it, then demoted it to a row, leaving a
    stale `roman_sequence`) is plain annex text without that evidence."""
    assert len(LONG_III) > 250 and S.parse_marker(LONG_III, "Text").kind == "none"
    pages = program_with_table_annex(MEASURES, ("Section-header", 'I. Подпрограмма "Развитие сырьевой базы"'), MEASURES,
                                     ("Text", "II." + LONG_III[4:]), MEASURES, ("Text", LONG_III))
    result = S.build(extraction(pages))
    got = owners(result)
    assert [got[f"3.{k}"] for k in range(3, 9)] == ["S/AN1"] * 6
    evidence = [p["evidence"] for p in result["paragraphs"]]
    assert not any("roman_sequence" in e for ev in evidence for e in ev)
    rows = [p for p in result["paragraphs"] if any("table_row" in e for e in p["evidence"])]
    assert [p["text_preview"][:3] for p in rows] == ["I. "]


def test_long_title_case_annex_caption_of_the_approved_text():
    """Cycle 9 B1: «Приложение № N к Административному регламенту по предоставлению … утвержденному приказом …
    от … № 494 (форма)» in title case is over 300 characters and still opens the annex of the approved text,
    like the uppercase «ПРИЛОЖЕНИЕ № N к <Документ>» of C7. A long sentence ending with a dot stays text."""
    service = ("по предоставлению государственной услуги по регистрации опасных производственных объектов "
               "в государственном реестре опасных производственных объектов, ")
    caption = (f"Приложение № {{n}}\nк Административному регламенту\n{service}утвержденному приказом Федеральной "
               "службы по экологическому, технологическому и атомному надзору\nот 25 ноября 2016 г. № 494{{tail}}")
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить прилагаемый Административный регламент."),
              ("Text", "А.Алёшин", 1200)],
             [("Text", "УТВЕРЖДЕН\nприказом Ростехнадзора\nот 25 ноября 2016 г. № 494", 1000),
              ("Section-header", "АДМИНИСТРАТИВНЫЙ РЕГЛАМЕНТ"), ("Text", "1. Регламент устанавливает сроки."),
              ("Text", "2. Заявление подается по форме приложения № 2.")],
             [("Text", caption.format(n=1, tail=""), 1000), ("Section-header", "СВЕДЕНИЯ О ТЕРРИТОРИАЛЬНЫХ ОРГАНАХ"),
              ("Text", "Центральное управление.")],
             [("Text", caption.format(n=2, tail=" (форма)"), 1000), ("Section-header", "ЗАЯВЛЕНИЕ"),
              ("Text", "Прошу зарегистрировать объект.")]]
    assert len(caption.format(n=1, tail="")) > S.CAPTION_BLOCK_MAX
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "S/2"
    assert (got["3.0"], got["3.1"], got["3.2"]) == ("S/AN1",) * 3
    assert (got["4.0"], got["4.1"], got["4.2"]) == ("S/AN2",) * 3
    sentence = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить прилагаемый Административный регламент.")],
                [("Text", "УТВЕРЖДЕН\nприказом Ростехнадзора", 1000), ("Section-header", "АДМИНИСТРАТИВНЫЙ РЕГЛАМЕНТ"),
                 ("Text", "1. Сроки."),
                 ("Text", f"Приложение № 1 к Административному регламенту {service * 2}содержит сведения об органах.")]]
    assert owners(S.build(extraction(sentence)))["2.3"] == "S/1"


KOAP_NOTES = [[("Title", "КОДЕКС РОССИЙСКОЙ ФЕДЕРАЦИИ ОБ АДМИНИСТРАТИВНЫХ ПРАВОНАРУШЕНИЯХ"),
               ("Section-header", "Статья 1.5. Презумпция невиновности"), ("Text", "1. Лицо подлежит ответственности."),
               ("Text", "2. Лицо считается невиновным."),
               ("Text", "Примечание. Положение части 1 настоящей статьи не распространяется на правонарушения."),
               ("Section-header", "Статья 9.1. Нарушение требований"), ("Text", "1. Нарушение требований -"),
               ("Text", "влечет наложение штрафа."), ("Text", "2. Дача ложного заключения -"),
               ("Text", "(Дополнение частью - Федеральный закон от 02.07.2013 № 186-ФЗ)"), ("Text", "Примечания:"),
               ("Text", "1. Под грубым нарушением понимается нарушение."), ("Text", "2¹. Для целей настоящей статьи иное."),
               ("Text", "(Дополнение примечанием - Федеральный закон от 02.07.2005 № 80-ФЗ)"),
               ("Section-header", "Статья 9.2. Далее"), ("Text", "1. Текст статьи.")]]


def test_article_note_belongs_to_the_article_not_its_last_part():
    """Cycle 9 B2: «Примечание. …» or «Примечания:» after the parts of an article belongs to the article, and so
    do the numbered notes «1.», «2¹.» under it and the editorial note after them, up to the next article. The
    next article's parts open as usual."""
    got = owners(S.build(extraction(KOAP_NOTES)))
    assert (got["1.2"], got["1.3"], got["1.4"]) == ("A/ст1.5/ч1", "A/ст1.5/ч2", "A/ст1.5")
    assert (got["1.8"], got["1.9"]) == ("A/ст9.1/ч2", "A/ст9.1/ч2")
    assert [got[f"1.{k}"] for k in range(10, 14)] == ["A/ст9.1"] * 4
    assert (got["1.14"], got["1.15"]) == ("A/ст9.2", "A/ст9.2/ч1")


def test_note_outside_an_article_keeps_its_point():
    """Cycle 9 B2 Review Focus 2: in a resolution with points and no articles «Примечание.» after a point stays
    with that point."""
    pages = [[("Title", "ПОСТАНОВЛЕНИЕ"), ("Text", "1. Утвердить перечень."), ("Text", "2. Установить сроки."),
              ("Text", "Примечание. Сроки исчисляются в рабочих днях.")]]
    assert owners(S.build(extraction(pages)))["1.3"] == "A/2"
    # An amending law quotes a new code article with its note: the note is quoted text of point «5)».
    amending = [[("Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"), ("Section-header", "Статья 1"), ("Text", "Внести в Кодекс изменения:"),
                 ("Text", "5) дополнить статьей 13.42¹ следующего содержания:"),
                 ("Section-header", "\"Статья 13.42¹. Нарушение требований"), ("Text", "1. Нарушение -"),
                 ("Text", "Примечание. За правонарушения лица несут ответственность как юридические лица.\";"),
                 ("Text", "6) дополнить статьей 13.49 следующего содержания:")]]
    got = owners(S.build(extraction(amending)))
    assert (got["1.6"], got["1.7"]) == ("A/ст1/5", "A/ст1/6")


def test_labelled_first_item_opens_the_list():
    """Step 13 B2: «Приложение: 1. Копии …» right before «2. Опись …» is item 1 of the enclosure list (FSB sample
    forms; «Примечания: 1. …» in a resolution's form). Negatives: no «2.» next, «2)» after «1.», a label of three
    words. In an article «Примечания: 1. …» still opens the article's note block."""
    form = [[("Text", "1. Утвердить форму заявления."), ("Text", "Директор", 1200)],
            [("Text", "Приложение № 1\nк приказу Министерства", 1000), ("Title", "ЗАЯВЛЕНИЕ"),
             ("Text", "Сведения о заявителе: ________"),
             ("Text", "Приложение: 1. Копии документов и сведения согласно описи."),
             ("Text", "2. Опись прилагаемых документов.")]]
    got = owners(S.build(extraction(form)))
    assert (got["2.3"], got["2.4"]) == ("A/AN1/1", "A/AN1/2")
    for second in ("Опись прилагаемых документов.", "2) Опись прилагаемых документов."):
        changed = copy.deepcopy(form)
        changed[1][4] = ("Text", second)
        assert owners(S.build(extraction(changed)))["2.3"] == "A/AN1", second
    changed = copy.deepcopy(form)
    changed[1][3] = ("Text", "Приложение к заявлению: 1. Копии документов и сведения согласно описи.")
    assert owners(S.build(extraction(changed)))["2.3"] == "A/AN1"
    koap = [[("Title", "КОДЕКС"), ("Section-header", "Статья 15.27. Неисполнение требований"),
             ("Text", "1. Неисполнение требований влечет наложение штрафа."),
             ("Text", "2. Повторное неисполнение влечет дисквалификацию."),
             ("Text", "Примечания: 1. Предприниматели несут ответственность как юридические лица."),
             ("Text", "2. Сотрудники освобождаются от ответственности.")]]
    got = owners(S.build(extraction(koap)))
    assert (got["1.4"], got["1.5"]) == ("A/ст15.27", "A/ст15.27")


@pytest.mark.parametrize("captions", [
    ["(наименование должности", "руководителя юридического лица)", "(подпись)", "(инициалы, фамилия)", "М.П."],
    ["(подпись)", "(инициалы, фамилия индивидуального предпринимателя)", "М.П. (при наличии)"],
])
def test_form_signature_captions_open_the_requisite_block(captions):
    """Step 13 B3: the captions under a sample form's signature lines after its last point belong to the form, not
    to the last point; «Директор» over «А.Бортников» after the order's last point opens the order's requisites.
    Negatives: a field caption «(фамилия, имя, отчество …)» stays with the point; a quoted form's «М.П.» does not
    end the amending quotation's point."""
    form = [[("Text", "1. Утвердить форму заявления."), ("Text", "2. Признать утратившим силу приказ."),
             ("Text", "Директор"), ("Text", "А.Бортников")],
            [("Text", "Приложение № 1\nк приказу Министерства", 1000), ("Title", "ЗАЯВЛЕНИЕ"),
             ("Text", "1. Копии документов согласно описи."), ("Text", "2. Опись прилагаемых документов."),
             *[("Text", c) for c in captions]]]
    got = owners(S.build(extraction(form)))
    assert (got["1.2"], got["1.3"]) == ("A", "A")
    assert [got[f"2.{k}"] for k in range(4, 4 + len(captions))] == ["A/AN1"] * len(captions)
    form[1][4:] = [("Text", "(фамилия, имя, отчество (при наличии)"), ("Text", "серия ____ № ____")]
    assert owners(S.build(extraction(form)))["2.4"] == "A/AN1/2"
    quoted = [[("Title", "ПОСТАНОВЛЕНИЕ"), ("Text", "1. Внести в Правила изменение, изложив форму в редакции:"),
               ("Text", "\"Руководитель организации ______ (подпись)"), ("Text", "М.П. (при наличии)\".")]]
    assert owners(S.build(extraction(quoted)))["1.3"] == "A/1"     # the quotation runs to the end of the act


def test_quoted_list_number_does_not_close_its_own_quotation():
    """Cycle 9 B3: a quoted article whose own list reaches «5)» and goes on «6)» stays quoted although the
    introducing point is «5)»: «6)» continues the quotation's list, not the introducing one. After the closing
    quote the introducing list goes on."""
    pages = [[("Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"), ("Section-header", "Статья 2"), ("Text", "Внести в Федеральный закон изменения:"),
              ("Text", "5) дополнить статьей 9 следующего содержания:"),
              ("Section-header", "\"Статья 9. Федеральная организация"), ("Text", "1. Организацией признается союз."),
              ("Text", "2. Организация выполняет функции:"), ("Text", "1) установление стандартов;"),
              ("Text", "5) выдача сертификатов;"), ("Text", "6) составление расчета;"),
              ("Text", "7) иные функции."), ("Text", "3. Стандарты обязательны для членов.\";"),
              ("Text", "6) в статье 10:"), ("Text", "а) часть 1 изложить в следующей редакции:")]]
    got = owners(S.build(extraction(pages)))
    assert [got[f"1.{k}"] for k in range(3, 12)] == ["A/ст2/5"] * 9
    assert (got["1.12"], got["1.13"]) == ("A/ст2/6", "A/ст2/6/а")


def quoted_articles(closing):
    return [[("Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"), ("Section-header", "Статья 1"), ("Text", "Внести в Федеральный закон изменения:"),
             ("Text", "5) дополнить статьями 10 и 11 следующего содержания:"),
             ("Section-header", "\"Статья 10. Устав общины"), ("Text", "1. Устав содержит сведения."),
             ("Section-header", "Статья 11. Членство в общине"), ("Text", "1. Членами вправе быть лица."),
             ("Text", "2. Воля выражается в заявлении." + closing),
             ("Section-header", "Статья 2"), ("Text", "Настоящий Федеральный закон вступает в силу.")]]


@pytest.mark.parametrize("closing", ["\";", ""])
def test_quoted_article_heading_stays_quoted_text(closing):
    """Cycle 9 B4: inside an amending quotation a later article heading («Статья 11.») is quoted text of the
    introducing point, not an article of the act; the act's own next article «Статья 2» closes the quotation
    even when the closing quote is lost."""
    got = owners(S.build(extraction(quoted_articles(closing))))
    assert [got[f"1.{k}"] for k in range(3, 9)] == ["A/ст1/5"] * 6
    assert (got["1.9"], got["1.10"]) == ("A/ст2", "A/ст2")


def test_print_shop_footer_is_a_page_mark_not_a_signature():
    """Cycle 10 B1: a typist's mark in a page footer («Компьютер /Н.Н./При-К7552-3», read differently on every
    page, so not running noise) is a page mark of the scope root: it does not open the requisite block, and the
    tables after it stay with the open point. A real signature printed as a footer still opens the block."""
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить формат."), ("Text", "Руководитель А.А. Иванов", 1200)],
             [("Text", "Приложение № 1\nк приказу ФНС России", 1000), ("Section-header", "I. Общие сведения"),
              ("Text", "1. Формат описывает файл обмена."), ("Table", "<table><tr><td>Элемент</td></tr></table>"),
              ("Page-footer", "Компьютер /Н.Н./При-К7552-3", 1500)],
             [("Page-header", "X", 900), ("Table", "<table><tr><td>Сведения</td></tr></table>"),
              ("Caption", "Таблица 4.3"), ("Caption", "Таблица 4.4", 1200), ("Table", "<table><tr><td>НПЮЛ</td></tr></table>"),
              ("Text", "Таблица 4.23", 1150), ("Text", "Сведения о сумме акциза"),
              ("Table", "<table><tr><td>Сумма</td></tr></table>"),
              ("Page-footer", "копибуто /Н.И./Прил-К7552-3", 1500)]]
    got = owners(S.build(extraction(pages)))
    assert got["2.2"] == got["2.3"] == "A/AN1/I/1"
    # a table caption at the right edge of a landscape page is no signature either
    assert [got[f"3.{k}"] for k in range(1, 8)] == ["A/AN1/I/1"] * 7
    assert got["2.4"] == got["3.8"] == "A/AN1"
    signed = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить формат."), ("Text", "2. Контроль оставляю за собой."),
               ("Page-footer", "Руководитель Д.В. Егоров", 1100)]]
    assert owners(S.build(extraction(signed)))["1.3"] == "A"


def test_lowercase_document_referent_nests_in_the_open_act_annex():
    """Cycle 10 B2: inside an act annex («Приложение № 1 к приказу ФНС России», a declaration form) the captions
    «Приложение № 1 к форме налоговой декларации» name that form in lowercase: they are annexes of the act annex
    (`A/AN1/AN1`), not act annexes. «Приложение № 2 к приказу» in lowercase still opens the next act annex."""
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить форму и порядок."), ("Text", "Руководитель А.А. Иванов", 1200)],
             [("Text", "Приложение № 1\nк приказу ФНС России", 1000), ("Section-header", "Налоговая декларация"),
              ("Text", "Сумма акциза исчисляется налогоплательщиком.")],
             [("Text", "Приложение № 1\nк форме налоговой декларации", 1000), ("Text", "Расчет суммы акциза.")],
             [("Text", "Приложение № 2\nк форме налоговой декларации", 1000), ("Text", "Сведения о гарантиях.")],
             [("Text", "Приложение № 2\nк приказу ФНС России", 1000), ("Section-header", "ПОРЯДОК заполнения"),
              ("Text", "1. Декларация заполняется.")]]
    got = owners(S.build(extraction(pages)))
    assert (got["2.0"], got["2.2"]) == ("A/AN1", "A/AN1")
    assert (got["3.0"], got["3.1"]) == ("A/AN1/AN1", "A/AN1/AN1")
    assert (got["4.0"], got["4.1"]) == ("A/AN1/AN2", "A/AN1/AN2")
    assert (got["5.0"], got["5.2"]) == ("A/AN2", "A/AN2/1")


def same_row(ext, page, indexes, y):
    """Put the listed regions of a page on one printed row (the helper stacks regions vertically)."""
    for i in indexes:
        bbox = ext["pages"][page - 1]["regions"][i]["bbox"]
        bbox[1], bbox[3] = y, y + 40
    return ext


def test_card_field_on_a_table_row_is_not_a_signature():
    """Cycle 10 B3: in a professional standard's card the short fields at the right («Код», «А/01.4», «Уровень
    квалификации», «Код оригинала») share their printed row with a table or a long text at the left: they are
    cells of that row and stay with the open point, not a signature of the document. A signer's name at the
    right of a long title row is still a signature."""
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить профессиональный стандарт."),
              ("Text", "Министр А.О. Котяков", 1200)],
             [("Text", "УТВЕРЖДЕН\nприказом Министерства труда", 1000), ("Title", "ПРОФЕССИОНАЛЬНЫЙ СТАНДАРТ"),
              ("Section-header", "III. Характеристика трудовых функций"), ("Section-header", "3.1. Обобщенная трудовая функция"),
              ("Text", "Контроль технического состояния кузнечно-штамповочного оборудования", 400),
              ("Text", "Код", 1030), ("Text", "А/01.4", 1110), ("Text", "Уровень квалификации", 1270), ("Text", "4", 1510),
              ("Table", "<table><tr><td>Оригинал</td><td>X</td></tr></table>", 480), ("Text", "Код оригинала", 1080),
              ("Text", "Регистрационный номер профессионального стандарта", 1250),
              ("Table", "<table><tr><td>Трудовые действия</td><td>Подготовка</td></tr></table>")]]
    # «Код оригинала» sits under the table, on one row with the long field name at its right
    ext = same_row(same_row(extraction(pages), 2, [4, 5, 6, 7, 8], 700), 2, [10, 11], 800)
    got = owners(S.build(ext))
    assert [got[f"2.{k}"] for k in range(4, 13)] == ["S/III/3.1"] * 9
    signed = [[("Title", "ПОСТАНОВЛЕНИЕ"), ("Text", "1. Утвердить правила."),
               ("Text", "Председатель Правительства Российской Федерации"), ("Text", "М.Мишустин", 1250)]]
    assert owners(S.build(same_row(extraction(signed), 1, [2, 3], 600)))["1.3"] == "A"


def test_table_of_contents_lines_belong_to_the_document_root():
    """Cycle 10 B4: a professional standard opens with its table of contents: «I. Общие сведения ………… 1»,
    «3.1. Обобщенная трудовая функция «…» ……». Such lines (words, then a dot leader and maybe a page number)
    open no section or point; they are text of the document root. The real sections after them open as usual;
    a numbered fill-in line of a form («2. ……………») is not a contents line."""
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить профессиональный стандарт."),
              ("Text", "Министр А.О. Котяков", 1200)],
             [("Text", "УТВЕРЖДЕН\nприказом Министерства труда", 1000), ("Title", "ПРОФЕССИОНАЛЬНЫЙ СТАНДАРТ"),
              ("List-item", "I. Общие сведения ................................................ 1"),
              ("List-item", "III. Характеристика обобщенных трудовых функций ........................ 3"),
              ("List-item", "3.1. Обобщенная трудовая функция «Перемещение ручной клади» ............"),
              ("Section-header", "I. Общие сведения"), ("Text", "Обслуживание пассажиров вокзала."),
              ("Section-header", "III. Характеристика обобщенных трудовых функций"),
              ("Section-header", "3.1. Обобщенная трудовая функция"), ("Text", "Перемещение ручной клади."),
              ("Text", "4. ………………………")]]
    got = owners(S.build(extraction(pages)))
    assert (got["2.2"], got["2.3"], got["2.4"]) == ("S", "S", "S")
    assert (got["2.5"], got["2.6"], got["2.7"], got["2.9"]) == ("S/I", "S/I", "S/III", "S/III/3.1")
    assert S.toc_line("I. Общие сведения ........ 1") and not S.toc_line("4. ………………………")


def test_notes_heading_after_the_last_point_belongs_to_the_document():
    """Cycle 10 B5: a form («Сведения, характеризующие ОПО», an annex) ends with its last point «8. …», a table and
    a standalone heading «Примечания» with explanatory paragraphs: the notes belong to the form, not to point 8.
    A note sentence «Примечание. Текст …» after a point keeps its owner (B2 covers only articles)."""
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить регламент."), ("Text", "Руководитель А.В. Алёшин", 1200)],
             [("Text", "Приложение № 4\nк Административному регламенту", 1000), ("Section-header", "Сведения, характеризующие ОПО"),
              ("Section-header", "8. Сведения о составе ОПО"), ("Table", "<table><tr><td>№ п/п</td></tr></table>"),
              ("Section-header", "Примечания", 700), ("Text", "Сведения оформляются заявителем в виде документа."),
              ("Text", "В графе 1.1 вносится полное наименование объекта.")]]
    got = owners(S.build(extraction(pages)))
    assert (got["2.2"], got["2.3"]) == ("A/AN4/8", "A/AN4/8")
    assert (got["2.4"], got["2.5"], got["2.6"]) == ("A/AN4", "A/AN4", "A/AN4")
    sentence = [[("Title", "ПОСТАНОВЛЕНИЕ"), ("Text", "1. Утвердить перечень."), ("Text", "2. Установить сроки."),
                 ("Text", "Примечание. Сроки исчисляются в рабочих днях.")]]
    assert owners(S.build(extraction(sentence)))["1.3"] == "A/2"


def test_closing_paragraph_of_an_amending_quotation_does_not_close_the_subpoint():
    """Cycle 11 B1: inside «б) в Правилах …:» an amendment quotes new points «"13. …», «14. …» and a closing
    paragraph «При отклонении … суда.";» without a marker. That closing paragraph is quoted text: it closes no
    subpoint, and the later amendments of «б)» («дополнить пунктом 15¹ …») stay in «б)»."""
    pages = [[("Title", "ПОСТАНОВЛЕНИЕ"), ("Text", "1. Утвердить прилагаемые изменения."),
              ("Text", "УТВЕРЖДЕНЫ\nпостановлением Правительства", 1000), ("Section-header", "ИЗМЕНЕНИЯ"),
              ("Text", "3. В постановлении от 29 июля 2013 г. № 644:"), ("Text", "а) пункт 3 признать утратившим силу;"),
              ("Text", "б) в Правилах холодного водоснабжения:"), ("Text", "пункты 13 и 14 изложить в следующей редакции:"),
              ("Text", "\"13. Абонент направляет проект договора."), ("Text", "14. В случае разногласий договор заключается."),
              ("Text", "При отклонении протокола абонент вправе обратиться в суд.\";"),
              ("Text", "дополнить пунктом 15¹ следующего содержания:"),
              ("Text", "4. В постановлении от 29 июля 2013 г. № 645 слова заменить.")]]
    got = owners(S.build(extraction(pages)))
    assert [got[f"1.{k}"] for k in range(6, 12)] == ["S/3/б"] * 6
    assert got["1.12"] == "S/4"


def test_annex_caption_quoted_in_an_amendment_opens_no_annex():
    """Cycle 11 B2: «приложения № 6 и 7 изложить в следующей редакции:» quotes two new annexes of the amended Rules:
    «"ПРИЛОЖЕНИЕ № 6 к Правилам …» and, without its own quote mark, «ПРИЛОЖЕНИЕ № 7 к Правилам …». Inside the
    quotation neither caption opens an annex, and a quoted right-hand «(форма)» opens no requisite block: everything
    up to the closing quote is text of «б)». An act annex («ПРИЛОЖЕНИЕ к постановлению …») after the quotation
    still opens."""
    pages = [[("Title", "ПОСТАНОВЛЕНИЕ"), ("Text", "1. Утвердить прилагаемые изменения."),
              ("Text", "УТВЕРЖДЕНЫ\nпостановлением Правительства", 1000), ("Section-header", "ИЗМЕНЕНИЯ"),
              ("Text", "3. В постановлении от 29 июля 2013 г. № 644:"), ("Text", "а) пункт 3 признать утратившим силу;"),
              ("Text", "б) в Правилах холодного водоснабжения:"), ("Text", "приложения № 6 и 7 изложить в следующей редакции:"),
              ("Section-header", "\"ПРИЛОЖЕНИЕ № 6\nк Правилам холодного водоснабжения", 900), ("Text", "(форма)", 1300),
              ("Section-header", "ПЕРИОДИЧНОСТЬ"), ("Text", "отбора проб сточных вод."),
              ("Section-header", "ПРИЛОЖЕНИЕ № 7\nк Правилам холодного водоснабжения", 900),
              ("Section-header", "Значения нормативов состава сточных вод"), ("Text", "Нормативы утверждаются ежегодно.\";"),
              ("Text", "4. В постановлении от 29 июля 2013 г. № 645 слова заменить.")],
             [("Text", "ПРИЛОЖЕНИЕ\nк постановлению Правительства от 22 мая 2020 г. № 728", 1000),
              ("Text", "Перечень утративших силу актов.")]]
    got = owners(S.build(extraction(pages)))
    assert [got[f"1.{k}"] for k in range(6, 15)] == ["S/3/б"] * 9
    assert got["1.15"] == "S/4"
    assert (got["2.0"], got["2.1"]) == ("A/AN", "A/AN")


def test_quotation_opened_by_its_own_letter_keeps_its_list_and_notes():
    """Cycle 11 B3-B4: an amendment quotes new subpoints «"б) …;», «в) …;», «г) …"» right inside the introducing
    subpoint «б)»: the opener's own «б)» starts the quotation's list, so «в)» continues it and does not end the
    quotation. A quoted form's «Примечания:» inside a quotation is quoted text, not the notes of the document."""
    pages = [[("Title", "ПОСТАНОВЛЕНИЕ"), ("Text", "1. Утвердить прилагаемые изменения."),
              ("Text", "УТВЕРЖДЕНЫ\nпостановлением Правительства", 1000), ("Section-header", "ИЗМЕНЕНИЯ"),
              ("Text", "4. В постановлении от 29 июля 2013 г. № 645:"), ("Text", "а) в тексте постановления слова заменить;"),
              ("Text", "б) в типовом договоре:"), ("Text", "подпункты \"б\" - \"г\" изложить в следующей редакции:"),
              ("Text", "\"б) орган местного самоуправления;"), ("Text", "в) территориальный орган;"),
              ("Text", "г) структурные подразделения органа;\";"), ("Text", "приложение изложить в следующей редакции:"),
              ("Text", "\"1. Канализационный выпуск № 1"), ("Section-header", "Примечания:"),
              ("Text", "1. Значение концентрации указывается в миллиграммах.\";"),
              ("Text", "в) в типовом договоре водоотведения слова заменить.")]]
    got = owners(S.build(extraction(pages)))
    assert [got[f"1.{k}"] for k in range(6, 15)] == ["S/4/б"] * 9
    assert got["1.15"] == "S/4/в"


def test_typist_mark_in_a_footer_opens_no_point_and_belongs_to_the_scope_root():
    """Step 12 B1: OCR reads the typist's mark «Г:\копир\Н.И.\Прил-ГВ198-3» differently on every page («1. Коприво
    ИНМ / Прип-ГВ108-0», «Г. конфликт /ИН И /Прип. Г0198-3»): a page header/footer never opens a numbered point,
    and a header/footer ending in a job code («Прил-ГВ198-3», «Прим. 18198-7») after a slash is a page mark of the
    scope root. The tables of point «4.» after the page break stay in «4.». A caption «… № 553/15» is no job code."""
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить формат."), ("Text", "Руководитель А.А. Иванов", 1200)],
             [("Text", "Приложение № 1\nк приказу ФНС России", 1000), ("Section-header", "II. Состав файла"),
              ("Text", "3. Файл содержит элементы."), ("Text", "4. Описание элементов приведено в таблицах."),
              ("Table", "<table><tr><td>Файл</td></tr></table>"),
              ("Page-footer", "1. Коприво ИНМ / Прип-ГВ108-0", 1500)],
             [("Table", "<table><tr><td>Документ</td></tr></table>"), ("Caption", "Таблица 4.2"),
              ("Table", "<table><tr><td>Сведения</td></tr></table>"),
              ("Page-footer", "Г. конфликт /ИН И /Прип. Г0198-3", 1500)],
             [("Table", "<table><tr><td>Подписант</td></tr></table>"),
              ("Page-footer", "03.03.2015 13:48 1. копр. № 14/11/При-18198-5", 1500)]]
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == got["3.0"] == got["3.1"] == got["3.2"] == got["4.0"] == "A/AN1/II/4"
    assert got["2.5"] == got["3.3"] == got["4.1"] == "A/AN1"
    for text in ("1. Конфиско НН И/Прим. 18198-7", "Компьютер/Н.П.Приш-К7552-3", "1. КОМПЬЮТНО/МИ/ПРИП-Г0198-7",
                 "11.02.2015 13:41 В. Коприцкого И.И. Прын-ТВ108-1", "11.02.2015 12:52 t.kompburo@h.mj (Прим-Г8198-2)"):
        assert S.page_mark(S.Region(0, 1, 0, "r", "Page-footer", [0, 0, 1, 1], [1, 1], text, text, []))
    for text in ("Приложение № 1 к приказу ФАС России от 06.07.2015 № 553/15", "Руководитель Д.В. Егоров", "Стр. 12",
                 "Приложение № 2 к приказу ФНС России № ЕД-7-20/957"):
        assert not S.page_mark(S.Region(0, 1, 0, "r", "Page-header", [0, 0, 1, 1], [1, 1], text, text, []))


def test_bare_annex_number_before_an_approval_caption_heads_the_next_approved_document():
    """Step 12 B2: an order approving several formats heads each with «Приложение № N» (no reference) and
    «УТВЕРЖДЕН приказом …». The bare caption belongs to the approved document it heads (`S2`), also after the
    first one, not to the previous document as its annex (`S/AN2`). A caption naming another document («к
    Формату …») before an approval caption stays an annex of the open document."""
    approved = "УТВЕРЖДЕН\nприказом ФНС России\nот 24.03.2015 № ММВ-7-15/93@"
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить форматы."), ("Text", "Руководитель А.А. Иванов", 1200)],
             [("Text", "Приложение № 1", 1000), ("Text", approved, 1000), ("Section-header", "ФОРМАТ счета-фактуры"),
              ("Text", "1. Формат описывает файл.")],
             [("Text", "Приложение № 2", 1000), ("Text", approved, 1000), ("Section-header", "ФОРМАТ журнала"),
              ("Text", "1. Формат описывает журнал.")]]
    got = owners(S.build(extraction(pages)))
    assert (got["2.0"], got["2.1"], got["2.3"]) == ("S", "S", "S/1")
    assert (got["3.0"], got["3.1"], got["3.2"], got["3.3"]) == ("S2", "S2", "S2", "S2/1")
    nested = pages[:2] + [[("Text", "Приложение № 1\nк Формату счета-фактуры", 1000),
                           ("Text", "Сведения о файле.")]]
    assert owners(S.build(extraction(nested)))["3.0"] == "S/AN1"


def test_long_numbered_caption_naming_a_lowercase_approved_document_opens_its_annex():
    """Step 12 B3: inside an act annex («Приложение № 2 к приказу», a Procedure) the samples are headed «Приложение
    № 2 к порядку представления … заявки …, утвержденному приказом Министерства … № 791» (over 120 characters, OCR
    Text, lowercase document noun). A numbered caption naming a lowercase document that it calls approved by an
    act opens that document's annex (`A/AN2/AN2`) like a page-header caption does; its signature lines stay in it.
    Without «№» or with a final dot it is no caption."""
    procedure = ("к порядку представления субъектом Российской Федерации заявки на предоставление субсидии на "
                 "очередной финансовый год и плановый период, утвержденному приказом Министерства труда и социальной "
                 "защиты Российской Федерации от «24» февраля 2025 г. № 791")
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить порядок."), ("Text", "Министр А.А. Иванов", 1200)],
             [("Page-header", "Приложение № 2\nк приказу Министерства труда", 1000), ("Section-header", "Порядок"),
              ("Text", "1. Заявка представляется ежегодно."), ("Text", "2. К заявке прилагаются документы.")],
             [("Page-header", f"Приложение № 1 {procedure}", 900), ("Section-header", "ПОЯСНИТЕЛЬНАЯ ЗАПИСКА"),
              ("Text", "1. Цель субсидии:"), ("Text", "Высшее должностное лицо субъекта Российской Федерации")],
             [("Text", f"Приложение № 2 {procedure}", 900), ("Text", "(Рекомендуемый образец)", 1100),
              ("Section-header", "Финансово-экономическое обоснование"), ("Text", "1. Общая часть:"),
              ("Text", "Высшее должностное лицо субъекта Российской Федерации")]]
    got = owners(S.build(extraction(pages)))
    assert got["3.0"] == "A/AN2/AN1"
    assert (got["4.0"], got["4.1"], got["4.2"], got["4.3"]) == ("A/AN2/AN2", "A/AN2/AN2", "A/AN2/AN2", "A/AN2/AN2/1")
    for text in (f"Приложение 2 {procedure}", f"Приложение № 2 {procedure} заполняется заявителем."):
        p = S.Paragraph("body", [S.Region(0, 1, 0, "r", "Text", [0, 0, 1, 1], [1, 1], text, text, [])])
        assert S.annex_caption(p) is None


def test_official_signature_place_after_a_forms_last_point_opens_its_requisite_block():
    """Step 12 B4: a sample form ends «9. Дополнительная информация:» and then the signature place «Высшее
    должностное лицо субъекта Российской Федерации (уполномоченное им лицо)», «(подпись)», «(расшифровка подписи)»,
    the executor's name and phone: from the official's title on, the lines belong to the form root, not to «9.».
    A terminated sentence about an official stays in the point."""
    form = [("Page-header", "Приложение № 1\nк приказу Министерства труда", 1000), ("Section-header", "ЗАПИСКА"),
            ("Text", "8. Сведения о проекте."), ("Text", "9. Дополнительная информация (при необходимости):"),
            ("Text", "Высшее должностное лицо субъекта Российской Федерации (уполномоченное им лицо)"),
            ("Text", "(подпись)", 800), ("Text", "(расшифровка подписи)", 1150),
            ("Text", "Контактные телефоны: ______, адрес электронной почты: ______.")]
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить форму."), ("Text", "Министр А.А. Иванов", 1200)], form]
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "A/AN1/9"
    assert [got[f"2.{k}"] for k in range(4, 8)] == ["A/AN1"] * 4
    sentence = form[:4] + [("Text", "Должностное лицо, ответственное за подготовку заявки, подписывает ее.")]
    assert owners(S.build(extraction([pages[0], sentence])))["2.4"] == "A/AN1/9"



def subpoint_pages(lines):
    return [[("Title", "ПРИКАЗ"), *[("Text", t) for t in lines]]]


def test_ocr_letter_marker_in_place_of_the_next_digit_reads_as_that_digit():
    """Step 16 C1: OCR printed «6)» as «б)» (SP 2.4.2.4283-26, batch 15): after «5)» with no «а)» before, «б)» is the
    sixth subpoint, and the real «а)», «б)», «в)» of that subpoint nest under it; «7)» follows as usual."""
    got = owners(S.build(extraction(subpoint_pages([
        "16. Должны соблюдаться требования:", "4) помещения оборудуются;", "5) доски размещаются;",
        "б) при организации питания должны соблюдаться следующие требования:", "а) помещения предусматриваются;",
        "б) помещения оснащаются;", "в) залы оборудуются;", "7) комнаты обеспечиваются кроватями;",
        "8) кровати имеют твердое ложе.", "17. Следующий пункт."]))))
    assert [got[f"1.{k}"] for k in range(4, 11)] == [
        "A/16/6", "A/16/6/а", "A/16/6/б", "A/16/6/в", "A/16/7", "A/16/8", "A/17"]


def test_ocr_digit_marker_in_place_of_the_next_letter_reads_as_that_letter():
    """Step 16 C1, the reverse (prikaz-minselskogo-134-2016, batch 14): «3)» after «ж)» with no «2)» before is the
    letter «з)», a sibling of «ж)»."""
    letters = [f"{c}) основание {c};" for c in "абвгдеж"]
    got = owners(S.build(extraction(subpoint_pages(
        ["30. Основанием для отказа является:", *letters, "3) несоответствие заявителя требованиям.",
         "31. Для предоставления услуги необходимы документы."]))))
    assert got["1.8"] == "A/30/ж" and got["1.9"] == "A/30/з" and got["1.10"] == "A/31"


def test_genuine_letters_and_digits_keep_their_reading():
    got = owners(S.build(extraction(subpoint_pages([
        "2. Условия:", "а) первое;", "б) второе;", "3. Перечень:", "1) первое;", "2) второе;", "3) третье;",
        "4) четвёртое;", "5) пятое;", "6) шестое.", "4. Порядок:", "а) первое;", "б) второе;", "в) третье;",
        "г) четвёртое;", "д) пятое;", "е) шестое;", "ж) седьмое;", "з) восьмое."]))))
    assert got["1.3"] == "A/2/б" and got["1.7"] == "A/3/3" and got["1.10"] == "A/3/6"
    assert got["1.13"] == "A/4/б" and got["1.19"] == "A/4/з"


def test_paragraph_after_the_last_decimal_subpoint_stays_in_it():
    # Step 17 (owner 28.10.2026 «Да, подпункту»): a dotted «7.1.5.» is no list item; the paragraph after the last one
    # is its second paragraph, as after «7.1.4.» (step 16 C2 had given it to «7.1.»).
    pages = [[("Text", "УТВЕРЖДЕНЫ постановлением от 22.05.2020 № 15", 900),
              ("Section-header", "VII. Требования к содержанию"),
              ("Text", "7.1. Уборка проводится ежедневно."),
              ("Text", "7.1.4. Инвентарь протирается влажной ветошью."),
              ("Text", "Ковер очищается ежедневно."),
              ("Text", "7.1.5. В медицинском пункте помещения дезинфицируются."),
              ("Text", "Отходы класса Б обеззараживаются."),
              ("Text", "7.2. Оконные стекла очищаются по мере загрязнения.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.4"] == "S/VII/7.1/7.1.4"
    assert got["1.6"] == "S/VII/7.1/7.1.5"
    assert got["1.7"] == "S/VII/7.2"


def test_paragraph_after_a_nested_list_returns_to_the_owner_of_that_list():
    # Step 16 C2 (batch 14): after the last «д)» of the list inside «2)» the paragraph belongs to «2)», the owner
    # of the list, not to point 25 (convention v2: the point or part the list belongs to).
    got = owners(S.build(extraction(subpoint_pages([
        "25. К освещению предъявляются требования:", "1) показатели освещения соответствуют нормативам;",
        "2) без естественного освещения допускается размещение:", "а) технических помещений;",
        "б) помещений работников.", "Без естественного освещения допускается размещение операционных.",
        "26. Мебель выполняется из материалов, допускающих обработку."]))))
    assert got["1.5"] == "A/25/2/б"
    assert got["1.6"] == "A/25/2"
    assert got["1.7"] == "A/26"


def test_sentence_after_an_unterminated_last_subpoint_on_the_same_page_returns_to_the_point():
    # Step 16 C2 (batch 14): «19) … программой производственного контроля» lost its final «.»; the next
    # capitalised sentence on the same page is the point's. On the next page it may be the cut sentence's
    # end («Российской Федерации.»), so it stays in the subpoint.
    head = ["74. При эксплуатации аквапарков:", "18) ванны обрабатываются дезинфицирующими препаратами;",
            "19) осуществляется лабораторный контроль в соответствии с программой производственного контроля"]
    tail = "Кратность лабораторных исследований изложена в приложении № 6 к правилам."
    got = owners(S.build(extraction(subpoint_pages([*head, tail, "75. Размещение гостиниц не допускается."]))))
    assert got["1.3"] == "A/74/19"
    assert got["1.4"] == "A/74"
    got = owners(S.build(extraction([subpoint_pages(head)[0], [("Text", tail), ("Text", "75. Следующий пункт.")]])))
    assert got["2.0"] == "A/74/19"


def test_unterminated_lines_inside_a_subpoint_do_not_close_it():
    # Step 16 C2 negative (ukaz-410-2021): appointment lines without punctuation, then a long sentence ending «.»,
    # stay in «а)»; only the subpoint's own marked paragraph that lost its «.» counts.
    got = owners(S.build(extraction(subpoint_pages([
        "1. Назначить:", "а) судьями:", "председателем Арбитражного суда Мурманской области",
        "Драчена Артема Васильевича заместителем председателя Арбитражного суда города Москвы Китову Аллу.",
        "2. Назначить:", "а) судьей Иванова."]))))
    assert got["1.4"] == "A/1/а"


def test_header_subheadings_with_a_colon_or_after_an_unterminated_point_belong_to_the_section():
    # Step 16 C3 (batch 15): OCR Section-header subheadings «Проведение проверки:» / «Документарная проверка» and a
    # Section-header after a point that lost its final «.» belong to the section, as other subheadings do.
    got = owners(S.build(extraction(styled_regulation(
        ("Text", "4. Результатом процедуры является регистрация приказа."),
        ("Section-header", "## Проведение проверки:"), ("Section-header", "### Документарная проверка"),
        ("Text", "5. Основанием для проверки является приказ."),
        ("Text", "6. Заинтересованное лицо вправе обжаловать решения, принятые в ходе исполнения функции"),
        ("Section-header", "### Предмет досудебного обжалования"),
        ("Text", "7. Предметом обжалования являются действия должностных лиц.")))))
    assert got["2.8"] == "S/I" and got["2.9"] == "S/I"
    assert got["2.10"] == "S/I/5"
    assert got["2.12"] == "S/I"
    assert got["2.13"] == "S/I/7"
    # a body-text line after the unterminated point is still its cut sentence
    got = owners(S.build(extraction(styled_regulation(
        ("Text", "6. Заинтересованное лицо вправе обжаловать решения, принятые в ходе исполнения"),
        ("Text", "Государственной функции Министерства"), ("Text", "7. Предметом обжалования являются действия.")))))
    assert got["2.8"] == "S/I/6"


def test_rows_after_the_last_table_part_that_continue_the_row_numbers_are_annex_text():
    # Step 16 C4 (batch 15, a subsidy calculation form): rows «1.», «2.» are cut out between the table parts and
    # «3.»-«5.» after the last part; they continue the row numbers, so they are rows too. A marker that does not
    # continue them («1.» again) is a point as before.
    rows = (MEASURES, ("List-item", "1. Расходы на оплату труда"), ("List-item", "2. Расходы на общехозяйственные нужды"),
            MEASURES, ("Text", "материальных запасов и оплату услуг связи"), ("List-item", "3. Расходы на сопровождение"),
            ("List-item", "4. Прочие расходы"), ("List-item", "5. Итого затрат (строка 1 + строка 2)"))
    result = S.build(extraction(program_with_table_annex(*rows)))
    got = owners(result)
    for index in range(0, 11):
        assert got[f"3.{index}"] == "S/AN1", index
    marked = [p["text_preview"][:2] for p in result["paragraphs"] if any("table_row" in e for e in p["evidence"])]
    assert marked == ["1.", "2.", "3.", "4.", "5."]
    got = owners(S.build(extraction(program_with_table_annex(*rows[:5], ("Text", "1. Средства уточняются ежегодно.")))))
    assert got["3.8"] == "S/AN1/1"


def test_footer_printed_on_two_pages_is_a_page_mark_of_the_scope_root():
    # Step 16 C5 (batch 14): «ФГОС ВО культурология -05» in the footer of two pages is a page mark of the
    # document (convention v2 §2), not text of point 2 it interrupts; the point still continues on the next page.
    # A footer line printed once keeps the old reading.
    def act(second_footer):
        return [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить прилагаемый стандарт."),
                 ("Text", "2. Признать утратившими силу:"), ("Text", "приказ от 25 января 2010 г. № 71 «Об утверждении"),
                 ("Page-footer", "ФГОС ВО культурология -05")],
                [("Text", "образовательного стандарта»;"), ("Text", "Министр Д.В. Ливанов", 1100),
                 ("Page-footer", second_footer)]]
    result = S.build(extraction(act("ФГОС ВО культурология -05")))
    got = owners(result)
    assert got["1.4"] == "A"
    assert got["2.0"] == "A/2" and conts(result)["2.0"] is True
    assert owners(S.build(extraction(act("Страница 2"))))["1.4"] == "A/2"


def test_a_list_of_point_references_is_text_of_the_point_that_lists_them():
    # Step 17 B (owner 28.10.2026: a new class of batch 16): in «1.5. … не применяются к транспортным средствам, …
    # утверждена до вступления в силу» the lines «2.1.42 и 2.2.7 в части …», «2.1.34, 4.1.4 в части …» are references
    # to points (number without its dot, then a lowercase word, «,» or «и»), not points. A dotless point with a
    # capitalised text («2.1.8 Организации …», as «7.1.8» in batch 16) is still a point.
    pages = [[("Text", "УТВЕРЖДЕНЫ постановлением от 16.10.2020 № 30", 900),
              ("Section-header", "I. Общие положения"),
              ("Text", "1.4. Правила применяются к судам."),
              ("Text", "1.5. Правила не применяются к транспортным средствам, документация на которые утверждена"),
              ("Text", "2.1.42 и 2.2.7 в части наличия вкладных резервуаров;"),
              ("Text", "2.1.43 в части наличия документов об оценке соответствия;"),
              ("Text", "2.1.34, 4.1.4, 4.3.11 в части требований к обеззараживанию воздуха."),
              ("Text", "1.6. Требования пунктов 2.5.4 и 3.4.4 применяются с 2025 года."),
              ("Section-header", "II. Учет источников"),
              ("Text", "2.1. Учет ведется в журналах."),
              ("Text", "2.1.7. Передача продукции оформляется документально."),
              ("Text", "2.1.8 Организации проводят инвентаризацию источников один раз в год.")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.3"] == "S/I/1.5"
    for index in (4, 5, 6):
        assert got[f"1.{index}"] == "S/I/1.5", index
    assert got["1.7"] == "S/I/1.6"
    assert got["1.11"] == "S/II/2.1/2.1.8"


def test_a_dotless_lowercase_subpoint_that_goes_on_keeps_its_marker():
    # Step 17 B negative (prikaz-minkultury-1321-2016): «12.1 принятие решения …» under «12.» is a subpoint.
    got = owners(S.build(extraction(regulation(
        ("Text", "12. Сроки предоставления услуги составляют:"),
        ("Text", "12.1 принятие решения о внесении сведений - не позднее 5 дней;"),
        ("Text", "12.2. принятие решения об отказе - не позднее 5 дней.")))))
    assert got["2.3"] == "S/I/12/12.1" and got["2.4"] == "S/I/12/12.2"


def test_annex_word_before_the_approval_caption_in_one_region_opens_the_approved_document():
    # Step 20 A (batch 19, SanPiN 2.2.4.3359-16): OCR printed «Приложение ⏎ Утверждены ⏎ постановлением …» as one
    # region; the approved rules are `S`, not text of point 3 of the resolution.
    pages = [[("Title", "ГЛАВНЫЙ ГОСУДАРСТВЕННЫЙ САНИТАРНЫЙ ВРАЧ РОССИЙСКОЙ ФЕДЕРАЦИИ\nПОСТАНОВЛЕНИЕ"),
              ("Text", "1. Утвердить санитарно-эпидемиологические правила и нормативы СанПиН 2.2.4.3359-16."),
              ("Text", "2. Признать утратившими силу постановление от 2003 г. № 1."),
              ("Text", "3. Ввести в действие правила с 1 января 2017 года."),
              ("Text", "А.Ю. Попова", 1200)],
             [("Text", "Приложение\nУтверждены\nпостановлением\nГлавного государственного\nсанитарного врача\n"
                       "Российской Федерации", 1000),
              ("Text", "от 21.06.2016 № 81", 1000),
              ("Section-header", "I. Общие положения"),
              ("Text", "1.1. Правила устанавливают требования к физическим факторам.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.0"] == "S" and got["2.1"] == "S"
    assert got["2.2"] == "S/I" and got["2.3"] == "S/I/1.1"


def approving_act(second_page):
    return [[("Title", "ГЛАВНЫЙ ГОСУДАРСТВЕННЫЙ САНИТАРНЫЙ ВРАЧ РОССИЙСКОЙ ФЕДЕРАЦИИ\nПОСТАНОВЛЕНИЕ"),
             ("Text", "1. Утвердить санитарные правила СП 2.2.4285-26."),
             ("Text", "2. Ввести в действие правила с 1 марта 2026 года."),
             ("Text", "А.Ю. Попова", 1200)], second_page]


def test_approved_text_without_a_recognised_caption_opens_after_the_signature():
    # Step 20 B (safety net after batch 19): the act approves a document and is signed; the next page starts its text
    # without a caption OCR kept. The approved document opens there, so one lost caption costs one line, not the tree.
    got = owners(S.build(extraction(approving_act(
        [("Title", "САНИТАРНЫЕ ПРАВИЛА"), ("Section-header", "I. Общие положения"),
         ("Text", "1.1. Правила устанавливают требования.")]))))
    assert got["1.3"] == "A"
    assert got["2.0"] == "S" and got["2.1"] == "S/I" and got["2.2"] == "S/I/1.1"
    # an annex caption on the next page still opens the act annex
    got = owners(S.build(extraction(approving_act(
        [("Text", "Приложение № 1\nк постановлению Главного государственного санитарного врача", 1000),
         ("Text", "Перечень показателей.")]))))
    assert got["2.0"] == "A/AN1" and got["2.1"] == "A/AN1"
    # an act that approves nothing keeps its text after the signature in the act
    pages = approving_act([("Text", "Лист рассылки: территориальные органы.")])
    pages[0][1] = ("Text", "1. Руководителям органов обеспечить контроль.")
    assert owners(S.build(extraction(pages)))["2.0"].startswith("A")


def test_notes_heading_right_after_a_table_belongs_to_the_owner_of_the_table():
    # Step 20 C (batches 18-19, three SanPiN): «Примечание:» right under a table inside point 8.4 and the lines under it
    # are notes of that table, so of point 8.4, not notes of the whole document (cycle 10 B5 keeps that reading when
    # no table precedes the heading).
    got = owners(S.build(extraction(regulation(
        ("Text", "8.4. Допустимые уровни приведены в таблице:"), ("Table", "<table><tr><td>Класс</td><td>5***</td></tr></table>"),
        ("Section-header", "Примечание:"), ("Text", "* 5 класс - для работ с открытыми источниками."),
        ("Text", "Лица, допущенные к работе, проходят инструктаж."),
        ("Text", "8.5. Работы проводятся в спецодежде.")))))
    for index in (2, 3, 4, 5, 6):
        assert got[f"2.{index}"] == "S/I/8.4", index
    assert got["2.7"] == "S/I/8.5"


def test_a_table_printed_far_from_its_reference_belongs_to_the_point_that_refers_to_it():
    # Step 20 D (batch 19, SanPiN 2.2.4.3483-17): point 6.2 says «представлены в таблицах 6.1, 6.2»; the tables are
    # printed after section VII. «Таблица 6.1» and what follows it up to the next point belong to point 6.2. A table
    # caption nobody refers to keeps the current point.
    T = ("Table", "<table><tr><td>Участок</td><td>200</td></tr></table>")
    got = owners(S.build(extraction(regulation(
        ("Text", "1.1. Контроль освещения обязателен."), ("Text", "1.2. Уровни освещения представлены в таблицах 1.1, 1.2."),
        ("Section-header", "II. Аэроионный состав воздуха"), ("Text", "2.1. Контроль аэроионов не проводится."),
        ("Text", "2.2. Аэроионификация рекомендована для бытовых помещений."),
        ("Caption", "Таблица 1.1"), ("Text", "Уровни освещения на рабочих местах подземных объектов"), T,
        ("Section-header", "Примечание:"), ("Text", "*Норма снижена на ступень."),
        ("Caption", "Таблица 1.2"), T,
        ("Section-header", "III. Шум"), ("Text", "3.1. Уровни шума нормируются."), ("Caption", "Таблица 3.1"), T))))
    assert got["2.3"] == "S/I/1.2" and got["2.6"] == "S/II/2.2"
    for index in range(7, 14):
        assert got[f"2.{index}"] == "S/I/1.2", index
    # a caption line alone («Таблица 3.1») under its point stays with it (step 21 moves only tables with own headings)
    assert got["2.15"] == "S/III/3.1" and got["2.16"] == "S/III/3.1" and got["2.17"] == "S/III/3.1"


def test_a_table_with_its_own_heading_between_points_belongs_to_the_section():
    # Step 21 (owner 29.10.2026 «Разделу», batch 20, SanPiN 1.2.3685-21): after a finished point a table heading
    # («Вещества, обладающие эффектом суммации», «Таблица 1.3.»), its table and the lines under it up to the next point
    # are text of the section. A table the point introduces («… в таблице 1.1:») stays with the point; one it only
    # names («… приведены в таблице 1.3.») goes to the section too (owner 29.10.2026 «Разделу»).
    T = ("Table", "<table><tr><td>Азота диоксид</td><td>0,2</td></tr></table>")
    got = owners(S.build(extraction(regulation(
        ("Text", "4. Нормативы содержания веществ приведены в таблице 1.1:"), ("Caption", "Таблица 1.1."), T,
        ("Text", "5. Эффектом суммации обладают вещества однонаправленного действия."),
        ("Section-header", "Вещества, обладающие эффектом суммации"), ("Caption", "Таблица 1.3."), T, T,
        ("Section-header", "Вещества, обладающие эффектом неполной суммации"), ("Caption", "Таблица 1.4."), T,
        ("Text", "Коэффициент неполной суммации принимается равным 1,5."),
        ("Text", "6. Контроль проводится лабораториями.")))))
    assert got["2.3"] == "S/I/4" and got["2.4"] == "S/I/4"      # introduced by «… в таблице 1.1:»
    assert got["2.5"] == "S/I/5"
    for index in range(6, 14):
        assert got[f"2.{index}"] == "S/I", index
    assert got["2.14"] == "S/I/6"
    got = owners(S.build(extraction(regulation(
        ("Text", "5. Вещества с эффектом суммации приведены в таблице 1.3."),
        ("Section-header", "Вещества, обладающие эффектом суммации"), ("Caption", "Таблица 1.3."), T,
        ("Text", "6. Контроль проводится лабораториями.")))))
    assert [got[f"2.{index}"] for index in range(2, 7)] == ["S/I/5", "S/I", "S/I", "S/I", "S/I/6"]
    # without an enclosing section the table stays with the point
    got = owners(S.build(extraction([[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить нормативы."),
                                      ("Section-header", "Вещества"), ("Caption", "Таблица 1."), T]])))
    assert got["1.2"] == "A/1" and got["1.4"] == "A/1"


def test_a_title_caption_over_a_table_is_its_own_heading_but_a_numbered_caption_is_not():
    # Step 21: OCR may give the table title the Caption category («Вещества, обладающие эффектом суммации.»); that is a
    # heading of its own -> section. A caption that is the table number with its name («Таблица 2.1. Оптимальные
    # величины …», SanPiN 2.2.4.3359-16 gold) stays with the point.
    T = ("Table", "<table><tr><td>Азота диоксид</td><td>0,2</td></tr></table>")
    got = owners(S.build(extraction(regulation(
        ("Text", "5. Эффектом суммации обладают вещества однонаправленного действия."),
        ("Caption", "Вещества, обладающие эффектом суммации."), T,
        ("Text", "6. Перепады температуры воздуха не должны превышать 3 °С."),
        ("Caption", "Таблица 2.1. Оптимальные величины параметров микроклимата"), T,
        ("Text", "7. Контроль проводится лабораториями.")))))
    assert got["2.3"] == "S/I" and got["2.4"] == "S/I"
    assert got["2.6"] == "S/I/6" and got["2.7"] == "S/I/6"


def test_a_headed_table_after_a_formula_or_with_a_long_title_goes_to_the_section():
    # Step 21.7 B (sanpin-2-2021): a point ending in a formula «$$ … загрязнения.} $$» is finished; a 307-character
    # plain title before «Таблица 3.13» is still the table's title.
    T = ("Table", "<table><tr><td>Азота диоксид</td><td>0,2</td></tr></table>")
    title = "Предельно допустимые концентрации (ПДК) химических веществ в воде " + "питьевой, " * 26 + "аквапарков"
    assert 300 < len(title) <= S.TABLE_TITLE_MAX
    got = owners(S.build(extraction(regulation(
        ("Text", "5. Суммарный показатель загрязнения равен сумме коэффициентов."),
        ("Formula", "$$\nКсі - \\text{коэффициент концентрации і-го компонента загрязнения.}\n$$"),
        ("Section-header", "Степени химического загрязнения почвы"), ("Caption", "Таблица 4.5"), T,
        ("Text", "6. Оценка воды проводится по санитарному законодательству."),
        ("Text", title), ("Caption", "Таблица 3.13"), T,
        ("Text", "7. Контроль проводится лабораториями.")))))
    assert [got[f"2.{index}"] for index in range(4, 7)] == ["S/I"] * 3
    assert [got[f"2.{index}"] for index in range(8, 11)] == ["S/I"] * 3
    assert got["2.11"] == "S/I/7"


def test_a_numbered_rubric_between_table_parts_is_not_a_point():
    # Step 21.7 C (sanpin-2-2021, table 5.25): «2. Учреждения общего образования» between two parts of one table, numbered
    # back from the open point 87, is the table's rubric; a «88.» there going on from 87 is still a point.
    T = ("Table", "<table><tr><td>11</td><td>Инструментальная</td></tr></table>")
    got = owners(S.build(extraction(regulation(
        ("Text", "87. Требования к освещению приведены в таблице:"), T,
        ("Section-header", "2. Учреждения общего образования"), T,
        ("Section-header", "3. Дошкольные образовательные организации"), T,
        ("Text", "88. Нормативы микроклимата установлены для помещений."), T,
        ("Text", "89. Контроль проводится лабораториями.")))))
    assert [got[f"2.{index}"] for index in range(2, 8)] == ["S/I/87"] * 6
    assert got["2.8"] == "S/I/88" and got["2.10"] == "S/I/89"


def test_dotted_rubrics_cut_out_of_tables_whose_siblings_ocr_kept_inside_are_not_points():
    # Step 21.7 D (prikaz-minzdravookhraneniya-369-2022): OCR kept «2.2. Хирургические …» as the table's <caption> and cut
    # «1.1. Прием врача» and «2.1. …» out above their tables; all are rubrics in the table grid, the text stays in «1.»,
    # «2.». Without a dotted caption inside a table «1.1.» over a table is a point («5.5. Номенклатура …», minekon-37).
    T = ("Table", "<table><tr><td>B01.068.001</td><td>Прием</td></tr></table>")
    C = ("Table", "<table><caption>2.2. Хирургические методы лечения</caption><tr><td>A16</td></tr></table>")
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить стандарт.")],
             [("Text", "Приложение к приказу Министерства здравоохранения"), ("Text", "СТАНДАРТ МЕДИЦИНСКОЙ ПОМОЩИ"),
              ("Text", "1. Медицинские услуги для диагностики"), ("Text", "1.1. Прием врача-специалиста"), T,
              ("Text", "2. Медицинские услуги для лечения"), ("Text", "2.1. Прием и наблюдение врача"), T, C]]
    got = owners(S.build(extraction(pages)))
    assert [got[f"2.{index}"] for index in range(2, 5)] == ["A/AN/1"] * 3
    assert [got[f"2.{index}"] for index in range(5, 9)] == ["A/AN/2"] * 4
    pages[1][-1] = T
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "A/AN/1/1.1" and got["2.6"] == "A/AN/2/2.1"


def test_an_unnumbered_table_heading_between_5_1_and_5_3_is_the_missing_sibling():
    # Step 21.7 E (prikaz-minekonomicheskogo-37-2015): «Пусковые расходы¹,²» over a table after the table of «5.1.» and
    # before «5.3.» stands for the unprinted «5.2»: the block leaves «5.1» for the annex root. Before «5.2.» it stays.
    T = ("Table", "<table><tr><td>1</td><td>Затраты на сырье</td></tr></table>")
    def build(following):
        return owners(S.build(extraction([[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить номенклатуру.")],
                                          [("Text", "Приложение № 5 к приказу"), ("Text", "5.1. Затраты на сырье"), T,
                                           ("Section-header", "Пусковые расходы¹,²"), T, ("Text", following)]])))
    got = build("5.3. Затраты на освоение производства")
    assert got["2.1"] == "A/AN5/5.1" and got["2.3"] == "A/AN5" and got["2.4"] == "A/AN5"
    got = build("5.2. Затраты на освоение производства")
    assert got["2.3"] == "A/AN5/5.1"


def test_a_dotted_point_the_act_names_together_with_its_number_is_a_peer():
    # Step 21.7 G (prikaz-minkultury-1321-2016): «документы, указанные в пунктах 15 и 15.1» makes «15.1» a peer of «15»
    # (convention v2 §5 exception), with its own «1)», «2)»; without such a reference «15.1» nests in «15».
    def build(reference):
        return owners(S.build(extraction(regulation(
            ("Text", "15. Для получения услуги заявитель представляет заявление."),
            ("Text", "15.1. Для внесения изменений заявитель представляет:"), ("Text", "1) заявление;"),
            ("Text", "2) договор страхования."), ("Text", f"16. Специалист проверяет документы, {reference}.")))))
    got = build("указанные в пунктах 15 и 15.1")
    assert [got[f"2.{index}"] for index in range(3, 6)] == ["S/I/15.1", "S/I/15.1/1", "S/I/15.1/2"]
    got = build("указанные в пункте 15")
    assert got["2.3"] == "S/I/15/15.1" and got["2.5"] == "S/I/15/15.1/2"


def test_footnote_with_a_lost_superscript_and_its_list_continuation_find_their_owner():
    # Step 21.2 A (sanpin-81-2016, sanpin-44-2017): OCR printed the footnote number as plain digits («15 СП 3.4.2318-08 …»)
    # in a Footnote region; it is footnote 15 owned by the point with «¹⁵». A numberless Footnote region right after a
    # footnote ending «:» or «;» on the same page («а) 1 с – для локальной вибрации;») continues it.
    pages = regulation(("Text", "4.4. Граждане вскрывают контейнеры с товарами¹⁵."),
                       ("Text", "4.5. Шкуры животных проходят контроль⁸."),
                       ("Footnote", "15 СП 3.4.2318-08 «Санитарная охрана территории Российской Федерации»."),
                       ("Footnote", "⁸ Для измерений приняты следующие постоянные времени:"),
                       ("Footnote", "а) 1 с – для локальной вибрации;"), ("Footnote", "б) 10 с – для общей вибрации."))
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "S/I/4.4"
    assert got["2.5"] == "S/I/4.5" and got["2.6"] == "S/I/4.5" and got["2.7"] == "S/I/4.5"


def test_page_code_line_signer_title_and_marker_without_a_space():
    # Step 21.2 B (pp-931-2022, pp-996-2022): «5590030 (1.4)» — the document's page code printed as body text at the page
    # foot — is a page mark of the scope root; point 2 goes on after it on the next page.
    pages = [[("Text", "УТВЕРЖДЕНЫ\nпостановлением Правительства", 1000), ("Section-header", "ПРАВИЛА"),
              ("Text", "1. Правила определяют порядок."), ("Text", "2. Понятия используются в"),
              ("Text", "5590030 (1.4)")],
             [("Text", "значении, определенном в Правилах перевозок."), ("Text", "3. Участники обмениваются файлами.")]]
    result = S.build(extraction(pages))
    got = owners(result)
    assert got["1.4"] == "S" and got["2.0"] == "S/2" and conts(result)["2.0"] is True
    # Step 21.2 C (prikaz-minnauki-511-2019, prikaz-minkultury-1321-2016): «Врио Министра» signs the act
    got = owners(S.build(extraction([[("Title", "ПРИКАЗ"), ("Text", "1. Создать комиссию."),
                                      ("Text", "2. Контроль возложить на заместителя Министра."),
                                      ("Text", "Врио Министра"), ("Text", "А.В. Петров", 1200)]])))
    assert got["1.3"] == "A"
    # Step 21.2 D (fz-435-2020; the owner's known class «6.Сообщение»): a point number glued to a capitalised word
    got = owners(S.build(extraction([[("Section-header", "Статья 21. Реорганизация"),
                                      ("Text", "5. Имущество передается единому заказчику."),
                                      ("Text", "6.Сообщение о реорганизации подлежит размещению в реестре.")]])))
    assert got["1.2"] == "A/ст21/ч6"


def test_step_21_3_captions_legends_and_notes_inside_subpoints():
    # Step 21.3 A-E (owner 29.10.2026: fix every prototype error; sanpin-81-2016 cases)
    T = ("Table", "<table><tr><td>Время</td><td>8</td></tr></table>")
    got = owners(S.build(extraction(regulation(
        ("Text", "7.2. Магнитное поле:"), ("Text", "а) оценка проводится по уровню поля;"),
        ("Text", "б) уровни приведены в таблице 7.1."), ("Caption", "Таблица 7.1. Уровни поля"), T,   # A: caption
        ("Text", "7.3. Облучение:"), ("Text", "е) уровни определяются по формуле, где"),
        ("Text", "К – коэффициент;"), ("Text", "К = 10 – для вращающихся антенн;"),
        ("Text", "К = 12,5 – для облучения кистей рук."),                                     # B: legend line
        ("Text", "7.4. Диапазоны:"), ("Text", "а) от 180 до 380 нм;"), ("Text", "б) от 380 до 1400 нм,"),
        ("Text", "где λ – длина волны излучения."),                                          # C: «где» legend
        ("Text", "7.5. Коэффициенты приведены в таблице 7.2."), T, ("Section-header", "Примечания."),
        ("Footnote", "¹ С – северное направление."),                                          # D: table notes
        ("Text", "7.6. Последний пункт.")))))
    assert got["2.5"] == "S/I/7.2/б" and got["2.6"] == "S/I/7.2/б"
    assert got["2.11"] == "S/I/7.3/е"
    assert got["2.15"] == "S/I/7.4"
    assert got["2.18"] == "S/I/7.5"
    # E: numbered notes «1)», «2)» under a notes heading after the annex's last table are the annex's notes
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить нормы."), ("Text", "Министр", 1200)],
             [("Text", "Приложение № 9\nк нормам", 1000), ("Section-header", "Нормы освещенности"), T,
              ("Section-header", "Примечания."), ("Text", "1) Допускается устройство световодов."),
              ("Text", "2) Источники света имеют индекс цветопередачи 85.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.4"] == "A/AN9" and got["2.5"] == "A/AN9"


def test_step_21_3_footnote_without_its_mark_belongs_to_its_page_and_scope():
    # Step 21.3 F (prikaz-minfinansov-198-2015, prikaz-minekonomicheskogo-37-2015): a footnote whose mark is printed
    # nowhere belongs to the document of its page, never to nobody; one whose mark is only on an earlier page follows the
    # footnotes of its own page that found their marks there.
    pages = regulation(("Text", "1. Отчет составляется по форме."), ("Table", "<table><tr><td>8.</td></tr></table>"),
                       ("Footnote", "⁴ В соответствии с приказом от 10.03.2011 № 96/30н."))
    assert owners(S.build(extraction(pages)))["2.4"] in {"S", "S/I/1"}
    pages = [[("Text", "УТВЕРЖДЕН\nприказом", 1000), ("Text", "5.4. Затраты на оплату труда²."), ("Text", "Расчет ведется ежегодно.")],
             [("Text", "5.5. Номенклатура общепроизводственных затрат¹"), ("Table", "<table><tr><td>4.2.3</td></tr></table>"),
              ("Footnote", "¹ В соответствии с приложением № 5."), ("Footnote", "² Индекс рассчитывается как дефлятор.")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.2"] == "S/5.5" and got["2.3"] == "S/5.5"


def test_step_21_4_reference_ranges_root_headings_document_notes_signature_lines_and_dash_items():
    # Step 21.4 A (pp-1521-2014): «10.10 - 10.17), 11 (пункты …» continues item 11, it is no point 10.10
    pages = [[("Text", "УТВЕРЖДЕН\nпостановлением", 1000), ("Section-header", "ПЕРЕЧЕНЬ"),
              ("Section-header", "Национальные стандарты"), ("List-item", "1. ГОСТ Р 54257-2010. Разделы 1, 4."),
              ("List-item", "2. ГОСТ 31937-2011. Разделы 1, 6."),
              ("Section-header", "Своды правил (актуализированные редакции СНиП)"),             # B: root heading
              ("List-item", "3. СП 22.13330.2011. Разделы 1, 4 (пункты 4.2, 4.4), 5 (пункты 5.1.3,")],
             [("List-item", "10.10 - 10.17), 11 (пункты 11.2, 11.3), приложения Л, М."),
              ("List-item", "4. СП 132.13330.2011. Разделы 1, 7, 8."),
              ("List-item", "Примечание. Нормативные документы, на которые имеются ссылки в сводах правил, включенных в "
                            "настоящий перечень, применяются в части, необходимой для соблюдения требований.")]]  # C
    got = owners(S.build(extraction(pages)))
    assert got["1.5"] == "S" and got["2.0"] == "S/3" and got["2.2"] == "S"
    # D, E: signature captions of a form and its date line
    form = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить форму."), ("Text", "Министр", 1200)],
            [("Text", "УТВЕРЖДЕНА\nприказом", 1000), ("Section-header", "ОЦЕНОЧНЫЙ ЛИСТ"),
             ("Text", "1. Сведения о проверке."), ("Text", "2. Обеспечен ли запрет контактов?"),
             ("Text", "(фамилия, имя, отчество (при наличии) должностного лица, заполнившего оценочный лист)"),
             ("Text", "(место для подписи должностного лица, заполнившего оценочный лист)"),
             ("Text", "«___» ______ 20__ г.\n(ФИО, должность) (подпись)")]]
    got = owners(S.build(extraction(form)))
    assert got["2.4"] == "S" and got["2.5"] == "S" and got["2.6"] == "S"
    # F (prikaz-minekonomicheskogo-37-2015): a dash item after the letter list a dash item opened goes back to it
    got = owners(S.build(extraction(regulation(
        ("Text", "2. Индексы применяются:"), ("Text", "- на очередной финансовый год и плановый период:"),
        ("Text", "а) отечественного производства - индекс цен производителей;"),
        ("Text", "б) для продукции по импорту - индекс обменного курса;"),
        ("Text", "- на долгосрочный период - индекс цен на продукцию машиностроения."),
        ("Text", "3. Следующий пункт.")))))
    assert got["2.6"] == "S/I/2"


def test_quoted_article_heading_ending_with_an_inner_title_quote_keeps_the_quotation_open():
    # Step 21.4 G (fz-119-2016): «Статья 25⁸. Особенности … в соответствии с Федеральным законом «Об особенностях …»» ends
    # with the inner title's quote; the quoted article's parts «1.», «2.» are text of article 12 that quotes them.
    pages = [[("Section-header", "Статья 12. О внесении изменения в Федеральный закон"),
              ("Text", "Федеральный закон от 21 июля 1997 года № 122-ФЗ дополнить статьей 25⁸ следующего содержания:"),
              ("List-item", "«Статья 25⁸. Особенности регистрации прав на участки, предоставленные в соответствии с "
                            "Федеральным законом «Об особенностях предоставления гражданам земельных участков»"),
              ("Text", "1. При регистрации права пользования участком регистрируется ограничение."),
              ("Text", "2. Ограничение прекращается одновременно с правом пользования.»."),
              ("Section-header", "Статья 13. О внесении изменений в Земельный кодекс")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.3"] == "A/ст12" and got["1.4"] == "A/ст12"
    assert got["1.5"] == "A/ст13"


def test_step_21_5_approval_sheet_form_fields_repeated_table_headers_and_form_page_heads():
    # Step 21.5 B (prikaz-fas-553-2015): «Лист согласования к проекту документа …» after the act's forms is the act's
    # service tail, not text of the last form's point.
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить форму представления."), ("Text", "Руководитель И.Ю. Артемьев", 1200)],
             [("Text", "Приложение № 13\nк приказу", 1000), ("Section-header", "ПРЕДСТАВЛЕНИЕ"),
              ("Text", "11. Краткая характеристика деятельности кандидата"),
              ("Section-header", "Лист согласования к проекту документа №2015-50720 от 04.06.2015"),
              ("Text", "Инициатор согласования:"), ("Table", "<table><tr><td>№ п/п</td><td>Согласующий</td></tr></table>")]]
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == "A" and got["2.4"] == "A" and got["2.5"] == "A"
    # Step 21.5 C (prikaz-minkultury-1321-2016): after a field line with text and blanks the form's sentence is the form's,
    # the field's caption «(…)» stays with the field and opens no requisite block
    form = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить форму."), ("Text", "Министр", 1200)],
            [("Text", "Приложение № 1\nк Регламенту", 1000), ("Section-header", "ЗАЯВЛЕНИЕ"),
             ("Text", "19. Размер взноса __________"), ("Text", "(тыс. руб. цифрами и прописью)"),
             ("Text", "20. Телефон/факс __________ Адрес электронной почты __________"),
             ("Text", "Прошу внести соответствующие сведения в единый федеральный реестр туроператоров."),
             ("Text", "21. Данные документа, удостоверяющего личность руководителя"),
             ("Text", "(серия, номер, дата выдачи, кем выдан)", 900),
             ("Text", "Телефон/факс ______ Адрес электронной почты ______")]]
    got = owners(S.build(extraction(form)))
    assert got["2.3"] == "A/AN1/19" and got["2.5"] == "A/AN1"
    assert got["2.7"] == "A/AN1/21"
    # Step 21.5 D (rp-2728-2020) not kept: a table part repeating a header stays with the current owner
    H = "<table><thead><tr><th>Наименование мероприятия</th><th>Параметры объекта</th></tr></thead>"
    pages = [[("Text", "1. Утвердить распределение."), ("Text", "Председатель Правительства", 1100)],
             [("Text", "УТВЕРЖДЕНО\nраспоряжением", 1000), ("Section-header", "РАСПРЕДЕЛЕНИЕ"),
              ("Table", H + "<tbody><tr><td>а</td></tr></tbody></table>"), ("List-item", "1. Реконструкция маршрута"),
              ("Text", "мощность - 4,68 км")],
             [("Table", H + "<tbody><tr><td>б</td></tr></tbody></table>")]]
    got = owners(S.build(extraction(pages)))
    # step 21.5 D (repeated header -> previous table) was dropped: it scattered XML-format tables; since step 21.7 H the
    # cut-out row «1.» of a table document is no point, so the table part after it is the document's (`S`)
    assert got["2.3"] == "S"
    # Step 21.5 E (prikaz-fns-815-2024): a declaration page head «1680 6016», «ИНН», «КПП», «Стр.» and a typist mark or
    # time stamp in the text are page marks; a head printed before the form's caption on its page goes to the form
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить форму декларации."),
              ("Text", "21.08.2024 15:44"), ("Text", "компьютер / Н.И. / П-К7552"), ("Text", "Руководитель Д.В. Егоров", 1200)],
             [("Text", "1680 6016"), ("Text", "ИНН¹"), ("Text", "КПП²"), ("Text", "Стр. 0 0 1"),
              ("Text", "Приложение № 1\nк приказу ФНС России", 1000), ("Section-header", "Налоговая декларация"),
              ("Text", "Раздел 1. Сумма акциза")]]
    got = owners(S.build(extraction(pages)))
    assert got["1.2"] == "A" and got["1.3"] == "A"
    assert all(got[f"2.{k}"] == "A/AN1" for k in range(4))


def test_a_plain_text_title_before_a_numbered_caption_makes_a_headed_table():
    # Step 21.6 (sanpin-2-2021): «Предельно допустимые концентрации (ПДК) химических веществ …» as plain text, then
    # «Таблица 3.13» and the table, after a finished point: the table has its own heading -> the section.
    T = ("Table", "<table><tr><td>Азота диоксид</td><td>0,2</td></tr></table>")
    got = owners(S.build(extraction(regulation(
        ("Text", "18. Оценка воды проводится по показателям."),
        ("Text", "Предельно допустимые концентрации (ПДК) химических веществ в воде"), ("Text", "Таблица 3.13"), T,
        ("Text", "19. Контроль проводится лабораториями.")))))
    assert got["2.3"] == "S/I" and got["2.4"] == "S/I" and got["2.5"] == "S/I"


def readmission_form(*parts):
    """An order with one annex form whose parts are «А.», «Б.» … (rp-1829-2015 readmission forms)."""
    return [[("Text", "1. Утвердить прилагаемую форму."), ("Text", "Председатель Правительства", 1100)],
            [("Text", "Приложение № 1 к распоряжению", 900), ("Text", "ЗАПРОС О РЕАДМИССИИ"), *parts]]


def test_step_22_letter_parts_of_a_form_and_their_fields():
    # Step 22 A: «А. Персональные данные», «Б. Особые обстоятельства» open parts with their own points 1, 2 …; D: a blank
    # under a part heading and under a field «2. … ______» stays with them; «Подпись представителя …» opens the
    # form's requisite block.
    got = owners(S.build(extraction(readmission_form(
        ("Text", "А. Персональные данные"), ("Text", "1. Фамилия, имя, отчество ______"),
        ("Text", "2. Документы, дающие основание предполагать гражданство, __________"), ("Text", "__________"),
        ("Text", "Б. Особые обстоятельства"), ("Text", "1. Состояние здоровья"),
        ("Text", "В. Примечания"), ("Text", "__________"),
        ("Text", "Подпись представителя компетентного органа запрашивающей Стороны"), ("Text", "М.П.")))))
    assert [got[f"2.{index}"] for index in range(2, 6)] == ["A/AN1/а", "A/AN1/а/1", "A/AN1/а/2", "A/AN1/а/2"]
    assert got["2.6"] == "A/AN1/б" and got["2.7"] == "A/AN1/б/1"
    assert got["2.8"] == "A/AN1/в" and got["2.9"] == "A/AN1/в"
    assert got["2.10"] == "A/AN1" and got["2.11"] == "A/AN1"
    # a lone «А. …» line (no «Б.» after it) opens no part
    got = owners(S.build(extraction(readmission_form(("Text", "А. Персональные данные"),
                                                     ("Text", "1. Фамилия, имя, отчество ______")))))
    assert got["2.3"] == "A/AN1/1"


def test_step_22_table_document_with_skipped_rubric_numbers_reads_them_as_rows():
    # Step 22 B (rp-22-2015): a plan under «УТВЕРЖДЕН» that is one table; the rubrics «I.», «III.» and rows «1.», «32.»
    # cut out between its parts skip numbers, so they are rows: text of the document (`S`). A standard whose «I.»,
    # «II.» go on without gaps keeps its sections (Mintrud, step 21.7 H).
    head = [[("Text", "1. Утвердить прилагаемый план."), ("Text", "Председатель Правительства", 1100)],
            [("Text", "УТВЕРЖДЕН\nраспоряжением Правительства", 1000), ("Section-header", "ПЛАН"), MEASURES]]
    got = owners(S.build(extraction(head[:1] + [head[1] + [
        ("Section-header", "I. Общие мероприятия"), ("Text", "1. Разработка документации"), MEASURES,
        ("Text", "32. Реализация мероприятий"), ("Section-header", "III. Наука и образование"), MEASURES]])))
    assert [got[f"2.{index}"] for index in range(3, 9)] == ["S"] * 6
    # Step 22 C (pp-648-2016): a field ending in a date blank «"__" ______ 20__ г.» hands the table under it to the form
    got = owners(S.build(extraction(readmission_form(
        ("Text", "1. Дата предоставления кредита __________"),
        ("Text", '2. Дата уплаты процентов по кредиту "__" __________ 20__ г.'), MEASURES,
        ("Text", "Размер субсидии __________ рублей")))))
    assert got["2.4"] == "A/AN1" and got["2.5"] == "A/AN1"


def protocol(*body):
    """An order approving a protocol to an international agreement (rp-1622-2020)."""
    return [[("Text", "1. Одобрить проект Протокола."), ("Text", "Председатель Правительства", 1100)],
            [("Page-header", "Проект", 900), ("Section-header", "ПРОТОКОЛ"),
             ("Text", "Стороны согласились о нижеследующем:"), *body]]


def test_step_23_roman_articles_and_a_quotation_across_a_page_footer():
    # Step 23 A: «Статья I», «Статья II» of a treaty are articles 1, 2 with their own points; B: a page footer
    # «4557147.doc» between «… в следующей редакции:» and «"Статья VI» does not break the quotation.
    got = owners(S.build(extraction(protocol(
        ("Section-header", "Статья I"), ("Text", "1. В подпункте b слово исключить."), ("Text", "2. Слова заменить."),
        ("Section-header", "Статья II"), ("Text", "Статью VI Соглашения изложить в следующей редакции:"),
        ("Page-footer", "4557147.doc"), ("Section-header", '"Статья VI'),
        ("Text", "1. Стороны будут обеспечивать извещения."), ("Text", '2. Каждая из Сторон предпримет меры."')))))
    assert got["2.3"] == "S/ст1" and got["2.4"] == "S/ст1/1" and got["2.5"] == "S/ст1/2"
    assert got["2.6"] == "S/ст2" and [got[f"2.{index}"] for index in (7, 9, 10, 11)] == ["S/ст2"] * 4


def test_step_23_an_annex_of_a_form_inside_an_attached_document():
    # Step 23 C, E (prikaz-minprirodnykh-955-2021, prikaz-fns-269-2020): «Приложение 1 к акту патрулирования лесов» after
    # the Order's annex 3 «АКТ патрулирования лесов» is that form's annex (`…/AN3/AN1`); «Приложение 4 к Порядку» goes
    # on with the Order's annexes.
    def caption(text):
        return ("Text", text, 900)
    pages = [[("Title", "ПРИКАЗ"), ("Text", "1. Утвердить Порядок.")],
             [caption("Приложение 1 к приказу Минприроды России"), ("Section-header", "Порядок осуществления лесной охраны"),
              ("Text", "1. Лесная охрана осуществляется органами власти.")],
             [caption("Приложение 3 к Порядку осуществления лесной охраны"), ("Section-header", "АКТ патрулирования лесов"),
              ("Text", "Дата патрулирования ______")],
             [caption("Приложение 1 к акту патрулирования лесов"), ("Text", "ФОТО № ______")],
             [caption("Приложение 4 к Порядку осуществления лесной охраны"), ("Text", "Рекомендуемый образец")]]
    got = owners(S.build(extraction(pages)))
    assert got["3.0"] == "A/AN1/AN3" and got["4.0"] == "A/AN1/AN3/AN1" and got["4.1"] == "A/AN1/AN3/AN1"
    assert got["5.0"] == "A/AN1/AN4"
    # a form caption with its long tail (date, number, title, «Форма») still opens the form's annex 1
    pages[3] = [caption("Приложение к акту патрулирования лесов от «21» 04 2020г. № 48-7-15/2692 о проведении "
                        "патрулирования лесов на территории лесничества в границах лесного участка Форма"),
                ("Text", "ФОТО № ______")]
    got = owners(S.build(extraction(pages)))
    assert got["4.0"] == "A/AN1/AN3/AN1"


def test_step_23_subheading_after_a_page_mark_and_a_second_fill_in_list():
    # Step 23 D: a typist's mark at the page foot does not hide a subheading's finished point; F: «1. ______;» after a
    # fill-in «2. ______;» starts a second list of the form, not a subpoint.
    got = owners(S.build(extraction(regulation(
        ("Text", "13. Услуга называется выдачей свидетельства."), ("Page-footer", "компьютер /Ю.Р. /Прил-И301-1"),
        ("Section-header", "Наименование органа, предоставляющего услугу"), ("Text", "14. Услугу предоставляет ФНС России."),
        ("Section-header", "Порядок обжалования решений"), ("Text", "15. Жалоба подается в письменной форме.")))))
    assert got["2.4"] == "S/I"
    got = owners(S.build(extraction(readmission_form(
        ("Text", "Адрес:"), ("Text", "1. __________;"), ("Text", "2. __________;"), ("Text", "ИНН организации:"),
        ("Text", "Реквизиты документов:"), ("Text", "1. __________;"), ("Text", "2. __________;")))))
    assert got["2.3"] == "A/AN1/1" and got["2.4"] == "A/AN1/2" and got["2.5"] == "A/AN1"
    assert got["2.7"] == "A/AN1/1" and got["2.8"] == "A/AN1/2"


def test_step_24_bare_decimal_form_positions_keep_their_field_captions():
    pages = readmission_form(
        ("Text", "1. Сведения о территории"), ("Text", "1.1."),
        ("Text", "(наименование субъекта Российской Федерации)"), ("Text", "1.2."),
        ("Text", "(перечень муниципальных образований)"), ("Text", "2. Обоснование создания территории"))
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == got["2.4"] == "A/AN1/1/1.1"
    assert got["2.5"] == got["2.6"] == "A/AN1/1/1.2"
    assert S.parse_marker("12.02.2026", "Text").kind == "none"


def test_step_24_bare_decimal_table_rubric_without_a_field_caption_opens_no_point():
    got = owners(S.build(extraction(readmission_form(
        ("Text", "1. Сведения о трудовой функции"), ("Text", "1.1."),
        ("Table", "<table><tr><td>Наименование</td><td>Код</td></tr></table>"),
        ("Text", "Уровень квалификации")))))
    assert got["2.3"] == got["2.4"] == "A/AN1/1"


@pytest.mark.parametrize("category", ["Text", "Page-header"])
def test_step_24_form_sheet_marks_are_separate_from_the_field_across_pages(category):
    pages = readmission_form(
        ("Text", "2. Сведения о лицах"), ("Text", "Место для служебных отметок регистрирующего органа"))
    pages.append([(category, "оборотная сторона листа № 1"), ("Text", "продолжение сведений о лицах.")])
    got = owners(S.build(extraction(pages)))
    assert got["2.3"] == got["3.0"] == "A/AN1"
    assert got["2.2"] == got["3.1"] == "A/AN1/2"


def test_step_24_bold_body_subheadings_use_the_section_without_rewriting_the_text():
    heading = "**Порядок предоставления государственной услуги**"
    ext = extraction(regulation(("Text", "46. Государственная пошлина возвращается."),
                                ("Text", heading), ("Text", "47. Плата за услугу не предусмотрена.")))
    before = copy.deepcopy(ext)
    got = owners(S.build(ext))
    assert got["2.3"] == "S/I"
    assert ext == before
    # A bold sentence with a final period is still text of the point.
    got = owners(S.build(extraction(regulation(
        ("Text", "46. Государственная пошлина возвращается."),
        ("Text", "**Плата за услугу не предусмотрена.**"), ("Text", "47. Заявитель подает запрос.")))))
    assert got["2.3"] == "S/I/46"


def test_step_24_bold_sentence_after_a_signer_opens_no_attached_document():
    pages = [[("Text", "1. Утвердить прилагаемый Регламент."), ("Text", "Министр", 1200)],
             [("Text", "**Документы направляются по почте.**")]]
    assert owners(S.build(extraction(pages)))["2.0"] == "A"


@pytest.mark.parametrize("closing", ["Составлен ______ 20______.", "Ответ на запрос прошу направить __________"])
def test_step_24_form_completion_and_reply_address_start_the_requisite_tail(closing):
    got = owners(S.build(extraction(readmission_form(
        ("Text", "6. Срок действия ______ (лет)"), ("Text", closing),
        ("Text", "(указывается полный почтовый адрес)"), ("Text", "Начальник __________")))))
    assert all(got[f"2.{i}"] == "A/AN1" for i in (3, 4, 5))
    assert got["2.2"] == "A/AN1/6"
