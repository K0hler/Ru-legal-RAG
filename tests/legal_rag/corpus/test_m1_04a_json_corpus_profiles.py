"""Authored controls for the M1-04A JSON corpus acquisition profiles; no network, no corpus files."""

import importlib.util
import json
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[3] / "docs" / "assets"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


A = load_script("acquire_m1_04a_json_corpus")


def test_profile_v1_is_the_default_and_unchanged():
    p = A.PROFILES["v1"]
    assert p["seed"] == 20261025 and p["exclude_corpora"] == ()
    assert sum(p["quotas"].values()) == 100 and p["quotas"]["ukaz"] == 19 and p["quotas"]["pp"] == 29


def test_profile_v2_150_acts_biased_to_decrees_and_resolutions_without_v1_acts(tmp_path):
    p = A.PROFILES["v2"]
    assert p["seed"] != A.PROFILES["v1"]["seed"] and sum(p["quotas"].values()) == 150
    assert p["quotas"]["ukaz"] == 45 and p["quotas"]["pp"] == 45
    assert max(p["quotas"], key=p["quotas"].get) in ("ukaz", "pp")
    # candidates found in an excluded corpus never enter the screening order
    v1 = tmp_path / "v1"
    v1.mkdir()
    (v1 / "fetch.json").write_text(json.dumps({"documents": [{"nd": "111"}]}), encoding="utf-8")
    root = tmp_path / "v2"
    root.mkdir()
    docs = [{"nd": nd, "hash": nd} for nd in ("111", "222", "333")]
    (root / "candidates.json").write_text(json.dumps({"groups": {g: [{"docs": docs}] for g in A.GROUPS}}),
                                          encoding="utf-8")
    profile = dict(p, exclude_corpora=(v1,))
    orders = A.candidate_orders(root, profile)
    assert sorted(d["nd"] for d in orders["ukaz"]) == ["222", "333"]
