"""Opt-in pool adapter; frozen publication-pravo/1 validation remains unchanged.

Temporary validation views never replace archived source bytes. Feed envelopes and
each item are checked by the frozen validator, with item failures reported separately.
"""

from datetime import datetime
import hashlib
import json
from urllib.parse import parse_qs, urlsplit

from .publication_pravo import PublicationPravoConnector, PublicationPravoFailure


class _FeedReplay(PublicationPravoConnector):
    def __init__(self, feed, transport):
        super().__init__()
        self.response = json.dumps(feed, ensure_ascii=False).encode(), transport

    def _get(self, url, accept):
        return self.response


class PublicationPoolConnector(PublicationPravoConnector):
    adapter_version = "publication-pravo-pool/2"

    def fetch_feed(self, publication_date, page=1):
        self._rejected = []
        fetched = super().fetch_feed(publication_date, page)
        fetched["raw_bytes"] = self._feed_bytes
        fetched["rejected_items"] = self._rejected
        return fetched

    def fetch(self, eo_number):
        self._warnings = []
        fetched = super().fetch(eo_number)
        fetched["publication_card_bytes"] = self._card_bytes
        fetched["raw_bytes"] = self._asset_bytes
        transport = fetched["transport_metadata"]
        transport["card_request"]["sha256"] = hashlib.sha256(self._card_bytes).hexdigest()
        transport["warnings"] = self._warnings
        return fetched

    def _get(self, url, accept):
        raw, transport = super()._get(url, accept)
        route = urlsplit(url).path
        if route == "/File/Pdf":
            self._asset_bytes = raw
            if raw.startswith(b"%PDF-"):
                return raw, transport
            kind = "unknown format"
            if raw.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
                kind = "ZIP archive"
            elif raw.startswith((b"II*\0", b"MM\0*")):
                kind = "TIFF image"
            elif raw.lstrip()[:32].lower().startswith((b"<!doctype html", b"<html")):
                kind = "HTML response"
            headers = transport.get("headers", {})
            raise PublicationPravoFailure(
                "unsupported_asset_format",
                f"File/Pdf returned {kind}, not PDF; content-type={headers.get('content-type')}; "
                f"content-disposition={headers.get('content-disposition')}. "
                "Archive/image conversion is outside the PDF acquisition contract.",
                retryable=False, source_url=url,
            )
        try:
            value = json.loads(raw.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError):
            return raw, transport  # Frozen validator reports malformed JSON.
        if route == "/api/Document":
            self._card_bytes = raw
            if (isinstance(value, dict) and isinstance(value.get("name"), str)
                    and value["name"] == ""
                    and isinstance(value.get("documentType"), dict)
                    and value["documentType"].get("name") == "Распоряжение"
                    and isinstance(value.get("signatoryAuthorities"), list)
                    and any(isinstance(a, dict) and a.get("name") == "Правительство Российской Федерации"
                            for a in value["signatoryAuthorities"])):
                value["name"] = value.get("complexName")
                self._warnings.append({"reason": "empty_card_name", "title_field": "complexName"})
                return json.dumps(value, ensure_ascii=False).encode(), transport
        elif route == "/api/Documents" and isinstance(value, dict) and isinstance(value.get("items"), list):
            self._feed_bytes = raw
            query = parse_qs(urlsplit(url).query)
            day = datetime.strptime(query["Date"][0], "%d.%m.%Y").date()
            page = int(query["Index"][0])
            envelope = dict(value, items=[])
            _FeedReplay(envelope, transport).fetch_feed(day, page)
            valid, seen = [], set()
            for index, item in enumerate(value["items"]):
                try:
                    _FeedReplay(dict(envelope, items=[item]), transport).fetch_feed(day, page)
                    if item["eoNumber"] in seen:
                        raise PublicationPravoFailure("invalid_feed_item", "duplicate feed eoNumber",
                                                      retryable=False, source_url=url)
                except PublicationPravoFailure as error:
                    self._rejected.append({"index": index,
                                           "eo_number": item.get("eoNumber") if isinstance(item, dict) else None,
                                           **error.as_record()})
                    continue
                seen.add(item["eoNumber"])
                valid.append(item)
            return json.dumps(dict(value, items=valid), ensure_ascii=False).encode(), transport
        return raw, transport
