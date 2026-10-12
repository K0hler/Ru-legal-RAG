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

