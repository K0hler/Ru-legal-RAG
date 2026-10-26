"""Authored controls for the M1-04A JSON corpus stand (``m1_04a_json_baseline.py``); no corpus files."""

import importlib.util
import json
import sys
from pathlib import Path

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
