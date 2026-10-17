# Legal RAG

Repository skeleton for the M0-M2 vertical slice: reproducible acquisition of official legal sources, deterministic corpus compilation, and exact/full-text retrieval with verifiable evidence coordinates.

M0-12 reporting and contract freeze are implemented. The [M0 gate](docs/milestones/m0/M0_GATE_REPORT.md)
is `pass`; M0 is accepted and M1 may start. The product owner accepted
`not_recorded` placeholders for the missing M0-10 timing measurements; no repeat
legal review is required for that measurement deviation.
The retained M0-11 v2 gold set contains 30
Legal Reviewer-approved questions split 15/15 into working and closed sets;
the two-hour review and local-storage approval are recorded.
See [the gold-set record](docs/milestones/m0/M0_11_GOLD_SET.md).
The fixture-backed path and the
`PublicationPravoConnector` store immutable raw bytes and provenance, then report
`new`, `unchanged`, `changed`, or `failed` without losing the latest successful
asset. Changed runs record the old and new SHA-256 without copying raw content into
the report. Publication reconciliation stores acquired and discovered records in
the canonical `items/` lifecycle and writes evidence-backed `publishes` and
`amends` source claims; missing or ambiguous targets remain visible exceptions.
The publication connector uses the portal's documented HTTP read API without a
protocol fallback.
`ActualPravoConnector` archives the portal card, declared-editions response, and
consolidated-text response separately for the ЖК РФ and 59-ФЗ pilots. It links
each candidate to the declared act while keeping the source edition date separate
from unknown verified temporal coverage.
`LegislationRussiaConnector` archives the portal's JSON card and selected
`documenttext` response separately for the ПП РФ № 354 and № 491 pilots. It binds
the text to the card's `hash`, `nd`, `baseid`, and `rdk`, preserves the
source-declared edition date and label, and keeps verified temporal coverage
explicitly unresolved.
The `build-candidate` handoff serializes one reconciled edition candidate with
allowlisted source evidence and an explicit review gate, without connector transport
fields or inferred legal applicability. `discover-publications` reads the documented
official day feed, archives amendment cards and PDFs, records evidence-backed targets
from the official document, and blocks stale candidates from that handoff.

M1-01 implements a separate diagnostic corpus CLI: validated versioned input
and processing permission, UTF-8 fixture extraction, identity/structure drafts,
full text accounting and an offline HTML report. Repeated compilation returns
`new` then `unchanged`. It preserves source/admission blockers and does not grant
legal approval. See the [implemented contract and replay](docs/milestones/m1/M1_01_FIXTURE_DRAFT.md).

M1-03 adds the full permitted 59-FZ diagnostic JSON/HTML path, with native
source locators, explicit cleanup mappings, legal structure and retained notes.
Two independent full builds match; admission and date coverage remain unresolved.
See the [native-text implementation and replay](docs/milestones/m1/M1_03_NATIVE_TEXT.md).

A separate [Housing Code HTML diagnostic parser](docs/guides/HOUSING_HTML_PARSER.md)
reads raw UTF-8 HTML into a source-bound hierarchy with superscript numbering,
retained notes, exact character locators, explicit unsupported regions and an
inert offline report. It does not admit an edition or change the permission-gated
compiler. Run `python -m legal_rag.corpus.housing_html --input <html> --output-dir <fresh-dir>`
with `PYTHONPATH=src`; use pytest for its synthetic regression suite.

The [parser-independent HTML preparer](docs/guides/HTML_PREPARATION.md) accepts the
permission-bound native JSON inputs before a downstream parser is chosen. It
preserves text, indices, notes, tables, images and references, with original/output
opening-tag maps. Install `requirements-html.txt`, then use
`python -m legal_rag.corpus prepare-html --input <manifest> --target-date <date> --output-dir <dir>`.
All four original HTML inputs now pass full diagnostic parsing through the
[shared legal engine](docs/milestones/m1/03a/M1_03A_SHARED_STRUCTURE.md): 59-FZ, Housing Code,
Government Resolutions No. 354 and No. 491. Approved texts, annexes, source table
topology and image formulas retain their own source-bound structure. Native
transfer qualification and unsupported shapes are recorded separately; these
diagnostics do not admit dated legal editions.

For paired official JSON-tree/HTML inputs, M1-03A now uses
`official-json-import/1`: source rows, types, captions and hierarchy are retained
without semantic reconstruction. Boundary defects stay visible and are never
repaired automatically. The owner-approved contract, 19 retained-input replays
and limits are in the [M1-03A closure](docs/milestones/m1/03a/M1_03A_CLOSURE_2026-10-16.md).

Scanned PDF inputs can use the configurable local dots.mocr adapter:
`python -m legal_rag.corpus extract --input <manifest> --ocr-config <local.json> --output-dir <dir>`.
Native OCR evidence, page/region/cell trees and exact text locators feed
`compile --extraction-index <index.json>`. See [setup and replay](docs/milestones/m1/04/M1_04_PDF_OCR.md).
The [owner-scoped acceptance](docs/milestones/m1/04/M1_04_ACCEPTANCE_2026-10-16.md) covers all
10 PDFs / 103 pages with bounded Picture recovery. Round-seal text accuracy and
the source-bound page-75 table are excluded from OCR quality grading; fresh
inference is versioned and saved replay is deterministic. Inferred legal PDF
hierarchy remains unqualified.
The planned [M1-04A OCR structure parser](docs/plans/2026-10-17-m1-04a-ocr-structure.md)
adds legal hierarchy reconstruction and independent experiments on additional official acts.

```powershell
$env:PYTHONPATH = "src"
python -m legal_rag.corpus compile --input data/m1/inputs/fixture.json --target-date 2025-01-01 --output-dir data/m1
python -m unittest discover -s tests/legal_rag/corpus -p "test_*.py"
```

```powershell
$env:PYTHONPATH = "src"
python -m legal_rag.sources acquire-fixture `
  --fixture tests/legal_rag/sources/fixtures/sample_act.txt `
  --metadata tests/legal_rag/sources/fixtures/sample_act.json `
  --data-dir data/m0-01

python -m legal_rag.sources acquire-publication `
  --eo-number 0001202511280030 `
  --data-dir data/m0-04

python -m legal_rag.sources reconcile-relations `
  --claims tests/legal_rag/sources/fixtures/pp354_publication_relations.json `
  --data-dir data/m0-04

python -m legal_rag.sources acquire-actual `
  --document-hash 4c8dcb690700cdc95a209ca40db2bb177cfc85916d6cfef83439b8696fbf546f `
  --data-dir data/m0-05

python -m legal_rag.sources acquire-legislation `
  --document-hash c0f54c3af0cc8f1b02f48f62483afb358baeb55269d4be8e00e69458ebd3a663 `
  --data-dir data/m0-06

python -m legal_rag.sources build-candidate `
  --reconciliation data/m0-08/reconciliations/<reconciliation-id>.json `
  --data-dir data/m0-08

python -m legal_rag.sources run-pilot `
  --data-dir data/m0-09

python -m legal_rag.sources discover-publications `
  --date 2026-09-26 `
  --data-dir data/m0-09
```

Scanned amendment PDFs require `pdftoppm` and Tesseract with the `rus` language
data on `PATH`. OCR is retained as a derived audit artifact; the relation cites
the immutable official PDF hash and page.

Run its offline acceptance tests with:

```powershell
python -m unittest discover -s tests/legal_rag/sources -p "test_*.py" -v
python docs/assets/generate_m0_gate.py
```

The gate command verifies retained local evidence and the frozen contracts,
regenerates the report and writes `data/m0-12-gate/gate.json`. Exit code `2`
means the M0 gate blocks M1. See [the frozen contracts](docs/milestones/m0/M0_CONTRACTS.md).

## Map

```text
docs/                    Architecture, policy, research, diagrams
src/legal_rag/sources/   Official-source acquisition and provenance
src/legal_rag/corpus/    Editions, provisions, structure, evidence spans
src/legal_rag/retrieval/ Exact lookup and PostgreSQL FTS baseline
tests/                   Automated checks mirroring src/
data/                    Local untracked corpora and fixtures
```

Start with the [documentation index](docs/README.md), then read the nearest `AGENTS.md` before editing a subtree.

