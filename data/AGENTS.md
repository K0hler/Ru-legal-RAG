# Local data instructions

Scope: local corpora, raw downloads, fixtures, manifests, and generated databases.

- `data/` content is ignored by default; only this instruction file is tracked.
- Never commit secrets, licensed aggregator exports, private case files, or large generated indexes.
- Treat raw assets as immutable. Store derived artifacts separately and link them by hash and build metadata.
- Small redistributable test fixtures may be committed only after their source, license, and expected hash are documented.
- M0-11 packets contain private evaluation labels. Use only an approved working
  export for implementation/tuning; complete drafts, closed review packets and
  frozen snapshots are for authoring, legal review or explicit gate evaluation.
  Keep raw hashes, transcription method and span offsets with each label. Local
  evaluation is the proposed scope; public redistribution is not approved.
- When revising gold drafts, keep the shared dataset, working export, private
  preparation script and review-template hash consistent. Preserve human review
  annotations; do not regenerate a checklist over the reviewer's edits. Record
  corrections separately and never turn an editorial correction into approval.
- Cross-reference questions distinguish the originating provision from its
  target reference. Include the source context needed to resolve phrases such
  as "these organisations"; the target address alone is not a source-text result.

