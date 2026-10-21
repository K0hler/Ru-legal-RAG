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
    assert first["schema_version"] == "m1-04a-pool-selection/2"
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



def test_amending_variants_rejected():
    titles = (
        "О внесении изменений в статью 1", "О внесении изменения в пункт 2",
        "О внесении дополнений в закон", "О признании утратившими силу отдельных актов",
        "«О признании утратившим силу постановления»",
    )
    for title in titles:
        result = P.select_pool([card(1, title=title)], {"federal_law": 1}, 1, require_single_edition=False)
        assert result["rejected"] == [{"eo_number": f"{1:016d}", "reason": "amending_act"}], title
    kept = P.select_pool([card(1, title="О порядке внесения изменений в реестр")], {"federal_law": 1}, 1)
    assert ids(kept) == [f"{1:016d}"]


def test_already_used_rejected():
    used = {f"{2:016d}"}
    result = P.select_pool([card(1), card(2)], {"federal_law": 2}, 1, already_used=used)
    assert ids(result) == [f"{1:016d}"]
    assert result["rejected"] == [{"eo_number": f"{2:016d}", "reason": "already_used"}]


def test_long_document_share_filled_first():
    short = [card(n, types, pages=5) for n, types in zip(range(1, 41), ["federal_law", "ministry_order"] * 20)]
    long = [card(n, "ministry_order", pages=25) for n in range(41, 44)] + [card(44, "federal_law", pages=150)]
    quotas = {"federal_law": 2, "ministry_order": 2}
    kwargs = {"require_single_edition": False, "pages_range": (3, 200), "long_min": 3, "long_pages": 20}
    for seed in (1, 2, 3, 4):
        result = P.select_pool(short + long, quotas, seed, **kwargs)
        pages = [row["pages"] for row in result["selected"]]
        assert sum(p >= 20 for p in pages) >= 3, seed
        assert len(pages) == 4 and result["long_selected"] >= 3
        assert P.select_pool(list(reversed(short + long)), quotas, seed, **kwargs)["selected"] == result["selected"]
    # Without the share the short majority wins for at least one seed.
    plain = [P.select_pool(short + long, quotas, s, require_single_edition=False, pages_range=(3, 200))
             for s in (1, 2, 3, 4)]
    assert any(sum(r["pages"] >= 20 for r in p["selected"]) < 3 for p in plain)
    assert P.select_pool([card(1, pages=201)], {"federal_law": 1}, 1, pages_range=(3, 200))["rejected"][0][
        "reason"] == "pages_out_of_range"


def test_single_edition_filter_optional():
    cards = [
        card(1, edition_count=3),
        card(2, in_official_tree=False, edition_count=None),
        card(3, in_official_tree=False, edition_count=None, lookup_error="URLError: timeout"),
    ]
    strict = P.select_pool(cards, {"federal_law": 3}, 1)
    assert {r["eo_number"][-1]: r["reason"] for r in strict["rejected"]} == {
        "1": "edition_count_not_1", "2": "not_in_official_tree", "3": "lookup_error"}
    loose = P.select_pool(cards, {"federal_law": 3}, 1, require_single_edition=False)
    assert loose["rejected"] == [] and len(loose["selected"]) == 3
    assert loose["require_single_edition"] is False and strict["require_single_edition"] is True
    # Metadata-only rows (no lookup yet) are selectable when the filter is off.
    bare = {k: v for k, v in card(4).items() if k not in ("in_official_tree", "edition_count")}
    assert ids(P.select_pool([bare], {"federal_law": 1}, 1, require_single_edition=False)) == [f"{4:016d}"]


def test_code_category_from_title():
    c = P.categorize
    law = "Федеральный закон от 08.03.2015 № 21-ФЗ \"{}\""
    for title in ("Кодекс административного судопроизводства Российской Федерации",
                  "Градостроительный кодекс Российской Федерации"):
        assert c(law.format(title), f'"{title}"') == "code", title
    for title in ("О внесении изменений в Налоговый кодекс Российской Федерации",
                  "О введении в действие Градостроительного кодекса Российской Федерации",
                  "О признании утратившими силу положений Кодекса Российской Федерации"):
        assert c(law.format(title), f'"{title}"') == "federal_law", title
    order = "Приказ Министерства юстиции Российской Федерации от 01.01.2020 № 1 \"{}\""
    assert c(order.format("Об утверждении Кодекс Российской Федерации"), "Х") == "ministry_order"


def test_selection_pair_write_once(tmp_path):
    out = tmp_path / "batch" / "selection.json"
    payload = b"{}" + bytes([10])
    assert P.write_selection_pair(out, payload) == "written"
    digest = out.with_name("selection.sha256").read_text(encoding="utf-8")
    assert digest == P.hashlib.sha256(payload).hexdigest() + "  selection.json" + chr(10)
    assert P.write_selection_pair(out, b"other") == "unchanged"
    assert out.read_bytes() == payload
    assert out.with_name("selection.sha256").read_text(encoding="utf-8") == digest
    lone = tmp_path / "lone" / "selection.json"
    lone.parent.mkdir()
    lone.with_name("selection.sha256").write_text("x  selection.json", encoding="utf-8")
    with pytest.raises(FileExistsError):
        P.write_selection_pair(lone, payload)
    assert not lone.exists()
    assert P.selection_pair_state(lone) == "partial"
    assert P.selection_pair_state(tmp_path / "none" / "selection.json") == "absent"


def test_already_used_from_indexes(tmp_path):
    index = {"documents": [{"source_url": "http://publication.pravo.gov.ru/File/Pdf?eoNumber=0001201305220001"}]}
    (tmp_path / "index.json").write_text(P.json.dumps(index), encoding="utf-8")
    (tmp_path / "selection.json").write_text(P.json.dumps({"selected": [{"eo_number": "0001202001010001"}]}),
                                             encoding="utf-8")
    used = P.load_already_used([tmp_path / "index.json"], [tmp_path / "selection.json"])
    assert used == {"0001201305220001", "0001202001010001"}


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


class FakeActual:
    """Authored actual.pravo stand-in: the act is hidden whenever the query carries AttrId 999."""

    _api_base = "http://actual.example/api/ebpi"

    def __init__(self):
        self.requests = []

    def _url(self, path, params):
        from urllib.parse import urlencode

        return f"{self._api_base}/{path}?{urlencode(params)}"

    def _get(self, url):
        from urllib.parse import parse_qs, urlsplit

        self.requests.append(url)
        if "/attrsearch/" in url:
            attrs = P.json.loads(parse_qs(urlsplit(url).query)["q"][0])
            hidden = any(attr.get("AttrId") == 999 for attr in attrs)
            docs = [] if hidden else [
                {"docpass0number": "22-ФЗ", "docpass0date": "20180219", "dochash": "h22"},
                {"docpass0number": "22-ФЗ", "docpass0date": "20170219", "dochash": "other-date"},
            ]
            return P.json.dumps({"docs": docs}).encode(), {}
        edition = {"redofficial": True, "redcompleted": True, "hascontent": True, "contentcomplete": True}
        return P.json.dumps({"redactions": [edition, edition]}).encode(), {}


def test_actual_lookup_query_has_no_position_filter():
    actual = FakeActual()
    info = P.lookup_official(actual, None, "22-ФЗ", "2018-02-19")
    assert info == {"in_official_tree": True, "official_source": "actual", "official_hash": "h22",
                    "edition_count": 2}
    assert len(actual.requests) == 2


def test_enrich_counts_incrementally_and_matches_selection(monkeypatch):
    rows = [card(n, ["federal_law", "ministry_order"][n % 2], pages=5 + (n % 4) * 10,
                 in_official_tree=None, edition_count=None) for n in range(1, 81)]
    truth = {r["eo_number"]: {"in_official_tree": r["eo_number"][-1] != "3",
                              "edition_count": 2 if r["eo_number"][-1] == "7" else 1} for r in rows}
    calls = []

    def fake_lookup(actual, ips, row):
        calls.append(row["eo_number"])
        if row["eo_number"][-1] == "9":
            return {"in_official_tree": False, "lookup_error": "URLError: down", "official_found": None}
        return dict(truth[row["eo_number"]], official_found=truth[row["eo_number"]]["in_official_tree"])

    monkeypatch.setattr(P, "lookup", fake_lookup)
    quotas = {"federal_law": 2, "ministry_order": 2}
    pool_rows = {r["eo_number"]: r for r in rows}
    enriched = {}
    P.enrich(pool_rows, enriched, None, None, quotas, 5, pages_range=(3, 200), long_min=2)
    assert len(calls) == len(set(calls)) < len(rows)
    partial = P.select_pool(list(enriched.values()), quotas, 5, pages_range=(3, 200), long_min=2)
    full = P.select_pool([dict(r, **truth[r["eo_number"]]) if r["eo_number"][-1] != "9"
                          else dict(r, lookup_error="x") for r in rows],
                         quotas, 5, pages_range=(3, 200), long_min=2)
    assert ids(partial) == ids(full) and P.quotas_full(partial)
    assert "lookup_error" in {r["reason"] for r in full["rejected"]}


def test_titles_with_full_act_prefix():
    # Older feed names repeat the act prefix before the quoted title.
    title = 'Федеральный закон от 02.05.2012 № 41-ФЗ "О внесении изменений в отдельные акты"'
    assert P.select_pool([card(1, title=title)], {"federal_law": 1}, 1)["rejected"][0]["reason"] == "amending_act"
    law = "Федеральный закон от 01.01.2015 № 1-ФЗ \"{}\""
    amending = law.format("О внесении изменений в Налоговый кодекс Российской Федерации")
    assert P.categorize(amending, amending) == "federal_law"
    code = law.format("Водный кодекс Российской Федерации")
    assert P.categorize(code, code) == "code"
    kept = 'Федеральный закон от 03.12.2011 № 382-ФЗ "О государственной системе"'
    assert P.select_pool([card(2, title=kept)], {"federal_law": 1}, 1)["selected"]


def test_quota_override_and_zero_quota():
    quotas = P.override_quotas(P.BATCH2_QUOTAS, ["code=0", "federal_law=4"])
    assert quotas["code"] == 0 and quotas["federal_law"] == 4 and P.BATCH2_QUOTAS["code"] == 1
    for bad in (["statute=1"], ["code=x"]):
        with pytest.raises(ValueError):
            P.override_quotas(P.BATCH2_QUOTAS, bad)
    result = P.select_pool([card(1, "code"), card(2)], {"code": 0, "federal_law": 1}, 1)
    assert ids(result) == [f"{2:016d}"] and P.quotas_full(result)
    assert result["rejected"] == [{"eo_number": f"{1:016d}", "reason": "quota_full"}]
