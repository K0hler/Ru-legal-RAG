# Source acquisition test instructions

Scope: connector replay fixtures and acquisition lifecycle tests in this directory.

- Default tests must not use the network; replay saved response metadata through a fake transport.
- Keep fixture provenance, capture time, rights note, and expected raw SHA-256 together.
- Test the observable run report and persisted provenance, not private parsing helpers.
- Keep one focused lifecycle regression that drives the same source item through
  `new`, `unchanged`, `changed`, and `failed`.
- Live checks must be explicit CLI commands and must write only to ignored `data/` paths.
- A first-attempt transport failure must leave no successful source item or raw asset
  behind; after a prior success, it must retain that successful item and asset pointer.
