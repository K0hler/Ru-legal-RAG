# Corpus compilation module

Scope: extraction, cleanup, legal structure, canonical entities, review gates, and corpus builds.

- `LegalAct` is stable identity; `LegalEdition` is a specific verified snapshot; `LegalProvision` belongs to exactly one edition.
- Preserve offsets and provenance through every transformation. Account for all source text as parsed, unresolved, or explicitly excluded.
- Build `ActIdentity` before the Legal AST. Uncertain structure becomes `unresolved_block`; never invent a provision.
- Keep `captured_at`, declared revision date, and verified `valid_from`/`valid_to` separate. Unknown coverage stays unknown.
- IDs and hashes must be deterministic for the same inputs and tool versions.
- Approved canonical data is immutable within a `CorpusBuild`; activate a new build only after its gates pass.
- M0-11 `python -m legal_rag.corpus.gold` validates local gold-question records
  against tracked ID membership and archived raw/text hashes. Positive labels
  are source-snapshot lookups, not corpus admission or verified applicability.
- Freeze requires explicit hash-bound Legal Reviewer decisions for every label
  plus local-storage approval. A disputed label needs an independent second
  reviewer; changed frozen content must be rejected rather than overwritten.
- During parser/retrieval tuning, use only the legally approved working export.
  Complete draft/review/frozen files and the private preparation script contain
  closed labels and are restricted to authoring, legal review or explicit gate
  evaluation. No dataset labels belong in production code or regression fixtures.
- Acceptance: `python -m unittest discover -s tests/legal_rag/corpus -p 'test_*.py' -v`;
  then Ruff, compileall and a retained-packet validation without printing labels.

