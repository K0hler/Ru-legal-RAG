# Documentation instructions

- M1-04A source-pool fixes are recorded in
  `milestones/m1/04a/M1_04A_BUG_SOURCE_ACQUISITION_2026-10-22.md` ("Результат").
  Future selection schema /3 uses `publication-pravo-pool/2`, retains per-item
  feed diagnostics, and requires `--code-candidates` when the code quota is
  positive (refused with a zero code quota; the recorded path is repo-relative;
  code titles exclude «О/Об…» and amending forms). `assets/select_m1_04a_pool.py freeze-codes --day ISO --output
  DIR/selection.json` freezes all code candidates from explicit days before
  selection/body acquisition; this is a bounded targeted pool, not a census.
  KAS publication 2015-03-09 declares 480 pages, so using it requires an explicit
  `--pages-max 500`; the old page limit is not silently relaxed. Refills verify
  and reuse the pinned code list. Batch-01/02 data and their v1 acquisition
  route remain frozen; future acquisition directories use the opt-in wrapper.
- `select_m1_04a_pool.py census-codes --output DIR/selection.json [--previous OLD/census.json]`
  is the code census: an authored `CODE_REFERENCE` (adoption acts only, incl.
  codes that lost force), each verified in actual.pravo by exact number+date;
  the portal entry in the actual.pravo `publications` list gives the date/EO,
  the day feed confirms EO and pages, then `freeze-codes` runs on eligible days
  and `census.json` records every code with its reason. actual.pravo names code
  parts «<Кодекс>. Часть первая» (accepted only inside the census). `--previous`
  reuses recorded exact matches and empty feed days of an unfrozen earlier run.

- `milestones/m1/04a/M1_04A_LOGICAL_PARAGRAPHS_2026-10-17.md` records the
  logical-paragraph/depth-solver experiment (`assets/ocr_logical_structure.py`),
  not G13 qualification. Keep development, holdout-1 (failed before two generic
  fixes, then promoted to development) and frozen-code holdout-2 results apart.
  Owner-path gold is single-annotator text-based; it does not check table cells,
  quote scopes or legal-ast/2 contracts. On 21.10.2026 the owner decided: СП/СанПиН with the same number are one
  designation (alias dictionary, number is identity); approved texts and act
  annexes are one attached-document kind with `owner`; thresholds accepted; the
  check pool takes diverse families with automatic pravo.gov.ru gold; LLM deferred.
  See section 9 of the evaluation protocol.

- `milestones/m1/04a/M1_04A_TWO_PDF_2026-10-17.md` records the frozen-code
  26-page SP3597/Resolution416 PDF experiment, not G13 qualification. Distinguish
  preservation/repeats from selected-image semantic controls (26/26 and 21/24).
  An ordinary continued reference falsely opens approval scope in No.416;
  Dedoc foiv handles the selected controls, while Docling remains flat. No.416
  was already known on the native route; it is not a fresh independent act.

- M1-04A's owner refinement prioritizes error classes by semantic/citation
  impact; see `milestones/m1/04a/M1_04A_FAILURE_CLASSES_2026-10-17.md`.
  Unresolved counts, aesthetic tree depth and known-document successes are not
  severity or transfer evidence. Document harmless deviations with retained
  context; unknown impact remains unknown, and critical gates stay unchanged.
  The first implementation is OCR-only explicit reference/scope resolution (/7),
  connected through the existing compiler. Distinguish supported caption variants
  from missing/conflicting owner evidence. Increased unresolved counts can expose
  formerly false metadata/root assignments; they do not establish worse OCR or
  qualify the new structure. Retain native and official-import route boundaries.

- `milestones/m1/04a/M1_04A_EVALUATION_PROTOCOL_2026-10-20.md` defines how
  M1-04A stage-3 progress is measured. Progress is the first-pass result on
  frozen code for documents not seen before, recorded in its ledger before the
  document joins development; development scores are not progress. The rolling
  check pool is separate from the four Task 3 reserved acts, which it must not
  consume. Gold and its annotation convention are frozen before runs; a
  convention change re-annotates all gold and keeps old numbers. Its stop
  thresholds and the annex `owner` convention are proposals awaiting the owner.

- `milestones/m1/04a/M1_04A_POOL_BATCH_1_2026-10-21.md` is the first check-pool
  first-pass result on frozen `code-final`, not G13/Task 3. Headline numbers use
  annotation convention v1 (Picture regions not scored, as in earlier ledger
  rows): prototype 226/333, `/7` 89/333; all 363 regions (237/91) are shown
  labelled. Frozen gold scored pictures; v1 is a scoring filter, not re-annotation.
  Gold is single-agent (Codex) annotation of OCR text with two spot page checks;
  owners are blind to stage 3, continuation is not (the annotator saw stage-2
  joins). Keep these limits and the selection biases (no actual.pravo hits)
  with any number quoted from it. The batch is now development: later scores on
  it are not progress. Its 30-region sample is a sibling `_SAMPLE_` file.
- `milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v1.md` (`m1-04a-annotation/v1`)
  is the versioned check-pool gold convention; a change needs a new version,
  re-annotation and retained old numbers. Batch tools in `assets/`:
  `build_m1_04a_annotation_input.py` (v1 input without stage-2 `P`/`join`,
  Picture/noise excluded; `--legacy-batch-01` reproduces batch 1 byte for byte),
  `freeze_m1_04a_gold.py` (write-once, also hashes the annotator input),
  `run_m1_04a_first_pass.py` (`freeze`/`run`/`rescore`/`sample`, `--convention`),
  `classify_m1_04a_errors.py` (batch-1 reading, strict variant) and
  `summarize_m1_04a_ocr.py` (per-act OCR summary).
- `milestones/m1/04a/M1_04A_POOL_BATCH_2_2026-10-22.md` is the batch-2 first
  pass on frozen prototype v1 (+ `code-final` and `/7` for comparison), not
  G13/Task 3: v1 1077/1782, `code-final` 597, `/7` 123. Gold is blind
  (no stage 2/3, no pictures/noise), three parallel Codex jobs, text-only with
  spot page checks. Quote the 75.4% `S/AN<n>`=`S<n+1>` figure only as a
  labelled reference; the naming and «4.1.» depth are open convention questions where
  the prototype follows the earlier SanPiN 2.1.3684-21 development gold (`S/AN<n>`, `A/4/4.1`)
  and the batch-2 gold departs from it (v1 is silent; annotators could not see the precedent).
  Both go into convention v2 before batch 3 (proposals: convention v1 section 8, not in
  force); batch 2 is then re-scored as development, 60.4% stays the first-pass headline.
  No code or government order in the batch. Batch 2 is now development.
  `run_m1_04a_first_pass.py --prototype LABEL=PATH` (freeze schema /3) and
  `classify_m1_04a_errors.py --system` with evidence rules (batch 2+) were
  added; batch-1 outputs still reproduce byte for byte.
- `milestones/m1/04a/M1_04A_POOL_BATCH_3_2026-10-22.md` is the batch-3 first
  pass on frozen v1 (+ `code-final`, `/7`), not G13/Task 3: 4008/1125/170 of
  4108. KAS RF is 69% of the regions: always quote it separately (v1 2847/2855;
  strict 9 because v1 builds no «Раздел» level) and the without-KAS figure
  (1161/1253). The evaluator's `first_scope` counts 0 cross-scope, but 30
  annex-of-attached-document regions went silently to the body (§7 violated).
  `classify_m1_04a_errors.py` gained batch-3 evidence rules: for v1 every
  reassigned error was previously unclassified; for code-final one error
  (fsnson 14.1) moved from a batch-2 class to ATTACHED_ANNEX because three new
  checks run before the batch-2 rules (batch-1/2 outputs unchanged). Without KAS
  and the award-list decree: v1 954/1046 (91.2%). Batch 3 is now
  development. Open convention question: `S/AN` vs `S/AN1` for a single unnumbered annex.
- `milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v2.md` (`m1-04a-annotation/v2`,
  22.10.2026) adds the owner's two rules (attached-document annexes `S/AN<n>`;
  «N.M» nests under an existing «N.», exceptions noted by the annotator); v1 §8
  proposals 3–5 remain proposals. `assets/derive_m1_04a_gold_v2.py` derives v2
  gold mechanically from frozen v1 gold with a per-document annex map (data, not
  code; optional `flat_dotted` in the map and annotator `exceptions.json` keep
  listed «N.M» flat, empty by default); `run_m1_04a_first_pass.py rescore --gold-suffix gold-v2` and
  `classify_m1_04a_errors.py --gold-suffix gold-v2` score it. Batch 2 report
  section 10 is a development re-score (v1 1464/1782); never replace the 60.4%
  first-pass ledger entry with it.
- Cycle 3 (22.10.2026, owner decision in convention v2 §5): with exactly one
  annex (`AN`/`AN1`, counted per document from the gold) `<doc>/AN` == `<doc>/AN1`;
  opt-in `--single-annex` in `evaluate_ocr_owner_gold.py` and
  `run_m1_04a_first_pass.py rescore` (summary `single_annex_equivalence`), so old
  outputs reproduce without it. `scope_v2`/`cross_scope_v2` (nearest document or
  annex) sits beside the unchanged `first_scope`/`cross_scope`; the classifier
  writes it for such rescores or `--cross-scope-v2`. Rescores `20261022-batch-0{2,3}-rescore-cycle3`:
  batch 2 unchanged (v1 1464, transfers 278/278), batch 3 v1 4014 (+6 pp-2249),
  `cross_scope_v2` 30 vs old 0. Batches 1/2 and the old 8 are unaffected.
- Batches after batch-03 default to the single-annex equivalence: `run_m1_04a_first_pass.py
  freeze` records `single_annex_equivalence` (override `--[no-]single-annex`), `run` and
  `rescore` follow it, the classifier writes `cross_scope_v2` for them. Batches 1-3 stay off.
  `freeze` also hashes the gold `freeze-addendum.json` (if present) into `files`; `run`
  re-checks it and its listed files. Pool selection provenance now checks `src/legal_rag/sources`
  too and records `PYTHONPATH=src <interpreter> docs/assets/select_m1_04a_pool.py ...`.
- `assets/run_m1_04a_dev_regression.py` now covers all 34 development documents (old 8, batch 1, batch 2 on
  `gold-v2`, batch 3), scores with `single_annex=True`, counts `cross_scope_v2` per document and has a per-family
  breakdown (family = slug prefix; `holdout2-*` and `sanpin-*`/`sp-*` are sanitary rules). Cycle-3 baseline of frozen
  v1: `data/m1/m1-04a/experiments/20261022-dev-regression-cycle3-baseline/` (6660/7072 no_section, `cross_scope_v2` 308).
- Cycle 3 B2 (prototype, VERSION unchanged until B5): an annex caption «Приложение [№|N] N к <referent>» opens
  an annex without «УТВЕРЖДЕН». Referent = the act (`ACT_REFERENT`: закону/кодексу/постановлению/приказу/указу/
  распоряжению/решению, optional «настоящему») -> `A/AN<n>`; otherwise the current attached document `S<k>/AN<n>`.
  A body caption up to 300 characters is accepted when its reference names the act or a capitalised document
  («к Порядку …», «к СП …»); a caption ending in a dot is a sentence unless it ends in «г.». Regression
  `20261022-dev-regression-cycle3-b2`: 6968/7072 no_section (+308: fz-431/433, fsnson-282), `cross_scope_v2` 0, no drops.
- `milestones/m1/04a/M1_04A_PROTOTYPE_V1_2026-10-21.md` is the Russian
  development report for prototype `ocr-logical-structure/1-experiment`, frozen in
  `data/m1/m1-04a/experiments/20261021-prototype-v1-freeze/` (`code-final` a7b81b59
  stays for comparison). 1182/1182 is on development documents the rules were
  written against; never quote it as progress, only batch 2 measures transfer.

- `milestones/m1/04a/M1_04A_LOGICAL_TEXT_2026-10-20.md` records the stage-2
  `logical-text/1` implementation and `assets/evaluate_logical_text.py`:
  full prototype parity on the 8 saved documents (0 D1/D2/unexpected),
  continuation 29/0/2 and no false/missed header exclusions. These are
  development documents, not progress, G13 or Task 3 qualification; stage 3
  is not connected yet.

- `assets/stitch_ocr_footnotes.py` writes a separate logical continuation view
  with exact physical fragment pointers/pages/bboxes and combined-text offsets.
  Unnumbered Footnotes before a new numbered note join the last note on the
  immediately preceding physical page. Mislabelled Text recovery is deliberately
  narrower: one adjacent bottom-band parenthetical block after an unfinished
  citation number. The Dedoc JSON probe consumes its region order only with
  `--stitch-footnotes`; retain native JSON and earlier failures unchanged.
  This heuristic and its development replay do not qualify OCR hierarchy/G13.

- M1-04A direct JSON follow-up is `milestones/m1/04a/M1_04A_DIRECT_JSON_2026-10-17.md`.
  Native JSON maps directly to Dedoc/Docling API objects, without HTML or new
  OCR. Distinguish exact schema transfer, actual inference and source sidecars;
  retained geometry/tables do not qualify legal parents. Preserve raw/prefix
  variants, synthetic UUID variability and Picture-text/table-anchor losses.

- M1-04A execution began on 17 October 2026. Its retained baseline is
  `milestones/m1/04a/M1_04A_BASELINE_2026-10-17.md`: 10 PDFs/103 pages,
  1,139 regions/1,296 blocks, 0 legacy legal nodes and 1,284 unresolved blocks.
  Dedoc TXT and prepared-HTML trials are diagnostic, not qualification. Six
  additional official PDFs have a frozen development/reserved split and exact
  permissions under `data/m1/inputs/m1-04a/`; reserved bodies must stay separate
  from rule design. Keep the slice/G13 open until independent full checks pass.

- On 17 October 2026 the owner added M1-04A as the next planned slice:
  `plans/2026-10-17-m1-04a-ocr-structure.md`. It owns reusable OCR hierarchy
  reconstruction, existing-file analysis and additional official corpus/heldout
  experiments. M1-06 consumes its engine for full SanPiN coverage; M1-05 still
  needs only M1-04 extraction. Preserve the accepted native official-tree route
  and M1-04's bounded seal/page-75 quality scope. Adding the task is not its
  implementation or acquisition. Keep the 17-slice plan and G13 synchronized.

- Keep only this instruction file and `README.md` at the documentation root.
  Use `overview/` for product/architecture/roadmap, `policies/` for admission
  rules, `milestones/m0/` and `milestones/m1/` for stage records, `guides/` for
  tool usage, `research/` for research/historical context, and `plans/` for
  individual plans. M1-03A and M1-04 records live in M1's `03a/` and `04/`.
  Keep existing scripts and rendered/source assets together under `assets/`.
- The 16 October 2026 documentation relocation changes paths and links only.
  Its M0 receipt records old/new pinned hashes against the preceding Git
  revision; acceptance criteria, human decisions, production code, fixtures and
  local evidence are unchanged. Gate generation still uses
  `python docs/assets/generate_m0_gate.py`; its records now live under
  `milestones/m0/`. Do not refresh unrelated frozen hashes during maintenance.

- `milestones/m1/04/M1_04_ACCEPTANCE_2026-10-16.md` supersedes the initial open OCR assessment
  under an explicit owner scope: round-seal text accuracy is noncritical, and
  only the original SanPiN PDF's physical-page-75 table is excluded from quality
  grading. Keep raw data/failed controls and all page accounting. New inference
  is versioned; exact saved replay and pinned verified runtime/model/configuration
  remain mandatory. Other tables, dates/requisites and legal admission are not
  waived. Bounded Picture recovery completes the diagnostic M1-04 slice; M1-04A
  is next. Distinguish the 103-page live snapshot from the subsequent metadata
  retention fix, validated with authored retry faults and three real seals/date.

- `milestones/m1/04/M1_04_REGION_PROBES_2026-10-16.md` is a bounded diagnostic comparison,
  not a production change or gate waiver. Wide seal crops stop loops (3/3 each)
  but still mistranscribe; retain the successful narrow date crop. Row bands
  recover six ordinary minus cells (50/50 selected guard signs, 3/3 trials),
  while conditional signs remain 0/13; x2 can introduce a tenth column.
  The added 91-cell engineering control is a known-page development check,
  not new heldout evidence or human legal qualification.

- On 16 October 2026 the owner replaced M1-04's unimplemented Docling/RapidOCR
  baseline with the existing local dots.mocr OCR-Lab pipeline. Preserve native
  outputs and normalize through an engine adapter; physical document trees and
  inferred legal hierarchy have separate acceptance. The OCR-Lab transcription
  reference has `human_review=false`. A separate actual owner confirmation now
  covers page 1 only; do not promote it to full-reference human qualification.
- `milestones/m1/04/M1_04_QUALIFICATION_2026-10-16.md` records implemented OCR integration with
  open acceptance: both runs cover 10 PDFs / 103 pages, but fresh text/category/
  geometry changes, 0/13 table signs and incomplete Picture responses remain.
  Saved-result replay is deterministic, fresh inference is not qualified.
  `assets/verify_m1_04.py` validates native normalization and explicit one-page
  decisions; the actual duration of human review is unknown. Keep the original
  runtime freeze/failed attempts and the explicit report-only freeze amendment.

- The owner accepted source granularity and requested M1-03A closure on
  16 October 2026. `milestones/m1/03a/M1_03A_CLOSURE_2026-10-16.md` is the current decision and
  evidence; the v2 compiler imports the official tree without reconstruction.
  Older 2/6 and 3/6 reports remain historical failures of their own versions.
  Do not rename retained regression acts as fresh G13 qualification. Distinguish
  this accepted native JSON contract from future PDF/OCR/sanitary-rule gates
  and the ten edition admissions. Real source-boundary warnings remain visible.

- `assets/official-json-visual-review-20261016/index.html` is an offline Russian
  source/JSON/failure viewer, generated by `build_official_json_visual_review.py`
  and its adjacent template from the retained six-act cohort. It preserves source
  captions/types and demonstrates the quoted 184-FZ article inside 384-FZ article
  43. Its 6,514-unit raw ID/level/anchor/range checks pass; this is formal source
  consistency, not legal correctness, a parser fix or changed frozen decisions.
  Keep unrecognized units separate from source nesting defects. Rebuild with the
  pinned validation Python; checks.json pins the HTML, generator, template and
  original sources. Source HTML is displayed through inert formatting only.

- `milestones/m1/03a/M1_03A_OFFICIAL_NORMALIZATION_2026-10-16.md` records the `/5` development
  replay: 6/6, full text/media/source bindings and 43 negative mutations, seven
  regressions and four identical v1 drafts. Retain `/4` failures as history.
  Separate HTML-only printed controls from independent replay of JSON scope
  claims; neither implies human legal admission or universal parser coverage.
  A subsequent distinct frozen cohort passes only 2/6 full controls (3/6
  technical). Separate unsupported source paragraphs/titled parts/subsections
  from the quoted-article reader limitation. G13 remains failed for this route;
  never replace failed documents or promote a posthoc correction to frozen proof.

- `milestones/m1/03a/M1_03A_OFFICIAL_JSON_TRANSFER_2026-10-16.md` records the frozen
  official-structure/4 independent cohort: 2/6, G13 fail. Both laws pass full
  replay and independent paragraph ownership; code part headings and an approved
  list type are unsupported, while No.306 has conflicting source-sidecar ranges.
  Keep failed readers separate from production failures. The preliminary verifier
  lacked payload-owner coverage; the separate payload checker/reviewed report
  closes that validation gap. Diagnostic acquisition attribution has a correction
  receipt; frozen source metadata and production allowlists remain unchanged.

- `milestones/m1/03a/M1_03A_STRUCTURE_AUDIT_2026-10-15.md` records the subsequent implementation
  of independent HTML reconciliation, bounded superscript sibling recovery and
  coarse form/amendment payloads. Preserve the earlier integration/triage as
  historical evidence. Distinguish normalized and source-declared ranges, critical
  missing provisions and optional segmentation. Seven development inputs and
  injected faults do not establish new G13 coverage or universal error detection.

- `milestones/m1/03a/M1_03A_STRUCTURE_GAP_TRIAGE_2026-10-15.md` is an analysis/proposal, not a
  deployed gate change. Two No.354 6² provisions need distinct addresses and full
  payload scopes; No.47's inline form list and seven amendment-quote cases may
  use coarser verbatim paragraphs under the correct provision. Two No.410 cases
  are false quote boundaries around defined terms. Do not equate optional inline
  segmentation with missing own provisions or silently remove real parent errors.

- `milestones/m1/03a/M1_03A_OFFICIAL_STRUCTURE_INTEGRATION_2026-10-15.md` documents the implemented
  opt-in M0 bundle/v2-input route and seven full compiler replays. Keep technical
  preservation separate from unresolved No.354 siblings and mixed quote bounds
  in three acts. V2 bindings preserve per-acquisition transport when bytes are
  shared by editions; legacy v1 research traces remain explicitly limited.
  Old frozen M0 files and v1 outputs are unchanged; M1-03A/G13/legal admission
  are not closed by this integration.

Scope: every file under `docs/`.

- Keep confirmed implementation, target architecture, external research, and hypotheses visibly distinct.
- Preserve source links, dates, edition scope, and evidence for time-sensitive legal or technical claims.
- Update `docs/README.md` when adding, renaming, or moving a document.
- Keep deterministic diagram sources beside rendered assets when both exist.
- Do not present a planned component as deployed without current code or runtime evidence.
- `guides/HTML_PREPARATION.md` documents the implemented parser-independent preparation
  slice. Keep its four-input preservation evidence separate from M1-03A legal
  hierarchy and G13 qualification. Opening-tag maps are not full token/provision
  locators; common CSS hints are not computed rendering or arbitrary-CSS support.
  Its downstream Housing Code control improves number evidence, not legal-tree
  coverage; Docling inline-group evaluation is distinct from native heading types.
- PRD v0.2 assigns edition reconstruction to M1. Processing permission is
  separate from legal admission; rejected/stale inputs may produce diagnostic
  drafts without changing M0-10 decisions or bypassing the frozen handoff.
  The original-plus-amendments input needs its own versioned contract. SanPiN
  reconstruction requires a chosen date, a verified amendment bundle, reviewed
  operations, official evidence and an explicit Legal Reviewer decision.
- M1 covers all five pilot acts in full at 2026-10-01 and 2025-01-01: ten
  act/date checks, with legal admission for each. Exclude changes effective
  after the historical target, including ones published earlier. A later
  snapshot needs evidence-backed reconstruction before historical admission;
  the owner's choice of dates is not legal approval or complete history.
- Follow `milestones/m1/M1_IMPLEMENTATION_PLAN.md` for the current 17-slice decomposition
  (M1-01–M1-15 plus M1-03A/M1-04A) and 13 milestone gates. The owner approved the
  parser-transfer requirement on 13.10.2026. M1-03A native engineering now
  passes all four original HTML inputs (59-FZ, Housing Code, No. 354, No. 491)
  and two non-pilot acts per declared family/format. Keep `original-four-v8`
  acceptance separate from `resolution-transfer-v5` qualification; preparation
  or additional acts cannot replace the mandatory original set. See
  `milestones/m1/03a/M1_03A_SHARED_STRUCTURE.md`; preserve the earlier premature-closure correction.
  M1-01's fixture-only contracts/compile CLI are implemented and documented in
  `milestones/m1/M1_01_FIXTURE_DRAFT.md`; PDF extract/compile is qualified in M1-04 under
  the recorded owner scope above. Docling/RapidOCR was an unimplemented target
  replaced by the owner. Qualify the pinned runtime/models before PDF rollout;
  discovery consumes shared extraction artifacts without importing heavy OCR.
  Keep M1's ten legal checks and closed-gold isolation separate from engineering
  completion. Compatible frozen-source changes need a reviewed update and replay,
  not a hash refresh that hides drift.
- Separate source-format adapters from the shared legal structure engine.
  Production profiles must not select/permit acts by hard-coded number, date,
  title, filename or source hash. Extract identity and compare the evidence-bound
  input claim; keep conflicts and unsupported structure unresolved.
  G13 requires two distinct non-pilot acts per supported family/source-format
  combination, not development examples, different editions or renamed fixtures.
  Pin final parser/profile versions, check independent structural controls and
  repeated full-document runs, and retain failures before changing rules.
  These permitted diagnostic documents do not enlarge the ten edition admissions
  or authorize reading closed retrieval gold. Missing/failed transfer evidence
  blocks M1/M2; M1-04A owns initial inferred OCR checks, with M1-06/M1-09
  consuming/extending them. M1-03A's paired official import keeps its own contract.
- Distinguish the legacy and new test versions of the integrated bank; do not
  infer shared document coverage. Treat commercial consolidated texts as
  discovery evidence unless the source-admission policy explicitly grants a
  stronger role.
- M0-10 keeps human comparison separate from corpus admission: critical
  amendment, temporal, consolidated-edition, or case-law-relation gaps remain
  fail-closed even when the reviewer reports the supplied document as “OK”.
- M0-10A treats the official day feed as discovery, not legal applicability.
  OCR is derived evidence; `amends` remains a source claim tied to the official
  PDF hash/page, and a stale candidate stays blocked until acquisition plus review.
- Before contradicting a reviewer on a time-sensitive control page, inspect its
  cache metadata and verify the current response against the primary official
  publication; a cached commercial page is not live-edition evidence.
- M0-11 keeps questions, labels, evidence and the complete review record under
  ignored local data; only IDs, split membership and content/review hashes are
  tracked. A hash check alone is not legal review; a completed `review.json`
  with reviewer, time, rationales and storage decision unblocks M0-12.
- M0-12's `assets/generate_m0_gate.py` renders all plan criteria from the tracked
  assessment and checks pinned evidence/code/fixture hashes. Exit 2 blocks M1;
  M0-10 timing uses `not_recorded` placeholders, explicitly accepted by the
  product owner on 01.10.2026. Count that measurement criterion as completed
  without repeat review; never present the placeholders as measured timestamps.
  Closed gold files are read as bytes for hashing only. The contract freeze
  records existing unversioned acquisition formats without inventing embedded
  schema versions; incompatible handoff changes require a new version.
- M1-02's `assets/generate_m1_inventory.py` prepares the ten act/date rows from
  retained source metadata and validated raw hashes without extracting legal text
  or changing frozen adapters. Search observations and the full review packet
  remain local. Pending permission templates have no signature/time and cannot
  authorize extraction. Known-ID replay, advertised history and empty search
  results do not prove completeness or historical applicability. Preserve the
  rejected M0 candidates and the 59-FZ case-law-sensitive blocker; M1-02 acceptance
  requires separate human inventory/permission decisions. Repeats are immutable
  and must not overwrite a human record; use a new output directory for new evidence.
- On 02.10.2026 the owner explicitly consented to all five diagnostic processing
  requests and inventory acceptance with disclosed gaps. Record this in the
  separate `data/m1/reviews/m1-02-owner-consent/decision.json`; retain the original
  pending packet. Respect that consent for the approved scope without asking
  again. The permitted 59-FZ input is ready for M1-03's control-date diagnostic
  path only; historical coverage and all substantive legal admission remain
  unresolved. Timestamp the recording honestly, not an invented chat-message time.
- M1-02's owner-facing packet is built by `assets/build_m1_02_review.py` under
  `data/m1/reviews/m1-02-review-v1/`. The owner remains the assigned Legal Reviewer;
  present readable Russian questions, official documents, exact page/provision
  references and a response form. Its source-review scope excludes final edition
  admission. Bounded historical research assets do not extend production adapters
  or waive frozen M0 checks. Preserve returned findings separately against the
  packet hash; draft autosave and technical QA are not human decisions. Never infer
  completed review time from an export timestamp or elapsed browser session.
- Use `assets/build_m1_02_review_v2.py` for the latest M1-02 reviewer packet.
  It embeds all evidence in one HTML file; document buttons open an in-page reader
  without network/new tabs/PDF plugins. Preserve v1 and any returned answers.
  The owner requested minimum reviewer work: engineers perform factual checks and
  prepare evidence; request only the remaining specific legal classification,
  with short excerpts and a proposed rationale that explicit agreement may accept.
  Missing evidence stays engineering work and remains blocked. This does not
  waive final review of all ten complete editions. Verify actual offline document
  opening with `assets/check_m1_02_review_v2.js`, not just file/link existence.
- On 12.10.2026 `legal-reviewer-owner` confirmed v2's specific 19-P-after-80-FZ
  classification for both targets. The actual response and hash/scope receipt are
  separate `human-review.json` / `human-review-verification.json` files under
  `data/m1/reviews/m1-02-review-v2/`; preserve the supplied recording timestamp,
  rationale and original packets. This question is resolved for the bound scope
  without repeat confirmation. Engineering completeness/applicability and all ten
  final admissions remain open; recording the decision imports no runtime relation
  and does not rewrite historical source/candidate blockers.
- M1-02 closes the input-route inventory with declared admission blockers, not
  M1's full-text or ten-edition legal-review work. The 12 October result is in
  `milestones/m1/M1_02_CLOSURE.md` and `data/m1/inputs/m1-02-completion/closure.json`;
  validate it read-only with `assets/validate_m1_02_closure.py`. It retains 27 new
  official publications, a fresh two-pass pilot and independent historical
  candidates. The new bank now includes No. 1242 in No. 491; preserve the old
  stale/rejected archive. No. 354's general text and No. 1979/931 application
  conditions stay distinct. No. 2's SanPiN targets are 282, 283, 286; 272 is a
  reference in the other sanitary rules. Bounded feed inspection preserves three
  strict validation failures and never proves all historical amendments absent.
- M1-03's implemented profile and full native 59-FZ replay are documented in
  `milestones/m1/M1_03_NATIVE_TEXT.md`. Report engineering accounting and determinism separately
  from legal admission. Keep JSON-scalar character locations distinct from raw
  bytes/PDF pages. Preserve earlier manifests and their historical questions;
  expose the original excerpt for every provision in the offline report.


- The final M1-03A native matrix uses `legal-structure/7`, law/code profiles `/5`
  and `government-resolution/3`: two retained held-out laws, two codes, and
  Resolutions25/416. These are full repeated compiler runs with independent
  controls; they are not six newly acquired bodies. Keep earlier failures
  (quoted whole annex, Cyrillic-lookalike Roman marker, legacy merged paragraphs,
  unqualified footnote shape) visible. Native engineering is not milestone-wide
  G13 completion, arbitrary HTML support, PDF/OCR qualification or legal admission.
  Source raster formulas remain images; numeric footnote support does not imply
  other markers. Retain the Housing item `1.1-1` semantic correction.
- The separate preselected native-HTML expansion probe on 15 October 2026 passes
  only 3/6 with the frozen `55b93ca` compiler. All six retain source integrity;
  No.261-FZ, No.410 and No.47 retain structural failures. Historical 4/4 and
  transfer results do not establish arbitrary-act coverage. The owner's pause
  and self-contained Russian continuation context are recorded in
  `milestones/m1/03a/M1_03A_PARSER_HANDOFF_2026-10-15.md`; the proposed LLM hybrid and new experiment
  are unapproved, unimplemented options.
- The separately owner-authorized local Documind schema-layer probe is documented
  in `milestones/m1/03a/M1_03A_DOCUMIND_EXPERIMENT_2026-10-15.md`. Full Housing Code stock requests
  exceed both tested models' declared contexts; four complete 59-FZ schema controls
  (Gemma/Qwen, stock/guided) fail the legal-schema gate. No downstream extraction
  or production integration was performed. This bounds the tested configuration,
  not every possible model/provider, and does not close M1-03A or qualify PDF/OCR.
- The broader 15 October parser research is in `milestones/m1/03a/M1_03A_PARSER_OPTIONS_2026-10-15.md`.
  Both official banks expose separate typed structure sidecars. Seven retained
  inputs / 3,906 nodes pass anchor/parent checks and fresh text responses match
  the original assets byte for byte. This is source research, not a production
  adapter or G13 completion. Source `unit=вложение` can also mean notes, so do not
  equate it with approved text. Indigo has automatic hierarchy import upstream
  of Bluebell; PageIndex Flash can build an outline without an LLM. Neither fact
  establishes Russian legal-leaf coverage or supersedes preserved failures.
- The owner-authorized sidecar experiment is documented in Russian in
  `milestones/m1/03a/M1_03A_OFFICIAL_STRUCTURE_EXPERIMENT_2026-10-15.md`. Its separate scripts
  under `docs/assets/` preserve 3,906 source nodes, pass all 3,894 explicit-number
  checks and technical accounting on seven acts. Source JSON omits quoted-law
  subtrees and some form lists; 261-FZ's quoted articles and No.47's a–d list
  are confirmed examples. Three acts have no detected gaps in the bounded scans,
  not full legal acceptance. Preserve 147 protected files and earlier attempts;
  do not present the experimental format as a production contract or G13 result.
  User-facing analytical overviews and experiment reports must be in Russian.
