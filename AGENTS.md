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
- M1-04A naming (owner decision 27.10.2026): one number for step, prototype and check — step N freezes prototype
  П<N>, checked on scan batch N. Write owner-facing text with «сканы», «официальные деревья от <дата>», «проверка»,
  «доработка»; never introduce new words for these. Glossary and the old→new name table: section 0 and 3 of
  [`docs/milestones/m1/04a/M1_04A_MAP_2026-10-25.md`](docs/milestones/m1/04a/M1_04A_MAP_2026-10-25.md).
- The numbers never differ (owner 28.10.2026, «ни при каких обстоятельствах»): a step and its prototype take the
  number of the scan batch the prototype will be checked on. When a prototype is checked on several batches in a
  row, the next step takes the next unused batch number and skipped step numbers are never used (old «П14» = П16 =
  step 16, checked on batch 16; the next is step 17 -> П17 -> batch 17; there are no steps 14 and 15). Before naming
  a step or prototype, look up the next batch number. Code comments and AGENTS notes follow the same numbers; only
  folder/file names and `VERSION` labels keep old numbers (`…-step14-c1`, `…-step15-a`, `M1_04A_CYCLE14_…`).

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
- BB tooling lives in `.bb/`: saved workflows in `.bb/workflows/` and project
  skills (slash commands such as `/peer-analysis` and `/run-workflow`) in
  `.bb/skills/`. Workflow workers share the user's checkout. Analysis
  workflows must not write repository files. Writing workflows such as
  `implement-review-fix` leave their edits unstaged, skip files that have
  unstaged changes or are untracked, and leave commits to the user.

