"""Authored controls for the IPS tree-coverage sample estimate; no network."""

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


S = load_script("survey_ips_tree_coverage")


def doc(nd, adoption, docdate):
    return {"hash": f"h{nd}", "nd": str(nd), "docdate": docdate, "adoption": adoption, "name": "x", "state": "s"}


def test_organ_groups_from_the_adoption_line():
    assert S.organ_group("Постановление", "Постановление Правительства Российской Федерации от 01.02.2020 № 1") == \
        "Правительство"
    assert S.organ_group("Постановление", "Постановление Совета Министров - Правительства РФ от 01.02.1993 № 1") == \
        "Правительство"
    assert S.organ_group("Распоряжение", "Распоряжение Президента Российской Федерации от 01.02.2020 № 5-рп") == \
        "Президент"
    assert S.organ_group("Постановление", "Постановление Государственной Думы Федерального Собрания от …") == \
        "Государственная Дума"
    assert S.organ_group("Постановление", "Постановление Конституционного Суда Российской Федерации от …") == \
        "Конституционный Суд"
    assert S.organ_group("Решение", "Решение Центральной избирательной комиссии от …") == S.OTHER_ORGAN
    assert S.organ_group("Федеральный закон", "Федеральный закон от 01.02.2020 № 1-ФЗ") == S.OTHER_ORGAN


def test_decades_and_undated_acts():
    assert S.decade("31.12.1999") == "1990-е" and S.decade("01.01.2020") == "2020-е"
    assert S.decade("12.12.1952") == "до 1990" and S.decade("") == "без даты" and S.decade(None) == "без даты"


def test_required_n_is_96_point_04_rounded_up_with_the_finite_population_correction():
    assert S.required_n(10_000_000) == 97
    assert S.required_n(46454) == 96
    assert S.required_n(500) == 81 and S.required_n(40) == 29
    assert S.required_n(5) == 5 and S.required_n(1) == 1 and S.required_n(0) == 0


def test_small_organ_groups_are_merged_into_others():
    frame = {"Постановление": [doc(i, "Постановление Правительства РФ от 01.01.2020 № 1", "01.01.2020")
                               for i in range(S.MIN_ORGAN_GROUP)]
             + [doc(10_000 + i, "Постановление Конституционного Суда РФ от 01.01.2020", "01.01.2020")
                for i in range(3)]}
    keys = S.strata(frame)
    assert set(keys) == {("Постановление", "Правительство", "2020-е"), ("Постановление", S.OTHER_ORGAN, "2020-е")}
    assert len(keys[("Постановление", S.OTHER_ORGAN, "2020-е")]) == 3


def test_plan_is_seeded_census_for_small_strata_and_sized_for_large():
    frame = {"Указ": [doc(i, "Указ Президента РФ", "01.01.1995") for i in range(1000)]
             + [doc(5000 + i, "Указ Президента РФ", "01.01.2021") for i in range(40)]
             + [doc(9000 + i, "Указ Президента РФ", "01.01.2011") for i in range(5)]}
    a, b = S.plan_sample(frame, seed=1), S.plan_sample(frame, seed=1)
    assert a == b and S.plan_sample(frame, seed=2) != a
    by = {r["decade"]: r for r in a}
    assert by["1990-е"]["n"] == S.required_n(1000) and not by["1990-е"]["census"]
    assert by["2020-е"]["n"] == 29 and not by["2020-е"]["census"]
    assert by["2010-е"]["n"] == 5 and by["2010-е"]["census"]
    assert len({d["nd"] for d in by["1990-е"]["docs"]}) == by["1990-е"]["n"]


def test_wilson_interval_is_inside_zero_one_and_not_degenerate_at_zero():
    low, high = S.wilson(0, 97)
    assert low == 0.0 and 0.03 < high < 0.05
    low, high = S.wilson(48, 97)
    assert 0.39 < low < 0.41 and 0.59 < high < 0.6
    assert S.wilson(0, 0) == (0.0, 1.0)


def test_stratified_share_weights_by_population_and_census_adds_no_variance():
    cells = [{"population": 900, "n": 97, "k": 97}, {"population": 100, "n": 97, "k": 0}]
    r = S.stratified(cells)
    assert abs(r["share"] - 0.9) < 1e-9 and r["low"] < 0.9 < r["high"]
    census = S.stratified([{"population": 30, "n": 30, "k": 6}])
    assert census["share"] == 0.2 and census["low"] == census["high"] == 0.2
    assert S.stratified([])["share"] is None


def test_screen_record_reads_the_actual_edition_and_the_tree():
    card = {"actualrdk": "2", "redactions": [{"id": 0, "hascontent": False}, {"id": 2, "hascontent": True}]}
    tree = {"status": "200", "data": [{"lvl": 0, "unit": "статья"}, {"lvl": 1, "unit": "часть"}]}
    assert S.screen_record(card, tree) == {"rdk": "2", "has_text": True, "nodes": 2, "depth": 2, "message": None}
    empty = {"message": "У документа нет содержания", "status": "200", "data": ""}
    r = S.screen_record({"actualrdk": "0", "redactions": [{"id": 0, "hascontent": False}]}, empty)
    assert r["nodes"] == 0 and r["depth"] == 0 and not r["has_text"]


class FakeClient:
    def __init__(self, *_):
        self.calls = []

    def request(self, endpoint, params, post=False):
        self.calls.append(endpoint)
        if endpoint == "document_card.json":
            body = {"nd": "7", "actualrdk": 0, "baseid": "c000000000", "redactions": [{"id": 0, "hascontent": True}]}
        else:
            body = {"status": "200", "data": [{"lvl": 0, "unit": "пункт"}]}
        return json.dumps(body).encode(), {"sha256": "x"}


def test_screen_resumes_reuses_cached_screens_and_estimates(tmp_path, monkeypatch):
    clients = []
    monkeypatch.setattr(S.corpus, "Client", lambda *a: clients.append(FakeClient()) or clients[-1])
    cache = tmp_path / "cache"
    (cache / "8").mkdir(parents=True)
    (cache / "8" / "card.json").write_text(json.dumps({"actualrdk": 0, "redactions": [{"id": 0, "hascontent": True}]}),
                                           encoding="utf-8")
    (cache / "8" / "document_content.json").write_text(json.dumps({"status": "200", "data": ""}), encoding="utf-8")
    monkeypatch.setattr(S, "CACHED_SCREENS", [cache])
    frame = {"Указ": [doc(7, "Указ Президента РФ", "01.01.2021"), doc(8, "Указ Президента РФ", "01.01.2021")]}
    (tmp_path / "frame").mkdir()
    (tmp_path / "frame" / "ukaz.json").write_text(json.dumps({"type": "Указ", "docs": frame["Указ"]}),
                                                  encoding="utf-8")
    S.phase_plan(tmp_path)
    S.phase_screen(tmp_path)
    assert clients[0].calls == ["document_card.json", "document_content"]  # nd 8 came from the cache
    S.phase_screen(tmp_path)
    assert clients[1].calls == []  # resumed: nothing left
    S.phase_estimate(tmp_path)
    est = json.loads((tmp_path / "estimate.json").read_text(encoding="utf-8"))
    (cell,) = est["cells"]
    assert (cell["population"], cell["n"], cell["k"], cell["with_text"], cell["census"]) == (2, 2, 1, 2, True)
    assert est["types"][0]["share"] == 0.5
    assert "| Указ | прочие | 2 | 2 | 50% |" in (tmp_path / "coverage.md").read_text(encoding="utf-8")
