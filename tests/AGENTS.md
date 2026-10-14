# Test instructions

Scope: automated tests and checked fixtures.

- Mirror the `src/legal_rag/` module layout.
- Prefer one focused regression test for each branch, parser rule, or bug.
- Test idempotent acquisition, full text accounting, deterministic IDs/hashes, temporal refusal, and exact evidence coordinates.
- Corrupt, remove, and mispoint archived evidence in negative tests; reconciliation
  must reject it before writing derived records.
- Keep working examples separate from the closed gate set; do not use closed labels for tuning.
- Never require live network access in the default test run. Record live-source checks as explicit integration tests.
- M1-01 corpus tests are in `legal_rag/corpus/test_input_and_compile.py`. Use
  the existing acquisition lifecycle for synthetic archives and the frozen
  source test fixture for read-only wrapper checks; never load private gold.
  Fixture text and permission bytes are hash-pinned and exempt from Git newline
  conversion. Keep raw/approved-state snapshots in negative tests, and verify
  full text/byte accounting through the observable CLI artifacts.
- M1-02 inventory checks are in `legal_rag/corpus/test_input_inventory.py` and
  exercise the documentation generator against project-authored synthetic
  archives. Verify ten distinct blocked rows, separate unsigned permissions,
  corrupt/mispointed evidence, publication card versus PDF URLs and immutable
  replay protecting human records. Do not load private gold or require a network.
- `docs/assets/check_m1_02_review_v2.js` is an explicit local browser regression
  check for the owner packet. It disables network after page load, exercises all
  embedded documents/PDF navigation and report gates, and resets its synthetic
  answer in an isolated session. It is not human legal approval or a default
  network-dependent unit test.
- M1-02 closure checks are in `legal_rag/corpus/test_m1_02_closure.py`. Use only
  project-authored temporary evidence/review fixtures. Verify read-only repeat,
  corruption, path escape, duplicate/date rows, exact permission asset scope and
  reviewer-role refusal; synthetic confirmation never approves real editions.
- M1-03 native checks are in `legal_rag/corpus/test_native_text.py`. Use the
  project-authored HTML and literal expected address order; verify entity and
  whitespace maps, original scalar locators, one-time token accounting, unknown
  context/duplicate/identity refusal, retained notes and split superscripts.
  Full retained 59-FZ verification stays local under `data/m1/pilot_runs/m1-03/`;
  it must not read closed questions or imply dated legal approval.

- `legal_rag/corpus/test_html_preparation.py` tests the optional BS4/tinycss2
  preparer with authored HTML and the existing synthetic permission archive.
  Verify original/prepared opening anchors, exact text/order, indices, notes,
  tables/images/links, unsupported CSS preservation and immutable CLI replay.
  Include legacy CSS comments, media-rule isolation and adjacent whitespace;
  all three are observed native-HTML failure modes. Full retained-input controls
  stay local and are preservation checks, not legal-structure or G13 evidence.
  Reject body/content parsed under `head` before writing, and check `!important`
  priority across simple class and inline declarations to avoid false indices.

