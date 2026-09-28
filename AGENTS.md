# Legal RAG agent map

Read the nearest `AGENTS.md` before changing files. A deeper file overrides this one for its subtree.

## Project map

- [`docs/AGENTS.md`](docs/AGENTS.md) — architecture, policy, research, and generated diagrams.
- [`src/AGENTS.md`](src/AGENTS.md) — shared rules for production Python code.
  - [`src/legal_rag/sources/AGENTS.md`](src/legal_rag/sources/AGENTS.md) — official-source acquisition and provenance.
  - [`src/legal_rag/corpus/AGENTS.md`](src/legal_rag/corpus/AGENTS.md) — canonical legal model and corpus compilation.
  - [`src/legal_rag/retrieval/AGENTS.md`](src/legal_rag/retrieval/AGENTS.md) — exact and full-text retrieval.
- [`tests/AGENTS.md`](tests/AGENTS.md) — test placement and acceptance checks.
- [`data/AGENTS.md`](data/AGENTS.md) — local corpus and fixture handling.

## Project-wide direction

- The current implementation boundary is the M0-M2 vertical slice in [`docs/LEGAL_RAG_MASTER_PLAN_2026.md`](docs/LEGAL_RAG_MASTER_PLAN_2026.md).
- Treat [`docs/LEGAL_SOURCES_POLICY.md`](docs/LEGAL_SOURCES_POLICY.md) as the source-admission policy.
- Keep implemented behavior, target architecture, research findings, and hypotheses explicitly separate.
- Keep the repository root limited to project-wide entry points and configuration.

## Development workflow

- During the current early-development phase, work directly on `main`. Create a
  separate branch or worktree only when the user explicitly requests isolation.
- After each implemented plan item, update the nearest applicable `AGENTS.md` with
  durable module knowledge, run its acceptance checks, and commit the completed item
  before starting the next one.
- Keep project-wide workflow in this file and module-specific facts in the deeper
  `AGENTS.md` files linked above.

