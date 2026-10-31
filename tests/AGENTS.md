# Test instructions

- `corpus/test_ocr_logical_structure.py` now exercises maintained production
  `ocr_owner_structure.py`, not the retained experimental copy.
  `corpus/test_ocr_owner_ast.py` covers actual compiler dispatch, deterministic
  compilation/replay, source accounting/locators, unresolved identity/owners,
  table preservation, explicit unit kinds, superscript number metadata and
  rejection of changed source/bindings/parents/anchors. The repeated-parser
  validator checks conversion consistency; it is not independent qualification.

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
  Batch-05 soft preferences: short act only to fill a quota, one act per type/issuer/day unless needed, long share
  kept, defaults off leave results identical; the batch-04 reproduction test skips without local data.
  Batch-06 profile = batch-05 + prior batch 05; frozen batch-05 selection reproduces from its feed cache (skips without data).
  Batch-07 profile = batch-06 + prior batch 06; frozen batch-06 selection reproduces likewise.
  Batch-14 (no network): profile = batch-13 + SanPiN decade quotas and the tree filter; `sanpin_title` positives
  and negatives (ГН, amendments, «изменений № 1 к СанПиН»); `freeze-sanpin` over all pages with decade types,
  write-once and checksum refusal, short or foreign listings refused before writing; `tree_reason` per category;
  `ips_tree` reads the actual edition of the single exact match; tree `enrich` stops at the quotas; refill takes
  only checked acts without a tree; a full run with frozen SanPiN, rejected trees, reserves and a SanPiN refill.
  Batch-15: profile = batch-14 + 3/3 SanPiN, 1 resolution, `require_title`; `title_missing` only when required
  (empty and quote-only titles), recorded by `select_pool`, honoured by `refill`; singular «дополнения» is
  amending; `ips_title` from card `name` or `description`; with the tree filter an untitled act is looked up and
  judged by `ips_title` (missing / amending / ok), also inside tree `enrich`.
  Batch-16: profile = batch-15 + prior batch 15; the catalog lists batch 16 and records batches 14 and 15 measured
  then development (step 16, 28.10.2026).
  Batch-21: batch-16 settings without SanPiN or laws (2+2+2 acts, 4 orders), prior batches 1-20; the catalog lists batch 21
  and records batch 20 measured then development.
  Batch-22: batch-21 settings with 4 resolutions, 5 orders, 3 government orders (types with the most first-check
  errors), prior batches 1-21; the catalog lists batch 22 and records batch 21 measured then development.
  Batch-23: batch-22 settings with 5 government orders, 5 orders, 2 resolutions, prior batches 1-22; the catalog lists
  batch 23 and records batch 22 measured then development.

- Cycle 8 C1-C3 tests in `corpus/test_ocr_logical_structure.py` (inserted chapter/section/§ numbers, editorial
  notes owned by the named unit with negatives, list restarted after a closing sentence with «;»/quotation
  negatives) fail on the frozen v6.1 copy and pass on the working prototype.

- `corpus/test_m1_04a_gold_footnotes.py` covers the footnote-owner derivation (owner 28.10.2026): mapped regions
  get the marked point (continuation `+` kept, alternatives allowed), unmapped acts are exact copies, the receipt lists
  derived gold, frozen gold and map; an unpinned map, an absent region, a wrong `from` owner or a malformed owner is
  refused before writing; write-once.
- `corpus/test_m1_04a_gold_forms.py` covers the §6.1 forms derivation: mapped roots (owners and alternatives, tails
  kept), exact copies without a map, a map not pinned to the frozen gold refused, write-once outputs and receipt rows.

- Step 24: bare decimal form positions require an immediately following same-page parenthesised field caption;
  a bare decimal over a table opens no point. Sheet-side marks (Text/Page-header) and service-stamp places belong
  to the form, without joining a previous page's field. Bold Text subheadings use the section; a bold terminated
  sentence stays in the point and opens no attached document after a signer; building leaves extraction text
  unchanged. Form completion / reply-address blanks
  open the requisite tail. Dev regression lists 237 documents (batch 23 on frozen `gold`).
  Continuation E-F: short caption runs between tables stay in the form's receipt position; a standalone name/signature
  block before that numbered position belongs to the form (name caption as Text or Table), while an explicitly
  numbered signature position keeps its captions. «Исполняющий обязанности …» before initials is an act requisite.
  Batch-23 acceptance compares integer counts for EACH document, strictly >99% in both strict and no_section.
- Step 23: Roman treaty articles and a quotation across a page footer; an annex of a form inside the attached
  document (also with a long caption tail); a subheading after a page mark; a second fill-in list of a form. Dev
  regression lists 225 documents (batch 22 on `gold`).
- Step 22: form parts «А.», «Б.», «В.» with their own points, blanks under a field or a part heading, «Подпись
  представителя …» to the form root, a lone «А. …» opens nothing; a table plan whose rubrics skip numbers («I.», «III.»,
  «1.», «32.») reads them as rows; a field ending «20__ г.» hands the table under it to the form. Dev regression lists
  213 documents (batch 21 on `gold`).
- Step 21.7 H: an approved text that is a table reads its cut-out row «1.» and a last «4.15. …» as text (`S`), a «1.»
  after the last table is a point, and one with «I.» sections keeps its points (the old «keeps its row numbers» test
  and the step-25 `S/1` expectation changed by the owner decision).
- Step 21.7 G: «в пунктах 15 и 15.1» makes «15.1» with its «1)», «2)» a peer of «15»; without it «15.1» nests.
- Step 21.7 E: an unnumbered heading and table between «5.1.» and «5.3.» go to the annex root; before «5.2.» they stay.
- Step 21.7 D: dotted «1.1.», «2.1.» over tables are rubrics when another table keeps «2.2. …» as its caption;
  without such a caption they stay points.
- Step 21.7 B-C: a headed table after a formula line and one with a 307-character plain title go to the section; a
  «2. …» rubric between table parts numbered back from point 87 is not a point («88.» there still is).
- Step 21.7: a headed table the point only names («… приведены в таблице 1.3.») goes to the section; one introduced
  with «:» stays. The dev regression scores the three FGOS and sanpin-2-2021 on `gold-tables`.
- Step 21.6: a plain-text title before «Таблица 3.13» makes a headed table that goes to the section.
- Step 21.5: an approval sheet after the forms goes to the act; a field line with text and blanks, its caption and the
  form's sentence; a declaration page head, typist mark and time stamp are page marks carried into the form they head.
- Step 21.4: reference ranges, a root heading between root points, a note about «настоящий перечень», a form's
  signer captions and date line, a dash item closing its sibling's letter list, a quoted «Статья 25⁸ …» heading
  ending with an inner title quote.
- Step 21.3: caption, legend, «где» and table-notes cases under subpoints; numbered «1)» notes under an annex notes
  heading; footnotes without a mark get the page's document (the cycle 5/6 «stays unowned» expectations changed to it).
- Step 21.2: a plain-digit Footnote and its «а) …;» list continuation find the marked point; «5590030 (1.4)» is a page
  mark and point 2 continues on the next page; «Врио Министра» is the act's signer; «6.Сообщение» is part 6.
- Step 21: a headed table block after a finished point goes to the section (with lines under it), an introduced
  («… в таблице 1.1:», «ниже») or named table stays, no enclosing section keeps the point; a title Caption is a
  heading, «Таблица 2.1. …» alone is not. Dev regression lists 203 documents.
- Step 20 E: `test_first_pass_alarms_name_acts_a_prototype_mostly_misses` (only prototypes, below 0.9 of regions).
- Step 20 C/D: «Примечание:» under a table inside point 8.4 stays in 8.4 (the cycle-10 plural «Примечания» negative
  stays); tables «Таблица 1.1/1.2» printed after section II belong to point 1.2 that names them, «Таблица 3.1» under
  its own point keeps it.
- Step 20 A/B: «Приложение ⏎ Утверждены …» in one region opens `S`; an approving act without a recognised caption
  opens `S` at the next page's heading after the signature; an annex caption there still opens `A/AN1`, and an act
  that approves nothing keeps its text. Dev regression lists 202 documents (batches 17-19 on `gold`, no
  sanpin-6-2025).
- Step 17 B: point-reference lines inside «1.5.» are its text, a dotless capitalised «2.1.8 Организации …» and a
  dotless lowercase «12.1 принятие …» under «12.» keep their markers.
- Step 17 A: the paragraph after the last dotted «7.1.5.» stays in it (owner 28.10.2026); dev regression lists 179
  documents (batch 15 on `gold-dotted`, batch 16 on `gold`); `test_m1_04a_gold_footnotes.py` derives a later copy
  (`--base gold-footnotes --suffix gold-dotted --map dotted-map`) pinned to the earlier copy.
- Step 16 C5 test: a footer printed on two pages is a page mark of the act (`A`) and the interrupted point still
  continues; a footer printed once keeps the point.
- Step 16 C4 test: rows «3.»-«5.» after the last table part going on from the cut-out «1.», «2.» are annex text
  (`table_row`); a «1.» there is a point.
- Step 16 C3 test: Section-header subheadings ending «:» and after an unterminated point go to the section; a
  body-text line after an unterminated point stays its cut sentence.
- Step 16 C2 tests in `corpus/test_ocr_logical_structure.py`: a paragraph after the last dotted «7.1.5.» returns to
  «7.1.» (after «7.1.4.» followed by «7.1.5.» it stays); after a nested «а)»-«б)» list it goes to the list's owner
  «2)»; after an unterminated marked «19)» a same-page sentence goes to the point, on the next page it stays;
  unterminated unmarked lines inside «а)» close nothing.
- Step 16 C1 tests in `corpus/test_ocr_logical_structure.py`: OCR «б)» for «6)» after «5)» reads as the sixth
  subpoint and its own «а)»-«в)» nest under it; «3)» after «ж)» reads as «з)»; genuine letter and digit lists keep
  their reading.
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
  `test_batch5_error_classes_from_evidence_only` pins the batch-5 rules (roman heading as OCR Text, footnote to
  another annex by its mark) and that earlier classes keep priority.
  `test_batch7_error_classes_from_evidence_only` pins the batch-7 rules (attached document's annex given the act
  annex with the same number, read via `raw_predicted`; OCR letter «з)» as «3)») and earlier-class priority.
  `test_batch6_error_classes_from_evidence_only` pins the batch-6 rules (dotted-section gap, footnote to another
  point, subpoint closed early, attached-document signature heading) and earlier-class priority.
  `test_dev_regression_baseline_comparison_flags_drops` covers `--baseline`: per-document drops
  (no_section/strict down, `cross_scope_v2` up, region count changed, missing) and CLI exit 1.
  Cycle 4 A1: `attached_ordinal` tests (both files) pin ordinal heads by first appearance, `S, S2` == `S, A/AN`,
  merged/moved second document = error + `cross_scope_v2`, `S/AN<n>` untouched, one document as before; freeze
  default only after batch-04, rescore/regression opt-in/opt-out and the classifier's renamed reading.
  Cycle 4 A2: the regression set has 45 documents (batch 4 on `.gold.txt`, families by prefix).
  Cycle 5 A1: 56 documents (batch 5 on `.gold.txt`, rp-1099 the stitched file).
  Cycle 6 A1: 67 documents (batch 6 on `.gold.txt`).
  Cycle 7 A1: 78 documents (batch 7 on `.gold.txt`).
  Step 12 A: 122 documents (scan batch 11 on `.gold-quoted.txt`).
  Step 13 A: 133 documents (scan batch 12 on `.gold.txt`, prikaz-fsb-641 the stitched file).
  Step 13 B1-B3 (`test_ocr_logical_structure.py`): a 400-character Text rubric is a subheading only in a
  corroborated scope and up to `SUBHEADING_STYLED_MAX`; «Приложение: 1. …» before «2. …» is item 1 (not without
  «2.», with «2)», or a three-word label) and «Примечания: 1. …» in an article stays its note; form signature
  captions and «Директор» open the requisite block, «(фамилия, имя, отчество …)» and a quoted «М.П.» do not.
  The cycle-7 negative now expects «М.П.» after a point with text to open the form's block.
  Scan batch 13: `test_catalog_records_batch_13_checked_then_rework` (catalog lists batch 13, measured then
  development).
  IPS tree coverage (`corpus/test_ips_tree_coverage.py`, no network): organ groups and decades, `required_n` with the
  finite-population correction (97/96/81/29/5), small organ groups merged, seeded plan, Wilson and stratified shares
  (census adds no variance), screen record of the actual edition, resumable screen with cache reuse and estimate.
  Scan batch 12 evaluator fix: `test_ordinal_single_annex_numbers_the_only_annex_of_an_act_annex_document` (opt-in,
  `A/AN2/AN` = gold `S2/AN1`, no transfer with `result_heads`, two annexes keep their numbers, default after batch-12).
  Step 12 B1-B4 (`test_ocr_logical_structure.py`): typist marks in footers open no point and belong to the scope
  root (job codes with and without a slash; «№ 553/15», «Стр. 12» are not); a bare «Приложение № 2» before
  «УТВЕРЖДЕН» heads `S2` («к Формату …» stays `S/AN1`); a 230-character lowercase sample caption «… утвержденному
  приказом …» opens `A/AN2/AN2` (not without «№» or with a final dot); «Высшее должностное лицо …» opens a form's
  requisite block (a terminated «Должностное лицо, …» sentence stays in the point).
  Cycle 5 B1 (`test_ocr_logical_structure.py`): rubrics «I. Подпрограмма …» and rows «1.», «1.1» between the
  parts of a table that opens an annex are annex text (evidence `table_row`); negatives: «2.» after a table in
  ordinary text or in an annex whose first point precedes the table, a point after the last table, and an
  approved text `S` that is a table keep their points.
  Cycle 5 B2: two lists numbering footnotes from «¹» (second marks `<sup>N</sup>` or «¹») keep their own
  footnotes; a footnote whose mark is absent (other `<sup>` number, bare digit) stays unowned.
  Cycle 5 B3: a 590-character Text «V. …» after Section-header sections I–IV opens `S/V` with its points;
  negatives: only I or I–III before it (parametrised), a Roman number inside a sentence.
  Guard: a Text «V. …» ending «;»/«,»/«.» or longer than `ROMAN_TEXT_MAX` stays with the open point.
  Cycle 7 B1: Rules attached as «Приложение № 1 к приказу» keep their annexes «Приложение № N к Правилам …»
  (`A/AN1/AN<n>`, = gold `S/AN<n>` under the ordinal), «№ 2 к приказу» opens `A/AN2`; negatives: act annexes in
  sequence, document annexes «к СП …» opened in the act body, a bare «Приложение № 3».
  Cycle 7 B2: after form fill-in lines «1. ___», «2. ___» the caption, tables, scheme line, stamp and «Приложения:»
  list go to the form (`S/AN1`); negative: a numbered line with text keeps them. `test_m1_04a_batch_tools.py`
  pins `POINT_TAIL` only for a gold fill-in point, `SCHEME_LIST` otherwise.
  Cycle 7 B3: footnotes «*- …», «**- …» under a table printing «*», «**» belong to its owner; negatives: «*» only
  inside «**», mark only on an earlier page. «Подписи членов рабочей комиссии:» after a form's last point -> form
  root; negatives: a terminated sentence about signatures, a long colon line.
  Cycle 7 B4: «От Сторон …» (with or without a dot) stays in the last point, «От Правительства …» still opens the
  block; dotted-gap limit: «5.5» after «5.1» nests in «5.1», «5.4» is a sibling.
  v6.1: inside «УТВЕРЖДЕН … ПОРЯДОК» a form «к приказу» does not nest «Приложение № 1 к Порядку …» (`S/AN1`);
  markdown emphasis («*…*» body line, «**Примечание**» footnote) is no asterisk mark.
  Cycle 6 B1: «5.3» after «5.1» and an unnumbered block is a sibling under «5.» (flat at an annex root without
  «5.»); negatives: «5.1.1» in «5.1», unbroken «5.1, 5.2, 5.3».
  Cycle 6 B2: a footnote goes to the last mark before it, not to a point continued on the next page with the
  same mark; a mark only on an earlier page keeps that point; one mark twice on the page -> common owner.
  Cycle 6 B3: «Подписи и реквизиты Сторон», «От Правительства …», signer and initials after an agreement's last
  point -> `S`, the act's signer -> `A`; negatives: terminated «Председатель …»/«От …»/«Подписи …» sentences.
  Cycle 6 B4: table-annex rubrics «I.» are not roman sections (long Text «III. …» after the last table, «II. …»
  between tables: no section, no `roman_sequence`); «V. …» after an unterminated paragraph opens nothing.
  Cycle 4 B1: leading-zero markers («01.», «02)», «001.») are list lines; «Состав работ: 01. …» lists under
  tables stay in «РАЗДЕЛ 1.», «10.» after «09.» continues the list, «10.» after other text stays a point;
  restarted «1.» after a table/heading takes the level of «N.»; negatives: no break, «1)» and «3.1.» after a table,
  «1.» after «1.».
  Cycle 4 B2: a right-aligned line between two tables follows the unit (not a signature; one before text still is);
  a footer file code («….doc», «….DOCX») goes to the scope root and opens no continuation, other footer text unchanged.

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
  Impossible table grids (batch-5 span-past-rows and overlap shapes) degrade one
  table with null columns and kept cell text; a resolved table has no `grid` key.
  Rotation retry: an accepted cw90 page and 13 mutations (bbox/text/category/labels, selection,
  sideways or earlier-accepted attempts, sizes, unknown/third turns); `test_ocr_runtime.py` keeps
  the flag off by default and refuses non-boolean values.
- `docs/assets/check_ocr_lab_rotation.py <lab-root>` checks the external client's
  rotation retry on real PIL images: coordinate mapping for both turns, the
  upright-text rule, first accepted turn, retained attempts and the two-turn bound.
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
