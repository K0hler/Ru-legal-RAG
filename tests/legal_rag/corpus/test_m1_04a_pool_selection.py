import importlib.util
from pathlib import Path
import sys

import pytest

MODULE = "select_m1_04a_pool"


def load_script(name):
    path = Path(__file__).resolve().parents[3] / f"docs/assets/{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = load_script(MODULE)

QUOTAS = {"federal_law": 2, "presidential_decree": 1, "ministry_order": 2}


def card(n, act_type="federal_law", **over):
    value = {
        "eo_number": f"{n:016d}",
        "act_type": act_type,
        "date": "2020-01-01",
        "number": str(n),
        "title": f"Об акте {n}",
        "pages": 10,
        "edition_count": 1,
        "in_official_tree": True,
    }
    value.update(over)
    return value


def pool():
    types = ["federal_law", "presidential_decree", "ministry_order"]
    return [card(n, types[n % 3]) for n in range(1, 60)]


def ids(result):
    return [row["eo_number"] for row in result["selected"]]


def test_quotas_and_seed_are_deterministic():
    first = P.select_pool(pool(), QUOTAS, 20261021)
    again = P.select_pool(list(reversed(pool())), QUOTAS, 20261021)
    other = P.select_pool(pool(), QUOTAS, 7)
    assert first["schema_version"] == "m1-04a-pool-selection/1"
    assert first["seed"] == 20261021 and first["quotas"] == QUOTAS
    assert ids(first) == ids(again)
    assert ids(first) != ids(other)
    for kind, quota in QUOTAS.items():
        assert sum(row["act_type"] == kind for row in first["selected"]) == quota
    assert any(row["reason"] == "quota_full" for row in first["rejected"])


def test_rejections_carry_reasons():
    cards = [
        card(1, edition_count=2),
        card(2, in_official_tree=False, edition_count=None),
        card(3, pages=2),
        card(4, pages=61),
        card(5, title="О внесении изменений в закон"),
        card(6, in_official_tree=True, edition_count=None),
    ]
    result = P.select_pool(cards, {"federal_law": 5}, 1)
    reasons = {row["eo_number"]: row["reason"] for row in result["rejected"]}
    assert reasons == {
        f"{1:016d}": "edition_count_not_1",
        f"{2:016d}": "not_in_official_tree",
        f"{3:016d}": "pages_out_of_range",
        f"{4:016d}": "pages_out_of_range",
        f"{5:016d}": "amending_act",
        f"{6:016d}": "edition_count_unknown",
    }
    assert result["selected"] == []


def test_no_selection_field_reads_body_text():
    result = P.select_pool(pool(), QUOTAS, 3)
    assert result["selected"]
    for row in result["selected"]:
        assert set(row) <= set(P.METADATA_FIELDS)
    noisy = card(1, body_text="текст акта", html="<p>x</p>")
    row = P.select_pool([noisy], {"federal_law": 1}, 1)["selected"][0]
    assert "body_text" not in row and "html" not in row


def test_categorize_uses_title_prefix_and_policy():
    c = P.categorize
    assert c("Федеральный закон от 01.01.2020 № 1-ФЗ \"О чём-то\"", "О чём-то") == "federal_law"
    assert c("Указ Президента Российской Федерации от 01.01.2020 № 1 \"Х\"", "Х") == "presidential_decree"
    gov = "Постановление Правительства Российской Федерации от 01.01.2020 № 1 \"{}\""
    assert c(gov.format("Об утверждении Правил"), "Об утверждении Правил") == "government_resolution"
    assert c(gov.format("О порядке"), "О порядке") is None
    assert c("Распоряжение Правительства Российской Федерации от 01.01.2020 № 1-р", "Х") == "government_order"
    order = "Приказ {} от 01.01.2020 № 1 \"Х\""
    assert c(order.format("Министерства юстиции Российской Федерации"), "Х") == "ministry_order"
    assert c(order.format("Федеральной налоговой службы"), "Х") == "ministry_order"
    assert c(order.format("Министерства финансов Республики Крым"), "Х") is None
    assert c(order.format("Департамента внутреннего контроля Ненецкого автономного округа"), "Х") is None
    assert c("Постановление Губернатора области от 01.01.2020 № 1", "Х") is None


def test_edition_counting_counts_only_complete_official():
    rows = [
        {"redofficial": True, "redcompleted": True, "hascontent": True, "contentcomplete": True},
        {"redofficial": True, "redcompleted": True, "hascontent": True, "contentcomplete": False},
        {"redofficial": False, "redcompleted": True, "hascontent": True, "contentcomplete": True},
    ]
    assert P.count_actual_editions({"redactions": rows}) == 1
    assert P.count_actual_editions({"error": "x"}) is None
    assert P.count_ips_editions({"redactions": [{"completed": True}, {"completed": False}]}) == 1
    assert P.count_ips_editions({}) is None


def test_amending_title_is_detected_through_leading_quotes():
    # Federal-law feed names arrive wrapped in quotes: "О внесении изменений ...".
    for title in ('"О внесении изменения в статью 3"', "«О внесении изменений в закон»", "  О внесении изменений"):
        result = P.select_pool([card(1, title=title)], {"federal_law": 1}, 1)
        assert result["rejected"] == [{"eo_number": f"{1:016d}", "reason": "amending_act"}], title


A = load_script("acquire_m1_04a_pool")

POOL_ACT = {
    "eo_number": "0001202001010001", "act_type": "government_resolution", "date": "2020-01-01",
    "number": "7", "title": "Об утверждении правил", "pages": 3, "edition_count": 1,
    "official_source": "ips", "official_hash": "a" * 64,
}


def ips_card(**over):
    edition = {"id": 0, "date": "01.01.2020", "actual": True, "completed": True,
               "status": "актуальная", "redname": "на 01.01.2020, исходная, актуальная"}
    value = {"hash": "a" * 64, "type": "Постановление", "nd": "1", "baseid": "c000000000", "actualrdk": 0,
             "adoption": "Постановление Правительства Российской Федерации от 01.01.2020 № 7",
             "name": "Об утверждении правил", "redactions": [edition]}
    value.update(over)
    return value


class FakeIPS(A.PoolIPS):
    def __init__(self, card):
        super().__init__(timeout=1, request_interval=0)
        self.card = card
        self.requests = []

    def _get(self, url):
        import json

        self.requests.append(url)
        if "document_card" not in url:
            raise AssertionError("text must not be requested for a mismatched edition")
        return json.dumps(self.card, ensure_ascii=False).encode(), {"request_url": url, "response_url": url}


def test_acquire_refuses_edition_mismatch(tmp_path):
    later = {"id": 1, "date": "05.05.2021", "actual": True, "completed": True,
             "status": "актуальная", "redname": "на 05.05.2021, актуальная"}
    first = dict(ips_card()["redactions"][0], actual=False, status="недействующая")
    mismatches = [
        ips_card(actualrdk=1, redactions=[first, later]),          # second edition appeared
        ips_card(redactions=[dict(later, id=0)]),                  # single edition is not the original
        ips_card(redactions=[dict(first, date="31.12.2019", actual=True, status="актуальная")]),  # before act
        ips_card(hash="b" * 64),                                   # other official identity
    ]
    for card in mismatches:
        base = FakeIPS(card)
        with pytest.raises(ValueError):
            A.acquire_official(POOL_ACT, "pp-7-2020", base, tmp_path)
        assert [p for p in tmp_path.rglob("*") if p.is_file()] == []
        assert len(base.requests) == 1
    assert A.check_edition(ips_card(), POOL_ACT)["id"] == 0
    published_later = dict(ips_card()["redactions"][0], date="05.01.2020", redname="на 05.01.2020, исходная, актуальная")
    assert A.check_edition(ips_card(redactions=[published_later]), POOL_ACT)["date"] == "05.01.2020"


def test_pool_slug_rule():
    act = dict(POOL_ACT)
    assert A.slug(dict(act, act_type="federal_law", number="23-ФЗ", date="2018-02-19")) == "fz-23-2018"
    assert A.slug(dict(act, act_type="government_order", number="1378-р", date="2018-07-06")) == "rp-1378-2018"
    assert A.slug(dict(act, act_type="presidential_decree", number="204", date="2016-04-30")) == "ukaz-204-2016"
    assert A.slug(dict(act, act_type="government_resolution", number="884", date="2024-06-29")) == "pp-884-2024"
    order = dict(act, act_type="ministry_order", number="173", date="2021-03-25")
    assert A.slug(order, "Министерство просвещения Российской Федерации") == "prikaz-minprosveshcheniya-173-2021"
    assert A.slug(order, "Федеральная налоговая служба") == "prikaz-fns-173-2021"
    with pytest.raises(ValueError):
        A.slug(order)
