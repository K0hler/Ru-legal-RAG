# Source acquisition module

Scope: official-source connectors, acquisition runs, immutable raw assets, and source relations.

- Connectors are read-only adapters around one external source contract.
- `PublicationPravoConnector` uses the portal's documented HTTP read API. Do not
  silently switch protocols, hard-code IP addresses, or add an undocumented endpoint.
- Detect format from content, not filename; retain the original bytes and SHA-256.
- Record source URL, acquisition time, adapter version, declared identity/edition, rights status, and failures.
- Treat API card fields as source claims, not as proof of legal applicability.
- Repeated unchanged acquisition must be idempotent; changed content creates a new asset and diff.
- Acquisition outcomes are exactly `new`, `unchanged`, `changed`, and `failed`.
  A changed run preserves asset history and records the source item plus old/new
  SHA-256 values without embedding raw content in the run report.
- A failed resynchronization must retain the latest successful asset pointer.
- Never infer legal applicability, reconstruct amendments by meaning, or delete the last approved asset after a source failure.
- Verify source terms and rate limits before enabling bulk acquisition.

