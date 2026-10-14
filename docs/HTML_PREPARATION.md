# Parser-independent HTML preparation

Implemented on 14 October 2026 as a preparatory part of M1-03A. The legal
structure engine, non-pilot transfer qualification and G13 remain open.

## Implementation

`src/legal_rag/corpus/html_preparation.py` provides `prepare_html(html)` and a
permission-gated `prepare-html` CLI. It uses BeautifulSoup 4.14.3 for the DOM,
Python's `html.parser` for original opening-tag anchors, and tinycss2 1.4.0 for
CSS syntax. Neither Docling nor Dedoc is selected or imported. No act number,
title, date, filename or source hash selects a preparation rule.

| Input | Preparation |
|---|---|
| `head`, `script`, `style` | Explicit exclusion, recorded separately; original HTML is retained |
| Presentation attributes and event handlers | Removed from output; original attributes remain in the map |
| `span` / `font` with explicit `vertical-align: super` / `sub` | `sup` / `sub`, with unchanged text |
| Other `font` | `span`, with unchanged text |
| Source `mark` / `markx` classes | `data-lr-note="true"` hint; no inferred note scope |
| Paragraphs, breaks, headings, lists, tables, images, links, unknown tags | Preserved in order |

Typography hints use inline declarations and simple top-level `.class` /
`tag.class` selectors. CSS syntax is parsed, including legacy HTML comment
wrappers. Screen/print media rules and complex selectors are not evaluated.
`!important` is respected across class and inline declarations. Conflicting
class hints remain unconverted. This is a conservative source-hint
reader, not a computed-style renderer. Classes such as `H` and `T` remain in the
sidecar for the future legal parser; they are not assigned arbitrary heading
levels. No dots, digits or other legal text are inserted or removed.

Each retained tag has original and prepared opening-tag character spans in
`manifest.json`. These are Unicode positions inside `source.html` and
`prepared.html`, respectively. The source asset hash and JSON pointer bind the
original scalar. **These anchors are not full element spans or provision/token
locators.** A downstream structure adapter must still produce its own exact
text-span mappings. Original classes, styles, IDs and reference attributes are
available in the sidecar; unchanged original HTML is also saved.

The manifest accounts for decoded DOM text as retained or explicitly excluded.
Comments/declarations have their own exclusion entries. Empty comments replace
removed markup so that BeautifulSoup does not merge adjacent whitespace nodes
on the next parse. Hidden editorial text remains present. This is content
preparation, not a browser security sanitizer or a JavaScript renderer.
If the chosen DOM backend places body/content inside `head` (including some
omitted-end-tag HTML), preparation refuses before writing instead of excluding
that content as metadata. Such input needs explicit HTML repair or a qualified
different DOM backend.

## Running it

```powershell
python -m pip install -r requirements-html.txt
$env:PYTHONPATH = "src"
python -m legal_rag.corpus prepare-html `
  --input data/m1/inputs/m1-02-completion/inputs/housing-code-2026-10-01.json `
  --target-date 2026-10-01 `
  --output-dir data/m1/prepared-html
```

The CLI currently accepts one permission-bound JSON asset with explicit
`/redtext` or `/doctext` evidence. The pure HTML function is independent of those
portal wrappers. Input validation and diagnostic permission use the existing
`corpus-input/1` contract. The declared target date is a claim, not verified
applicability. Source status/admission blockers are retained.

The output directory is content-addressed and contains `prepared.html`,
`source.html`, `manifest.json` and the validated `input.json`. The ID binds input,
output, map and runtime versions. Identical repeats report `unchanged`; conflicts
and destinations inside protected source/approved state fail before writes.
Image bytes/URLs and link destinations are retained; resources are not fetched.
Relative URLs still need their original base context in the downstream adapter.

## Full retained-document verification

Local evidence: `data/m1/experiments/html-preparation-20261014-v1/verification.json`
and its retained `verify.py`. All paragraph texts and complete body text match
exactly. Table topology/cell spans, image sources, links, portal commands, note
texts and index typography pass; repeated and independently created outputs are
byte-identical. The input archive and earlier Docling experiment match their
340-file before/after snapshot.

| Document | All `p` elements, including empty ones | Note markers | Superscripts | Subscripts | Tables | Images |
|---|---:|---:|---:|---:|---:|---:|
| 59-FZ | 154 | 24 | 6 | 0 | 0 | 0 |
| Housing Code | 2,826 | 996 | 419 | 0 | 0 | 0 |
| Government Resolution 354 | 2,337 | 602 | 765 | 265 | 1 | 93 |
| Government Resolution 491 | 311 | 90 | 52 | 9 | 0 | 6 |

These are preservation controls on four development documents, not legal AST
accuracy or proof of universal coverage. Arbitrary HTML/CSS and other source
formats remain unqualified. The closed gold set is not used. Failed prototype
outputs remain in separate content directories; the final verification names
the passing IDs. The initial failure JSON's CSS-comment diagnosis was an early
hypothesis: inspection also identified nested media overrides in the prototype's
regex scan. The final code uses a CSS parser and regression tests for both cases.

Run the corpus pytest suite and frozen source unittest suite after changes.
The focused `test_html_preparation.py` covers content/metadata preservation,
ambiguous and media CSS, legacy comments, whitespace boundaries, original/output
anchors, `!important`, head-content refusal, both portal fields, CLI/date refusal
and immutable protected output.

## Existing libraries checked through Exa

| Library | Relevant capability | Fit for this preparation |
|---|---|---|
| [HtmlRAG Toolkit](https://github.com/plageon/HtmlRAG/blob/main/toolkit/README.md) | `clean_html`, block trees and query-based pruning | Closest RAG-oriented option; its example strips source classes. Pruning is a later query operation, not a substitute for retaining the full act |
| [lxml Cleaner](https://lxml-html-clean.readthedocs.io/en/latest/usage.html) | Configurable script/style/tag/attribute removal | Useful general cleaner; CSS indices and original-coordinate bindings still need an adapter |
| [Trafilatura](https://trafilatura.readthedocs.io/en/latest/usage-python.html) | Heuristic main-text extraction | Useful for web articles; full legal-text preservation requires independent controls |
| [pure-html-for-rag](https://github.com/Page-Replica/pure-html-for-rag) | Dependency-free JavaScript cleaner | Its documented cleanup removes images; unsuitable as our default for formula images |

The implementation reuses [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
and [tinycss2](https://doc.courtbouillon.org/tinycss2/stable/) instead of adding a
full extraction/pruning framework. The repository's permission, original-source
bindings and conservative preparation rules are the small project-specific layer.
