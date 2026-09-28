# Legal RAG

Repository skeleton for the M0-M2 vertical slice: reproducible acquisition of official legal sources, deterministic corpus compilation, and exact/full-text retrieval with verifiable evidence coordinates.

M0-01 through M0-06 are implemented. The fixture-backed path and the
`PublicationPravoConnector` store immutable raw bytes and provenance, then report
`new`, `unchanged`, `changed`, or `failed` without losing the latest successful
asset. Changed runs record the old and new SHA-256 without copying raw content into
the report. Publication reconciliation stores acquired and discovered records in
the canonical `items/` lifecycle and writes evidence-backed `publishes` and
`amends` source claims; missing or ambiguous targets remain visible exceptions.
The publication connector uses the portal's documented HTTP read API without a
protocol fallback.
`ActualPravoConnector` archives the portal card, declared-editions response, and
consolidated-text response separately for the 59-ФЗ pilot. It links the candidate
to the declared act while keeping the source edition date separate from unknown
verified temporal coverage.
`LegislationRussiaConnector` archives the official Windows-1251 HTML candidate for
ПП РФ № 354 and links it to the same declared act identity used by publication
relations. The portal response does not provide a distinct verified edition date,
so edition metadata and temporal coverage remain explicitly unresolved.

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
  --document-id 102147807 `
  --data-dir data/m0-06
```

Run its offline acceptance tests with:

```powershell
python -m unittest discover -s tests/legal_rag/sources -p "test_*.py" -v
```

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

