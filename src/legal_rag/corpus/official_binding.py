"""Validate a same-edition acquisition record without importing source adapters."""

import hashlib
import json
from urllib.parse import parse_qs, urlsplit

from .compiler import _asset, _hash, _inside, _object, _read, _text


def validate_binding(root, bundle, assets):
    _object(bundle, {"schema_version", "source_system", "source_item", "document_hash", "source_url",
                     "selector", "text_sha256", "structure_sha256", "edition_evidence_sha256"}, optional={"transport_evidence"})
    for field in ("schema_version", "source_system", "source_item", "source_url"):
        _text(bundle[field])
    for field in ("document_hash", "text_sha256", "structure_sha256", "edition_evidence_sha256"):
        _hash(bundle[field])
    if bundle["schema_version"] not in {"official-structure-bundle/1", "official-structure-bundle/2"}:
        raise ValueError("unknown structure bundle version")
    current = bundle["schema_version"] == "official-structure-bundle/2"
    if current:
        _object(bundle.get("transport_evidence"), {"text", "structure"})
    elif "transport_evidence" in bundle:
        raise ValueError("legacy bundle cannot contain per-capture transport")
    selector = _object(bundle["selector"], {"database", "document_id", "edition_id"})
    for field in ("database", "document_id"):
        _text(selector[field])
    actual = bundle["source_system"] == "actual.pravo.gov.ru"
    if bundle["source_system"] not in {"actual.pravo.gov.ru", "pravo.gov.ru/legislation-russia"}:
        raise ValueError("unsupported structure source")
    if type(selector["edition_id"]) is not int or selector["edition_id"] <= 0:
        raise ValueError("invalid structure edition selector")
    item_id = hashlib.sha256(bundle["source_item"].encode()).hexdigest()
    item = _read(_inside(root, f"items/{item_id}.json"))
    if (bundle["source_item"] != bundle["source_system"] + ":" + bundle["document_hash"]
            or item["source_system"] != bundle["source_system"] or item["external_id"] != bundle["document_hash"]):
        raise ValueError("misbound structure source identity")
    for asset in assets:
        key = "text_sha256" if asset["role"] == "consolidated" else "structure_sha256"
        if (asset["sha256"] != bundle[key] or asset["source_item"] != bundle["source_item"]
                or asset["source_url"] != bundle["source_url"]):
            raise ValueError("structure bundle asset mismatch")
        locator = "$.data" if key == "structure_sha256" else "$.redtext" if actual else "$.doctext"
        if asset["evidence"]["locator"] not in {locator, "/" + locator[2:]}:
            raise ValueError("structure bundle scalar mismatch")
        metadata = _read(_inside(root, f"assets/{asset['sha256']}.json"))
        text = key == "text_sha256"
        capture = bundle["transport_evidence"]["text" if text else "structure"] if current else metadata.get("transport_metadata", {})
        if not isinstance(capture, dict):
            raise ValueError("invalid transport capture")
        request = capture.get("request_url", "")
        url = urlsplit(request)
        query = parse_qs(url.query, keep_blank_values=True)
        if actual:
            origin = "actual.pravo.gov.ru:8000"
            path = "/api/ebpi/redtext" if text else "/api/ebpi/getcontent/"
            expected = {"bpa": ["ebpi"], "t" if text else "rdk": [str(selector["edition_id"])]}
            if text:
                expected["ttl"] = ["0"]
        else:
            origin = "ips.pravo.gov.ru"
            path = "/api/ips/legislation/" + ("documenttext" if text else "document_content")
            expected = {"bpa": [selector["database"]], "nd": [selector["document_id"]], "rdk": [str(selector["edition_id"])]}
        if url.scheme != "http" or url.netloc != origin or url.path != path or query != expected:
            raise ValueError("structure/text transport edition mismatch")
        response_url = capture.get("response_url")
        if current and response_url is None:
            raise ValueError("per-capture response URL is missing")
        if response_url is not None:
            response = urlsplit(response_url)
            if (response.scheme != "http" or response.netloc != origin or response.path != path
                    or parse_qs(response.query, keep_blank_values=True) != expected):
                raise ValueError("structure/text response edition mismatch")
        if text and not actual:
            _, payload = _asset(root, asset["sha256"])
            body = json.loads(payload)
            if (not isinstance(body, dict) or body.get("docid") != selector["document_id"] or body.get("baseid") != selector["database"]
                    or body.get("rdk") != selector["edition_id"]):
                raise ValueError("text body edition mismatch")
    digest = bundle["edition_evidence_sha256"]
    if digest not in item.get("asset_sha256s", []):
        raise ValueError("edition evidence does not belong to source item")
    _, raw = _asset(root, digest)
    evidence = json.loads(raw)
    if not isinstance(evidence, dict):
        raise ValueError("invalid edition evidence object")
    if actual:
        if (evidence.get("dochash") != bundle["document_hash"] or str(evidence.get("docid")) != selector["document_id"]
                or selector["database"] != "ebpi"):
            raise ValueError("structure edition evidence identity mismatch")
        editions, id_key = evidence["redactions"], "redid"
    else:
        if (evidence.get("hash") != bundle["document_hash"] or evidence.get("nd") != selector["document_id"]
                or evidence.get("baseid") != selector["database"] or evidence.get("actualrdk") != selector["edition_id"]):
            raise ValueError("structure edition evidence identity mismatch")
        editions, id_key = evidence["redactions"], "id"
    selected = [e for e in editions if e.get(id_key) == selector["edition_id"]]
    flags = ("actual", "redofficial", "redcompleted", "hascontent", "contentcomplete") if actual else ("actual", "completed")
    if len(selected) != 1 or any(selected[0].get(flag) is not True for flag in flags):
        raise ValueError("structure selected edition is incomplete")
