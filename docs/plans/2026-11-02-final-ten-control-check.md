# Run the frozen ten-document official-tree control check

Owner request: execute the parser and check the prepared ten documents.
One check item; work on main, preserve first results regardless of outcome.

- [x] Verify all preparation code/source/control/prior/seal bindings at466c043
  and copy the21frozen controls into a new check experiment without reprojection.
- [x] Freeze the execution wrapper and record exposure before the first build.
  Run every document once using the maintained frozen owner parser. Do not edit
  production code, source controls or corpus status/split during this check.
- [x] Verify all715source keys and saved output hashes; replay scores from
  stored predictions. Report strict per-document counts and the strictly>99%
  criterion, retaining raw errors and any failed builds. Distinguish reduced
  metrics and source-reference limits without rescoring changed expectations.
- [x] Verify original bindings again, write a separate exposure-complete receipt
  and result freeze. Record a short Russian result and update nearest notes.
  Commit the completed check. This does not qualify new OCR scans or admit acts.

Preparation: `data/m1/m1-04a/experiments/20261102-final-control-10-acquisition-01/`.
Check: `data/m1/m1-04a/experiments/20261102-final-control-10-check-01/`.
Only one-run orchestration, receipts and reports are new; no parser changes.
