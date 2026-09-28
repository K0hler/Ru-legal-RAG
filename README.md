# Legal RAG

Repository skeleton for the M0-M2 vertical slice: reproducible acquisition of official legal sources, deterministic corpus compilation, and exact/full-text retrieval with verifiable evidence coordinates.

M0-01 through M0-04 are implemented. The fixture-backed path and the
`PublicationPravoConnector` store immutable raw bytes and provenance, then report
`new`, `unchanged`, `changed`, or `failed` without losing the latest successful
asset. Changed runs record the old and new SHA-256 without copying raw content into
the report. Publication reconciliation stores evidence-backed `publishes` and
`amends` source claims in a separate discovery snapshot namespace; missing or
ambiguous targets remain visible exceptions.
The publication connector uses the portal's documented HTTP read API without a
protocol fallback.

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

