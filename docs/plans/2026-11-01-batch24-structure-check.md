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

- [ ] Verify acquisition/novelty records, prepare source-only annotation brief and reuse existing orchestration.
- [ ] Regenerate M0, commit preparation, then freeze all candidate code, source permissions, OCR profile/runtime/model files.

## B. Extract and seal independent controls

- [ ] OCR all94pages locally and replay saved native results; verify actual runtime receipts and source coverage.
- [ ] Three independent jobs inspect/annotate all pages and source units; seal outputs before any candidate evaluation.
- [ ] Record full coverage, immutable hashes and annotation completion; update module knowledge and commit.

## C. Evaluate and report

- [ ] Compile each act twice and replay unchanged; require identical artifacts and compare all controls with explicit warning policy.
- [ ] Retain every failure, separate OCR/source defects from parser errors and record the family/format limits.
- [ ] Run applicable tests/Ruff/M0 and final fresh review; write a short Russian result, update instructions and commit.
