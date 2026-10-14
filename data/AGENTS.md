# Local data instructions

Scope: local corpora, raw downloads, fixtures, manifests, and generated databases.

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


- M1-03A final development replay is `m1/pilot_runs/m1-03a-shared-v4/`;
  transfer cohorts `/m1-03a-transfer-v1` through `v4` retain frozen code,
  permissions, full source assets, independent controls, failures and repeat
  outputs. `m1-03a-transfer-v4-controls-v2` corrects only the DOM reference's
  dropped br whitespace; it uses the unchanged v4 production code and original
  v4 input/archive bindings. Its `parser-transfer-report.json` is the accepted
  native engineering evidence. Earlier code failures replay successfully under
  `shared-v4/former-failure-replays.json` but are not new qualification acts.
  Housing item `1.1-1` and its inline note have a documented semantic correction;
  preserve both the original and corrected drafts. No edition admission changes.

- `m1/pilot_runs/m1-03a-original-four-status-v1/acceptance.json` records the
  corrected stage acceptance: fail, 2/4. Original No. 354/491 inputs fail the
  actual compiler before derived writes; 59-FZ/Housing repeats are unchanged.
  The prior code/law transfer report is subset evidence and cannot close
  M1-03A. Retain all earlier results rather than rewriting the failed history.
