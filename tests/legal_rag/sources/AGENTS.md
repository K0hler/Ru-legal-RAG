# Source acquisition test instructions

- `test_publication_pool.py` uses authored metadata and fake transport only.
  Check empty-name order acquisition/repeat with exact original card hashes,
  unchanged identity validation, per-item feed refusal (including duplicates,
  invalid dates and non-objects), strict envelopes and explicit non-PDF formats.
  Frozen M0 replay fixtures and tests must not change for this opt-in adapter.

- `test_structure_bundle.py` replays both banks with authored sidecars and the
  unchanged frozen fixtures. Check exact bytes, same-edition selectors, repeat
  identity and failed refresh preserving all prior source/bundle state.
- Include changed-edition redirects, duplicate empty selectors and identical
  text/structure bytes across distinct editions. V2 bindings must retain each
  capture; immutable asset metadata keeps its first capture, and v1 still loads.

Scope: connector replay fixtures and acquisition lifecycle tests in this directory.

- Default tests must not use the network; replay saved response metadata through a fake transport.
- Connector failure coverage includes invalid IDs/cards/assets, timeout, retryable
  network/HTTP failure, and non-retryable HTTP failure.
- Keep fixture provenance, capture time, rights note, and expected raw SHA-256 together.
- The `actual` replay is synthetic: preserve the observed response shape and official
  act metadata, but do not embed the portal's full consolidated legal text.
- The `legislation-russia` replay contains synthetic JSON card and `documenttext`
  payloads matching the observed ПП РФ № 354 response shape. Preserve the
  `hash`/`nd`/`baseid`/`rdk` binding checks and do not commit the full live text.
- Verify media type from fixture bytes and archive both raw publication-card JSON and
  the original document asset; failure assertions include the attempted source URL.
- Test the observable run report and persisted provenance, not private parsing helpers.
- Keep one focused lifecycle regression that drives the same source item through
  `new`, `unchanged`, `changed`, and `failed`.
- Relation tests must keep act, publication, and amendment items distinct; verify
  exact evidence locators/raw-asset links, unresolved exceptions, canonical source
  items, and an idempotent readable report.
- Relation tests must also prove malformed evidence writes nothing and discovery does
  not proceed without its required acquired source item.
- Publication-discovery replay must start from the documented day feed, not a supplied
  publication number; cover PDF-page evidence, stale-candidate refusal, unresolved
  targets, and an idempotent overlapping-window replay.
- Live checks must be explicit CLI commands and must write only to ignored `data/` paths.
- `edition_candidate_v1.json` is a project-authored synthetic handoff, reproduced
  byte-for-byte by the existing candidate regression. Gate tests cover fail,
  unresolved, missing/changed evidence and acceptance-list completeness; neither
  test path loads private gold queries or labels.
- A first-attempt transport failure must leave no successful source item or raw asset
  behind; after a prior success, it must retain that successful item and asset pointer.
  In both cases it writes a complete exception item linked from the failed run.
