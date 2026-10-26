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
