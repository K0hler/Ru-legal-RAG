from datetime import UTC, datetime
import hashlib
from pathlib import Path
from time import monotonic, sleep
import uuid

from .acquisition import (
    _read_json,
    _write_json,
    acquire_actual,
    acquire_legislation,
    acquire_publication,
)
from .actual_pravo import ActualPravoConnector
from .legislation_russia import LegislationRussiaConnector
from .publication_pravo import PublicationPravoConnector


_REQUEST_INTERVAL_SECONDS = 1.0
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.0
_SOURCE_SYSTEMS = {
    "actual": "actual.pravo.gov.ru",
    "legislation": "pravo.gov.ru/legislation-russia",
    "publication": "publication.pravo.gov.ru",
}

PILOT_ACTS = (
    {
        "act_id": "housing-code",
        "label": "ЖК РФ",
        "original_publication": "official_print_metadata_only",
        "items": (
            {
                "connector": "actual",
                "external_id": "8b4a1920bd1b392ecc9684dc74ddebb02da5af465df06bc4a7ff8c2baf3915ce",
                "role": "consolidated_edition",
            },
        ),
    },
    {
        "act_id": "government-decree-354",
        "label": "ПП РФ № 354",
        "original_publication": "official_print_metadata_only",
        "items": (
            {
                "connector": "legislation",
                "external_id": "c0f54c3af0cc8f1b02f48f62483afb358baeb55269d4be8e00e69458ebd3a663",
                "role": "consolidated_edition",
            },
        ),
    },
    {
        "act_id": "government-decree-491",
        "label": "ПП РФ № 491",
        "original_publication": "official_print_metadata_only",
        "items": (
            {
                "connector": "legislation",
                "external_id": "79a4eeb726366b2c4d5b7c72cd6185c5ca569a8ea77fd7a2e96c0582d95ae4dd",
                "role": "consolidated_edition",
            },
        ),
    },
    {
        "act_id": "federal-law-59",
        "label": "59-ФЗ",
        "original_publication": "official_print_metadata_only",
        "items": (
            {
                "connector": "actual",
                "external_id": "4c8dcb690700cdc95a209ca40db2bb177cfc85916d6cfef83439b8696fbf546f",
                "role": "consolidated_edition",
            },
        ),
    },
    {
        "act_id": "sanpin-2.1.3684-21",
        "label": "СанПиН 2.1.3684-21",
        "original_publication": "acquisition_required",
        "items": (
            {
                "connector": "publication",
                "external_id": "0001202102050027",
                "role": "official_publication",
            },
            *(
                {
                    "connector": "publication",
                    "external_id": external_id,
                    "role": "official_amendment",
                }
                for external_id in (
                    "0001202107070011",
                    "0001202112300125",
                    "0001202202170032",
                    "0001202412270033",
                    "0001202507240013",
                    "0001202507250037",
                    "0001202512300004",
                    "0001202602270023",
                    "0001202609240014",
                )
            ),
        ),
    },
)


def run_pilot(data_dir: Path, timeout: float = 20.0) -> dict[str, object]:
    data_dir = Path(data_dir)
    manifest = _manifest()
    source_items = [item["source_item"] for act in manifest for item in act["items"]]
    if len(manifest) != 5 or len(source_items) != len(set(source_items)):
        raise ValueError("pilot manifest must contain five acts with unique source items")

    connectors = {
        "actual": ActualPravoConnector(timeout, _REQUEST_INTERVAL_SECONDS),
        "legislation": LegislationRussiaConnector(timeout, _REQUEST_INTERVAL_SECONDS),
        "publication": PublicationPravoConnector(timeout, _REQUEST_INTERVAL_SECONDS),
    }
    pilot_id = str(uuid.uuid4())
    pilot_dir = data_dir / "pilot_runs" / pilot_id
    started_at = _utc_now()
    started = monotonic()
    passes = []
    for pass_number in (1, 2):
        pass_report = _run_pass(pass_number, manifest, connectors, data_dir)
        pass_path = pilot_dir / f"pass-{pass_number}.json"
        _write_json(pass_path, pass_report)
        passes.append({**pass_report, "report": str(pass_path.resolve())})

    coverage, coverage_gaps = _coverage(manifest, passes, data_dir)
    metrics = {
        "bytes_received": sum(item["metrics"]["bytes_received"] for report in passes for item in report["items"]),
        "elapsed_seconds": round(monotonic() - started, 3),
        "failed_attempts": sum(len(item["errors"]) for report in passes for item in report["items"]),
        "request_count": sum(item["metrics"]["request_count"] for report in passes for item in report["items"]),
        "retry_count": sum(item["retry_count"] for report in passes for item in report["items"]),
    }
    exceptions = [
        {
            "act_id": item["act_id"],
            "errors": item["errors"],
            "exception_ids": [
                exception_id
                for attempt in item["attempts"]
                for exception_id in attempt["exception_ids"]
            ],
            "pass": pass_report["pass"],
            "source_item": item["source_item"],
        }
        for pass_report in passes
        for item in pass_report["items"]
        if item["errors"]
    ]
    result = "failed" if any(report["counts"]["failed"] for report in passes) else "completed"
    report = {
        "coverage": coverage,
        "coverage_gaps": coverage_gaps,
        "duplicate_source_items": [],
        "exceptions": exceptions,
        "finished_at": _utc_now(),
        "manifest": manifest,
        "metrics": metrics,
        "passes": passes,
        "pilot_id": pilot_id,
        "result": result,
        "schema_version": "m0-pilot-report/1",
        "started_at": started_at,
    }
    report_path = pilot_dir / "report.json"
    _write_json(report_path, report)
    return {
        "pilot_id": pilot_id,
        "report": str(report_path.resolve()),
        "result": result,
    }


def _manifest() -> list[dict[str, object]]:
    return [
        {
            "act_id": act["act_id"],
            "items": [
                {**item, "source_item": _source_item(item)} for item in act["items"]
            ],
            "label": act["label"],
            "original_publication": act["original_publication"],
        }
        for act in PILOT_ACTS
    ]


def _run_pass(
    pass_number: int,
    manifest: list[dict[str, object]],
    connectors: dict[str, object],
    data_dir: Path,
) -> dict[str, object]:
    started_at = _utc_now()
    started = monotonic()
    raw_before = _file_count(data_dir / "raw")
    items = []
    for act in manifest:
        for item in act["items"]:
            items.append(
                _run_item(
                    act["act_id"],
                    act["label"],
                    item,
                    connectors,
                    data_dir,
                )
            )
    counts = {
        status: sum(item["result"] == status for item in items)
        for status in ("new", "unchanged", "changed", "failed")
    }
    raw_after = _file_count(data_dir / "raw")
    return {
        "counts": counts,
        "finished_at": _utc_now(),
        "items": items,
        "metrics": {
            "bytes_received": sum(item["metrics"]["bytes_received"] for item in items),
            "elapsed_seconds": round(monotonic() - started, 3),
            "request_count": sum(item["metrics"]["request_count"] for item in items),
            "retry_count": sum(item["retry_count"] for item in items),
        },
        "pass": pass_number,
        "raw_asset_count_after": raw_after,
        "raw_asset_count_before": raw_before,
        "raw_assets_added": raw_after - raw_before,
        "schema_version": "m0-pilot-pass/1",
        "started_at": started_at,
    }


def _run_item(
    act_id: str,
    act_label: str,
    item: dict[str, str],
    connectors: dict[str, object],
    data_dir: Path,
) -> dict[str, object]:
    started = monotonic()
    attempts = []
    for attempt_number in range(1, _MAX_ATTEMPTS + 1):
        result = _acquire_item(item, connectors, data_dir)
        report = _read_json(Path(result["report"]))
        if result["source_item"] != item["source_item"]:
            raise ValueError(f"pilot source item mismatch: {item['source_item']}")
        attempts.append(
            {
                "errors": report["errors"],
                "exception_ids": report.get("exception_ids", []),
                "metrics": report["metrics"],
                "report": result["report"],
                "result": result["result"],
                "run_id": result["run_id"],
            }
        )
        retryable = bool(report["errors"] and report["errors"][0]["retryable"])
        if result["result"] != "failed" or not retryable or attempt_number == _MAX_ATTEMPTS:
            break
        sleep(_RETRY_BACKOFF_SECONDS * 2 ** (attempt_number - 1))

    return {
        "act_id": act_id,
        "act_label": act_label,
        "attempts": attempts,
        "connector": item["connector"],
        "elapsed_seconds": round(monotonic() - started, 3),
        "errors": [error for attempt in attempts for error in attempt["errors"]],
        "external_id": item["external_id"],
        "metrics": {
            "bytes_received": sum(attempt["metrics"]["bytes_received"] for attempt in attempts),
            "request_count": sum(attempt["metrics"]["request_count"] for attempt in attempts),
        },
        "result": attempts[-1]["result"],
        "retry_count": len(attempts) - 1,
        "role": item["role"],
        "source_item": item["source_item"],
    }


def _acquire_item(
    item: dict[str, str],
    connectors: dict[str, object],
    data_dir: Path,
) -> dict[str, str]:
    connector = connectors[item["connector"]]
    if item["connector"] == "actual":
        return acquire_actual(connector, item["external_id"], data_dir)
    if item["connector"] == "legislation":
        return acquire_legislation(connector, item["external_id"], data_dir)
    return acquire_publication(connector, item["external_id"], data_dir)


def _coverage(
    manifest: list[dict[str, object]],
    passes: list[dict[str, object]],
    data_dir: Path,
) -> tuple[list[dict[str, object]], dict[str, list[str]]]:
    results = {
        item["source_item"]: item
        for report in passes
        for item in report["items"]
        if item["result"] != "failed"
    }
    coverage = []
    for act in manifest:
        consolidated = [item for item in act["items"] if item["role"] == "consolidated_edition"]
        publications = [item for item in act["items"] if item["role"] == "official_publication"]
        amendments = [item for item in act["items"] if item["role"] == "official_amendment"]
        consolidated_state = (
            "acquired"
            if consolidated and all(_has_state(item, results, data_dir) for item in consolidated)
            else "failed" if consolidated else "missing"
        )
        if publications:
            publication_state = (
                "acquired"
                if all(_has_state(item, results, data_dir) for item in publications)
                else "failed"
            )
        else:
            publication_state = act["original_publication"]
        acquired_amendments = sum(_has_state(item, results, data_dir) for item in amendments)
        amendment_state = (
            "acquired"
            if amendments and acquired_amendments == len(amendments)
            else "incomplete" if amendments else "unresolved"
        )
        coverage.append(
            {
                "act_id": act["act_id"],
                "amendments": {
                    "acquired": acquired_amendments,
                    "expected": len(amendments) or None,
                    "status": amendment_state,
                },
                "consolidated_edition": consolidated_state,
                "label": act["label"],
                "official_publication": publication_state,
                "temporal_evidence": "unresolved",
            }
        )
    return coverage, {
        "amendment_coverage_unresolved": [
            act["act_id"] for act in coverage if act["amendments"]["status"] != "acquired"
        ],
        "missing_consolidated_editions": [
            act["act_id"] for act in coverage if act["consolidated_edition"] != "acquired"
        ],
        "temporal_evidence_unresolved": [act["act_id"] for act in coverage],
    }


def _has_state(
    item: dict[str, str],
    successful_results: dict[str, dict[str, object]],
    data_dir: Path,
) -> bool:
    if item["source_item"] in successful_results:
        return True
    item_id = hashlib.sha256(item["source_item"].encode("utf-8")).hexdigest()
    item_path = data_dir / "items" / f"{item_id}.json"
    return item_path.is_file() and bool(_read_json(item_path).get("latest_successful_asset"))


def _source_item(item: dict[str, str]) -> str:
    return f"{_SOURCE_SYSTEMS[item['connector']]}:{item['external_id']}"


def _file_count(path: Path) -> int:
    return sum(1 for item in path.iterdir() if item.is_file()) if path.is_dir() else 0


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
