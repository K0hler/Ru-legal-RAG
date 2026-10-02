"""Prepare M1-02's ten-row review request from retained official source assets."""

import argparse
import hashlib
import json
from pathlib import Path

from legal_rag.corpus.compiler import _asset, _read, _write_once, content_hash, json_bytes
from legal_rag.sources.pilot import PILOT_ACTS


ROOT = Path(__file__).resolve().parents[2]
DATES = ("2025-01-01", "2026-10-01")
REVIEWER = "legal-reviewer-owner"
FINDINGS = {
    "housing-code": ("unresolved", "Amendment chain and effective dates are unverified."),
    "government-decree-354": (
        "rejected", "The 2026-07-27 label includes a territorial overlay; it is not the general text's revision date."
    ),
    "government-decree-491": (
        "rejected", "The 2025-09-01 snapshot predates Resolution No. 1242; its stale M0 candidate remains rejected."
    ),
    "federal-law-59": (
        "unresolved", "No. 48-FZ special application and Constitutional Court No. 19-P effects need separate decisions."
    ),
    "sanpin-2.1.3684-21": ("unresolved", "The original plus nine located amendments is not an admitted edition."),
}
QUESTIONS = {
    "housing-code": "Verify the full code, amendment completeness, future-effective provisions and both dates.",
    "government-decree-354": "Obtain dated text bases; separate the approving act, Rules, annexes and No. 931 territory conditions.",
    "government-decree-491": "Obtain dated text bases; reconcile No. 1242 with both approved texts and its commencement clause.",
    "federal-law-59": "Owner and Legal Reviewer must explicitly keep or resolve the No. 19-P/No. 48-FZ admission blocker; diagnostic permission does not resolve it.",
    "sanpin-2.1.3684-21": "Verify the nine leads against the official chain and a search for omissions; review No. 11 (published before 2025) and No. 25 (published before the control date) commencement separately.",
}


def source_document(archive: Path, source_item: str, role: str) -> dict:
    """Read metadata and hash raw bytes; do not extract legal text."""
    item_path = archive / "items" / (hashlib.sha256(source_item.encode()).hexdigest() + ".json")
    item = _read(item_path)
    if item.get("source_item") != source_item:
        raise ValueError("source item identity mismatch")
    primary = item["latest_successful_asset"]
    if primary not in item["asset_sha256s"]:
        raise ValueError("primary asset missing from source history")
    allowed_urls = {item["source_url"]}
    if source_item.startswith("publication.pravo.gov.ru:"):
        allowed_urls.add("http://publication.pravo.gov.ru/api/Document?eoNumber=" + source_item.split(":", 1)[1])
    assets = {}
    for digest in sorted(set(item["asset_sha256s"])):
        metadata, _ = _asset(archive, digest)
        if metadata["source_url"] not in allowed_urls:
            raise ValueError("source URL mismatch")
        assets[digest] = metadata
    supporting = dict(item.get("supporting_assets", {}))
    if item.get("declared_publication_asset"):
        supporting["declared_publication"] = item["declared_publication_asset"]
    if not set(supporting.values()) <= assets.keys():
        raise ValueError("supporting asset missing from source history")
    history = []
    if "declared_editions" in supporting:
        editions = _read(archive / assets[supporting["declared_editions"]]["archive_key"])
        history = [{"date": entry["reddate"], "label": entry["redcaption"],
                    "source_claim_only": True} for entry in editions["redactions"]]
    return {
        "source_item": source_item, "role": role, "source_url": (
            item.get("declared_publication", {}).get("official_publication_url", item["source_url"])
            if item.get("declared_publication") else item["source_url"]
        ),
        "declared_identity": item["declared_act_identity"], "primary_sha256": primary,
        "assets": assets, "supporting_assets": supporting, "declared_history": history,
        "edition_claim": item.get("edition_claim"), "publication_claim": item.get("declared_publication"),
        "source_status": item.get("candidate_status", "unreviewed"),
        "source_unresolved_items": item.get("unresolved_items", []),
    }


def build_inventory(archive: Path, search: dict) -> dict:
    if search.get("status") != "incomplete" or not search.get("checks"):
        raise ValueError("M1-02 search record must retain incomplete coverage and explicit checks")
    documents, rows, permissions = {}, [], {}
    systems = {"actual": "actual.pravo.gov.ru", "legislation": "pravo.gov.ru/legislation-russia",
               "publication": "publication.pravo.gov.ru"}
    for act in PILOT_ACTS:
        act_id = act["act_id"]
        sources, missing = [], []
        specifications = list(act["items"])
        if act_id == "government-decree-491":
            specifications.append({"connector": "publication", "external_id": "0001202609260011",
                                   "role": "official_amendment"})
        for item in specifications:
            source = systems[item["connector"]] + ":" + item["external_id"]
            path = archive / "items" / (hashlib.sha256(source.encode()).hexdigest() + ".json")
            if not path.exists():
                missing.append(source)
                continue
            documents[source] = source_document(archive, source, item["role"])
            sources.append(source)
        permission = {
            "schema_version": "processing-permission/1", "act_identity": (
                documents[sources[0]]["declared_identity"] if sources else act["label"]
            ), "source_asset_sha256s": sorted(documents[source]["primary_sha256"] for source in sources),
            "scope": "diagnostic", "decision": "pending", "authorized_by": None, "authorized_at": None,
            "rights_basis": "Proposed: retained official legal texts under the approved bounded-pilot policy; no bulk access or commercial editorial text.",
        }
        permissions[act_id] = permission
        for target in DATES:
            sanpin = act_id == "sanpin-2.1.3684-21"
            historical = target == DATES[0]
            route = "original_amendments" if sanpin else "unresolved" if historical else "official_consolidated"
            blockers = ["processing_permission_pending", "human_inventory_review_pending",
                        "amendment_completeness_unverified", "date_and_territory_evidence_unverified"]
            if missing:
                blockers.append("required_source_assets_missing")
            if historical and not sanpin:
                blockers.append("historical_text_not_acquired_or_justified")
            if act_id in {"government-decree-354", "government-decree-491"}:
                blockers.append("retained_rejected_candidate_not_a_verified_date_basis")
            if act_id == "federal-law-59":
                blockers.append("case_law_sensitive_effect_unresolved")
            if sanpin:
                blockers.append("amendment_operations_and_commencement_unreviewed")
            rows.append({
                "row_id": act_id + ":" + target, "act_id": act_id, "label": act["label"],
                "target_date": target, "route": route, "status": "blocked", "source_documents": sources,
                "selected_date_basis": None, "missing_source_items": missing,
                "processing_permission": {"path": "permissions/" + act_id + ".json", "status": "pending"},
                "legal_admission": "unresolved", "legal_reviewer": REVIEWER,
                "m0_decision": {"status": FINDINGS[act_id][0], "rationale": FINDINGS[act_id][1],
                                "record": "docs/M0_10_LEGAL_REVIEW.md"},
                "required_legal_evidence": QUESTIONS[act_id], "blockers": blockers,
                "historical_rule": "Later snapshots are diagnostic leads only; never reverse them by guessed wording. Publication dates alone do not justify operation inclusion/exclusion.",
            })
    inventory = {
        "schema_version": "m1-input-inventory/1", "archive_root": str(archive.resolve()),
        "target_dates": list(DATES), "documents": documents, "rows": rows,
        "permission_requests": permissions, "search_coverage": search,
        "human_review": {"status": "pending", "role": "Legal Reviewer", "reviewer": REVIEWER,
                         "signed_at": None, "inventory_hash": None},
        "summary": {"rows": 10, "blocked": 10, "admitted": 0, "m1_02_status": "awaiting_human_review"},
    }
    inventory["inventory_hash"] = content_hash({key: value for key, value in inventory.items()
                                               if key != "archive_root"})
    return inventory


def review_markdown(inventory: dict) -> str:
    lines = ["# M1-02 input inventory: human review request", "",
             "Engineering inventory only. All ten date checks remain blocked. No permission or legal admission is signed.",
             "", "Inventory content hash: `" + inventory["inventory_hash"] + "`.", "",
             "| Act | Target | Route | M0 decision | Required human evidence |",
             "|---|---|---|---|---|"]
    for row in inventory["rows"]:
        lines.append(f"| {row['label']} | {row['target_date']} | {row['route']} | {row['m0_decision']['status']} | {row['required_legal_evidence']} |")
    lines += ["", "## Retained official documents", ""]
    for document in inventory["documents"].values():
        lines += [f"- [{document['declared_identity'].replace(chr(10), ' ')}]({document['source_url']})",
                  f"  - Raw SHA-256: `{document['primary_sha256']}`; role: `{document['role']}`."]
        if document["declared_history"]:
            lines.append("  - Advertised history (metadata only; historical text not acquired): " +
                         "; ".join(entry["date"] + ": " + entry["label"] for entry in document["declared_history"]))
    lines += ["", "## Decisions requested from the owner and human Legal Reviewer", "",
              "1. Sign acceptance of this inventory with its hash, reviewer/role, UTC timestamp and rationale. Confirm or correct every row's route, unresolved completeness, date/territory evidence and missing materials. Acceptance of a blocked row does not admit an edition.",
              "2. Separately authorize or refuse diagnostic extraction of each act's exact listed raw hashes. The five permission templates are pending; no signature/time is generated. Bulk access remains unresolved.",
              "3. Explicitly keep the 59-FZ admission blocker until No. 48-FZ special application and Constitutional Court No. 19-P (18 July 2012, Articles 1-3) are evidenced and reviewed, or supply an evidence-bound alternative decision without reducing the full-act scope. No court subsystem is introduced.",
              "4. For SanPiN, check the nine located amendments for omissions and give separate dispositions for both dates. Neither the known-ID replay nor a search returning zero proves completeness. No. 11's 2024 publication and No. 25's September 2026 publication are not effective-date decisions.",
              "", "Search checks and remaining coverage gaps are retained in `inventory.json`. No historical source adapter or M0 contract has changed.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ROOT / "data/m1-02-sources")
    parser.add_argument("--search-record", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/m1/inputs/m1-02")
    args = parser.parse_args(argv)
    if args.output_dir.resolve().is_relative_to(args.archive.resolve()):
        raise ValueError("inventory output must be separate from the source archive")
    inventory = build_inventory(args.archive, _read(args.search_record))
    files = {args.output_dir / "inventory.json": json_bytes(inventory),
             args.output_dir / "review.md": review_markdown(inventory).encode("utf-8")}
    files.update({args.output_dir / "permissions" / (key + ".json"): json_bytes(value)
                  for key, value in inventory["permission_requests"].items()})
    for path, payload in files.items():
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"refusing to replace an existing inventory/review record: {path}")
    result = "unchanged" if all(path.exists() for path in files) else "new"
    for path, payload in files.items():
        if not path.exists():
            _write_once(path, payload)
    print(json.dumps({"result": result, "inventory_hash": inventory["inventory_hash"],
                      **inventory["summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
