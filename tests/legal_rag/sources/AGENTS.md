# Source acquisition test instructions

Scope: connector replay fixtures and acquisition lifecycle tests in this directory.

- Default tests must not use the network; replay saved response metadata through a fake transport.
- Keep fixture provenance, capture time, rights note, and expected raw SHA-256 together.
- Test the observable run report and persisted provenance, not private parsing helpers.
- Live checks must be explicit CLI commands and must write only to ignored `data/` paths.
- A transport failure must leave no successful source item or raw asset behind.
