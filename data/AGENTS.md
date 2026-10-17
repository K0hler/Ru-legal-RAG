# Local data instructions

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
