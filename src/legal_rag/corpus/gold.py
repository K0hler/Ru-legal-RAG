"""Validate local gold labels; freeze only an explicitly reviewed dataset."""

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile


QUERY_CLASSES = {
    "exact_reference", "paraphrase", "exception_negation", "confirmed_date",
    "missing_coverage", "cross_reference",
}
PILOT_ACTS = {"housing-code", "pp-354", "pp-491", "59-fz", "sanpin"}


def digest(value: object) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def _bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _text(record: dict, key: str) -> str:
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text")
    return value


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON record must be an object")
    return value


def _evidence_file(root: Path, record: dict, prefix: str) -> bytes:
    path = (root / _text(record, f"{prefix}_path")).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("evidence path escapes the dataset directory")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != _text(record, f"{prefix}_sha256"):
        raise ValueError(f"{prefix} evidence hash mismatch")
    return content


def validate(dataset_path: Path, split_path: Path, review_path: Path | None = None) -> dict:
    dataset, split = _read(dataset_path), _read(split_path)
    if dataset.get("schema_version") != "gold-question-set/1":
        raise ValueError("unsupported gold schema")
    if _text(dataset, "dataset_id") != _text(split, "dataset_id"):
        raise ValueError("split belongs to another dataset")
    _text(dataset, "label_author")
    _text(dataset, "storage_policy")
    questions = dataset.get("questions")
    if not isinstance(questions, list) or not 30 <= len(questions) <= 50:
        raise ValueError("gold set must contain 30-50 questions")
    ids = [_text(q, "id") for q in questions]
    queries = [_text(q, "query").strip().casefold() for q in questions]
    if len(set(ids)) != len(ids) or len(set(queries)) != len(queries):
        raise ValueError("duplicate question ID or query")
    members = split.get("members", {})
    if not isinstance(members, dict) or set(members) != {"working", "closed"}:
        raise ValueError("split must contain working and closed membership")
    all_members = []
    for values in members.values():
        if not isinstance(values, list) or not values or not all(isinstance(x, str) for x in values):
            raise ValueError("each split must have a non-empty ID list")
        all_members.extend(values)
    if len(set(all_members)) != len(all_members) or set(all_members) != set(ids):
        raise ValueError("split must contain every question exactly once")
    membership = {qid: name for name, values in members.items() for qid in values}
    groups, texts = {}, {}
    evidence_records = dataset.get("evidence", {})
    if not isinstance(evidence_records, dict):
        raise ValueError("evidence must be an object")
    for evidence_id, evidence in evidence_records.items():
        _text(evidence, "source_url")
        _text(evidence, "method")
        _evidence_file(dataset_path.parent, evidence, "raw")
        texts[evidence_id] = _evidence_file(dataset_path.parent, evidence, "text").decode("utf-8")
    for question in questions:
        group = _text(question, "leakage_group")
        name = membership[question["id"]]
        if groups.setdefault(group, name) != name:
            raise ValueError("related questions cross the working/closed split")
        if _text(question, "query_class") not in QUERY_CLASSES:
            raise ValueError("unsupported query class")
        if not isinstance(question.get("disputed"), bool):
            raise ValueError("disputed must be explicitly true or false")
        expected = question.get("expected", {})
        for field in ("act", "address", "edition_claim", "expected_value"):
            _text(expected, field)
        if expected["act"] not in PILOT_ACTS:
            raise ValueError("expected act is outside the pilot")
        spans = expected.get("spans")
        if expected.get("outcome") == "no_answer":
            _text(expected, "reason")
            if spans != [] or question.get("task_scope") != "applicability":
                raise ValueError("no-answer label must have empty spans and applicability scope")
            gaps = expected.get("gap_evidence")
            if not isinstance(gaps, list) or not gaps or not set(gaps) <= set(texts):
                raise ValueError("no-answer label requires archived gap evidence")
        elif expected.get("outcome") == "source_span":
            if question.get("task_scope") != "source_snapshot" or not isinstance(spans, list) or not spans:
                raise ValueError("positive labels require source_snapshot scope and evidence spans")
            for span in spans:
                text = texts.get(_text(span, "evidence_id"))
                start, end = span.get("start"), span.get("end")
                if (text is None or type(start) is not int or type(end) is not int
                        or not 0 <= start < end <= len(text)
                        or text[start:end] != _text(span, "quote")):
                    raise ValueError("source span does not match archived text")
                if expected["act"] not in evidence_records[span["evidence_id"]].get("acts", []):
                    raise ValueError("span evidence is not associated with the expected act")
        else:
            raise ValueError("outcome must be source_span or no_answer")
    if {q["query_class"] for q in questions} != QUERY_CLASSES:
        raise ValueError("query-class coverage is incomplete")
    for name, values in members.items():
        if {q["expected"]["act"] for q in questions if q["id"] in values} != PILOT_ACTS:
            raise ValueError(f"{name} split must cover all five pilot acts")
    reviewed = set()
    review = _read(review_path) if review_path else None
    if review is not None:
        if review.get("dataset_sha256") != digest(dataset) or review.get("split_sha256") != digest(split):
            raise ValueError("review does not bind the exact dataset and split")
        approvals = {qid: [] for qid in ids}
        blocked = set()
        for decision in review.get("decisions", []):
            if _text(decision, "reviewer_role") != "Legal Reviewer":
                raise ValueError("only a Legal Reviewer may decide gold labels")
            reviewer = _text(decision, "reviewer_id")
            _text(decision, "rationale")
            if datetime.fromisoformat(_text(decision, "decided_at").replace("Z", "+00:00")).utcoffset() is None:
                raise ValueError("decided_at must include a UTC offset")
            scope = decision.get("question_ids")
            if not isinstance(scope, list) or not scope or len(set(scope)) != len(scope) or not set(scope) <= set(ids):
                raise ValueError("review scope must name known unique question IDs")
            if decision.get("decision") not in {"reviewed", "rejected", "disputed"}:
                raise ValueError("unsupported review decision")
            for qid in scope:
                if decision["decision"] == "reviewed":
                    if reviewer not in approvals[qid]:
                        approvals[qid].append(reviewer)
                else:
                    blocked.add(qid)
        for question in questions:
            qid = question["id"]
            first = approvals[qid][0] if approvals[qid] else None
            independent = any(r not in {first, dataset["label_author"]} for r in approvals[qid][1:])
            if qid not in blocked and first and (not question["disputed"] or independent):
                reviewed.add(qid)
    return {
        "dataset": dataset, "split": split, "review": review,
        "summary": {
            "dataset_sha256": digest(dataset), "split_sha256": digest(split),
            "question_count": len(ids), "split_counts": {k: len(v) for k, v in members.items()},
            "query_classes": dict(sorted(Counter(q["query_class"] for q in questions).items())),
            "reviewed_count": len(reviewed), "pending_count": len(ids) - len(reviewed),
            "storage_approved": bool(review and review.get("storage_approved") is True),
        },
    }


def freeze(records: dict, path: Path) -> str:
    summary = records["summary"]
    if summary["pending_count"] or not summary["storage_approved"]:
        raise ValueError("freeze requires all labels reviewed and explicit storage approval")
    payload = _bytes({"schema_version": "frozen-gold-set/1", **{k: records[k] for k in ("dataset", "split", "review")}})
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(name, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError("frozen gold set cannot be overwritten") from None
            return "unchanged"
        return "new"
    finally:
        Path(name).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args(argv)
    try:
        records = validate(args.dataset, args.split, args.review)
        summary = records["summary"]
        if args.freeze:
            path = args.dataset.parent / "frozen.json"
            summary.update(result=freeze(records, path), frozen_path=str(path.resolve()))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
