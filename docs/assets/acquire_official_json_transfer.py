"""Bounded six-act diagnostic acquisition using unchanged M0 transport/validators."""

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import Request

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from legal_rag.corpus.compiler import json_bytes, manifest_digest  # noqa: E402
from legal_rag.sources.actual_pravo import ActualPravoConnector  # noqa: E402
from legal_rag.sources.legislation_russia import LegislationRussiaConnector, urlopen  # noqa: E402
from legal_rag.sources.structure_bundle import StructureConnector, acquire_bundle  # noqa: E402

ACTS = [
    {"key": "real-estate", "number": "218-ФЗ", "date": "13.07.2015", "family": "federal_law", "source": "actual"},
    {"key": "enforcement", "number": "229-ФЗ", "date": "02.10.2007", "family": "federal_law", "source": "actual"},
    {"key": "criminal", "number": "63-ФЗ", "date": "13.06.1996", "family": "code", "source": "actual"},
    {"key": "labour", "number": "197-ФЗ", "date": "30.12.2001", "family": "code", "source": "actual"},
    {"key": "utility-norms", "number": "306", "date": "23.05.2006", "family": "government_resolution", "source": "ips"},
    {"key": "minimum-services", "number": "290", "date": "03.04.2013", "family": "government_resolution", "source": "ips"},
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def retain(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == payload, f"immutable conflict: {path}"
    else:
        with path.open("xb") as stream:
            stream.write(payload)


def write(path, value):
    retain(path, json_bytes(value))


def verify(root):
    freeze = json.loads((root / "freeze.json").read_bytes())
    for path, expected in freeze["protected_sha256"].items():
        assert sha(PROJECT / path) == expected, path
    return freeze


def initialize(root):
    root.mkdir(parents=True, exist_ok=False)
    paths = list((PROJECT / "src/legal_rag").rglob("*.py"))
    paths.append(Path(__file__))
    old = json.loads((PROJECT / "data/m1/experiments/official-structure-20261015-v1/preflight.json").read_bytes())
    paths += [PROJECT / p for p in old["protected_files_sha256"]]
    paths += [p for p in (PROJECT / "data/m1/pilot_runs/independent-structure-audit-20261015-v2").rglob("*") if p.is_file()]
    write(root / "freeze.json", {"schema_version": "official-json-transfer-freeze/1", "documents": ACTS,
        "frozen_at": datetime.now(UTC).isoformat(), "selected_before_bodies": True,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True).strip(),
        "profile_version": "official-structure/4", "scanner_version": "html-structure-audit/2",
        "protected_sha256": {p.relative_to(PROJECT).as_posix(): sha(p) for p in sorted(set(paths))},
        "authorization": "Owner requested necessary documents through M0 and the new official-JSON route; diagnostic only, not legal admission."})


def discover(root):
    freeze = verify(root)
    actual = ActualPravoConnector(timeout=25, request_interval=1)
    ips = LegislationRussiaConnector(timeout=25, request_interval=1)
    for act in freeze["documents"]:
        dest = root / "discovery" / act["key"]
        try:
            if act["source"] == "actual":
                iso = "".join(reversed(act["date"].split(".")))
                attrs = [{"AttrId": 6, "AttrMode": 0, "Words": [act["number"]]},
                    {"AttrId": 5, "AttrMode": 0, "DateFrom": iso, "DateTo": iso},
                    {"AttrId": 999, "AttrMode": 1, "Words": [10, "position", "20220701", 0, 1]}]
                url = actual._api_base + "/attrsearch/?" + urlencode({"bpa": "ebpi", "q": json.dumps(attrs, separators=(",", ":"))})
                write(dest / "request.json", {"method": "GET", "url": url})
                body, transport = actual._get(url)
            else:
                url = ips._api_base + "/search.json"
                params = {"searchType": "attrSearch", "number_eq": act["number"], "date": act["date"], "page": 1, "limit": 10, "sort": "-date"}
                write(dest / "request.json", {"method": "POST", "url": url, "params": params})
                ips._meter.before_request()
                request = Request(url, data=urlencode(params).encode(), headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
                with urlopen(request, timeout=25) as response:
                    body = response.read()
                    transport = {"request_url": url, "response_url": response.geturl(), "http_status": response.status}
                ips._meter.record_response(body)
            retain(dest / "response.json", body)
            write(dest / "transport.json", transport)
            docs = json.loads(body)["docs"]
            assert len(docs) == 1, f"expected one source identity, got {len(docs)}"
            md = docs[0]
            if act["source"] == "actual":
                assert md["docpass0number"] == act["number"] and md["docpass0date"] == iso
            else:
                assert md["docdate"] == act["date"] and md["adoption"].endswith("№ " + act["number"])
            write(dest / "selected.json", md)
            print(act["key"], "FOUND", flush=True)
        except Exception as error:
            write(dest / "failure.json", {"type": type(error).__name__, "message": str(error)})
            print(act["key"], "DISCOVERY FAILED", str(error), flush=True)
    verify(root)


def diagnostic_fetch(base, act, md, document_hash):
    """Explicit selected cohort only; production pilot allowlists are unchanged."""
    actual = isinstance(base, ActualPravoConnector)
    assert document_hash == md["dochash" if actual else "hash"]
    base._meter.reset()
    if actual:
        card_url = base._url("card/", {"hash": document_hash})
        cb, ct = base._get(card_url)
        card = json.loads(cb)
        base._validate_card(card, document_hash, {"adoption_type": "Кодекс" if act["family"] == "code" else "Федеральный закон",
            "adoption_date": act["date"], "adoption_number": act["number"], "title": md["docnames"]}, card_url)
        rb, rt = base._get(base._url("redactions/", {"hash": document_hash, "ttl": 4}))
        edition = base._select_edition(json.loads(rb), card["docid"], document_hash, rt["request_url"])
        body, transport = base._get(base._api_base + "/redtext?" + urlencode({"bpa": "ebpi", "t": edition["redid"], "ttl": 0}))
        value = json.loads(body)
        assert value.get("error") is None and isinstance(value.get("redtext"), str) and "<html" in value["redtext"].lower()
        source_url = base.base_url + "/list.html#hash=" + document_hash + "&bpa=ebpi"
        prefix = "Кодекс Российской Федерации" if act["family"] == "code" else "Федеральный закон"
        claim = f'{prefix} от {act["date"]} № {act["number"]} "{card["docname"]}"'
        support = [("actual_card", cb, ct), ("declared_editions", rb, rt)]
        label = edition["redcaption"]
    else:
        card_url = base._api_base + "/document_card.json?" + urlencode({"hash": document_hash})
        cb, ct = base._get(card_url)
        card = json.loads(cb)
        edition = base._validate_card(card, document_hash, {"adoption": md["adoption"], "title": md["name"]}, card_url)
        body, transport = base._get(base._api_base + "/documenttext?" + urlencode({"nd": card["nd"], "rdk": edition["id"], "bpa": card["baseid"]}))
        base._validate_text(json.loads(body), card, edition, transport["request_url"])
        source_url = base.base_url + "/search/" + document_hash
        claim, label = card["adoption"] + ' "' + card["name"] + '"', edition["redname"]
        support = [("legislation_card", cb, ct)]
    return {"adapter_version": "diagnostic-selected-cohort/1", "captured_at": datetime.now(UTC).isoformat(),
        "declared_act_identity": claim, "declared_edition_label": label, "declared_publication": None,
        "external_id": document_hash, "request_cursor": document_hash, "source_system": base.source_system,
        "source_url": source_url, "media_type": "application/json", "raw_bytes": body,
        "raw_asset_role": "actual_redtext" if actual else "legislation_text", "transport_metadata": transport,
        "rights_status": "Owner-authorized bounded official-act diagnostic; no legal admission or bulk synchronization.",
        "supporting_assets": [{"role": role, "raw_bytes": raw, "media_type": "application/json", "source_url": source_url,
            "transport_metadata": capture} for role, raw, capture in support],
        "unresolved_items": [{"reason": "temporal_coverage_unknown"}]}


class DiagnosticActual(ActualPravoConnector):
    def fetch(self, document_hash):
        return diagnostic_fetch(self, self.act, self.md, document_hash)


class DiagnosticIPS(LegislationRussiaConnector):
    def fetch(self, document_hash):
        return diagnostic_fetch(self, self.act, self.md, document_hash)


def acquire(root):
    freeze = verify(root)
    bases = {"actual": DiagnosticActual(timeout=25, request_interval=1), "ips": DiagnosticIPS(timeout=25, request_interval=1)}
    for act in freeze["documents"]:
        try:
            base = bases[act["source"]]
            base.act, base.md = act, json.loads((root / "discovery" / act["key"] / "selected.json").read_bytes())
            archive = root / act["key"] / "archive"
            result = acquire_bundle(StructureConnector(base), base.md["dochash" if act["source"] == "actual" else "hash"], archive)
            write(root / act["key"] / "acquisition.json", result)
            assert result["result"] != "failed", result
            bundle_path = Path(result["structure_bundle"])
            bundle = json.loads(bundle_path.read_bytes())
            item_key = hashlib.sha256(bundle["source_item"].encode()).hexdigest()
            item = json.loads((archive / "items" / (item_key + ".json")).read_bytes())
            claim = item["declared_act_identity"]
            permission = {"schema_version": "processing-permission/1", "decision": "allowed", "scope": "diagnostic", "act_identity": claim,
                "source_asset_sha256s": [bundle["text_sha256"], bundle["structure_sha256"]], "authorized_by": "project-owner-current-instruction-recorded-by-agent",
                "authorized_at": datetime.now(UTC).isoformat(), "rights_basis": freeze["authorization"]}
            pp = archive / "reviews/permission.json"
            write(pp, permission)
            manifest = {"schema_version": "corpus-input/2", "kind": "official_consolidated", "archive_root": ".",
                "act_identity_claim": {"declared_identity": claim}, "target_dates": ["2026-10-16"], "admission_status": "unresolved",
                "admission_blockers": ["transfer_diagnostic_only", "temporal_coverage_unknown", "legal_admission_not_requested"],
                "unresolved_questions": ["Source snapshot for syntax transfer only; no dated applicability decision."],
                "processing_permission": {"path": "reviews/permission.json", "sha256": sha(pp)},
                "structure_bundle": {"path": bundle_path.relative_to(archive).as_posix(), "sha256": sha(bundle_path)},
                "assets": [{"role": role, "sha256": bundle[field], "source_item": bundle["source_item"], "source_url": bundle["source_url"],
                    "declared_identity": claim, "evidence": {"source_asset_sha256": bundle[field], "source_url": bundle["source_url"], "locator": locator}}
                    for role, field, locator in [("consolidated", "text_sha256", "$.redtext" if act["source"] == "actual" else "$.doctext"),
                                                 ("official_structure", "structure_sha256", "$.data")]]}
            manifest["manifest_hash"] = manifest_digest(manifest)
            write(archive / "input.json", manifest)
            print(act["key"], "ACQUIRED", bundle["text_sha256"], flush=True)
        except Exception as error:
            write(root / act["key"] / "failure.json", {"stage": "acquisition", "type": type(error).__name__, "message": str(error)})
            print(act["key"], "ACQUISITION FAILED", str(error), flush=True)
    verify(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("init", "discover", "acquire"))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    {"init": initialize, "discover": discover, "acquire": acquire}[args.phase](args.root.resolve())
