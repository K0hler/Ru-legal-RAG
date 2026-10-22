# Local data instructions

- Since 21.10.2026 all new M1-04A work lives under `m1/m1-04a/`:
  `documents/{development,reserved,pool/<batch>}/<slug>/` hold hash-verified
  copies of originals (`document.pdf` + `source.json`) built by
  `docs/assets/build_m1_04a_catalog.py`; `ocr/<slug>/<run>/`, `gold/<slug>/` and
  `experiments/<YYYYMMDD>-<name>/` hold derived outputs, one new folder per run.
  Never open `reserved/` bodies before Task 3. Earlier M1-04A material was not
  moved (pinned paths); `m1/m1-04a/LEGACY.md` maps it.

- Check-pool batch 1 (21.10.2026): originals in `m1/m1-04a/documents/pool/batch-01/`
  (slug = `<type>-<number>-<year>`, ministry orders `prikaz-<ministry>-<n>-<year>`;
  `selection.json` frozen before PDFs, superseded `attempt-01` kept), OCR in
  `ocr/<slug>/run-01/`, agent gold `gold/<slug>/agent-<slug>.gold.txt` frozen by
  `experiments/20261021-batch-01-gold-freeze/freeze.json` before any parser run.
  First pass: `experiments/20261021-batch-01-first-pass/` (`freeze.json` written
  before `run`, all regions scored); `-first-pass-conv-v1/` rescores the same
  saved outputs under annotation convention v1 (Picture not scored) with split
  error classes. Annotator input `-annotation-input/` carried stage-2 `P`/`join`
  (continuation not blind); future inputs come from
  `docs/assets/build_m1_04a_annotation_input.py` (v1). `attempt-02-superseded-receipts/`
  keeps acquisition receipts frozen by a broad `ValueError` catch; superseded,
  not used. `pool/batch-01/status.json` records measured -> development;
  indexes stay write-once. IPS gives its single edition `rdk = 0`, so
  `official_binding` refuses those bundles; only pp-884 would import a tree.

- Check-pool batch 2: `m1/m1-04a/documents/pool/batch-02/selection.json` (frozen, quotas code 1→0 / federal_law 3→4 recorded as `quota_change`); its `--min-days 120`, exact command, feed-cache hash and the meaning of `attempt-01-partial-unfilled.json` are in the write-once sidecar `selection-provenance.json`.

- Check-pool batch 2 first pass: `m1/m1-04a/experiments/20261022-batch-02-first-pass/`
  (`freeze.json` schema /3 with v1 and `code-final` prototype hashes, written
  before `run`; outputs `prototype-v1/`, `prototype-code-final/`, `current/`;
  `error-classes-{v1,code-final}.json`, `sample-30.json` with ukaz-919 personal
  names that must not be copied into docs). Gold frozen in
  `20261022-batch-02-gold-freeze/`. `pool/batch-02/status.json` records
  measured -> development.
- Convention v2 (22.10.2026): `gold/<slug>/agent-<slug>.gold-v2.txt` is derived
  write-once from the frozen v1 gold by `docs/assets/derive_m1_04a_gold_v2.py`
  with the hand-written annex map `agent-<slug>.v2-map.json` (pinned to the v1
  gold hash) and receipt `.gold-v2.sha256`; only batch 2 has them (pp-931 and
  favt changed, batch 1 would not change). `experiments/20261022-batch-02-rescore-v2/`
  rescores the saved first-pass outputs against it (no system re-run); development only.

- Prototype regressions: `m1/m1-04a/experiments/20261021-dev-regression-<tag>/`
  (baseline, a2, a3 to a3-r4, a4, a4-r2, v1; `summary.json` + `errors.json`, one
  new folder per run; failed attempts a3 and a3-r3 are kept). The `-v1` run is the
  last on the frozen prototype. `20261021-prototype-v1-freeze/` holds the
  prototype copy, `code-v1.sha256` and `freeze.json`; write-once. `code-final`
  (sha256 a7b81b59...) stays for comparison.

- `m1/experiments/m1-04a-20261017-logical-v1/` retains the logical-paragraph
  experiment: copied extractions, hand-made owner gold with freeze hashes written
  before each evaluated run, all code snapshots, attempt/holdout/final runs and
  current/Dedoc owner exports. `comparisons-04` keeps the adapter namespace bug;
  `eval-05/summary.json` is the corrected result. Empty `runs/attempt-01/02`
  are crash leftovers (deletion is not permitted), not results.

- `m1/experiments/m1-04a-20261017-two-pdf-v1/` retains two additional official
  PDFs, permissions, metadata and new/unchanged acquisition on frozen f98b637.
  All 26 pages have fresh dots.mocr, exact saved replay and two identical actual
  compiler builds. Keep the pre-output selected image controls and No.416's
  false approval/cascaded unresolved tail; no document-specific fixes were made.
  Separate 782 preservation checks from 47/50 selected semantic checks and
  direct Dedoc/Docling API probes. No.416 was previously known on the native
  route; original four reserved bodies and legal admission remain separate.

- `m1/experiments/m1-04a-20261017-scope-v1/` retains the complete 12-document
  development scope inventory before reusable boundary changes. Keep reason
  counts distinct from reviewed severity, cascaded blocks from root causes and
  physical-heading candidates from confirmed semantic boundaries. Native inputs,
  prior failures, reserved bodies and closed gold remain unchanged.
  `reviewed/` and `compiler-reviewed/` are the final version-7 direct/permission-
  checked replays. Keep `after-*`, the first compiler harness date failure and
  interrupted pre-review official replay as superseded attempts. Typed-reference
  conflicts exposed by the final rule must remain visible, not treated as repaired
  by their previous numeric-only match or a smaller unresolved counter.

- `m1/experiments/m1-04a-20261017-footnotes-v1/` retains the initial footnote
  heuristic; `footnotes-v2/` retains the reviewed, narrower Text rule and actual
  Dedoc replay. Keep the joined logical sidecars, source hashes, raw native
  files, code snapshots and before/after owner checks. A corrected continuation
  owner is a bounded development fix, not general footnote/annex qualification.

- `m1/experiments/m1-04a-20261017-json-v1/` freezes the unchanged native JSON
  and source-bound table topology for all 12 development PDFs/205 pages.
  Keep Dedoc/Docling raw and prefix-only attempts, code/runtime freezes and
  source/output maps. Sidecar retention is distinct from engine output fidelity;
  no production parser or legal/G13 acceptance is changed by these diagnostics.

- M1-04A `development-ocr/` retains new complete SP3678 (79-page) and
  Resolution1156 (23-page) dots.mocr evidence. `shared-verified-v5/` binds the
  actual `ocr-layout-structure/5` code and three full compiler cohorts: baseline
  103 pages plus these 102 pages, two identical outputs and unchanged replay.
  Preserve earlier shared-v1/v2/v3/v4/v5 attempts separately. Both new acts and
  the baseline still have unresolved structure; four reserved acts are not
  qualified or consumed for rule design. None of these artifacts admits an edition.

- `m1/experiments/m1-04a-20261017-v1/` retains the 103-page legacy baseline,
  isolated Dedoc trials and six additional official acquisitions (222 pages by
  source metadata). Split hash `272ad4033e1b3d8178c3ddc43a62fc380da63b13e3160f6a6df25ab2cb6fda46`
  predates PDF bodies: SP3678/Resolution1156 are development; SanPiN3590,
  SP3648 and Resolutions2314/564 are reserved. Keep the recorded development
  search exposure, original metadata/receipts, exact permission hashes and
  `new`/`unchanged` evidence. Acquisition is not OCR/structure qualification.

- `m1/pilot_runs/m1-04-seal-recovery-20261016-v1/` retains the actual owner
  scope record and source-bound quality policy, the new 10-PDF/103-page run,
  deterministic saved replay, both target-date compile repeats and passing scoped
  qualification. Keep before/before-review client versions. The full run used
  the pre-review immutable streaming/retry snapshot; a later persistence-only
  fix was verified on authored retry errors and final real three-seal/date
  checks in OCR-Lab/results/legal-rag-seal-recovery-final/20261016-v1.
  Owner scope accepts inaccurate round-seal text and excludes only the original
  page-75 table's quality. All pages, errors, attempts and historical failures
  remain stored. This is diagnostic M1-04 acceptance, not legal admission.

- `m1/experiments/m1-04-region-probe-20261016-v1/` retains the owner-approved
  30-request diagnostic on two seals, the original date and page-75 row bands.
  Preserve the pre-inference plan/91-cell controls, post-screen amendments,
  all baseline/analysis versions, outcome-final, scorer selfcheck and manifest.
  `comparison.html` embeds eight inert image/response pairs. Native requests
  are in OCR-Lab/results/legal-rag-region-probe/20261016-v1, with separate
  prompt-stack probes. This changes no production model/config/extraction.
  Loop termination is not correct seal transcription; all 13 conditional signs
  still fail despite recovery of six ordinary minus cells. No gate waiver.

- `m1/pilot_runs/m1-04-20261016-v1/` retains preliminary failed pass-1 and two
  final complete dots.mocr passes on all 10 permitted SanPiN PDFs / 103 pages.
  Preserve native evidence, images, extraction indexes, runtime freeze, model
  hashes and offline/memory observations. `qualification-final/report.json`
  records open acceptance: output drift, 0/13 critical table signs and incomplete
  Picture OCR. No source text was repaired and no legal edition was admitted.
  `human-transcription-review/human-review.json` records the owner's actual
  page-1 confirmation; the old reference remains human_review=false. No duration
  was supplied. The report-only change after this answer is explicitly recorded
  in `final-evidence-summary.json`; the original freeze/report remain immutable.
  Both target-date diagnostic compilations, 19 retained v2 replays and four
  byte-identical v1 manifests are separate from OCR accuracy qualification.

- `m1/pilot_runs/official-source-import-20261016-v3/` is the source-preserving
  M1-03A closure replay on the three retained cohorts (not fresh heldout acts).
  Preserve attempts v1/v2, code/input freezes, both builds and repeat receipts.
  Raw rows/ranges stay unchanged, including source defects in the older cohort.
  Owner acceptance changes the official-JSON contract; it does not turn earlier
  semantic-parser failures into passing qualification or admit legal editions.

- `m1/pilot_runs/official-json-qualification-20261016-v1/` is the distinct
  pre-body selected `/5` cohort after commit `3b2c6c6`: all six acquired with
  correctly attributed diagnostic-selected-cohort/2 wrappers and bundle/v2.
  `official-json-qualification-20261016-validation-v1/parser-transfer-report.json`
  records 2/6 full-control passes (3/6 technical builds), 14 caught mutations and
  105 unchanged input files. Preserve paragraph-unit, titled-part and subsection
  refusals plus the separate quoted-article control-reader failure. No parser or
  verifier tuning/replacements occurred during qualification; this is not G13
  completion or admission. Postrun diagnoses live under
  `m1/reviews/official-json-qualification-20261016/`.

- `m1/pilot_runs/official-normalization-20261016/` retains `/5` development
  probes and immutable full builds. `full-04/results.json` is the final six-act
  control revalidation (6/6, 43 caught mutations); `full-01` holds the two full
  builds/repeat. Preserve failed verifier attempts 02/03 and their explanations.
  `regressions-02` passes seven retained inputs and four byte-identical v1 drafts.
  HTML-only printed contexts and DOM replay of sidecar claims are distinct;
  hidden source ordinals are not independently legally verified. This cohort
  cannot be reused as fresh qualification after tuning.

Scope: local corpora, raw downloads, fixtures, manifests, and generated databases.

- `m1/pilot_runs/official-json-transfer-20261016-v1/` retains a pre-body selected
  six-act cohort for official-structure/4: all acquired with bundle/v2, final G13
  fail 2/6. Use `parser-transfer-report-reviewed.json` plus per-law payload checks;
  preserve original controls/report, three control-reader failures, four parser
  failures and identical repeats/diagnoses. `diagnostic-wrapper-receipt.json`
  corrects adapter attribution without rewriting immutable metadata. Do not reuse
  this failed cohort as new heldout evidence after tuning rules on its bodies.

- `m1/pilot_runs/independent-structure-audit-20261015-v2/` is the final frozen-code
  seven-input replay for official-structure/4: 3906 source nodes plus two derived
  siblings, preserved raw pointers/text/media, ten witnesses and three injected
  faults. V1 is preliminary because code changed during execution; retain its
  attempt-status record and all earlier audit probes. These are development
  controls, not G13 heldout acts, source corrections or legal admission.

- `m1/experiments/official-structure-20261015-v1/` is the owner-authorized local
  follow-up to the sidecar research. `preflight.json` fixes seven permitted inputs
  and 147 protected hashes; retain attempts 01–05 and their adapter snapshots.
  Final attempt 05 preserves all 3,906 source nodes, text/media and explicit
  numbering, but exposes missing quote/form subtrees. Its `index-v2.html` is
  an offline review aid, not human approval; raw HTML is sandboxed for display.
  Never overwrite old attempts, turn heuristic candidate counts into verified
  error counts, or treat the experimental source bundle as production admission.

- `m1/research/parser-search-20261015-v2/` retains the broader parser search,
  pinned external code/frontend snapshots and official structure sidecars for
  seven existing diagnostic inputs. Keep `official-structure-anchor-checks.json`
  separate from `official-fresh-text-checks.json`: valid anchors do not by
  themselves prove an unchanged edition. All seven text responses matched the
  retained raw assets exactly. This is bounded source research, not a compiler
  input-contract update, legal admission or full semantic qualification.

- `data/` content is ignored by default; only this instruction file is tracked.
- Never commit secrets, licensed aggregator exports, private case files, or large generated indexes.
- Treat raw assets as immutable. Store derived artifacts separately and link them by hash and build metadata.
- M1-02's original inventory/review packet under `m1/inputs/m1-02/` remains
  immutable. The owner's explicit consent is a separate record under
  `m1/reviews/m1-02-owner-consent/`, with allowed exact-asset permissions and
  hash-identical archive-local copies for compiler references. The permitted
  59-FZ manifest under `m1/inputs/m1-02-permitted/` supports only the diagnostic
  control target; it does not establish historical or legal admission.
- The owner-facing M1-02 packet under `m1/reviews/m1-02-review-v1/` contains
  separate bounded research acquisitions, raw evidence, readable derived views,
  page images and a blank human response form. Preserve the original inventory,
  owner consent and source pointers. Store returned findings separately; verify
  their packet hash and scope before applying a human decision. Changed evidence
  needs a new packet version. These readable exports are review aids, not compiler
  inputs, approved reconstructed text or qualified production OCR.
- `m1/reviews/m1-02-review-v2/` is the focused standalone successor to v1.
  Its embedded content and one proposed legal classification are hash-bound;
  rendered PDF pages are review aids linked to the unchanged original hashes.
  Preserve v1, its consent and user responses. A v2 reply concerns only its named
  question; never treat it as approval of unrelated missing evidence or the ten
  unfinished editions. Browser QA answers are synthetic and must not be imported.
- The actual v2 human response received on 12.10.2026 is retained separately as
  `human-review.json`, with its hash/scope validation in
  `human-review-verification.json`. Preserve the reviewer's supplied timestamp
  and rationale. It confirms only `59-ks19p-after-80` at both targets;
  `edition_admission` remains false. Keep original inventory/packets immutable
  and distinguish this received decision from synthetic browser QA or a later
  runtime relation import.
- `m1/inputs/m1-02-completion/` retains the 12 October routing result, separate
  official acquisitions, source research, ten exact-asset diagnostic permission
  records and a hash-bound closure matrix. Permissions record continuing owner
  authorization and actual record-creation time; they are not fresh human legal
  admission decisions. Validate all 463 bindings before using the result. Preserve
  earlier inventories, permissions, packets and the rejected/stale M0 candidates.
  Every matrix row still carries explicit edition-admission blockers and its next
  M1 slice; new acquisition does not approve a `LegalEdition`.
  Six exact `corpus-input/1` diagnostic manifests are under `inputs/`; their
  archive-local permission copies match the row records. Four historical research
  candidates are separate and are not silently registered as approved inputs.
- M1-03 diagnostic native drafts, full replay observations and browser QA remain
  under `m1/pilot_runs/m1-03/`. Preserve successive development outputs; compiler
  artifacts are immutable and a changed report needs a fresh output directory.
  The permitted 59-FZ input and original admission blockers remain read-only.
  Native coordinates refer to `/redtext` scalar characters; these local drafts
  are neither legally admitted editions nor historical reconstruction evidence.
- The Housing Code parser controls are retained under
  `m1/experiments/dedoc-housing-code-20261012-v1/` and
  `m1/experiments/parser-alternatives-housing-code-20261012-v1/`. The latter uses
  the same immutable HTML for isolated Docling, Unstructured and DocSlicer runs;
  installed environments are under `m1/tool-environments/`. Preserve raw outputs
  and read `COMPARISON.md` / `comparison.json` before interpreting counts. Generic
  text blocks or heading trees are not legal article/part/item nodes. DocSlicer's
  browser mode omits two CSS-hidden editorial paragraphs; its static control
  keeps the text but collapses this document to one block. New settings/runs need
  separate outputs; this experiment is not production integration or admission.
- The follow-up chain probe is under
  `m1/experiments/parser-pipeline-housing-code-20261013-v1/`. A fresh Unstructured
  pass feeds separately retained HTML/TXT inputs to pinned Dedoc and DocSlicer.
  Plain TXT restores all Housing Code article boundaries in Dedoc. The best
  experimental branch adds 41 canonical article-number dots only where original
  W9 ranges prove superscript semantics; its ledger and paragraph alignment remain
  separate from raw inputs. Its 243 article/number/section-chapter controls pass;
  nested provisions, legal paragraphs, note scope and other documents remain
  unqualified. Attribute this source-specific adapter to the experiment, not to
  native library features, and retain the weaker plain/HTML branches as evidence.
- The direct simplification probe is under
  `m1/experiments/bs4-dedoc-housing-code-20261013-v1/`. BeautifulSoup alone retains
  source paragraph IDs/W9 ranges and produces the same normalized TXT content
  as the previous best chain, excluding whitespace. Pinned Dedoc passes the
  same 243 article/number/section-chapter controls and retains 996 notes;
  Unstructured adds no measured benefit for this exact HTML. Use dotted article
  numbers as strings with explicit article kind and parent scope; retain the
  source-number components/display ledger. Bare strings are not provision IDs.
  This is not production integration, nested-structure qualification or admission.
- The two-document follow-up benchmark is under
  `m1/experiments/parser-benchmark-html-20261013-v1/`. The unchanged normalizer
  and pinned Dedoc run three sequential passes on Decrees 354/491 and repeat
  the Housing Code. Warm normalization-plus-parse times are about 1.40/0.18/1.56
  seconds, excluding process startup and JSON IO. Text/notes survive, but attached
  rules stay raw text under preceding provisions, and superscript point/subpoint
  numbers remain unqualified. Independent prefix controls are not full AST
  accuracy. TXT flattens 354's table and omits embedded formula images; retain
  their source controls. Do not promote the pipeline from article-only scores.
- The parser-independent preparation replay is under
  `m1/experiments/html-preparation-20261014-v1/`. `verification.json` names four
  passing content-addressed outputs; retain earlier failed prototypes separately.
  Original JSON scalar HTML, prepared HTML, source/output opening anchors and
  validated input are separate files. Preserve source status and permission;
  this replay checks text/notes/indices/tables/images/references and determinism,
  not legal hierarchy, date validity, admission or non-pilot G13 transfer.
- `m1/experiments/html-preparation-parsers-housing-code-20261014-v1/` retains a
  fresh raw/prepared HTML pair for Docling 2.138.0 and pinned Dedoc 2.8. Dedoc's
  native article count stays 228/243 while correct numbers improve 189 to 228.
  Docling retains 419 native super-script fragments; an experimental native
  inline-group fold recovers 243/243 article numbers, without legal heading
  classification. Keep raw native outputs distinct from that evaluation export.
  Preservation/number gains do not qualify hierarchy, full nested provisions or
  G13. M1-03A now supplies the shared legal structure engine; its native transfer evidence is separate from these preparer experiments.
- Small redistributable test fixtures may be committed only after their source, license, and expected hash are documented.
- M0-11 questions, labels and evidence remain local. Only a legally approved
  working export may be used for implementation; the closed set is reserved for
  gate evaluation. Keep exact source hashes and spans with every positive label.
- The tracked M0-11 manifest fixes IDs, split membership and local-file hashes.
  Any content change creates a new draft and requires fresh Legal Reviewer
  approval; a hash match alone is not approval.
- Name annexed rules separately from the approving act: use “Rules approved by
  Government Resolution No. 354/491”, never “Rules No. 354/491”. The number
  belongs to the resolution, not to the rules.
- Audit each M0-11 label for one unambiguous question and one matching failure
  mode. Expected values must be user-facing answers or refusals, not evaluator
  instructions; evidence spans must stop at the last provision needed to
  support the answer.
- Keep the expected article, part, clause, subclause, or annex address in the
  hidden label. Do not disclose it in the user-shaped query merely as a lookup
  hint; retain a document identifier only when it is the subject of an
  applicability/date question or is needed to disambiguate the request.


- M1-03A historical law/code replay is `m1/pilot_runs/m1-03a-shared-v4/`;
  transfer cohorts `/m1-03a-transfer-v1` through `v4` retain frozen code,
  permissions, full source assets, independent controls, failures and repeat
  outputs. `m1-03a-transfer-v4-controls-v2` corrects only the DOM reference's
  dropped br whitespace; it uses the unchanged v4 production code and original
  v4 input/archive bindings. Its `parser-transfer-report.json` is historical
  law/code evidence. Earlier code failures replay successfully under
  `shared-v4/former-failure-replays.json` but are not new qualification acts.
  Housing item `1.1-1` and its inline note have a documented semantic correction;
  preserve both the original and corrected drafts. No edition admission changes.

- `m1/pilot_runs/m1-03a-original-four-status-v1/acceptance.json` records the
  historical corrected acceptance: fail, 2/4. Keep that failure immutable.
  `m1-03a-original-four-v8/acceptance.json` now passes all four complete compiler
  paths with two identical fresh builds, unchanged repeats and 345 protected
  prior/source files unchanged. Resolution354 retains 2 approved texts, 5 annexes,
  a 28-row/64-cell table and 93 images; Resolution491 retains 2 approved texts,
  an annex and 6 images. Source images are not transcribed mathematical content.
- `m1-03a-resolution-transfer-v1` through `v3` retain failed/unqualified shapes:
  quoted entire annex, Cyrillic-lookalike Roman heading, legacy merged paragraphs
  and an independent numeric-footnote reader stopped by an asterisk. Never
  relabel those acts as qualification. Resolution25 was retained but unparsed in
  v1; its first frozen-code full validation in v3 passed. It and Resolution416
  remain held-out validation bodies; no rules were developed from their text.
- Final current native matrix: `m1-03a-resolution-transfer-v5/parser-transfer-report.json`
  passes two laws, two codes and Resolutions25/416 with `legal-structure/7`,
  government profile `/3`. Six final-version full builds repeat identically;
  57 protected source records remain unchanged. Earlier bodies remain held-out
  validation, not newly acquired acts or legal admissions; keep all failures.
- The owner-requested 15 October expansion experiment is
  `m1/pilot_runs/native-expansion-20261015-v1/`. Six acts were preselected and
  downloaded using frozen M0 transport/validators/persistence, with unchanged
  compiler `55b93ca`: 3/6 pass (323-FZ, Merchant Shipping Code81-FZ, Inland Water
  Transport Code24-FZ); 261-FZ, Resolutions410/47 fail structural checks. Each has
  two identical fresh builds and an unchanged repeat; source text/integrity is
  retained even for failed legal structure. Keep the initial full failures and
  independent-reader errors immutable. Unknown annex references and quoted
  amendments require future common rules; do not repair or replace these bodies
  inside the frozen baseline. This probe limits general coverage claims and
  does not cancel or broaden the earlier exact-input acceptance evidence.

- The authorized Documind schema-layer experiment is retained under
  `m1/experiments/documind-housing-code-20261015-v1/`, with the upstream checkout
  pinned at `f258286fc1026c1a6cd2b3f624906453681e7c87`. Preserve complete input,
  paragraph maps, token/memory preflights, every raw LLM response and unsuccessful
  generated schema. Full Housing Code stock requests exceed the declared context
  windows of the tested local Gemma/Qwen models; the smaller complete 59-FZ
  schema controls do not replace that gate or the four original-document checks.
  This profile supplies complete retained text directly to Documind autoschema;
  it does not qualify its PDF/OCR front end, full extraction, production parsing,
  transfer or legal admission. Read the dated Documind report before interpreting
  an HTTP 200 or `finish_reason=stop` as a usable legal schema.
- Pool selection's actual.pravo lookup hit 0 of 311 (batch-1 `selection.json`: `looked_up_in_official_tree` 311, no `official_source: actual`) because of a query defect: the `AttrId 999` filter hides acts such as 22-FZ and No.884; without it both are found (21.10.2026, `m1/m1-04a/experiments/20261021-actual-lookup-diagnosis/`). The fix landed in Task B1 (`select_m1_04a_pool.py`, commit `48f3b7c`: the `AttrId 999` filter was removed) and was used for batch 2 (7 of 9 acts found in actual); batch 1 stays frozen.
- Batch-2 PDF permissions (`m1/m1-04a/documents/pool/batch-02/archive/reviews/*-permission.json`) carry a `rights_basis` that speaks of an automatic gold standard from the official pravo.gov.ru text. That text is stale: batch 2 was acquired without `--with-official` and its gold is agent annotation of OCR text. The files are write-once and are left as is; `acquire_m1_04a_pool.py` now writes `AUTHORIZATION_OCR_GOLD` for batches without `--with-official` and takes target dates from `TARGET_DATES` (batch 1 and 2: 2026-10-21; a new batch: the UTC run date).
- Pool acquisition-failure refill (batch 2): a failed slot is replaced deterministically by `select_m1_04a_pool.py refill` (next same-category candidate in the frozen seeded order, max 3 attempts per slot, write-once `selection-refill-NN.json`; the frozen `selection.json` stays). Known failure classes under the frozen publication validator: empty card `name` (all government orders tried, 4 of 4) and early-2011 `File/Pdf` that is not a PDF by signature, so batch 2 is biased against 2011 and `government_order`.
- Owner decision 22.10.2026: codes may have up to 500 pages (KAS RF 480). `select_m1_04a_pool.py` applies `CODE_PAGES_MAX = 500` to the `code` category only when the code quota is positive and records `code_pages_max` in the selection/refill; other categories keep the profile ceiling.
- Code census 22.10.2026 (`m1/m1-04a/documents/pool/batch-03/codes/census.json`, run 1 in `m1/m1-04a/experiments/20261022-code-census/run-1/`): of 29 reference codes only KAS RF (21-FZ, EO 0001201503090041, 480 pages) has an original publication on the portal; the other 28 (adopted 1994-2006) have no portal entry in actual.pravo and the portal day feed for their first publication day is empty (0 items for every checked day 1994-12-08..2006-12-21). Batch-03 `selection.json` holds only KAS.
