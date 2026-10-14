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

- `html_preparation.py` implements the parser-independent preparatory part of
  M1-03A, not its legal structure engine or transfer gate. `prepare-html` reuses
  the diagnostic input/permission contract for one JSON `/redtext` or `/doctext`
  asset. Keep originals, source blockers and immutable replay. BeautifulSoup /
  tinycss2 are optional dependencies in `requirements-html.txt`, imported lazily
  by the CLI. Infer indices only from supported common/inline CSS hints; never
  map `H`/`T` directly to heading levels. Respect `!important` between class and
  inline hints; refuse body/content parsed inside `head` before exclusions.
  Preserve unknown content, note markers,
  tables, image resources and reference attributes. The sidecar maps opening-tag
  anchors, not complete text/provision spans; downstream adapters must still
  retain exact text provenance. See `docs/HTML_PREPARATION.md` and its four-input
  preservation replay; passing these development controls does not satisfy G13.


- M1-03A replaces the act-bound traversals with `structure.py`, one
  `legal-structure/7` engine and `federal-law/5`, `code/5` and
  `government-resolution/3` profiles. Select by
  source identity evidence, never by act constants. The native JSON adapter
  (`actual-native-html/3`) reuses the raw HTML lexer and rebinds exact spans to
  the explicitly selected `/redtext` or `/doctext` field and JSON asset hash.
  Raw diagnostic `--identity` is optional;
  source-only identity is not claim verification or legal admission.
  Roman/decimal/superscript/hyphen numbering and scoped chapter paragraphs (`§`,
  `subchapter`) share the same traversal. Rejected boundaries clear context;
  unmarked textual editorial notes are still notes, and nontext regions must
  add `unresolved_structure` and appear in the report. Preserve previous
  outputs. Final native transfer evidence uses four fresh non-pilot acts,
  after frozen versions; earlier failed acts remain development controls.
  See `docs/M1_03A_SHARED_STRUCTURE.md`; standalone editorial note scope, dated
  editions, PDF/OCR and other act families are not qualified by this evidence.

- Closure correction, 14 October 2026: the earlier 2/4 failure remains retained;
  full compiler acceptance now passes all four original HTML inputs (59-FZ,
  Housing Code, Government Resolutions No. 354 and No. 491) in
  `m1-03a-original-four-v8`. Preparation checks and unrelated transfer acts
  cannot substitute for this mandatory set. Final transfer evidence is separate.
- Resolution scopes separate the approving act, approved texts, title-bound
  annexes and quoted changes. Numeric/letter nesting follows the first child
  marker style within a point; reset or restore it with the owning scope.
  Substantive unmarked annex notes are normative nodes, not unscoped editorial
  metadata. Unknown footnote markers must remain unresolved.
- The raw HTML lexer retains table rows/cells with row/column and spans, plus
  complete image attributes/data. Recognized government tables/images become
  typed source nodes; every legacy `unsupported_regions` entry belongs exactly
  once to `parsed_regions` or `unresolved_regions`. Embedded tables restore
  their owning context; nodes/children retain source order, including images.
  Source raster formulas are not math transcriptions. Reports execute no source
  HTML and display only supported embedded raster image data.
- Unknown whole-document headings inside amendment quotations, Cyrillic-lookalike
  Roman markers and legacy multi-provision paragraphs are unqualified shapes.
  Preserve their failed runs; never turn unsupported content into silent success.
