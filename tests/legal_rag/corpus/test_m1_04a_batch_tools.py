"""Authored controls for the M1-04A check-pool batch tools; no corpus files or OCR engine."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[3] / "docs" / "assets"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


B = load_script("build_m1_04a_annotation_input")
R = load_script("run_m1_04a_first_pass")
F = load_script("freeze_m1_04a_gold")


def extraction():
    """Two pages: picture, title, text; page 2 has a bare page-number header (noise)."""
    pages = [
        [("Picture", ""), ("Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"), ("Text", "Статья 1\nТекст\tнормы")],
        [("Page-header", "2"), ("Text", "продолжение нормы."), ("Picture", "2 100039 06204 3")],
    ]
    out = {"pages": [], "blocks": [], "text_nodes": []}
    for pno, regions in enumerate(pages, start=1):
        page = {"page": pno, "regions": []}
        for index, (category, text) in enumerate(regions):
            rid = f"r{pno}-{index}"
            page["regions"].append({"region_id": rid, "category": category, "bbox": [100, 100 + 50 * index, 900, 140]})
            if text:
                out["text_nodes"].append({"text_node_id": f"t{rid}", "raw_text": text})
                out["blocks"].append({"source_region_id": rid, "original_text": text, "text_node_ids": [f"t{rid}"]})
        out["pages"].append(page)
    return out


def test_v1_input_has_no_stage2_columns_and_skips_pictures_and_noise():
    data, info = B.v1_tsv("act", extraction())
    lines = data.decode("utf-8").splitlines()
    assert lines[1] == "# key\tcategory\ttext"
    rows = [line.split("\t") for line in lines if not line.startswith("#")]
    assert rows == [["1.1", "Title", "ФЕДЕРАЛЬНЫЙ ЗАКОН"],
                    ["1.2", "Text", "Статья 1 ⏎ Текст нормы"],
                    ["2.1", "Text", "продолжение нормы."]]
    assert "P=" not in lines[0] and "join" not in lines[0]
    assert info == {"regions": 3, "excluded": {"picture": ["1.0", "2.2"], "noise": ["2.0"]}}
    assert lines[-2] == "# not annotated (Picture): 1.0 2.2"
    assert lines[-1] == "# not annotated (noise: page numbers/running text): 2.0"


def test_legacy_input_still_carries_stage2_columns():
    from legal_rag.corpus.logical_text import build_logical_text

    lines = B.legacy_tsv("act", build_logical_text(extraction())).decode("utf-8").splitlines()
    assert lines[1] == "# key\tcategory\tP\tjoin\ttext"
    assert any(line.startswith("1.0\tPicture\tP") for line in lines)


def test_convention_filter_excludes_pictures_and_noise_only_in_v1():
    gold = {key: {"owners": ["A"], "continuation": False} for key in ("1.0", "1.1", "1.2", "2.1", "2.2")}
    kept, removed = R.apply_convention(gold, extraction(), "v1")
    assert list(kept) == ["1.1", "1.2", "2.1"] and removed == ["1.0", "2.2"]
    kept, removed = R.apply_convention(gold, extraction(), "all-regions")
    assert kept == gold and removed == []
    assert R.excluded_keys(extraction(), "v1") == {"1.0", "2.2", "2.0"}
    with pytest.raises(ValueError):
        R.apply_convention(gold, extraction(), "v2")


def test_gold_freeze_hashes_annotation_input_and_is_write_once(tmp_path):
    gold = tmp_path / "data" / "m1" / "m1-04a" / "gold" / "act"
    gold.mkdir(parents=True)
    (gold / "agent-act.gold.txt").write_text("1.1 A\n", encoding="utf-8")
    (gold / "annotation-notes.md").write_text("notes\n", encoding="utf-8")
    inp = tmp_path / "input"
    inp.mkdir()
    (inp / "act.regions.tsv").write_bytes(b"# key\tcategory\ttext\n1.1\tText\tx\n")
    (inp / "manifest.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "freeze"
    record = F.freeze(out, ["act"], inp, "test annotator", root=tmp_path)
    assert set(record["annotation_input"]) == {"input/act.regions.tsv", "input/manifest.json"}
    assert record["annotation_convention"] == "m1-04a-annotation/v1"
    assert json.loads((out / "freeze.json").read_text(encoding="utf-8"))["files"] == record["files"]
    assert (gold / "agent-act.sha256").read_text(encoding="utf-8").endswith("  agent-act.gold.txt\n")
    with pytest.raises(FileExistsError):
        F.freeze(out, ["act"], inp, "again", root=tmp_path)
    (gold / "agent-act.gold.txt").write_text("1.1 S\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        F.freeze(tmp_path / "freeze-2", ["act"], inp, "changed gold", root=tmp_path)
