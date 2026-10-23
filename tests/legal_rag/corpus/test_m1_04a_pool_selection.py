import importlib.util
import subprocess
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


@pytest.mark.parametrize("title", [
    "Кодекс Российской Федерации об административных правонарушениях",
    "Кодекс административного судопроизводства Российской Федерации",
    "Градостроительный кодекс Российской Федерации",
])
def test_code_titles_with_different_portal_types(title):
    for prefix in ("Федеральный закон от 01.01.2020 № 1-ФЗ", title):
        assert P.categorize(prefix, title) == "code"
    assert P.categorize("Федеральный закон от 01.01.2020 № 1-ФЗ",
                        "О введении в действие " + title) == "federal_law"


def test_code_slug_can_be_acquired():
    assert A.slug(card(1, "code", number="21-ФЗ", date="2015-03-08")) == "code-21-2015"


def test_targeted_code_candidates_frozen_before_selection(tmp_path):
    import json
    from datetime import date

    title = "Кодекс Российской Федерации об авторских примерах"

    class Publication:
        calls = []

        def fetch_feed(self, day, page):
            self.calls.append((day, page))
            return {"events": [{"eoNumber": f"{page:016d}", "complexName": title,
                                "name": title, "number": str(page), "documentDate": day.isoformat(),
                                "pagesCount": 30}], "pages_total": 2,
                    "raw_bytes": f"authored page {page}".encode(), "source_url": f"http://source/{page}",
                    "rejected_items": []}

    publication = Publication()
    path = tmp_path / "selection.json"
    P.freeze_code_candidates(publication, [date(2020, 1, 1)], path)
    rows, digest = P.load_code_candidates(path)
    assert len(rows) == 2 and publication.calls == [(date(2020, 1, 1), 1), (date(2020, 1, 1), 2)]
    assert len(json.loads(path.read_bytes())["feed_pages"]) == 2
    result = P.select_pool(rows, {"code": 1}, 71, require_single_edition=False)
    assert ids(result) == ids(P.select_pool(list(reversed(rows)), {"code": 1}, 71,
                                          require_single_edition=False))
    assert digest == P.hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="sha256"):
        P.load_code_candidates(path)


def test_new_feed_cache_retains_candidates_with_rejections():
    cache = {"2020-01-01": {"candidates": [card(1)], "feed_pages": [{"rejected_items": ["bad"]}]}}
    assert P.pool_from_cache(cache, ["2020-01-01"]) == {card(1)["eo_number"]: card(1)}


def test_selection_and_refill_use_frozen_targeted_codes(tmp_path, monkeypatch):
    import json
    from datetime import date, timedelta
    from types import SimpleNamespace

    codes = [card(i, "code", title="Водный кодекс Российской Федерации", pages=480) for i in (1, 2)]
    code_path = tmp_path / "codes" / "selection.json"
    P.write_selection_pair(code_path, json.dumps({"schema_version": P.CODE_CANDIDATES_SCHEMA,
                                                "candidates": codes}).encode())
    days = [date(2020, 1, 1) + timedelta(days=i) for i in range(120)]
    cache = {d.isoformat(): [] for d in days}
    cache[days[0].isoformat()] = {"candidates": [card(3)],
                                "feed_pages": [{"rejected_items": [{"index": 1, "reason": "invalid_feed"}]}]}
    cache_path = tmp_path / "feed.json"
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    monkeypatch.setattr(P, "sample_days", lambda *args: days)
    monkeypatch.setitem(P.PROFILES, "test", {"quotas": {"code": 1, "federal_law": 1},
                       "pages_range": (3, 200), "long_min": 1,
                       "require_single_edition": False, "exclude_used": False})
    monkeypatch.setattr(P, "lookup", lambda *args: {"in_official_tree": False, "official_found": False})
    batch = tmp_path / "batch-03"
    args = SimpleNamespace(output=batch / "selection.json", profile="test", quota=[],
                           code_candidates=code_path, seed=7, date_from="2020-01-01", date_to="2020-12-31",
                           feed_cache=cache_path, min_days=0, partial_output=None, quota_change=None,
                           pages_max=500)
    assert P.run(args) == 0
    selection = json.loads(Path(args.output).read_bytes())
    assert selection["schema_version"] == "m1-04a-pool-selection/3"
    assert selection["selected_per_category"] == {"code": 1, "federal_law": 1}
    assert selection["pages_range"] == [3, 500]
    assert selection["feed_pages"][0]["rejected_items"][0]["index"] == 1
    failed = next(r for r in selection["selected"] if r["act_type"] == "code")
    (batch / "failures").mkdir()
    (batch / "failures" / f"{failed['eo_number']}-test.json").write_text(json.dumps({"reason": "authored"}))
    refill = P.refill_round(batch, cache_path)
    assert refill["selected"][0]["act_type"] == "code"
    assert refill["selected"][0]["eo_number"] != failed["eo_number"]


def test_quota_override_and_zero_quota():
    quotas = P.override_quotas(P.BATCH2_QUOTAS, ["code=0", "federal_law=4"])
    assert quotas["code"] == 0 and quotas["federal_law"] == 4 and P.BATCH2_QUOTAS["code"] == 1
    for bad in (["statute=1"], ["code=x"]):
        with pytest.raises(ValueError):
            P.override_quotas(P.BATCH2_QUOTAS, bad)
    result = P.select_pool([card(1, "code"), card(2)], {"code": 0, "federal_law": 1}, 1)
    assert ids(result) == [f"{2:016d}"] and P.quotas_full(result)
    assert result["rejected"] == [{"eo_number": f"{1:016d}", "reason": "quota_full"}]


def test_min_days_only_checkpoints(monkeypatch):
    seen = []
    monkeypatch.setattr(P, "run", lambda args: seen.append(args.min_days) or 0)
    base = ["--from", "2011-01-01", "--to", "2025-12-31", "--seed", "1", "--output", "x/selection.json"]
    for value in ("0", "60", "120"):
        assert P.main(base + ["--min-days", value]) == 0
    assert seen == [0, 60, 120]
    for value in ("30", "121", "-1"):
        with pytest.raises(SystemExit):
            P.main(base + ["--min-days", value])
    assert seen == [0, 60, 120]


def test_authority_short_rule():
    f = A.authority_short
    assert f("Министерство труда и социальной защиты Российской Федерации") == "mintruda"
    assert f("Министерство Российской Федерации по делам гражданской обороны") == "minpo"
    assert f("Федеральная служба по надзору в сфере здравоохранения") == "fsnsz"
    assert f("Федеральная Российской Федерации налоговая служба") == "fns"
    assert f("Министерство здравоохранения") == "minzdravookhraneniya"
    with pytest.raises(ValueError):
        f("Российской Федерации")


def make_fetched(act, pdf=b"%PDF-body", length=None, **declared_over):
    import json

    declared = {"electronic_publication_number": act["eo_number"], "document_number": act["number"],
                "document_date": act["date"] + "T00:00:00", "pages_count": act["pages"]}
    declared.update(declared_over)
    card = {"pdfFileLength": len(pdf) if length is None else length}
    return {"declared_publication": declared, "raw_bytes": pdf,
            "publication_card_bytes": json.dumps(card).encode()}


def test_check_publication_refuses_card_or_length_mismatch():
    act = POOL_ACT
    A.check_publication(make_fetched(act), act)
    for bad in (make_fetched(act, pages_count=act["pages"] + 1), make_fetched(act, document_number="8"),
                make_fetched(act, document_date="2020-01-02T00:00:00"),
                make_fetched(act, electronic_publication_number="0001202001010002"),
                make_fetched(act, length=3)):
        with pytest.raises(A.PublicationMismatch):
            A.check_publication(bad, act)


def test_pool_publication_refuses_before_any_write(tmp_path, monkeypatch):
    fetched = make_fetched(POOL_ACT, length=3)
    monkeypatch.setattr(A.PublicationPravoConnector, "fetch", lambda self, eo: fetched)
    connector = A.PoolPublication(timeout=1, request_interval=0)
    with pytest.raises(A.PublicationMismatch):
        A.acquire_pdf(POOL_ACT, connector, tmp_path)
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


def test_pool_v2_checks_selected_identity_before_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(A.PublicationPoolConnector, "fetch",
                        lambda self, eo: make_fetched(POOL_ACT, pages_count=999))
    with pytest.raises(A.PublicationMismatch):
        A.acquire_pdf(POOL_ACT, A.PoolPublicationV2(), tmp_path)
    assert not list(tmp_path.rglob("*"))


@pytest.mark.parametrize("batch, expected", [("batch-01", "v1"), ("batch-02", "v1"), ("batch-03", "v2")])
def test_batch_connector_version_is_independent_of_target_date(monkeypatch, batch, expected):
    seen = []
    monkeypatch.setitem(A.TARGET_DATES, "batch-03", "2026-10-22")
    monkeypatch.setattr(A, "frozen_selection", lambda *args: ({"selected": []}, "sha"))
    monkeypatch.setattr(A, "PoolPublication", lambda **kwargs: seen.append("v1"))
    monkeypatch.setattr(A, "PoolPublicationV2", lambda **kwargs: seen.append("v2"))
    assert A.run(Path(batch), Path("unused")) == 0
    assert seen == [expected]


def test_write_once_conflict(tmp_path):
    path = tmp_path / "sub" / "x.json"
    assert A.write(path, {"a": 1}) == "new"
    assert A.write(path, {"a": 1}) == "unchanged"
    before = path.read_bytes()
    with pytest.raises(ValueError, match="immutable output conflict"):
        A.write(path, {"a": 2})
    assert path.read_bytes() == before


def test_run_catches_only_edition_mismatch(tmp_path, monkeypatch):
    batch = tmp_path / "batch"
    batch.mkdir()
    selection = {"selected": [dict(POOL_ACT)], "quotas_filled": True}
    monkeypatch.setattr(A, "frozen_selection", lambda b, w=False: (selection, "s"))
    monkeypatch.setattr(A, "acquire_pdf", lambda act, c, b: {
        "status": "ok", "runs": [], "item": {}, "sha256": "d", "asset": {"archive_key": "k", "byte_length": 1},
        "authority": "X", "card_sha256": "c", "pdf_file_length": 1})
    monkeypatch.setattr(A, "write_pdf_input", lambda *a: (batch / "i.json", batch / "p.json"))
    monkeypatch.setattr(A, "sha", lambda p: "0")
    monkeypatch.setattr(A, "rel", lambda p: str(p))

    def mismatch(*args):
        raise A.EditionMismatch("edition count")

    monkeypatch.setattr(A, "acquire_official", mismatch)
    monkeypatch.setattr(A, "retryable", lambda failure: False)
    assert A.run(batch, tmp_path, with_official=True) == 0
    assert list((batch / "failures").glob("*official*.json"))
    receipt = A.read(batch / "receipts" / (POOL_ACT["eo_number"] + ".json"))
    assert receipt["official"]["stage"] == "official_validation"

    def broken(*args):
        raise ValueError("unrelated defect")

    (batch / "receipts" / (POOL_ACT["eo_number"] + ".json")).unlink()
    monkeypatch.setattr(A, "acquire_official", broken)
    with pytest.raises(ValueError, match="unrelated defect"):
        A.run(batch, tmp_path, with_official=True)


def test_run_without_official_never_touches_ips(tmp_path, monkeypatch):
    batch = tmp_path / "batch"
    batch.mkdir()
    monkeypatch.setattr(A, "frozen_selection", lambda b, w=False: ({"selected": [dict(POOL_ACT)], "quotas_filled": True}, "s"))
    monkeypatch.setattr(A, "acquire_pdf", lambda act, c, b: {
        "status": "ok", "runs": [], "item": {}, "sha256": "d", "asset": {"archive_key": "k", "byte_length": 1},
        "authority": "X", "card_sha256": "c", "pdf_file_length": 1})
    monkeypatch.setattr(A, "write_pdf_input", lambda *a: (batch / "i.json", batch / "p.json"))
    monkeypatch.setattr(A, "sha", lambda p: "0")
    monkeypatch.setattr(A, "rel", lambda p: str(p))
    monkeypatch.setattr(A, "acquire_official", lambda *a: pytest.fail("official must not run"))
    assert A.run(batch, tmp_path) == 0
    receipt = A.read(batch / "receipts" / (POOL_ACT["eo_number"] + ".json"))
    assert receipt["official"] == {"status": "not_requested", "runs": [], "run_ids": []}


def test_frozen_selection_official_only_with_flag(tmp_path):
    import json

    selection = {"quotas_filled": True, "selected": [{"eo_number": "1"}]}
    raw = json.dumps(selection).encode()
    (tmp_path / "selection.json").write_bytes(raw)
    (tmp_path / "selection.sha256").write_text(A.hashlib.sha256(raw).hexdigest() + "  selection.json")
    assert A.frozen_selection(tmp_path)[0] == selection
    with pytest.raises(ValueError):
        A.frozen_selection(tmp_path, with_official=True)


def refill_fixture(tmp_path):
    import json

    rows = [card(n, ["federal_law", "ministry_order"][n % 2], pages=5 if n % 4 else 30) for n in range(1, 41)]
    cache = {"2020-01-01": rows[:20], "2020-01-02": rows[20:], "2020-01-03": {"error": "bad"}}
    base = P.select_pool(rows, {"federal_law": 2, "ministry_order": 2}, 9, long_min=1, pages_range=(3, 200))
    base.update({"days_sampled": list(cache), "already_used": [], "quotas_filled": True})
    batch = tmp_path / "batch"
    batch.mkdir()
    raw = (json.dumps(base, ensure_ascii=False, sort_keys=True) + chr(10)).encode()
    (batch / "selection.json").write_bytes(raw)
    (batch / "selection.sha256").write_text(P.hashlib.sha256(raw).hexdigest() + "  selection.json" + chr(10))
    (tmp_path / "feed.json").write_text(json.dumps(cache), encoding="utf-8")
    return batch, base, rows


def test_refill_replaces_failed_slot_with_next_same_category_candidate(tmp_path):
    batch, base, rows = refill_fixture(tmp_path)
    failed = base["selected"][1]
    failures = {failed["eo_number"]: "invalid_asset: not a PDF"}
    result = P.refill(base, {r["eo_number"]: r for r in rows}, failures,
                      taken={r["eo_number"] for r in base["selected"]})
    (item,) = result["replaced"]
    new = item["replacement"]
    assert item["failed_reason"] == "invalid_asset: not a PDF" and item["attempt"] == 1
    assert new["act_type"] == failed["act_type"] and new["eo_number"] != failed["eo_number"]
    # first eligible of the category in the seeded order, nothing selected or failed before it
    skipped = {r["eo_number"] for r in base["selected"]}
    expected = [r for r in P.ordered(rows, 9) if r["act_type"] == failed["act_type"] and r["eo_number"] not in skipped][0]
    assert new["eo_number"] == expected["eo_number"]
    assert result["long_selected_after"] >= base["long_min"]
    again = P.refill(base, {r["eo_number"]: r for r in reversed(rows)}, failures,
                     taken={r["eo_number"] for r in base["selected"]})
    assert again == result
    with pytest.raises(ValueError, match="exhausted"):
        P.refill(base, {r["eo_number"]: r for r in rows}, failures, attempts={failed["eo_number"]: 3})


def test_refill_keeps_long_share(tmp_path):
    batch, base, rows = refill_fixture(tmp_path)
    long_rows = [r for r in base["selected"] if r["pages"] >= 20]
    assert long_rows
    base = dict(base, long_min=len(long_rows))
    failed = long_rows[0]
    result = P.refill(base, {r["eo_number"]: r for r in rows}, {failed["eo_number"]: "x"},
                      taken={r["eo_number"] for r in base["selected"]})
    assert result["selected"][0]["pages"] >= 20


def test_refill_round_write_once_and_chain(tmp_path):
    import json

    batch, base, rows = refill_fixture(tmp_path)
    failed = base["selected"][0]["eo_number"]
    (batch / "failures").mkdir()
    (batch / "failures" / f"{failed}-run1.json").write_text(
        json.dumps({"stage": "pdf_acquisition", "reason": "invalid_card: empty name", "runs": []}), encoding="utf-8")
    first = P.refill_round(batch, tmp_path / "feed.json")
    assert first["round"] == 1 and first["replaced"][0]["failed_reason"] == "invalid_card: empty name"
    P.write_refill(batch, first)
    with pytest.raises(FileExistsError):
        P.write_refill(batch, first)
    with pytest.raises(ValueError, match="no failed slot"):
        P.refill_round(batch, tmp_path / "feed.json")
    # the refill act fails too: second round takes the next candidate, attempt 2
    second_failed = first["selected"][0]["eo_number"]
    (batch / "failures" / f"{second_failed}-run1.json").write_text(
        json.dumps({"stage": "pdf_acquisition", "reason": "invalid_asset", "runs": []}), encoding="utf-8")
    second = P.refill_round(batch, tmp_path / "feed.json")
    assert second["round"] == 2 and second["replaced"][0]["attempt"] == 2
    assert second["selected"][0]["eo_number"] not in {second_failed, failed, *(r["eo_number"] for r in base["selected"])}
    # the acquisition script merges refills and drops replaced acts
    P.write_refill(batch, second)
    selection, _ = A.frozen_selection(batch)
    eos = [a["eo_number"] for a in selection["selected"]]
    assert failed not in eos and second_failed not in eos and second["selected"][0]["eo_number"] in eos
    assert len(eos) == len(base["selected"])
    (batch / "selection-refill-02.json").write_text("{}")
    with pytest.raises(ValueError, match="differs from its sha256"):
        A.frozen_selection(batch)


def test_refill_round_replaces_acquired_act_whose_ocr_failed(tmp_path):
    import json

    batch, base, rows = refill_fixture(tmp_path)
    acquired = base["selected"][1]["eo_number"]
    (batch / "receipts").mkdir()
    (batch / "receipts" / f"{acquired}.json").write_text("{}", encoding="utf-8")
    (batch / "failures").mkdir()
    # an acquisition failure record of an act that has a receipt is not a failed slot
    (batch / "failures" / f"{acquired}-run1.json").write_text(
        json.dumps({"stage": "pdf_acquisition", "reason": "transient", "runs": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="no failed slot"):
        P.refill_round(batch, tmp_path / "feed.json")
    (batch / "failures" / f"{acquired}-ocr-run-01.json").write_text(
        json.dumps({"stage": "ocr", "status": "failed", "reason": "ocr_failed: token limit, pages 25, 30, 42"}),
        encoding="utf-8")
    result = P.refill_round(batch, tmp_path / "feed.json")
    (item,) = result["replaced"]
    assert item["failed_eo_number"] == acquired
    assert item["failed_reason"] == "ocr_failed: token limit, pages 25, 30, 42"
    assert item["replacement"]["act_type"] == base["selected"][1]["act_type"]


def test_code_page_ceiling_applies_to_codes_only():
    rows = [{"eo_number": "c1", "act_type": "code", "pages": 480, "title": "Кодекс административного судопроизводства Российской Федерации",
             "number": "21-ФЗ", "date": "2015-03-08"},
            {"eo_number": "l1", "act_type": "federal_law", "pages": 480, "title": "О бюджете",
             "number": "1-ФЗ", "date": "2015-03-08"}]
    quotas = {"code": 1, "federal_law": 1}
    narrow = P.select_pool(rows, quotas, 7, require_single_edition=False, pages_range=(3, 200))
    assert narrow["selected"] == [] and "code_pages_max" not in narrow
    wide = P.select_pool(rows, quotas, 7, require_single_edition=False, pages_range=(3, 200),
                         code_pages_max=P.CODE_PAGES_MAX)
    assert [r["eo_number"] for r in wide["selected"]] == ["c1"]
    assert {r["eo_number"]: r["reason"] for r in wide["rejected"]} == {"l1": "pages_out_of_range"}
    assert wide["code_pages_max"] == 500 and wide["pages_range"] == [3, 200]


@pytest.mark.parametrize("title", [
    "Об утверждении Водного кодекса Российской Федерации",
    "Об утверждении Кодекса Российской Федерации об административных правонарушениях",
    "О внесении изменений в Водный кодекс Российской Федерации",
    "О признании утратившим силу Водного кодекса Российской Федерации",
])
def test_code_title_excludes_approving_and_amending_forms(title):
    assert P.categorize("", title) != "code"


def test_code_title_still_recognized():
    assert P.categorize("", "Водный кодекс Российской Федерации") == "code"


def test_code_candidates_with_zero_code_quota_is_refused(tmp_path):
    from types import SimpleNamespace

    args = SimpleNamespace(output=tmp_path / "b" / "selection.json", profile="batch-02",
                           quota=["code=0"], code_candidates=tmp_path / "codes.json", seed=1,
                           date_from="2020-01-01", date_to="2020-12-31", feed_cache=None,
                           min_days=0, partial_output=None, quota_change=None, pages_max=None)
    with pytest.raises(ValueError, match="code quota is zero"):
        P.run(args)


def test_code_candidates_path_is_repo_relative_and_resolves():
    inside = P.PROJECT / "data" / "m1" / "m1-04a" / "codes" / "selection.json"
    assert P.repo_relative(inside) == "data/m1/m1-04a/codes/selection.json"
    assert P.resolve_repo_path("data/m1/m1-04a/codes/selection.json") == inside
    absolute = Path(P.PROJECT.anchor) / "elsewhere" / "x.json"
    assert P.resolve_repo_path(absolute) == absolute


class CensusActual:
    """Authored actual.pravo stand-in for the code census: exact number+date hits only."""

    _api_base = "http://actual.example/api/ebpi"

    def __init__(self, docs):
        self.docs, self.requests = docs, []

    def _get(self, url):
        from urllib.parse import parse_qs, urlsplit

        self.requests.append(url)
        attrs = P.json.loads(parse_qs(urlsplit(url).query)["q"][0])
        assert all(attr.get("AttrId") != 999 for attr in attrs)
        number = attrs[0]["Words"][0]
        docs = [d for d in self.docs if d["docpass0number"] == number]
        return P.json.dumps({"docs": docs}, ensure_ascii=False).encode(), {}


class CensusPublication:
    """Authored day feeds: {iso day: [items]}; every other day is empty."""

    def __init__(self, days):
        self.days, self.calls = days, []

    def fetch_feed(self, day, page):
        self.calls.append((day, page))
        events = self.days.get(day.isoformat(), [])
        return {"events": events, "pages_total": 1 if events else 0,  # the portal reports 0 for empty days
                "raw_bytes": f"authored {day}".encode(), "source_url": f"http://feed/{day}",
                "rejected_items": []}


def census_fixture():
    portal = "Официальный интернет-портал правовой информации (www.pravo.gov.ru), 09.03.2015,\xa0№\xa00001201503090041"
    docs = [
        {"docpass0number": "21-ФЗ", "docpass0date": "20150308", "dochash": "kas",
         "docnames": "Кодекс административного судопроизводства Российской Федерации",
         "publications": [portal, '"Российская газета" от 11.03.2015']},
        {"docpass0number": "63-ФЗ", "docpass0date": "19960613", "dochash": "uk",
         "docnames": "Уголовный кодекс Российской Федерации",
         "publications": ["Собрание законодательства РФ, 17.06.1996, № 25, ст. 2954",
                          '"Российская газета" от 18.06.1996']},
        {"docpass0number": "7-ФЗ", "docpass0date": "20200101", "dochash": "big",
         "docnames": "Авторский кодекс Российской Федерации",
         "publications": ["Официальный интернет-портал правовой информации (www.pravo.gov.ru), 02.01.2020, № 0001202001020001"]},
        {"docpass0number": "8-ФЗ", "docpass0date": "20200101", "dochash": "amend",
         "docnames": "О внесении изменений в Авторский кодекс Российской Федерации", "publications": []},
    ]
    kas = {"eoNumber": "0001201503090041", "complexName": "Федеральный закон от 08.03.2015 № 21-ФЗ",
           "name": "Кодекс административного судопроизводства Российской Федерации", "number": "21-ФЗ",
           "documentDate": "2015-03-08T00:00:00", "pagesCount": 480}
    big = dict(kas, eoNumber="0001202001020001", name="Авторский кодекс Российской Федерации",
               number="7-ФЗ", documentDate="2020-01-01T00:00:00", pagesCount=900)
    reference = (("КАС", "21-ФЗ", "2015-03-08"), ("УК", "63-ФЗ", "1996-06-13"),
                 ("Авторский", "7-ФЗ", "2020-01-01"), ("Поправка", "8-ФЗ", "2020-01-01"),
                 ("Нет", "9-ФЗ", "2020-01-01"))
    return CensusActual(docs), CensusPublication({"2015-03-09": [kas], "2020-01-02": [big]}), reference


def test_code_census_reasons_and_freeze(tmp_path):
    from datetime import date

    actual, publication, reference = census_fixture()
    output = tmp_path / "codes/selection.json"
    result = P.write_code_census(actual, publication, output, {"x": 1}, reference)
    by_number = {e["number"]: e for e in result["codes"]}
    assert by_number["21-ФЗ"]["status"] == "eligible" and by_number["21-ФЗ"]["pages"] == 480
    assert by_number["21-ФЗ"]["portal_publication"] == {"date": "2015-03-09", "eo_number": "0001201503090041"}
    assert by_number["63-ФЗ"]["reason"] == "no_portal_publication"
    assert by_number["63-ФЗ"]["feed_check"]["day"] == "1996-06-17"  # earliest dated publication
    assert by_number["7-ФЗ"]["reason"] == "pages_out_of_range"
    assert by_number["8-ФЗ"]["reason"] == "not_a_code_title"
    assert by_number["9-ФЗ"]["reason"] == "not_in_official_tree"
    assert set(result["excluded_by_reason"]) <= set(P.CENSUS_REASONS)
    rows, digest = P.load_code_candidates(output)
    assert [r["eo_number"] for r in rows] == ["0001201503090041"]
    assert digest == result["selection_sha256"]
    # The freeze reads only the eligible day again; act bodies are never requested.
    assert publication.calls.count((date(2015, 3, 9), 1)) == 2
    assert len(actual.requests) == 5
    with pytest.raises(FileExistsError):
        P.write_code_census(actual, publication, output, None, reference)


def test_code_census_refuses_feed_eo_that_contradicts_actual(tmp_path):
    actual, publication, reference = census_fixture()
    publication.days["2015-03-09"][0] = dict(publication.days["2015-03-09"][0], eoNumber="0001201503090099")
    entries, _ = P.census_codes(actual, publication, reference[:1])
    assert entries[0]["reason"] == "eo_mismatch"


def test_code_census_feed_failure_is_not_eligible(monkeypatch):
    actual, publication, reference = census_fixture()

    def broken(day, page):
        raise RuntimeError("feed down")

    publication.fetch_feed = broken
    monkeypatch.setattr(P.time, "sleep", lambda seconds: None)
    entries, coverage = P.census_codes(actual, publication, reference[:2])
    assert [e["reason"] for e in entries] == ["not_in_day_feed", "no_portal_publication"]
    assert all(c["error"] for c in coverage)


def test_reference_codes_are_code_titles_and_adoption_acts():
    for title, number, adoption in P.CODE_REFERENCE:
        assert P.categorize("", title.split(" (")[0]) == "code", title
        assert number.endswith("-ФЗ") and P.date.fromisoformat(adoption)


def test_code_census_accepts_actual_part_titles():
    actual, publication, _ = census_fixture()
    actual.docs.append({"docpass0number": "51-ФЗ", "docpass0date": "19941130", "dochash": "gk1",
                        "docnames": "Гражданский кодекс Российской Федерации. Часть первая",
                        "publications": ['"Российская газета" от 08.12.1994']})
    entries, _ = P.census_codes(actual, publication, (("ГК 1", "51-ФЗ", "1994-11-30"),))
    assert entries[0]["reason"] == "no_portal_publication"
    assert P.categorize("", "Кодекс Российской Федерации. Часть первая") is None  # feed rule unchanged


def test_code_census_reuses_previous_matches_and_empty_days(tmp_path):
    from datetime import date

    actual, publication, reference = census_fixture()
    first = P.write_code_census(actual, publication, tmp_path / "one/selection.json", None, reference[:2])
    previous = tmp_path / "one/census.json"
    actual.requests.clear()
    publication.calls.clear()
    second = P.write_code_census(actual, publication, tmp_path / "two/selection.json", None, reference[:3],
                                 previous=previous)
    assert len(actual.requests) == 1  # only the code missing from the previous census
    # The empty 1996 day is reused; days with items are fetched again.
    assert (date(1996, 6, 17), 1) not in publication.calls and (date(2015, 3, 9), 1) in publication.calls
    assert [e["status"] for e in second["codes"][:2]] == [e["status"] for e in first["codes"]]
    assert second["codes"][0]["actual"]["reused_from"].endswith("one/census.json")
    assert second["selection_sha256"] == first["selection_sha256"]


def test_batch_03_profile_matches_plan():
    profile = P.PROFILES["batch-03"]
    assert profile["quotas"] == {"code": 2, "federal_law": 2, "presidential_decree": 1,
                                 "government_resolution": 2, "government_order": 1, "ministry_order": 2}
    assert profile["pages_range"] == (3, 200) and profile["long_min"] == 4 and P.LONG_PAGES == 20
    assert profile["codes_from_census"] and profile["prior_batches"] == ("batch-01", "batch-02")
    assert not profile["require_single_edition"] and P.CODE_PAGES_MAX == 500
    # Earlier profiles keep their frozen behaviour.
    assert "prior_batches" not in P.PROFILES["batch-02"] and P.BATCH2_QUOTAS["federal_law"] == 3


def test_batch_04_profile_matches_plan():
    profile = P.PROFILES["batch-04"]
    assert profile["quotas"] == P.BATCH4_QUOTAS == {"federal_law": 3, "presidential_decree": 1,
                                                    "government_resolution": 2, "government_order": 2,
                                                    "ministry_order": 3}
    assert "code" not in profile["quotas"] and not profile.get("codes_from_census")
    assert profile["pages_range"] == (3, 200) and profile["long_min"] == 4
    assert profile["prior_batches"] == ("batch-01", "batch-02", "batch-03")
    assert not profile["require_single_edition"] and profile["exclude_used"]
    # Batch 3 keeps its frozen profile.
    assert P.PROFILES["batch-03"]["prior_batches"] == ("batch-01", "batch-02")


def test_sample_days_excludes_earlier_days_and_keeps_old_order():
    from datetime import date

    start, end = date(2020, 1, 1), date(2020, 12, 31)
    assert P.sample_days(start, end, 5, 120, ()) == P.sample_days(start, end, 5)
    earlier = [d.isoformat() for d in P.sample_days(start, end, 4, 120)]
    fresh = P.sample_days(start, end, 5, 120, earlier)
    assert len(fresh) == 120 and not {d.isoformat() for d in fresh} & set(earlier)


def prior_tree(root):
    """Authored metadata of two earlier batches (no bodies)."""
    import json

    docs = root / "documents"
    (docs / "pool/batch-01/failures").mkdir(parents=True)
    (docs / "pool/batch-02/failures").mkdir(parents=True)
    url = "http://publication.pravo.gov.ru/File/Pdf?eoNumber="
    (docs / "index.json").write_text(json.dumps({"documents": [{"source_url": url + "1" * 16}]}))
    for name, eo, day in (("batch-01", "2" * 16, "2020-01-05"), ("batch-02", "3" * 16, "2020-02-07")):
        (docs / "pool" / name / "index.json").write_text(json.dumps({"documents": [{"source_url": url + eo}]}))
        (docs / "pool" / name / "selection.json").write_text(json.dumps(
            {"selected": [{"eo_number": eo}], "days_sampled": [day]}))
    (docs / "pool/batch-02/selection-refill-01.json").write_text(json.dumps({"selected": [{"eo_number": "4" * 16}]}))
    (docs / "pool/batch-02/failures" / f"{'5' * 16}-x.json").write_text("{}")  # failed refill pick
    (docs / "pool/batch-01/failures" / f"{'6' * 16}-official-1.json").write_text("{}")
    (docs / "pool/batch-01/failures" / "notes.json").write_text("{}")  # not an eo-named record
    return docs


def test_prior_batch_exclusions_cover_indexes_refills_and_failures(tmp_path):
    used, days = P.prior_batch_exclusions(("batch-01", "batch-02"), prior_tree(tmp_path))
    assert used == {c * 16 for c in "123456"}
    assert days == {"2020-01-05", "2020-02-07"}


def batch3_run(tmp_path, monkeypatch, n_codes):
    import json
    from datetime import date, timedelta
    from types import SimpleNamespace

    docs = prior_tree(tmp_path)
    monkeypatch.setattr(P, "DOCUMENTS", docs)
    codes = [card(100 + i, "code", title="Водный кодекс Российской Федерации", pages=480) for i in range(n_codes)]
    code_path = tmp_path / "codes" / "selection.json"
    P.write_selection_pair(code_path, json.dumps({"schema_version": P.CODE_CANDIDATES_SCHEMA,
                                                "candidates": codes}).encode())
    seen = {}

    def days(start, end, seed, count, exclude):
        seen["exclude"] = exclude
        return [date(2020, 3, 1) + timedelta(days=i) for i in range(120)]

    rows = [card(1, "federal_law"), card(7, "federal_law", pages=30), card(8, "federal_law", pages=40),
            card(9, "presidential_decree", pages=25), card(10, "government_resolution", pages=22),
            card(11, "government_resolution"), card(12, "government_order"), card(13, "ministry_order"),
            card(14, "ministry_order"), card(15, "federal_law")]
    batch = docs / "pool" / "batch-03"
    batch.mkdir()
    cache_path = batch / "feed-cache-b3.json"
    cache = {d.isoformat(): [] for d in days(None, None, None, None, None)}
    cache["2020-03-01"] = {"candidates": rows, "feed_pages": []}
    cache_path.write_text(json.dumps(cache), encoding="utf-8")
    monkeypatch.setattr(P, "sample_days", days)
    monkeypatch.setattr(P, "lookup", lambda *args: {"in_official_tree": True, "official_found": True})
    args = SimpleNamespace(output=batch / "selection.json", profile="batch-03", quota=[],
                           code_candidates=code_path, seed=20261023, date_from="2011-01-01",
                           date_to="2025-12-31", feed_cache=cache_path, min_days=120, partial_output=None,
                           quota_change=None, pages_max=None, command="python select ... --profile batch-03")
    return P.run(args), args, seen


def test_batch_03_run_takes_census_codes_excludes_prior_and_writes_provenance(tmp_path, monkeypatch):
    import json

    status, args, seen = batch3_run(tmp_path, monkeypatch, 1)
    assert status == 0 and seen["exclude"] == ["2020-01-05", "2020-02-07"]
    selection = json.loads(Path(args.output).read_bytes())
    assert selection["selected_per_category"]["code"] == 1  # one census code -> quota 1, not an error
    assert selection["quotas_filled"] and selection["long_selected"] >= 4
    assert {c * 16 for c in "123456"} <= set(selection["already_used"])
    assert selection["days_excluded_from_sampling"] == ["2020-01-05", "2020-02-07"]
    assert selection["code_pages_max"] == 500 and selection["pages_range"] == [3, 200]
    provenance = json.loads((args.output.parent / "selection-provenance.json").read_text(encoding="utf-8"))
    raw = Path(args.output).read_bytes()
    assert provenance["selection_sha256"] == P.hashlib.sha256(raw).hexdigest()
    assert provenance["min_days"] == 120 and provenance["command"] == args.command
    assert provenance["feed_cache"]["sha256"] == P.hashlib.sha256(args.feed_cache.read_bytes()).hexdigest()
    assert P.run(args) == 0  # frozen pair: unchanged, provenance untouched
    assert json.loads((args.output.parent / "selection-provenance.json").read_text(encoding="utf-8")) == provenance


@pytest.mark.parametrize("n_codes, expected", [(2, 2), (3, 2)])
def test_batch_03_code_quota_is_census_count_capped_at_two(tmp_path, monkeypatch, n_codes, expected):
    import json

    status, args, _ = batch3_run(tmp_path, monkeypatch, n_codes)
    assert status == 0
    assert json.loads(Path(args.output).read_bytes())["quotas"]["code"] == expected


def test_main_records_exact_command(monkeypatch):
    seen = []
    monkeypatch.setattr(P, "run", lambda args: seen.append(args.command) or 0)
    argv = ["--profile", "batch-03", "--from", "2011-01-01", "--to", "2025-12-31", "--seed", "20261023",
            "--output", "a b/selection.json"]
    assert P.main(argv) == 0
    assert seen == ['PYTHONPATH=src ' + subprocess.list2cmdline([sys.executable]) + ' docs/assets/select_m1_04a_pool.py --profile batch-03 --from 2011-01-01 '
                    '--to 2025-12-31 --seed 20261023 --output "a b/selection.json"']


def test_catalog_records_batch_04_measured_then_development():
    catalog = load_script("build_m1_04a_catalog")
    assert "batch-04" in catalog.POOL_BATCHES
    history = catalog.POOL_STATUS["batch-04"]  # written only after the first pass
    assert [h["status"] for h in history] == ["measured", "development"]
    assert history[0]["evidence"] == "experiments/20261023-batch-04-first-pass"
    assert history[1]["report"] == "docs/milestones/m1/04a/M1_04A_POOL_BATCH_4_2026-10-23.md"


SOFT = {"require_single_edition": False, "pages_range": (3, 200), "preferred_pages_min": 5,
        "one_per_issuer_day": True}


def test_batch_05_profile_matches_plan():
    profile = P.PROFILES["batch-05"]
    assert profile["quotas"] == P.BATCH4_QUOTAS and "code" not in profile["quotas"]
    assert profile["pages_range"] == (3, 200) and profile["long_min"] == 4
    assert profile["prior_batches"] == ("batch-01", "batch-02", "batch-03", "batch-04")
    assert profile["preferred_pages_min"] == 5 and profile["one_per_issuer_day"] is True
    assert not profile["require_single_edition"] and profile["exclude_used"]
    # Earlier profiles carry no soft preferences.
    for name in ("batch-01", "batch-02", "batch-03", "batch-04"):
        assert "preferred_pages_min" not in P.PROFILES[name] and "one_per_issuer_day" not in P.PROFILES[name]


def test_short_act_not_taken_while_preferred_candidates_suffice():
    rows = [card(n, pages=3 + n % 2, issuer=f"i{n}", publication_date="2020-01-02") for n in range(1, 9)]
    rows += [card(n, pages=5 + n, issuer=f"i{n}", publication_date="2020-01-02") for n in range(9, 12)]
    for seed in range(1, 6):
        result = P.select_pool(rows, {"federal_law": 3}, seed, **SOFT)
        assert sorted(ids(result)) == [f"{n:016d}" for n in (9, 10, 11)], seed
        assert result["soft_fallbacks"] == [] and result["preferred_pages_min"] == 5
        assert result["soft_fallback_counts"] == {"issuer_day_repeat": 0, "pages_below_preferred": 0}


def test_short_act_taken_only_to_fill_quota_and_recorded():
    rows = [card(1, pages=4, issuer="a", publication_date="2020-01-02"),
            card(2, pages=3, issuer="b", publication_date="2020-01-02"),
            card(3, pages=12, issuer="c", publication_date="2020-01-02")]
    result = P.select_pool(rows, {"federal_law": 2}, 7, **SOFT)
    assert ids(result)[0] == f"{3:016d}" and len(ids(result)) == 2
    short = ids(result)[1]
    expected_first = min((f"{1:016d}", f"{2:016d}"), key=lambda eo: P.order_key(7, eo))
    assert short == expected_first  # seeded order among the fallbacks
    assert result["soft_fallbacks"] == [{"eo_number": short, "act_type": "federal_law",
                                         "pages": 4 if short.endswith("1") else 3,
                                         "misses": ["pages_below_preferred"]}]
    assert result["soft_fallback_counts"]["pages_below_preferred"] == 1
    assert result["selected"][0]["issuer"] == "c" and result["selected"][0]["publication_date"] == "2020-01-02"


def test_one_act_per_type_issuer_and_day_unless_quota_needs_more():
    twins = [card(1, pages=40, issuer="mintrans", publication_date="2015-03-10"),
             card(2, pages=40, issuer="mintrans", publication_date="2015-03-10")]
    other = card(3, pages=8, issuer="minselhoz", publication_date="2015-03-10")
    same_issuer_other_day = card(4, pages=8, issuer="mintrans", publication_date="2015-03-11")
    other_type = card(5, "ministry_order", pages=8, issuer="mintrans", publication_date="2015-03-10")
    for seed in range(1, 6):
        result = P.select_pool(twins + [other], {"federal_law": 2}, seed, **SOFT)
        chosen = set(ids(result))
        assert len(chosen & {f"{1:016d}", f"{2:016d}"}) == 1 and f"{3:016d}" in chosen, seed
        assert result["soft_fallbacks"] == []
        result = P.select_pool(twins + [same_issuer_other_day], {"federal_law": 2}, seed, **SOFT)
        assert f"{4:016d}" in ids(result) and result["soft_fallbacks"] == []
        result = P.select_pool(twins + [other_type], {"federal_law": 1, "ministry_order": 1}, seed, **SOFT)
        assert f"{5:016d}" in ids(result) and result["soft_fallbacks"] == []
        # Only the twins: the second one fills the quota and is recorded.
        result = P.select_pool(twins, {"federal_law": 2}, seed, **SOFT)
        assert len(ids(result)) == 2
        assert [f["misses"] for f in result["soft_fallbacks"]] == [["issuer_day_repeat"]]
        assert result["soft_fallback_counts"] == {"issuer_day_repeat": 1, "pages_below_preferred": 0}


def test_soft_preferences_keep_long_share_first():
    rows = [card(n, pages=8, issuer=f"s{n}", publication_date="2020-01-02") for n in range(1, 20)]
    rows += [card(30, pages=30, issuer="x", publication_date="2020-01-02"),
             card(31, pages=30, issuer="x", publication_date="2020-01-02")]
    result = P.select_pool(rows, {"federal_law": 3}, 3, long_min=2, long_pages=20, **SOFT)
    assert result["long_selected"] == 2  # the twin is taken in the fallback long pass
    assert [f["misses"] for f in result["soft_fallbacks"]] == [["issuer_day_repeat"]]


@pytest.mark.parametrize("seed", [1, 2, 3, 20261024])
def test_soft_preferences_off_leave_selection_unchanged(seed):
    rows = [card(n, ["federal_law", "ministry_order"][n % 2], pages=3 + (n * 7) % 40,
                 issuer="same", publication_date="2020-01-02") for n in range(1, 60)]
    kwargs = {"require_single_edition": False, "pages_range": (3, 200), "long_min": 2, "long_pages": 20}
    quotas = {"federal_law": 2, "ministry_order": 3}
    plain = P.select_pool(rows, quotas, seed, **kwargs)
    explicit = P.select_pool(rows, quotas, seed, preferred_pages_min=None, one_per_issuer_day=False, **kwargs)
    assert plain == explicit
    assert not {"soft_fallbacks", "preferred_pages_min", "one_per_issuer_day"} & set(plain)
    assert all("issuer" not in row for row in plain["selected"])


def test_frozen_batch_04_selection_reproduces_from_its_feed_cache():
    import json

    batch = Path(__file__).resolve().parents[3] / "data/m1/m1-04a/documents/pool/batch-04"
    if not (batch / "feed-cache-b4.json").exists():
        pytest.skip("local batch-04 data not present")
    raw = (batch / "selection.json").read_bytes()
    assert P.hashlib.sha256(raw).hexdigest().startswith("bf4bde02")
    frozen = json.loads(raw)
    cache = json.loads((batch / "feed-cache-b4.json").read_text(encoding="utf-8"))
    profile = P.PROFILES["batch-04"]
    result = P.select_pool(list(P.pool_from_cache(cache, frozen["days_sampled"]).values()), profile["quotas"],
                           frozen["seed"], require_single_edition=False, already_used=set(frozen["already_used"]),
                           pages_range=profile["pages_range"], long_min=profile["long_min"])
    assert ids(result) == [row["eo_number"] for row in frozen["selected"]]
    assert result["rejected"] == frozen["rejected"] and result["long_selected"] == frozen["long_selected"]
    for row, frozen_row in zip(result["selected"], frozen["selected"]):
        assert {k: frozen_row[k] for k in row} == row


def test_feed_cards_carry_issuer_and_publication_day():
    from datetime import date

    class Publication:
        def fetch_feed(self, day, page):
            base = {"documentDate": "2015-03-03T00:00:00", "pagesCount": 9,
                    "publishDateShort": "2015-03-10T00:00:00", "name": "Об акте"}
            prefix = "Приказ Министерства транспорта Российской Федерации от 03.03.2015 № "
            return {"events": [
                dict(base, eoNumber="1" * 16, number="107", complexName=prefix + "107",
                     signatoryAuthorityId="guid-mintrans"),
                dict(base, eoNumber="2" * 16, number="108", complexName=prefix + "108"),
            ], "pages_total": 1, "raw_bytes": b"x", "source_url": "http://source", "rejected_items": []}

    cards = P.feed_candidates(Publication(), date(2015, 3, 10))
    assert [c["issuer"] for c in cards] == [
        "guid-mintrans", "name:Приказ Министерства транспорта Российской Федерации"]
    assert {c["publication_date"] for c in cards} == {"2015-03-10"}


def test_catalog_records_batch_05_measured_then_development():
    catalog = load_script("build_m1_04a_catalog")
    assert catalog.POOL_BATCHES == ("batch-01", "batch-02", "batch-03", "batch-04", "batch-05")
    history = catalog.POOL_STATUS["batch-05"]  # written only after the first pass
    assert [h["status"] for h in history] == ["measured", "development"]
    assert history[0]["evidence"] == "experiments/20261023-batch-05-first-pass"
    assert history[1]["report"] == "docs/milestones/m1/04a/M1_04A_POOL_BATCH_5_2026-10-23.md"


def test_batch_06_profile_repeats_batch_05_with_prior_batches_01_to_05():
    b5, b6 = P.PROFILES["batch-05"], P.PROFILES["batch-06"]
    assert {k: v for k, v in b6.items() if k != "prior_batches"} == {
        k: v for k, v in b5.items() if k != "prior_batches"}
    assert b6["prior_batches"] == ("batch-01", "batch-02", "batch-03", "batch-04", "batch-05")
    assert b6["quotas"] == P.BATCH4_QUOTAS and b6["long_min"] == 4 and b6["pages_range"] == (3, 200)
    assert b6["preferred_pages_min"] == 5 and b6["one_per_issuer_day"] is True


def test_profiles_01_to_05_unchanged_by_batch_06():
    assert P.PROFILES["batch-05"]["prior_batches"] == ("batch-01", "batch-02", "batch-03", "batch-04")
    assert P.PROFILES["batch-04"]["prior_batches"] == ("batch-01", "batch-02", "batch-03")
    assert P.PROFILES["batch-03"]["prior_batches"] == ("batch-01", "batch-02")
    assert "prior_batches" not in P.PROFILES["batch-02"] and "prior_batches" not in P.PROFILES["batch-01"]


def test_frozen_batch_05_selection_reproduces_from_its_feed_cache():
    import json

    batch = Path(__file__).resolve().parents[3] / "data/m1/m1-04a/documents/pool/batch-05"
    if not (batch / "feed-cache-b5.json").exists():
        pytest.skip("local batch-05 data not present")
    raw = (batch / "selection.json").read_bytes()
    assert P.hashlib.sha256(raw).hexdigest().startswith("ab90d9c9")
    frozen = json.loads(raw)
    cache = json.loads((batch / "feed-cache-b5.json").read_text(encoding="utf-8"))
    profile = P.PROFILES["batch-05"]
    result = P.select_pool(list(P.pool_from_cache(cache, frozen["days_sampled"]).values()), profile["quotas"],
                           frozen["seed"], require_single_edition=False, already_used=set(frozen["already_used"]),
                           pages_range=profile["pages_range"], long_min=profile["long_min"],
                           preferred_pages_min=profile["preferred_pages_min"],
                           one_per_issuer_day=profile["one_per_issuer_day"])
    assert ids(result) == [row["eo_number"] for row in frozen["selected"]]
    assert result["rejected"] == frozen["rejected"] and result["long_selected"] == frozen["long_selected"]
    assert result["soft_fallbacks"] == frozen["soft_fallbacks"]
    for row, frozen_row in zip(result["selected"], frozen["selected"]):
        assert {k: frozen_row[k] for k in row} == row
