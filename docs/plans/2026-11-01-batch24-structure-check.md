# Scan batch24: independent structure check

> Use superpowers:executing-plans; source annotation uses fresh independent contexts.

**Goal:** OCR and check all five new scans/94pages against independent source/image controls.
**Architecture:** Reuse the pinned local OCR runtime, maintained compiler and existing validators.
Keep the candidate unchanged from its pre-OCR freeze through evaluation; no new parser rules.
**Tech stack:** Python, OCR-Lab dots.mocr, source-only JSON packets and saved-native replay.
**Spec:** Owner go-ahead on the five downloaded scans, 01.11.2026; the existing
[Task 3 protocol](2026-10-17-m1-04a-ocr-structure.md#task-3-qualify-the-frozen-parser-on-independent-documents).

## Constraints and review focus

- Check every selected document; no after-run replacements or tuning. Source requisites are outside this verdict.
- Three Government resolutions and two sanitary amending acts; report their actual scope without broadening it.
- Source numbering warnings follow the explicit owner policy: printed numbers stay unchanged, warnings bind to source;
  parser errors, unrelated ambiguities, missing text, wrong parents/notes/order or table damage still fail.
- Annotation authors inspect every assigned page image and raw source region in fresh contexts, with no candidate/old gold.
- Preserve sources, prior downloads/runs, model/profile hashes and every genuine failed result. No push.

## A. Prepare and freeze

- [x] Verify acquisition/novelty records, prepare source-only annotation brief and reuse existing orchestration.
- [x] Regenerate M0, commit preparation, then freeze all candidate code, source permissions, OCR profile/runtime/model files.

## B. Extract and seal independent controls

- [x] OCR all94pages locally and replay saved native results; verify actual runtime receipts and source coverage.
- [x] Three independent jobs inspect/annotate all pages and source units; seal outputs before any candidate evaluation.
- [x] Record full coverage, immutable hashes and annotation completion; update module knowledge and commit.

Source stage: `20261101-batch24-check-01/` freezes code at `4d916ef`, all five source/runtime bindings,
94 actually viewed images,986 regions and443 source units before candidate evaluation. Three fresh-context
jobs sealed their controls; all saved-native replays and actual runtime receipts match. Docker stopped.

## C. Evaluate and report

- [x] Compile each act twice and replay unchanged; require identical artifacts and compare all controls with explicit warning policy.
- [x] Retain every failure, separate OCR/source defects from parser errors and record the family/format limits.
- [x] Run applicable tests/Ruff/M0 and final fresh review; write a short Russian result, update instructions and commit.

Result: [short Russian check report](../milestones/m1/04a/M1_04A_BATCH24_CHECK_2026-11-01.md).
Strict1/5, Government1/3 and sanitary-amendments0/2; all443units match, but16content-owner
differences and24heterogeneous continuation differences remain. Retain original controls/results.
Ruling: do not tune the candidate or rewrite controls during this frozen check. Record the
continuation-adjacency convention gap and actual OCR table defects separately from parser ownership.
