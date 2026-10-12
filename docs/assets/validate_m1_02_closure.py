"""Validate the retained routing result without granting legal admission."""
import argparse
import hashlib
import json
from pathlib import Path

from legal_rag.corpus.compiler import content_hash

ROOT = Path(__file__).resolve().parents[2]
ACTS = {"housing-code", "government-decree-354", "government-decree-491",
        "federal-law-59", "sanpin-2.1.3684-21"}
DATES = {"2025-01-01", "2026-10-01"}


def validate(path: Path, project: Path = ROOT) -> dict:
    result = json.loads(path.read_text("utf-8"))
    if result["schema"] != "m1-02-route-closure/1" or result["edition_admission"] is not False:
        raise ValueError("closure must remain a routing result without edition admission")
    if result["content_hash"] != content_hash({k: v for k, v in result.items() if k != "content_hash"}):
        raise ValueError("closure content hash mismatch")
    rows = result["rows"]
    expected = {(act, date) for act in ACTS for date in DATES}
    if len(rows) != 10 or {(row["act_id"], row["target_date"]) for row in rows} != expected:
        raise ValueError("closure requires exactly ten distinct act/date rows")
    for row in rows:
        if row["edition_admission"] is not False or not row["blockers"] or not row["next_slice"]:
            raise ValueError("unfinished editions must retain actionable blockers")
        if not row["source_sha256s"] or row["route"] not in {
            "historical_official_candidate", "official_consolidated", "original_amendments"
        }:
            raise ValueError("missing route evidence")
        if row["act_id"] == "sanpin-2.1.3684-21" and row["route"] != "original_amendments":
            raise ValueError("SanPiN must retain reconstruction for both dates")
        if row["target_date"] == "2025-01-01" and row["act_id"] != "sanpin-2.1.3684-21":
            if row["route"] != "historical_official_candidate":
                raise ValueError("later consolidated text cannot replace a historical input")
    files = result["evidence_files"]
    if not files or len({entry["path"] for entry in files}) != len(files):
        raise ValueError("evidence bindings must be nonempty and unique")
    hashes = set()
    for entry in files:
        source = (project / entry["path"]).resolve()
        if not source.is_relative_to(project.resolve()):
            raise ValueError("evidence path escapes the project")
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("evidence hash mismatch: " + entry["path"])
        hashes.add(entry["sha256"])
    if any(not set(row["source_sha256s"]) <= hashes for row in rows):
        raise ValueError("route references unbound source bytes")
    bindings = {entry["path"]: entry["sha256"] for entry in files}
    for row in rows:
        reference = row["processing_permission"]
        if bindings.get(reference["path"]) != reference["sha256"]:
            raise ValueError("processing permission is not hash-bound")
        permission = json.loads((project / reference["path"]).read_text("utf-8"))
        if (permission["schema_version"] != "processing-permission/1"
                or permission["decision"] != "allowed" or permission["scope"] != "diagnostic"
                or permission["act_identity"] != row["act_identity"]
                or permission["source_asset_sha256s"] != sorted(row["source_sha256s"])):
            raise ValueError("processing permission scope mismatch")
    review_path = result["human_decision_path"]
    if review_path not in {entry["path"] for entry in files}:
        raise ValueError("human decision is not hash-bound")
    review = json.loads((project / review_path).read_text("utf-8"))
    if (review["schema"] != "m1-02-focused-human-review/2"
            or review["question"] != "59-ks19p-after-80"
            or review["role"] != "Legal Reviewer" or review["decision"] != "confirmed"
            or set(review["targets"]) != DATES or review["edition_admission"] is not False
            or review["packet_hash"] != result["review_packet_hash"]):
        raise ValueError("human decision scope does not match the routing result")
    return {"schema": result["schema"], "rows": 10, "evidence_files_checked": len(files),
            "content_hash": result["content_hash"], "edition_admission": False,
            "status": "verified_routes_with_admission_blockers"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, nargs="?", default=ROOT / "data/m1/inputs/m1-02-completion/closure.json")
    args = parser.parse_args()
    print(json.dumps(validate(args.path), sort_keys=True))


if __name__ == "__main__":
    main()
