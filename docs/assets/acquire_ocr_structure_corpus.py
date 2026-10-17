"""Freeze and acquire six official PDF inputs without reading reserved bodies."""

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from generate_m1_inventory import source_document  # noqa: E402
from legal_rag.corpus.compiler import content_hash, json_bytes, load_input, manifest_digest  # noqa: E402
from legal_rag.sources.acquisition import acquire_publication  # noqa: E402
from legal_rag.sources.publication_pravo import PublicationPravoConnector  # noqa: E402

ACTS = [
    {"key": "sp-2.1.3678-20", "eo": "0001202012310005", "number": "44", "date": "2020-12-24", "token": "2.1.3678", "family": "sanitary_rules", "split": "development"},
    {"key": "resolution-1156", "eo": "0001201611170026", "number": "1156", "date": "2016-11-12", "token": "отход", "family": "government_resolution", "split": "development"},
    {"key": "sanpin-2.3-2.4.3590-20", "eo": "0001202011120001", "number": "32", "date": "2020-10-27", "token": "3590", "family": "sanitary_rules", "split": "reserved"},
    {"key": "sp-2.4.3648-20", "eo": "0001202012210122", "number": "28", "date": "2020-09-28", "token": "3648", "family": "sanitary_rules", "split": "reserved"},
    {"key": "resolution-2314", "eo": "0001202012310016", "number": "2314", "date": "2020-12-28", "token": "правил", "family": "government_resolution", "split": "reserved"},
    {"key": "resolution-564", "eo": "0001201606240028", "number": "564", "date": "2016-06-21", "token": "стандарт", "family": "government_resolution", "split": "reserved"},
]
AUTHORIZATION = (
    "The project owner explicitly requested M1-04A implementation and downloading six additional "
    "official acts for local diagnostic OCR/structure experiments on 17 October 2026. "
    "This records that instruction at recording time; it is not a message timestamp or legal admission. "
    "No external document transmission or dated-edition admission is authorized."
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    payload = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable experiment conflict: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(payload)


def read(path):
    return json.loads(path.read_bytes())


def frozen(root):
    freeze = read(root / "split.json")
    assert freeze["split_hash"] == content_hash(freeze["documents"])
    assert len({act["eo"] for act in freeze["documents"]}) == 6
    for family in ("sanitary_rules", "government_resolution"):
        assert sum(a["family"] == family and a["split"] == "reserved" for a in freeze["documents"]) == 2
        assert sum(a["family"] == family and a["split"] == "development" for a in freeze["documents"]) == 1
    for path, digest in freeze["protected_sha256"].items():
        assert sha(PROJECT / path) == digest, path
    for act in freeze["documents"]:
        assert sha(root / act["metadata_path"]) == act["metadata_sha256"]
    return freeze


def select(root):
    if (root / "split.json").exists():
        return frozen(root)
    assert not (root / "archive").exists(), "freeze must precede body acquisition"
    connector = PublicationPravoConnector(timeout=40, request_interval=1)
    documents = []
    for act in ACTS:
        path = root / "metadata" / (act["key"] + ".json")
        if not path.exists():
            body, transport = connector._get(connector.base_url + "/api/Document?eoNumber=" + act["eo"], "application/json")
            write(path, json.loads(body.decode("utf-8-sig")))
            write(path.with_suffix(".transport.json"), transport)
        card = read(path)
        assert card["eoNumber"] == act["eo"] and card["number"] == act["number"]
        assert card["documentDate"][:10] == act["date"] and act["token"] in card["complexName"].lower()
        assert type(card["pagesCount"]) is int and card["pagesCount"] > 0
        documents.append({**act, "declared_identity": card["complexName"], "declared_pages": card["pagesCount"],
            "source_url": connector.base_url + "/document/" + act["eo"],
            "pdf_url": connector.base_url + "/File/Pdf?eoNumber=" + act["eo"],
            "metadata_path": path.relative_to(root).as_posix(), "metadata_sha256": sha(path)})
    paths = [Path(__file__), PROJECT / "docs/assets/generate_m1_inventory.py"]
    paths += [PROJECT / "src/legal_rag/sources" / name for name in ("acquisition.py", "publication_pravo.py", "transport.py")]
    freeze = {"schema_version": "ocr-corpus-split/1", "recorded_at": datetime.now(UTC).isoformat(),
        "selected_before_pdf_download": True, "reserved_bodies_unread": True, "authorization": AUTHORIZATION,
        "development_exposure": "Metadata search for SP 2.1.3678-20 returned automatic text snippets of its approving clauses and approved-text heading. It was assigned to development before this freeze; no reserved-body snippets were read.",
        "documents": documents, "split_hash": content_hash(documents),
        "protected_sha256": {p.relative_to(PROJECT).as_posix(): sha(p) for p in paths}}
    write(root / "split.json", freeze)
    return frozen(root)


def acquire(root, inputs):
    freeze = frozen(root)
    archive = root / "archive"
    connector = PublicationPravoConnector(timeout=60, request_interval=1)
    documents = []
    for act in freeze["documents"]:
        receipt_path = root / "receipts" / (act["key"] + ".json")
        if receipt_path.exists():
            receipt = read(receipt_path)
        else:
            runs = []
            for expected in ("new", "unchanged"):
                result = acquire_publication(connector, act["eo"], archive)
                runs.append(result)
                if result["result"] != expected:
                    write(root / "failures" / (act["key"] + "-" + result["run_id"] + ".json"), {"expected": expected, "runs": runs})
                    raise ValueError(f"unexpected acquisition: {act['key']} {result['result']}")
            receipt = {"split_hash": freeze["split_hash"], "key": act["key"], "runs": runs}
            write(receipt_path, receipt)
        assert [run["result"] for run in receipt["runs"]] == ["new", "unchanged"]
        document = source_document(archive, "publication.pravo.gov.ru:" + act["eo"], "original")
        assert document["declared_identity"] == act["declared_identity"]
        permission_path = archive / "reviews" / (act["key"] + "-permission.json")
        if not permission_path.exists():
            write(permission_path, {"schema_version": "processing-permission/1", "decision": "allowed", "scope": "diagnostic",
                "act_identity": document["declared_identity"], "source_asset_sha256s": [document["primary_sha256"]],
                "authorized_by": "project-owner-current-instruction-recorded-by-agent", "authorized_at": datetime.now(UTC).isoformat(),
                "rights_basis": AUTHORIZATION})
        input_path = inputs / act["key"] / "input.json"
        digest = document["primary_sha256"]
        url = document["assets"][digest]["source_url"]
        manifest = {"schema_version": "corpus-input/1", "kind": "original_amendments",
            "archive_root": os.path.relpath(archive, input_path.parent).replace("\\", "/"),
            "act_identity_claim": {"declared_identity": document["declared_identity"]}, "target_dates": ["2026-10-17"],
            "admission_status": "unresolved", "admission_blockers": ["diagnostic_structure_experiment_only", "dated_edition_not_verified", "legal_admission_not_requested"],
            "unresolved_questions": ["Original publication for structure experiments; amendments and dated applicability are not verified."],
            "processing_permission": {"path": permission_path.relative_to(archive).as_posix(), "sha256": sha(permission_path)},
            "assets": [{"role": "original", "sha256": digest, "source_item": document["source_item"], "source_url": url,
                "declared_identity": document["declared_identity"], "evidence": {"source_asset_sha256": digest, "source_url": url, "locator": "pdf:whole-document"}}]}
        manifest["manifest_hash"] = manifest_digest(manifest)
        write(input_path, manifest)
        normalized, _, _ = load_input(input_path, "2026-10-17")
        assert normalized["manifest_hash"] == manifest["manifest_hash"]
        documents.append({**act, "source_document": document, "receipt": receipt_path.relative_to(root).as_posix(),
            "input_path": input_path.relative_to(PROJECT).as_posix(), "input_sha256": sha(input_path),
            "raw_sha256": digest, "permission_sha256": sha(permission_path), "body_decoded": False})
        print(json.dumps({"key": act["key"], "split": act["split"], "declared_pages": act["declared_pages"], "sha256": digest, "results": [r["result"] for r in receipt["runs"]]}), flush=True)
    write(root / "inventory.json", {"schema_version": "ocr-acquired-corpus/1", "split_hash": freeze["split_hash"],
        "documents": documents, "page_count_basis": "official metadata; reserved PDFs were hashed only, not decoded", "admitted_editions": 0})
    frozen(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("select", "acquire", "verify"))
    parser.add_argument("--root", type=Path, default=PROJECT / "data/m1/experiments/m1-04a-20261017-v1/acquisition")
    parser.add_argument("--inputs", type=Path, default=PROJECT / "data/m1/inputs/m1-04a")
    args = parser.parse_args()
    if args.phase == "select":
        print(json.dumps({"split_hash": select(args.root)["split_hash"]}))
    elif args.phase == "acquire":
        acquire(args.root, args.inputs)
    else:
        inventory = read(args.root / "inventory.json")
        assert frozen(args.root)["split_hash"] == inventory["split_hash"]
        for document in inventory["documents"]:
            path = PROJECT / document["input_path"]
            assert sha(path) == document["input_sha256"]
            load_input(path, "2026-10-17")
        print(json.dumps({"verified": len(inventory["documents"]), "split_hash": inventory["split_hash"]}))
