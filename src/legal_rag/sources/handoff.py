from datetime import datetime
import hashlib
from pathlib import Path

from .acquisition import _read_json, _write_json_once
from .relations import _stable_id


def build_edition_candidate(
    reconciliation_path: Path,
    data_dir: Path,
    review_decision_path: Path | None = None,
) -> dict[str, str]:
    data_dir = Path(data_dir)
    reconciliation = _read_json(Path(reconciliation_path))
    reconciliation_id = _text(reconciliation, "reconciliation_id")
    act_source_item = _text(reconciliation, "act_source_item")
    item_ids = _ids(reconciliation, "item_source_ids")
    relation_ids = _ids(reconciliation, "relation_ids")
    exception_ids = _ids(reconciliation, "exception_ids")

    items = {
        source_item: _record(
            data_dir / "items" / f"{_stable_id(source_item)}.json",
            "source_item",
            source_item,
        )
        for source_item in item_ids
    }
    if act_source_item not in items:
        raise ValueError("reconciliation act_source_item is missing")

    relations = [
        _record(
            data_dir / "relations" / f"{relation_id}.json",
            "relation_id",
            relation_id,
        )
        for relation_id in relation_ids
    ]
    for relation in relations:
        if (
            relation.get("from_source_item") not in items
            or relation.get("to_source_item") not in items
        ):
            raise ValueError("source relation references an item outside the reconciliation")

    consolidates = [
        relation
        for relation in relations
        if relation.get("relation_type") == "consolidates"
        and relation.get("to_source_item") == act_source_item
        and items[relation.get("from_source_item", "")].get("item_kind")
        == "edition_candidate"
    ]
    candidate_ids = {relation["from_source_item"] for relation in consolidates}
    if len(candidate_ids) != 1:
        raise ValueError("reconciliation must contain exactly one consolidated edition candidate")
    candidate_source_item = candidate_ids.pop()
    candidate_item = items[candidate_source_item]
    claim_relation_ids = sorted(relation["relation_id"] for relation in consolidates)
    claim_asset_sha256s = sorted(
        {
            relation["evidence_reference"]["source_asset_sha256"]
            for relation in consolidates
            if relation.get("evidence_reference", {}).get("source_asset_sha256")
        }
    )
    if not claim_asset_sha256s:
        raise ValueError("edition candidate relation must reference a source asset")

    edition_claim = candidate_item.get("edition_claim")
    temporal = candidate_item.get("temporal_coverage")
    if not isinstance(edition_claim, dict) or not isinstance(temporal, dict):
        raise ValueError("edition candidate claims are incomplete")
    edition_asset = _text(edition_claim, "source_asset_sha256")
    snapshot_asset = _text(candidate_item, "latest_successful_asset")

    unresolved = [
        {
            "diagnostic_message": _text(item, "diagnostic_message"),
            "reason": _text(item, "reason"),
            "source_asset_sha256s": [_text(item, "source_asset_sha256")],
            "source_relation_ids": claim_relation_ids,
        }
        for item in candidate_item.get("unresolved_items", [])
    ]
    for exception_id in exception_ids:
        exception = _record(
            data_dir / "exceptions" / f"{exception_id}.json",
            "exception_id",
            exception_id,
        )
        evidence = exception.get("evidence_reference", {})
        exception_asset = (
            [_text(evidence, "source_asset_sha256")]
            if isinstance(evidence, dict) and evidence.get("source_asset_sha256")
            else []
        )
        unresolved.append(
            {
                "diagnostic_message": _text(exception, "diagnostic_message"),
                "exception_id": exception_id,
                "reason": _text(exception, "reason"),
                "source_asset_sha256s": exception_asset,
                "source_relation_ids": [],
            }
        )
    unresolved.sort(key=_stable_id)

    asset_ids = {
        sha256
        for item in items.values()
        for sha256 in _ids(item, "asset_sha256s", required=False)
    }
    asset_ids.update({edition_asset, snapshot_asset, *claim_asset_sha256s})
    asset_ids.update(
        relation["evidence_reference"]["source_asset_sha256"]
        for relation in relations
        if relation.get("evidence_reference", {}).get("source_asset_sha256")
    )
    asset_ids.update(
        sha256
        for item in unresolved
        for sha256 in item["source_asset_sha256s"]
    )
    assets = [_asset(data_dir, sha256) for sha256 in sorted(asset_ids)]
    review_status, review_decision = _review(
        review_decision_path,
        candidate_source_item,
        asset_ids,
        set(relation_ids),
    )

    payload = {
        "act_identity_claim": {
            "declared_identity": _text(items[act_source_item], "declared_act_identity"),
            "source_asset_sha256s": claim_asset_sha256s,
            "source_item": act_source_item,
            "source_relation_ids": claim_relation_ids,
        },
        "edition_claim": {
            "captured_at": _text(candidate_item, "captured_at"),
            "claimed_edition_date": _text(edition_claim, "claimed_edition_date"),
            "claimed_edition_label": _text(edition_claim, "claimed_edition_label"),
            "snapshot_asset_sha256": snapshot_asset,
            "source_asset_sha256s": sorted(
                {edition_asset, snapshot_asset, *claim_asset_sha256s}
            ),
            "source_item": candidate_source_item,
            "source_relation_ids": claim_relation_ids,
        },
        "reconciliation_id": reconciliation_id,
        "review_decision": review_decision,
        "review_status": review_status,
        "schema_version": "edition-candidate/1",
        "source_evidence": {
            "assets": assets,
            "exceptions": exception_ids,
            "items": sorted(
                (_public_item(item) for item in items.values()),
                key=lambda item: item["source_item"],
            ),
            "relations": sorted(
                (_public_relation(relation) for relation in relations),
                key=lambda relation: relation["relation_id"],
            ),
        },
        "temporal_evidence": {
            "source_asset_sha256s": sorted(
                {
                    *claim_asset_sha256s,
                    *(
                        sha256
                        for item in unresolved
                        for sha256 in item["source_asset_sha256s"]
                    ),
                }
            ),
            "source_relation_ids": claim_relation_ids,
            "status": _text(temporal, "status"),
            "valid_from": temporal.get("valid_from"),
            "valid_to": temporal.get("valid_to"),
        },
        "unresolved_items": unresolved,
    }
    candidate_id = _stable_id(payload)
    candidate = {"candidate_id": candidate_id, **payload}
    candidate_path = data_dir / "candidates" / f"{candidate_id}.json"
    result = "unchanged" if candidate_path.exists() else "new"
    if candidate_path.exists() and _read_json(candidate_path) != candidate:
        raise ValueError(f"candidate record conflict: {candidate_id}")
    _write_json_once(candidate_path, candidate)
    return {
        "candidate": str(candidate_path.resolve()),
        "candidate_id": candidate_id,
        "result": result,
    }


def _review(
    path: Path | None,
    candidate_source_item: str,
    asset_ids: set[str],
    relation_ids: set[str],
) -> tuple[str, dict[str, object] | None]:
    if path is None:
        return "unreviewed", None
    decision = _read_json(Path(path))
    status = _text(decision, "decision")
    if status not in {"reviewed", "rejected"}:
        raise ValueError("review decision must be reviewed or rejected")
    if _text(decision, "reviewer_role") != "Legal Reviewer":
        raise ValueError("reviewer_role must be Legal Reviewer")
    if _text(decision, "reviewed_scope") != candidate_source_item:
        raise ValueError("reviewed_scope must identify the edition candidate source item")
    decided_at = _text(decision, "decided_at")
    try:
        if datetime.fromisoformat(decided_at.replace("Z", "+00:00")).utcoffset() is None:
            raise ValueError
    except ValueError as error:
        raise ValueError("decided_at must be an ISO timestamp with a UTC offset") from error
    references = decision.get("evidence_references")
    if not isinstance(references, list) or not references:
        raise ValueError("evidence_references must be a non-empty list")
    evidence = []
    for reference in references:
        asset_id = _text(reference, "source_asset_sha256")
        relation_id = _text(reference, "source_relation_id")
        if asset_id not in asset_ids or relation_id not in relation_ids:
            raise ValueError("review decision references evidence outside the candidate")
        evidence.append(
            {"source_asset_sha256": asset_id, "source_relation_id": relation_id}
        )
    normalized = {
        "decided_at": decided_at,
        "decision": status,
        "evidence_references": sorted(
            evidence,
            key=lambda item: (item["source_asset_sha256"], item["source_relation_id"]),
        ),
        "rationale": _text(decision, "rationale"),
        "reviewed_scope": candidate_source_item,
        "reviewer_id": _text(decision, "reviewer_id"),
        "reviewer_role": "Legal Reviewer",
    }
    normalized["decision_id"] = _stable_id(normalized)
    return status, normalized


def _asset(data_dir: Path, sha256: str) -> dict[str, object]:
    asset = _record(data_dir / "assets" / f"{sha256}.json", "sha256", sha256)
    raw_path = data_dir / "raw" / sha256
    if (
        not raw_path.is_file()
        or asset.get("archive_key") != f"raw/{sha256}"
        or asset.get("byte_length") != raw_path.stat().st_size
        or hashlib.sha256(raw_path.read_bytes()).hexdigest() != sha256
    ):
        raise ValueError(f"invalid source asset: {sha256}")
    return {
        field: asset[field]
        for field in (
            "archive_key",
            "byte_length",
            "captured_at",
            "media_type",
            "rights_status",
            "sha256",
            "source_url",
        )
    }


def _public_item(item: dict[str, object]) -> dict[str, str]:
    fields = (
        "declared_act_identity",
        "item_kind",
        "label",
        "source_item",
        "source_system",
    )
    public = {field: _text(item, field) for field in fields}
    if item.get("source_url"):
        public["source_url"] = _text(item, "source_url")
    return public


def _public_relation(relation: dict[str, object]) -> dict[str, object]:
    fields = (
        "asserted_by",
        "from_source_item",
        "relation_id",
        "relation_type",
        "review_state",
        "to_source_item",
    )
    public = {field: _text(relation, field) for field in fields}
    source = relation.get("evidence_reference")
    if not isinstance(source, dict):
        raise ValueError("source relation evidence_reference must be an object")
    evidence = {field: _text(source, field) for field in ("locator", "source_url")}
    if source.get("source_asset_sha256"):
        evidence["source_asset_sha256"] = _text(source, "source_asset_sha256")
    public["evidence_reference"] = evidence
    return public


def _record(path: Path, identity_field: str, identity: str) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"missing {identity_field} record: {identity}")
    record = _read_json(path)
    if record.get(identity_field) != identity:
        raise ValueError(f"{identity_field} record mismatch: {identity}")
    return record


def _ids(
    record: dict[str, object],
    field: str,
    *,
    required: bool = True,
) -> list[str]:
    values = record.get(field, [] if not required else None)
    if (
        not isinstance(values, list)
        or any(not isinstance(value, str) or not value.strip() for value in values)
        or len(values) != len(set(values))
    ):
        raise ValueError(f"{field} must be a list of unique non-empty strings")
    return sorted(values)


def _text(record: dict[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value
