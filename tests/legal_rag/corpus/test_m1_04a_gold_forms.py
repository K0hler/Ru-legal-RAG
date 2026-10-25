"""Authored controls for the M1-04A §6.1 forms gold derivation; no corpus files."""

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


D = load_script("derive_m1_04a_gold_forms")
GOLD = ["# convention: m1-04a-annotation/v2", "1.0 A", "2.0 S4", "2.1 S4/1", "2.2 S5", "2.3 S5/1|S5 +", "3.0 S6", ""]


def write_gold(tmp_path, slug, lines):
    folder = tmp_path / slug
    folder.mkdir()
    (folder / f"agent-{slug}.gold.txt").write_bytes("\n".join(lines).encode())
    return folder


def test_mapped_roots_merge_into_their_annex_and_receipt_lists_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "prikaz-x", GOLD)
    frozen = folder / "agent-prikaz-x.gold.txt"
    (folder / "agent-prikaz-x.forms-map.json").write_text(json.dumps({
        "schema_version": "m1-04a-gold-forms-map/1", "gold_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "roots": {"S5": "S4"}}), encoding="utf-8")
    assert D.derive("prikaz-x") == {"slug": "prikaz-x", "mapped": True, "changed_rows": 2}
    out = (folder / "agent-prikaz-x.gold-forms.txt").read_text(encoding="utf-8").split("\n")
    assert out[4] == "2.2 S4" and out[5] == "2.3 S4/1|S4 +" and out[6] == "3.0 S6" and out[-1] == ""
    receipt = (folder / "agent-prikaz-x.gold-forms.sha256").read_text(encoding="utf-8").splitlines()
    assert [r.split("  ")[1] for r in receipt] == ["agent-prikaz-x.gold-forms.txt", "agent-prikaz-x.gold.txt",
                                                   "agent-prikaz-x.forms-map.json"]
    with pytest.raises(FileExistsError):
        D.derive("prikaz-x")  # write-once


def test_act_without_map_is_copied_and_a_stale_map_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "fz-y", GOLD)
    assert D.derive("fz-y")["changed_rows"] == 0
    assert (folder / "agent-fz-y.gold-forms.txt").read_bytes() == (folder / "agent-fz-y.gold.txt").read_bytes()
    folder = write_gold(tmp_path, "pp-z", GOLD)
    (folder / "agent-pp-z.forms-map.json").write_text(json.dumps({
        "schema_version": "m1-04a-gold-forms-map/1", "gold_sha256": "0" * 64, "roots": {"S5": "S4"}}), encoding="utf-8")
    with pytest.raises(SystemExit):
        D.derive("pp-z")
