import hashlib
import json
from pathlib import Path

from .acquisition import _write_json_once, _write_once


def reconcile_publication_relations(
    claims_path: Path,
    data_dir: Path,
) -> dict[str, object]:
    claims_path = Path(claims_path)
    data_dir = Path(data_dir)
    claims = json.loads(claims_path.read_text(encoding="utf-8"))

    if not isinstance(claims, dict):
        raise ValueError("claims must be a JSON object")
    for field in ("act_source_item", "captured_at"):
        if not isinstance(claims.get(field), str) or not claims[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if not isinstance(claims.get("items"), list):
        raise ValueError("items must be a list")
    if not isinstance(claims.get("relation_claims"), list):
        raise ValueError("relation_claims must be a list")
    if not isinstance(claims.get("provenance"), dict):
        raise ValueError("provenance must be an object")

    items = claims["items"]
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each item must be an object")
        for field in ("external_id", "item_kind", "label", "source_item", "source_system"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"item {field} must be a non-empty string")
        if "source_url" in item and (
            not isinstance(item["source_url"], str) or not item["source_url"].strip()
        ):
            raise ValueError("item source_url must be a non-empty string")

    item_by_id = {item["source_item"]: item for item in items}
    if len(item_by_id) != len(items):
        raise ValueError("source_item values must be unique")
    if claims["act_source_item"] not in item_by_id:
        raise ValueError("act_source_item must identify an item")

    relations = []
    exceptions = []
    for claim in claims["relation_claims"]:
        if not isinstance(claim, dict):
            raise ValueError("each relation claim must be an object")
        for field in ("asserted_by", "from_source_item", "relation_type"):
            if not isinstance(claim.get(field), str) or not claim[field].strip():
                raise ValueError(f"relation claim {field} must be a non-empty string")
        candidates = claim.get("to_candidates")
        if not isinstance(candidates, list) or any(
            not isinstance(candidate, str) or not candidate.strip()
            for candidate in candidates
        ):
            raise ValueError("relation claim to_candidates must be a list of non-empty strings")
        evidence = claim.get("evidence_reference")
        if not isinstance(evidence, dict):
            raise ValueError("relation claim evidence_reference must be an object")
        for field in ("locator", "source_url"):
            if not isinstance(evidence.get(field), str) or not evidence[field].strip():
                raise ValueError(f"evidence_reference {field} must be a non-empty string")
        if "diagnostic_message" in claim and (
            not isinstance(claim["diagnostic_message"], str)
            or not claim["diagnostic_message"].strip()
        ):
            raise ValueError("diagnostic_message must be a non-empty string")

        source_item = claim["from_source_item"]
        if source_item not in item_by_id:
            raise ValueError(f"unknown from_source_item: {source_item}")

        if len(candidates) == 1 and candidates[0] in item_by_id:
            relation = {
                "asserted_by": claim["asserted_by"],
                "evidence_reference": claim["evidence_reference"],
                "from_source_item": source_item,
                "relation_type": claim["relation_type"],
                "review_state": "source_claim",
                "to_source_item": candidates[0],
            }
            relation["relation_id"] = _stable_id(relation)
            relations.append(relation)
            continue

        reason = (
            "ambiguous_relation_target"
            if len(candidates) > 1
            else "missing_relation_target"
        )
        message = claim.get(
            "diagnostic_message",
            f"{claim['relation_type']} claim has {len(candidates)} candidate targets; no relation was created.",
        )
        exception = {
            "asserted_by": claim["asserted_by"],
            "candidate_source_items": candidates,
            "created_at": claims["captured_at"],
            "diagnostic_message": message,
            "evidence_reference": claim["evidence_reference"],
            "reason": reason,
            "relation_type": claim["relation_type"],
            "retryable": False,
            "source_item": source_item,
            "stage": "relation_reconciliation",
        }
        exception["exception_id"] = _stable_id(exception)
        exceptions.append(exception)

    reconciliation_id = _stable_id(claims)
    reconciliation_path = data_dir / "reconciliations" / f"{reconciliation_id}.json"
    report_path = data_dir / "reports" / "relations" / f"{reconciliation_id}.md"
    result = "unchanged" if reconciliation_path.exists() else "new"
    report = _render_report(claims["act_source_item"], item_by_id, relations, exceptions)
    item_record_ids = [_stable_id(item) for item in items]

    for item, item_record_id in zip(items, item_record_ids, strict=True):
        item_path = data_dir / "relation-items" / f"{item_record_id}.json"
        _write_json_once(item_path, item)
    for relation in relations:
        relation_path = data_dir / "relations" / f"{relation['relation_id']}.json"
        _write_json_once(relation_path, relation)
    for exception in exceptions:
        exception_path = data_dir / "exceptions" / f"{exception['exception_id']}.json"
        _write_json_once(exception_path, exception)

    _write_once(report_path, report.encode("utf-8"))
    _write_json_once(
        reconciliation_path,
        {
            "act_source_item": claims["act_source_item"],
            "captured_at": claims["captured_at"],
            "exception_ids": [item["exception_id"] for item in exceptions],
            "item_record_ids": item_record_ids,
            "item_source_ids": [item["source_item"] for item in items],
            "provenance": claims["provenance"],
            "reconciliation_id": reconciliation_id,
            "relation_ids": [item["relation_id"] for item in relations],
        },
    )
    return {
        "act_source_item": claims["act_source_item"],
        "exception_count": len(exceptions),
        "reconciliation": str(reconciliation_path.resolve()),
        "relation_count": len(relations),
        "report": str(report_path.resolve()),
        "result": result,
    }


def _stable_id(value: object) -> str:
    if isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _render_report(
    act_source_item: str,
    item_by_id: dict[str, dict[str, object]],
    relations: list[dict[str, object]],
    exceptions: list[dict[str, object]],
) -> str:
    lines = [
        "# Publication relations",
        "",
        f"Act: **{item_by_id[act_source_item]['label']}** (`{act_source_item}`)",
        "",
        "## Source items",
        "",
    ]
    for source_item, item in sorted(item_by_id.items()):
        lines.append(f"- `{item['item_kind']}` — {item['label']} (`{source_item}`)")

    lines.extend(["", "## Relations", ""])
    if not relations:
        lines.append("- None.")
    for relation in relations:
        source = item_by_id[relation["from_source_item"]]
        target = item_by_id[relation["to_source_item"]]
        evidence = relation["evidence_reference"]
        lines.extend(
            [
                f"- {source['label']} — `{relation['relation_type']}` → {target['label']}",
                f"  - Asserted by: `{relation['asserted_by']}`",
                f"  - Evidence: {evidence['source_url']} — {evidence['locator']}",
            ]
        )

    lines.extend(["", "## Unresolved gaps", ""])
    if not exceptions:
        lines.append("- None.")
    for exception in exceptions:
        lines.append(
            f"- `{exception['reason']}` for `{exception['relation_type']}` from "
            f"`{exception['source_item']}`: {exception['diagnostic_message']}"
        )
    return "\n".join(lines) + "\n"
