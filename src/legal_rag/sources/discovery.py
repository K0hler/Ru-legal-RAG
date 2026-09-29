from datetime import UTC, date, datetime
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .acquisition import (
    _persist_success,
    _read_json,
    _record_failed_run,
    _write_json,
    _write_json_once,
    acquire_publication,
)
from .publication_pravo import PublicationPravoConnector, PublicationPravoFailure
from .relations import _stable_id, reconcile_publication_relations


_RUSSIAN_MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def discover_official_publications(
    connector: PublicationPravoConnector,
    publication_date: date,
    data_dir: Path,
) -> dict[str, object]:
    data_dir = Path(data_dir)
    targets = _known_targets(data_dir)
    if not targets:
        raise ValueError("no edition candidates with declared act targets were found")

    events = []
    feed_asset_sha256s = []
    page = 1
    while True:
        started_at = _utc_now()
        try:
            fetched = connector.fetch_feed(publication_date, page)
        except PublicationPravoFailure as error:
            return _record_failed_run(
                data_dir=data_dir,
                source=connector.source_system,
                source_item=(
                    f"{connector.source_system}:feed:{publication_date.isoformat()}:page:{page}"
                ),
                adapter_version=connector.adapter_version,
                request_cursor=f"{publication_date.isoformat()}:page:{page}",
                started_at=started_at,
                error=error.as_record(),
                metrics=connector.metrics,
            )
        _persist_success(fetched, data_dir, started_at, connector.metrics)
        feed_asset_sha256s.append(hashlib.sha256(fetched["raw_bytes"]).hexdigest())
        events.extend(fetched["events"])
        if page >= fetched["pages_total"]:
            break
        page += 1

    publication_event_ids = _persist_events(
        events,
        feed_asset_sha256s,
        publication_date,
        data_dir,
    )
    acquired_source_items = []
    relation_ids = []
    exception_ids = []
    invalidation_ids = []
    failed_source_items = []

    for event in events:
        if (
            not event["name"].strip().casefold().startswith("о внесении изменен")
            or not event["complexName"].startswith(
                "Постановление Правительства Российской Федерации"
            )
        ):
            continue
        acquisition = acquire_publication(connector, event["eoNumber"], data_dir)
        acquired_source_items.append(acquisition["source_item"])
        if acquisition["result"] == "failed":
            failed_source_items.append(acquisition["source_item"])
            continue

        item = _read_json(
            data_dir / "items" / f"{_stable_id(acquisition['source_item'])}.json"
        )
        amendment_item = next(
            (
                discovered
                for discovered in item.get("discovered_source_items", [])
                if discovered.get("item_kind") == "amendment"
            ),
            None,
        )
        if not amendment_item or not amendment_item["source_item"].startswith(
            "declared-act:government-decree:"
        ):
            continue

        amendment_claims = [
            claim
            for claim in item.get("relation_claims", [])
            if claim.get("relation_type") == "amends"
        ]
        matched_claims = [
            claim
            for claim in amendment_claims
            if len(claim.get("to_candidates", [])) == 1
            and claim["to_candidates"][0] in targets
        ]
        extraction = None
        generic_amendment = any(
            not claim.get("to_candidates") for claim in amendment_claims
        )
        if not matched_claims and generic_amendment:
            try:
                matched_claims, extraction = _claims_from_document(item, targets, data_dir)
            except RuntimeError as error:
                exception_ids.append(
                    _record_unresolved(
                        item,
                        amendment_item,
                        publication_date,
                        data_dir,
                        "document_text_extraction_failed",
                        str(error),
                    )
                )
                failed_source_items.append(acquisition["source_item"])
                continue

        if not matched_claims and not generic_amendment:
            continue
        if not matched_claims:
            exception_ids.append(
                _record_unresolved(
                    item,
                    amendment_item,
                    publication_date,
                    data_dir,
                    "unresolved_amendment_target",
                    "The official document text contains no reference to a monitored act.",
                    extraction,
                )
            )
            continue

        if extraction is not None:
            item["relation_claims"] = [
                claim
                for claim in item["relation_claims"]
                if not (
                    claim.get("relation_type") == "amends"
                    and not claim.get("to_candidates")
                )
            ] + matched_claims
            item["document_text_extraction"] = extraction
            _write_json(
                data_dir / "items" / f"{_stable_id(item['source_item'])}.json",
                item,
            )

        reconciliation = _reconcile_discovered_relations(
            item,
            matched_claims,
            targets,
            publication_date,
            data_dir,
        )
        reconciliation_record = _read_json(Path(reconciliation["reconciliation"]))
        for relation_id in reconciliation_record["relation_ids"]:
            relation = _read_json(data_dir / "relations" / f"{relation_id}.json")
            if relation["relation_type"] != "amends":
                continue
            relation_ids.append(relation_id)
            invalidation_ids.extend(
                _invalidate_candidates(
                    targets[relation["to_source_item"]]["candidate_paths"],
                    relation,
                    item,
                )
            )

    state = {
        "acquired_publication_source_items": sorted(set(acquired_source_items)),
        "candidate_invalidation_ids": sorted(set(invalidation_ids)),
        "exception_ids": sorted(set(exception_ids)),
        "failed_source_items": sorted(set(failed_source_items)),
        "feed_asset_sha256s": sorted(set(feed_asset_sha256s)),
        "publication_date": publication_date.isoformat(),
        "publication_event_ids": sorted(publication_event_ids),
        "relation_ids": sorted(set(relation_ids)),
        "schema_version": "publication-discovery/1",
    }
    discovery_id = _stable_id(state)
    report_path = data_dir / "discoveries" / f"{discovery_id}.json"
    result = "unchanged" if report_path.exists() else "new"
    _write_json_once(report_path, {"discovery_id": discovery_id, **state})
    if failed_source_items:
        result = "failed"
    return {
        "candidate_invalidation_count": len(set(invalidation_ids)),
        "discovery_id": discovery_id,
        "publication_event_count": len(publication_event_ids),
        "report": str(report_path.resolve()),
        "resolved_relation_count": len(set(relation_ids)),
        "result": result,
        "unresolved_target_count": len(set(exception_ids)),
    }


def _known_targets(data_dir: Path) -> dict[str, dict[str, object]]:
    targets: dict[str, dict[str, object]] = {}
    items_dir = data_dir / "items"
    if not items_dir.exists():
        return targets
    records = [_read_json(path) for path in items_dir.glob("*.json")]
    canonical = {
        item["source_item"]: item
        for item in records
        if item.get("item_kind") == "act"
        and isinstance(item.get("source_item"), str)
        and item["source_item"].startswith("declared-act:")
    }
    for candidate_path, candidate in (
        (path, _read_json(path)) for path in items_dir.glob("*.json")
    ):
        if candidate.get("item_kind") != "edition_candidate":
            continue
        discovered = {
            item.get("source_item"): item
            for item in candidate.get("discovered_source_items", [])
            if isinstance(item, dict)
        }
        for claim in candidate.get("relation_claims", []):
            if claim.get("relation_type") != "consolidates":
                continue
            for target in claim.get("to_candidates", []):
                target_item = discovered.get(target) or canonical.get(target)
                if target_item is None:
                    continue
                entry = targets.setdefault(
                    target,
                    {"candidate_paths": [], "item": target_item},
                )
                entry["candidate_paths"].append(candidate_path)
    return targets


def _persist_events(
    events: list[dict[str, object]],
    feed_asset_sha256s: list[str],
    publication_date: date,
    data_dir: Path,
) -> list[str]:
    event_ids = []
    for event in events:
        event_id = _stable_id(f"publication.pravo.gov.ru:{event['eoNumber']}")
        path = data_dir / "publication_events" / f"{event_id}.json"
        record = {
            "document_date": event["documentDate"],
            "document_number": event["number"],
            "event_id": event_id,
            "name": event["name"],
            "observed_feed_asset_sha256s": sorted(set(feed_asset_sha256s)),
            "publication_date": event["publishDateShort"],
            "publication_source_item": (
                f"publication.pravo.gov.ru:{event['eoNumber']}"
            ),
            "schema_version": "publication-event/1",
            "title": event["complexName"],
            "window_date": publication_date.isoformat(),
        }
        if path.exists():
            existing = _read_json(path)
            for field, value in record.items():
                if field == "observed_feed_asset_sha256s":
                    continue
                if existing.get(field) != value:
                    raise ValueError(f"publication event conflict: {event['eoNumber']}")
            record["observed_feed_asset_sha256s"] = sorted(
                set(existing["observed_feed_asset_sha256s"])
                | set(feed_asset_sha256s)
            )
            if record != existing:
                _write_json(path, record)
        else:
            _write_json_once(path, record)
        event_ids.append(event_id)
    return event_ids


def _claims_from_document(
    item: dict[str, object],
    targets: dict[str, dict[str, object]],
    data_dir: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    source_asset_sha256 = item["latest_successful_asset"]
    raw_path = data_dir / "raw" / source_asset_sha256
    pages = _extract_pdf_pages(raw_path)
    extraction = {
        "method": "pdftoppm+tesseract-rus",
        "pages": [
            {"page": page_number, "text": text}
            for page_number, text in enumerate(pages, 1)
        ],
        "source_asset_sha256": source_asset_sha256,
    }
    extraction_id = _stable_id(extraction)
    extraction["extraction_id"] = extraction_id
    _write_json_once(
        data_dir / "extractions" / f"{extraction_id}.json",
        extraction,
    )

    amendment_item = next(
        discovered
        for discovered in item["discovered_source_items"]
        if discovered.get("item_kind") == "amendment"
    )
    claims = []
    for target, page_number in _find_targets(pages, targets).items():
        claims.append(
            {
                "asserted_by": "publication.pravo.gov.ru",
                "evidence_reference": {
                    "extraction_id": extraction_id,
                    "locator": f"PDF page {page_number}; OCR match for {target}",
                    "source_asset_role": "primary_document",
                    "source_asset_sha256": source_asset_sha256,
                    "source_url": item["source_url"],
                },
                "from_source_item": amendment_item["source_item"],
                "relation_type": "amends",
                "to_candidates": [target],
            }
        )
    return claims, extraction


def _find_targets(
    pages: list[str],
    targets: dict[str, dict[str, object]],
) -> dict[str, int]:
    matches = {}
    for target in targets:
        parts = target.split(":")
        if len(parts) != 4 or parts[:2] != ["declared-act", "government-decree"]:
            continue
        signed_on = date.fromisoformat(parts[2])
        number = re.escape(parts[3])
        pattern = re.compile(
            r"постановлен\w*\s+правительства\s+российской\s+федерации\s+от\s+"
            rf"{signed_on.day}\s+{_RUSSIAN_MONTHS[signed_on.month - 1]}\s+"
            rf"{signed_on.year}\s*г?\s*\.\s*№\s*{number}(?!\d)",
            re.IGNORECASE,
        )
        for page_number, text in enumerate(pages, 1):
            normalized = re.sub(
                r"\s+",
                " ",
                text.replace("\xa0", " ").replace("—", " ").replace("–", " "),
            )
            if pattern.search(normalized):
                matches[target] = page_number
                break
    return matches


def _reconcile_discovered_relations(
    item: dict[str, object],
    matched_claims: list[dict[str, object]],
    targets: dict[str, dict[str, object]],
    publication_date: date,
    data_dir: Path,
) -> dict[str, object]:
    target_ids = sorted(claim["to_candidates"][0] for claim in matched_claims)
    claims = {
        "acquired_source_items": [item["source_item"]],
        "act_source_item": target_ids[0],
        "captured_at": f"{publication_date.isoformat()}T00:00:00Z",
        "items": [targets[target]["item"] for target in target_ids],
        "provenance": {
            "method": "official publication feed and document text",
            "rights_status": item["rights_status"],
        },
        "relation_claims": [],
    }
    claims_path = data_dir / "discovery_claims" / f"{_stable_id(claims)}.json"
    _write_json_once(claims_path, claims)
    return reconcile_publication_relations(claims_path, data_dir)


def _record_unresolved(
    item: dict[str, object],
    amendment_item: dict[str, object],
    publication_date: date,
    data_dir: Path,
    reason: str,
    message: str,
    extraction: dict[str, object] | None = None,
) -> str:
    evidence = {
        "locator": "official PDF document text",
        "source_asset_sha256": item["latest_successful_asset"],
        "source_url": item["source_url"],
    }
    if extraction is not None:
        evidence["extraction_id"] = extraction["extraction_id"]
    exception = {
        "candidate_source_items": [],
        "created_at": f"{publication_date.isoformat()}T00:00:00Z",
        "diagnostic_message": message,
        "evidence_reference": evidence,
        "reason": reason,
        "relation_type": "amends",
        "retryable": reason == "document_text_extraction_failed",
        "source_item": amendment_item["source_item"],
        "stage": "publication_discovery",
    }
    exception_id = _stable_id(exception)
    exception["exception_id"] = exception_id
    _write_json_once(data_dir / "exceptions" / f"{exception_id}.json", exception)
    return exception_id


def _invalidate_candidates(
    candidate_paths: list[Path],
    relation: dict[str, object],
    publication_item: dict[str, object],
) -> list[str]:
    invalidation_ids = []
    amendment_date = publication_item["declared_publication"]["document_date"][:10]
    for path in candidate_paths:
        candidate = _read_json(path)
        claimed_date = candidate.get("edition_claim", {}).get("claimed_edition_date")
        if not isinstance(claimed_date, str) or amendment_date <= claimed_date:
            continue
        evidence = relation["evidence_reference"]
        invalidation = {
            "candidate_source_item": candidate["source_item"],
            "newer_document_date": amendment_date,
            "required_actions": [
                "acquire_newer_consolidated_edition",
                "legal_review",
            ],
            "source_asset_sha256": evidence["source_asset_sha256"],
            "source_publication_item": publication_item["source_item"],
            "source_relation_id": relation["relation_id"],
            "status": "stale",
        }
        invalidation_id = _stable_id(invalidation)
        invalidation["invalidation_id"] = invalidation_id
        existing = {
            record["invalidation_id"]: record
            for record in candidate.get("candidate_invalidations", [])
        }
        existing[invalidation_id] = invalidation
        candidate["candidate_invalidations"] = sorted(
            existing.values(),
            key=lambda record: record["invalidation_id"],
        )
        candidate["candidate_status"] = "stale"
        unresolved = {
            "diagnostic_message": (
                f"Official publication {publication_item['external_id']} records a newer "
                "amendment; acquire and review a newer consolidated edition."
            ),
            "reason": "newer_amendment_detected",
            "source_asset_sha256": evidence["source_asset_sha256"],
            "source_relation_id": relation["relation_id"],
        }
        existing_unresolved = {
            _stable_id(record): record for record in candidate.get("unresolved_items", [])
        }
        existing_unresolved[_stable_id(unresolved)] = unresolved
        candidate["unresolved_items"] = sorted(
            existing_unresolved.values(),
            key=_stable_id,
        )
        _write_json(path, candidate)
        invalidation_ids.append(invalidation_id)
    return invalidation_ids


def _extract_pdf_pages(path: Path) -> list[str]:
    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not pdftoppm or not tesseract:
        raise RuntimeError("pdftoppm and tesseract with Russian data are required")
    with tempfile.TemporaryDirectory(prefix="legal-rag-ocr-") as temporary_directory:
        prefix = Path(temporary_directory) / "page"
        try:
            subprocess.run(
                [pdftoppm, "-r", "200", "-png", str(path), str(prefix)],
                check=True,
                capture_output=True,
            )
            images = sorted(
                prefix.parent.glob("page-*.png"),
                key=lambda image: int(image.stem.rsplit("-", 1)[1]),
            )
            if not images:
                raise RuntimeError("PDF rendering produced no pages")
            return [
                subprocess.run(
                    [tesseract, str(image), "stdout", "-l", "rus"],
                    check=True,
                    capture_output=True,
                    encoding="utf-8",
                    text=True,
                ).stdout
                for image in images
            ]
        except (OSError, subprocess.CalledProcessError) as error:
            raise RuntimeError(f"official PDF OCR failed: {error}") from error


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
