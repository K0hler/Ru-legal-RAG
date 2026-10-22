"""Authored portal responses; no network or retained act bodies."""

from datetime import date
import hashlib
import json
from pathlib import Path

import pytest

from legal_rag.sources.acquisition import acquire_publication
from legal_rag.sources.publication_pravo import PublicationPravoConnector
from legal_rag.sources.publication_pravo import PublicationPravoFailure
from legal_rag.sources.publication_pool import PublicationPoolConnector as Connector


EO = "0001202001010001"
DAY = date(2020, 1, 1)


def card(**changes):
    value = {"eoNumber": EO, "name": "", "number": "1-р", "pagesCount": 3,
             "complexName": "Распоряжение Правительства Российской Федерации от 01.01.2020 № 1-р",
             "documentDate": "2020-01-01T00:00:00", "publishDateShort": "2020-01-01T00:00:00",
             "documentType": {"name": "Распоряжение"},
             "signatoryAuthorities": [{"name": "Правительство Российской Федерации"}]}
    return dict(value, **changes)


def event(n, **changes):
    return dict(card(eoNumber=f"{n:016d}", name="Об авторском примере", title="Пример"), **changes)


def feed(items):
    return {"items": items, "currentPage": 1, "itemsPerPage": 200,
            "itemsTotalCount": len(items), "pagesTotalCount": 1}


def replay(monkeypatch, responses):
    responses = iter(responses)

    def get(self, url, accept):
        body = next(responses)
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=False).encode()
        return body, {"request_url": url, "response_url": url, "http_status": 200,
                      "headers": {"content-type": accept}}

    monkeypatch.setattr(PublicationPravoConnector, "_get", get)


def test_empty_order_name_archives_exact_card_and_warning(tmp_path, monkeypatch):
    original = card()
    raw = json.dumps(original, ensure_ascii=False).encode()
    replay(monkeypatch, [raw, b"%PDF-authored"] * 2)
    connector = Connector()
    first = acquire_publication(connector, EO, tmp_path)
    second = acquire_publication(connector, EO, tmp_path)
    assert (first["result"], second["result"]) == ("new", "unchanged")
    assert (tmp_path / "raw" / hashlib.sha256(raw).hexdigest()).read_bytes() == raw
    assets = [json.loads(p.read_bytes()) for p in (tmp_path / "assets").glob("*.json")]
    pdf = next(a for a in assets if a["media_type"] == "application/pdf")
    assert pdf["transport_metadata"]["warnings"][0]["reason"] == "empty_card_name"
    assert pdf["transport_metadata"]["card_request"]["sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("change", [{"number": None}, {"complexName": ""},
                                     {"signatoryAuthorities": []}, {"name": None}])
def test_empty_name_does_not_bypass_identity_checks(monkeypatch, change):
    replay(monkeypatch, [card(**change)])
    with pytest.raises(PublicationPravoFailure, match="document card is not valid"):
        Connector().fetch(EO)


def test_feed_rejects_only_invalid_item_and_retains_raw(monkeypatch):
    data = feed([event(1), event(2, number=None), event(3)])
    raw = json.dumps(data, ensure_ascii=False).encode()
    replay(monkeypatch, [raw])
    result = Connector().fetch_feed(DAY)
    assert [i["eoNumber"] for i in result["events"]] == [f"{i:016d}" for i in (1, 3)]
    assert result["raw_bytes"] == raw
    assert result["rejected_items"][0]["index"] == 1
    assert "number must be a string" in result["rejected_items"][0]["message"]


def test_feed_still_rejects_invalid_envelope(monkeypatch):
    replay(monkeypatch, [dict(feed([event(1)]), currentPage=2)])
    with pytest.raises(PublicationPravoFailure, match="pagination"):
        Connector().fetch_feed(DAY)


def test_feed_rejects_duplicates_bad_dates_and_non_objects(monkeypatch):
    data = feed([event(1), event(1), None, event(2, documentDate="bad"), event(3, name=None)])
    replay(monkeypatch, [data])
    result = Connector().fetch_feed(DAY)
    assert [i["eoNumber"] for i in result["events"]] == [f"{1:016d}"]
    assert [r["index"] for r in result["rejected_items"]] == [1, 2, 3, 4]


def test_invalid_feed_item_does_not_hide_valid_same_id(monkeypatch):
    replay(monkeypatch, [feed([event(1, number=None), event(1)])])
    result = Connector().fetch_feed(DAY)
    assert len(result["events"]) == len(result["rejected_items"]) == 1


@pytest.mark.parametrize("asset, label", [(b"PK\x03\x04authored", "ZIP"),
                                         (b"<!DOCTYPE html>", "HTML"), (b"II*\0", "TIFF")])
def test_non_pdf_reports_source_format(tmp_path, monkeypatch, asset, label):
    replay(monkeypatch, [card(name="Об авторском примере"), asset])
    result = acquire_publication(Connector(), EO, tmp_path)
    report = json.loads(Path(result["report"]).read_bytes())
    assert report["errors"][0]["reason"] == "unsupported_asset_format"
    assert label in report["errors"][0]["message"]
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize("raw", [b"x%PDF-authored", b" " * 1025 + b"%PDF-authored"])
def test_unknown_signature_is_not_accepted_as_pdf(monkeypatch, raw):
    replay(monkeypatch, [card(name="Об авторском примере"), raw])
    with pytest.raises(PublicationPravoFailure, match="not PDF"):
        Connector().fetch(EO)


def test_whitespace_only_order_name_is_not_replaced(monkeypatch):
    replay(monkeypatch, [card(name="   ")])
    with pytest.raises(PublicationPravoFailure, match="document card is not valid"):
        Connector().fetch(EO)
