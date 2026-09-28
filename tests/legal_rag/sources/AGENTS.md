# Source acquisition test instructions

Scope: connector replay fixtures and acquisition lifecycle tests in this directory.

- Default tests must not use the network; replay saved response metadata through a fake transport.
- Connector failure coverage includes invalid IDs/cards/assets, timeout, retryable
  network/HTTP failure, and non-retryable HTTP failure.
- Keep fixture provenance, capture time, rights note, and expected raw SHA-256 together.
- The `actual` replay is synthetic: preserve the observed response shape and official
  act metadata, but do not embed the portal's full consolidated legal text.
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
- Live checks must be explicit CLI commands and must write only to ignored `data/` paths.
- A first-attempt transport failure must leave no successful source item or raw asset
  behind; after a prior success, it must retain that successful item and asset pointer.
  In both cases it writes a complete exception item linked from the failed run.
