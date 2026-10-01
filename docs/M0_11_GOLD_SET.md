# M0-11 — gold-question set v2

**Rebuilt:** 1 October 2026

**Status:** draft; 30 labels and the local-storage decision await Legal Reviewer approval. M0-12 remains blocked.

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
local `full-audit.md` records the result for every ID. Existing human `ОК` marks
on the five unchanged working questions were preserved; all labels still await
completion of the Legal Reviewer gate.

| Query class | Count |
|---|---:|
| Exact reference | 6 |
| Paraphrase | 7 |
| Exception or negation | 8 |
| Confirmed date | 2 |
| Missing coverage | 5 |
| Cross-reference | 2 |

## Split and retained files

The local packet is `data/m0-11-gold/`. It contains:

- `working.json` and `working-review.md` — 15 questions available only after legal approval for implementation-time evaluation;
- `closed.json` and `closed-review.md` — 15 questions reserved for the gate;
- `dataset.draft.json`, `split.json`, retained evidence and `review.template.json` — authoring and review material;
- `verification.json` — the recorded hashes and structural checks.

[The tracked manifest](M0_11_GOLD_SPLIT.json) fixes the 15/15 membership and the
SHA-256 of the complete, working, closed and split JSON files. It deliberately
contains no query text or labels. No runtime validator or synthetic gold test is
needed: this is review data, not production corpus behavior.

## Remaining human gate

The designated `legal-reviewer-owner` must review every question, answer or
refusal, act/address, edition claim and source span; record actual review time;
and approve or reject local private storage. A disputed label requires a second
Legal Reviewer who is neither the author nor the first reviewer.

Until that happens:

- no label is legally approved;
- neither split may be used to claim retrieval quality;
- the closed labels must not be used for parser, retrieval or prompt tuning;
- M0-11 and M0-12 remain incomplete.
