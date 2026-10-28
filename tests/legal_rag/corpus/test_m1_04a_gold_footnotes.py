"""Authored controls for the M1-04A footnote-owner gold derivation; no corpus files."""

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


D = load_script("derive_m1_04a_gold_footnotes")
GOLD = ["# convention: m1-04a-annotation/v2", "1.1 S/I/1.1", "1.2 S", "2.1 S/I/1.2 +", "2.2 S +", "3.1 S/II/2.1", ""]


def write_gold(tmp_path, slug, lines=GOLD):
    folder = tmp_path / slug
    folder.mkdir()
    (folder / f"agent-{slug}.gold.txt").write_bytes("\n".join(lines).encode())
    return folder


def write_map(folder, slug, regions, pin=None):
    frozen = folder / f"agent-{slug}.gold.txt"
    (folder / f"agent-{slug}.footnotes-map.json").write_text(json.dumps({
        "schema_version": "m1-04a-gold-footnotes-map/1",
        "gold_sha256": pin or hashlib.sha256(frozen.read_bytes()).hexdigest(), "regions": regions}), encoding="utf-8")


def test_mapped_footnotes_move_to_the_marked_point_and_keep_continuation(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "sanpin-x")
    write_map(folder, "sanpin-x", {"1.2": {"from": "S", "owner": "S/I/1.1", "mark": "1.1"},
                                   "2.2": {"from": "S", "owner": "S/I/1.2|S/II/2.1", "mark": "2.1, 3.1"}})
    assert D.derive("sanpin-x") == {"slug": "sanpin-x", "mapped": True, "changed_rows": 2}
    out = (folder / "agent-sanpin-x.gold-footnotes.txt").read_text(encoding="utf-8").split("\n")
    assert out[2] == "1.2 S/I/1.1" and out[4] == "2.2 S/I/1.2|S/II/2.1 +"
    assert out[1] == GOLD[1] and out[-1] == ""
    receipt = (folder / "agent-sanpin-x.gold-footnotes.sha256").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in receipt] == [
        "agent-sanpin-x.gold-footnotes.txt", "agent-sanpin-x.gold.txt", "agent-sanpin-x.footnotes-map.json"]


def test_acts_without_a_map_get_an_exact_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "fz-x")
    assert D.derive("fz-x") == {"slug": "fz-x", "mapped": False, "changed_rows": 0}
    assert (folder / "agent-fz-x.gold-footnotes.txt").read_bytes() == (folder / "agent-fz-x.gold.txt").read_bytes()


@pytest.mark.parametrize("regions, pin", [
    ({"1.2": {"from": "S", "owner": "S/I/1.1"}}, "0" * 64),  # map not pinned to the frozen gold
    ({"9.9": {"from": "S", "owner": "S/I/1.1"}}, None),  # region absent from the gold
    ({"1.1": {"from": "S", "owner": "S/I/1.2"}}, None),  # gold owner differs from the map's "from"
    ({"1.2": {"from": "S", "owner": "S/I 1.1"}}, None),  # owner with a space would break the line
])
def test_a_wrong_map_is_refused_before_writing(tmp_path, monkeypatch, regions, pin):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "sanpin-x")
    write_map(folder, "sanpin-x", regions, pin)
    with pytest.raises(SystemExit):
        D.derive("sanpin-x")
    assert not (folder / "agent-sanpin-x.gold-footnotes.txt").exists()


def test_derived_gold_is_write_once(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    write_gold(tmp_path, "fz-x")
    D.derive("fz-x")
    with pytest.raises(FileExistsError):
        D.derive("fz-x")


def test_a_later_decision_derives_from_an_earlier_copy(tmp_path, monkeypatch):
    # Owner 28.10.2026 (dotted subpoints): the map is pinned to the gold-footnotes copy, the new copy is gold-dotted.
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "sanpin-x")
    write_map(folder, "sanpin-x", {"1.2": {"from": "S", "owner": "S/I/1.1", "mark": "1.1"}})
    D.derive("sanpin-x")
    base = folder / "agent-sanpin-x.gold-footnotes.txt"
    (folder / "agent-sanpin-x.dotted-map.json").write_text(json.dumps({
        "schema_version": "m1-04a-gold-footnotes-map/1", "gold_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
        "regions": {"2.2": {"from": "S", "owner": "S/I/1.2"}}}), encoding="utf-8")
    assert D.derive("sanpin-x", "gold-footnotes", "gold-dotted", "dotted-map")["changed_rows"] == 1
    out = (folder / "agent-sanpin-x.gold-dotted.txt").read_text(encoding="utf-8").split("\n")
    assert out[2] == "1.2 S/I/1.1" and out[4] == "2.2 S/I/1.2 +"
    receipt = (folder / "agent-sanpin-x.gold-dotted.sha256").read_text(encoding="utf-8").splitlines()
    assert [line.split("  ")[1] for line in receipt] == [
        "agent-sanpin-x.gold-dotted.txt", "agent-sanpin-x.gold-footnotes.txt", "agent-sanpin-x.dotted-map.json"]
    D.main(["--slugs", "sanpin-x", "--base", "gold-footnotes", "--suffix", "gold-other", "--map", "absent-map"])
    assert (folder / "agent-sanpin-x.gold-other.txt").read_bytes() == base.read_bytes()
