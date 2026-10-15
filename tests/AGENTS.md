# Test instructions

- `corpus/test_official_structure.py` checks the opt-in v2 path, source selectors,
  permission scope, sidecar numbering/ranges, note scope and exactly-once media/
  text accounting. Negative bindings must write no derived files; the original
  v1 replay and frozen M0 gate remain required.
- Official-structure completion controls include quoted whole articles, media
  and inline-note ownership, mixed closing/opening boundaries, omitted top-level
  markers, inline anchors, break-separated units, form sections/continuations,
  numbered table-row cell ownership, malformed JSON and IPS body selectors.

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


- M1-03A adds `corpus/test_structure.py`: authored cross-act identities,
  scalar/raw adapter equivalence, literal hierarchy/number controls, scoped
  `§` nodes, Roman/uppercase headings, hyphenated superscripts, invalid zero
  components, break-boundary refusal, textual notes and region-only blockers.
  Keep the full transfer corpus local, freeze before parsing validation bodies,
  and retain independent DOM controls and failed cohorts. A corrected control
  reader must retain `<br/>` whitespace; do not change production code to agree
  with a reference reader that dropped it. Native transfer never reads gold.

- M1-03A completion requires a full retained-input acceptance run on the
  original four HTML documents, including No. 354 and No. 491 through the
  same compiler. Preparation-only preservation and additional federal-law/code
  tests are supplemental. A missing path or unresolved critical structure
  means stage failure even when the complete default test suite is green.
- `corpus/test_resolution_structure.py` covers source-derived government
  identities, approved/annex/quote scopes, both numeric/letter nesting orders,
  normative notes, numeric-footnote handling/refusal of other markers, table
  topology/ownership, image order and inert raster preview. Test nested ASCII
  and Russian quotation marks, unclosed quotation refusal, duplicate boundaries,
  immutable permission-bound compiler replay and preserved admission blockers.
  An unsupported heading inside a quotation is an exception, never a crash.
