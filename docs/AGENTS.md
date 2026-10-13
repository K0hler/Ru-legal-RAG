# Documentation instructions

Scope: every file under `docs/`.

- Keep confirmed implementation, target architecture, external research, and hypotheses visibly distinct.
- Preserve source links, dates, edition scope, and evidence for time-sensitive legal or technical claims.
- Update `docs/README.md` when adding, renaming, or moving a document.
- Keep deterministic diagram sources beside rendered assets when both exist.
- Do not present a planned component as deployed without current code or runtime evidence.
- PRD v0.2 assigns edition reconstruction to M1. Processing permission is
  separate from legal admission; rejected/stale inputs may produce diagnostic
  drafts without changing M0-10 decisions or bypassing the frozen handoff.
  The original-plus-amendments input needs its own versioned contract. SanPiN
  reconstruction requires a chosen date, a verified amendment bundle, reviewed
  operations, official evidence and an explicit Legal Reviewer decision.
- M1 covers all five pilot acts in full at 2026-10-01 and 2025-01-01: ten
  act/date checks, with legal admission for each. Exclude changes effective
  after the historical target, including ones published earlier. A later
  snapshot needs evidence-backed reconstruction before historical admission;
  the owner's choice of dates is not legal approval or complete history.
- Follow `M1_IMPLEMENTATION_PLAN.md` for the current 16-slice decomposition
  (M1-01–M1-15 plus M1-03A) and 13 milestone gates. The owner approved the
  parser-transfer requirement on 13.10.2026. M1-03A is the next slice: shared
  structure with act-type profiles, not another parser bound to one act.
  M1-01's fixture-only contracts/compile CLI are implemented and documented in
  `M1_01_FIXTURE_DRAFT.md`; later schemas/commands and Docling/RapidOCR remain
  target decisions. Qualify the pinned runtime/models before PDF rollout;
  discovery consumes shared extraction artifacts without importing heavy OCR.
  Keep M1's ten legal checks and closed-gold isolation separate from engineering
  completion. Compatible frozen-source changes need a reviewed update and replay,
  not a hash refresh that hides drift.
- Separate source-format adapters from the shared legal structure engine.
  Production profiles must not select/permit acts by hard-coded number, date,
  title, filename or source hash. Extract identity and compare the evidence-bound
  input claim; keep conflicts and unsupported structure unresolved.
  G13 requires two distinct non-pilot acts per supported family/source-format
  combination, not development examples, different editions or renamed fixtures.
  Pin final parser/profile versions, check independent structural controls and
  repeated full-document runs, and retain failures before changing rules.
  These permitted diagnostic documents do not enlarge the ten edition admissions
  or authorize reading closed retrieval gold. Missing/failed transfer evidence
  blocks M1/M2; M1-03A, M1-06 and M1-09 own the profile checks.
- Distinguish the legacy and new test versions of the integrated bank; do not
  infer shared document coverage. Treat commercial consolidated texts as
  discovery evidence unless the source-admission policy explicitly grants a
  stronger role.
- M0-10 keeps human comparison separate from corpus admission: critical
  amendment, temporal, consolidated-edition, or case-law-relation gaps remain
  fail-closed even when the reviewer reports the supplied document as “OK”.
- M0-10A treats the official day feed as discovery, not legal applicability.
  OCR is derived evidence; `amends` remains a source claim tied to the official
  PDF hash/page, and a stale candidate stays blocked until acquisition plus review.
- Before contradicting a reviewer on a time-sensitive control page, inspect its
  cache metadata and verify the current response against the primary official
  publication; a cached commercial page is not live-edition evidence.
- M0-11 keeps questions, labels, evidence and the complete review record under
  ignored local data; only IDs, split membership and content/review hashes are
  tracked. A hash check alone is not legal review; a completed `review.json`
  with reviewer, time, rationales and storage decision unblocks M0-12.
- M0-12's `assets/generate_m0_gate.py` renders all plan criteria from the tracked
  assessment and checks pinned evidence/code/fixture hashes. Exit 2 blocks M1;
  M0-10 timing uses `not_recorded` placeholders, explicitly accepted by the
  product owner on 01.10.2026. Count that measurement criterion as completed
  without repeat review; never present the placeholders as measured timestamps.
  Closed gold files are read as bytes for hashing only. The contract freeze
  records existing unversioned acquisition formats without inventing embedded
  schema versions; incompatible handoff changes require a new version.
- M1-02's `assets/generate_m1_inventory.py` prepares the ten act/date rows from
  retained source metadata and validated raw hashes without extracting legal text
  or changing frozen adapters. Search observations and the full review packet
  remain local. Pending permission templates have no signature/time and cannot
  authorize extraction. Known-ID replay, advertised history and empty search
  results do not prove completeness or historical applicability. Preserve the
  rejected M0 candidates and the 59-FZ case-law-sensitive blocker; M1-02 acceptance
  requires separate human inventory/permission decisions. Repeats are immutable
  and must not overwrite a human record; use a new output directory for new evidence.
- On 02.10.2026 the owner explicitly consented to all five diagnostic processing
  requests and inventory acceptance with disclosed gaps. Record this in the
  separate `data/m1/reviews/m1-02-owner-consent/decision.json`; retain the original
  pending packet. Respect that consent for the approved scope without asking
  again. The permitted 59-FZ input is ready for M1-03's control-date diagnostic
  path only; historical coverage and all substantive legal admission remain
  unresolved. Timestamp the recording honestly, not an invented chat-message time.
- M1-02's owner-facing packet is built by `assets/build_m1_02_review.py` under
  `data/m1/reviews/m1-02-review-v1/`. The owner remains the assigned Legal Reviewer;
  present readable Russian questions, official documents, exact page/provision
  references and a response form. Its source-review scope excludes final edition
  admission. Bounded historical research assets do not extend production adapters
  or waive frozen M0 checks. Preserve returned findings separately against the
  packet hash; draft autosave and technical QA are not human decisions. Never infer
  completed review time from an export timestamp or elapsed browser session.
- Use `assets/build_m1_02_review_v2.py` for the latest M1-02 reviewer packet.
  It embeds all evidence in one HTML file; document buttons open an in-page reader
  without network/new tabs/PDF plugins. Preserve v1 and any returned answers.
  The owner requested minimum reviewer work: engineers perform factual checks and
  prepare evidence; request only the remaining specific legal classification,
  with short excerpts and a proposed rationale that explicit agreement may accept.
  Missing evidence stays engineering work and remains blocked. This does not
  waive final review of all ten complete editions. Verify actual offline document
  opening with `assets/check_m1_02_review_v2.js`, not just file/link existence.
- On 12.10.2026 `legal-reviewer-owner` confirmed v2's specific 19-P-after-80-FZ
  classification for both targets. The actual response and hash/scope receipt are
  separate `human-review.json` / `human-review-verification.json` files under
  `data/m1/reviews/m1-02-review-v2/`; preserve the supplied recording timestamp,
  rationale and original packets. This question is resolved for the bound scope
  without repeat confirmation. Engineering completeness/applicability and all ten
  final admissions remain open; recording the decision imports no runtime relation
  and does not rewrite historical source/candidate blockers.
- M1-02 closes the input-route inventory with declared admission blockers, not
  M1's full-text or ten-edition legal-review work. The 12 October result is in
  `M1_02_CLOSURE.md` and `data/m1/inputs/m1-02-completion/closure.json`;
  validate it read-only with `assets/validate_m1_02_closure.py`. It retains 27 new
  official publications, a fresh two-pass pilot and independent historical
  candidates. The new bank now includes No. 1242 in No. 491; preserve the old
  stale/rejected archive. No. 354's general text and No. 1979/931 application
  conditions stay distinct. No. 2's SanPiN targets are 282, 283, 286; 272 is a
  reference in the other sanitary rules. Bounded feed inspection preserves three
  strict validation failures and never proves all historical amendments absent.
- M1-03's implemented profile and full native 59-FZ replay are documented in
  `M1_03_NATIVE_TEXT.md`. Report engineering accounting and determinism separately
  from legal admission. Keep JSON-scalar character locations distinct from raw
  bytes/PDF pages. Preserve earlier manifests and their historical questions;
  expose the original excerpt for every provision in the offline report.

