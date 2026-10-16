# Corpus compilation module

- `official-structure/5` handles named/word-number upper code parts without
  invented numbers, approved attachment titles proven by a matching HTML title
  and approval stamp, inline normative notes and lettered point captions.
  Unprinted article parts retain contiguous source ordinals, explicitly marked
  `number_origin=official_sidecar_ordinal` and `number_is_explicit=false`.
- `official_normalization.py` may reconcile an overlong end at a confirmed
  parent/next heading, or recover a missing end anchor at the first verified
  peer/ancestor boundary. Preserve original ranges or unresolved anchor names
  and evidence. Text AND nontext gaps must be empty; uncertain starts, parent
  prefixes, leaf crossings and unconfirmed boundaries remain blockers.
- Recovery also handles a contiguous explicit letter list after a colon inside
  an established part/point. Its full continuation/media belongs to the item;
  a printed comma/dash closes the list and restores the enclosing provision.
  Table cells retain their physical table parent and `source_container_address`.
  Audit `/3` checks lexical ownership and recognizes body references separately
  from upper part headings. Raw source data and the v1 route stay unchanged.
- The subsequent frozen `/5` qualification passes only 2/6 full controls (3/6
  technical builds). Source `абзац`, titled word-number upper parts and
  `подраздел` remain unsupported; the fourth failure belongs to the independent
  quoted-article reader. Preserve this distinction and all failures. Development
  6/6 and the two passing resolutions do not qualify arbitrary acts or close G13.

- `official-structure/4` recovers only explicit superscript successors of an
  established point, with matching paragraph style, a known parent, no nested
  crossing or address collision, and no protected quote/form payload. Derived
  nodes have `structure_origin=html_recovery`, HTML evidence and no official
  source ID/state; trimmed neighbors retain `source_declared_span`. Sidecar
  `/data/N` pointers keep original row indices after insertion. Media and inline
  notes follow the full recovered scope, not only its opening paragraph.
- Complete inline amendment payloads and standalone quoted-term definitions
  may remain whole paragraphs in their source provision, with an audit warning
  and no precise quote node. Known form lists may remain multiline paragraphs.
  Unclosed/crossing quotes, unknown headings and uncertain own markers still
  block readiness. Recovery is bounded; passing seven development acts is not
  new G13 qualification, dated admission or proof of universal detection.

- `structure_audit.py` inventories raw HTML markers independently of sidecar
  traversal/regex. The official route records `structure-audit/1` findings
  with evidence, critical/warning counts and a candidate digest. Critical missing
  markers, type/parent/range errors block readiness; form/table/quoted content is
  distinguished from missing own provisions. The v1 route remains unchanged.

- `corpus-input/2` adds exactly one `official_structure` asset plus a hashed
  `structure_bundle` reference. `official_binding.py` verifies source membership,
  archived edition evidence and both private transport selectors before writes;
  both text/structure hashes must be explicitly permitted. V1 remains unchanged.
- `official_structure.py` emits `legal-ast/2`: source units carry sidecar pointers,
  full scalar spans and canonical/display numbers; lexical child blocks own
  tokens exactly once. Validate level/prefix/range/number agreement and reject
  malformed structures. Keep table/image regions once; raster transcription is
  unverified. Notes retain structural containment separately from legal scope;
  standalone editorial notes remain document-level with unresolved scope.
- `official-structure/2` completes quoted articles/parts under their amending
  source item and form sections/list items plus numbered table rows. Media and
  inline notes inherit the completed scope. Mixed quote boundaries inside one
  paragraph remain structural blockers; unsupported inline source anchors fail
  and multiple markers across breaks stay unresolved. Missing source siblings
  must not become children of the previous provision by adjacency.
- Bundle v2 uses its per-capture transport evidence; v1 uses historical asset
  metadata, checking the response URL when present. Check IPS body selectors too.
  All seven replayed acts preserve source nodes/text/media; this is diagnostic
  development coverage, not a new G13 qualification or legal admission.

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
