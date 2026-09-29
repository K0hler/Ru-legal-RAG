# M0-07 — pilot act and review policy

**Prepared:** 28 September 2026

**Status:** approved by the product owner on 28 September 2026; M0-07 complete

**Scope:** decisions needed by M0-07 only; this document does not approve any
`EditionCandidate`, legal provision, or gold label.

## 1. Approved fifth pilot act

Use the **Resolution of the Chief State Sanitary Doctor of the Russian
Federation dated 28 January 2021 No. 3**, which approved SanPiN 2.1.3684-21.
The Ministry of Justice registered it on 29 January 2021 as No. 62297.

Official route:

1. [Official publication card No. 0001202102050027](http://publication.pravo.gov.ru/document/0001202102050027)
   and its [original PDF](http://publication.pravo.gov.ru/file/pdf?eoNumber=0001202102050027).
2. [Integrated bank record `nd=602024221`](http://pravo.gov.ru/proxy/ips/?docbody=&link_id=7&nd=602024221&intelsearch=)
   as a consolidated-text candidate, not as verified temporal coverage.
3. Resolve every later amendment to its own official publication. A later
   publication found during this check is the Resolution dated 10 September 2026 No. 25,
   [publication No. 0001202609240014](http://publication.pravo.gov.ru/document/0001202609240014),
   registered on 23 September 2026 as No. 88406.

Why this act exercises the intended boundary:

- it is a registered federal agency act relevant to housing, waste sites,
  drinking water, and residential premises;
- the original publication is 75 pages and contains nine separately numbered
  appendices;
- the appendices include tables, sampling rules, controlled indicators, and
  journal forms rather than plain paragraphs only;
- the recent amendment chain makes repeat acquisition and explicit temporal
  uncertainty useful parts of the pilot.

The integrated-bank page inspected on 28 September 2026 exposed editions only
through the amendment dated 14 February 2022, while later official amendment
publications exist. Therefore its current consolidated coverage is
`unresolved`; M0 must not infer that it includes the amendments published in
2024-2026.

The legacy bank, the new test bank, the commercial consolidated text, and the
later official publications are reconciled separately in
[SanPiN 2.1.3684-21 source coverage](SANPIN_2_1_3684_21_SOURCE_COVERAGE.md).

## 2. Source access, rights, and rate assumptions

The portal describes itself as a federal state information system and lists
registered federal agency acts among the materials officially published there.
Its [documented publication API](http://publication.pravo.gov.ru/help) is
read-only. Official legal texts are not protected by copyright under paragraph
6 of [Article 1259 of the Civil Code](https://rospatent.gov.ru/ru/documents/grazhdanskiy-kodeks-rossiyskoy-federacii-chast-chetvertaya/download),
but that does not by itself grant a right to unrestricted automated use of
portal services, metadata, or interfaces.

No published machine-readable rate limit or bulk-use licence was found for the
four live portal interfaces. M0 therefore permits bounded pilot acquisition
only. Bulk acquisition remains blocked until the access terms are confirmed.

| M0 source | Recorded access and rights status | M0 rate assumption |
|---|---|---|
| Project fixture | Project-authored test data; redistribution permitted; no external service. | No network limit. |
| `publication.pravo.gov.ru` | Official publication and documented read-only API. Current connector status remains `Official legal act; verify access terms before bulk acquisition`. Pilot use allowed; bulk use unresolved. | At most 1 request/second, one concurrent acquisition, at most 3 total attempts per request with backoff. |
| `actual.pravo.gov.ru` | Public official consolidated-text UI; connector uses an undocumented backend whose stability and bulk-use terms are not a public contract. Current connector status remains `Official consolidated-text candidate; verify access terms before bulk acquisition`. Pilot use allowed for supported acts; bulk use unresolved. | At most 1 request/second, one concurrent acquisition, at most 3 total attempts per request with backoff. |
| New `ips.pravo.gov.ru` test bank | Public official integrated bank; the M0-06 connector uses undocumented JSON routes. Current connector status remains `Official legal act; verify access terms before bulk acquisition`. Pilot use allowed; bulk use unresolved. | At most 1 request/second, one concurrent acquisition, at most 3 total attempts per request with backoff. |
| Legacy `pravo.gov.ru/proxy/ips` bank | Public official integrated bank with a separate legacy interface. No connector is implemented. Manual pilot inspection is allowed; automated and bulk use remain unresolved. | If a connector is later approved, start with at most 1 request/second, one concurrent acquisition, and at most 3 total attempts per request with backoff. |

`declared-act` and `official-print` are provenance namespaces, not network
sources, so they do not receive independent request limits.

The rate values above are conservative operating assumptions for M0, not claims
about limits imposed by the portal and not evidence that retry/backoff is
already implemented by every connector.

## 3. Review authority

The named role **Legal Reviewer** is the only role allowed to assign
`reviewed` or `rejected` to an edition candidate or legal label. Each decision
must record the reviewer identifier, decision time, rationale, reviewed scope,
and evidence references. A source operator, corpus engineer, or product owner
does not gain this authority by operating the pipeline.

A critical unresolved identity, completeness, source, or temporal-coverage gap
prevents `reviewed`; it cannot be waived by an engineering assumption.

Before M0-10 starts, the product owner must designate at least one person to
the Legal Reviewer role. Until then, legal review is blocked.

## 4. Independent second decision for disputed gold labels

A gold label becomes `disputed` when its author or any reviewer challenges its
expected act, address, edition, source span, or no-answer result.

The disputed label must receive a second decision from another **Legal Reviewer**.
That reviewer is neither the label author nor the first reviewer. The second
decision is recorded separately and never overwrites the first. The label may
enter the closed gate set only when both decisions agree on the label and its
evidence coordinates. Otherwise it remains `disputed` and is excluded from gate
metrics; M0 records the disagreement instead of inventing a tie-break.

## 5. Recorded approval and remaining blockers

On 28 September 2026 the product owner approved:

- fifth act: SanPiN 2.1.3684-21 under Resolution No. 3 of 28 January 2021;
- the bounded-pilot source policy and rate assumptions in Section 2;
- review policy: the Legal Reviewer authority and independent-second-decision
  rule stated above.

These decisions complete M0-07. On 29 September 2026 the product owner
explicitly accepted the Legal Reviewer role under identifier
`legal-reviewer-owner`; the resulting decisions are recorded in
[M0-10 legal review](M0_10_LEGAL_REVIEW.md). Bulk acquisition remains blocked
while source terms and published rate limits are unconfirmed. The SanPiN
edition candidate remains unresolved until every official amendment and its
effective date are reconciled.

## 6. Acceptance check

| M0-07 criterion | Evidence | State |
|---|---|---|
| Fifth act and official route | Section 1 names the act, registration, official publication, consolidated candidate, and structural reason. | Pass |
| Access/rights and rate assumptions for every M0 source | Section 2 records all acquisition sources and distinguishes confirmed facts from operating assumptions. | Pass |
| Named role may assign `reviewed` or `rejected` | Section 3 grants that authority only to the Legal Reviewer role. | Pass |
| Independent second decision for disputed gold labels | Section 4 defines independence, separate decisions, and fail-closed disagreement handling. | Pass |
| Unresolved decisions are blockers | Section 5 lists reviewer assignment, edition coverage, bulk rights, and rate-limit blockers explicitly. | Pass |

## 7. Evidence checked on 28 September 2026

- [About the Official Internet Portal of Legal Information](http://pravo.gov.ru/o-portale.php)
- [Publication API help](http://publication.pravo.gov.ru/help)
- [Original act publication](http://publication.pravo.gov.ru/document/0001202102050027)
- [Later amendment publication found in this check](http://publication.pravo.gov.ru/document/0001202609240014)
- [Project source-admission policy](LEGAL_SOURCES_POLICY.md)
