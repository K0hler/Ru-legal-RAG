# M1-02: ten input routes and human review request

**Prepared:** 2 October 2026.
**Status:** M1-02 completed as the ten-route inventory with accepted unresolved
edition rows on 12 October 2026. See the [closure evidence and current matrix](M1_02_CLOSURE.md).
The owner authorized all five diagnostic acts and accepted inventory gaps on
2 October; the focused 19-P-after-80-FZ qualification was confirmed on 12 October.
Full text/operation/applicability work remains in M1-03–M1-13. No dated edition is
legally admitted. The sections below retain the earlier packets and requests.

## Received human decision

The assigned `legal-reviewer-owner` returned the [human decision](../../../data/m1/reviews/m1-02-review-v2/human-review.json)
with `decision: confirmed` for `59-ks19p-after-80`, covering 2025-01-01 and
2026-10-01. The supplied recording time is `2026-10-12T10:08:31.056Z`; no review
duration is inferred. The complete rationale and four engineering open items
are retained verbatim.

The confirmed qualification uses 59-FZ Article 1 part 4 and Article 2 part 1 as
amended by 80-FZ for the expanded applicants and addressees on both targets.
Retain a separate link to Constitutional Court No. 19-P: regional guarantees
may supplement federal guarantees without creating new obligations or
restrictions on individuals' or legal entities' rights. The court annotation is
an addressed interpretation and source relation; it does not by itself establish
that the entire consolidated 59-FZ text is wrong.

The [verification receipt](../../../data/m1/reviews/m1-02-review-v2/human-review-verification.json)
binds the actual human response to v2 packet hash
`78999703f930d605078090726c984da3006010887ba25e7490f7daf5c852d0c1`,
the retained v1 packet hash and the original inventory content hash. The role,
question, rationale, targets and scope match; all 30 raw evidence assets and
readable views match their packet hashes. The original inventory, source records
and both review packets remain unchanged.

This specific human-classification request is resolved; do not request it again
for the same evidence and scope. No runtime case-law relation has been imported
and no edition has been admitted (`edition_admission: false`). Historical M0
candidate blockers are preserved as originally recorded. Engineering must still:

- Prove amendment-chain completeness and applicability of all four historical
  candidates; a later consolidated text cannot replace the 2025-01-01 input.
- Complete the No. 491 chain after 2025-09-01, establish the general No. 354
  edition and check No. 931's special-regime conditions at the control target.
- Verify the nine discovered SanPiN amendments, their exact operations and
  special commencement rules; Decree No. 763 calculations remain proposals
  until the special rules are checked.
- Prepare full diagnostic/reconstructed texts. Final admission of all five acts
  at both dates remains a separate review of completed results.

## Focused owner review packet v2

**Revised:** 12 October 2026. The owner reported that document links in the open
HTML did not work and requested minimal reviewer effort. The live preview's
localhost server had stopped; the cached v1 HTML still appeared but its relative
document URLs could not load. Filesystem-link checks had not covered this failure.

The [v2 standalone HTML](../../../data/m1/reviews/m1-02-review-v2/index.html) embeds all
30 evidence documents. Text views open inside the page; all pages of all 15 PDFs
are available as rendered images, with the original PDFs also embedded. No
document preview needs a server, network access, new tab or PDF plugin. While the
preview server runs, the retained v1 document/page/raw URLs are still available.
The original v1 packet and its browser-local answers are preserved.

The packet requested **one required decision**, replacing the previous 22 replies:
classify the remaining effect of Constitutional Court No. 19-P after the changes
introduced by 80-FZ. The packet supplies the proposed conclusion, three short
source excerpts and buttons opening the precise source paragraphs/pages. It
explains that human legal classification is required by the accepted project
review policy, not by a separate statutory permission to read or compare laws.
Agreement actively accepts the displayed proposal as rationale; corrections or
insufficient evidence require a comment. No decision is preselected.

Engineering owns hash/identity checks, historical selector verification,
comparison of the affected 59-FZ paragraphs, directly stated commencement dates,
source discovery and missing amendment/date evidence. The builder confirms that
59-FZ Article 1 part 4 and Article 2 part 1 match character-for-character in the
retained historical and control views. These factual findings are distinct from
whole-edition applicability and admission. The already accepted 48-FZ
special-application classification is not presented as a new permission request.

Missing chains, historical applicability, SanPiN operations/special dates and
full reconstructed output remain explicit engineering work. Reducing repeated
review fields does not waive the ten act/date checks, source completeness or the
final human admission in M1-13. A v2 response cannot approve an unfinished edition
or clear unrelated blockers. Its hash binds the scope, source hashes, excerpts,
embedded document content and proposed interpretation.

Rebuild with `python docs/assets/build_m1_02_review_v2.py`. Regression check:
load the page in an isolated Playwright CLI session, then run
`playwright-cli run-code --filename docs/assets/check_m1_02_review_v2.js`.
This check disables the browser network, opens all 30 documents, inspects every
PDF's first/last image, verifies rendered HTML and report refusal/scope, and
restores an unanswered form. Technical QA creates no human legal-review record.

## Previous owner-facing review packet v1 (retained)

The owner reconfirmed that they will perform the already assigned
`legal-reviewer-owner` role and return their own findings. On 2 October 2026 a
Russian-language [local review packet](../../../data/m1/reviews/m1-02-review-v1/index.html)
was prepared with 30 evidence documents, 13 questions and nine separate SanPiN
amendment rows. Its [offline ZIP](../../../data/m1/reviews/m1-02-review-v1/M1-02-review-package.zip)
includes the PDFs, readable text views, raw responses and acquisition records.
A [plain response template](../../../data/m1/reviews/m1-02-review-v1/Форма-ответа.md)
is available when the browser form is inconvenient.

The form has empty decisions, per-question rationale fields, browser-local draft
storage, report text for copying into this chat, optional JSON/TXT downloads and
JSON answer restoration. A completed source-review report requires all 22
decisions and rationales; an insufficient-evidence decision preserves the blocker.
The exported scope explicitly excludes final `LegalEdition` admission. Review
start time is recorded only when the reviewer clicks Start; an export timestamp
is not fabricated review duration.

New bounded evidence preparation obtained four historical text candidates from
the edition identifiers already present in the official retained selectors:
Housing Code 01.09.2024, No. 354 01.09.2024, No. 491 14.09.2024 and 59-FZ
01.09.2023. Each historical response repeated with identical bytes. These are
separate human-review research assets; production historical adapters, M0
contracts, source pointers and the original M1-02 inventory were not changed.
The candidate labels alone do not establish applicability on 01.01.2025.

New official publication acquisitions of 48-FZ, 80-FZ, 547-FZ and No. 931 each
returned `new` then `unchanged`. The packet also contains the official-bank
consolidated 48-FZ, the legacy-bank text of Decree No. 763 and the official
publication of Constitutional Court No. 19-P in Rossiyskaya Gazeta. The direct
Court-site requests failed certificate validation; validation was not bypassed.
Publication-feed validation/search gaps are retained in the research records.

The SanPiN table proposes each amendment's date basis, dispositions for both
targets, affected provisions and conditions, with PDF page links and expandable
original page images. No. 11's PDF page 3 explicitly states commencement on
31.12.2024. Dates calculated under Decree No. 763 remain proposals requiring
review of special rules. Temporary OCR assisted inspection of these scans only;
it is not an implemented production extraction path or M1-04 qualification.

Rebuild from the retained local evidence with
`python docs/assets/build_m1_02_review.py`. The builder validates raw hashes and
all question/document/page references. Returned human decisions must be retained
separately and checked against `packet.json`'s content hash; never infer approval
from preparing the packet or a technical form test. Changed evidence requires a
new review packet and an explicit human disposition.

## Retained engineering result

The M0 gate was regenerated: `pass`, 78/78 criteria, no evidence problems.
The existing source lifecycle acquired the fourteen pilot documents in a new
local archive, then returned fourteen `unchanged` results. The separate
acquisition of Resolution No. 1242 returned `new`, then `unchanged`. There are
15 source items and 32 immutable raw assets under `data/m1-02-sources/`.
The pilot's 60 requests received 21,306,568 bytes in 101.055 seconds, with no
retries or failures; the No. 1242 replay is recorded separately.

The new [inventory generator](../../assets/generate_m1_inventory.py) reads source
metadata and validates every retained raw asset's length, SHA-256, archive path,
source membership and evidence URL. It does not extract legal text, change M0
source contracts, select historical text or create a legal admission.
It writes a ten-row local inventory, a review packet and five **pending**
`processing-permission/1` templates. A repeat returns `unchanged`; a conflicting
existing inventory or human record is never overwritten. Absolute archive paths
do not enter the inventory content hash.

Local artifacts:

- [Ten-row inventory](../../../data/m1/inputs/m1-02/inventory.json), content hash
  `dd1a34e60aaeac8e0d5134421cf338c1854a12414678317465d358f7f3df7dfc`.
- [Human review request](../../../data/m1/inputs/m1-02/review.md), with official URLs,
  document hashes, source-declared edition history and exact decisions requested.
- [Search observations](../../../data/m1/inputs/m1-02-search.json), retaining failed
  official-domain searches, successful known-ID acquisitions, discovery-only
  commercial leads, the prior official amendment-chain check and remaining gaps.
- [Pilot result pointer](../../../data/m1-02-live-pilot.json) and
  [No. 1242 replay](../../../data/m1-02-pp491-replay.json).
- Pending permission files are beside the inventory under `permissions/`.
  Their signer and timestamp are null; `pending` cannot pass M1-01's permission
  validation. No user or Legal Reviewer signature is inferred from implementation
  authorization or the historical M0 review.
- [Owner consent](../../../data/m1/reviews/m1-02-owner-consent/decision.json) records
  the explicit chat message “Я даю согласие на все”, its explained scope, exact
  inventory content/file hashes, ten row dispositions and five separately
  authorized permission records. The record uses `legal-reviewer-owner`, the
  previously accepted owner/reviewer identifier. Its UTC timestamp is the time
  the decision was recorded; the exact chat-message time was not supplied.
- Allowed permissions are under `data/m1/reviews/m1-02-owner-consent/permissions/`.
  Identical hash-checked copies under `data/m1-02-sources/reviews/m1-02-owner-consent/`
  allow the compiler to resolve them within its declared archive root.
  The original pending packet remains immutable historical evidence.
- [Permitted 59-FZ input](../../../data/m1/inputs/m1-02-permitted/federal-law-59-2026-10-01.json)
  passes M1-01's `load_input` validation for a diagnostic snapshot at the control
  target only. The JSON/HTML extraction profile remains pending M1-03. The later
  text cannot be passed as a `2025-01-01` input; that request is refused.
- [Consent verification](../../../data/m1/reviews/m1-02-owner-consent/verification.json)
  confirms the raw hashes, unchanged source/archive records and original packet,
  allowed permission, retained legal blockers and refusal of the historical target.

## Ten checks

This table describes the immutable initial inventory. The later owner-facing
packet above adds unreviewed historical candidates; it does not rewrite those
original rows or resolve their legal blockers.

These are proposed source routes with explicit blockers, not admitted inputs.
`selected_date_basis` is null for all ten rows. Every row retains its original
[M0-10 decision](../m0/M0_10_LEGAL_REVIEW.md), reviewer `legal-reviewer-owner`, unverified
amendment completeness and unverified date/territory evidence. The separate owner
decision clears the processing-permission and inventory-acceptance requests;
the immutable original inventory still describes their earlier pending state.

| Act | 2025-01-01 | 2026-10-01 |
|---|---|---|
| Housing Code | Unresolved historical route. Official metadata advertises 01.09.2024 and earlier editions, but their texts were not acquired or justified. | Official consolidated-text diagnostic lead, source label 01.09.2026. Amendment chain and future-effective provisions require review. |
| No. 354 | Unresolved historical route; the later snapshot is not reused as historical text. | Retained official snapshot remains rejected as a date basis. Separate general text revision, No. 931's territorial overlay, approving act, Rules and annexes. |
| No. 491 | Unresolved historical route; the 01.09.2025 snapshot is later than the target. | Retained 01.09.2025 snapshot plus separately acquired No. 1242 are diagnostic evidence. A suitable full base, complete amendments and commencement evidence remain unresolved. |
| 59-FZ | Unresolved historical route. Official metadata advertises 01.09.2023, but its text was not acquired or justified. | Official consolidated-text diagnostic lead, source label 30.03.2025. Amendment/date evidence and the No. 48-FZ / Constitutional Court No. 19-P effects remain unresolved. |
| SanPiN 2.1.3684-21 | Reconstruction from the original and reviewed amendments. The 2024 publication is not assumed effective by this date. | Reconstruction from the original and reviewed amendments. The September 2026 publication is not assumed effective by this date. |

## SanPiN completeness and temporal questions

All nine located amendment publications were acquired again with their cards
and PDFs. The [earlier official-source inspection](../../research/SANPIN_2_1_3684_21_SOURCE_COVERAGE.md)
recorded that No. 25 recites the preceding eight amendments. This is corroboration
of the located chain, not proof that the list is closed. The search observations
record no established new required SanPiN document; omissions remain unverified.
Empty search results and a known-ID replay cannot establish complete history.

The reviewer must compare the official PDFs and resolve each operation for
each date, including:

- No. 11 of 15.11.2024, [published 27.12.2024](http://publication.pravo.gov.ru/document/0001202412270033):
  verify commencement before changing the historical wording on 01.01.2025.
- No. 25 of 10.09.2026, [published 24.09.2026](http://publication.pravo.gov.ru/document/0001202609240014):
  verify its commencement rule and the supporting general legal rule before
  including or excluding it on 01.10.2026.
- The original's full approving text, sanitary rules, nine appendices and tables;
  each earlier amendment's affected provisions, dates, dependencies and scope.

## Owner consent and remaining legal checks

The owner explicitly consented after the diagnostic scope and 59-FZ issue were
explained. The separate decision binds the inventory hash, role, recording time,
rationale and all ten row dispositions. The inventory is accepted with unresolved
routes; those rows stay blocked in later legal reports and the final gate.
Inventory acceptance does not establish amendment completeness or applicability.

Diagnostic processing permission is now explicitly allowed for the exact listed
raw assets of all five acts. The prior bounded-pilot source policy and this chat
consent are its recorded basis. No further consent is needed for the same approved
diagnostic scope. Bulk-service access terms remain unresolved.

The decision retains the 59-FZ legal-admission blocker pending concrete evidence
and review of
[No. 48-FZ special application](http://ips.pravo.gov.ru/search/e1a7d76abfd409ca7d2cc0188226889cc76f796f651d171d42ece8014910f008)
and [Constitutional Court No. 19-P of 18.07.2012](https://rg.ru/documents/2012/08/03/ks1807-dok.html)
are distinct effects. Their raw evidence is not retained by this slice.
Permission to diagnose 59-FZ does not resolve them. The later legislative
implementation must also be checked before proposing the remaining effect for
review. No court subsystem, reduced act scope or change to the earlier admission
decision is implemented.

## Reproduction and acceptance

```powershell
$env:PYTHONPATH = "src"
python docs/assets/generate_m1_inventory.py --search-record data/m1/inputs/m1-02-search.json
python -m unittest discover -s tests/legal_rag/corpus -p "test_*.py"
python -m unittest discover -s tests/legal_rag/sources -p "test_*.py"
python docs/assets/generate_m0_gate.py
```

The search record and source archive are required local evidence, not a generic
public dataset. To capture changed observations, use a new output directory;
do not replace an already reviewed inventory or its pending/signed records.
Permission requests are preparation artifacts; subsequent extraction must use
a separate signed record and its exact byte hash in the appropriate input.

| M1-02 acceptance | State |
|---|---|
| Ten rows have a route or explicit blocker; SanPiN reconstructs for both dates | Engineering verified; owner accepted the inventory with its disclosed gaps. |
| Nine amendments checked for completeness; new required documents retained | Latest official chain cross-checked and all 26 pages of the bounded eight-day feed inspected; nine SanPiN publications replayed, 27 further source/application publications retained. Full historical completeness is not claimed. |
| Historical input independently justified, with bounded extension evidence if needed | Four independent historical responses and unchanged replays retained, nearby commencement evidence acquired; no later snapshot reused and no production adapter changed. Final date applicability stays blocked. |
| Processing permission separate from admission; owner/reviewer address the 59-FZ blocker | Exact-asset diagnostic records retained for all ten rows; the actual v2 human decision resolves the named 19-P qualification. Runtime relation import and full edition admission remain later work. |

The final [M1-02 closure](M1_02_CLOSURE.md) supersedes this initial matrix's
pending request state without overwriting its records. Closure completes source
routing with declared blockers, as the plan allows; all ten dated editions still
require the full later review.

Four focused inventory tests cover the ten-row/permission/temporal blockers,
corrupt and mispointed evidence, distinct card/PDF URLs, immutable replay and
protection of human records. Existing corpus/source acceptance tests and the
frozen handoff remain required. Engineering completion does not waive HITL.
