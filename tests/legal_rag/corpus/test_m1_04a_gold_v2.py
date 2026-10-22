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


def test_flat_dotted_exception_stays_flat_and_children_nest_under_it():
    gold = ["1.0 S/II/4", "1.1 S/II/4.1", "1.2 S/II/4.2", "1.3 S/II/4.1.2"]
    lines, _ = D.derive_lines(gold, {}, ["S/II/4.1"])
    assert lines == ["1.0 S/II/4", "1.1 S/II/4.1", "1.2 S/II/4/4.2", "1.3 S/II/4.1/4.1.2"]
    default, _ = D.derive_lines(gold, {})
    assert default == D.derive_lines(gold, {}, [])[0] != lines


@pytest.mark.parametrize("entry", ["", "S/II/4", "S//4.1", 5])
def test_bad_flat_dotted_entry_is_refused(entry):
    with pytest.raises(ValueError):
        D.derive_lines(["1.0 S/4"], {}, [entry])


def test_exceptions_json_and_map_flat_dotted_are_applied_and_recorded(tmp_path):
    slug_dir, _ = write_case(tmp_path, "1.0 S/4\n1.1 S/4.1\n1.2 S/4.2\n1.3 S/5\n1.4 S/5.1\n", {})
    (slug_dir / "exceptions.json").write_text(json.dumps(
        {"schema_version": D.EXCEPTIONS_SCHEMA, "flat_dotted": ["S/4.1"]}), encoding="utf-8")
    map_path = slug_dir / "agent-doc-1-2026.v2-map.json"
    record = json.loads(map_path.read_text(encoding="utf-8"))
    record["flat_dotted"] = ["S/5.1"]
    map_path.write_text(json.dumps(record), encoding="utf-8")
    report = D.derive(slug_dir, write=True)
    assert report["flat_dotted"] == ["S/4.1", "S/5.1"]
    out = (slug_dir / "agent-doc-1-2026.gold-v2.txt").read_text(encoding="utf-8").splitlines()
    assert out[-5:] == ["1.0 S/4", "1.1 S/4.1", "1.2 S/4/4.2", "1.3 S/5", "1.4 S/5.1"]
    assert "S/4.1, S/5.1" in out[1]


def test_without_exceptions_output_is_unchanged(tmp_path):
    slug_dir, _ = write_case(tmp_path, "1.0 S/4\n1.1 S/4.1\n", {})
    assert "flat_dotted" not in D.derive(slug_dir, write=True)
    out = (slug_dir / "agent-doc-1-2026.gold-v2.txt").read_text(encoding="utf-8")
    assert "flat dotted" not in out and "1.1 S/4/4.1" in out


def test_flat_dotted_entry_in_v1_scope_follows_annex_rename():
    gold = ["1.0 S2/4", "1.1 S2/4.1", "1.2 S2/4.2"]
    for entry in ("S2/4.1", "S/AN1/4.1"):
        lines, _ = D.derive_lines(gold, {"S2": "S/AN1"}, [entry])
        assert lines == ["1.0 S/AN1/4", "1.1 S/AN1/4.1", "1.2 S/AN1/4/4.2"]


def test_unmatched_flat_dotted_entry_raises():
    with pytest.raises(ValueError, match="match no owner path"):
        D.derive_lines(["1.0 S/4", "1.1 S/4.1"], {}, ["S/9.9"])


def test_receipt_records_exceptions_hash_and_check_validates_map_schema(tmp_path):
    slug_dir, _ = write_case(tmp_path, "1.0 S/4\n1.1 S/4.1\n", {})
    ex = slug_dir / "exceptions.json"
    ex.write_text(json.dumps({"schema_version": D.EXCEPTIONS_SCHEMA, "flat_dotted": ["S/4.1"]}), encoding="utf-8")
    D.derive(slug_dir, write=True)
    receipt = (slug_dir / "agent-doc-1-2026.gold-v2.sha256").read_text(encoding="utf-8")
    assert f"{hashlib.sha256(ex.read_bytes()).hexdigest()}  exceptions.json" in receipt
    map_path = slug_dir / "agent-doc-1-2026.v2-map.json"
    map_path.write_text(json.dumps({"schema_version": "bad", "flat_dotted": []}), encoding="utf-8")
    with pytest.raises(SystemExit):
        D.derive(slug_dir, write=False)
