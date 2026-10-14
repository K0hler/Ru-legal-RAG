# M1-03A: shared native legal structure

**Status: implemented and verified for the declared native grammar, 14 October 2026.**
All four original retained HTML documents pass the complete compiler path, and
the native transfer matrix passes two non-pilot acts per family/format. These
are distinct acceptance checks. No legal edition is admitted.
The previous premature closure and corrected 2/4 failure remain in the history.

## Mandatory original-input acceptance

| Original retained input | HTML preparation | Complete legal structure |
|---|---|---|
| 59-FZ | pass | pass |
| Housing Code | pass | pass |
| Government Resolution No. 354 | pass | pass |
| Government Resolution No. 491 | pass | pass |

Current evidence: `data/m1/pilot_runs/m1-03a-original-four-v8/acceptance.json`:
**pass, 4/4**. Each input has two fresh full compiler builds with identical files
and IDs, plus an unchanged repeat. All 345 protected source/previous-artifact
files remain unchanged. Independent DOM markers/parent controls supplement
token/region checks; the original laws/codes retain their reviewed semantic
structure. Earlier `original-four-status-v1` (2/4) and failed `original-four-v5`
are preserved. Preparation checks do not replace these compiler runs.

| Resolution | Approved texts | Annexes | Sections | Points | Letter subitems | Images |
|---|---:|---:|---:|---:|---:|---:|
| No. 354 | 2 | 5 | 45 | 416 | 387 | 93 |
| No. 491 | 2 | 1 | 5 | 83 | 76 | 6 |

No. 354 also retains the table's 28 rows / 64 cells, seven footnotes, a
substantive annex-scoped note and a separate numbered normative-notes section.
Counts include quoted provisions inside changes; their addresses are scoped to
the quotation, never confused with the approving resolution's own provisions.

## Implementation

`corpus/structure.py` provides one traversal, `legal-structure/7`, with
`federal-law/5`, `code/5` and `government-resolution/3` identity profiles. It consumes extracted blocks,
not HTML tags. Number, signing date and title come from source evidence and
are compared with the input claim. Neither profile selects documents by act
number, date, title, filename or hash. Decorative title case is normalized
for comparison; the original title remains in the evidence.

`native_text.py` reads the explicit saved JSON `/redtext` or `/doctext` evidence field and delegates HTML
tokenization to the existing raw HTML adapter in `housing_html.py`.
`actual-native-html/3` produces `text-extraction/1`; positions remain Unicode
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

The resolution profile reads issuer/type/date/number/title/signature from the
source. Approved texts and their title-bound annexes form distinct address
scopes. Bare Roman sections, restarted/superscript point numbers, both observed
numeric/letter list orders, quoted amendment text and normative notes use the
same traversal. Rejected scopes cannot reuse earlier parents.

Recognized tables retain row/column, rowspan/colspan, exact cell source spans
and text ownership. An embedded table preserves its owning point and restores
the surrounding context on exit. Images retain their complete original
attributes/data and source spans in reading order. Raster formulas are source
images, not mathematical transcriptions. The offline report displays embedded
PNG/JPEG/GIF/WebP data without executing source HTML or fetching remote images.
The legacy extraction key `unsupported_regions` lists source regions; a tree
accounts for each once in `parsed_regions` or `unresolved_regions`.

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

## Historical federal-law/code transfer

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

## Current verification and transfer limits

The complete default suite passes **189 tests**; Ruff passes; M0 gate passes
**78/78**. Authored resolution controls cover two identities, claim conflicts,
approved/annex scopes, tables, source-order images, nested numbering, substantive
notes, ASCII/Russian quotation marks, nested quotations, incomplete quotation
refusal, inert reports and permission-bound immutable compiler replay.

Fresh-context review found and corrected false-success paths in quotation
boundaries, image ordering, normative-note scope, embedded-table ownership and
mixed numbering. A later transfer exposed an unsupported whole document quoted
inside an amendment: it now fails explicitly instead of raising a missing-title
exception. Earlier failed runs are retained. Native HTML is not uniform:
`resolution-transfer-v2` also records a Cyrillic-lookalike Roman heading and
legacy multi-provision paragraphs which the declared grammar does not support.
Do not hide these failures or describe the engine as an arbitrary-HTML parser.

The latest native matrix and its original-four acceptance binding are retained
under `data/m1/pilot_runs/m1-03a-resolution-transfer-v5/`. Resolution validation
uses two reserved full acts not used to change rules; the four previously held-out
laws/codes are replayed against their existing independent controls and semantic
results. These replays are not newly discovered validation bodies. Original
resolution-transfer v1/v2 failures and v3's incomplete reference run remain
available and are not promoted. The final added guard explicitly refuses
unrecognized footnotes rather than classifying them as point continuations.

| Final family / saved field | Validation acts | Result |
|---|---|---|
| Federal law / `/redtext` | Nos. 273-FZ and 35-FZ | pass, 2/2 |
| Code / `/redtext` | Town Planning Code, Administrative Judicial Procedure Code | pass, 2/2 |
| Government resolution / `/doctext` | 21.01.2006 No. 25; 15.05.2013 No. 416 | pass, 2/2 |

All six final-version inputs have two identical fresh full compiler builds and
unchanged repeats, independent source controls and no structural exceptions.
The final matrix preserves 57 protected source records. No.25 is a repealed act
used only for syntactic transfer; No.416's source-declared snapshot is not an
admitted edition. These bodies were not used to change rules. The final added
negative-footnote guard was requalified against the same held-out corpus,
with a fresh frozen code binding and full rebuilds.

Original-four acceptance SHA-256:
`77cab175c67f4f2d762eb84729831d7893779a10c91f23237b288e8f543a2221`.
Final transfer-report SHA-256:
`8c4e6b94c89f3bbad7b1b11e959878b26fe8a2a4be3a1e9e2314f87259f7583f`.

### Earlier subset verification

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

These earlier checks qualified the recorded federal-law/code subset only.
Neither the historical nor current engineering evidence guarantees arbitrary
HTML, infers missing structure, implements other act
families, resolve every editorial note's scope, reconstruct historical
editions or establish legal applicability. Unsupported structures remain
explicit exceptions and cannot pass this transfer protocol.
