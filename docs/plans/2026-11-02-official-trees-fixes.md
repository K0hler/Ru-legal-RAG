# Fix the 50-act official-tree development set

Owner request: 02.11.2026. Every document must score strictly above99%; keep
the first check, raw sources, projected controls and earlier failures immutable.
The 50 acts are now development inputs, not fresh independent qualification.

## One implementation item: preserve quotation ownership through form fields

Diagnosis: the three documents below99% all encounter an underscore line inside
an amendment quotation. `assign_body_owners` accepts it as the start of the
document's requisite block despite its explicit `in_quotation` evidence, moving
the remaining contract/form and quoted explanatory notes to the document root.
The note differences in these two amendments are not missing OCR footnote links.

- [x] Reproduce the retained region outputs before editing; snapshot the maintained
  rules and source/control/result hashes in a new local experiment.
- [x] Add failing synthetic controls for quoted blank fields, a quoted separator
  before explanatory notes, quoted signature lines, and a genuine outside-quote
  requisite block. Preserve source bytes and normal quoted-list boundaries.
- [x] Apply the smallest shared owner-rule correction, without act IDs, source
  edits, evaluator changes, exclusions or new alternatives; run the authored controls.
- [x] Run all50 against the same frozen projection6 controls in a new output.
  Require integer `100 * correct > 99 * regions` for every document; report full
  paths and section-excluding scores separately, even if identical.
- [x] Compare all237 earlier scan metrics/error lists and both earlier official-tree
  sets (100+146acts); retain any real improvements and reject regressions. Recheck
  full compiler/source-control baselines where changed ownership can reach them.
- [x] Run appropriate/full tests, Ruff and M0; obtain final code review, update
  module knowledge and a short Russian result note, then commit the completed item.

Production scope: `src/legal_rag/corpus/_ocr_owner/ownership.py` and its callers
`ocr_owner_structure.build` / `ocr_owner_ast.build_owner_tree` / PDF compiler route.
Tests: `tests/legal_rag/corpus/test_ocr_owner_notes.py` and the existing owner-rule suite.
Local evidence: `data/m1/m1-04a/experiments/20261102-official-trees-fixes-01/`.
OCR execution, OCR table correction, requisites validation and new scan selection
are outside this item. Batch24's original failed verdict remains unchanged.

Result: all50 above99% on unchanged controls,3551/3552 (99.97185%),49perfect;
minimum146/147 (99.31973%). All237 scan rows/totals/errors unchanged. Actual
before/after runs on both old official sets (100+146) have no new errors and
14 additional correct regions in3 acts. Full compiler controls10+4 pass with
identical repeats. Full1166tests pass; Ruff and M0(78/78) pass; focused fresh
review found no remaining issues. Acceptance is recorded in the new experiment.

The first partial correction retained quoted separator ownership under the
introducing point; the unchanged projection expects tail rules at the scope root.
An owner-only separator override preserves that contract without moving following
content. A broad override initially changed4 existing pp728 blank fields; the
final rule restricts it to after the last outer marker, with a failing-then-passing
negative control. All intermediate outputs remain; only `final` labels qualify
this development result. No frozen controls, evaluator, source or old report edited.
