# M1-03A parser options after the Documind probe

Research date: 15 October 2026. Status: external research and a bounded, read-only
source-API probe. No production parser, acquisition contract, admission decision
or milestone gate was changed.

## Decision supported by the evidence

For the seven checked official HTML inputs, the strongest newly verified route
is to acquire the source's existing legal structure alongside its HTML. Both
official banks expose typed, nested, edition-specific structural units with
HTML start/end anchors. A new model does not need to infer those trees.

For inputs without that sidecar, the practical open-source shortlist is:

1. **Indigo's import pipeline** for legislative hierarchy and an Akoma Ntoso
   representation, with a Russian recognition profile still required.
2. **Warp-Ingest**, or its upstream **nlm-ingestor** for HTML/DOCX, for geometry,
   nested lists and clause grouping. Their numbering and language assumptions
   require validation on Russian acts.
3. **PageIndex Flash** for a local PDF outline without an LLM. Its output is a
   section/page tree, not a demonstrated article/part/item/subitem legal AST.

None of these external engines was installed or run on the corpus in this
research. The earlier [Documind results](M1_03A_DOCUMIND_EXPERIMENT_2026-10-15.md)
and [native expansion failures](M1_03A_PARSER_HANDOFF_2026-10-15.md) remain valid.

## 1. Verified official structure route

### Discovery and transport

The [official publication of FSO Order No. 92 of 4 July 2024](http://publication.pravo.gov.ru/document/0001202411180012)
identifies the technical requirements and markup formats. Annex 2, section V,
describes separate JSON structural markup linked to HTML element identifiers.
The standard led to the search; the live responses below establish actual
availability for these inputs. A format specification alone would not do so.

The live public frontends identify the endpoints:

- `actual.pravo.gov.ru`: [config](http://actual.pravo.gov.ru/config.js) and
  [content frontend](http://actual.pravo.gov.ru/content/js/content-build.js),
  whose `getContent()` requests `getcontent/?bpa=...&rdk=...`.
- `ips.pravo.gov.ru`: [frontend bundle](http://ips.pravo.gov.ru/main.js),
  whose `getDocContentOnly()` requests
  `/api/ips/legislation/document_content?nd=...&rdk=...&bpa=...`.

The observed nodes carry `id`, `np`, `npe`, `caption`, `unit`, `lvl`, and `state`.
`np` and `npe` identify the first and last HTML elements. `lvl` and the ordered
node stream recover parents; hierarchical IDs provide an independent consistency
check. This is substantially more detailed than a table of article headings.

### Bounded results

| Retained document | Bank / edition selector | Nodes | Observed unit counts |
|---|---|---:|---|
| No. 59-FZ | actual / `466661`, 2025-03-30 | 89 | 18 articles, 50 parts, 21 items |
| Housing Code | actual / `488169`, 2026-09-01 | 2,051 | 12 sections, 21 chapters, 243 articles, 1,085 parts, 683 items, 7 subitems |
| No. 261-FZ | actual / `496053`, 2026-08-04 | 472 | 10 chapters, 51 articles, 160 parts, 231 items, 20 subitems |
| Resolution No. 354 | ips / `59`, 2026-07-27 | 742 | 351 items, 353 subitems, 28 sections, 5 annexes, 5 generic attachments |
| Resolution No. 491 | ips / `21`, 2026-09-26 | 167 | 83 items, 76 subitems, 5 sections, 1 annex, 2 generic attachments |
| Resolution No. 410 | ips / `8`, 2026-03-01 | 283 | 139 items, 132 subitems, 9 sections, 1 annex, 2 generic attachments |
| Resolution No. 47 | ips / `17`, 2026-09-01 | 102 | 72 items, 20 subitems, 6 sections, 3 annexes, 1 generic attachment |

Dates and completion flags are source declarations, not legal applicability
decisions. The two banks were queried separately; their API and document coverage
were not assumed interchangeable.

For **all seven responses, 3,906 nodes in total**, the local checks found:

- Every start/end anchor exists in the exact retained source HTML.
- No reversed ranges, children outside parent ranges, parent-ID prefix conflicts,
  level jumps, duplicate node IDs or duplicate HTML IDs.
- Seven fresh edition-text responses match the seven retained raw assets
  **byte for byte**, including their SHA-256 hashes. This goes beyond checking
  that similarly named anchors survived across different editions.

The Housing Code sidecar explicitly includes the seven lettered subitems
`а–ж` under article 12, item `2¹`, which the LlamaExtract export left embedded
in a text field. Their parent is `si_h1_a12_j2:1~`; the last child is `k-8`,
so child suffixes must not be treated as consecutive legal numbers.

Direct examples:
[Housing Code structure](http://actual.pravo.gov.ru:8000/api/ebpi/getcontent/?bpa=ebpi&rdk=488169),
[No. 261-FZ structure](http://actual.pravo.gov.ru:8000/api/ebpi/getcontent/?bpa=ebpi&rdk=496053),
[No. 354 structure](http://ips.pravo.gov.ru/api/ips/legislation/document_content?nd=1000000000102147807&rdk=59&bpa=c000000000),
[No. 47 structure](http://ips.pravo.gov.ru/api/ips/legislation/document_content?nd=1000000000102104517&rdk=17&bpa=c000000000).

### Remaining work before production

These are successful availability and structural-consistency checks, not a
completed legal compiler qualification. In particular:

- Source `unit=вложение` is broad: No. 354 uses it for both approved texts and
  a notes container with two notes. It cannot map unconditionally to
  `approved_text`. Preserve the source label and determine the canonical role.
- Preserve rich numbering such as `<sup>` and the source ID syntax. Do not sort
  `pNNN` anchors numerically: HTML document order determines their position.
- Derive exact character/byte coordinates from the archived HTML. Element
  identifiers alone are not exact quotations, PDF coordinates or stable lineage
  across editions.
- Account for preambles, editorial notes, quotations, unnumbered text, tables,
  images and formulas outside or inside structural spans. Do not lose text or
  duplicate descendant text in parent provisions.
- Test the difficult quotation/annex/form scopes independently; valid nesting
  and matching counts do not establish semantic correctness.
- Archive the sidecar with its edition selector, response hash and text-asset
  binding. A changed or missing sidecar must remain visible.
- Review the frozen acquisition/handoff contract before adding this asset;
  retain old evidence and replay the required checks. This research did not alter
  the frozen adapters.

The route uses public official source data rather than an open-source parser.
It therefore fits the broadened “any method” request, while leaving a separate
parser/OCR route necessary for other sources and formats.

## 2. Open-source candidates checked against implementation

| Candidate / source | What it actually offers | Fit and material limitation |
|---|---|---|
| [Indigo](https://github.com/laws-africa/indigo), GPL-3.0 | Python/Django legislative platform with real automatic PDF/DOCX/HTML/text import, not only an XML editor. `DoctypePipeline` calls recognizers, nesting stages, then Bluebell serialization. | Strongest legislation-specific framework to examine. Its default recognizers use terms such as `Article`, `Chapter`, `Part`, English-style numbering and attachment rules. Russian recognition, quoted amendments, editorial roles and provenance still need a profile and validation. |
| [Warp-Ingest](https://github.com/Open-Source-Legal/Warp-Ingest), Apache-2.0 | Pure-Python PDF parser; block/word geometry, section parents, nested lists, tables and cross-page joins. Optional additive semantic units split enumerated clauses into nested units. | Good PDF experiment candidate without a generative model. It rewrites nlm-ingestor and shares its lineage. The semantic layer contains English contract vocabulary and enumerator heuristics; it is not demonstrated as a Russian statutory parser. PDF only. |
| [nlm-ingestor](https://github.com/nlmatics/nlm-ingestor), Apache-2.0 | Broader format coverage: PDF, HTML, text, and Tika-mediated DOCX/other formats; section/list/table structure. | Useful counterpart when native HTML/DOCX must remain native. The older PDF path needs modified Tika/JVM and OCR dependencies. English lexical features and generic layout labels require Russian legal checks. Do not count it and Warp as independent algorithms. |
| [PageIndex Flash](https://github.com/VectifyAI/PageIndex/tree/main/pageindex/flash), MIT | PDF layout/bookmark tree with `nodes`, `start_index`, `end_index`, and `toc_source`; structure generation can run without an LLM. | Useful low-cost outline baseline. It does not establish typed article/part/item/subitem recovery, exact text spans or legal note roles. No hierarchy can fall back to page nodes; unreadable PDFs yield no structure. |
| [Slaw](https://github.com/laws-africa/slaw), MIT | Real Treetop legal grammar: plain text to Akoma Ntoso with nested-list postprocessing and schedules. | A genuine legislative parser, but the bundled grammar targets South African practice. Russian support requires a new grammar. Current README's PDF wording is historical: the changelog explicitly removed PDF ingestion in 2.0; extract text separately. Prefer inspecting current Indigo before adopting this older Ruby path. |
| [LexML normative-document parser](https://github.com/lexml/lexml-parser-projeto-lei), GPL-2.0 | Scala parser with DOCX reading, document profiles, legal-label combinators, hierarchy rendering and validation. | Strong example of explicit normative structure: articles, paragraphs, incisos, alíneas and items. Its labels and numbering rules are Brazilian/Portuguese, not a ready Russian service. JVM/Maven integration and adaptation are additional work. |
| [eurlex-unit-parser](https://github.com/Kymylyy/eurlex-unit-parser), MIT | Source-specific EU HTML units with explicit parents, canonical paths, source references, annex/table handling and validation. | Useful design reference for an adapter consuming rich source structure. Its EUR-Lex DOM and language assumptions do not transfer automatically to Russian banks. |
| [HiPS](https://github.com/anybass/HiPS), source MIT; dataset separately licensed | Reproducible outline/section segmentation for legal textbooks; TOC alignment and layout/local-context LLM refinement. | Research reference for deep headings, not statutory leaf extraction. README still marks parts of the local Phi4/Llama3 path as forthcoming and documents manual cleaning of GPT outputs. Not the next turnkey experiment. |

### Important details behind the shortlist

**Indigo is more capable than Bluebell alone.** Bluebell consumes explicitly
marked structural text. Indigo's upstream importer first tries to create that
markup from unstructured input. The checked
[importer](https://github.com/laws-africa/indigo/blob/e07b0eddb3771c89db39c6521419944fc48a9842/indigo_api/importers/base.py)
and [hierarchy stages](https://github.com/laws-africa/indigo/blob/e07b0eddb3771c89db39c6521419944fc48a9842/indigo/pipelines/hier.py)
include `IdentifyArticles`, `IdentifyChapters`, `IdentifySubsections`, attachment
detection, `NestBlocks` and `NestedSubparagraphs`. The Russian adaptation cost
is an inference from these implementation assumptions, not a measured failure.

**Warp has clause-level logic beyond heading detection.** Its
[semantic-unit implementation](https://github.com/Open-Source-Legal/Warp-Ingest/blob/fea191b478f39dd58486c175d1d2c8b16975b665/warp_ingest/ingestor/semantic_units.py)
preserves the fine structural graph and adds nested clause units. Its English
contract guards, article/section patterns and definition heuristics are visible
in code. Geometric parent links still need independent legal-role checks.

**PageIndex has a model-free mode.** The checked
[Flash README](https://github.com/VectifyAI/PageIndex/blob/af92d9658a6a9c0ae31171b43198db28951af2f4/pageindex/flash/README.md)
documents `page_index_flash(path, summary=False, optimize=False)` for a raw tree.
Summaries and full expansion use an LLM. The
[v0.2.21 release](https://github.com/VectifyAI/PageIndex/releases/tag/v0.2.21)
describes the layout-based engine; its retrieval benchmarks are not Russian
legal-structure evidence. [Issue 237](https://github.com/VectifyAI/PageIndex/issues/237)
documents self-hosted OpenAI-compatible/LiteLLM configuration, but that route
was not tested against this machine's LM Studio models here.

The structural-only paths above do not require loading a large generative model
into the RTX 5070 Ti. OCR, optional models and actual memory/runtime remain
separate configuration questions; no local performance figures were measured.

## 3. Candidates not promoted

- [Lex-parse](https://github.com/Lexvault-in/lex-parse) is actual code, but its
  [section numbering](https://github.com/Lexvault-in/lex-parse/blob/97493e3e01dfab3c91a968361d7fa224ebb5d6d7/lexparse/engine/section_tree.py)
  explicitly matches `ARTICLE`, `SECTION`, Latin `(a)` and Roman `(i)`;
  its clause classifier uses keyword counts. It is not a newly verified Russian
  hierarchy engine despite the contract-aware description.
- [OpenDataLoader](https://github.com/opendataloader-project/opendataloader-pdf)
  and [EdgeParse](https://github.com/raphaelmansuy/edgeparse) are credible generic
  PDF/layout tools. A heading or nested-list claim does not establish legal
  typing. OpenDataLoader's [issue 755](https://github.com/opendataloader-project/opendataloader-pdf/issues/755)
  was still open in the live GitHub response: nested lists flattened and article
  headings misclassified. This is a reported example, not a controlled comparison
  against Warp or PageIndex.
- [UniHDSA](https://github.com/microsoft/CompHRDoc/tree/main/UniHDSA) describes
  relation-based hierarchy recovery, but explicitly withholds the model code
  under company policy. Configurations/evaluation code are not a runnable model.
  [HRDoc](https://github.com/jfma-ustc/HRDoc) does release a baseline, but targets
  research-paper roles and requires domain work; it is not a ready legal parser.
- [RusLawOD](https://github.com/irlcode/RusLawOD) is a relevant Russian corpus,
  not proof of a full legal hierarchy parser. Its published description excludes
  internal hierarchy annotation and removes tables for uniformity.
- Generic OCR/Markdown extraction and fixed-size hierarchical chunking remain
  useful frontends or retrieval components. They do not resolve the missing
  legal parent/child and scope decisions by themselves.

## 4. Recommended next experiment

First build an isolated adapter experiment over the seven retained HTML inputs
and their newly retained sidecars. Keep production untouched initially. Compare
every source node/parent/number with independent controls, account for all
unassigned text, and inspect the three known failure shapes: quoted amendments
in No. 261-FZ, edition-qualified annexes in No. 410, and forms/annexes in No. 47.
The deliverable should be a complete, source-bound legal draft with explicit
unresolved material, not a fresh model-generated schema.

For a genuinely separate PDF route, use the same real document and independent
controls to compare Warp-Ingest with PageIndex Flash's structural-only mode.
Judge full legal leaves and attachment/note scope as well as headings. Do not
convert an already structured HTML input to PDF merely to make it fit a tool.

If inference is necessary for a source without reliable structural metadata,
a bounded alternative is to ask a local model to label immutable block IDs,
types and parents in overlapping windows, while deterministic code retains and
checks the original text. This is a proposed method, not an implemented or
qualified solution; it still needs cross-act transfer evidence.

## Evidence and reproducibility

Search used Parallel Search, Exa and Firecrawl across Russian legal tools,
legislative grammars, layout/list parsers, tree-oriented LLM systems and hierarchy
research. Exa's five searches requested 47 result slots, including duplicates;
this is not a claim of 47 independently verified full-text sources.

Ignored local evidence is retained under
`data/m1/research/parser-search-20261015-v2/`:

- `search-index.json`: 23 retained search/fetch result lists, 153 URL entries
  before deduplication, from the three requested services.
- `official-structure-anchor-checks.json`: all seven exact source bindings,
  response hashes, unit counts, boundary/parent checks and attachment samples.
- `official-fresh-text-checks.json`: seven fresh responses and byte-level equality
  against the retained source assets.
- `official-housing-boundary-check.json`: detailed article 12 child paths.
- `upstream/`: source responses, public frontend snapshots and inspected pinned
  external implementation files. The initial incorrect redactions query's 404
  is preserved separately from the successful request.

Checked implementation revisions: Indigo `e07b0ed`, Slaw `0c1c25b`,
LexML `0717d18`, Warp `fea191b`, nlm-ingestor `5f0c1b9`, lex-parse `97493e3`,
HiPS `5ca16dd`, eurlex-unit-parser `5aa49ca`, PageIndex `af92d96`.

The probe inspected only already permitted diagnostic source documents and
public upstream material. It did not read closed retrieval gold, run an external
extraction service on the corpus, qualify arbitrary HTML/PDF, or change edition
admission. The successful source-side structure route is new evidence for the
next M1-03A experiment, not retroactive success for the frozen native compiler.
