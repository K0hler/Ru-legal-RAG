# M1-03: full native-text diagnostic compilation of 59-FZ

**14 October 2026 update:** the original act-bound traversal below is superseded by the [shared M1-03A engine](03a/M1_03A_SHARED_STRUCTURE.md). Previous artifacts remain immutable; the existing command is retained as an adapter.


**Implemented:** 12 October 2026. **Scope:** the owner-permitted retained
59-FZ input at the diagnostic target `2026-10-01`. Engineering completion
does not establish historical coverage, applicability or legal admission.

## Implemented profile

The existing `python -m legal_rag.corpus compile` command now accepts the
saved JSON response with an explicit `$.redtext` or `/redtext` evidence
locator. `actual-redtext-html/1` reads that scalar and its HTML text nodes
using the standard library. A source error, missing/empty scalar, unsupported
format, wrong locator or incomplete/unbalanced HTML fails before derived
writes. Permission, raw hashes, source-item membership and immutable-output
checks remain the M1-01 checks. No acquisition adapter or frozen handoff changed.

`native-59-structure/1` establishes the act identity before creating legal
addresses: the law type/title must occur before the first article; the exact
59-FZ number and signing date must be unique within the final presidential
signing block. A matching number elsewhere cannot override a conflicting signature.
Unknown identity leaves substantive content unresolved. This is a bound
59-FZ profile, not a parser for arbitrary laws.

The ordered diagnostic AST includes headers, articles, numbered parts,
numbered items, lettered nested items, unnumbered paragraphs and separate
notes. HTML `mark`/`markx` annotations are retained, including amendment and
application notes. Source-marked superscripts (`sup` and this profile's `W9`
class) produce distinct addresses such as `act/article/11/part/5.1` while
the visible source spelling `51.` remains unchanged. Duplicate addresses,
unknown boundaries/numbering, multiple provision markers separated by a line
break inside one paragraph, and unsupported HTML lists/tables stay visible
and stop targeting until a new recognized boundary. PDF/table qualification
belongs to later slices.

Standalone notes have document-level addresses; only notes in the same source
paragraph as a recognized provision inherit that provision's address. Proximity
to an earlier header is not evidence of a note's legal scope.

## Coordinates and accounting

Each `text-extraction/1` text/entity token records its raw HTML spelling,
decoded text, source hash, JSON pointer `/redtext`, HTML text location and
half-open Unicode offsets **inside the decoded JSON scalar**. Native pages
are null; there are no invented physical pages or raw JSON byte offsets.
A `br`, when present, is explicitly recorded as a structural break token.

Paragraph groups retain decoding mappings to the original tokens. Cleanup
only collapses Unicode whitespace and trims group edges; every consumed
decoded range has an ordered before/after mapping. It neither changes
non-whitespace characters nor performs legal corrections. AST blocks refer
to those tokens and extraction groups. Every token is assigned exactly once
to parsed content, unresolved content or explicit exclusion: whitespace,
non-document head/style/script text, or the portal's label control. Legal
headers, signatures and meaningful notes are retained.

The offline HTML report has a disclosure for every native AST block, opening
its original text and escaped HTML excerpt beside its exact scalar locator.
Source HTML is displayed as text and never executed. Original status,
processing permission, questions and all inherited admission blockers remain
visible. The earlier M1-02 manifest is read-only; its earlier pending-work
question is preserved as input history rather than edited in place.

## Retained full-text verification

Input: `data/m1/inputs/m1-02-permitted/federal-law-59-2026-10-01.json`.
Source SHA-256:
`7aeb1a26b3b099f2ae73b07377afc31fcc9d238d6eb4ecea6b962c5d9477b889`.

Engineering verification is retained in
`data/m1/pilot_runs/m1-03/verification-v4.json`. It records Python 3.13.12,
independent `new` builds and an immutable `unchanged` repeat, exact artifact
comparison, all locator/cleanup/accounting checks and 117 unchanged archive
files. Full documents and derived records remain local and ignored.

| Observed class | Count |
|---|---:|
| Articles | 18, ordered 1 through 18 |
| Parts | 50 |
| Numbered items | 21 |
| Unnumbered paragraphs | 6 |
| Notes | 24 |
| Headers/signature fields | 9 |
| Source tokens | 293; each accounted exactly once |
| Unresolved source tokens | 0 for this retained input |

Of 48,105 source token characters, 28,019 belong to parsed document content
and 20,086 to explicitly excluded service/whitespace tokens. All
non-whitespace decoded characters in document blocks survive cleanup.
Zero structural exceptions is an engineering result, not an admission gate.

Draft ID: `f1e21488b43572ce5a4caa83138076aef531ff1dcc67cb0a739a0e5651f5b5c5`.
Content hash: `13fcd6e50937f3a07432a67428e83d2b6d31c234c284c36e79ad7fbb62da9e52`.
Extraction ID: `987d0ee4977e29d80ae13da52d9a09f5566a73481f40231e690eb0d50227cf87`.
Report:
`data/m1/pilot_runs/m1-03/native-control-v4/drafts/<draft-id>/report.html`.
The independent build is under `native-control-independent-v4`; earlier
development outputs are retained separately.

## Replay and tests

Use Python 3.13 and the existing compiler arguments:

```powershell
$env:PYTHONPATH = "src"
python -m legal_rag.corpus compile --input data/m1/inputs/m1-02-permitted/federal-law-59-2026-10-01.json --target-date 2026-10-01 --output-dir data/m1/pilot_runs/m1-03/native-control-v4
python -m unittest discover -s tests/legal_rag/corpus -p "test_*.py" -v
python -m unittest discover -s tests/legal_rag/sources -p "test_*.py" -v
python docs/assets/generate_m0_gate.py
```

Eight focused native tests use project-authored synthetic HTML and a literal
expected tree. They cover source/entity/cleanup coordinates, nested addresses,
superscripts, sibling paragraphs, retained notes, identity conflicts, duplicate
addresses, unknown numbering/tables, service text, source failures, immutable
repeat and refusal of the undeclared historical target. Closed gold is unused.

The final independent code review found three structure/identity issues:
standalone-note scope, ambiguous numbering/breaks and a signature conflict
masked by a matching body number. Each was reproduced by a failing synthetic
case and corrected. Browser QA records actual original-source opening, including
an opening after the temporary local server was stopped; source HTML is inert.
Final results: 69 offline corpus/source tests pass; Ruff, bytecode compilation,
the unchanged M1-01 fixture replay and the regenerated M0 gate (`78/78`, no
evidence problems) pass. The final browser record is
`data/m1/pilot_runs/m1-03/report-browser-qa-v4.json`.

The original M0 source and candidate blockers are deliberately retained.
M1-02's separately confirmed `19-P-after-80-FZ` classification is not imported
as a runtime applicability relation by this slice. M1-11 must reconcile that
evidence and both dated editions; final admission remains M1-12/M1-13 work.
