# Check 50 new acts against official trees

Owner request: 02.11.2026. Use existing website structure instead of new manual
annotation; defer OCR defects. This is a clean-text structure check, not a scan batch.

- [x] Freeze the current maintained post-П23 rules, projection 6, metadata-based
  candidate order and previous-input inventory before downloading new text.
  Quotas: 20 Government resolutions, 12 federal laws, 12 decrees,
  4 Government orders and 2 federal constitutional laws; seed 20261102.
  Exclude previously consumed IPS IDs, known act identities and matching body hashes.
- [x] Acquire 50 same-edition IPS HTML/tree pairs through the existing official API;
  retain failures and refill only from the preordered same-family reserve.
  Verify all tree anchors/ranges and freeze raw responses before evaluation.
- [x] Use the unchanged official-tree projection and owner evaluator for all 50.
  Freeze automatic controls before running the maintained parser once; do not tune it.
- [x] Report strict and section-excluding owner accuracy per document, exclusions
  and alternatives; verify source/code hashes, update module notes and commit.

Local sources: `data/m1/m1-04a/json-corpus/20261102-v3/`.
Evidence: `data/m1/m1-04a/experiments/20261102-official-trees-check-01/`.
Existing tools: `docs/assets/acquire_m1_04a_json_corpus.py` and
`docs/assets/m1_04a_json_baseline.py` (projection 6).

The fixed old screening metadata is reused only to order previously unconsumed acts;
this is not a new portal-wide random sample. Official trees can omit quoted/form
substructures; retain the existing projection's exclusions and accepted alternatives.
Artificial page geometry does not test OCR, physical page continuations or table cells.
No result here replaces the failed scan-batch24 check or constitutes legal admission.

Result: 3437/3552 (96.76%), identical strict/no_section scores; 47/50 above 99%,
46/50 perfect. All 50 acquired without refills, 1896 official nodes, no projected
region exclusions or alternative owners. Main mismatch is the quoted contract form
in Government Resolution1288/2023 (111 regions); four footnote differences remain
in three other resolutions. These are retained comparison results, not 115 independently
adjudicated parser defects. The each-document target fails; M1-04A stays open.

Verification: M0 78/78, existing projection/profile checks 7 passed; all frozen
candidate/source/control/prior-file bindings match. The first read-only verifier
compared newline-normalized HTML text with raw JSON strings and stopped. A separate
verifier compares UTF-8 bytes; no source, control, candidate or score was changed.
The original verifier and attempt receipt are retained. API responses were downloaded
with the explicitly recorded curl transport, retaining the same HTTP IPS endpoints.
