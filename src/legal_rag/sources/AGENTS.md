# Source acquisition module

- M1-05 discovery consumes an explicit `extraction-index/1` via
  `--extraction-index`. `extraction.read_pdf_extraction` validates content IDs,
  exact official-card page coverage and source-bound text locators using only
  the standard library. Missing/invalid artifacts produce retryable discovery
  exceptions; run `corpus extract` separately and replay the day. Keep the legacy
  item summary keys and archive the unmodified `text-extraction/1` under its own
  ID. Relations bind that ID, the PDF hash and physical page. No OCR/compilation
  is invoked or imported by `sources`; old M0 OCR evidence remains readable data.

- `publication_pool.py` is opt-in `publication-pravo-pool/4` for future acquisitions.
  It reuses frozen v1 validators through temporary metadata views:
  accept empty, null or absent `name` with otherwise valid metadata, with a `complexName`
  warning; archive the exact original card and its hash. Reject feed items
  independently, retaining raw response bytes, pagination and indexed reasons.
  `File/Pdf` may return ZIP (observed for December 2011); report the format and
  headers without treating it as PDF or unpacking it. Frozen v1 stays unchanged.
  Whitespace-only names and non-string, non-null values remain invalid.
  PDF requests use a dedicated urllib HTTP handler with Connection: keep-alive:
  the portal stalls mid-response with urllib's forced Connection: close, also
  reproduced by adding that header to curl. Each response is still closed;
  no shared persistent socket or curl dependency is introduced. `_get_pdf`
  retains rate metering, error reports and the frozen same-HTTP-origin redirect
  handler; incomplete Content-Length responses fail without persisting bytes.
  Card/feed transport and frozen v1 remain unchanged.

- `structure_bundle.py` is an opt-in `official-structure-bundle/2` acquisition
  wrapper. It reuses frozen adapters and lifecycle without changing their files
  or `edition-candidate/1`. Both requests use the selected edition; archive the
  exact sidecar as `official_structure`, then an immutable binding record under
  `structure_bundles/`. Invalid sidecars fail before persistence. Existing pilot
  allowlists and source-admission restrictions still apply.
- Bundle v2 stores per-acquisition text/structure transport captures. Never use
  a content-addressed asset's first transport as the sole selector for a later
  edition with identical bytes. Require matching request/response selectors;
  keep v1 bindings readable without rewriting archived metadata.

Scope: official-source connectors, acquisition runs, immutable raw assets, and source relations.

- Connectors are read-only adapters around one external source contract.
- `PublicationPravoConnector` uses the portal's HTTP-only read API. Do not attempt
  HTTPS fallback, silently switch protocols, hard-code IP addresses, or add an
  undocumented endpoint. Follow redirects only within the same HTTP origin.
- M0-10A publication discovery uses the documented `/api/Documents` day window,
  stores every returned entry once under `publication_events/`, and acquires
  Government amendment cards/documents through the existing immutable lifecycle.
  Overlapping windows may add feed observations but must not duplicate or rewrite
  event identity. Broaden act types only with matching stable identity rules.
- A generic amendment title is insufficient evidence. For scanned official PDFs,
  store OCR as a derived extraction and bind `amends` to the archived PDF hash and
  page. An unmatched monitored target remains a deterministic exception.
- A newer evidence-backed amendment marks affected edition candidates `stale`.
  Candidate handoff must refuse that state until a newer consolidated edition is
  acquired and reviewed. Ordinary source resynchronization must preserve the stale
  marker and its evidence instead of reconstructing a falsely current candidate.
- `ActualPravoConnector` supports the ЖК РФ and 59-ФЗ pilots by their approved
  64-character portal hashes.
  Keep its undocumented JSON routes private to the adapter, retain the public UI URL
  in source claims, and record exact request URLs only as transport provenance.
- Archive the `actual` card, redactions response, and consolidated-text response as
  separate immutable assets. Select only one complete official current edition; its
  source-declared date/label is not verified `valid_from` evidence.
- `LegislationRussiaConnector` supports the ПП РФ № 354 and № 491 pilots by their
  approved 64-character public-page hashes. Keep the JSON card and `documenttext` routes
  private to the adapter, retain the public search URL in source claims, and do not
  follow redirects outside the portal's HTTP origin.
- The connector targets the new `ips.pravo.gov.ru` test bank only. Treat the
  legacy `pravo.gov.ru/proxy/ips` bank as a separate source contract; never infer
  matching coverage or add a silent fallback between them.
- Archive the card as `legislation_card` and the selected `documenttext` response as
  `legislation_text`. Bind them by `hash`, `nd`, `baseid`, and `rdk`; record the
  card's edition date/label as source claims without inferring `valid_from/to`.
- TXT, PDF, and office downloads are generated derivative formats and are not
  required primary assets; add one only when a later acceptance check needs it.
- Detect format from content, not filename; retain every fetched response body,
  including publication-card JSON and the document asset, with its own SHA-256.
- Record source URL, acquisition time, adapter version, declared identity/edition,
  rights status, and the exact failed request URL.
- Treat API card fields as source claims, not as proof of legal applicability.
- Validate identity-bearing strings, ISO dates, positive page counts, document
  type, and signatory authorities before requesting or persisting the document.
- Repeated unchanged acquisition must be idempotent across both the document asset
  and publication-card asset; a change to either creates a new asset and diff.
- Validate an existing source item's system, external ID, and declared act identity
  before writing new raw bytes or asset metadata; record conflicts as failed runs.
- Acquisition outcomes are exactly `new`, `unchanged`, `changed`, and `failed`.
  A changed run preserves asset history and records the source item plus old/new
  SHA-256 values without embedding raw content in the run report.
- A failed resynchronization must retain the latest successful asset pointer.
- Every failed acquisition writes a standalone `ExceptionItem` linked from its run;
  the item records UTC creation, source/item, reason, diagnostic, retryability, and URL.
- Persist a source relation only when one known target is supported by an asserting
  source and evidence reference. Missing or ambiguous targets become deterministic
  exception items; never choose a target by title similarity or legal inference.
- Publication-card relation claims use structured fields or an explicit supported
  case-insensitive single-target amendment-title pattern matching the whole trimmed
  title and point to the archived raw JSON asset; never infer legal effect from meaning. An explicit
  amendment title without one supported target emits an unresolved `amends` claim
  with no target candidate.
- Acquired and discovered records share the canonical `items/` lifecycle. An
  unacquired discovered item has `latest_successful_asset: null`; reject identity
  conflicts instead of creating a parallel item namespace.
- Reconciliation loads every `acquired_source_items` record before writing and
  validates the complete combined claim document before persisting anything.
  Its relation evidence hash must belong to that source item's archived assets and
  match the claim's current asset-role pointer, asset metadata, source URL, and
  archived raw bytes; membership in asset history alone is insufficient.
- Never infer legal applicability, reconstruct amendments by meaning, or delete the last approved asset after a source failure.
- Build an M1 handoff only from a persisted reconciliation containing exactly one
  evidence-backed `edition_candidate -> consolidates -> act` path. Serialize the
  shared allowlist under `candidates/`; connector transport fields stay in source
  records and never enter the handoff.
- Candidate claims cite archived asset SHA-256 values and relation IDs. Validate
  archived bytes before writing the candidate and keep unknown temporal coverage
  explicit.
- The M0-09 pilot is exactly five acts and 14 source items: four consolidated
  candidates plus the SanPiN original and nine located amendment publications.
  Run two sequential passes with one shared connector per source so the
  one-request-per-second limit spans adjacent items. Retain per-attempt reports,
  cap retryable failures at three attempts with backoff, and aggregate requests,
  received bytes, elapsed time, retries, failures, raw-asset growth, and coverage
  gaps under `pilot_runs/`.
- A candidate is `unreviewed` unless a separate decision names the `Legal Reviewer`
  role, reviewer, time, rationale, candidate scope, and known asset/relation evidence.
- Verify source terms and rate limits before enabling bulk acquisition.
- M0 acquisition and `edition-candidate/1` are frozen in
  `docs/milestones/m0/M0_CONTRACTS.md` and `docs/milestones/m0/M0_CONTRACT_FREEZE.json`. Preserve the
  byte-for-byte synthetic handoff fixture; version incompatible changes instead
  of silently refreshing its expected output or frozen hashes.

