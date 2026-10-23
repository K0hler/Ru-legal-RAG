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
    assert got["2.4"] is None                                # marker ³ absent: owner stays unresolved


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
    # a body-text line over 200 characters is not a subheading without heading evidence
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
