"""Opt-in official HTML/structure acquisition; frozen M0 adapters stay intact."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

from .acquisition import acquire_actual, acquire_legislation, _write_json_once
from .actual_pravo import ActualPravoConnector, ActualPravoFailure
from .legislation_russia import LegislationRussiaConnector, LegislationRussiaFailure


VERSION = "official-structure-bundle/1"


class StructureConnector:
    def __init__(self, base: ActualPravoConnector | LegislationRussiaConnector):
        self.base = base
        self.source_system = base.source_system
        self.adapter_version = base.adapter_version + "+" + VERSION
        self.bundle = None

    @property
    def metrics(self):
        return self.base.metrics

    def fetch(self, document_hash: str) -> dict:
        self.bundle = None
        fetched = self.base.fetch(document_hash)
        actual = isinstance(self.base, ActualPravoConnector)
        failure = ActualPravoFailure if actual else LegislationRussiaFailure
        support = {a["role"]: a for a in fetched["supporting_assets"]}
        if actual:
            card = json.loads(support["actual_card"]["raw_bytes"])
            editions = json.loads(support["declared_editions"]["raw_bytes"])
            edition = self.base._select_edition(editions, card["docid"], document_hash, fetched["source_url"])
            selector = {"database": "ebpi", "document_id": str(card["docid"]), "edition_id": edition["redid"]}
            evidence = support["declared_editions"]["raw_bytes"]
            url = self.base._api_base + "/getcontent/?" + urlencode({"bpa": "ebpi", "rdk": edition["redid"]})
        else:
            evidence = support["legislation_card"]["raw_bytes"]
            card = json.loads(evidence)
            selector = {"database": card["baseid"], "document_id": card["nd"], "edition_id": card["actualrdk"]}
            url = self.base._api_base + "/document_content?" + urlencode(
                {"nd": card["nd"], "rdk": card["actualrdk"], "bpa": card["baseid"]})
        raw, transport = self.base._get(url)
        response = self.base._parse_json(raw, "invalid_structure", url)
        if (type(response.get("status")) is not int or response["status"] != (0 if actual else 200)
                or response.get("error") is not None or not isinstance(response.get("data"), list)
                or not response["data"] or actual and response.get("complete") is not True):
            raise failure("invalid_structure", "incomplete or invalid official structure response",
                          retryable=False, source_url=url)
        fetched["supporting_assets"].append({"role": "official_structure", "raw_bytes": raw,
            "media_type": "application/json", "source_url": fetched["source_url"], "transport_metadata": transport})
        fetched["adapter_version"] = self.adapter_version
        self.bundle = {"schema_version": VERSION, "source_system": self.source_system,
            "source_item": f"{self.source_system}:{document_hash}", "document_hash": document_hash,
            "source_url": fetched["source_url"], "selector": selector,
            "text_sha256": hashlib.sha256(fetched["raw_bytes"]).hexdigest(),
            "structure_sha256": hashlib.sha256(raw).hexdigest(),
            "edition_evidence_sha256": hashlib.sha256(evidence).hexdigest()}
        return fetched


def acquire_bundle(connector: StructureConnector, document_hash: str, data_dir: Path) -> dict:
    acquire = acquire_actual if isinstance(connector.base, ActualPravoConnector) else acquire_legislation
    result = acquire(connector, document_hash, Path(data_dir))
    if result["result"] != "failed":
        payload = json.dumps(connector.bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        path = Path(data_dir) / "structure_bundles" / (hashlib.sha256(payload).hexdigest() + ".json")
        if path.exists():
            if json.loads(path.read_bytes()) != connector.bundle:
                raise ValueError("immutable structure bundle conflict")
        else:
            _write_json_once(path, connector.bundle)
        result["structure_bundle"] = str(path.resolve())
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Acquire same-edition HTML and official legal structure")
    parser.add_argument("--source", choices=("actual", "ips"), required=True)
    parser.add_argument("--document-hash", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    base = ActualPravoConnector if args.source == "actual" else LegislationRussiaConnector
    result = acquire_bundle(StructureConnector(base(request_interval=1.0)), args.document_hash, args.data_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 2 if result["result"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
