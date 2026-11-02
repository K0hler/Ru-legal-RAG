"""Authored controls for the M1-04A JSON corpus stand (``m1_04a_json_baseline.py``); no corpus files."""

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[3] / "docs" / "assets"


def load_script(name):
    if str(ASSETS) not in sys.path:
        sys.path.insert(0, str(ASSETS))  # the script imports evaluate_ocr_owner_gold from docs/assets
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


J = load_script("m1_04a_json_baseline")


def fake_corpus(root: Path) -> Path:
    for slug, text in (("pp-a", "Первый акт."), ("pp-b", "Второй акт.")):
        doc = root / "docs" / slug
        doc.mkdir(parents=True)
        (doc / "document.html").write_text(f'<p id="p1">{text}</p>', encoding="utf-8")
        (doc / "document_content.json").write_text(json.dumps({"data": []}), encoding="utf-8")
    (root / "split.json").write_text(json.dumps({"dev": ["pp-a"], "holdout": ["pp-b"]}), encoding="utf-8")
    return root


def test_split_all_projects_dev_then_holdout_as_development(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "CORPUS", fake_corpus(tmp_path / "corpus"))
    out = tmp_path / "all"
    J.phase_project(out, projection=4, part="all")
    freeze = json.loads((out / "freeze.json").read_text(encoding="utf-8"))
    assert list(freeze["stats"]) == ["pp-a", "pp-b"] and freeze["split_part"] == "all"
    assert (out / "pp-b" / "gold.txt").read_text(encoding="utf-8").splitlines()[1:] == ["1.0 A"]


def test_split_parts_keep_their_slugs():
    split = {"dev": ["a", "c"], "holdout": ["b"]}
    assert J.split_slugs(split, "dev") == ["a", "c"]
    assert J.split_slugs(split, "holdout") == ["b"]
    assert J.split_slugs(split, "all") == ["a", "c", "b"]


def test_projection_5_bare_numbered_subsection_is_a_point():
    # Convention v2 §6.1 (owner decision 26.10.2026): «1.» inside a concept section is a point, not a section;
    # a subsection captioned with the word («Подраздел 1») stays a section.
    nodes = [{"id": "r", "lvl": 0, "unit": "раздел", "caption": "I. Общие положения", "np": "p1", "npe": "p3"},
             {"id": "s1", "lvl": 1, "unit": "подраздел", "caption": "1. Мировые тенденции", "np": "p2", "npe": "p2"},
             {"id": "s2", "lvl": 1, "unit": "подраздел", "caption": "Подраздел 2. Цели", "np": "p3", "npe": "p3"}]
    order = {"p1": 0, "p2": 1, "p3": 2}
    first = {"p1": "I. Общие положения", "p2": "1. Мировые тенденции", "p3": "Подраздел 2. Цели"}
    paths4, _ = J.node_paths(nodes, order, first, projection=4)
    paths5, _ = J.node_paths(nodes, order, first, projection=5)
    assert (paths4["s1"], paths4["s2"]) == ("A/I/разд1", "A/I/разд2")
    assert (paths5["s1"], paths5["s2"]) == ("A/I/1", "A/I/разд2")


def test_projection_6_article_notes_are_transparent():
    # IPS stores article notes as «вложение» nodes («Примечания» with «примечание 1», «примечание 2<sup>1</sup>»);
    # they are notes of the article, not annexes: projection 6 gives their paragraphs to the article.
    nodes = [{"id": "a", "lvl": 0, "unit": "статья", "caption": "Статья 9.1. Нарушение", "np": "p1", "npe": "p5"},
             {"id": "c4", "lvl": 1, "unit": "часть", "caption": "часть 4", "np": "p2", "npe": "p2"},
             {"id": "n", "lvl": 1, "unit": "вложение", "caption": "Примечания", "np": "p3", "npe": "p5"},
             {"id": "n1", "lvl": 2, "unit": "вложение", "caption": "примечание 1", "np": "p4", "npe": "p4"},
             {"id": "n2", "lvl": 2, "unit": "вложение", "caption": "примечание 2<sup>1</sup>", "np": "p5", "npe": "p5"}]
    order = {f"p{i}": i - 1 for i in range(1, 6)}
    first = {"p1": "Статья 9.1. Нарушение", "p2": "4. Дача ложного заключения", "p3": "Примечания:",
             "p4": "1. Под грубым нарушением понимается", "p5": "2¹. Для целей настоящей статьи"}
    paths5, _ = J.node_paths(nodes, order, first, projection=5)
    paths6, _ = J.node_paths(nodes, order, first, projection=6)
    assert (paths5["n"], paths5["n1"]) == ("A/ст9.1/AN1", "A/ст9.1/AN1/AN1")
    assert (paths6["c4"], paths6["n"], paths6["n1"], paths6["n2"]) == ("A/ст9.1/ч4", None, None, None)
    owners6 = J.paragraph_owners(nodes, order, first, projection=6)
    assert [owners6[f"p{i}"][0] for i in range(1, 6)] == ["A/ст9.1", "A/ст9.1/ч4", "A/ст9.1", "A/ст9.1", "A/ст9.1"]


def test_project_reads_the_corpus_given_on_the_command_line(tmp_path):
    corpus = fake_corpus(tmp_path / "v2")
    out = tmp_path / "proj"
    J.main(["project", "--out", str(out), "--split", "holdout", "--corpus", str(corpus)])
    freeze = json.loads((out / "freeze.json").read_text(encoding="utf-8"))
    assert list(freeze["stats"]) == ["pp-b"] and freeze["corpus"] == corpus.name


@pytest.mark.parametrize("act_type", ["Распоряжение", "Послание"])
def test_projection_7_current_act_wrapper_uses_source_type_and_start(act_type):
    nodes = [{"id": "act", "lvl": 0, "unit": "вложение", "caption": act_type, "np": "p8", "npe": "p10"},
             {"id": "point", "lvl": 1, "unit": "пункт", "caption": "пункт 1", "np": "p9", "npe": "p10"}]
    order = {"p8": 0, "p9": 1, "p10": 2}
    first = {"p8": act_type.upper(), "p9": "1. Основной текст.", "p10": "Продолжение."}
    before = deepcopy((nodes, order, first))
    paths, _ = J.node_paths(nodes, order, first, projection=7, act_type=act_type)
    owners = J.paragraph_owners(nodes, order, first, projection=7, act_type=act_type)
    assert paths == {"act": None, "point": "A/1"}
    assert owners == {"p8": ("A", None), "p9": ("A/1", None), "p10": ("A/1", None)}
    assert (nodes, order, first) == before
    for projection in range(1, 7):
        old = J.node_paths(deepcopy(nodes), order, first, projection=projection, act_type=act_type)
        assert (old if projection == 1 else old[0]) == {"act": "S", "point": "S/1"}


@pytest.mark.parametrize(("act_type", "changes", "first_text"), [
    (None, {}, "РАСПОРЯЖЕНИЕ"),
    ("", {}, "РАСПОРЯЖЕНИЕ"),
    ("Постановление", {}, "РАСПОРЯЖЕНИЕ"),
    ("Распоряжение", {"np": "p9"}, "РАСПОРЯЖЕНИЕ"),
    ("Распоряжение", {"np": "missing"}, "РАСПОРЯЖЕНИЕ"),
    ("Распоряжение", {"npe": "missing"}, "РАСПОРЯЖЕНИЕ"),
    ("Распоряжение", {}, ""),
])
def test_projection_7_refuses_wrapper_without_positive_source_evidence(act_type, changes, first_text):
    nodes = [{"id": "act", "lvl": 0, "unit": "вложение", "caption": "Распоряжение",
              "np": "p8", "npe": "p10", **changes}]
    paths, _ = J.node_paths(nodes, {"p8": 0, "p9": 1, "p10": 2}, {"p8": first_text},
                            projection=7, act_type=act_type)
    assert paths == {"act": "S"}


def test_projection_7_keeps_later_and_nested_same_type_attachments():
    nodes = [{"id": "act", "lvl": 0, "unit": "вложение", "caption": "Распоряжение", "np": "p1", "npe": "p2"},
             {"id": "later", "lvl": 0, "unit": "вложение", "caption": "Распоряжение", "np": "p3", "npe": "p5"},
             {"id": "nested", "lvl": 1, "unit": "вложение", "caption": "Распоряжение", "np": "p3", "npe": "p5"},
             {"id": "point", "lvl": 2, "unit": "пункт", "caption": "пункт 1", "np": "p4", "npe": "p5"}]
    order = {f"p{i}": i - 1 for i in range(1, 6)}
    first = {"p1": "РАСПОРЯЖЕНИЕ", "p3": "РАСПОРЯЖЕНИЕ", "p4": "1. Текст вложения."}
    paths, _ = J.node_paths(nodes, order, first, projection=7, act_type="Распоряжение")
    assert paths == {"act": None, "later": "S", "nested": "S/AN1", "point": "S/AN1/1"}


def test_projection_7_explicit_approval_outranks_current_act_wrapper():
    nodes = [{"id": "act", "lvl": 0, "unit": "вложение", "caption": "Распоряжение", "np": "p1", "npe": "p2"},
             {"id": "point", "lvl": 1, "unit": "пункт", "caption": "пункт 1", "np": "p2", "npe": "p2"}]
    first = {"p1": "УТВЕРЖДЕНО распоряжением от 01.01.2026 № 1", "p2": "1. Правило."}
    paths, _ = J.node_paths(nodes, {"p1": 0, "p2": 1}, first, projection=7, act_type="Распоряжение")
    assert paths == {"act": "S", "point": "S/1"}


@pytest.mark.parametrize("card", [None, {}, {"type": "Распоряжение"}, {"type": "Постановление"}])
def test_project_7_reads_optional_card_type_without_changing_sources(tmp_path, monkeypatch, card):
    corpus = fake_corpus(tmp_path / "corpus")
    doc = corpus / "docs" / "pp-a"
    (doc / "document.html").write_text('<p id="p1">РАСПОРЯЖЕНИЕ</p><p id="p2">1. Текст.</p>', encoding="utf-8")
    nodes = [{"id": "act", "lvl": 0, "unit": "вложение", "caption": "Распоряжение", "np": "p1", "npe": "p2"},
             {"id": "point", "lvl": 1, "unit": "пункт", "caption": "пункт 1", "np": "p2", "npe": "p2"}]
    (doc / "document_content.json").write_text(json.dumps({"data": nodes}), encoding="utf-8")
    if card is not None:
        (doc / "card.json").write_text(json.dumps(card), encoding="utf-8")
    before = {p: p.read_bytes() for p in corpus.rglob("*") if p.is_file()}
    monkeypatch.setattr(J, "CORPUS", corpus)
    out = tmp_path / "projection7"
    J.main(["project", "--out", str(out), "--projection", "7"])
    root = "A" if card and card.get("type") == "Распоряжение" else "S"
    assert (out / "pp-a" / "gold.txt").read_text(encoding="utf-8").splitlines()[1:] == [f"1.0 {root}", f"1.1 {root}/1"]
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("projection", range(1, 7))
def test_older_projections_do_not_read_card(tmp_path, monkeypatch, projection):
    corpus = fake_corpus(tmp_path / "corpus")
    (corpus / "docs" / "pp-a" / "card.json").write_text("invalid JSON", encoding="utf-8")
    monkeypatch.setattr(J, "CORPUS", corpus)
    J.phase_project(tmp_path / "out", projection=projection)


@pytest.mark.parametrize("unit", ["раздел", "подраздел"])
def test_projection_7_bare_dotted_section_keeps_its_printed_full_number(unit):
    nodes = [{"id": "c", "lvl": 0, "unit": "глава", "caption": "Глава 1", "np": "p1", "npe": "p4"},
             {"id": "s1", "lvl": 1, "unit": unit, "caption": "1.1. Экономика", "np": "p2", "npe": "p2"},
             {"id": "s2", "lvl": 1, "unit": unit, "caption": "1.2. Политика", "np": "p3", "npe": "p3"},
             {"id": "worded", "lvl": 1, "unit": unit, "caption": "Раздел 1. Цели", "np": "p4", "npe": "p4"}]
    order = {f"p{i}": i - 1 for i in range(1, 5)}
    first = {n["np"]: n["caption"] for n in nodes}
    old, _ = J.node_paths(deepcopy(nodes), order, first, projection=6)
    new, _ = J.node_paths(nodes, order, first, projection=7)
    assert (old["s1"], old["s2"]) == ("A/гл1/1", "A/гл1/1")
    assert (new["s1"], new["s2"], new["worded"]) == ("A/гл1/1.1", "A/гл1/1.2", "A/гл1/разд1")


@pytest.mark.parametrize("text", ["Экономика", "1.2. Другой номер", "1.1 без разделителя"])
def test_projection_7_does_not_extend_dotted_section_without_printed_number(text):
    nodes = [{"id": "s", "lvl": 0, "unit": "раздел", "caption": "1.1. Экономика", "np": "p1", "npe": "p1"}]
    paths, _ = J.node_paths(nodes, {"p1": 0}, {"p1": text}, projection=7)
    assert paths == {"s": "A/1"}
