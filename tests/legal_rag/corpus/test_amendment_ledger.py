from copy import deepcopy
import sys
from pathlib import Path

import pytest

from legal_rag.corpus.amendment_ledger import bind_operations, check_review
from legal_rag.corpus.compiler import content_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "docs/assets"))
from build_m1_07_sanpin_ledger import quoted_payload, span  # noqa: E402

ROOT = "act/owner/A"
POINT = ROOT + "/5"
TEXT = "act/content/4"
INSERTED = ROOT + "/5(1)"
DATES = ["2025-01-01", "2026-10-01"]


def node(address, parent, kind, children=(), text=""):
    return {"address": address, "parent_address": parent, "kind": kind, "children": list(children), "text": text}


def operation(op_id, kind, target, owner, payload, requires=()):
    return {"id": op_id, "kind": kind, "target": target, "owner": owner, "payload": payload,
            "requires": list(requires), "evidence": [{"address": "fixture/" + op_id, "locator": "fixture"}],
            "effect": {"start": "2025-01-01"}}


@pytest.fixture
def proposal():
    original = {"nodes": [node(ROOT, "act", "act", [POINT]), node(POINT, ROOT, "point", [TEXT]),
                          node(TEXT, POINT, "text", text="Text 2025.")]}
    operations = [
        operation("insert", "insert_after", POINT, "A", {"address": INSERTED, "number": "5(1)", "text": "5(1). New."}),
        operation("edit-new", "replace_text", INSERTED + "/text", "A/5(1)",
                  {"before": "New", "after": "Updated"}, ["insert"]),
        {**operation("edit-old", "insert_text", TEXT, "A/5", {"before": "", "after": " test"}),
         "position": "before_final_punctuation", "punctuation": ".", "paragraph": 1},
        operation("delete", "delete_unit", POINT, "A", None, ["edit-old"]),
    ]
    return original, operations


def test_binds_before_payload_and_chained_subtree_without_changing_source(proposal):
    before = deepcopy(proposal)
    insert, edit_new, edit_old, delete = bind_operations(*proposal)
    assert proposal == before
    assert insert["expected_before"]["absent_text_address"] == INSERTED + "/text"
    assert edit_new["range"] == [6, 9]
    assert edit_new["expected_before"]["nodes"][0]["text"] == "5(1). New."
    assert edit_old["range"] == [9, 9]
    assert [n["text"] for n in delete["expected_before"]["nodes"]] == ["", "Text 2025 test."]
    assert delete["expected_before"]["sha256"] == content_hash(delete["expected_before"]["nodes"])


@pytest.mark.parametrize(("op", "edit", "error"), [
    (0, {"payload": {"address": POINT, "number": "5", "text": "5. New."}}, "occupied"),
    (0, {"evidence": []}, "missing operation evidence"),
    (1, {"requires": []}, "missing dependency"),
    (1, {"requires": ["delete"]}, "forward dependency"),
    (1, {"payload": {"before": "Absent", "after": "Text"}}, "text precondition"),
    (2, {"owner": "S/5"}, "target owner mismatch"),
    (2, {"paragraph": 2}, "paragraph number differs"),
    (2, {"position": "unknown"}, "unknown insertion boundary"),
    (3, {"requires": []}, "missing dependency"),
    (3, {"kind": "renumber"}, "unsupported operation"),
])
def test_refuses_unbound_or_unsupported_operations(proposal, op, edit, error):
    proposal[1][op].update(edit)
    with pytest.raises(ValueError, match=error):
        bind_operations(*proposal)


@pytest.fixture
def reviewed(proposal):
    operations = bind_operations(*proposal)
    operations[3]["effect"] = {"start": "2026-10-01"}
    ledger = {"target_dates": DATES, "operations": operations, "primary_legal_reviewer": "fixture-lawyer",
              "original": {"ast_sha256": "authored test only"}}
    review = {"schema_version": "amendment-ledger-review/1", "ledger_sha256": content_hash(ledger),
              "reviewer": "fixture-lawyer", "role": "Legal Reviewer", "reviewed_at": "2026-11-11T12:00:00+05:00",
              "rationale": "authored test only", "operations": dict.fromkeys((op["id"] for op in operations), "confirmed"),
              "dates": {date: {"complete": "confirmed", "rationale": "fixture",
                               "dispositions": {op["id"]: {"status": "include" if date >= op["effect"]["start"]
                                                            else "not_yet_effective", "rationale": "fixture"}
                                                for op in operations}} for date in DATES}}
    return ledger, review


def test_two_dates_require_separate_human_decisions(reviewed):
    ledger, review = reviewed
    assert check_review(ledger) == dict.fromkeys(DATES, "awaiting_legal_review")
    assert check_review(ledger, review) == dict.fromkeys(DATES, "reviewed_for_reconstruction")
    review["dates"][DATES[1]]["complete"] = "unresolved"
    assert check_review(ledger, review) == {DATES[0]: "reviewed_for_reconstruction", DATES[1]: "unresolved"}
    review["dates"][DATES[0]]["dispositions"]["delete"]["status"] = "include"
    with pytest.raises(ValueError, match="conflicts with ledger date"):
        check_review(ledger, review)


@pytest.mark.parametrize("change", ["payload", "ast", "evidence"])
def test_review_invalidated_by_edits(reviewed, change):
    ledger, review = reviewed
    if change == "ast":
        ledger["original"]["ast_sha256"] = "different tree"
    else:
        ledger["operations"][0][change] = "changed operation"
    with pytest.raises(ValueError, match="different ledger"):
        check_review(ledger, review)


def test_rejects_unassigned_reviewer_and_missing_dependency(reviewed):
    ledger, review = reviewed
    with pytest.raises(ValueError, match="assigned Legal Reviewer"):
        check_review(ledger, {**review, "reviewer": "engineer"})
    review["dates"][DATES[0]]["dispositions"]["insert"].update(
        status="outside_scope", basis={"operation_id": "insert", "address": "fixture/insert"})
    with pytest.raises(ValueError, match="lacks its predecessor"):
        check_review(ledger, review)


def test_scope_exclusion_requires_official_evidence(reviewed):
    ledger, review = reviewed
    row = review["dates"][DATES[1]]["dispositions"]["delete"]
    row.update(status="outside_scope", basis={"operation_id": "delete", "address": "mispointed"})
    with pytest.raises(ValueError, match="no bound official evidence"):
        check_review(ledger, review)
    row["basis"]["address"] = "fixture/delete"
    assert check_review(ledger, review)[DATES[1]] == "reviewed_for_reconstruction"


def test_disagreement_needs_independent_bound_record(reviewed):
    ledger, review = reviewed
    second = {**deepcopy(review), "first_review_sha256": content_hash(review)}
    with pytest.raises(ValueError, match="independent"):
        check_review(ledger, review, second)
    second["reviewer"] = "fixture-second-lawyer"
    second["operations"]["insert"] = "rejected"
    assert check_review(ledger, review, second) == dict.fromkeys(DATES, "disputed")
    review["operations"]["insert"] = "disputed"
    assert check_review(ledger, review) == dict.fromkeys(DATES, "independent_legal_review_required")
    with pytest.raises(ValueError, match="bind the first"):
        check_review(ledger, review, second)


def test_evidence_stays_in_its_pdf_and_keeps_nested_quotes():
    entry = {"address": "source/leaf", "node_id": "fixture", "kind": "text", "text": "«Text «quoted».».",
             "source_spans": [{"source_asset_sha256": "fixture", "locator": "ocr:fixture", "page": 2}]}
    assert span(entry, "fixture")["spans"] == entry["source_spans"]
    assert quoted_payload(entry["text"]) == "Text «quoted»."
    with pytest.raises(ValueError, match="missing text or PDF spans"):
        span(entry, "wrong")
    with pytest.raises(ValueError, match="ambiguous quoted payload"):
        quoted_payload("Insert «Two» and «two»")
    with pytest.raises(ValueError, match="invalid outer quotation"):
        quoted_payload("«Two» and «two».")
