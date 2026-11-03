# Documentation instructions

- Owner acceptance on 3 November 2026 closes the page-orientation task recorded in
  `milestones/m1/04a/M1_04A_OCR_PAGE_ORIENTATION_2026-11-03.md`; retain its documented
  transcription limits and failed first control as evidence.

- `assets/ocr_lab_page_orientation.patch` applies after the page-recovery patch;
  it adds RapidOrientation 0.0.11 (packaged PaddleClas ONNX model, Apache-2.0)
  to the dots client image without upgrading its Transformers or recognizer.
  Rebuild `dotsmocr`; the recovery config enables `page_orientation`.
  Apply turns only at minimum crop confidence >=0.85: the first full control
  exposed a false 180 on a sparse upright page (score 0.267). Retain that failed
  check; the later confidence-gated check is separate.
  `assets/check_ocr_lab_page_orientation.py` checks four-way mapping and actual
  preprocessing/source-image preservation without GPU inference. The module
  handles whole-page quarter turns, not mixed-direction text or table semantics.

- Post-M1-04A OCR refill repair is recorded in
  `milestones/m1/04a/M1_04A_OCR_REFILL_FIXES_2026-11-03.md`. The external
  `assets/ocr_lab_page_recovery.patch` applies after the existing loop/rotation/
  Picture patches; verify its before/after hashes, never overwrite lab results.
  `assets/m1_04_ocr_recovery_config.example.json` selects four workers and the
  opt-in streaming loop recovery. The patch also reduces dots.mocr's vLLM GPU
  reservation from 0.65 to 0.55: a reproduced page-19 timeout with four workers
  coincided with Windows GPU shared-memory spill. Successful primary sampling stays greedy
  (`temperature=0`, `seed=1`, 24000 tokens). Page failures retain partial native
  responses and allow later pages to finish, while the run remains failed.
  `summarize_m1_04a_ocr.py --ocr-root` matches the runner's `-OcrRoot`;
  `--table-stats` also lists upright loop-retry pages. Keep completed OCR,
  preservation/replay, table accuracy and legal qualification separate.
  The runner now defaults to `data/m1/ocr.recovery.local.json` (copy the recovery
  example); the old rotation-only config remains historical evidence. Keep four
  clients with the reduced KV cache; do not assume the old 16-client throughput
  result qualifies this resource profile.

- Section 5 of `milestones/m1/M1_NPA_REQUISITES_2026-11-03.md` records the later
  PDF transport fix: Connection: close alone reproduces partial-body timeout
  even in curl; pool/4 uses a PDF-only Python keep-alive handler. Main-loader
  acquisition/repeat succeeds without curl or monkeypatch; frozen M0 stays intact.
  Earlier curl workarounds and timeout reports remain historical evidence.

- Owner decision on 3 November 2026 supersedes the mandatory OCR requisites-comparison
  plan: date/full number/type/issuer come from the official card, with card/PDF/OCR
  linkage retained. `plans/2026-11-03-official-card-requisites.md` implements the
  publication.pravo PDF route. `milestones/m1/M1_NPA_REQUISITES_2026-11-03.md`
  separates the preceding diagnostic counts from the later card-policy result.
  Do not treat 147 unsupported OCR types or 7 OCR disagreements as manual requisites
  tasks when bound cards already contain the fields. Missing/corrupt source
  evidence and temporal/structural/legal review remain independent concerns.
  Completed replay: 229/229 card records, 229 exact tree/content replays and unchanged
  repeats, 159 removed OCR identity blockers, 2064 unchanged source files, 1306 tests,
  Ruff and M0 78/78. This is bounded publication-PDF behavior, not bank-wide
  metadata coverage, new OCR qualification, network transport repair or legal admission.

- `milestones/m1/M1_NPA_REQUISITES_2026-11-03.md` records the separate post-M1-04A
  empty-title fix: opt-in pool/3 accepts empty/null/absent names with all other
  card guards retained. Exact raw bytes stay archived; frozen M0 is unchanged.
  Real No.1165-r repeats new/unchanged only with a disclosed one-run curl transport
  injection after native Python PDF timeouts. Keep that limit separate from
  metadata correctness and from future OCR/requisites/manual-review measurements.
  Its subsequent offline diagnostic binds1606unchanged inputs for229scan-pool
  documents: all have cards/four fields;17empty titles. Existing OCR profile:
  75four-field matches,7unresolved postanovlenie cases,147other-type coverage gaps.
  These are research sidecars, not new compiler statuses or actual human workload.
  Keep the next extraction work and all-source/manual-load acceptance open.

- M1-04A is closed by owner acceptance on2November2026; the current record is
  `milestones/m1/04a/M1_04A_CLOSURE_2026-11-02.md`. Acceptance covers250corrected
  official-tree acts each>99% and the final frozen ten each100%. No further scan
  batch is required for that task. Earlier frozen reports retain their historical
  open/failed status; never edit them to imply a passed independent PDF protocol.
  Family/OCR-format qualification under M1 G13, PDF/identity/admission guards and
  the separate requisites/empty-title loader task remain outside this closure.

- `milestones/m1/04a/M1_04A_FINAL_TEN_CHECK_2026-11-02.md` records the first
  frozen control run at466c043:10/10strictly above99%, all715/715, every file100%.
  No production/source/gold edits or retuning; full key coverage, zero exclusions/
  alternatives and10stored-score replays. Four literal path labels in one
  unnumbered annex differ only as AN vs AN1 under the pre-existing equivalence;
  printed source caption confirms no own number. Do not call this byte equality
  of all owner strings or a new OCR/AST/legal-admission qualification. The ten
  documents are now exposed; old preparation status remains historical.

- `milestones/m1/04a/M1_04A_FINAL_TEN_PREPARATION_2026-11-02.md` records10new
  official-tree control documents reserved at466c043, not a passed check.9type/
  issuer groups,490source nodes,715/715regions controlled, no exclusions or
  alternatives. All screened codes/rare groups were already acquired; one extra
  Government resolution uses the declared fallback. One Duma source lacking
  unit types was replaced before any candidate run. Production/projector8 are
  unchanged; no owner parser, scoring, OCR or manual annotation was run.

- `milestones/m1/04a/M1_04A_REMAINING_SETS_FIXES_2026-11-02.md` records the
  subsequent development correction:250/250strictly above99%, minimum99.16%,
  total38675/38746. Source projection8 preserves printed code parts, typed
  subparagraphs, compound indices and own-caption annex numbers. New source-only
  review covers209regions in6files plus2single-region decisions; one annex-parent
  decision is propagated to82source-node addresses. Prior set1 review is reused.
  Original sources, projection6/7 controls and failed results stay sealed. Scored
  keys/extractions and142exclusions are unchanged;6stale alternatives resolved,
  no new alternatives. Parser gain is1198regions on the200new acts when compared
  on identical corrected controls; separate source correction gain7620.
  All5sets are exposed development, no fresh scan qualification or M1-04A closure.

- `milestones/m1/04a/M1_04A_REMAINING_FOUR_SETS_2026-11-02.md` records the
  first frozen check of sets2–5 on343c94e: strict above99 counts43/50,41/50,
  47/50,46/50 (177/200). All200first results remain unchanged; no tuning or
  control edits followed exposure. Strict19329/28181 and no_section27564/28181
  differ greatly because three code parts absent from source trees add ancestor
  segments in parser paths; other differences remain. Do not silently drop
  sections or call23strict failures23confirmed parser defects. Source coverage
  retains130exclusions and21alternative regions. All five sets are now exposed;
  preparation-time reserved statuses are historical. M1-04A stays open.

- `milestones/m1/04a/M1_04A_SET01_FIXES_2026-11-02.md` records corrected
  exposed set1:50/50above99%,46perfect,10528/10565strict, minimum99.27%.
  Source projection7 corrects first-act wrappers and printed dotted sections;
  a source-only independent13-region annotation replaces missing unit typing
  for one RP. The original9749/10565 and all projection6 files remain sealed;
  12exclusions and zero alternatives are unchanged. On corrected controls the
  old parser scores10437/10565; parser changes add91correct regions. Do not
  attribute the entire gain to parser rules or call this fresh scan qualification.

- `milestones/m1/04a/M1_04A_FIVE_SETS_SET01_CHECK_2026-11-02.md` records the
  first frozen check of set1 only:38/50above99%,35perfect,9749/10565 (92.28%),
  identical strict/no_section scores;12projected regions unscored. Six President
  orders score0 solely because projection6 treats their current-act wrapper
  `вложение/Распоряжение` as attached S, while the parser uses A; all remaining
  tails match in those six. Preserve raw scores/controls and source-review proof;
  this is a projection defect, not total structure loss. Address/other acts retain
  additional differences. No tuning/rescoring occurred. Set1 is exposed; sets2–5
  remain unused. Do not read the acquisition report's reserved status as current
  exposure status for set1; the new experiment records that transition separately.

- `milestones/m1/04a/M1_04A_FIVE_OFFICIAL_TREE_SETS_2026-11-02.md` records
  five prepared reserves of50new IPS documents,250total,14act/issuer groups
  (11source types). All250same-edition HTML/tree pairs and existing projection6
  controls are sealed; parser/OCR were not executed. Each set has11–12groups;
  source Protocol/Addresses/Constitution/Fundamentals are included where available,
  without normative-status or admission claims for all types.8tree failures
  refilled7slots, preserving all planned groups.38746/38888projected regions
  have automatic controls; retain142exclusions and21alternative-owner regions.
  The five sets are for successive checks; do not consume every reserve in a
  single correction run or call preparation a passed structure check.

- `milestones/m1/04a/M1_04A_OFFICIAL_TREES_FIXES_2026-11-02.md` is the latest
  clean-text development result: all50 above99%,49perfect,3551/3552 (99.97%),
  minimum146/147 (99.32%). Preserve the first3437/3552 report and controls.
  The three failed amendments shared a quoted-blank/requisite-block cascade;
  they were not fixed by changing OCR or footnote links. Old237 scan metrics/error
  lists are exact; old246 official acts have no new errors and14 additional
  correct regions. Full14-document compiler controls and1166tests pass. These
  exposed50 acts are development evidence; scan-batch24 qualification stays failed.

- `milestones/m1/04a/M1_04A_OFFICIAL_TREES_2026-11-02.md` records the owner's
  automatic-control alternative: 50 previously unconsumed IPS acts, unchanged
  maintained post-П23 code and projection6. Strict/no_section3437/3552 (96.76%),
  47/50 above99%,46perfect; the each-document target fails. Retain the111-region
  quoted-contract mismatch in1288/2023 and four footnote comparisons separately;
  source-tree agreement is not independent adjudication of every difference.
  All projected regions were evaluated, with no alternative owners. This uses
  clean text/artificial pages; scan batch24 remains failed and M1-04A open.

- `milestones/m1/04a/M1_04A_BATCH24_CHECK_2026-11-01.md` is the latest check:
  strict1/5 (Government1/3, sanitary amending acts0/2). All443unit properties
  match, but16content-owner failures and24heterogeneous continuation differences
  remain. Do not equate unit matches or OCR accounting with correct content/table
  placement. Retain the original controls and explicit continuation-adjacency
  convention gap; no after-run retuning/rescoring or qualification claim.

- Batch24 source stage has completed94pages of local OCR and actual independent
  image review:986regions/443units, three sealed fresh-context jobs and matching
  saved replay/runtime evidence. The candidate is still unchanged from its
  pre-OCR freeze. Source coverage is not the structural verdict; retain all failures.

- Batch24 execution follows `plans/2026-11-01-batch24-structure-check.md`:
  freeze before OCR, independent source/image annotation before evaluation,
  all five inputs retained, no parser tuning or sample replacement during check.
  Report the two sanitary documents specifically as amending acts.

- `milestones/m1/04a/M1_04A_BATCH24_DOWNLOADS_2026-11-01.md` records five newly
  acquired originals/94pages at the download stage. The two sanitary acts are
  amendments; later source review and evaluation are separate evidence.

- `milestones/m1/04a/M1_04A_TASK3_FIXES_2026-11-01.md` is the current short result:
  four exposed scans pass all source controls under the explicit warning policy;
  the full ten-document baseline and all237 old metrics/error lists are retained.
  Keep the initial fail0/4 report as history. These tuned scans are development
  evidence; M1-04A still needs fresh two-act-per-family qualification.

- `assets/check_m1_04a_source_controls.py` accepts source numbering warnings
  only with explicit `allow_source_warnings=True` (owner decision 01.11.2026).
  Exact source coverage, unit kinds/numbers/parents/order and continuations still
  apply. Repeated units need independent occurrence/start evidence and matching
  warning coverage; ambiguous non-marker owners after multiple starts need
  `owner_unit_start_key`. Do not infer the occurrence from the latest position
  or the candidate output. Warning acceptance never changes frozen controls.

- `milestones/m1/04a/M1_04A_BASELINE_FIXES_2026-11-01.md` is the later result:
  all seven full-baseline table-owner differences, four continuation misses and
  nine annex-number omissions are fixed against unchanged controls. Eight
  document trees pass the full controls; No.2/No.16 still have identity refusals
  and the reserved Task3 qualification remains pending. Preserve the preceding
  audit as its genuine failed baseline; proposed owner agreement is not admission.

- The full M1-04A baseline source/image audit is now recorded in
  `milestones/m1/04a/M1_04A_BASELINE_STRUCTURE_AUDIT_2026-11-01.md`: 103 images
  actually viewed, 1139 regions and 457 independent source units. This supersedes
  the earlier partial-review coverage limit, not its retained failures. Full
  source coverage is not acceptance: 7 table-owner differences without an
  enclosing section, 4 missed continuations, 9 annex-number omissions and two
  identity refusals remain. No reserved body was opened or parser rule changed.

- M1-04A closure checks on 01.11.2026 are recorded in
  `milestones/m1/04a/M1_04A_CLOSURE_CHECKS_2026-11-01.md`. The independent
  `assets/validate_ocr_structure.py` does not call the parser and requires full
  source controls plus frozen file/split bindings. Its authored tests are not
  Task 3 qualification. Actual compiler replay passes preservation on 12/205;
  baseline literal comparison is 97 canonical passes, 14 unresolved, one
  unscored Picture, with 20/20 numbering sequences. The 111 matching proposed
  owners cannot replace canonical acceptance or full 103-page structural review.

- M1-04A closure resumes under `plans/2026-10-31-m1-04a-closure.md`. Its baseline
  preflight verifies source/control text anchors, not semantic parent correctness.
  Never report 112 matching text hashes as 112 passed structural relations, or
  treat the retained legacy prefix scanner as independent exhaustive gold.

- Owner decision, 31.10.2026: requisites discussion/expansion and the empty-title
  loader fix are deferred to `plans/2026-10-31-npa-requisites-task.md`, Trello
  `https://trello.com/c/UdIdY6We`, after M1-04A. Record the loader defect; do not
  implement it while completing M1-04A. The identity-presentation decision stays
  open. This split does not waive source provenance or structural qualification.

- Requisites metadata research, 31.10.2026:
  `milestones/m1/04a/M1_04A_REQUISITES_METADATA_2026-10-31.md` distinguishes absent
  cards, empty titles, optional fields and adapter rejection. The 2369-row cache
  is already filtered (195 separate rejects), not a portal-wide completeness
  sample. Archived cards and old IPS/actual pilot snapshots likewise cannot
  establish an overall missing-card rate. No identity behavior was changed.

- Compiler connection, 31.10.2026: maintain post-П23 rules in
  `src/legal_rag/corpus/ocr_owner_structure.py` and its private `_ocr_owner/`
  package; the experimental
  `assets/ocr_logical_structure.py` and frozen prototypes remain historical.
  `assets/export_owner_maps.py` / the first-pass `current` route now use the
  actual compiler adapter `ocr_owner_ast.build_owner_tree`, exporting only
  parsed bindings; unresolved identity cannot count as parsed ownership.
  `assets/check_m1_04a_owner_integration.py` checks known development scans only,
  preserving outputs in new directories. It compares owner proposals separately
  from canonical nodes. Never present this replay as Task 3 or a П24 freeze.
  New first-pass freezes must explicitly pin `--prototype LABEL=PATH` to the
  maintained module (or an approved frozen copy); the runner's historical
  no-argument prototype default still names the retained experiment.
  Connection report: `milestones/m1/04a/M1_04A_COMPILER_INTEGRATION_2026-10-31.md`.
- Owner-parser organization, 31.10.2026: `run_m1_04a_first_pass.tracked()`
  recursively hashes corpus Python files so nested rule modules remain in every
  new first-pass freeze. A dev-regression `prototype_sha256` identifies only its
  entry file; it is not a complete rule freeze. Keep a full code-hash manifest
  with parity evidence. Historical prototype/freeze outputs stay unchanged.
  Report: `milestones/m1/04a/M1_04A_OWNER_ORGANIZATION_2026-10-31.md`.

- `research/ZAKON_LEGAL_AI_TAKEAWAYS_2026-10-23.md` retains the Zakon.ru
  article takeaways and two primary texts read on 22 October 2026. Keep verified
  facts, project implications and proposed tests separate; the note grants no
  corpus admission, implemented capability or milestone-scope change.

- **M1-04A naming (owner decision 27.10.2026; the owner was confused by versions, pools, cycles, corpora and
  batches whose numbers differed by one). Follow it in every new report, plan and message:**
  - one number: **step N** (old «цикл N») freezes **prototype П<N>**, which is checked on **scan batch N**. The next
    step after П11 is step 12 -> П12 -> batch 12. Never number a prototype differently from its step.
  - old names stay where they are (old reports, `experiments/<date>-prototype-v<k>-freeze/`, `VERSION =
    "ocr-logical-structure/<k>-experiment"`, `cycle` in file names): П8 = v7, П9 = v8, П10 = v9, П11 = v10 (frozen
    27.10 in `20261027-prototype-v10-freeze/`). Earlier versions (`code-final`, v1-v6.1) have no П-name. When you name
    a frozen copy or data folder, give both (`П11 (v10)`). Owner decision 27.10.2026: folders, file names and the
    code's `VERSION` label are **not** renamed — the old->new table is enough; do not propose renaming again.
- `milestones/m1/04a/M1_04A_POOL_BATCH_11_2026-10-27.md`: scan batch 11, the check of П11 (v10; П10 = v9 equal in total,
  differences only in rp-2417): 1532/1998; quote the without-rp-2417 figure (1521/1829) and the per-type table
  (resolutions 464/465). rp-2417-2015 is a convention question: a whole Programme with its own «ОДОБРЕНА» mark quoted in
  an amendment is `S2` in the Codex gold (§6.1 own-mark rule) but quoted text of point «2.» for the prototype (as the
  pp-728 annotator did). prikaz-fns-93-2015 (858 regions) annotated in 2 page-range parts; ukaz-1615-2011 refilled
  (ZIP instead of PDF). `POOL_STATUS` has batch-11. Codex jobs: `.superpowers/sdd/2026-10-27-m1-04a-pool-batch-11/`.
  Owner decision 27.10.2026 (convention v2 §6.1): a whole document with its own approval mark quoted in an amendment is
  quoted text of the introducing amendment point; the own-mark rule does not apply to quotations. Counter 2 of 3.
  `assets/derive_m1_04a_gold_quoted.py` derives write-once `agent-<slug>.gold-quoted.txt` (+ receipt; map
  `agent-<slug>.quoted-map.json` pinned to the frozen gold collapses a quoted document's root `S2…` into its introducing
  point `S/2`; acts without a map copied). Rescore `20261027-batch-11-rescore-quoted`: П11 1690/1998, rp-2417 169/169
  (П10 77). The dev regression must score batch 11 on `gold-quoted`, never the raw frozen gold.
- Step 12 A (owner 27.10.2026: «84,6% слишком низкий показатель»): dev regression covers 122 documents (+ `BATCH_11` on
  `gold-quoted`). Baseline of frozen П11 (v10) `20261027-dev-regression-122-v10`: 23232/23693, batch 11 1690 (= the
  rescore), the 111 earlier rows equal `…-dev-regression-v10`. Step-12 rules gate with `--baseline` it and
  `--frozen-families` (no names: all but «приказы»); JSON v1/v2 `s12-*` runs must equal `v10-results.json` per act.
- Step 12 B1-B4 (report `milestones/m1/04a/M1_04A_CYCLE12_2026-10-27.md`, prototype not frozen, `VERSION` unchanged):
  B1 a page header/footer never carries a marker (`PAGE_BAND_EVIDENCE`; in 122 documents only FNS-93 typist marks
  «1. Коприво ИНМ / Прип-ГВ108-0» ever did, all wrong) and `JOB_CODE` makes a header/footer ending in a job code
  («Прил-ГВ198-3», «Прим. 18198-7» after a slash; without a slash a hyphen and 3+ digits) a page mark; B2 a bare
  «Приложение № N» (or one naming the act) before «УТВЕРЖДЕН …» heads every approved document, not only the first;
  B3 `APPROVED_DOCUMENT`: a «№» caption with a lowercase document referent that names its approving act («…,
  утвержденному приказом …») gets the 600-character limit in any OCR category (the name `APPROVED_BY` was already
  taken: run `…-step12-b3` used the old pattern by accident, `…-b3-r2` has equal errors); B4 `SIGNER` takes «Высшее
  должностное лицо …»/«Должностное лицо …». Final `…-step12-b4`: 23542/23693, batch 11 1992/1998, orders 7758 -> 8068
  of 8188, `cross_scope_v2` 94 -> 26, no drops, other families byte-equal, JSON v1/v2 unchanged.
- Step 12 freeze: П12 = v11 `ocr-logical-structure/11-experiment` (sha256 4824bde3…, LF, blob 3c9ad46f) in
  `data/m1/m1-04a/experiments/20261027-prototype-v11-freeze/` (`code-v11.sha256` also pins
  `derive_m1_04a_gold_quoted.py`); regression `20261027-dev-regression-v11` 23542/23693 with the family gate (errors
  equal to `…-step12-b4`); JSON v1/v2 `v11-results.json` equal to `v10` per act. Measured on scan batch 12.
- `milestones/m1/04a/M1_04A_POOL_BATCH_12_2026-10-27.md`: scan batch 12, the check of П12 (v11; П11 = v10 identical region
  by region, step-12 rules never fired): 1738/1782 (97.5%), orders 1313/1354. Evaluator gap (no owner decision yet):
  `single_annex_documents`/`number_single_annex` work on raw paths before ordinal renaming, so `A/AN2/AN` (the only
  annex of a document printed as an act annex) never equals gold `S2/AN1` (minekonomicheskogo-136, 12 regions,
  counted as `cross_scope_v2`; 1750/1782 with it). «6.Сообщение» (no space after the number, fz-435 2 regions).
  Owner decisions 27.10.2026: «6.Сообщение» is a variant of the known class «OCR distorted the marker», so batch 12 has no
  new class — counter 3 of 3 (batches 10-12); the evaluator fix is accepted (convention v2 §5): opt-in
  `evaluate(..., ordinal_single_annex=True)` / `--ordinal-single-annex` re-applies `single_annex_documents` to the
  ordinally renamed gold (`ordinal_single_annex_documents`) and numbers both paths after `rename_head`; the eval result
  records `attached_ordinal.single_annex_documents`, and consumers read heads through `result_heads(result)` (a 3-tuple
  then). `run_m1_04a_first_pass.py` freezes/runs with it by default for batches after batch-12
  (`default_ordinal_single_annex`; summary/freeze key `ordinal_single_annex_equivalence`); the dev regression defaults it
  on (`--no-ordinal-single-annex`; 122 documents unchanged, `…-dev-regression-122-v11-ordinal-single`). Rework rescore
  `20261027-batch-12-rescore-ordinal-single`: 1750/1782, minekonomicheskogo-136 243/243, `cross_scope_v2` 0. prikaz-fsb-641-2020 (625 regions) annotated in 2 page-range parts. `POOL_STATUS` has batch-12.
  Profile `batch-12` (`BATCH12_QUOTAS`: orders 5, resolutions 3, law, decree, government order 1 each; prior 01-11).
  Codex jobs: `.superpowers/sdd/2026-10-27-m1-04a-pool-batch-12/`.
- Step 13 A (owner 27.10.2026: batch 12 into the stand, orders on the FSB regulation): dev regression covers 133
  documents (+ `BATCH_12` on the frozen `.gold.txt`; prikaz-fsb-641 is the stitched file). Baseline of frozen П12 (v11)
  `20261027-dev-regression-133-v11`: 25292/25475, batch 12 1750 (= the rework rescore), `cross_scope_v2` 26; the 122
  earlier rows and errors equal `…-dev-regression-122-v11-ordinal-single`. Step-13 rules gate with `--baseline` it and
  `--frozen-families`; JSON v1/v2 runs must equal `v11-results.json` per act.
- Step 13 B1-B3 (report `milestones/m1/04a/M1_04A_CYCLE13_2026-10-27.md`, prototype not frozen, `VERSION` unchanged):
  B1 `SUBHEADING_STYLED_MAX` (1000): in a corroborated scope (two header-category subheading runs) a body-text
  subheading may be longer than `SUBHEADING_MAX` (`subheading_candidate(p, long=True)`); B2 `labelled_first_items`
  (`LABELLED_FIRST`, evidence `labelled_first`): «<one or two words>: 1. …» right before «2. …» (or «1)»/«2)») takes
  marker 1; `article_notes` still opens an article's notes on such «Примечания: 1. …» (attempt `s13-b2` cost KoAP 5
  on JSON v1); B3 `SIGNATURE_CAPTION`/`signature_caption`: «(подпись)», «(наименование должности», «(инициалы …»,
  «М.П.» open the requisite block after the last marker unless quoted, and `SIGNER` takes «(Генеральный) Директор»
  (attempt `…-step13-b3` also took «(фамилия, имя …)» and quoted lines: JSON v2 two resolutions -1/-3). Final
  `…-step13-b3-r2`: 25330/25475, batch 12 1779/1782, FSB-641 625/625, orders 9430/9542, no drops; the family gate
  reports pp-262-2017 100 -> 101 (B2 gain, owner decision pending); JSON `s13-b3-r2` equal to v11 per act.
- Step 13 freeze (owner 27.10.2026: the pp-262 gain is accepted): П13 = v12 `ocr-logical-structure/12-experiment`
  (sha256 c3789931…, LF) in `data/m1/m1-04a/experiments/20261027-prototype-v12-freeze/`; regression
  `20261027-dev-regression-v12` 25330/25475 (errors equal to `…-step13-b3-r2`; the family gate's only change is the
  accepted pp-262-2017, so its exit 1 is expected); JSON v1/v2 `v12-results.json` equal to v11 per act. Measured on
  scan batch 13.
- `milestones/m1/04a/M1_04A_POOL_BATCH_13_2026-10-27.md`: scan batch 13, the check of П13 (v12; П12 = v11 2413):
  2424/2430 (99.75%), strict 2423, `cross_scope_v2` 0 for both; orders 1546/1549 (fsvng-63 regulation 613/615, B1 fixed
  all 12 П12 subheadings), resolutions 500/503: pp-1006 «Приложение: 1. Поэтажный план …» at the end of a form (gold
  `S2`, root of the form) becomes item `S2/IX/1` under B2 where П12 left `S2/IX` (no_section −1 against П12). Other
  errors: signer titles «Директор … – главнокомандующий …» and «Врио Министра» (signature block), a paragraph after
  subpoint 3.2 (classifier leaves it unclassified: gold `S` vs predicted `A/AN`), strict-only profstandard field
  caption. No new class (owner 27.10.2026: counter 4, batches 10-13): first batch meeting all three section-7
  conditions. Owner 27.10.2026: ministry orders and government resolutions are ready by §7 with frozen П13 (v12,
  c3789931…) as their candidate; rule B2 stays as is (pp-1006 keeps its 3 errors). Laws, government orders and
  decrees keep the v8 (П9) candidate. §7 readiness is not Task 3/G13: no qualification set exists yet. Rosaviatsiya
  favt-150 refilled by fadm-313 (nested `<table>` on p. 63 rejected by `pdf_extraction._Table`).
- `milestones/m1/04a/M1_04A_POOL_BATCH_14_2026-10-28.md`: scan batch 14 (profile `batch-14`: SanPiN/SP + 2011-2019 acts without an IPS
  tree), the second check of П13 (v12; П12 = v11 2287): 2289/2293 (99.83%), strict 2289, `cross_scope_v2` 0 for
  both; SanPiN/SP 1235/1237 on the first sight of the kind (SP 2.1.4284-26 755/757: subpoint closed early, closing
  sentence of point 74 left in subpoint 19), orders 614/616 (minobrazovaniya-1412 footer «ФГОС ВО …» given to a
  point; minselskogo-134 20.1 OCR «з)» read «3)» nested under «ж)» as `S/II/30/ж/3` — the batch-7 rule expects
  the digit at the subpoint's own level, so the classifier leaves it unclassified). rp-774-2017 approves changes
  (empty feed title passed the amending filter). No new class (owner 28.10.2026: counter 5, batches 10-14; the nested «з)» -> «3)» is the batch-7 class).
  SanPiN/SP: 1 of 3 batches, not ready by §7.
- `milestones/m1/04a/M1_04A_POOL_BATCH_15_2026-10-28.md`: scan batch 15 (profile `batch-15`, selection attempt 2), the third check of П13
  (v12; П12 = v11 2440): 2442/2513 (97.17%), strict 2441, `cross_scope_v2` 0. SanPiN/SP 1478/1541: job b15-06 gave
  37 source footnotes (+ one continuation) of sanpin-69-2016 and sanpin-61-2015 to the root `S`, while the prototype
  and every earlier gold give a footnote to the point carrying its mark (37/38 match; 8.9 is a footnote
  continuation given to the page's last point). Owner 28.10.2026: a footnote belongs to the point carrying its mark
  (convention v2 §6.1); `assets/derive_m1_04a_gold_footnotes.py` writes `gold-footnotes` copies from per-region
  maps pinned to the frozen gold (from-owner checked); rework rescore 2479/2513 (98.65%), SanPiN 98.3%. sanpin-19-2026: OCR «б)» for «6)» twice nests real subpoints under «5)» (23,
  classifier names only the marker region). pp-737 form rows «3. …»-«5. Итого» and signatures as points (5),
  minenergetiki-728 unnumbered subheadings (3), paragraph after the last subpoint (2, unclassified). New class: none
  by reading, owner to confirm.
- Step 16 A (owner 28.10.2026: known classes keep recurring on frozen П13): dev regression covers 167 documents
  (+ `BATCH_13`, `BATCH_14` on the frozen `.gold.txt` without the refilled favt-150/sanpin-20-2015, `BATCH_15` on
  `gold-footnotes`). Baseline of frozen П13 (v12) `20261028-dev-regression-167-v12` (3655a364…): 32522/32711, batches
  13/14/15 = 2424/2289/2479 (the checks and the batch-15 rework rescore); the 133 earlier rows equal
  `…-dev-regression-v12`. Step-16 rules gate with `--baseline` it and `--frozen-families`; JSON v1/v2 must equal
  `v12-results.json` per act.
- Step 16 C1 (prototype not frozen, `VERSION` unchanged): `Marker.alt` holds the other reading of a one-character
  subpoint marker OCR confuses (`OCR_CONFUSED`: «б)»/«6)», «з)»/«3)», `with_ocr_reading`); `solve_depths` also
  tries it at `OCR_READING_COST` 0.5 (above a tie-break, below any gap or unexplained nesting), and the build keeps
  the chosen reading in `p.marker` with evidence `ocr_marker`. `…-step14-c1` (43c1f93b…): 32551/32711 (+29), no
  document below baseline; error lists changed only by fixes: sanpin-19-2026 662 -> 685/685, fz-119-2016 350 -> 353,
  fz-15-2013 219 -> 221, prikaz-minselskogo-134-2016 392 -> 393; batch 15 2502/2513 (99.56%). The family gate exits
  1 for those fixes (laws, sanitary rules). JSON `s14-c1` equal to v12 per act on both stands.
- Step 16 C2 (B4 `close_subpoints`, convention v2 «абзац после последнего подпункта принадлежит родителю»):
  `subpoint_level` also counts a dotted «7.1.5.» inside the dotted point «7.1.» it extends; only the list of the last
  subpoint closes (the paragraph after «д)» inside «2)» goes to «2)», not to the point); the subpoint's own marked
  paragraph that lost its final «.» closes too when the next sentence is on the same page and has at least
  `OWN_SENTENCE_MIN_WORDS` 8 words («Российской Федерации.» and lists of names stay). Regressions against
  `…-step14-c1`: `…-c2` dotted (9d8901b5…, +2: sanpin-61-2015, sanpin-69-2016), `…-c2b` one level (cc83589f…, +1
  sanpin-20-2026 15.3), `…-c2c` unterminated (23dd0d5d…, +1 sanpin-20-2026 38.16): 32555/32711, no document below;
  batches 14/15 = 2292/2504. `…-c2c-failed-ukaz410` kept: without the marked-paragraph condition ukaz-410-2021 lost 2
  (appointment lines). JSON `s14-c2`: v1 equal to v12 per act, v2 one code +1 (17813 -> 17814), nothing lower.
- Step 16 C3 (`subheading_candidate` / `subheading_stacks`): an OCR heading (Section-header/Title) may end with «:»
  («## Проведение проверки:» over «### Документарная проверка»), and a run of OCR headings also follows a numbered
  point that lost its final «.»; a body-text line there, a section heading or an editorial note before the run keep
  the old reading. `…-step14-c3` (6bd14c7e…): 32558/32711 (+3, prikaz-minenergetiki-728-2015 212/216), nothing
  else changed; JSON `s14-c3` equal to `s14-c2` per act.
- Step 16 C4 (`table_rows`): in a table annex, «N.» rows after the last table part that go on by one from the last
  row cut out between the parts («3.»-«5.» after «2.», a subsidy calculation form) are rows too; the first marker that
  does not go on stops it. `…-step14-c4` (7b615357…): 32563/32711 (+5, pp-737-2019 144/144), nothing else changed;
  batch 15 2512/2513. JSON `s14-c4` equal to `s14-c2` per act.
- Step 16 C5 (`page_mark`): a Page-footer line printed on exactly two pages («ФГОС ВО культурология -05») is a page
  mark of the scope root (convention v2 §2) and opens no continuation; on three or more it is running noise as
  before. `…-step14-c5` (9c99cdc9…): 32567/32711 (+4: prikaz-minobrazovaniya-1412-2015, also pp-1327-2019 +2 and
  prikaz-minobrazovaniya-1126-2017 +1), nothing lower; batches 13/14/15 = 2424/2293/2512. JSON `s14-c5` equal to
  `s14-c2` per act.
- Step 16 freeze (owner 28.10.2026 «Сделай все, не спрашивай у меня»): П16 = v13 `ocr-logical-structure/13-experiment`
  (sha256 b2cee806…, LF) in `data/m1/m1-04a/experiments/20261028-prototype-v13-freeze/` (code hashes add
  `derive_m1_04a_gold_footnotes.py`); regression `20261028-dev-regression-167-v13` 32567/32711 (errors equal to
  `…-step14-c5`); JSON `v13-results.json` on both stands (v1 equal to v12 per act, v2 one code +1). Report
  `milestones/m1/04a/M1_04A_CYCLE14_2026-10-28.md`. Measured on scan batch 16 (SanPiN reported separately).
- `milestones/m1/04a/M1_04A_POOL_BATCH_16_2026-10-28.md`: scan batch 16, the check of П16 (v13; П13 = v12 4736):
  4723/4752 (99.39%), strict 4723, `cross_scope_v2` 0, sample 30/30; SanPiN 3332/3360 (99.17%). П16 fixed nothing
  over П13 and added 13 errors, all from the dotted part of C2: a second paragraph of the last «N.M.K.» point stays
  in it in this gold (two batch-15 regions said the point) — the dotted extension overfitted batch 15. Reading:
  a list of point references «2.1.42 и 2.2.7 в части …» read as points (5, sanpin-30-2020, both prototypes) is a
  new class. Owner questions: that class and the counter; dotted subpoint paragraphs.
- Owner 28.10.2026 «Да, подпункту»: a paragraph after the last dotted subpoint «N.M.K.» belongs to it (convention v2
  §6.1; list rule only for «1)», «а)»). `assets/derive_m1_04a_gold_footnotes.py` takes `--base/--suffix/--map`:
  batch 15 `gold-dotted` = `gold-footnotes` + maps `agent-<slug>.dotted-map.json` (sanpin-61-2015 11.13,
  sanpin-69-2016 11.6). Dev regression = 179 documents (`BATCH_15` on `gold-dotted`, `BATCH_16` on `gold`); frozen
  П16 baseline `20261028-dev-regression-179-v13` (2c24b657…): 37288/37463, batches 14/15/16 = 2293/2510/4723.
- Step 17 A (prototype not frozen, `VERSION` 13 unchanged): `subpoint_level` is back to «1)» / «а)» only (the C2
  dotted reading removed). `…-step15-a` (77f34461…): 37303/37463 (+15: sanpin-30-2020 +11, sanpin-31-2015 +2, sanpin-61/69 +1
  each), nothing below; batch 16 4736 (rework, the check stays 4723). JSON `s15-a` equal to `v13` per act.
- Owner 28.10.2026 «Да, новый вид»: point references read as points are a new class; the section-7 counter restarts
  (0 after batch 16). Step 17 B (`point_references`, before `table_rows`): a `POINT_REFERENCES` line (dotted number
  without its dot, then «,» / «и» and a number, or a lowercase word) whose number does not go on from the last
  marker (`goes_on_from`: child, sibling or parent's sibling) loses its marker (evidence `point_references`).
  First attempt inside `parse_marker` (no sequence check) cost prikaz-minkultury-1321-2016 «12.1 принятие …» one
  region: kept as `…-step15-b-failed-minkultury1321`. `…-step15-b2` (2c7836c3…): 37308/37463 (+5 sanpin-30-2020),
  nothing below; batch 16 4741/4752. JSON `s15-b` equal to `v13` per act.
- Step 17 freeze (owner go-ahead 28.10.2026: 30 SanPiN at once to close the family): П17 = v17
  `ocr-logical-structure/17-experiment` (sha256 78fecc69…, LF; no v14-v16 labels) in
  `data/m1/m1-04a/experiments/20261028-prototype-v17-freeze/`; regression `20261028-dev-regression-179-v17`
  37308/37463 (errors equal to `…-step15-b2`); JSON `v17-results.json` equal to v13 per act. Measured on scan
  batches 17, 18 and 19 (profiles `batch-17..19`: 6 SanPiN of 2011-2019 + 4 of 2020+ each, `long_min` 0).
- Step 20 (after batch 19, owner «Да»): dev regression = 202 documents (`BATCH_17..19` on `gold`); frozen П17
  baseline `20261029-dev-regression-202-v17` (02f34220…): 42506/43583, `cross_scope_v2` 918.
  A (`ANNEX_BEFORE_APPROVAL`, `approval_caption`): «Приложение[ № N] ⏎ Утверждены …» in one region is an approval
  caption. `…-step20-a` (bc1d8c98…): 43382/43583 (sanpin-81-2016 14 -> 890/914, `cross_scope_v2` back to 26), nothing
  else changed. B (safety net, scope loop): the act has a point «Утвердить …», then a requisite line (text only), and
  on a later page — before any point or article — an OCR heading without a marker or with a Roman one: the approved
  document `S` opens there (evidence `approved_without_caption`). With A off it alone gives sanpin-81-2016 888/914.
  First attempt (signature by geometry, any page-first paragraph) broke 9 laws/resolutions: kept as
  `…-step20-b-failed-too-wide`; page-first-only variant `…-step20-b2-page-first`. `…-step20-b`
  (21e6fa86…): equal to A. JSON `s20-a`, `s20-b` equal to v17 per act.
- Step 20 C (`article_notes`, `under_table_ids`): a singular «Примечание:» right under a table is that table's note and
  keeps its owner; the plural «Примечания» after a form's last point still opens the document's notes (cycle 10 B5).
  D (`table_references`): a caption «Таблица N» named by an earlier point («в таблицах 6.1, 6.2») but printed under
  another point belongs, with what follows up to the next marker, to the latest naming point (evidence
  `table_reference`). C alone dropped sanpin-110-2017 by 19 (its notes followed tables wrongly owned by 7.2): kept as
  `…-step20-c-failed-without-d`. `…-step20-cd` (3a980c7d…): 43402/43583 (+20: sanpin-26-2015 +6, sanpin-110-2017
  94/94, sanpin-81-2016 +4, sanpin-91-2014 221/221), nothing below. JSON `s20-cd` equal to v17 per act.
- Step 20 E (`run_m1_04a_first_pass.py`): the check summary lists `alarms` — acts a prototype scores below
  `ALARM_SHARE` 0.9 of their regions — and prints each as `ALARM …`; report every alarm next to the batch total.
- Step 20 freeze: П20 = v20 `ocr-logical-structure/20-experiment` (sha256 626cd8a7…, LF; no v18-v19) in
  `data/m1/m1-04a/experiments/20261029-prototype-v20-freeze/`; regression `20261029-dev-regression-202-v20`
  (8c602f1c…) 43402/43583, errors equal to `…-step20-cd`; JSON `v20-results.json` equal to v17 per act. Measured on
  scan batch 20: profile `batch-20` (one SanPiN of 2020+, pages up to 500) = SanPiN 1.2.3685-21 (469 p.).
- Owner 29.10.2026 «Разделу»: a table with its own heading between points belongs to the section (convention v2
  §6.1). Dev regression = 203 documents (`BATCH_20` on `gold`); frozen П20 baseline `20261029-dev-regression-203-v20`
  (0a94c8aa…): 44453/45354. Step 21 (`table_block_sections`, after `table_references`): after a finished point,
  a block of unmarked table heads (`table_head`) followed by a table goes to the enclosing named unit, with the
  unmarked lines after the table up to the next marker; the next head-and-table block right after a moved table goes
  too. Only with its own heading: an OCR heading line or a Caption that is not «Таблица N…» (`TABLE_NUMBER`); a caption
  «Таблица 2.1. Оптимальные …» alone, a point that names the table (in its text or lines after it) or introduces it
  («ниже», «следующ…», final «:»), and a block rule D moved stay with the point. First attempt (any head) cost
  sanpin-81-2016 55 regions: kept as `…-step21-a-failed-sanpin81`. `…-step21-a` (heading lines only,
  083f5475…) 44718; `…-step21-b` (51a97e59…, title captions too): 44827/45354, batch 20 1425/1771, nothing below. JSON
  `s21` equal to v20 per act. Batch-20 annotators disagree in places (some blocks given to the point, e.g. 306.12).
- Step 21.2 (owner 29.10.2026: «Все документы ниже 99% доводи до 99%», development): A `region_footnote_number` — a
  Footnote region with a plain-digit number («15 СП …», `PLAIN_FOOTNOTE_NUMBER`) is that footnote; a numberless
  Footnote right after a footnote ending «:» / «;» on the same page continues it. B `PAGE_CODE_LINE` «5590030 (1.4)»
  is a page mark (scope root, no break of the open point). C SIGNER takes «Врио», «И.о.». D an int marker may be
  glued to a capitalised word («6.Сообщение»). E JOB_CODE allows a dot before the code («Н.П.Прир-К7552-3»).
  `…-step22-a` (32b138b3…): 44852/45354 (+25), nothing below; pp-931-2022, pp-996-2022, fz-435-2020,
  prikaz-minnauki-511-2019 and sanpin-44-2017 now at 99% or more. JSON `s22` equal to v20 per act.
- Owner 29.10.2026: classify every residual error (prototype vs gold) and fix the prototype's, even one-off, never by
  per-document patches; nothing may get worse. Owner decisions of 28.10 applied to earlier golds by hand-checked
  maps: `GOLD_OVERRIDE` in the regression (prikaz-fns-815-2024 `gold-dotted`, prikaz-mintruda-141-2023
  `gold-footnotes` on its forms copy); rebaseline `…-step22-b-golds` 44871.
- Step 21.3 A-F (`close_subpoints`, `article_notes`, `under_table_ids`, footnote owners): a table caption under a
  subpoint closes nothing; after an unmarked capitalised «;» line (formula legend «К = 10 – …;») the last line closes
  nothing (a lowercase «;» list line still lets the closing sentence close); a «где λ – …» legend after the last list
  item closes like a sentence; a notes heading under a table followed by footnotes is the table's notes; under a
  document notes heading «1)», «2)» stay notes («1.», «2.» stay points, sanpin-31-2015 gold); a footnote with no mark
  found belongs to the document of its page (never ownerless), and one whose mark is only on an earlier page follows
  its page's marked footnotes when they share one owner. First attempt (int notes, any sibling owner) cost
  sanpin-31-2015 10 and sanpin-61-2015 1: kept as `…-step23-a-failed-notes`. `…-step23-a`: 44887/45354 (+16),
  nothing below; JSON `s23a`: v1 equal, v2 two acts +1 (fz 72 -> 73, rp 22 -> 23), nothing lower.
- Step 21.4 A-G: `POINT_REFERENCES` takes ranges («10.10 - 10.17), 11 …»); a run of OCR headings between points of the
  scope root is the root's heading; «Примечание. … настоящий перечень/Правила/Порядок …» outside an article is the
  document's note (`DOCUMENT_NOTE`); SIGNATURE_CAPTION takes «(место для подписи …)», «(фамилия, имя, отчество …
  должностного лица / заполнившего / подписавшего …)» and ««___» ______ 20__ г.»; a dash item after the letter list
  a dash item ending «:» opened goes back to that dash's owner; a quoted article/chapter/section heading whose final
  «»» closes an inner title (no «.;,» after it) keeps the quotation open (`QUOTED_UNIT_HEADING`). `…-step24-a`
  44897, `…-step24-b` 44903/45354, nothing below (pp-1521-2014, prikaz-fsvfn-1310-2025, fz-119-2016 at 100%).
  JSON `s24a`/`s24b`: v1 equal, v2 as s23a plus one act strict 354 -> 355; nothing lower.
- Step 21.5 (after the step 21.5 A attempt — headed tables to the scope root without a unit — cost pp-728-2020 8 and
  sanpin-81-2016 2: reverted, kept as `…-step25-a-failed-root-tables`): B `SERVICE_TAIL` «Лист согласования …» after
  the act's documents goes, with the rest, to the act's requisite tail; C `field_line` «20. Телефон/факс ___ Адрес ___»
  — a sentence after it is the form's, captions «(…)» / «*…» stay with the field; a field caption «(серия, номер …)»
  is never a signature by position and the requisite block opens after it; E `page_mark` also takes Text lines:
  typist marks, time stamps `TIME_STAMP`, a declaration page head near the page top `FORM_PAGE_HEAD` («1680 6016»,
  «ИНН», «КПП», «Стр.»), and footers with «компьют…» or one or two characters; `carry_page_head` moves a page head
  printed before a scope caption on its page into that scope; a short upper-case registration stamp table belongs to
  the scope root. A repeated-table-header rule (D) scattered XML-format tables (fns-93, fns-815, favt-547, mintruda-742,
  rp-2417): dropped, kept as `…-step25-b-failed-headers`. `…-step25-b`: 44935/45354 (+32), `cross_scope_v2` 26 -> 5,
  nothing below; JSON `s25` equal to `s24b` per act.
- Step 21.6 (`table_title`): an unmarked unterminated line right before a «Таблица N» caption heading a table is that
  table's title, so the block has its own heading (sanpin-2-2021 +68 -> 1494/1771). Attempts kept: headed blocks to
  the scope root without a unit and after the point's own table (`…-step26-a-failed-after-table`: fns-93 -389,
  fns-815 -87, Mintrud forms) and the same without the «after a table» part (`…-step26-a-no-effect`). `…-step26-b`:
  45003/45354, nothing below; JSON `s26` equal to `s25` per act.
- Step 21.7 (owner 29.10.2026, second «Разделу»: a headed table a point names belongs to the section too):
  `table_block_sections` no longer keeps named or «ниже» tables with the point (only a point ending «:» keeps its
  table; `INTRODUCES_BELOW` removed). `…-step27-a` 45063 (sanpin-2-2021 +60; the three FGOS lose 3 each on the frozen
  gold). The decision applied by hand-checked `tables-map` → `gold-tables` copies (`GOLD_OVERRIDE`): prikaz-minobrazovaniya
  1126-2017 and 1412-2015 on `gold`, 518-2017 on `gold-quoted` (3 regions each), sanpin-2-2021 91 regions (26 blocks its
  annotators gave to the point; figure caption 310.10 left out). `…-step27-b-golds`: 45154/45354, nothing below,
  sanitary rules 99.0%; JSON `step27-a`: v1 equal, v2 as s24b.
- Step 21.7 B-C (sanpin-2-2021 to 99%): B `TABLE_TITLE_MAX` 300 -> 400 (a 307-character ПДК title before «Таблица
  3.13», 94 regions) and `formula_body` — a point ending in a formula «$$ … загрязнения.} $$» is finished; C
  `table_rubrics` — a short unterminated int-marked line between two table parts, numbered back from the open point
  by 2 or more («2. Учреждения общего образования» under point 87), is a table rubric (`table_row`), not a point.
  `…-step27-c` 45251, `…-step27-d` (54904b9a…) 45274/45354 (99.82%), nothing below; sanpin-2-2021 1765/1771, sanitary
  rules 99.82%; JSON `step27-d`: v1 equal, v2 as s24b.
- Step 21.7 D: the minzdrav-369 «gold question» was a prototype error — its annotator saw on the page images that
  «1.1. Прием …», «2.1. …» sit in the tables' top grid rows (§6: no points). `TABLE_GRID_RUBRIC`: when a table of the
  scope carries a dotted rubric as `<caption>2.2. …`, unterminated dotted lines right above a table are rubrics.
  `…-step27-e` 45284/45354, minzdrav-369 47/47, nothing below; JSON `step27-e` as `step27-d`. Read annotation-notes.md
  before calling a residual error a gold error.
- Step 21.7 E (`gap_sibling` in `table_block_sections`): an unterminated unnumbered heading over a table, when the
  open point is decimal «5.1» and the next marker is «5.3», is the missing sibling «5.2» — the block goes to the
  parent (minekon-37 «Пусковые расходы¹,²», gold `S/AN5|S/AN5/5.2`). `…-step27-f` 45293/45354, minekon-37 286/288,
  nothing below; JSON `step27-f` as `step27-d`. Left there: 10.6, 17.4 — the annotator gave a capitalised paragraph
  after the last list subpoint to that subpoint by meaning (convention: the point); owner question. A «;»-final
  paragraph keeping its subpoint (for 17.4) broke 10.4, 12.6, 13.3 of the same act and sanpin-20-2026 36.9 (gold gives
  those to the point): reverted, kept as `…-step27-g-failed-semicolon`. Owner 29.10.2026 «Пункту»: `closing-map` →
  `gold-closing` (10.6 → S/5, 17.4 → S/8/1); `…-step27-h-golds` 45295/45354, minekon-37 288/288.
- Step 21.7 G (`peer_points`, before `close_subpoints`): «в пунктах 15 и 15.1» in the act makes «15.1» a peer of «15»
  (the minkultury-1321 annotator's §5 `exceptions.json` exception, grounded on that reference); «15.1» and its list
  move up a level. `…-step27-i` (lookahead too strict for «15.1.» in the test) and `…-step27-j` 45298/45354,
  minkultury-1321 458/461, nothing below; JSON `step27-j` as `step27-d`. Its other exception «8.1» has no text
  ground (a meaning exception the convention allows): stays a prototype miss. `…-step27-i-broken-regex`: a run with
  a heredoc backspace in the regex (no effect) — write regexes through a file, never a bash heredoc.
- Step 21.7 H (owner 29.10.2026 «Часть таблицы»): `table_rows` also reads an approved text (`TABLE_DOCUMENT_SCOPE`
  `S\d*`) that opens with a table and has no sections/named units; there a first int/decimal marker after the last
  table that starts no numbering («4.15.», not «1.») is the last row. rp-2728 gold → `rows-map`/`gold-rows` (2.6, 2.7
  → S). First attempt without the no-sections guard cost the Mintrud professional standards (S opens with a table,
  then «I.»): kept as `…-step27-k-failed-mintruda`. `…-step27-k` (2d2c770e…) 45300/45354 (99.88%), nothing below;
  rp-1431 and rp-2728 100%; JSON `step27-k` as `step27-d`. Now every document is at 99% or more.
- Step 21 freeze (owner 29.10.2026 «Да, П21»): the development steps after step 21 are its parts 21.2-21.7 in code,
  tests and notes (folders/commits keep `step22`…`step27`). П21 = v21 `ocr-logical-structure/21-experiment` (sha256
  97246c3e…, LF) in `data/m1/m1-04a/experiments/20261029-prototype-v21-freeze/`; regression
  `20261029-dev-regression-203-v21` 45300/45354 (equal to `…-step27-k`), JSON `v21-results.json` as `step27-k`.
  freeze.json quotes П20 44453 — that was on the golds before the 29.10 decisions. Checked on scan batch 21: profile
  `batch-21` (no SanPiN left; 2 decrees, 2 resolutions, 2 government orders, 4 orders; batch-16 settings; no law: every
  law offered had an IPS tree).
- Step 22 (owner 30.10.2026 «Да, шаг 22»; batch 21 in development, regression = 213 documents, baseline
  `20261030-dev-regression-213-v21` 47021/47188): A `letter_part` — «А. Персональные данные», «Б. …» heading lines
  (`UNIT_RANK` 0, label lowercase «а») are parts of a form only as a run «А.», «Б.» … (`letter_parts`; a lone «А. …»
  is text); B `numbering_gaps` — an approved text with sections is still a table document when the markers between
  its tables skip numbers («I.» then «III.», «1.» then «32.», rp-22-2015); C `FIELD_LINE` takes a trailing date blank
  «"__" ______ 20__ г.»; D `FORM_SIGNER_LINE` «Подпись представителя …» opens the requisite block, `BLANK_LINE` under
  a field or right under a letter part stays there (first under any heading: cost JSON pp-…102369318 one strict region,
  narrowed in `…-step22-e`). `…-step22-e` (a4bcf79a…) 47133/47188 (99.88%), every document at 99% or more, nothing
  below; JSON `step22-e` equal to `v21` per act. rp-1829-2015 318/319 (left: a page footer «250826a2 …» repeating
  the next page's text), rp-22 235/235, pp-648 158/158.
- Step 22 freeze (owner 30.10.2026 «Заморозь»): П22 = v22 `ocr-logical-structure/22-experiment` (sha256 80436fd7…, LF)
  in `data/m1/m1-04a/experiments/20261030-prototype-v22-freeze/`; regression `20261030-dev-regression-213-v22`
  47133/47188 (equal to `…-step22-e`), JSON `v22-results.json` equal to v21 per act. Checked on scan batch 22 (1893/2019,
  report `M1_04A_POOL_BATCH_22_2026-10-30.md`): profile
  `batch-22` (owner 30.10.2026: acts of 2020-2026, types with the most first-check errors of batches 1-21 —
  resolutions 25%, orders 15%, government orders 13% of regions wrong; decrees 0%: 4 + 5 + 3, no decrees or laws);
  `tree_allowed` lets resolutions in with an IPS tree (the first run found all 93 2020+ resolutions with one).
- Step 23 (owner 30.10.2026 «Да, шаг 23»; batch 22 in development, regression = 225 documents, baseline
  `20261030-dev-regression-225-v22` 49026/49207): A `ARTICLE` takes Roman figures («Статья IV» = `ст4`, a treaty
  protocol); B `quoted_markers` skips page marks (a footer «4557147.doc» between «… редакции:» and «"Статья VI»);
  C `form_annex_owner` / `FORM_REFERENT` — «Приложение 1 к акту патрулирования лесов», «Приложение к форме заявления …»
  nest under the attached document's annex just printed when the referent's next word is in its text and the number
  does not go on the document's annexes (unnumbered -> `AN1`); the first attempt (any lowercase referent, any number)
  broke 7 acts with «Приложение 2 к санитарным правилам»: kept as `…-step23-c-failed-too-wide`; D `subheading_stacks`
  skips page marks, `FILL_IN` takes a final «;»/«.»; E `annex_caption` takes a long form caption (`FORM_REFERENT`); F
  `mark_restarts`: «1.» after a fill-in «2. ___;» restarts. `…-step23-g` (c4cb1f3d…) 49150/49207 (99.88%), every
  document at 99% or more, nothing below; JSON `step23-g` equal to v22 per act. rp-1622 71/71, minprirodnykh-955
  196/196, fns-269 506/508 (left: two Text subheadings after a page-foot stamp picture).
- Step 23 freeze (owner 30.10.2026 «Да, П23»): П23 = v23 `ocr-logical-structure/23-experiment` in
  `data/m1/m1-04a/experiments/20261030-prototype-v23-freeze/`; regression `20261030-dev-regression-225-v23`
  49150/49207 (equal to `…-step23-g`), JSON `v23-results.json` equal to v22 per act. Checked on scan batch 23: profile
  `batch-23` (acts of 2020+, first-check error share since batch 16: government orders 16.3%, orders 2.9%,
  resolutions 0.3% -> 5 + 5 + 2).
  Below 99%: minkultury-1321, rp-1431 / rp-2728.
- Step 24 (owner 31.10.2026: improve after П23 to above 99% on scan batch 23): regression = 237 documents
  (+ `BATCH_23` on frozen `gold`), baseline `20261031-dev-regression-237-v23` 51600/51704. A bare decimal «1.1.»
  opens a form position only with its immediately following same-page parenthesised field caption; bare numbers
  over tables must stay unmarked (the broad attempt `…-step24-a` broke seven professional standards). Form sheet-side
  and service-stamp marks bypass cross-page joining and belong to the form root. Whole bold lines give heading
  evidence only for subheadings (`bold=True`, never document opening); tests use the emphasis-stripped view,
  retaining source text. Form completion / reply-address blanks open the requisite tail. `…-step24-c` (76e5b151…)
  51624/51704; batch 23 2474/2497 (99.08%, strict equal),
  cross_scope_v2 0 there; previous 225 error lists exact, other families exact. Official trees 100 + 146 documents
  `step24-c-results.json` equal v23 per act. Owner clarification: EACH batch-23 document must be strictly above 99%.
  Continuation E: short unmarked same-page caption runs between tables are fields; the name/signature suffix before
  a numbered document-receipt position signs the whole form, unless the preceding numbered position explicitly
  names a signature. F: SIGNER takes «Исполняющий обязанности» without «Временно». Final `…-step24-f` (ea7f4d95…)
  51640/51704, batch 23 2490/2497 (99.72%), every act >99% in strict/no_section (MVD 915/921, RP-1301 24/24).
  Previous 225 error lists exact, no drops against step24-c; official trees `step24-f-results.json` equal v23 per act.
  Seven errors remain. VERSION still 23-experiment; frozen П23 untouched, no П24 freeze.
  Report `milestones/m1/04a/M1_04A_STEP24_2026-10-31.md`.
- `assets/survey_ips_tree_coverage.py` (owner request 28.10.2026): sample estimate of which IPS acts have an official
  structure tree. Phases `frame` (every search page per act type of the owner's 32-type list, base c000000000),
  `plan` (strata type × organ × decade, organs read from `adoption`, groups under 200 merged into «прочие»; seeded
  `required_n` = worst-case 95% margin 10 pp with finite-population correction), `screen` (card + document_content,
  resumable, reuses the 25-26.10 corpus screens), `estimate` (Wilson per stratum, type share weighted by exact
  stratum sizes, Agresti-Coull variance). Uses the `acquire_m1_04a_json_corpus` client (1.1 s pause). Output
  `data/m1/m1-04a/experiments/20261028-ips-tree-coverage/`.
  Result (`milestones/m1/04a/M1_04A_IPS_TREE_COVERAGE_2026-10-28.md`): 252,381 acts listed (equals the per-type
  counters), 99 strata, 4190 screened, 9401 requests, 0 errors; 25.9% (24.5-27.3%) with a tree, 2020s 76.3%,
  1990s 6.0%, 2000s 9.1%, 2010s 13.1%. `has_text` (actual edition `hascontent`) equals `nodes > 0` in all 4190:
  IPS gives no text without a tree. Zero trees: Constitutional Court acts, treaties/agreements/conventions, appeals,
  statements, other organs of the 1990s. Measurement of the source only; not a prototype check.
  - owner-facing words: **сканы** / **партия N** (old «пул», «проверочный пул», «стенд пула»), **официальные деревья
    от <дата>** (old «корпус JSON v1/v2», «проекция»: `json-corpus/20261025-v1` = «деревья от 25.10»,
    `…/20261026-v2` = «деревья от 26.10»), **проверка** (old «мера», «первый прогон», «holdout»: one run of a frozen
    prototype on unseen data with gold frozen first — the only progress) and **доработка** (old «разработка»,
    «регрессия», «dev»). Plain words instead of internals: «ничего не сломалось» (no document below the baseline),
    «другие виды актов не затронуты» (family gate), «текст ушёл в чужой документ» (`cross_scope_v2`).
  - the glossary, the old->new table and «где мы сейчас» live in `milestones/m1/04a/M1_04A_MAP_2026-10-25.md`
    (sections 0, 2, 3); update that map after every step and check, in these words.
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
- Profile `batch-14` (owner go-ahead 28.10.2026, after the IPS tree-coverage estimate): batch-13 settings with
  quotas `sanpin_2010s` 2, `sanpin_2020s` 2 (act date before 2020 / from 2020), law 1, decree 1, resolutions 2,
  government order 1, ministry orders 2. `select_m1_04a_pool.py freeze-sanpin --output DIR/selection.json` freezes
  every portal act of the Chief State Sanitary Doctor (`SignatoryAuthorityId` `SANPIN_SIGNATORY`, all pages, item
  count must equal the portal total, other signatories refused) and keeps `sanpin_title` approvals of SanPiN or SP
  (owner 21.10.2026: SP = SanPiN); ГН normatives, amendments and other resolutions are not candidates. The run takes
  `--sanpin-candidates` (all dates; `--from/--to` bound only the day feed) and the IPS tree filter: in seeded order
  each wanted card gets `ips_tree` (IPS search number+date, single exact match, card `actualrdk`,
  `document_content` nodes); reasons `ips_tree_present`, `not_in_ips` (federal acts only: IPS holds them all),
  `ips_identity_ambiguous`, `tree_lookup_error`; ministry orders and SanPiN qualify when IPS lacks them. After the
  quotas fill, `tree_reserve` checks 3 more acts per category (selection must stay identical) and
  `tree_checked` records every answer; a refill of such a selection draws only from checked acts without a tree.
  Acquisition slugs: `sanpin-<resolution number>-<year>`. The portal day feed starts in December 2011 (empty
  days in 2010 and early 2011), so 2010s scans are 2011-2019.
- Profile `batch-15` (owner go-ahead 28.10.2026): batch-14 settings with quotas `sanpin_2010s` 3, `sanpin_2020s`
  3, law 1, decree 1, resolution 1, government order 1, ministry orders 2, prior batches 1-14, and
  `require_title` (owner 28.10.2026: title from IPS). 524 of 617 feed government orders of 2011-2019 have an empty
  `name`, and so does IPS search `name`; the IPS `document_card` often has `description`. `ips_tree` records
  `ips_title` = card `name` or `description`; with the tree filter `tree_reason(row, require_title)` judges an empty
  feed title by `ips_title`: none -> `title_missing`, amending -> `amending_act` (without the tree filter
  `cheap_reason` rejects an empty feed title). The flag is written to the selection and its refills; earlier
  profiles keep their behaviour. `AMENDING_PREFIXES` now also holds «о внесении дополнения» (attempt 1 drew law
  252-FZ «О внесении дополнения …»). The run reuses the frozen batch-14 SanPiN list.

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
  Profile `batch-07`: batch-06 settings, `prior_batches` 01-06 (test pins it and profiles 01-06).
  `run_m1_04a_ocr.ps1 -Slugs` needs a real array: use `powershell -Command "& './docs/assets/run_m1_04a_ocr.ps1'
  -Slugs @('a','b')"`; with `-File`, `a,b` arrives as one string.
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
- `milestones/m1/04a/M1_04A_POOL_BATCH_7_2026-10-24.md`: batch-7 first pass of frozen v5 (+ v4): both 1394/1477, identical
  owners; quote the without-prikaz-90 figure (1154/1175). `cross_scope_v2` 62 (Rules' annexes numbered as order annexes),
  one new class, counter still 0 (owner question). No v3.1/v4/v5 rule fired. Classifier batch-7 rules: act annex with the
  gold annex's number (`raw_predicted`, before ordinal renaming) and OCR letter «з)» as «3)» (`_batch7_cause`); batch 1-6
  class files equal before/after (23; the 2 batch-2 first-pass files already differ at HEAD). `POOL_STATUS` has batch-07.
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
- Cycle 6 B4 (prototype; v4 §4.7 and cycle-5 final-review minors): `roman_sequence()` runs after `table_rows`
  demotion, so demoted rubrics do not count and no row keeps a stale `roman_sequence`; an unmarked «V. …» right
  after an unterminated text paragraph (no table/heading between) continues its sentence and opens nothing; the
  «inside a sentence» test now has that failing case. Regression `…-cycle6-b4` equals `…-cycle6-b3` (13663/13730),
  evidence counts unchanged (`roman_sequence` 1, `table_row` 39), no drops.
- Cycle 6 B5: prototype v5 `ocr-logical-structure/5-experiment` (sha256 6c590866… CRLF working copy, LF a7a8b659…,
  blob 1de3f652) frozen in `data/m1/m1-04a/experiments/20261024-prototype-v5-freeze/`; regression
  `20261024-dev-regression-v5` vs the cycle-6 baseline (v4): 13663/13730 no_section and strict (v4 13598), exit 0;
  rows/errors equal `…-cycle6-b4`. Report `milestones/m1/04a/M1_04A_PROTOTYPE_V5_2026-10-24.md` (development,
  batch 6 included; batch 7 is the measure).
- Cycle 7 A1: dev regression covers 78 documents (+ `BATCH_7` on frozen `20261024-batch-07-gold-freeze`). Baseline
  of frozen v5 `…/20261024-dev-regression-cycle7-baseline/`: 15057/15207 no_section and strict, `cross_scope_v2` 62;
  old 67 13663 with rows/errors equal to `…-v5`; batch 7 1394/1477 (minenergetiki-90 240/302, fsetan-461 173/188).
  Track B gates with `--baseline` it.
- Cycle 7 B1 (prototype, VERSION unchanged until B5): an act annex opened by a reference to the act («Приложение № 1
  к приказу») is an attached document; a later caption with a capitalised document referent («Приложение № N к
  Правилам …») opens `A/AN<k>/AN<n>` (evidence `nested_annex`) until the next act annex or approval caption.
  Regression `…-cycle7-b1`: 15118/15207, minenergetiki-90 240 -> 301, batch 7 1455/1477, `cross_scope_v2` 62 -> 0,
  no drops, no other document's errors changed. Left: 29.16 «Подписи членов рабочей комиссии:» in a form (`S/AN2`).
- Cycle 7 B2 (prototype): a numbered fill-in line of a form (`FILL_IN`: «2. __________», «3) …….») stays a point but
  holds no text: unmarked paragraphs continuing it and the tables/captions after it go to its parent (evidence
  `fill_in_line`), up to the next marker; a numbered line with text is unchanged (only one such case in the 78
  documents). Regression `…-cycle7-b2`: 15129/15207, fsetan-461 173 -> 184 (+9 tail, +2 signature lines), batch 7
  1466/1477, no drops, no other document changed. Classifier label `POINT_TAIL` replaces `SCHEME_LIST` only when the
  predicted point is a gold point whose every region is a fill-in line (`gold_fill_in_points`); batch 1-6 class
  files reproduce (23 equal to HEAD's output); batch-7 class files regenerated in
  `data/m1/m1-04a/experiments/20261024-batch-07-classes-cycle7/` (9 labels changed in each of v5/v4).
- Cycle 7 B3 (prototype): an asterisk footnote («*- …», «** …», `ASTERISK_NOTE`) is owned like a numbered one by the
  latest earlier body region with the same run of asterisks (not inside a longer run), searched only on the
  footnote's page; a form signature heading «Подписи <1-5 lowercase words>:» (`FORM_SIGNATURE_HEADING`) is
  `requisite_like`, so after the last point it opens the requisite block. Regressions `…-cycle7-b3` (footnotes only:
  15136) and `…-cycle7-b3-r2`: 15137/15207, fsetan-461 188/188, minenergetiki-90 302/302, fz-433 +2, rp-1431 +1
  (both old asterisk footnotes), batch 7 1471/1477, no drops.
- Cycle 7 B4 (v5 review minors): `SIGNER` no longer takes «От Сторон…» (both parties, not a signature place) as a
  signature place; the footnote common-owner condition is split over lines; a test pins the dotted-gap limit («5.5»
  after «5.1» stays nested, «5.4» is a sibling). Regression `…-cycle7-b4` equals `…-cycle7-b3-r2` (errors identical,
  15137/15207, batch 7 1471/1477), no drops. Left in batch 7 (6): OCR «з)» as «3)» (2, fz-15), page-footer codes
  (pp-1327 2 «291004 A5.doc» with a space, minobrazovaniya-1126 1), table caption «Таблица» at the root (1126 7.3).
- Cycle 7 B5: prototype v6 `ocr-logical-structure/6-experiment` (sha256 f4deaf54… CRLF working copy, LF b747de3c…,
  blob 3847f9a1) frozen in `data/m1/m1-04a/experiments/20261024-prototype-v6-freeze/`; regression
  `20261024-dev-regression-v6` vs the cycle-7 baseline (v5): 15137/15207 no_section and strict (v5 15057),
  `cross_scope_v2` 0, exit 0; rows/errors equal `…-cycle7-b4`. Report `milestones/m1/04a/M1_04A_PROTOTYPE_V6_2026-10-24.md`
  (development, batch 7 included; batch 8 is the measure).
- Cycle 7 final-review fix: prototype v6.1 `ocr-logical-structure/6.1-experiment` (sha256 e8d2784c… CRLF working
  copy, LF 6d3bd31a…, blob 8dc4f5c5) frozen in `data/m1/m1-04a/experiments/20261024-prototype-v6-1-freeze/`; the v6
  freeze stays as history (never measured on a new batch). An act annex nests later document annexes only when it was
  opened while no approved text was open (inside «УТВЕРЖДЕН … ПОРЯДОК» a form «к приказу» leaves «Приложение № 1 к
  Порядку …» as `S/AN1`); balanced markdown emphasis (`strip_emphasis`) is removed from footnote and body text before
  asterisk-mark matching. The classifier's `FILL_IN` copy must equal the prototype's. `FORM_SIGNATURE_HEADING` also
  accepts «Подписи сторон:» (unchanged). Regression `20261024-dev-regression-v6-1` vs v6: 15137/15207, rows and
  errors identical, exit 0. Batch 8 measures v6.1 (report `M1_04A_PROTOTYPE_V6_2026-10-24.md` §8).
- Cycle 8 C1-C3 (prototype, VERSION unchanged; rules from the JSON corpus dev split, report
  `milestones/m1/04a/M1_04A_CYCLE8_LEVEL_CLOSING_2026-10-25.md`): C1 `CHAPTER`/`SECTION_NAMED`/`PARAGRAPH_SIGN`
  accept a superscript («Глава 24¹» -> `гл24¹`); C2 `editorial_note_owners` gives a consolidated-edition note
  («(Статья в редакции …)», «(Дополнение частью …)», «(Особенности применения пункта …)») to the deepest open unit
  it names (part = «N.» right in an article); C3 `mark_restarts` marks «1)»/«а)» after a capitalised closing
  sentence (previous item ends «.», outside quotes) as `restart`, the solver lets it take the level of the last item,
  `continues_level` treats a lower value as a new list. JSON dev 79.8% -> 89.9% (macro 90.3%, 33 perfect), pool
  15137/15207 with `errors.json` byte-equal to v6.1 after each step; C2 never fires on the pool, C3 fires 37 times
  without changing owners. First C2 attempt `c8-c2` missed «Дополнение» (kept).
- Cycle 8 C4: «2¹.», «3²)», «е¹)» parse as int/paren/letter markers with `Marker.sup` (value = base number,
  label keeps the superscript); the solver accepts gap 0 for an inserted sibling. JSON dev 92.7% (macro 91.8%),
  pool errors equal to v6.1; corpus drops only inside quoted amendments (fz 603161051 -2, 603161055 -1).
- Cycle 8 C5 `quoted_markers(items)`: a multi-paragraph amending quotation opens with a paragraph starting
  with a quote mark (`"`, «, „, “; IPS prints straight quotes) right after one ending «:» and not closing
  itself, and ends at the first paragraph ending with a quote mark; paragraphs after the first lose their
  markers (`quoted` evidence). «…» balance is not used (OCR merges nested closing quotes: attempt 1 dropped
  fz-119/prikaz-135 on the pool, kept as `…cycle8-c8-c5-attempt1-failed`). The next number of the introducing
  list ends a quotation; after a quoted form/table (lost closing quote) the next number of any outer list does
  (r3 without the form gate: fz-603161051 351 -> 156; r2 without any outer guard: two PP drops). r4: JSON dev
  94.3% (macro 94.9%), no corpus or pool drops, pool errors equal to v6.1.
- Cycle 8 C6: `provision_final` ignores trailing consolidated-edition notes («…). (В редакции … № 90-ФЗ)»)
  and `editorial_only` notes are skipped as the previous provision in `close_subpoints` and the C3 closing check.
  JSON dev 94.6%, no drops. Not prototype rules (recorded): IPS leaves forms unstructured (`S2` for the whole
  «ФОРМА паспорта …», 282 regions in pp-102370057: convention question); «Статья 115¹⁻¹» of the Budget Code is
  a measuring-stand artifact (non-digit superscript span flattened to «1151-1», 167 regions).
- Cycle 8 C7: `APPROVAL` also takes uppercase «ОДОБРЕН(А/Ы/О)» (endorsed agreement; title-case «Одобрен Советом
  Федерации» stays a law requisite); an uppercase «ПРИЛОЖЕНИЕ № N к <Документ>» caption may be up to
  `CAPTION_UPPER_MAX` (600) characters. First run `c8-c7` (ОДОБРЕН only) +16, `c8-c7-r2` +34 in rp-102150462;
  JSON dev 94.7% (macro 95.3%), no drops. pp-102370057's form «УТВЕРЖДЕНА … № 272» is nested by IPS in the
  previous Requirements (`S3/AN2`) while the prototype opens `S4`: source nesting, not a prototype rule.
- Cycle 8 C8: `points_are_article_parts` reads the act's own vocabulary (more «пункт N настоящей статьи» than
  «часть N настоящей статьи», e.g. the Budget Code): then a note's «пункт» names the «N.» part and «подпункт»
  its «N)»; `EDITORIAL_NOTE` also takes «(Положения пункта N …)». JSON dev 95.0% (macro 95.3%, 36 perfect).
- Cycle 8 C9 `unbalanced_quotes`: a quotation opens/closes only on a paragraph whose own quote marks do not pair
  (straight quotes by parity, «»/„“ by surplus), so a quoted term at a line end («… "налоговый агент";») keeps
  it open; an opener must not itself end with a closing quote (a page-joined «7) … «Об …».; with a lost nested
  close dropped fz-119 on the pool: attempt `…cycle8-c8-c9-attempt1-failed`). JSON dev 95.1% (macro 95.5%).
- Cycle 8 C10: `ARTICLE` accepts a superscript minus («Статья 115¹⁻¹»). The JSON baseline gained projection 3
  (`m1_04a_json_baseline.py --projection 3`, default): compound superscript spans «1-1» stay superscripts in the
  pseudo text and gold is `ст115^1-1`; projections 1-2 reproduce byte for byte. Frozen
  `20261025-json-baseline-dev-proj3` (freeze 6df9bb99…): v6.1 79.8% / 89.4%, working prototype after C10 96.1% /
  95.6% (36 perfect), no act below v6.1, pool errors equal to v6.1.
- Cycle 8 C11 `editorial_note_unit`: a parenthesised note (≤ 400 chars) citing an act (`NOTE_SOURCE`:
  «Федеральный закон от …», «Постановление Конституционного Суда …») names its unit by the first unit word inside
  («(Приостановлено … действие части 1 …)»); `starts_continuation` no longer joins such a note to the previous
  paragraph across a page. Projection 3: 96.2%, no drops, pool errors equal to v6.1.
- Cycle 8 C12: `editorial_only` covers every `editorial_note_unit` note (a «(Особенности применения …)» between the
  last item and a closing sentence no longer hides the item's dot); named units `code_part` («ЧАСТЬ ВТОРАЯ …»,
  uppercase ordinal word, rank -1, label `разд<N>`) and `subsection` («ПОДРАЗДЕЛ II», rank 0.5, Roman label).
  Projection 3: 96.3%, no drops, pool errors equal to v6.1.
- Owner decisions 25.10.2026 (convention v2 §6.1, no pool re-annotation): numbered sections/positions of forms and
  agreements are points of that document; the abzac after the last list item belongs to the parent (B4); separators
  mark their document's page; a document with its own approval caption is attached separately. JSON baseline
  projection 4 (default) applies them: unstructured IPS forms/agreements not scored, parent|item alternative after
  a final list item (not after an item ending «:»). Frozen `20261025-json-baseline-dev-proj4` (6c8a36a3…, 21908
  regions): v6.1 81.3% / 91.6%, v7 98.0% / 97.7% (54/69 perfect). My first «58 of 61» for IPS stretching was wrong
  (it counted amending-quotation content); the real split is 4 inside / 3 parent.
- Cycle 8 freeze: prototype v7 `ocr-logical-structure/7-experiment` (sha256 7935988e…, LF working copy = LF form,
  blob eaaadbcd) in `data/m1/m1-04a/experiments/20261025-prototype-v7-freeze/`; regression `20261025-dev-regression-v7`
  15137/15207, errors equal to v6.1. Development result; the measure is the JSON holdout (31 acts) and pool batch 8.
- First measure of v7 (report `milestones/m1/04a/M1_04A_JSON_HOLDOUT_V7_2026-10-25.md`): JSON holdout, projection 4,
  gold frozen before the run (`20261025-json-holdout-proj4/freeze.json` 42f82227…, `run-receipt.json` written first),
  one run each: v7 94.5% regions / 94.2% per document (21/31 perfect), v6.1 84.8% / 91.3% (18/31). One act below
  v6.1: fz-602263702 383 -> 280 (C5 guard closed a quoted article at its own «6)» after the introducing «5)»).
  New classes: KoAP article notes «Примечание.», quoted new articles; IPS calls «1.» inside a concept section a
  «раздел» (convention question). The holdout is now development. `m1_04a_json_baseline.py --split holdout`.
- `milestones/m1/04a/M1_04A_POOL_BATCH_8_2026-10-25.md`: batch-8 first pass of frozen v7 (+ v6.1): both 1365/1710,
  identical owners; quote the without-494/553 figure (910/932) and the FAS gold question (forms without own caption split
  into separate documents -> 132 ordinal-shift errors). Only C3 fired (5, no owner change). `cross_scope_v2` 320, no new
  class: the owner (25.10.2026) ruled the approval sheet after the last annex a form of the signature-block class, so the
  no-new-class counter is 1 of 3. Selection profile `batch-08` (= batch-07, prior 01-07);
  `POOL_STATUS` has batch-08 (development). Codex jobs and logs: `.superpowers/sdd/2026-10-25-m1-04a-pool-batch-8/`.
  Owner decision 25.10.2026 (convention v2 §6.1): a form without its own caption or approval mark inside an annex is
  part of that annex. `assets/derive_m1_04a_gold_forms.py` derives write-once `agent-<slug>.gold-forms.txt` (+ receipt;
  roots renamed by a hand-written `agent-<slug>.forms-map.json` pinned to the frozen gold, others copied). Development
  rescore `20261025-batch-08-rescore-forms`: v7 = v6.1 1495/1710 (87.4%), FAS 225/234, `cross_scope_v2` 188; the 79.8%
  ledger entry is unchanged.
- Cycle 9 A1 (plan `plans/2026-10-25-m1-04a-cycle-9.md`): dev regression covers 89 documents (+ `BATCH_8` scored on
  `agent-<slug>.gold-forms.txt`, never the raw frozen gold, which under-counts FAS by 130 regions).
- Cycle 9 A2: `m1_04a_json_baseline.py project --split all` projects the 100 acts (dev then holdout, `split_slugs`)
  as one development stand; `freeze.json` records `split_part: all`. Never rewrite the frozen `…-dev-proj4` /
  `…-holdout-proj4` directories.
- Cycle 9 B0 (owner decision 26.10.2026, convention v2 §6.1): projection 5 (now the default) makes a bare numbered
  «1.» (sub)section without the word «Раздел»/«Подраздел» a point (`S/I/1`, not `S/I/разд1`); in the corpus it only
  hits the concept act rp-1000000000602087490. Codes' «Подраздел 1» stay `разд<N>`.
- Cycle 9 B1 (prototype, report `milestones/m1/04a/M1_04A_CYCLE9_2026-10-26.md`): `annex_caption` gives a numbered
  («№ N») caption naming a capitalised document (`DOCUMENT_REFERENT`) the long limit `CAPTION_UPPER_MAX` (600) in
  any case, not only «ПРИЛОЖЕНИЕ». Regression `20261026-dev-regression-cycle9-b1-r2`: 16790/16917, only
  prikaz-fsetan-494 360 -> 518, `cross_scope_v2` 188 -> 7; JSON proj5 unchanged (37212). Track B baseline stays
  `…-dev-regression-89-v7` for no-drop gating; compare a new rule with the previous step's run too.
- Cycle 9 B2: JSON projection 6 (default) makes IPS note attachments («Примечания», «примечание N») transparent,
  so their paragraphs are the article's (they were `…/AN<k>`); gold changes only in KoAP (145 rows) and one ukaz (4).
  Prototype `article_notes`: «Примечание. …»/«Примечания:» opens a note block owned by the article when the unit
  under the article is a part («ч…») or nothing; «N.» notes and editorial notes stay in it; any other marker ends it.
  A note under a point «5)» (an amending law quoting a new article) keeps its owner — attempt 1 without that guard
  dropped fz-603158321 87 -> 48 (`…-cycle9-b2`, kept). Final `…-cycle9-b2-r2`: pool unchanged, JSON KoAP 9516 -> 9745.
- Cycle 9 B3 (`quoted_markers`): a number continuing the quotation's own list («6)» after a quoted «5)») never
  ends the quotation, even when it also continues the introducing list. `…-cycle9-b3`: pool unchanged; JSON
  fz-602263702 280 -> 487/487, fz-603153558 23 -> 25; pp-1000000000102370341 67 -> 46 is an IPS tree error, not a
  drop: IPS files the quoted Rules' points «7.»-«16.» (quotation opened at «"УТВЕРЖДЕНЫ», closed only after «16. …".»)
  as points of the amendment list. Treat that act's 21 regions as known gold errors.
- Cycle 9 B4 (`quoted_markers`, `close_subpoints`, `marker_number`): inside an open amending quotation a heading
  («Статья 11.», «Статья 25¹⁷.») is quoted text; only the act's own next article/chapter («Статья 2» after
  «Статья 1») ends the quotation (also with a lost closing quote). A quoted heading does not close a subpoint.
  Article marker values are strings: compare numbers through `marker_number` (ASCII digits only; «5¹».isdigit() is
  True). `…-cycle9-b4`: pool unchanged; JSON +130 (fz-603471775 48 -> 98/98, fz-603123263 85 -> 129, fz-603161051
  496 -> 527, fz-603471778 -> 106/106), no drops.
- Cycle 9 freeze (owner 26.10.2026: projection 6 confirmed, pp-1000000000102370341 a known IPS gold error):
  prototype v8 `ocr-logical-structure/8-experiment` (sha256 0de5daa5…, LF, blob 7fd671c0) in
  `data/m1/m1-04a/experiments/20261026-prototype-v8-freeze/`; regression `20261026-dev-regression-v8` 16790/16917
  (errors equal to `…-cycle9-b4`), JSON proj6 `v8` 98.5%, 79/100. Development result; the measure is pool batch 9.
- `milestones/m1/04a/M1_04A_POOL_BATCH_9_2026-10-26.md`: batch-9 first pass of frozen v8 (+ v7): both 2140/2324 (92.1%),
  identical owners; cycle-9 rules never fired on scans. Quote the without-FNS-815@ figure (1737/1772). `cross_scope_v2`
  35 (FNS «Приложение № N к форме налоговой декларации», lowercase referent, read as order annexes; owner 26.10.2026:
  a variant of the batch-7 class, not a new class, recorded in protocol §6). New class: a
  professional standard's table of contents («3.1. … ……» with dot leaders) read as points (6) -> counter 0 of 3.
  The strict classifier marks section-only differences «Не классифицировано»; count no_section errors with the
  evaluator (`equivalent(..., "no_section", single, heads)`). Profile `batch-09` (= batch-08, prior 01-08);
  `POOL_STATUS` has batch-09 (development). Codex jobs: `.superpowers/sdd/2026-10-26-m1-04a-pool-batch-9/`.
  Docker Desktop must be started outside the command sandbox (`Start-Process` inside it silently does nothing).
- `milestones/m1/04a/M1_04A_FAMILY_READINESS_2026-10-26.md` (owner request 26.10.2026): §7 per family over batches 7-9
  from the recorded first passes (each batch's own frozen version), not a new measure. Laws, government orders and
  decrees meet the thresholds, resolutions are borderline; always quote the sample caveats (3 decrees, 6 orders/
  resolutions, Wilson bounds, regions of one document are dependent) and that the Task 3 reserve holds only
  resolutions and sanitary rules. Cycle 10 (`plans/2026-10-26-m1-04a-cycle-10.md`) works on ministry orders only and
  gates every rule on byte-equal errors of all other families. Owner decision 26.10.2026 (protocol §9, variant A):
  laws and government orders are ready by §7 with frozen v8 as their candidate; decrees and resolutions wait for a
  targeted family measure on frozen v8; ministry orders continue in cycle 10. §7 readiness is not Task 3/G13.
- Cycle 10 A1: dev regression covers 100 documents (+ `BATCH_9` on frozen `20261026-batch-09-gold-freeze`, `.gold.txt`).
- Cycle 10 A2: `run_m1_04a_dev_regression.py --baseline S --frozen-families [FAMILY ...]` (no names = all but
  «приказы», `FROZEN_FAMILIES_DEFAULT`) fails when a document of a frozen family changes its error list against
  `S`'s sibling `errors.json` — also when it improved (`frozen_family_changes`). Cycle-10 rules must pass it.
- Cycle 10 B1 (prototype; report `milestones/m1/04a/M1_04A_CYCLE10_2026-10-26.md`): `PRINT_MARK` («Компьютер /Н.Н./
  При-К7552-3», «21.08.2024 15:44 kompburo /Н.И./П-К7552») in a page header/footer is a page mark; a page mark never
  opens the requisite block; a page header/footer opens it only by text (`requisite_like`), not by position; an OCR
  `Caption` is never a signature by position (landscape-page «Таблица 4.4» sat at the right edge). Attempt 1
  (`…-cycle10-b1`: no position signature for any header/footer) dropped pp-1455 (footer code «5807597 (1.3)» lost its
  root owner; caught by the family gate); r2 left captions opening the block (+8). Final `…-cycle10-b1-r3`: FNS 403 ->
  462, favt-547 168 -> 178, minobrazovaniya-1126 +1, other families unchanged, JSON unchanged.
- Cycle 10 B2: `LOWERCASE_DOCUMENT_REFERENT` — with an act annex open, «Приложение № N к форме налоговой декларации»
  (a lowercase document noun, not the act: `annex_to_act` decides first) nests as `A/AN<k>/AN<n>` like the
  capitalised `DOCUMENT_REFERENT`. Same step, B1 addendum: a text caption (`FIGURE_CAPTION`, «Таблица 4.23» in OCR
  Text) is no position signature either. Runs `…-cycle10-b2` (referent only: FNS 478, `cross_scope_v2` 35 -> 19),
  `…-b2-r2` (caption edit did not apply), `…-b2-r3`: FNS 504/552, pool 19042/19241, other families unchanged.
- Cycle 10 B3 `mark_row_cells` (in `load_regions`, `Region.row_cell`): a body region sharing its printed row (vertical
  overlap ≥ half the lower height) with a table or a text over `ROW_LEFT_TEXT_MIN` (40) characters on either side is a
  row cell, never a position signature (professional-standard card fields «Код», «А/01.4», «Код оригинала»);
  headers/footers are never cells. Attempt 1 (`…-cycle10-b3`, left neighbours only, footers included) cost FNS 5 page
  marks and missed «Код оригинала» under its table. Final `…-b3-r2`: 687н 250 -> 269, 141н 247 -> 263, favt-547 179.
- Cycle 10 B4 `toc_line` (`TOC_LEADER`, evidence `toc_line`): a body paragraph ending in a dot leader (≥ 5 dots or
  «……», maybe a page number) with at least three letters before it is a table-of-contents line: no marker, owner the
  scope root (stack emptied after `article_notes`); a fill-in line «2. ……» has no letters and stays `FILL_IN`.
  `…-cycle10-b4`: 687н 269 -> 275/277 (strict 15 -> 272), nothing else changed.
- Cycle 10 B5 (`article_notes`, `NOTES_HEADING`): outside an article a standalone heading «Примечания»/«Примечание:»
  after the last point opens the notes of the scope root (evidence `notes_heading`) up to the next marker; a note
  sentence «Примечание. Текст …» keeps its owner (pp-1521 15.8 stays wrong on purpose: the family gate).
  `…-cycle10-b5`: fsetan-494 518 -> 536/544, nothing else changed.
- Cycle 10 freeze: prototype v9 `ocr-logical-structure/9-experiment` (sha256 38c57541…, LF) in
  `data/m1/m1-04a/experiments/20261026-prototype-v9-freeze/`; regression `20261026-dev-regression-v9` 19102/19241 with
  the family gate (no changes; errors equal to `…-cycle10-b5`), JSON proj6 `v9` equal to v8. v8 stays the candidate
  for laws and government orders; v9 is measured on the next pool batch.
- Owner request 26.10.2026: two data paths again. Pool profile `batch-10` (`BATCH10_QUOTAS`: law 1, decrees 2,
  resolutions 2, government order 1, ministry orders 5; prior 01-09) measures v9 on orders and adds decrees and
  resolutions to the targeted family measure of v8. `acquire_m1_04a_json_corpus.py --profile v2` (`PROFILES`): 150 new
  IPS acts (decrees 45, resolutions 45, laws 25, government orders 15, codes 8, FKZ/pre-1993/Duma-SF 4 each), seed
  20261026, v1 acts excluded (`excluded_nds`); `--profile v1` (default) reproduces the v1 order. IPS holds no ministry
  orders, so the JSON path cannot measure that family.
- `milestones/m1/04a/M1_04A_JSON_CORPUS_V2_2026-10-26.md`: JSON corpus v2 (146 acts, no Duma/SF acts with structure) and
  the one-time holdout measure of frozen v9 and v8 (identical, 99.45%): decrees 14/14 perfect, resolutions 97.5%. Clean
  text, not OCR: quote it as extra evidence beside the pool, never as §7 on its own. `m1_04a_json_baseline.py --corpus`
  selects the corpus (`freeze.json` records `corpus` when it is not v1).
- `milestones/m1/04a/M1_04A_POOL_BATCH_10_2026-10-26.md`: batch-10 first pass of frozen v9 (+ v8): 1378/2454; always quote
  the without-pp-728 figure (1125/1138) and the per-family table. pp-728-2020 (1316 regions) was annotated in 3 page-range
  parts (`experiments/20261026-batch-10-annotation-input/pp-728-2020-chunks/`, `gold/pp-728-2020/chunks/`, stitched
  unchanged); its errors are amending quotations inside the attached «Изменения» (subpoint closed early; a quoted
  «Приложение № 7 к Правилам» opening an annex: 477 transfers). prikaz-minkultury-2782 refilled after an OCR timeout
  (`failures/`, `selection-refill-01.json`, `index-superseded-11-acts.json`). `POOL_STATUS` has batch-10. Codex jobs:
  `.superpowers/sdd/2026-10-26-m1-04a-pool-batch-10/`.
  Owner decisions 26.10.2026 (protocol §9): decrees ready by §7 (candidate v8), batch 10 has no new class (counter 1 of 3),
  resolutions not ready; cycle 11 starts with pp-728 (amending quotations in the attached «Изменения»).
- Cycle 11 A: dev regression covers 111 documents (+ `BATCH_10` without the refilled minkultury-2782). Baselines of
  frozen v9: pool `20261027-dev-regression-111-v9` (a0a3b28e…, 20480/21695, `cross_scope_v2` 503 = pp-728 477 + orders
  26; the 100 earlier rows equal `…-dev-regression-v9`); JSON v1 `20261026-json-all-proj6/v9-results.json`, JSON v2
  `20261027-json-v2-all-proj6/v9-results.json` (146 acts, `--corpus …/20261026-v2 --split all`; its holdout rows equal
  the measure). Cycle-11 rules gate with `--frozen-families законы кодексы распоряжения приказы указы "санитарные правила"`
  (resolutions may change, never below the baseline) and no corpus document below its baseline.
- Cycle 11 B1 (`quoted_markers`, `IN_QUOTATION_EVIDENCE`): every unmarked paragraph inside an amending quotation (also its
  closing one, «… суда.";») gets evidence `in_quotation`, and `close_subpoints` skips it like `quoted` (straight quotes
  are invisible to `quote_balance`). `…-cycle11-b1` is a no-op run (the edit had not applied, code = v9); final
  `…-cycle11-b1-r2`: pp-728 253 -> 726/1316, JSON v1 +49, v2 +10, no drops, family gate clean.
- Cycle 11 B2 (scope loop `quote_open`, evidence `quoted_caption`): the scope loop tracks an open amending quotation
  (opener after «…:», closer «…";»); an annex caption inside it whose referent is not the act («ПРИЛОЖЕНИЕ № 7 к
  Правилам …», no quote mark of its own) is quoted text and opens nothing; the act's own annex still opens. Quoted
  paragraphs never open the requisite block or become a signature by position («(форма)» at the right), but a
  closing rule «____» still opens the block by text (attempt `…-cycle11-b2` dropped 4 JSON acts whose quotation never
  closed). Final `…-cycle11-b2-r2`: pp-728 -> 1064/1316, `cross_scope_v2` 477 -> 0, JSON v1 37811, v2 51973, no drops.
- Cycle 11 B3-B4: an opener «"б) …;» seeds the quotation's own list with its marker (`inner`), so «в)» does not end it
  (cycle 9 B3 knew only later quoted lines); `article_notes` ignores a «Примечания:» that is quoted text. Attempt
  `…-cycle11-b3` dropped JSON v2 pp-602033590 34 -> 13: its first quotation ends with a quoted title («…"Развитие
  образования".») and was taken as self-closing (C9), and the newly stripped quoted «4.» re-nested the real points.
  `self_closing`: with straight quotes only an even count closes an opener; «…» keep the C9 rule. Final
  `…-cycle11-b3-r2`: pp-728 1315/1316, JSON v1 37814 (fz-603161051 560/560), v2 52017 (pp-602033590 57/57,
  pp-605786844 104/104), no drops, family gate clean.
- Cycle 11 freeze: prototype v10 `ocr-logical-structure/10-experiment` (sha256 4c20134c…, LF) in
  `data/m1/m1-04a/experiments/20261027-prototype-v10-freeze/`; regression `20261027-dev-regression-v10` 21542/21695 with the
  family gate (errors equal to `…-cycle11-b3-r2`); JSON v1 and v2 `v10` equal to the last cycle step. Not measured yet.
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
  rotation retry; `assets/run_m1_04a_ocr.ps1` then defaulted `-OcrConfig` to
  `data/m1/ocr.rotation-retry.local.json` (superseded by the 3 November recovery
  profile) and records the selected config (with sha256) in the
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
- Owner decision 01.11.2026 excludes OCR requisites from M1-04A/Task 3 acceptance.
  `plans/2026-11-01-m1-04a-task3.md` supersedes earlier identity-based readiness
  refusals. Preserve historical results, source/permission/split integrity and
  downstream legal admission. `check_m1_04a_source_controls.validate_controls`
  requires full independent structural acceptance, not confirmed requisites.
- `milestones/m1/04a/M1_04A_TASK3_2026-11-01.md` records the frozen four-act
  attempt at `20261101-task3-01/`. OCR/replay completed for all120pages; source
  annotation precedes candidate evaluation. Keep its status explicit and retain
  the failed cases, initial freezes and absence of legal admission.
  The completed first run is fail0/4 (both rows0/2); full source preservation
  and reproducibility pass but do not waive wrong owners/section hierarchy.
  SP has both genuine source ambiguity and independent large hierarchy errors;
  its supplemental known-region diagnostic is explicitly not qualification.
- The Task 3 report's discrepancy addendum replays the same 237 scans at
  51640/51704 (all individual no_section scores >99%) with identical error lists.
  Old post-П23 and current code assign identical owners on the four Task 3 OCRs.
  Do not compare complete-document pass counts directly with region accuracy:
  old noise exclusions yield 100%,100%,99.04%,7.49% on those inputs. An in-memory
  Arabic 1 -> Roman I heading experiment isolates the SP scope cascade; it is not
  a source correction or qualification. Evidence: 20261101-task3-discrepancy-01/.
- Owner 01.11.2026 requests short, plain result summaries; retain large machine
  evidence locally. `plans/2026-11-01-task3-fixes.md` tracks shared corrections;
  the four previously reserved scans are development inputs for these fixes.
