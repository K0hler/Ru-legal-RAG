# Test instructions

- `corpus/test_m1_04a_pool_selection.py` covers targeted code metadata freezes,
  checksum refusal, standalone code titles across portal types, code slugs and
  selection/refill from the same frozen candidate list. Include an authored
  480-page code: the old 200-page ceiling remains the default; a declared
  `--pages-max` override must reach selection and refill. New feed caches carry
  candidates and indexed rejection diagnostics; old list caches remain readable.
  The code census uses authored actual.pravo/day-feed fakes: reasons
  (`no_portal_publication` from the earliest dated publication day, EO mismatch,
  pages, non-code titles, «. Часть …» titles), feed failure never eligible,
  `--previous` reuse without repeated requests, and write-once outputs.

- `corpus/test_ocr_logical_structure.py` checks the M1-04A logical-paragraph
  experiment with authored extractions: lowercase continuations never open
  approval scope, terminated list abzacy stay separate, decimal/global point
  sequences, dates are not points, second approval caption opens `S2`, annexes
  to the act stay in the act, footnote owners need the marker, and token
  accounting. Load docs/assets scripts with `sys.modules` registration
  (dataclasses need it). No corpus files or OCR engines.
  Since prototype v1 it also covers named units (article/chapter/part/section
  markers), attached-document captions («Проект», Page-header annex captions,
  repeated running captions), requisite blocks after the last norm and their
  negative probes (inline references, «Министерство…», «Москва и …»).
  Cycle 3 B2: long annex captions to the act («Приложение 1 к Федеральному закону "…"» -> `A/AN1`)
  and to an attached document («Приложение к Порядку …» -> `S/AN`), and in-sentence references
  («согласно приложению 1», a sentence starting «Приложение … » and ending in a dot) open no annex.
  Fix round 1: «к приказу …» inside a resolution stays with the attached document (own-kind rule), bare
  «Приложение 2» between points and a broken sentence open nothing, number signs №/N/Н, final dots after a number/date.
  Cycle 3 B3: uppercase «РАЗДЕЛ I …» (no dot, OCR «ІХ») is the level above chapters and closes the previous
  section's article (heading not absorbed); sentences starting «Раздел II настоящего …» are not headings;
  Roman «I. …» sections without the word still open sections.
  Cycle 3 B4: unnumbered subheadings inside a section go to the section (incl. long and two-line ones);
  negatives: terminated sentence, line after «:», before a table/picture/subpoint, OCR Caption region,
  no enclosing section. A capitalised paragraph after the last subpoint returns to the point; negatives:
  lowercase, «;» item after «;», text after «:», list that goes on. «8.1» closes an open «4)»; uppercase
  «ГЛАВА»/«СТАТЬЯ» and OCR Х/І in chapters (parametrised, sentences stay text).
  B4 fix round 1: captions by text («Схема 2», «Рисунок 1 - …», «Форма N 2», parametrised), «Адрес: …» lines and
  an OCR-cut 130-character sentence are not subheadings; Text over 200 characters or without two Section-header
  subheadings in the scope stays with the point; no closing inside quoted amending text; pinned known limitations.

- `corpus/test_m1_04a_batch_tools.py` checks the check-pool batch tools in
  `docs/assets/` on an authored extraction: the v1 annotator input has only
  key/category/text (no stage-2 `P`/`join`) and drops Picture and noise regions,
  the legacy mode still carries stage-2 columns, the `v1` scoring filter removes
  only Picture/noise gold keys, and the gold freeze hashes the annotator input,
  refuses a changed gold receipt and never overwrites. No corpus files.
  It also checks that rescore scoring with the single-annex equivalence is
  opt-in and that the classifier reads `<doc>/AN` as `<doc>/AN1` under it;
  `test_ocr_logical_structure.py` covers per-document annex counting, one vs
  two annexes in all variants, and `cross_scope_v2` transfers (annex↔body,
  between annexes) that the old `first_scope` misses.
  `test_batch4_error_classes_from_evidence_only` pins the batch-4 classifier rules (second attached document
  `A/AN` vs `S2`, restarted «01.» lists, line between tables at the root, footer code) and that `S/II/8/б` stays
  a closing error.
  `test_dev_regression_baseline_comparison_flags_drops` covers `--baseline`: per-document drops
  (no_section/strict down, `cross_scope_v2` up, region count changed, missing) and CLI exit 1.
  Cycle 4 A1: `attached_ordinal` tests (both files) pin ordinal heads by first appearance, `S, S2` == `S, A/AN`,
  merged/moved second document = error + `cross_scope_v2`, `S/AN<n>` untouched, one document as before; freeze
  default only after batch-04, rescore/regression opt-in/opt-out and the classifier's renamed reading.

- `corpus/test_m1_04a_gold_v2.py` checks the v1 -> v2 gold derivation on authored
  lines: annex map `S<k>` -> `S/AN<n>` (alternatives and `+` kept), «N.M» nested
  only under an existing sibling «N.» (recursively), typed `ст12.1` untouched,
  bad/stale/colliding maps refused, write-once output and a hash-pinned map.

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
