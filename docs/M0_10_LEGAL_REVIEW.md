# M0-10 — legal review of pilot candidates

**Review date:** 29 September 2026

**Decision time precision:** calendar date only; exact clock times were not
captured by the simplified checklist.

**Legal Reviewer:** `legal-reviewer-owner` — the product owner explicitly
accepted this role and supplied the five human review results.

**Result:** review activity completed; 0 candidates are admitted without a
blocker, 1 candidate is `rejected`, and 4 candidates remain `unresolved`.

## Reviewed scope and method

The Legal Reviewer checked the act identity, displayed edition and obvious text
completeness against the supplied official document and the public
ConsultantPlus card. Engineering checks supplied provenance, hashes, repeat
acquisition and the M0-09 gap report. ConsultantPlus was used only as a control;
it is not a corpus source.

`reviewed` is not assigned merely because the human comparison returned “OK”.
Under the approved review policy, unresolved amendment or effective-date
evidence still blocks corpus admission.

## Decisions

| Candidate | Human result | M0-10 status | Rationale and scope | Approx. human time |
|---|---|---|---|---:|
| ЖК РФ | OK | `unresolved` | Identity, edition displayed from 01.09.2026 and obvious completeness were accepted. M0-09 did not acquire the amendment chain or effective-date evidence, so temporal admission remains blocked. | 10 min |
| ПП РФ № 354 | OK with correction | `rejected` | The text edition remains 19.12.2025. Government Resolution No. 931 of 24.07.2026 is a territorial applicability overlay, not a new general text edition. The candidate's source-declared date 27.07.2026 therefore cannot be admitted as the text-edition date. | 10 min |
| ПП РФ № 491 | Initially reported as a problem; exception resolved | `unresolved` | The public ConsultantPlus heading says “ред. от 07.03.2025”; “26 сентября” is a news date lower on the page. A fresh official acquisition on 29.09.2026 again returned “на 01.09.2025, (№ 293 от 07.03.2025)” and the same asset hashes, then `unchanged` on repetition. Identity and displayed edition are accepted, but the amendment chain and effective-date evidence remain unresolved. | 20 min |
| 59-ФЗ | OK with note | `unresolved` | Identity, edition displayed from 30.03.2025 and obvious completeness were accepted. The official consolidated text's reference to Federal Law No. 48-FZ describes special application for regional ombudsmen. Constitutional Court Resolution No. 19-P of 18.07.2012 is a separate case-law effect on Articles 1–3. That relation and the amendment/effective-date evidence are not yet represented, so temporal and case-law-sensitive admission remains blocked. | 20 min |
| СанПиН 2.1.3684-21 | OK | `unresolved` | The original and nine official amendment publications were accepted as a source bundle. M0-09 has no verified consolidated edition and has not resolved the effective dates into one `LegalEdition`; the bundle is therefore not admitted as a consolidated candidate. | 20 min |

Total reported human effort is approximately **80 minutes**.

## Exception evidence

### ПП РФ № 491

- [ConsultantPlus control card](https://www.consultant.ru/document/cons_doc_LAW_62293/)
  displays edition 07.03.2025.
- [Official consolidated-text candidate](http://ips.pravo.gov.ru/search/79a4eeb726366b2c4d5b7c72cd6185c5ca569a8ea77fd7a2e96c0582d95ae4dd)
  displayed the current edition from 01.09.2025.
- The fresh run returned `new`, followed by `unchanged`; both retained text SHA-256
  `43084742027876a9c819d39c5664db7c3823391dae350f0ed5811cd82264e5f8`
  and card SHA-256
  `77c505af269e4f6bfea881d9b45dbcaf1a7a6c003942ad55e2129c583034d20d`.

### 59-ФЗ

- [Official consolidated text](http://actual.pravo.gov.ru/list.html#hash=4c8dcb690700cdc95a209ca40db2bb177cfc85916d6cfef83439b8696fbf546f&bpa=ebpi)
  records the special-application reference to Federal Law No. 48-FZ.
- [Federal Law No. 48-FZ in the official bank](http://ips.pravo.gov.ru/search/e1a7d76abfd409ca7d2cc0188226889cc76f796f651d171d42ece8014910f008)
  states that 59-FZ applies to regional ombudsmen subject to the special rules of
  No. 48-FZ.
- [Constitutional Court Resolution No. 19-P](https://rg.ru/documents/2012/08/03/ks1807-dok.html)
  sets binding constitutional-law requirements for applying Articles 1–3 to
  legal entities and organisations performing public functions. It is case
  law, not a text amendment made by No. 48-FZ.

## Measurement deviation and second review

The simplified checklist requested approximate minutes, not timestamps.
Consequently, per-act start/finish times and exception-only minutes were not
captured; the two 20-minute estimates include the ПП РФ № 491 and 59-ФЗ
exception handling. This part of the M0-10 acceptance criterion is recorded as
`partial`, not reconstructed from chat or file times.

No reviewer disagreement remains: the ПП РФ № 491 observation was resolved by
the exact card heading and repeat official acquisition, while the 59-ФЗ note is
classified as two different legal relations. If either classification is
challenged later, **a human Legal Reviewer other than `legal-reviewer-owner` is
required** and the candidate remains excluded until both decisions are stored.

## Acceptance check

| M0-10 criterion | Result |
|---|---|
| Every candidate has `reviewed`, `rejected` or `unresolved` with rationale | Pass: one `rejected`, four `unresolved`. |
| No coverage inferred from name, capture time or label | Pass: human comparison, M0-09 gap evidence and exception checks are recorded separately. |
| Critical gaps prevent approval | Pass: no candidate with a critical gap was marked `reviewed`. |
| Start/finish and exception time recorded per act | Partial: approximate per-act effort is retained; exact timestamps and exception-only minutes were not collected. |
| Disputes use an independent second reviewer | Pass as policy; no unresolved dispute exists. A future challenge is fail-closed and requires another human Legal Reviewer. |
