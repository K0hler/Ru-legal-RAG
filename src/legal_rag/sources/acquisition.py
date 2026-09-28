from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid

from .publication_pravo import PublicationPravoConnector, PublicationPravoFailure


def acquire_fixture(
    fixture_path: Path,
    metadata_path: Path,
    data_dir: Path,
) -> dict[str, str]:
    started_at = _utc_now()
    fixture_path = Path(fixture_path)
    metadata_path = Path(metadata_path)
    data_dir = Path(data_dir)

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw_bytes = fixture_path.read_bytes()
    if raw_bytes.startswith(b"%PDF-"):
        media_type = "application/pdf"
    else:
        try:
            decoded = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            media_type = "application/octet-stream"
        else:
            try:
                json.loads(decoded)
            except json.JSONDecodeError:
                media_type = "text/plain; charset=utf-8"
            else:
                media_type = "application/json"
    return _persist_success(
        {
            "adapter_version": metadata["adapter_version"],
            "captured_at": metadata["captured_at"],
            "declared_act_identity": metadata["declared_act_identity"],
            "declared_edition_label": metadata["declared_edition_label"],
            "declared_publication": None,
            "external_id": metadata["external_id"],
            "media_type": media_type,
            "raw_bytes": raw_bytes,
            "request_cursor": None,
            "rights_status": metadata["rights_status"],
            "source_system": metadata["source_system"],
            "source_url": metadata["source_url"],
            "transport_metadata": {
                "fixture": fixture_path.name,
                "metadata": metadata_path.name,
                "declared_media_type": metadata["media_type"],
            },
        },
        data_dir,
        started_at,
    )


def acquire_publication(
    connector: PublicationPravoConnector,
    eo_number: str,
    data_dir: Path,
) -> dict[str, str]:
    started_at = _utc_now()
    data_dir = Path(data_dir)
    source_item = f"{connector.source_system}:{eo_number}"
    try:
        fetched = connector.fetch(eo_number)
    except PublicationPravoFailure as error:
        return _record_failed_run(
            data_dir=data_dir,
            source=connector.source_system,
            source_item=source_item,
            adapter_version=connector.adapter_version,
            request_cursor=eo_number,
            started_at=started_at,
            error=error.as_record(),
        )
    return _persist_success(fetched, data_dir, started_at)


def _persist_success(
    fetched: dict[str, object],
    data_dir: Path,
    started_at: str,
) -> dict[str, str]:
    raw_bytes = fetched["raw_bytes"]
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    publication_card_bytes = fetched.get("publication_card_bytes")
    publication_card_sha256 = (
        hashlib.sha256(publication_card_bytes).hexdigest()
        if publication_card_bytes is not None
        else None
    )
    source_item = f"{fetched['source_system']}:{fetched['external_id']}"
    item_id = hashlib.sha256(source_item.encode("utf-8")).hexdigest()

    item_path = data_dir / "items" / f"{item_id}.json"
    previous_item = _read_json(item_path) if item_path.exists() else None
    if previous_item is not None and (
        previous_item["source_system"] != fetched["source_system"]
        or previous_item["external_id"] != fetched["external_id"]
        or previous_item["declared_act_identity"] != fetched["declared_act_identity"]
    ):
        return _record_failed_run(
            data_dir=data_dir,
            source=fetched["source_system"],
            source_item=source_item,
            adapter_version=fetched["adapter_version"],
            request_cursor=fetched["request_cursor"],
            started_at=started_at,
            error={
                "message": f"source item identity conflict: {source_item}",
                "reason": "source_item_identity_conflict",
                "retryable": False,
                "source_url": fetched["source_url"],
                "stage": "acquisition",
            },
        )

    previous_raw_sha256 = previous_item["latest_successful_asset"] if previous_item else None
    previous_card_sha256 = previous_item.get("declared_publication_asset") if previous_item else None
    change = None
    if previous_raw_sha256 is None:
        result = "new"
    elif previous_raw_sha256 == raw_sha256 and previous_card_sha256 == publication_card_sha256:
        result = "unchanged"
    else:
        result = "changed"
        if previous_raw_sha256 != raw_sha256:
            change = {
                "new_sha256": raw_sha256,
                "old_sha256": previous_raw_sha256,
                "source_item": source_item,
            }
        else:
            change = {"source_item": source_item}
        if previous_card_sha256 != publication_card_sha256:
            change["changed_assets"] = {
                "declared_publication": {
                    "new_sha256": publication_card_sha256,
                    "old_sha256": previous_card_sha256,
                }
            }

    _persist_asset(
        data_dir=data_dir,
        raw_bytes=raw_bytes,
        captured_at=fetched["captured_at"],
        media_type=fetched["media_type"],
        rights_status=fetched["rights_status"],
        source_url=fetched["source_url"],
        transport_metadata=fetched["transport_metadata"],
    )
    if publication_card_bytes is not None:
        _persist_asset(
            data_dir=data_dir,
            raw_bytes=publication_card_bytes,
            captured_at=fetched["captured_at"],
            media_type="application/json",
            rights_status=fetched["rights_status"],
            source_url=fetched["publication_card_url"],
            transport_metadata=fetched["publication_card_transport_metadata"],
            role="declared_publication",
        )

    previous_asset_sha256s = previous_item["asset_sha256s"] if previous_item else []
    current_asset_sha256s = [raw_sha256]
    if publication_card_sha256 is not None:
        current_asset_sha256s.append(publication_card_sha256)
    asset_sha256s = list(dict.fromkeys([*previous_asset_sha256s, *current_asset_sha256s]))
    item = {
        "adapter_version": fetched["adapter_version"],
        "asset_sha256s": asset_sha256s,
        "captured_at": fetched["captured_at"],
        "declared_act_identity": fetched["declared_act_identity"],
        "declared_edition_label": fetched["declared_edition_label"],
        "external_id": fetched["external_id"],
        "item_kind": fetched.get(
            "item_kind",
            previous_item.get("item_kind", "source") if previous_item else "source",
        ),
        "label": fetched.get(
            "label",
            previous_item.get("label", fetched["declared_act_identity"])
            if previous_item
            else fetched["declared_act_identity"],
        ),
        "latest_successful_asset": raw_sha256,
        "rights_status": fetched["rights_status"],
        "source_item": source_item,
        "source_system": fetched["source_system"],
        "source_url": fetched["source_url"],
    }
    if fetched["declared_publication"] is not None:
        item["declared_publication"] = fetched["declared_publication"]
    if publication_card_sha256 is not None:
        item["declared_publication_asset"] = publication_card_sha256
    if "discovered_source_items" in fetched:
        item["discovered_source_items"] = fetched["discovered_source_items"]
    if "relation_claims" in fetched:
        relation_claims = []
        for relation_claim in fetched["relation_claims"]:
            evidence_reference = dict(relation_claim["evidence_reference"])
            if publication_card_sha256 is not None:
                evidence_reference["source_asset_sha256"] = publication_card_sha256
            relation_claims.append(
                {
                    **relation_claim,
                    "evidence_reference": evidence_reference,
                }
            )
        item["relation_claims"] = relation_claims
    _write_json(
        item_path,
        item,
    )

    run_id = str(uuid.uuid4())
    report_path = data_dir / "runs" / f"{run_id}.json"
    counts = {status: int(status == result) for status in ("new", "unchanged", "changed", "failed")}
    report = {
        "adapter_version": fetched["adapter_version"],
        "counts": counts,
        "errors": [],
        "finished_at": _utc_now(),
        "request_cursor": fetched["request_cursor"],
        "result": result,
        "run_id": run_id,
        "source": fetched["source_system"],
        "source_item": source_item,
        "started_at": started_at,
    }
    if change is not None:
        report["change"] = change
    _write_json(report_path, report)
    return {
        "report": str(report_path.resolve()),
        "result": result,
        "run_id": run_id,
        "source_item": source_item,
    }


def _record_failed_run(
    *,
    data_dir: Path,
    source: str,
    source_item: str,
    adapter_version: str,
    request_cursor: str,
    started_at: str,
    error: dict[str, object],
) -> dict[str, str]:
    run_id = str(uuid.uuid4())
    exception_id = str(uuid.uuid4())
    created_at = _utc_now()
    exception = {
        "created_at": created_at,
        "diagnostic_message": error["message"],
        "exception_id": exception_id,
        "reason": error["reason"],
        "retryable": error["retryable"],
        "source": source,
        "source_item": source_item,
        "stage": error["stage"],
    }
    for field in ("http_status", "source_url"):
        if field in error:
            exception[field] = error[field]
    _write_json(data_dir / "exceptions" / f"{exception_id}.json", exception)

    report_path = data_dir / "runs" / f"{run_id}.json"
    _write_json(
        report_path,
        {
            "adapter_version": adapter_version,
            "counts": {status: int(status == "failed") for status in ("new", "unchanged", "changed", "failed")},
            "errors": [error],
            "exception_ids": [exception_id],
            "finished_at": created_at,
            "request_cursor": request_cursor,
            "result": "failed",
            "run_id": run_id,
            "source": source,
            "source_item": source_item,
            "started_at": started_at,
        },
    )
    return {
        "report": str(report_path.resolve()),
        "result": "failed",
        "run_id": run_id,
        "source_item": source_item,
    }


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _persist_asset(
    *,
    data_dir: Path,
    raw_bytes: bytes,
    captured_at: str,
    media_type: str,
    rights_status: str,
    source_url: str,
    transport_metadata: dict[str, object],
    role: str | None = None,
) -> str:
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    _write_once(data_dir / "raw" / raw_sha256, raw_bytes)
    asset = {
        "archive_key": f"raw/{raw_sha256}",
        "byte_length": len(raw_bytes),
        "captured_at": captured_at,
        "media_type": media_type,
        "rights_status": rights_status,
        "sha256": raw_sha256,
        "source_url": source_url,
        "transport_metadata": transport_metadata,
    }
    if role is not None:
        asset["role"] = role
    _write_json_once(data_dir / "assets" / f"{raw_sha256}.json", asset)
    return raw_sha256


def _write_json_once(path: Path, value: dict[str, object]) -> None:
    if not path.exists():
        _write_json(path, value)


def _write_json(path: Path, value: dict[str, object]) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    _write(path, payload)


def _write_once(path: Path, payload: bytes) -> None:
    if not path.exists():
        _write(path, payload)


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
