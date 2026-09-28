import hashlib
import json
from pathlib import Path

from .acquisition import _read_json, _write_json, _write_json_once, _write_once


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
    acquired_source_items = claims.get("acquired_source_items", [])
    if not isinstance(acquired_source_items, list) or any(
        not isinstance(source_item, str) or not source_item.strip()
        for source_item in acquired_source_items
    ):
        raise ValueError("acquired_source_items must be a list of non-empty strings")

    items = list(claims["items"])
    relation_claims = list(claims["relation_claims"])
    acquired_inputs = []
    for source_item in acquired_source_items:
        item_path = data_dir / "items" / f"{_stable_id(source_item)}.json"
        if not item_path.exists():
            raise ValueError(f"acquired source item not found: {source_item}")
        acquired_item = _read_json(item_path)
        if acquired_item.get("source_item") != source_item:
            raise ValueError(f"acquired source item identity conflict: {source_item}")
        discovered_items = acquired_item.get("discovered_source_items", [])
        discovered_relations = acquired_item.get("relation_claims", [])
        if not isinstance(discovered_items, list) or not isinstance(discovered_relations, list):
            raise ValueError(f"acquired source item has invalid source claims: {source_item}")
        asset_sha256s = acquired_item.get("asset_sha256s", [])
        if not isinstance(asset_sha256s, list):
            raise ValueError(f"acquired source item has invalid assets: {source_item}")
        supporting_assets = acquired_item.get("supporting_assets", {})
        if not isinstance(supporting_assets, dict):
            raise ValueError(f"acquired source item has invalid assets: {source_item}")
        for relation_claim in discovered_relations:
            if not isinstance(relation_claim, dict):
                raise ValueError(f"acquired source item has invalid source claims: {source_item}")
            evidence = relation_claim.get("evidence_reference", {})
            if not isinstance(evidence, dict):
                raise ValueError(f"acquired source item has invalid source claims: {source_item}")
            evidence_sha256 = evidence.get("source_asset_sha256")
            if evidence_sha256 not in asset_sha256s:
                raise ValueError(f"acquired relation evidence asset mismatch: {source_item}")
            evidence_role = evidence.get("source_asset_role")
            if evidence_role is None:
                expected_role = "declared_publication"
                expected_sha256 = acquired_item.get("declared_publication_asset")
            elif isinstance(evidence_role, str) and evidence_role.strip():
                expected_role = evidence_role
                expected_sha256 = supporting_assets.get(evidence_role)
            else:
                raise ValueError(f"acquired relation evidence asset role mismatch: {source_item}")
            if evidence_sha256 != expected_sha256:
                raise ValueError(f"acquired relation evidence asset role mismatch: {source_item}")
            asset_path = data_dir / "assets" / f"{evidence_sha256}.json"
            raw_path = data_dir / "raw" / str(evidence_sha256)
            if not asset_path.is_file() or not raw_path.is_file():
                raise ValueError(f"acquired relation evidence asset missing: {source_item}")
            asset = _read_json(asset_path)
            if (
                asset.get("sha256") != evidence_sha256
                or asset.get("archive_key") != f"raw/{evidence_sha256}"
                or asset.get("role") != expected_role
                or asset.get("source_url") != evidence.get("source_url")
                or hashlib.sha256(raw_path.read_bytes()).hexdigest() != evidence_sha256
            ):
                raise ValueError(f"acquired relation evidence asset invalid: {source_item}")
        items.extend([acquired_item, *discovered_items])
        relation_claims.extend(discovered_relations)
        acquired_inputs.append(
            {
                "declared_publication_asset": acquired_item.get("declared_publication_asset"),
                "discovered_source_items": discovered_items,
                "relation_claims": discovered_relations,
                "source_item": source_item,
                "supporting_assets": acquired_item.get("supporting_assets", {}),
            }
        )

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
    for claim in relation_claims:
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
        if "source_asset_sha256" in evidence and (
            not isinstance(evidence["source_asset_sha256"], str)
            or not evidence["source_asset_sha256"].strip()
        ):
            raise ValueError("evidence_reference source_asset_sha256 must be a non-empty string")
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

    reconciliation_id = _stable_id(
        {
            "acquired_inputs": acquired_inputs,
            "claims": claims,
        }
    )
    reconciliation_path = data_dir / "reconciliations" / f"{reconciliation_id}.json"
    report_path = data_dir / "reports" / "relations" / f"{reconciliation_id}.md"
    result = "unchanged" if reconciliation_path.exists() else "new"
    report = _render_report(claims["act_source_item"], item_by_id, relations, exceptions)
    canonical_items = []
    for item in items:
        canonical_item = _canonical_source_item(item, claims)
        item_path = data_dir / "items" / f"{_stable_id(item['source_item'])}.json"
        if item_path.exists():
            existing_item = _read_json(item_path)
            for field in ("declared_act_identity", "external_id", "source_system"):
                if existing_item.get(field) != canonical_item.get(field):
                    raise ValueError(
                        f"source item {field} conflict: {item['source_item']}"
                    )
            canonical_item = {
                **canonical_item,
                **existing_item,
                "item_kind": existing_item.get("item_kind", canonical_item["item_kind"]),
                "label": existing_item.get("label", canonical_item["label"]),
            }
        canonical_items.append((item_path, canonical_item))

    for item_path, canonical_item in canonical_items:
        if item_path.exists():
            if _read_json(item_path) != canonical_item:
                _write_json(item_path, canonical_item)
        else:
            _write_json_once(item_path, canonical_item)
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


def _canonical_source_item(
    item: dict[str, object],
    claims: dict[str, object],
) -> dict[str, object]:
    if "asset_sha256s" in item and "latest_successful_asset" in item:
        return dict(item)
    canonical_item = {
        "adapter_version": "relation-reconciliation/1",
        "asset_sha256s": [],
        "captured_at": claims["captured_at"],
        "declared_act_identity": item.get("declared_act_identity", item["label"]),
        "declared_edition_label": item.get("declared_edition_label"),
        "external_id": item["external_id"],
        "item_kind": item["item_kind"],
        "label": item["label"],
        "latest_successful_asset": None,
        "rights_status": claims["provenance"].get(
            "rights_status",
            "Unspecified relation-claim provenance",
        ),
        "source_item": item["source_item"],
        "source_system": item["source_system"],
    }
    if "source_url" in item:
        canonical_item["source_url"] = item["source_url"]
    return canonical_item


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
