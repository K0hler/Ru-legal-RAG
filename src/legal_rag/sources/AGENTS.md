# Source acquisition module

Scope: official-source connectors, acquisition runs, immutable raw assets, and source relations.

- Connectors are read-only adapters around one external source contract.
- `PublicationPravoConnector` uses the portal's HTTP-only read API. Do not attempt
  HTTPS fallback, silently switch protocols, hard-code IP addresses, or add an
  undocumented endpoint.
- Detect format from content, not filename; retain every fetched response body,
  including publication-card JSON and the document asset, with its own SHA-256.
- Record source URL, acquisition time, adapter version, declared identity/edition,
  rights status, and the exact failed request URL.
- Treat API card fields as source claims, not as proof of legal applicability.
- Repeated unchanged acquisition must be idempotent; changed content creates a new asset and diff.
- Acquisition outcomes are exactly `new`, `unchanged`, `changed`, and `failed`.
  A changed run preserves asset history and records the source item plus old/new
  SHA-256 values without embedding raw content in the run report.
- A failed resynchronization must retain the latest successful asset pointer.
- Every failed acquisition writes a standalone `ExceptionItem` linked from its run;
  the item records UTC creation, source/item, reason, diagnostic, retryability, and URL.
- Persist a source relation only when one known target is supported by an asserting
  source and evidence reference. Missing or ambiguous targets become deterministic
  exception items; never choose a target by title similarity or legal inference.
- Keep relation-discovery snapshots in `relation-items/`; only successful acquisition
  may write `items/`. Validate the complete claim document before persisting anything.
- Never infer legal applicability, reconstruct amendments by meaning, or delete the last approved asset after a source failure.
- Verify source terms and rate limits before enabling bulk acquisition.

