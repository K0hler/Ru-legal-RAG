"""Authored controls for the M1-04A «quoted document is quoted text» gold derivation; no corpus files."""

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


D = load_script("derive_m1_04a_gold_quoted")
GOLD = ["# convention: m1-04a-annotation/v2", "1.0 A", "2.0 S", "2.3 S/2", "2.4 S2", "2.6 S2/I", "3.1 S2/I/1|S2/I +",
        "4.2 S2/AN1", ""]


def write_gold(tmp_path, slug, lines):
    folder = tmp_path / slug
    folder.mkdir()
    (folder / f"agent-{slug}.gold.txt").write_bytes("\n".join(lines).encode())
    return folder


def test_quoted_document_collapses_into_its_introducing_point_and_receipt_lists_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "rp-x", GOLD)
    frozen = folder / "agent-rp-x.gold.txt"
    (folder / "agent-rp-x.quoted-map.json").write_text(json.dumps({
        "schema_version": "m1-04a-gold-quoted-map/1", "gold_sha256": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "collapse": {"S2": "S/2"}}), encoding="utf-8")
    assert D.derive("rp-x") == {"slug": "rp-x", "mapped": True, "changed_rows": 4}
    out = (folder / "agent-rp-x.gold-quoted.txt").read_text(encoding="utf-8").split("\n")
    # the whole subtree (sections, points, annexes) becomes the introducing point; alternatives too; «+» kept
    assert out[3:8] == ["2.3 S/2", "2.4 S/2", "2.6 S/2", "3.1 S/2 +", "4.2 S/2"] and out[-1] == ""
    receipt = (folder / "agent-rp-x.gold-quoted.sha256").read_text(encoding="utf-8").splitlines()
    assert [r.split("  ")[1] for r in receipt] == ["agent-rp-x.gold-quoted.txt", "agent-rp-x.gold.txt",
                                                   "agent-rp-x.quoted-map.json"]
    with pytest.raises(FileExistsError):
        D.derive("rp-x")  # write-once


def test_act_without_map_is_copied_and_a_stale_map_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "GOLD", tmp_path)
    folder = write_gold(tmp_path, "fz-y", GOLD)
    assert D.derive("fz-y")["changed_rows"] == 0
    assert (folder / "agent-fz-y.gold-quoted.txt").read_bytes() == (folder / "agent-fz-y.gold.txt").read_bytes()
    folder = write_gold(tmp_path, "pp-z", GOLD)
    (folder / "agent-pp-z.quoted-map.json").write_text(json.dumps({
        "schema_version": "m1-04a-gold-quoted-map/1", "gold_sha256": "0" * 64, "collapse": {"S2": "S/2"}}),
        encoding="utf-8")
    with pytest.raises(SystemExit):
        D.derive("pp-z")
