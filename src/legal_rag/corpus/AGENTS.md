# Corpus compilation module

- M1-04A adds diagnostic `ocr_structure.py` (`ocr-layout-structure/7`) before
  the shared grammar for government/sanitary resolutions. Group only physical
  OCR paragraphs, retaining source block IDs, every token/span and region binding;
  normalized whitespace/Markdown views never replace source text. OCR issuer,
  date/number/title are compared with the evidence-bound claim. Exact split
  approval/title and decimal-prefix rules are shared, not act-specific.
- Explicit OCR approval/attachment captions use source reference evidence,
  independently of Text/Page-header/Page-footer labels. Caption fragments retain
  individual tokens/spans; repeated physical captions preserve the active owner.
  Require a unique full typed designation/title or matching current-act identity;
  never merge SP/SanPiN types or identifier prefixes. Missing/ambiguous references
  keep scope unresolved, including tables, whose cells/topology remain present.
  Canonical numbers are null on unnumbered annexes. Validate caption/title evidence
  order/ownership against actual source blocks, not only a self-consistent graph.
  The shared native grammar version is unchanged: these additions are OCR-only.
- `validate_ocr_tree` checks actual text/spans, table cells, graph order/children,
  region coverage/ownership and intervening sibling scopes; returned data must
  not alias the saved extraction. Keep `pdf_structure_unqualified` on every
  PDF route: current full development runs still have critical unresolved
  structures. Task 3 independent transfer qualification has not passed.
- Physical images/headers/footers/footnotes must not open, close or rebalance
  amendment quotations. Multiple exact footnote references retain candidate
  owners as unresolved; never silently pick the last one. Only a confirmed
  independent approval/annex or explicit section resets an unknown-section scope.

- M1-04A stage 2 is `logical_text.py` (`logical-text/1`): region roles
  (content/noise/picture/table with a reason) and logical body/footnote
  paragraphs whose fragments keep region, page, bbox, text nodes, offsets and
  join type. Every text node is in exactly one paragraph or noise region; the
  input is never mutated and `match_text` is a matching view only. Declared
  prototype deviations: D1 forbids any join across a missing physical page
  (a multi-region unnumbered footnote on the next page still joins); D2 makes an empty-text content region its own
  `kind=empty` paragraph that is never open or joined to. The `logical-text`
  CLI verifies schema/identity/extraction hash before writing one immutable
  record. Known limitation: an empty Text region at a page top counts as
  first_on_page (as in the prototype) and blocks a body continuation onto the
  next region. Stage 3 and `compile` do not consume it yet.

- M1-04's `pdf_extraction.py` normalizes retained dots.mocr `pages[].layout[]`
  without loading a GPU library. Keep raw region records, physical-page/image
  coordinates, OCR-string locators and table spans/empty cells. Its document
  tree describes pages/regions/cells; legal grammar output remains diagnostic
  and carries `pdf_structure_unqualified`. Block ownership uses
  `source_region_id`: `region_id` is reserved for region events by `structure.py`.
  Grammar `block_id` is the source-order integer; retain the opaque hash as
  `source_block_id`, because existing grammar ordering/slicing uses numeric IDs.
  OCR offsets never identify byte positions in the original PDF.
- `ocr_runtime.py` validates the entire PDF permission/input before staging.
  Configure the external lab path through `ocr-provider/1`; fresh execution
  requires an already-healthy service and uses UUID-isolated outputs. Saved
  `ocr-results/1` replay needs no Docker. Retain native files and provider
  fingerprints in immutable `ocr-evidence/`; `extraction-index/1` binds exact
  input/permission hashes. PDF `compile --extraction-index` verifies every
  extraction and native evidence hash, retaining all admission/OCR blockers.
- OCR-Lab's `dotsmocr-layout/2` export (named by `run.json` `export.format`)
  keeps only `layout` in `document.json`; each raw response lives in
  `native/page_NNNN.json` with its `page_number`/`image_size`. `_read_ocr_output`
  attaches sidecars in memory for fresh import and evidence replay alike, so
  the normalized extraction equals the inline-native one. Legacy inline results
  are read unchanged; unknown formats, missing/mismatched sidecars and embedded
  native in this format fail before writes.
- Runtime execution uses immutable copied client/config/prompt files. Check the
  executed snapshot after inference, not the mutable lab originals. Re-import
  native evidence through the normalizer before accepting an extraction index;
  matching hashes alone cannot justify foreign source content. Validate every
  resolved output descendant to reject symlink escapes and protected-state writes.
- Optional Picture `retain_unresolved` needs the compatible external client;
  keep its incomplete native response and `picture_ocr_incomplete_response`, never
  truncated text. Strict failure remains available. Table captions/outside-cell
  text and nullable cell geometry are part of the preservation contract.
- `retain_unresolved` now sets `recover_repetitions=true` only in the copied
  Picture profile. The external client streams/cancels repeated tails, preserves
  each response before retry, and tries at most one wider 128-pixel crop.
  Successful narrow crops and primary OCR stay unchanged; all failed native
  attempts remain evidence. The normalizer has no source/page-specific waiver.

- Owner-approved direction, 16 October 2026: `corpus-input/2` uses
  `official_import.py` (`official-json-import/1`), not `build_official_tree`.
  Preserve every raw source row, opaque ID, unit, caption and level; addresses
  identify source nodes, not inferred legal citation numbers. No semantic type
  whitelist, number reconciliation, quote completion, sibling recovery or HTML
  marker audit runs on this route. The reconstruction modules below are retained
  historical tools, not compiler entry points. V1 native parsing is unchanged.
- Import source boundaries verbatim. Missing/reversed/crossing ranges produce
  `source_integrity` findings and a review blocker, never automatic repairs;
  affected branches cannot supply precise text ownership. Keep complete text
  and media plus source order, including when a source range is unresolved.
  `legal-ast/2` source units carry `source_record` and nullable `source_span`;
  `kind=source_unit` and null canonical numbers are deliberate source granularity.
  Same-edition binding, identity, permission and hashes remain mandatory.
  Closure evidence/limits are in `docs/milestones/m1/03a/M1_03A_CLOSURE_2026-10-16.md`.

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
  code; the exact contracts and replay are in `docs/milestones/m1/M1_01_FIXTURE_DRAFT.md`.
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
  `docs/milestones/m1/M1_03_NATIVE_TEXT.md`; the earlier fixture artifacts stay byte-identical.

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
  retain exact text provenance. See `docs/guides/HTML_PREPARATION.md` and its four-input
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
  See `docs/milestones/m1/03a/M1_03A_SHARED_STRUCTURE.md`; standalone editorial note scope, dated
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
