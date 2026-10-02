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
- Follow `M1_IMPLEMENTATION_PLAN.md` for the current 15-slice decomposition.
  M1-01's fixture-only contracts/compile CLI are implemented and documented in
  `M1_01_FIXTURE_DRAFT.md`; later schemas/commands and Docling/RapidOCR remain
  target decisions. Qualify the pinned runtime/models before PDF rollout;
  discovery consumes shared extraction artifacts without importing heavy OCR.
  Keep M1's ten legal checks and closed-gold isolation separate from engineering
  completion. Compatible frozen-source changes need a reviewed update and replay,
  not a hash refresh that hides drift.
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

