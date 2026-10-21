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
