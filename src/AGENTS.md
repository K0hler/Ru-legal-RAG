# Source code instructions

Scope: production code under `src/`.

- Use Python and keep the first implementation a modular monolith.
- Dependency direction is `sources -> corpus -> retrieval`; do not import in the opposite direction.
- Reuse standard-library or already-installed functionality before adding a dependency.
- Keep domain decisions explicit and deterministic; external I/O belongs at module boundaries.
- Every non-trivial branch, parser rule, or data transformation needs the smallest runnable test under `tests/`.
- Do not add agent orchestration, UI, vector search, reranking, or court-practice modules before their measured milestone requires them.

