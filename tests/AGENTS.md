# Test instructions

Scope: automated tests and checked fixtures.

- Mirror the `src/legal_rag/` module layout.
- Prefer one focused regression test for each branch, parser rule, or bug.
- Test idempotent acquisition, full text accounting, deterministic IDs/hashes, temporal refusal, and exact evidence coordinates.
- Corrupt, remove, and mispoint archived evidence in negative tests; reconciliation
  must reject it before writing derived records.
- Keep working examples separate from the closed gate set; do not use closed labels for tuning.
- Never require live network access in the default test run. Record live-source checks as explicit integration tests.
- M0-11 gold regression uses project-authored synthetic questions only. Run it
  with `python -m unittest discover -s tests/legal_rag/corpus -p 'test_*.py' -v`.
  Verify pending-review refusal, evidence corruption/path escape, split leakage,
  hash-bound decisions, independent second review and immutable freeze replay.

