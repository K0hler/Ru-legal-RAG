# Legal RAG

Repository skeleton for the M0-M2 vertical slice: reproducible acquisition of official legal sources, deterministic corpus compilation, and exact/full-text retrieval with verifiable evidence coordinates.

Implementation has not started yet. The current materials are architecture and research documents.

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

