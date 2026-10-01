# M0-11 — gold-question review packet and freeze gate

**Prepared:** 30 September 2026

**Status:** technical preparation implemented and verified; legal label review
and local-storage approval are pending. M0-11 is not complete and does not
unblock M0-12.

## Retained dataset

The local packet is `data/m0-11-gold/` in the main checkout. It contains 40
project-authored Russian questions: eight per pilot act, with 20 working and 20
closed questions. The membership is recorded before retrieval tuning in
[the tracked split](M0_11_GOLD_SPLIT.json). The tracked split contains IDs only,
not queries or labels. Related questions share a leakage group and cannot cross
the split.

| Query class | Count |
|---|---:|
| Exact reference | 10 |
| Paraphrase | 10 |
| Exception or negation | 7 |
| Confirmed date in the cited original source | 2 |
| Missing coverage or decisive facts | 8 |
| Explicit cross-reference | 3 |

The draft dataset SHA-256 is
`40f612caf42bfce35de79572245f50856433ac244dd71533a7e3bea890edc467`.
The canonical split SHA-256 is
`b6528c5be031aa248e670b914f225cbcdeff0129e0cc3f7683ac36e602a59d6f`.
Working-question wording was revised during human review on 1 October 2026;
source spans, split membership and existing reviewer annotations were preserved.
These hashes use UTF-8 JSON, sorted keys, two-space indentation and a trailing
newline, as implemented by `legal_rag.corpus.gold.digest`.

## Scope of labels

M0-10 admitted no pilot candidate without a blocker. Therefore positive
`source_span` labels test finding text in a named **archived source snapshot**,
including a rejected or stale snapshot when the question explicitly names it.
They do not approve a `LegalEdition`, establish present applicability, or
override candidate invalidation. The eight `no_answer` labels test refusal or
clarification where the requested applicability cannot be established.

Each question records its query class, task scope, expected act/address,
edition claim, proposed answer or explicit refusal reason, and dispute state.
A positive span names a retained text asset and its zero-based, half-open Unicode
character interval. Its exact quote must match that interval. Every text asset
also records the original raw SHA-256, source URL, extraction/transcription
method and physical PDF page where applicable. A no-answer label instead names
the retained M0-10 gap/review evidence and has no invented text span.

HTML text was extracted from the retained raw JSON with the standard-library
HTML parser. Selected PDF paragraphs were transcribed and compared with rendered
physical pages of the SanPiN original and Resolution No. 1242. These are
**review-only derivatives**, not the M1 extractor, Legal AST or proof of complete
document text accounting. The human reviewer still checks the proposed labels
and evidence coordinates.

## Review and storage decision

The packet entry point is `data/m0-11-gold/README.md`. Its separate
`working-review.md` and `closed-review.md` show each question, proposed label,
source quote or refusal evidence, and a space for the reviewer's decision.
`dataset.draft.json` is the complete reviewer/gate input; `working.json` contains
only the 20 working questions and their necessary evidence records.

The existing designated Legal Reviewer is `legal-reviewer-owner`; M0-10 review
does not automatically approve these new labels. Each review decision must name
the reviewer, `Legal Reviewer` role, offset-aware decision time, rationale and
question IDs. A review file binds the exact dataset and split hashes, so an
edited query, label, evidence record or membership requires a new decision.
Disputed labels need agreeing decisions from a first reviewer and another
reviewer who is neither the label author nor the first reviewer. Rejected or
disputed decisions block freezing; they are not silently replaced by approval.

Proposed storage/licensing scope: **local private evaluation only**. Questions
and labels are project-authored. Evidence consists of retained official assets,
review-only derivatives and the project's human review record; no commercial
aggregator exports or private case files are included. No public redistribution
licence is granted. Source-service access remains subject to the approved M0-07
bounded-pilot policy. The reviewer must explicitly approve this local scope via
`storage_approved: true`; until then storage approval is pending.

## Verification and freeze

```powershell
$env:PYTHONPATH = "src"
python -m legal_rag.corpus.gold `
  --dataset data/m0-11-gold/dataset.draft.json `
  --split docs/M0_11_GOLD_SPLIT.json

# Only after actual human decisions are recorded in review.json:
python -m legal_rag.corpus.gold `
  --dataset data/m0-11-gold/dataset.draft.json `
  --split docs/M0_11_GOLD_SPLIT.json `
  --review data/m0-11-gold/review.json --freeze

python -m unittest discover -s tests/legal_rag/corpus -p 'test_*.py' -v
```

Default validation reports counts and hashes, not queries or labels. It checks
30-50 unique questions, required query classes, five-act coverage in both splits,
disjoint/fixed membership, leakage groups, raw/text hashes, evidence paths,
act association and exact span coordinates. Freeze also requires every label to
pass review and explicit storage approval. It atomically creates `frozen.json`
without overwriting a different snapshot; identical replay is `unchanged`.

The retained preparation ran `new`, then `unchanged` with identical hashes.
Validation reports 40 pending labels, zero reviewed labels and storage approval
false. An attempted freeze correctly failed and created no `frozen.json`.
Synthetic offline regression covers review authority, independent second review,
corrupt/missing/mispointed evidence, altered review hashes, invalid coordinates,
split leakage, no-answer evidence and immutable freeze/replay. Actual labels are
not used by automated tests.

## Closed-set handling and remaining gate

All query/label files and raw assets remain ignored local data. Only the schema
validator, synthetic test, ID membership and this status document enter Git.
During parser/retrieval implementation or tuning, read **only** `working.json`
after its labels receive legal approval. Complete drafts, review packets,
`prepare.py` and frozen snapshots are for dataset authoring/legal review or
explicit gate evaluation; do not print their closed labels into tuning chats.
This is a process boundary, not an implemented ACL or evaluation service.

M0-11 can close only after the reviewer checks all 40 questions, approves the
local storage scope, resolves any disputes under M0-07 and freezes the reviewed
snapshot. Snapshot-lookup and applicability/refusal tasks must remain separate
when later milestones report metrics. The existing corpus-admission blockers
remain in force.
