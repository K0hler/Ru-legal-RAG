# M1-02: ten input routes and human review request

**Prepared:** 2 October 2026.
**Status:** engineering inventory and bounded acquisition verified; the owner
accepted the inventory with its disclosed gaps and authorized diagnostic
processing of all five acts on 2 October 2026. Substantive completeness and
dated legal-admission checks remain unresolved; M1-02 is not fully accepted.
No dated edition is legally admitted.

## Retained engineering result

The M0 gate was regenerated: `pass`, 78/78 criteria, no evidence problems.
The existing source lifecycle acquired the fourteen pilot documents in a new
local archive, then returned fourteen `unchanged` results. The separate
acquisition of Resolution No. 1242 returned `new`, then `unchanged`. There are
15 source items and 32 immutable raw assets under `data/m1-02-sources/`.
The pilot's 60 requests received 21,306,568 bytes in 101.055 seconds, with no
retries or failures; the No. 1242 replay is recorded separately.

The new [inventory generator](assets/generate_m1_inventory.py) reads source
metadata and validates every retained raw asset's length, SHA-256, archive path,
source membership and evidence URL. It does not extract legal text, change M0
source contracts, select historical text or create a legal admission.
It writes a ten-row local inventory, a review packet and five **pending**
`processing-permission/1` templates. A repeat returns `unchanged`; a conflicting
existing inventory or human record is never overwritten. Absolute archive paths
do not enter the inventory content hash.

Local artifacts:

- [Ten-row inventory](../data/m1/inputs/m1-02/inventory.json), content hash
  `dd1a34e60aaeac8e0d5134421cf338c1854a12414678317465d358f7f3df7dfc`.
- [Human review request](../data/m1/inputs/m1-02/review.md), with official URLs,
  document hashes, source-declared edition history and exact decisions requested.
- [Search observations](../data/m1/inputs/m1-02-search.json), retaining failed
  official-domain searches, successful known-ID acquisitions, discovery-only
  commercial leads, the prior official amendment-chain check and remaining gaps.
- [Pilot result pointer](../data/m1-02-live-pilot.json) and
  [No. 1242 replay](../data/m1-02-pp491-replay.json).
- Pending permission files are beside the inventory under `permissions/`.
  Their signer and timestamp are null; `pending` cannot pass M1-01's permission
  validation. No user or Legal Reviewer signature is inferred from implementation
  authorization or the historical M0 review.
- [Owner consent](../data/m1/reviews/m1-02-owner-consent/decision.json) records
  the explicit chat message “Я даю согласие на все”, its explained scope, exact
  inventory content/file hashes, ten row dispositions and five separately
  authorized permission records. The record uses `legal-reviewer-owner`, the
  previously accepted owner/reviewer identifier. Its UTC timestamp is the time
  the decision was recorded; the exact chat-message time was not supplied.
- Allowed permissions are under `data/m1/reviews/m1-02-owner-consent/permissions/`.
  Identical hash-checked copies under `data/m1-02-sources/reviews/m1-02-owner-consent/`
  allow the compiler to resolve them within its declared archive root.
  The original pending packet remains immutable historical evidence.
- [Permitted 59-FZ input](../data/m1/inputs/m1-02-permitted/federal-law-59-2026-10-01.json)
  passes M1-01's `load_input` validation for a diagnostic snapshot at the control
  target only. The JSON/HTML extraction profile remains pending M1-03. The later
  text cannot be passed as a `2025-01-01` input; that request is refused.
- [Consent verification](../data/m1/reviews/m1-02-owner-consent/verification.json)
  confirms the raw hashes, unchanged source/archive records and original packet,
  allowed permission, retained legal blockers and refusal of the historical target.

## Ten checks

These are proposed source routes with explicit blockers, not admitted inputs.
`selected_date_basis` is null for all ten rows. Every row retains its original
[M0-10 decision](M0_10_LEGAL_REVIEW.md), reviewer `legal-reviewer-owner`, unverified
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
and PDFs. The [earlier official-source inspection](SANPIN_2_1_3684_21_SOURCE_COVERAGE.md)
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
| Nine amendments checked for completeness; new required documents retained | All known publications replayed, prior official chain cross-checked and search gaps recorded; human completeness check remains unresolved. |
| Historical input independently justified, with bounded extension evidence if needed | No later snapshot reused and no adapter changed; four historical routes explicitly blocked and accepted as unresolved. |
| Processing permission separate from admission; owner/reviewer address the 59-FZ blocker | Five exact-asset permissions explicitly allowed; separate owner decision retains the 59-FZ admission blocker. |

Four focused inventory tests cover the ten-row/permission/temporal blockers,
corrupt and mispointed evidence, distinct card/PDF URLs, immutable replay and
protection of human records. Existing corpus/source acceptance tests and the
frozen handoff remain required. Engineering completion does not waive HITL.
