# M1-03A: shared native legal structure

**Status: reopened / incomplete, 14 October 2026.** The previous statement
that M1-03A was complete is withdrawn. The implemented federal-law/code
component passes its recorded checks, but only **two of the four original
retained HTML documents** pass the complete compiler path. Additional transfer
documents do not replace this acceptance set. No legal edition is admitted.

## Mandatory original-input acceptance

| Original retained input | HTML preparation | Complete legal structure |
|---|---|---|
| 59-FZ | pass | pass |
| Housing Code | pass | pass |
| Government Resolution No. 354 | pass | fail: `/doctext` and resolution structure unsupported |
| Government Resolution No. 491 | pass | fail: `/doctext` and resolution structure unsupported |

Current evidence: `data/m1/pilot_runs/m1-03a-original-four-status-v1/acceptance.json`.
The actual compiler calls give **fail, 2/4**, not stage completion. Closing
M1-03A requires full parsing of all four through the common pipeline, including
the hierarchy of approved texts/annexes, source accounting and explicit
table/formula/image handling. Renaming preservation or subset transfer results
as full acceptance is not permitted. Passing this minimum set does not replace
the independent transfer checks for every declared native family/format.

## Implementation

`corpus/structure.py` provides one traversal, `legal-structure/4`, with
`federal-law/4` and `code/4` identity profiles. It consumes extracted blocks,
not HTML tags. Number, signing date and title come from source evidence and
are compared with the input claim. Neither profile selects documents by act
number, date, title, filename or hash. Decorative title case is normalized
for comparison; the original title remains in the evidence.

`native_text.py` retains the saved JSON `/redtext` adapter and delegates HTML
tokenization to the existing raw HTML adapter in `housing_html.py`.
`actual-redtext-html/2` produces `text-extraction/1`; positions remain Unicode
characters in the original decoded JSON scalar, bound to the original JSON
asset hash. The raw diagnostic command keeps its previous output envelope
and delegates the same engine. Its optional `--identity` checks an explicit
claim; without it, identity is source-only rather than an implicit 188-FZ
allowlist. A conflicting claim remains unresolved.

The tree includes sections, chapters, chapter paragraphs (`§`, `subchapter`),
articles, parts, items, subitems, diagnostic unnumbered paragraphs and notes.
It preserves decimal, source-marked superscript and hyphenated numbering,
Roman chapter numbers, and upper/lower-case heading labels. Repeated `§ 1`
in different chapters has distinct addresses. HTML presentation classes are
hints, not legal levels. A line break separates a heading label from its title;
several provision markers inside one source paragraph remain ambiguous.

Each source token is parsed, unresolved or explicitly excluded exactly once.
Unsupported image/table/list regions remain visible. Both unresolved text
and regions add the compiler's `unresolved_structure` blocker. Unknown or
duplicate boundaries clear provision context. Editorial notes retain their
source claims; standalone note scope and legal effect stay unresolved.

The optional [HTML preparer](HTML_PREPARATION.md) remains useful to generic
readers. The native adapter reads the original HTML to retain complete token
coordinates: the preparer's opening-tag map alone cannot provide these.
The legal engine has no new runtime dependency and does not require Docling
or Dedoc. PDF/OCR adapters remain M1-04 work.

## Retained development controls

`data/m1/pilot_runs/m1-03a-shared-v4/verification.json` records two fresh
compiler builds and a same-directory repeat for 59-FZ and the Housing Code.
All 222 protected source/previous-artifact files stayed unchanged.

| Input | Sections | Chapters | Articles | Parts | Items | Notes | Unresolved text/regions |
|---|---:|---:|---:|---:|---:|---:|---:|
| 59-FZ | 0 | 0 | 18 | 50 | 21 | 24 | 0 / 0 |
| Housing Code | 12 | 21 | 243 | 1,085 | 683 | 996 | 0 / 0 |

All reviewed previous addresses, parents, text and character ranges agree,
with one documented correction: Housing Code article 44 part 2 item `1¹-1)`
was previously a continuation paragraph of item `1¹)`. It now has address
`act/article/44/part/2/item/1.1-1`; its inline note follows that item. Original
visible digits and source coordinates are unchanged. The report contains
the two affected before/after node records. All 243 article numbers/HTML
anchors also match the previously prepared independent controls.

## Partial evidence: frozen federal-law/code transfer

Federal-law/code evidence is retained under
`data/m1/pilot_runs/m1-03a-transfer-v4-controls-v2/`:
`freeze.json`, `controls/*.json`, per-act `result.json`, two complete builds,
offline reports and `parser-transfer-report.json` (`parser-transfer-report/1`).
The original hash-bound source assets, cards, permissions and input manifests
are in the sibling `m1-03a-transfer-v4/` acquisition directory.

| Family | Distinct non-pilot input | Articles | Structural exceptions | Fresh builds / repeat |
|---|---|---:|---:|---|
| Federal law | 25.12.2008 No. 273-FZ, countering corruption | 30 | 0 | identical / unchanged |
| Federal law | 06.03.2006 No. 35-FZ, countering terrorism | 29 | 0 | identical / unchanged |
| Code | 29.12.2004 No. 190-FZ, Town Planning Code | 144 | 0 | identical / unchanged |
| Code | 08.03.2015 No. 21-FZ, Administrative Judicial Procedure Code | 427 | 0 | identical / unchanged |

The declared source format is actual.pravo native HTML inside saved
`/redtext` JSON. Independent DOM controls were generated before AST runs
without importing the legal engine. They check every normative paragraph's
text, numbering, parent, address and order, plus every editorial note.
Separate source/token/region integrity checks and two fresh output-file hash
comparisons supplement these controls. This is engineering syntax validation,
not an independent human legal admission decision.

Previous failures were retained rather than promoted after tuning:
version 1 found hyphenated superscripts in Water/Forest codes; version 2
found uppercase Roman chapters in Land/Air codes; version 3 found chapter
paragraphs in the Arbitration Procedure Code. Every changed version used
four different reserved acts. The final independent reference initially
omitted `<br/>` whitespace and misclassified KAS section headings; its
original failed report is retained. Only that reference was corrected in
`controls-v2`; the frozen production code and validation cohort did not change.

`m1-03a-shared-v4/former-failure-replays.json` also records successful full
replays of those five former code failures with the final engine and corrected
independent controls. They remain development regressions, not fresh transfer
qualification. Synthetic tests cover identity conflicts, chapter scoping,
superscripts/hyphens, uppercase and ambiguous break boundaries, textual notes,
unsupported tables and region-only blockers.

## Verification and limits

Checks at commit `c97831e`: **166 tests passed** across the complete default
suite; Ruff passed; M0 gate passed all **78** criteria with no evidence problems.
The final transfer report SHA-256 is
`787caa154894b8bd7188ad8983ec989294235d2fbb0ad0ccdbf7b692edd51f24`.
All four frozen code hashes still match. The final transfer's 36 source records
and the development replay's 222 protected files remain unchanged.

Run the corpus tests, `test_candidate_handoff.py`, `test_m0_gate.py`, Ruff,
the retained verification scripts, then `python docs/assets/generate_m0_gate.py`.
The frozen M0 adapters/handoff are unchanged. Raw archives, previous drafts,
rejected/stale statuses and original admission blockers remain intact.

These checks qualify the recorded federal-law/code subset, not M1-03A as a
whole. They do
not guarantee arbitrary HTML, infer missing structure, implement other act
families, resolve every editorial note's scope, reconstruct historical
editions or establish legal applicability. Unsupported structures remain
explicit exceptions and cannot pass this transfer protocol.
