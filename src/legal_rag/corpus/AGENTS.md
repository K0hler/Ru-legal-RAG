# Corpus compilation module

Scope: extraction, cleanup, legal structure, canonical entities, review gates, and corpus builds.

- `LegalAct` is stable identity; `LegalEdition` is a specific verified snapshot; `LegalProvision` belongs to exactly one edition.
- Preserve offsets and provenance through every transformation. Account for all source text as parsed, unresolved, or explicitly excluded.
- Build `ActIdentity` before the Legal AST. Uncertain structure becomes `unresolved_block`; never invent a provision.
- Keep `captured_at`, declared revision date, and verified `valid_from`/`valid_to` separate. Unknown coverage stays unknown.
- IDs and hashes must be deterministic for the same inputs and tool versions.
- Approved canonical data is immutable within a `CorpusBuild`; activate a new build only after its gates pass.
- M1-01 implements `python -m legal_rag.corpus compile` with the diagnostic
  UTF-8 fixture profile only. `corpus-input/1` and a hash-bound
  `processing-permission/1` are validated before derived writes. Read source
  records directly without importing acquisition/OCR or changing frozen source
  code; the exact contracts and replay are in `docs/M1_01_FIXTURE_DRAFT.md`.
- Keep `original_amendments` separate from the optional frozen consolidated
  candidate wrapper. Stale candidates cannot be wrapped; permitted diagnostic
  assets retain source status and admission blockers. No M1-01 draft is admitted
  or reconstructed; unsupported formats fail, unsupported text stays unresolved.
- The fixture parser preserves UTF-8 bytes and original newlines, gives unknown
  identity/duplicate articles unresolved blocks and excludes only explicit
  whitespace. Repeats verify every immutable artifact before reporting
  `unchanged`; never overwrite a conflicting record or write into raw/approved
  state. Run corpus tests, frozen handoff regressions and retained CLI replay.
- M1-03 adds `native_text.py`: the explicit saved JSON `/redtext` HTML profile
  and bound 59-FZ structure parser. Validate identity from the preamble and
  unique final presidential signing fields before addresses; body references
  cannot repair a conflicting signature. Standalone notes are document-level;
  only a note in the same source paragraph inherits the provision address.
  Native offsets are Unicode positions inside
  the decoded JSON scalar, never raw JSON bytes or physical PDF pages. Retain
  every text/entity token, entity/whitespace mappings, notes and original HTML;
  source-marked superscripts affect addresses without changing visible digits.
  Unknown numbering/boundaries (including multiple numbered provisions separated
  by a break in one paragraph), duplicate addresses and unsupported lists/tables
  stop targeting and remain unresolved. Keep original source/admission blockers.
  Eight synthetic native tests and the full two-build replay are documented in
  `docs/M1_03_NATIVE_TEXT.md`; the earlier fixture artifacts stay byte-identical.

