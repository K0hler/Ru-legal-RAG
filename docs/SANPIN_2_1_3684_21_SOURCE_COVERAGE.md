# SanPiN 2.1.3684-21 — source coverage analysis

**Checked:** 28 September 2026

**Status:** source-routing decision approved for M0; current edition candidate unresolved

**Boundary:** this analysis does not reconstruct or legally approve a consolidated text.

## Result

The observed dates do not describe one synchronized dataset:

- the legacy official bank exposes a consolidated edition only through the
  amendment dated 14 February 2022;
- an exact search for `СанПиН 2.1.3684-21` in the new test bank returned zero
  documents;
- `docs.cntd.ru` presents a private editorial consolidation with changes through
  12 February 2026;
- the official publication portal contains the original act, every amendment
  publication that was located, and a further amendment dated 10 September 2026.

Therefore M0 cannot choose a current edition by taking the newest date shown by
one interface. It must acquire the original and amendment acts from the official
publication portal, preserve each source claim, and leave temporal coverage
unresolved until legal review.

## Evidence and source roles

| Source checked | Observation | M0 role |
|---|---|---|
| [Original official publication No. 0001202102050027](http://publication.pravo.gov.ru/document/0001202102050027) | Resolution No. 3 of 28 January 2021; registered as No. 62297. | Authoritative original and raw asset. |
| [Legacy integrated-bank record `nd=602024221`](http://pravo.gov.ru/proxy/ips/?docbody=&link_id=7&nd=602024221&intelsearch=) | Its edition selector ended at Resolution No. 6 of 14 February 2022 during the live check. | Official consolidated candidate with source-declared coverage only through that visible edition. |
| [New test bank](http://ips.pravo.gov.ru) | Exact live search returned `0 documents`. M0-06 integrates this system, not the legacy interface. | Record the coverage gap; do not silently fall back inside the M0-06 connector. |
| [CNTD page](https://docs.cntd.ru/document/573536177) | Marked active and “with changes as of 12 February 2026”; the page is an AO Kodeks copyrighted editorial resource. | Discovery and reconciliation checklist only. Do not ingest or redistribute its consolidated text as an official source. |
| [Official publication No. 0001202609240014](http://publication.pravo.gov.ru/document/0001202609240014) | Resolution No. 25 of 10 September 2026; registered 23 September and published 24 September 2026. Its PDF cites the prior amendment chain through 12 February 2026. | Authoritative later amendment publication; separate effective-date review required. |

The exact-search result proves only that the query returned no document on the
check date. It does not prove that the new bank's backend can never contain the
act under another identity or search form.

## Amendment acquisition checklist

The CNTD page supplied the first eight discovery leads. Each lead has an
independent official publication route, and Resolution No. 25 itself recites the
same prior chain.

| Amendment | Official publication |
|---|---|
| Resolution No. 16 of 26 June 2021 | [0001202107070011](http://publication.pravo.gov.ru/document/0001202107070011) |
| Resolution No. 37 of 14 December 2021 | [0001202112300125](http://publication.pravo.gov.ru/document/0001202112300125) |
| Resolution No. 6 of 14 February 2022 | [0001202202170032](http://publication.pravo.gov.ru/document/0001202202170032) |
| Resolution No. 11 of 15 November 2024 | [0001202412270033](http://publication.pravo.gov.ru/document/0001202412270033) |
| Resolution No. 10 of 17 June 2025 | [0001202507240013](http://publication.pravo.gov.ru/document/0001202507240013) |
| Resolution No. 13 of 25 June 2025 | [0001202507250037](http://publication.pravo.gov.ru/document/0001202507250037) |
| Resolution No. 21 of 29 December 2025 | [0001202512300004](http://publication.pravo.gov.ru/document/0001202512300004) |
| Resolution No. 2 of 12 February 2026 | [0001202602270023](http://publication.pravo.gov.ru/document/0001202602270023) |
| Resolution No. 25 of 10 September 2026 | [0001202609240014](http://publication.pravo.gov.ru/document/0001202609240014) |

An amendment date is not automatically its effective date. Resolution No. 25
contains no special commencement clause in the official PDF. Under paragraph 12
of [Presidential Decree No. 763](http://pravo.gov.ru/proxy/ips/?docbody=&nd=102041458),
a registered federal executive act normally takes effect after ten days from
official publication unless it sets another rule. That period had not elapsed
on 28 September 2026, so Resolution No. 25 did not yet change the edition in
force on the check date. Its exact `valid_from` still requires an evidence-backed
review before the candidate can be marked `reviewed`.

## M0 decision

1. Acquire the original and all nine located amendment publications from
   `publication.pravo.gov.ru` as separate immutable assets.
2. Treat the legacy-bank text as an official consolidated candidate limited to
   the coverage it declares; do not treat its 2022 endpoint as proof that later
   amendments do not exist.
3. Keep the M0-06 connector scoped to the new test bank. A legacy-bank adapter,
   if needed for the five-act pilot, is a separate source contract.
4. Use CNTD only to discover and cross-check amendment references. It cannot
   supply the product's authoritative raw or consolidated text.
5. Before M0-10, account for every amendment, its affected provisions, and its
   effective date. Any gap keeps temporal coverage unresolved.
