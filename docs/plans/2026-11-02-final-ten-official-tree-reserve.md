# Prepare the final ten-document official-tree control set

Owner request: ten new documents by the same official-tree principle, reserved
for a later control check. One preparation item; work on main and commit when sealed.

- [x] Freeze maintained code466c043, source projector8, scorer and acquisition
  scripts before fetching new bodies. No production edits, parser/OCR execution,
  scoring, manual gold or tuning on this set during preparation.
- [x] Reuse saved IPS candidate metadata and existing acquisition/validation
  helpers. Freeze an ordered primary/reserve queue before network requests.
  Target one each: code, federal constitutional law, federal law, RF law,
  President decree/order, Government resolution/order, Duma/SF resolution.
  If a category has no genuinely new usable source, retain the reason and use
  the next most diverse category from fallback order pp,fz,ukaz,rp,president-order,
  duma,sf,fkz,law. All five previously unused screened codes are now consumed;
  the frozen queue therefore starts with9available groups and a second distinct
  Government resolution,10documents total.
- [x] Exclude every previously acquired ID, equivalent act identity and exact
  body hash across earlier corpora, five exposed sets and scan input metadata.
  Census-only metadata does not count as prior acquisition. Verify both within
  the new set and against prior manifests; keep rejected attempts immutable.
- [x] Acquire official card, same-edition HTML and nonempty source tree through
  the existing IPS API workflow, sequential requests with at least1.1s pause.
  Before parsing, source-only usability requires ordered/nested valid spans and
  nonempty unit types throughout the tree, so missing typing cannot silently
  masquerade as an automatic reference. Replacements are source-only, never
  based on candidate success. Original titles, including empty titles, stay raw.
- [x] Prepare/freeze automatic projection8 controls, record all exclusions and
  alternatives, verify hashes/content/novelty and code immutability, run relevant
  acquisition/projector checks. Keep the entire set in holdout with reserved
  status and no exposure receipt. Do not call preparation a passed check.
- [x] Update nearest documentation/data instructions and a short Russian index,
  then commit. No new scan/prototype number or M1-04A/admission closure.

Corpus: `data/m1/m1-04a/json-corpus/20261102-final-control-10/`.
Evidence: `data/m1/m1-04a/experiments/20261102-final-control-10-acquisition-01/`.
Implementation uses existing `docs/assets/acquire_m1_04a_json_corpus.py` and
`m1_04a_json_baseline.py`; any one-run orchestration lives only in that experiment.
