"""Authored sidecar controls; original source replay fixtures remain unchanged."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest

from legal_rag.sources.actual_pravo import ActualPravoConnector
from legal_rag.sources.legislation_russia import LegislationRussiaConnector
from legal_rag.sources.structure_bundle import StructureConnector, acquire_bundle


FIXTURES = Path(__file__).with_name("fixtures")


@pytest.mark.parametrize("bank", ["actual", "ips"])
def test_bundle_archives_exact_bytes_same_edition_and_repeats(bank):
    filename = "actual_pravo_59_fz.json" if bank == "actual" else "legislation_russia_pp354.json"
    fixture = json.loads((FIXTURES / filename).read_bytes())
    base = ActualPravoConnector() if bank == "actual" else LegislationRussiaConnector()
    fields = ["card", "redactions", "redtext"] if bank == "actual" else ["card", "text"]
    if bank == "ips" and "text" not in fixture:
        fields[-1] = "documenttext"
    bodies = [json.dumps(fixture[key], ensure_ascii=False).encode() for key in fields]
    sidecar = json.dumps({"status": 0 if bank == "actual" else 200, "complete": True,
                          "data": [{"id": "a1", "np": "p1", "npe": "p2", "lvl": 0,
                                    "caption": "Статья 1", "unit": "статья"}]}).encode()
    connector = StructureConnector(base)
    calls = []

    def get(url):
        calls.append(url)
        body = [*bodies, sidecar][(len(calls) - 1) % (len(bodies) + 1)]
        return body, {"request_url": url, "response_url": url, "http_status": 200, "headers": {}}

    with tempfile.TemporaryDirectory() as temporary, patch.object(base, "_get", side_effect=get):
        root = Path(temporary)
        first = acquire_bundle(connector, fixture["document_hash"], root)
        second = acquire_bundle(connector, fixture["document_hash"], root)
        assert first["result"] == "new"
        assert second["result"] == "unchanged"
        bundle = json.loads(Path(first["structure_bundle"]).read_bytes())
        assert first["structure_bundle"] == second["structure_bundle"]
        assert bundle["schema_version"] == "official-structure-bundle/2"
        assert bundle["text_sha256"] == hashlib.sha256(bodies[-1]).hexdigest()
        assert bundle["structure_sha256"] == hashlib.sha256(sidecar).hexdigest()
        assert (root / "raw" / bundle["structure_sha256"]).read_bytes() == sidecar
        text_url, structure_url = calls[len(bodies) - 1:len(bodies) + 1]
        edition = bundle["selector"]["edition_id"]
        assert f"rdk={edition}" in structure_url
        assert (f"t={edition}" if bank == "actual" else f"rdk={edition}") in text_url
        before = {p.relative_to(root): p.read_bytes() for name in ("raw", "assets", "items", "structure_bundles")
                  for p in (root / name).glob("*")}
        with patch.object(base, "_get", side_effect=[(body, {"request_url": "http://example.invalid"})
                                                    for body in bodies] + [(b'{"status":500,"data":[]}', {})]):
            failed = acquire_bundle(connector, fixture["document_hash"], root)
        assert failed["result"] == "failed"
        assert "structure_bundle" not in failed
        assert before == {p.relative_to(root): p.read_bytes() for name in ("raw", "assets", "items", "structure_bundles")
                          for p in (root / name).glob("*")}


@pytest.mark.parametrize("broken", ["status", "data", "complete", "error"])
def test_actual_invalid_structure_is_not_persisted(broken, tmp_path):
    fixture = json.loads((FIXTURES / "actual_pravo_59_fz.json").read_bytes())
    response = {"status": 0, "data": [{"id": "a"}], "complete": True, "error": None}
    response.update({broken: {"status": 200, "data": {}, "complete": False, "error": "bad"}[broken]})
    connector = StructureConnector(ActualPravoConnector())
    bodies = [json.dumps(copy.deepcopy(fixture[key])).encode() for key in ("card", "redactions", "redtext")]
    with patch.object(connector.base, "_get", side_effect=[(body, {}) for body in [*bodies, json.dumps(response).encode()]]):
        result = acquire_bundle(connector, fixture["document_hash"], tmp_path)
    assert result["result"] == "failed"
    assert not (tmp_path / "raw").exists()


@pytest.mark.parametrize("bank", ["actual", "ips"])
@pytest.mark.parametrize("query_change", ["edition", "empty_selector"])
def test_same_origin_redirect_to_another_edition_is_rejected(bank, query_change, tmp_path):
    fixture = json.loads((FIXTURES / ("actual_pravo_59_fz.json" if bank == "actual" else "legislation_russia_pp354.json")).read_bytes())
    base = ActualPravoConnector() if bank == "actual" else LegislationRussiaConnector()
    fields = ["card", "redactions", "redtext"] if bank == "actual" else ["card", "documenttext"]
    bodies = [json.dumps(fixture[key]).encode() for key in fields]
    bodies.append(json.dumps({"status": 0 if bank == "actual" else 200, "complete": True, "data": [{}]}).encode())
    count = 0

    def get(url):
        nonlocal count
        body = bodies[count]
        count += 1
        response_url = url if count != len(bodies) else url.replace("rdk=", "rdk=1&old=")
        if query_change == "empty_selector" and count == len(bodies):
            response_url = url + "&rdk="
        return body, {"request_url": url, "response_url": response_url}

    with patch.object(base, "_get", side_effect=get):
        result = acquire_bundle(StructureConnector(base), fixture["document_hash"], tmp_path)
    assert result["result"] == "failed"
    assert not (tmp_path / "raw").exists()


def test_same_bytes_across_editions_keep_each_bundle_transport(tmp_path):
    from legal_rag.corpus.official_binding import validate_binding

    fixture = json.loads((FIXTURES / "actual_pravo_59_fz.json").read_bytes())
    first_editions = fixture["redactions"]
    second_editions = copy.deepcopy(first_editions)
    for edition in second_editions["redactions"]:
        if edition.get("actual") is True:
            edition["redid"] += 1
    sidecar = {"status": 0, "complete": True, "data": [{}]}
    bodies = [json.dumps(value).encode() for value in [fixture["card"], first_editions, fixture["redtext"], sidecar,
                                                      fixture["card"], second_editions, fixture["redtext"], sidecar]]
    count = 0
    base = ActualPravoConnector()

    def get(url):
        nonlocal count
        body = bodies[count]
        count += 1
        return body, {"request_url": url, "response_url": url}

    connector = StructureConnector(base)
    with patch.object(base, "_get", side_effect=get):
        a = acquire_bundle(connector, fixture["document_hash"], tmp_path)
        b = acquire_bundle(connector, fixture["document_hash"], tmp_path)
    first = json.loads(Path(a["structure_bundle"]).read_bytes())
    second = json.loads(Path(b["structure_bundle"]).read_bytes())
    assert second["schema_version"] == "official-structure-bundle/2"
    assert first["structure_sha256"] == second["structure_sha256"]
    assert first["text_sha256"] == second["text_sha256"]
    assert first["selector"]["edition_id"] + 1 == second["selector"]["edition_id"]
    assets = [{"sha256": second[key], "source_item": second["source_item"], "source_url": second["source_url"],
               "role": role, "evidence": {"locator": locator}}
              for key, role, locator in [("text_sha256", "consolidated", "$.redtext"),
                                        ("structure_sha256", "official_structure", "$.data")]]
    validate_binding(tmp_path, second, assets)
    legacy = {key: value for key, value in first.items() if key != "transport_evidence"}
    legacy["schema_version"] = "official-structure-bundle/1"
    validate_binding(tmp_path, legacy, assets)
