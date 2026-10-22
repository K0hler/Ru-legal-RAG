"""Authored controls for the M1-04A v1 -> v2 gold derivation; no corpus files."""

import hashlib
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


D = load_script("derive_m1_04a_gold_v2")

GOLD = [
    "# convention: m1-04a-annotation/v1",
    "1.0 A",
    "2.0 S",
    "2.1 S/II/4",
    "2.2 S/II/4.1 +",
    "2.3 S/II/4.1.2",
    "2.4 S/II/4.2/а",
    "2.5 S/III/2.1",
    "2.6 A/ст12.1/ч1",
    "3.0 S2",
    "3.1 S2/1/а|S2/1",
    "4.0 S3/5.1",
]


def test_annex_of_attached_document_and_nested_dotted_points():
    lines, counts = D.derive_lines(GOLD, {"S2": "S/AN1", "S3": "S/AN2"})
    assert lines == [
        "# convention: m1-04a-annotation/v1",
        "1.0 A",
        "2.0 S",
        "2.1 S/II/4",
        "2.2 S/II/4/4.1 +",
        "2.3 S/II/4/4.1/4.1.2",
        "2.4 S/II/4/4.2/а",
        "2.5 S/III/2.1",  # no point «2.» in section III: stays flat
        "2.6 A/ст12.1/ч1",  # typed article number is never nested
        "3.0 S/AN1",
        "3.1 S/AN1/1/а|S/AN1/1",
        "4.0 S/AN2/5.1",  # no point «5.» in that annex: stays flat
    ]
    assert counts == {"lines": 11, "scope": 3, "nested": 3, "changed": 6}


def test_sibling_must_be_in_the_same_parent():
    lines, _ = D.derive_lines(["1.0 S/I/4", "1.1 S/II/4.1"], {})
    assert lines == ["1.0 S/I/4", "1.1 S/II/4.1"]


def test_empty_map_and_no_dotted_points_change_nothing():
    lines, counts = D.derive_lines(["# c", "1.0 A/ст1/ч2", "1.1 S/3/б +"], {})
    assert lines == ["# c", "1.0 A/ст1/ч2", "1.1 S/3/б +"]
    assert counts["changed"] == 0


@pytest.mark.parametrize("annexes", [{"S": "S/AN1"}, {"S2": "S3"}, {"S2": "S/AN1", "S3": "S/AN1"},
                                     {"S9": "S/AN1"}])
def test_bad_or_stale_map_is_refused(annexes):
    with pytest.raises(ValueError):
        D.derive_lines(["1.0 S2/1", "1.1 S3"], annexes)


def test_map_target_already_in_gold_is_refused():
    with pytest.raises(ValueError):
        D.derive_lines(["1.0 S2/1", "1.1 S/AN1/2"], {"S2": "S/AN1"})


def write_case(tmp_path, gold_text, annexes, gold_sha=None):
    slug_dir = tmp_path / "doc-1-2026"
    slug_dir.mkdir()
    gold = slug_dir / "agent-doc-1-2026.gold.txt"
    gold.write_bytes(gold_text.encode("utf-8"))
    record = {"schema_version": D.MAP_SCHEMA, "source_gold_sha256": gold_sha or hashlib.sha256(gold.read_bytes()).hexdigest(),
              "attached_annexes": annexes}
    (slug_dir / "agent-doc-1-2026.v2-map.json").write_text(json.dumps(record), encoding="utf-8")
    return slug_dir, gold


def test_derive_writes_once_and_keeps_v1_gold(tmp_path):
    slug_dir, gold = write_case(tmp_path, "# v1\n1.0 S\n1.1 S/4\n1.2 S/4.1\n2.0 S2 +\n", {"S2": "S/AN1"})
    before = gold.read_bytes()
    report = D.derive(slug_dir, write=True)
    assert report["changed"] == 2 and gold.read_bytes() == before
    out = (slug_dir / "agent-doc-1-2026.gold-v2.txt").read_text(encoding="utf-8").splitlines()
    assert out[0] == "# convention: m1-04a-annotation/v2" and out[1].startswith("# derived:")
    assert out[2:] == ["# v1", "1.0 S", "1.1 S/4", "1.2 S/4/4.1", "2.0 S/AN1 +"]
    receipt = (slug_dir / "agent-doc-1-2026.gold-v2.sha256").read_text(encoding="utf-8").splitlines()
    digest = hashlib.sha256((slug_dir / "agent-doc-1-2026.gold-v2.txt").read_bytes()).hexdigest()
    assert receipt[0] == f"{digest}  agent-doc-1-2026.gold-v2.txt"
    with pytest.raises(FileExistsError):
        D.derive(slug_dir, write=True)


def test_derive_refuses_a_map_for_another_gold(tmp_path):
    slug_dir, _ = write_case(tmp_path, "1.0 S2\n", {"S2": "S/AN1"}, gold_sha="0" * 64)
    with pytest.raises(SystemExit):
        D.derive(slug_dir, write=True)
    assert not (slug_dir / "agent-doc-1-2026.gold-v2.txt").exists()
