# Documentation instructions

- `research/ZAKON_LEGAL_AI_TAKEAWAYS_2026-10-23.md` retains the Zakon.ru
  article takeaways and two primary texts read on 22 October 2026. Keep verified
  facts, project implications and proposed tests separate; the note grants no
  corpus admission, implemented capability or milestone-scope change.

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
- Selection profile `batch-04` (`BATCH4_QUOTAS`): no code quota (no `--code-candidates`), FZ 3, decree 1,
  PP 2, RP 2, ministry 3, pages 3..200, at least 4 acts of 20+ pages; excludes batches 1-3 (refills, failures, days).
- Selection profile `batch-05`: batch-04 quotas, excludes batches 1-4, plus soft preferences `preferred_pages_min 5`
  and `one_per_issuer_day` (type + feed `signatoryAuthorityId` + `publishDateShort`; fallback `name:` + complexName
  prefix). Each phase (long share first) runs with them, then without; `soft_fallbacks`/`soft_fallback_counts` record
  relaxed picks. Off by default: batch-04 reproduces from its feed cache (test). New feed cards carry `issuer` and
  `publication_date`. `refill` does not apply the preferences. The batch directory must exist before the run
  (the feed cache is written into it).
- Selection profile `batch-06`: batch-05 settings unchanged, `prior_batches` 01-05 (test pins it and profiles 01-05).
  Pool slug: a number without leading digits (FNS «ЕД-7-20/957@») uses the serial after the last «/».
  `summarize_m1_04a_ocr.py --table-stats` (batch 6 on) adds regions, tables, `grid: "unresolved"` tables and
  rotation-retry pages per act; batch 1-5 summaries reproduce without it.
- `refill` also replaces an acquired act (receipt present) whose `failures/<eo>-ocr-<run>.json` has
  `stage: ocr` (written by hand after a failed OCR run; reason `ocr_failed: ...`); first used for batch-05 141н.
- `milestones/m1/04a/M1_04A_POOL_BATCH_4_2026-10-23.md` is the batch-4 first pass, the first measure of frozen v2
  (+ v1, `/7`), not G13/Task 3: 1579/1546/35 of 2465. Two near-identical Mintrans estimate-table orders (954 regions)
  hold 864 of 886 v2 errors; always quote the without-them figure (1489/1511, 98.5%) and the diversity caveat.
  `cross_scope_v2` 20 = second attached document named `A/AN` vs gold `S2` (naming, owner decision open), not text
  moved. One new class; the new-class counter starts at batch 4 and is 0. The classifier gained batch-4 rules
  (second attached document, restarted «01.» lists, line between tables at the root, footer code); batch 1-3 class
  files reproduce byte for byte. Batch 4 is now development.
- `milestones/m1/04a/M1_04A_POOL_BATCH_5_2026-10-23.md`: batch-5 first pass of frozen v3.1 (+ v2): both 2144/2268,
  identical owners; quote the without-rp-1099 figure (1291/1296) and the OCR-failure selection bias. v3.1 rules
  never fired (check evidence `restart`/`list_line`/`page_mark` in outputs). `cross_scope_v2` 3, one new class;
  counter still 0. Classifier batch-5 rules (`_batch5_cause`, only where earlier rules give no class): section
  heading as OCR Text, footnote given by its mark to another annex; batch 1-4 class files reproduce byte for byte.
  `build_m1_04a_catalog.py` `POOL_STATUS` has batch-05 (development).
- `milestones/m1/04a/M1_04A_POOL_BATCH_6_2026-10-24.md`: batch-6 first pass of frozen v4 (+ v3.1): 1844/1830 of 1925;
  quote the without-prikaz-37 figure (1634/1637) and the gold memory-exposure limitation. `cross_scope_v2` 0, one new
  class (dotted-section gap), counter still 0. Rules fired: v4 `table_row`, `<sup>` marks, v3 `restart` once;
  `list_line`/`roman_sequence` never. Classifier batch-6 rules (`_batch6_before_scheme_list`, `_batch6_cause`): dotted
  gap, footnote to another point, subpoint closed early, signature heading of an attached document; batch 1-5 class
  files unchanged (21 files equal before/after). `POOL_STATUS` has batch-06 (development).
- Cycle 6 A1: dev regression covers 67 documents (+ `BATCH_6` on frozen `20261023-batch-06-gold-freeze`). Baseline
  of frozen v4 `…/20261024-dev-regression-cycle6-baseline/`: 13598/13730 no_section and strict, `cross_scope_v2` 0;
  old 56 11754 with rows/errors equal to `…-v4`; batch 6 1844/1925 (minekonomicheskogo-37 210/288, rp-356 82/84,
  pp-887 571/572). Track B gates with `--baseline` it.
- Cycle 6 B1 (prototype, VERSION unchanged until B5): a dotted «N.M» after «N.K» with a gap of 2-3 («5.3» after
  «5.1», «5.2» not printed) is a sibling (parent by prefix, cost 2 + gap) instead of the unexplained nesting into
  «5.1». Regression `…-cycle6-b1`: 13658/13730, minekonomicheskogo-37 210 -> 270, batch 6 1904/1925, no drops,
  no other document changed.
- Cycle 6 B2 (prototype): footnote marks are searched per region and only before the footnote (a paragraph
  joined across a page break no longer owns an earlier page's footnote; `candidates` now counts regions). One
  mark on several regions of the footnote's page in one scope -> their common owner (evidence
  `footnote_owner_common`; fires twice, minekonomicheskogo-37 12.10/25.4, as its gold notes). Regression
  `…-cycle6-b2` (last-mark only, 13659) and `…-cycle6-b2-r2`: 13661/13730, minekonomicheskogo-37 273, batch 6
  1907/1925, no drops, no other document changed. Footnotes whose mark OCR lost (35.4/35.5/36.4) stay wrong.
- Cycle 6 B3 (prototype): `requisite_like` also accepts an agreement signature heading (`SIGNATURE_HEADING`:
  «Подписи и реквизиты Сторон», «Адреса и реквизиты сторон», any case) and the signature place «От <Capitalised>»
  (beside «За …»), still short and unterminated, so the requisite block opens there. Regression `…-cycle6-b3`:
  13663/13730, rp-356 84/84, batch 6 1909/1925, no drops, no other document changed.
- Cycle 4 A1 (owner decision 23.10.2026, convention v2 §6; old §6-8 renumbered 7-9): opt-in `--attached-ordinal`
  (evaluator, `rescore`, classifier via the run summary) renames each top-level non-`A` scope (`S`, `S<k>`, `A/AN`,
  `A/AN<n>`, after the single-document/single-annex equivalences) to `S`, `S2`... by first appearance in region
  order, separately for gold (primary owners, then alternatives) and prediction; the tail (`S/AN<n>/...`) is kept.
  The eval result records the heads (`attached_ordinal`); the classifier reads them for its evidence rules and
  `cross_scope_v2`. `freeze` records `attached_ordinal_equivalence` for batches after batch-04 (override
  `--[no-]attached-ordinal`); batches 1-4 reproduce byte for byte without it (batch-2 first-pass class files already
  differed at HEAD by one reworded label). Dev regression defaults it on (`--no-attached-ordinal`). Development
  rescore `20261023-batch-04-rescore-cycle4`: v2 1599/2465 (pp-1688 48, pp-813 183), v1 1566, `cross_scope_v2` 0;
  the 64.1% ledger entry is unchanged (batch-4 report §11).
- Cycle 5 A1 (owner decision 23.10.2026 on batch 5, convention v2 §6): rubrics «I. Подпрограмма …» and row numbers
  inside table annexes are annex text (batch-5 gold already so). Dev regression covers 56 documents (+ `BATCH_5` on
  frozen `20261023-batch-05-gold-freeze`, rp-1099 = stitched `.gold.txt`). Baseline of frozen v3.1
  `…/20261023-dev-regression-cycle5-baseline/`: 11623/11805 no_section (strict 11556), `cross_scope_v2` 3; old 45
  9479 with rows/errors equal to `…-v3-1`; batch 5 2144/2268 (rp-1099 853/972, rp-3721 90/94 cross 3, minnauki 72/73).
- Cycle 5 B4: prototype v4 `ocr-logical-structure/4-experiment` (sha256 52c20ab5… CRLF working copy, LF 12f1ee45…,
  blob 6df9f547) frozen in `data/m1/m1-04a/experiments/20261023-prototype-v4-freeze/`; regression
  `20261023-dev-regression-v4` vs the cycle-5 baseline (v3.1): 11754/11805 no_section and strict (v3.1 11623/11556),
  `cross_scope_v2` 3 -> 0, exit 0; rows/errors equal `…-cycle5-b3`. Report `milestones/m1/04a/M1_04A_PROTOTYPE_V4_2026-10-23.md`
  (development, batch 5 included; batch 6 is the measure).
- Cycle 5 B3 (prototype): `next_roman_section` — an unmarked body paragraph «V. Капитализированное …» (OCR Text,
  too long for `heading_like`) opens section V (evidence `roman_sequence`) only when sections I..V-1 are open in
  the scope and the last is V-1; no gap, no first «I.», nothing mid-sentence. Regression `…-cycle5-b3`:
  11754/11805 no_section and strict, minnauki-697 73/73, batch 5 2268/2268, `cross_scope_v2` 0, no drops. Over the
  56 documents `table_row` fires only in rp-1099 (22) and pp-931 (6), `roman_sequence` once; `restart` never.
  Guard (B4 step 0): the rule also needs <= `ROMAN_TEXT_MAX` (1000) characters and no final «.;:!?,» (the real
  heading is 590 characters, so a 200/500 cap would drop it); regression `…-cycle5-b4-guard` equals `…-cycle5-b3`.
- Cycle 5 B2 (prototype): a footnote's mark is also found as HTML `<sup>N</sup>` (tables print it so); the owner
  stays the latest preceding body paragraph with the mark, a footnote without one stays unowned. Cause of the
  batch-5 transfers: the second list's marks were `<sup>`, so «¹» matched the first list. Regression
  `…-cycle5-b2`: 11753/11805 no_section (strict 11743), `cross_scope_v2` 3 -> 0, rp-3721 94/94, rp-1099 972/972,
  batch 5 2267/2268, no drops, no other error changed.
- Cycle 5 B1 (prototype, VERSION unchanged until B4): `table_rows` — in an annex scope (`…/AN<n>`) that opens with
  a table (no marker before its first table), a roman/«N.»/«N.M»/paren/letter marker between its first and last
  table is a table row (marker `none`, evidence `table_row`); named units, markers after the last table, an annex
  whose first marker precedes the table and approved texts `S` are unchanged. Regression `…-cycle5-b1` (failed,
  kept: rp-2728 −1, its batch-4 gold gives the row «1.» of the table-shaped approved text `S/1`); narrowed to annex
  scopes `…-cycle5-b1-r2`: 11747/11805 no_section (strict 11737), rp-1099 970/972 (+117), pp-931 +7 (`S/AN6`
  rows), batch 5 2261/2268, `cross_scope_v2` 3, no drops, no other error changed.
- Cycle 4 A2: `run_m1_04a_dev_regression.py` covers 45 documents (+ batch 4 `BATCH_4` on its frozen gold, families
  by slug prefix), single annex and attached ordinal on. Baseline of frozen v2
  `data/m1/m1-04a/experiments/20261023-dev-regression-cycle4-baseline/`: 8614/9537 no_section (strict 8603),
  `cross_scope_v2` 0; old 34 rows and errors identical to `20261022-dev-regression-v2` (7015/7072), batch 4
  1599/2465 = the A1 rescore. Track B gates against this summary with `--baseline`.
- Cycle 4 B1 (prototype, VERSION unchanged until B3): a marker with a leading zero («01.», «02)», «001.») is a
  list line (marker `none`, evidence `list_line`) and stays in the current unit; «N+1.» right after such a line
  («10.» after «09.») continues it. «1.» after «N.» (N > 1) of the same scope with a table or an unmarked
  Section-header/Title between them gets `restart` and may take the level of «N.» (cost 1.0 instead of the 10.0
  unexplained nesting); «1)», «а)», «N.M» unchanged. Regression `20261023-dev-regression-cycle4-b1-r2`
  (sha f091e9d3…): 9478/9537 no_section (strict 9467), Mintrans 107 47 -> 476/476, 136 43 -> 478/478, batch 4
  2463/2465, `cross_scope_v2` 0, no drops, only those two documents changed. `…-b1` has the same scores (restart
  evidence was then also written without an earlier «N.»). The restart rule changes no owner in the 45 documents.
- Cycle 4 B2 (prototype): a text paragraph whose neighbouring body items (pictures skipped) are both tables is
  never a position-only signature or requisite-block opener, so «Стоимостные показатели» between tables follows the
  current unit; a page header/footer that is a file name («200716A9.doc», `PAGE_MARK`) and not running noise is a
  page mark of the scope root and opens no continuation. Regression `20261023-dev-regression-cycle4-b2`
  (sha e88cbc9a…): 9479/9537 no_section and strict, batch 4 2464/2465, `cross_scope_v2` 0, no drops; changed only
  Mintrans 107/136 (strict 476/478) and rp-2023 (28/28). Known limitation: rp-2728 region 3.1, one OCR table
  region mixing a repeated header, the end of item 1, item 2 and «Итого» (gold `S`, annotator doubt), goes to `S/1`.
- Cycle 4 B3: prototype v3 `ocr-logical-structure/3-experiment` (sha256 556b4d62… LF, blob 68f7167f; behaviour of
  a72ce90) frozen in `data/m1/m1-04a/experiments/20261023-prototype-v3-freeze/`; regression
  `20261023-dev-regression-v3` 9479/9537 no_section and strict (v2 8614/8603), `cross_scope_v2` 0, no document
  below v2; rows and errors equal `…-cycle4-b2`. Report `milestones/m1/04a/M1_04A_PROTOTYPE_V3_2026-10-23.md`
  (development, not progress; batch 5 is the measure).
- Cycle 4 final-review fix: prototype v3.1 `ocr-logical-structure/3.1-experiment` (sha256 0093599a… CRLF working
  copy, LF 1794a748…, blob 71f11a73) frozen in `data/m1/m1-04a/experiments/20261023-prototype-v3-1-freeze/`; the v3
  freeze stays as history (never measured on a new batch). «N+1.» after a leading-zero list line continues it only
  past a digit rollover (`continues_list`: «10.» after «09.») or once rolled over; «5.» after «01.»…«04.» is a point.
  The classifier makes paths canonical before ordinal renaming (`read_paths(..., attached)`); batch 1-4 class files
  still reproduce. The dev regression records repo-relative prototype/baseline paths (`recorded_path`). Regression
  `20261023-dev-regression-v3-1` vs v3: 9479/9537, rows and errors identical, exit 0. Batch 5 measures v3.1
  (report `M1_04A_PROTOTYPE_V3_2026-10-23.md` §8).
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
  Fix round 1 (`…-cycle3-b2-r2`, same scores): an act word names the act only for the act's own kind (header line
  «ПОСТАНОВЛЕНИЕ»/«ПРИКАЗ»/…, else the first approval caption «УТВЕРЖДЕН приказом …») or with «настоящему»; unknown
  kind -> act. A bare number («Приложение 2», no №/N/Н/Ν) needs a «к …» reference on the line or next paragraph, a
  Page-header, or being the first text paragraph of its page. A final dot is accepted after «г.», DD.MM.YYYY or
  «№ <number>»; a comma/hyphen/function-word tail is a broken sentence. Attached-document captions need a
  capitalised referent; with two attached documents the annex goes to the last opened one (known limitation).
- Cycle 3 B3 (prototype): `SECTION_NAMED` accepts uppercase «РАЗДЕЛ» and OCR Roman letters (Cyrillic Х, Ukrainian І),
  with or without a dot after the number («РАЗДЕЛ I ОБЩИЕ ПОЛОЖЕНИЯ», «РАЗДЕЛ ІХ …»). As a named unit of rank 0 it
  closes the previous section's chapter/article stack, so the heading no longer falls into the last article.
  Roman «I. …» sections without the word are unchanged. Regression `20261022-dev-regression-cycle3-b3`: КАС strict
  9 -> 2855/2855, total 6976/7072 no_section and strict, `cross_scope_v2` 0, only code-21-2015 changed, no drops.
  Untested: a document mixing «РАЗДЕЛ I» headings (`section_named`) with Roman «I.» points (`roman`) — both are
  rank 0 and may nest unexpectedly; none in development, check on batch 4.
- Cycle 3 B4 (prototype): after the depth solver, (1) a run of unmarked capitalised unterminated lines (no final
  «.;:!?», «,» or hyphen; not a requisite, signature, caption or OCR Caption region; <= 500 characters) that follows
  a paragraph ending «.»/«;» and is immediately followed by a numbered point «N.»/«N.M» (no table or picture
  between) belongs to that point's parent, but only when the parent is a section or named unit (Review Focus 5);
  without an enclosing section the line stays with the open point. (2) An unmarked paragraph inside a «1)»/«а)»
  subpoint that starts with a capital letter returns to the point when the previous paragraph ended with «.», or
  with «;» and the paragraph itself ends with «.»; only list levels the next marked paragraph does not continue
  close, and later unmarked paragraphs up to the next marker follow. (3) A dotted «N.M» may close an open
  paren/letter subpoint. (4) Uppercase «ГЛАВА»/«СТАТЬЯ», OCR Х/І in chapter numbers. Regression
  `20261022-dev-regression-cycle3-b4-r2`: 7020/7072 no_section and strict (+44: minkultury-1321 +42,
  fsnson-282 +2), `cross_scope_v2` 0, no drops. `…-b4` (failed, kept): favt-547 −5, «Схема N» captions before
  a picture were taken as subheadings.
  Fix round 1 (`…-cycle3-b4-r3`, current): subheading length <= 200 as body text, <= 500 only with OCR
  Section-header/Title; a body-text subheading also needs two header-category subheading runs in the same scope
  (an OCR-cut sentence without its dot otherwise qualifies); captions by text («Схема 2», «Рисунок 1 - …»,
  «Рис. 3», «Таблица», «Форма N», «Диаграмма», «График» + number) and labelled lines («Адрес: …») are never
  subheadings; no subpoint closing inside an unbalanced «…» opened in the subpoint or on a paragraph ending «»»/«».».
  Score 7015/7072 (minkultury 447, −5 vs r2: Text-category subheadings of 214-452 characters 8.4, 9.9, 11.4, 11.9,
  14.5 are now left with the previous point), still no document below b3. Known limitations (pinned in tests): a
  subheading after a table or an editorial note «(в ред. …)» is missed; a capitalised second paragraph of the last
  subpoint (previous ends «.») goes to the point.
- Cycle 3 B5: prototype v2 `ocr-logical-structure/2-experiment` (sha256 081c95f9…, blob e8573d8f; behaviour of
  48fd085) frozen in `data/m1/m1-04a/experiments/20261022-prototype-v2-freeze/`; regression
  `20261022-dev-regression-v2` 7015/7072 no_section and strict, `cross_scope_v2` 0, no document below the v1
  baseline. `run_m1_04a_dev_regression.py --baseline SUMMARY` writes `baseline-comparison.json` and exits 1
  when a document falls (no_section/strict down, `cross_scope_v2` up, regions changed or missing). Report:
  `milestones/m1/04a/M1_04A_PROTOTYPE_V2_2026-10-22.md` (development, not progress; batch 4 is the measure).
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
  implementation or acquisition. Keep the slice plan (18 slices since M1-04B) and G13 synchronized.

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

- `milestones/m1/04/M1_04_DENSE_TABLES_2026-10-23.md` records the batch-5 OCR
  failures: two were impossible table grids (now degraded per table, both acts
  pass), the third (Minfin 141n) is a blank rotated form looping on empty rows.
  The opt-in rotation retry (OCR-Lab client + normalizer re-derivation) completes
  it (3 pages turned cw90); 0/12 forced turns of upright pages were accepted.
  Rotated pages read without a loop and upright looping blanks remain open.
  Owner decision 23.10.2026: M1-04A batches after batch 5 run OCR with the
  rotation retry; `assets/run_m1_04a_ocr.ps1` defaults `-OcrConfig` to
  `data/m1/ocr.rotation-retry.local.json` and records it (with sha256) in the
  raw summary. Batches 1-5 stay as frozen, without it.
- `assets/ocr_lab_rotation_retry.patch` retains the OCR-Lab client change for the
  rotation retry (before `42ddf34a…`, after `6beed388…`, compared without `\r`;
  OCR-Lab has no git). Apply like the picture patch, with `--ignore-space-change`.
- `plans/2026-10-23-m1-04b-ocr-runtime.md` (owner request 23.10.2026) plans M1-04B:
  a minimal dots.mocr runtime inside Legal RAG (own image without the TeleOCR base,
  one service, dots.mocr-only client, verified weights) with an unchanged output
  contract and qualification against the OCR-Lab runtime. Only Task 0 (the patch)
  is done. Owner decisions 23.10.2026: weights inside the project
  (`data/ocr/dotsmocr/model/`, ignored, hash-verified), code in `ocr/dotsmocr/`,
  M1-04B is a slice of the M1 plan (gates unchanged, G04 evidence), start only
  after M1-04A is complete; until then new OCR keeps the OCR-Lab runtime.

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
- Follow `milestones/m1/M1_IMPLEMENTATION_PLAN.md` for the current 18-slice decomposition
  (M1-01–M1-15 plus M1-03A/M1-04A/M1-04B; M1-04B added 23.10.2026) and 13 milestone gates. The owner approved the
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
