# Local data instructions

Scope: local corpora, raw downloads, fixtures, manifests, and generated databases.

- `data/` content is ignored by default; only this instruction file is tracked.
- Never commit secrets, licensed aggregator exports, private case files, or large generated indexes.
- Treat raw assets as immutable. Store derived artifacts separately and link them by hash and build metadata.
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

