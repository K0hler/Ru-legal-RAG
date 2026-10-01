# M0-11 — gold-question set v2

**Rebuilt:** 1 October 2026

**Status:** complete; all 30 labels are `reviewed`, the two-hour Legal Reviewer
check is recorded, and local private storage is approved. M0-12 is unblocked.

## What changed

Version 1 was discarded. It mostly tested commands such as “find this clause in
the archived text” and added a production validator for a private review file.
That did not provide a useful parser/retrieval benchmark.

Version 2 contains 30 user-shaped Russian legal queries: six for each pilot act.
Every positive label still points to an exact span in a retained source snapshot;
every `no_answer` label points to an unresolved M0-10 coverage or applicability
gap. A positive snapshot label does not approve a `LegalEdition` or establish
that the cited text governs a particular dispute.

A second full author audit checked all 30 records against one checklist and
corrected 14 of them. The corrections separate refusal causes, narrow questions
to the cited provisions, remove evaluator instructions from expected answers,
restore omitted legal conditions, and tighten one overlong evidence span. The
local `full-audit.md` records the result for every ID.

The subsequent Legal Reviewer pass established that a user-shaped query must
not disclose the gold article, part, clause, subclause, or annex merely as a
lookup hint. Ten queries were rewritten accordingly. Here `exact_reference`
means that the hidden label resolves to one exact provision; it does not mean
that the query contains that provision's address. Every rewritten record was
returned to pending review and subsequently rechecked. The final review accepts
all 30 labels.

| Query class | Count |
|---|---:|
| Exact single-provision target | 6 |
| Paraphrase | 7 |
| Exception or negation | 8 |
| Confirmed date | 2 |
| Missing coverage | 5 |
| Cross-reference | 2 |

## Split and retained files

The local packet is `data/m0-11-gold/`. It contains:

- `working.json` and `working-review.md` — 15 reviewed questions available for implementation-time evaluation;
- `closed.json` and `closed-review.md` — 15 questions reserved for the gate;
- `dataset.draft.json`, `split.json`, retained evidence and `review.template.json` — authoring material and the blank review template;
- `review.json` — the completed Legal Reviewer decisions, time and storage approval;
- `verification.json` — the recorded hashes and structural checks.

[The tracked manifest](M0_11_GOLD_SPLIT.json) fixes the 15/15 membership and the
SHA-256 of the complete, working, closed, split and review JSON files. It
deliberately contains no query text or labels. No runtime validator or synthetic
gold test is needed: this is review data, not production corpus behavior.

## Completed human gate

- Reviewer: `legal-reviewer-owner` (`Legal Reviewer`).
- Decision time: 1 October 2026 at 19:54:03 UTC+05:00.
- Review effort including corrections: 120 minutes.
- Decisions: 30 `reviewed`, 0 `rejected`, 0 pending.
- Storage: approved for private local evaluation; no public redistribution.
- Disputes: none remain, so no independent second review is required.

The approval is bounded:

- working labels may be used for implementation-time evaluation;
- closed labels must not be used for parser, retrieval or prompt tuning;
- positive snapshot labels do not remove the separate M0-10 admission blockers;
- M0-11 is complete; M0-12 reporting is now implemented. The separate
  [M0 gate](M0_GATE_REPORT.md) blocks M1 on M0-10's missing timing measurements.
