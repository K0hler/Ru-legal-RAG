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

- The current implementation boundary is the M0-M2 vertical slice in [`docs/overview/LEGAL_RAG_MASTER_PLAN_2026.md`](docs/overview/LEGAL_RAG_MASTER_PLAN_2026.md).
- Treat [`docs/policies/LEGAL_SOURCES_POLICY.md`](docs/policies/LEGAL_SOURCES_POLICY.md) as the source-admission policy.
- Keep implemented behavior, target architecture, research findings, and hypotheses explicitly separate.
- Keep the repository root limited to project-wide entry points and configuration.
- Do not use the `law-housing-utilities-law` skill in this project; rely on this repository's sources and instructions instead.

## Development workflow

- Before starting M1, regenerate the [M0 gate report](docs/milestones/m0/M0_GATE_REPORT.md).
  A failed or unresolved gate blocks the transition; implementation completion
  alone does not waive an acceptance criterion.
- During the current early-development phase, work directly on `main`. Create a
  separate branch or worktree only when the user explicitly requests isolation.
- After each implemented plan item, update the nearest applicable `AGENTS.md` with
  durable module knowledge, run its acceptance checks, and commit the completed item
  before starting the next one.
- Keep project-wide workflow in this file and module-specific facts in the deeper
  `AGENTS.md` files linked above.

