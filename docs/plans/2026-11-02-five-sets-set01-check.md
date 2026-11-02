# First check of official-tree set1

Owner request: 02.11.2026, start checking the five prepared sets. Check set1
first; leave sets2–5 unused for later checks after any corrections.

- [x] Verify sealed same-edition sources and projection6 controls; bind the entire
  current candidate, including private rules, before its first run.
- [x] Run all50 set1 documents once with the existing evaluator, without changing
  parser rules, controls, exclusions, alternatives or selected documents.
- [x] Verify stored results against every frozen control and input. Report exact
  per-document full-path and section-excluding scores, with the strict integer
  target `100 * correct > 99 * regions`. Retain failures and score exclusions.
- [x] Record set1 exposure outside immutable source/split/status files, preserve
  unused sets2–5, write a short Russian result and commit the completed check.

Candidate: maintained production code at `90d5cd4` (functional correction09fddb8).
Source: `data/m1/m1-04a/json-corpus/20261102-five-sets/set-01/`.
Prepared controls: `experiments/20261102-five-sets-acquisition-01/controls/set-01/`.
New evidence: `data/m1/m1-04a/experiments/20261102-five-sets-set01-check-01/`.
This is a clean-text comparison with website trees, not OCR or PDF qualification;
do not close M1-04A or replace historical failed checks from this result.

Result: first check failed the every-document target.38/50 above99%,35perfect;
strict/no_section9749/10565 (92.27638%).12of10577projected regions unscored;
no alternative owners. Six Presidential Orders have a confirmed projection-only
A/S current-act-wrapper mismatch; their internal paths agree. Preserve original
zero scores and controls, and do not confuse them with total parser loss. Other
documents retain actual comparison differences requiring separate source/rule work.
All46candidate files and2597source/control bindings match; stored50/50scores/errors
repeat. M0:78/78, existing projection/profile checks7passed. No code tuning,
control correction, OCR or other-set evaluation. Set1 exposure recorded separately.
