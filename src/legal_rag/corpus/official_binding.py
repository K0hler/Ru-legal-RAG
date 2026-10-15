"""Validate a same-edition acquisition record without importing source adapters."""

import hashlib
import json
from urllib.parse import parse_qs, urlsplit

from .compiler import _asset, _inside, _object, _read


def validate_binding(root, bundle, assets):
    _object(bundle, {"schema_version", "source_system", "source_item", "document_hash", "source_url",
                     "selector", "text_sha256", "structure_sha256", "edition_evidence_sha256"})
    if bundle["schema_version"] != "official-structure-bundle/1":
        raise ValueError("unknown structure bundle version")
    selector = _object(bundle["selector"], {"database", "document_id", "edition_id"})
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
        request = metadata.get("transport_metadata", {}).get("request_url", "")
        url = urlsplit(request)
        query = {name: values for name, values in parse_qs(url.query).items()}
        text = key == "text_sha256"
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
    digest = bundle["edition_evidence_sha256"]
    if digest not in item.get("asset_sha256s", []):
        raise ValueError("edition evidence does not belong to source item")
    _, raw = _asset(root, digest)
    evidence = json.loads(raw)
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
