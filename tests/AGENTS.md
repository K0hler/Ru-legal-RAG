# Test instructions

- `corpus/test_ocr_logical_structure.py` checks the M1-04A logical-paragraph
  experiment with authored extractions: lowercase continuations never open
  approval scope, terminated list abzacy stay separate, decimal/global point
  sequences, dates are not points, second approval caption opens `S2`, annexes
  to the act stay in the act, footnote owners need the marker, and token
  accounting. Load docs/assets scripts with `sys.modules` registration
  (dataclasses need it). No corpus files or OCR engines.

- `corpus/test_logical_text.py` checks stage-2 `logical-text/1` with authored
  extractions: running-noise reasons (incl. digit-normalized repeats), captions
  kept as content, cross-page body/footnote joins and their D1/D2 refusals,
  exact fragment offsets, token accounting, no input mutation and verified
  immutable CLI writes. It also runs `docs/assets/evaluate_logical_text.py`
  parity labels and metrics on authored inputs. No corpus files.

- `corpus/test_ocr_footnote_stitch.py` checks authored cross-page continuation
  joins, actual source fragments, three-page anchors, skipped pages, new markers
  and ordinary lower body paragraphs. Untagged Text needs positive parenthetical
  citation evidence as well as geometry; adjacency alone caused a reproduced
  false join. Check immutable CLI output and Dedoc logical order without changing
  source page/bbox/text. No private corpus or heavy library enters these tests.

- `corpus/test_dedoc_json_probe.py` and `test_docling_json_probe.py` verify
  authored direct-JSON mapping, table topology, unknown/empty regions, explicit
  prefix ledgers and immutable attempts without importing the heavy libraries.
  Actual library stages run only in the explicit external experiment runtimes.

- `corpus/test_ocr_structure.py` uses authored normalized input for both OCR
  resolution families. Check exact raw tokens/spans, split approvals/titles,
  cross-page context, decimal/Roman prefixes, quoted scopes, table/footnote
  owners, provider-neutral category variation and preserved ambiguity. Mutation
  controls include valid-but-wrong sibling ownership and normative text, beyond
  missing parents/cached accounting. No inference or corpus files enter CI.
  Include physical-category quote delimiters, multiple exact note references
  and recovery at a verified new approval/annex after an unknown section.
  Scope controls vary physical caption categories, reference fragmentation and
  date notation across both families. Include exact typed identifiers, prefix
  collisions, multiple owners, repeated approval/annex headers and quoted captions.
  Reject unknown-owner tables falling back to root and wrong scope/title evidence
  even when graph pointers and cached preservation counters remain consistent.

- `corpus/test_ocr_structure_probe.py` checks the explicit experiment projection
  with authored text/table inputs and refusal to overwrite retained failures.
  These tests do not run Dedoc/Docling, download documents or qualify hierarchy.

- `corpus/test_pdf_extraction.py` uses authored native OCR fixtures; no model,
  Docker or downloads. Check merged and empty cells, physical-page coverage,
  OCR-string spans, model/source binding, native truncation and one-time token
  accounting through the shared grammar. Unknown categories remain source data.
- `corpus/test_ocr_runtime.py` checks CLI saved import, subprocess argument
  construction, permission-before-write, immutable replay, fresh-runtime
  provenance replay and index/extraction/native corruption. Keep external OCR
  calls mocked only at the process boundary; test normalization/compilation real.
- `corpus/test_ocr_qualification.py` tests the report-only one-page human review
  binding: source/image/reference hashes, decision, reviewer and timezone.
  Use authored reference/image bytes; never turn synthetic decisions into actual
  permission or admission. Unknown review duration stays null.
- Owner quality-scope tests bind exclusions to an exact PDF hash/page and retain
  missing-review, runtime/model/configuration and saved-replay blockers. Fresh
  stochastic text may vary only under verified pinned settings.
- `docs/assets/check_ocr_lab_recovery.py <lab-root>` is an explicit external
  client check using authored images/streams, not a default CI dependency.
  Check early cancellation/connection close, at most one retry and preservation
  of a received attempt when the next request raises. No GPU is needed.

- `corpus/test_official_import.py` covers the current v2 compiler route:
  verbatim/unknown source types and fields, no quote/number recovery, immutable
  replay, source-ordered children, range warnings (including a broken intervening
  sibling), and the independent replay verifier's text-owner mutation. Older
  normalization/completion/audit unit tests retain historical module behavior;
  their reconstruction is no longer used by the v2 compiler. Missing sidecar
  subdivisions stay source text under the owner's accepted granularity.

- `corpus/test_official_normalization.py` covers named/ordinal upper parts,
  approval evidence, source ordinal parts, inline notes and proven/refused end
  normalization, including nontext gaps. Recovery tests include full letter-list
  continuation/media scopes. Audit tests distinguish numeric body references.
- `corpus/test_official_dom_controls.py` injects downstream text, heading-number,
  media, coordinate and outside-paragraph cell faults into the separate diagnostic
  verifier. Independent source controls must validate actual normative text and
  exact evidence, not only retained `original_text` and cached accounting/audit.

- `corpus/test_structure_recovery.py` checks unseen superscript sibling numbers,
  full formula/table/note scope, original row pointers and declared ranges;
  reject ambiguous/style/nested/colliding markers, quotes and form contexts.
  Inline amendment and quoted-term paragraphs must have no false quote node;
  unclosed payloads remain blocked. Retained real mutation controls belong in
  the offline replay, never in default tests or closed-gold fixtures.

- `corpus/test_structure_audit.py` exercises the independent HTML inventory,
  unseen superscript/decimal/Roman markers, no inferred numbering gaps, wrong
  kinds/parents/ranges, deterministic reports and the compiler HTML audit view.
  Keep the scanner independent from official JSON and parser marker patterns.

- `corpus/test_official_structure.py` checks the opt-in v2 path, source selectors,
  permission scope, sidecar numbering/ranges, note scope and exactly-once media/
  text accounting. Negative bindings must write no derived files; the original
  v1 replay and frozen M0 gate remain required.
- Official-structure completion controls include quoted whole articles, media
  and inline-note ownership, mixed closing/opening boundaries, omitted top-level
  markers, inline anchors, break-separated units, form sections/continuations,
  numbered table-row cell ownership, malformed JSON and IPS body selectors.

Scope: automated tests and checked fixtures.

- Mirror the `src/legal_rag/` module layout.
- Prefer one focused regression test for each branch, parser rule, or bug.
- Test idempotent acquisition, full text accounting, deterministic IDs/hashes, temporal refusal, and exact evidence coordinates.
- Corrupt, remove, and mispoint archived evidence in negative tests; reconciliation
  must reject it before writing derived records.
- Keep working examples separate from the closed gate set; do not use closed labels for tuning.
- Never require live network access in the default test run. Record live-source checks as explicit integration tests.
- M1-01 corpus tests are in `legal_rag/corpus/test_input_and_compile.py`. Use
  the existing acquisition lifecycle for synthetic archives and the frozen
  source test fixture for read-only wrapper checks; never load private gold.
  Fixture text and permission bytes are hash-pinned and exempt from Git newline
  conversion. Keep raw/approved-state snapshots in negative tests, and verify
  full text/byte accounting through the observable CLI artifacts.
- M1-02 inventory checks are in `legal_rag/corpus/test_input_inventory.py` and
  exercise the documentation generator against project-authored synthetic
  archives. Verify ten distinct blocked rows, separate unsigned permissions,
  corrupt/mispointed evidence, publication card versus PDF URLs and immutable
  replay protecting human records. Do not load private gold or require a network.
- `docs/assets/check_m1_02_review_v2.js` is an explicit local browser regression
  check for the owner packet. It disables network after page load, exercises all
  embedded documents/PDF navigation and report gates, and resets its synthetic
  answer in an isolated session. It is not human legal approval or a default
  network-dependent unit test.
- M1-02 closure checks are in `legal_rag/corpus/test_m1_02_closure.py`. Use only
  project-authored temporary evidence/review fixtures. Verify read-only repeat,
  corruption, path escape, duplicate/date rows, exact permission asset scope and
  reviewer-role refusal; synthetic confirmation never approves real editions.
- M1-03 native checks are in `legal_rag/corpus/test_native_text.py`. Use the
  project-authored HTML and literal expected address order; verify entity and
  whitespace maps, original scalar locators, one-time token accounting, unknown
  context/duplicate/identity refusal, retained notes and split superscripts.
  Full retained 59-FZ verification stays local under `data/m1/pilot_runs/m1-03/`;
  it must not read closed questions or imply dated legal approval.

- `legal_rag/corpus/test_html_preparation.py` tests the optional BS4/tinycss2
  preparer with authored HTML and the existing synthetic permission archive.
  Verify original/prepared opening anchors, exact text/order, indices, notes,
  tables/images/links, unsupported CSS preservation and immutable CLI replay.
  Include legacy CSS comments, media-rule isolation and adjacent whitespace;
  all three are observed native-HTML failure modes. Full retained-input controls
  stay local and are preservation checks, not legal-structure or G13 evidence.
  Reject body/content parsed under `head` before writing, and check `!important`
  priority across simple class and inline declarations to avoid false indices.


- M1-03A adds `corpus/test_structure.py`: authored cross-act identities,
  scalar/raw adapter equivalence, literal hierarchy/number controls, scoped
  `§` nodes, Roman/uppercase headings, hyphenated superscripts, invalid zero
  components, break-boundary refusal, textual notes and region-only blockers.
  Keep the full transfer corpus local, freeze before parsing validation bodies,
  and retain independent DOM controls and failed cohorts. A corrected control
  reader must retain `<br/>` whitespace; do not change production code to agree
  with a reference reader that dropped it. Native transfer never reads gold.

- M1-03A completion requires a full retained-input acceptance run on the
  original four HTML documents, including No. 354 and No. 491 through the
  same compiler. Preparation-only preservation and additional federal-law/code
  tests are supplemental. A missing path or unresolved critical structure
  means stage failure even when the complete default test suite is green.
- `corpus/test_resolution_structure.py` covers source-derived government
  identities, approved/annex/quote scopes, both numeric/letter nesting orders,
  normative notes, numeric-footnote handling/refusal of other markers, table
  topology/ownership, image order and inert raster preview. Test nested ASCII
  and Russian quotation marks, unclosed quotation refusal, duplicate boundaries,
  immutable permission-bound compiler replay and preserved admission blockers.
  An unsupported heading inside a quotation is an exception, never a crash.
