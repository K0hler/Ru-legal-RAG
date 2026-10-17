# M1-04A: Universal OCR Structure Parser Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans when the owner starts this slice. Work on `main`, one verified item and commit at a time. This document records the task; implementation and acquisition have not started.

**Status:** planned, added at the owner's request on 17 October 2026.

**Task board:** [M1-04A: Универсальный структурный парсер OCR](https://trello.com/c/fX6dQ9HM), ready for work with eight incomplete acceptance items.

**Goal:** Turn normalized OCR output into a reusable, source-bound legal hierarchy and demonstrate its transfer to additional official documents.

**Architecture:** Consume the existing `text-extraction/1` contract after M1-04, extending the shared structure engine and family profiles where useful. Keep OCR execution/engine-specific decoding separate from legal structure. Preserve the accepted official-JSON import route from M1-03A.

**Tech stack:** Python 3.13, the existing corpus CLI/test stack and local dots.mocr runtime. Ordinary structural tests use authored or retained normalized input without inference.

**Spec:** [M1 implementation plan, M1-04A](../milestones/m1/M1_IMPLEMENTATION_PLAN.md#m1-04a-universal-ocr-structure-parser); [PRD structure requirements](../overview/PRODUCT_REQUIREMENTS.md); the owner's instruction: add M1-04A for a universal OCR structural parser, examine existing files and download several additional files for experiments.

## Global constraints

- "Universal" means one engine with reusable family profiles and an explicit support matrix. It does not mean every legal layout is already supported. No rules selected by an act's number, date, title, filename, hash or fixed page position.
- Input is normalized `text-extraction/1`, not native dots.mocr fields. Output retains the existing `legal-ast/2` contract, physical `document_tree`, exact source spans and explicit unresolved findings.
- Reuse saved OCR for parser experiments. A fresh OCR attempt is a separate version; repeating the parser on one saved extraction must be deterministic.
- Keep original PDFs, native OCR, prior failed experiments, approved builds and frozen M0 evidence unchanged. Processing permission and exact asset hashes precede diagnostic compilation.
- Keep the owner-accepted round-seal accuracy exclusion and the original SanPiN's physical-page-75 table quality exclusion from M1-04. Retain their regions/text/topology and locators; neither exclusion waives other tables, missing hierarchy or invented legal addresses.
- Legal interpretation, automatic amendment application, dated reconstruction, retrieval/chunking and legal admission remain outside this slice. The task does not select a new LLM/provider or approve external document transmission.

## Review focus

- A provision split over pages and intervening page headers must keep its owner and source spans.
- Approving acts, approved texts, annexes and quoted amendment payloads need separate numbering scopes.
- Numbering-like seal junk, page numbers and headers must not create legal provisions.
- Tables, blank/merged cells, footnotes and image-only regions must remain visible under their actual owner or an explicit unresolved scope.
- OCR category/spacing variation and unclear legal numbers must produce recorded ambiguity rather than silently changing wording or fabricating a parent/address.

## Corpus and experiment protocol

1. Start with all ten retained SanPiN original/amendment PDFs and all 103 pages from M1-04. Inventory other available OCR-Lab files/results; reuse them only with verified origin and processing permission. Known files are development/regression inputs.
2. Initial additional acquisition target: **six distinct official non-pilot acts**. Use two for open experiments and reserve four for independent transfer checks: two acts for each of two families. Initial required families are sanitary rules with an approving act and government resolutions with approved texts. Record exact identities/URLs/hashes and the split before parsing reserved bodies. Acquire through the existing `sources` lifecycle; retain `new`/`unchanged` evidence and diagnostic permission bindings.
3. Select a mix covering legal numbering, multipage text, annexes, tables, footnotes and quoted changes. Laws/codes can extend the matrix with two further reserved acts per newly declared family. Different editions or pilot amendments do not count as distinct transfer acts. Six is an initial corpus target, not a substitute for the two-act-per-family rule.
4. Do not inspect reserved bodies for rule design. Prepare independent source/image-based structural controls separately from the candidate parser; do not generate expected parents/addresses from its output. Freeze parser/profile, extraction and control versions before evaluation.
5. If evaluation causes a rule change, keep the failed run, promote that document to development and reserve two new acts for the affected family. Keep a failed or incomplete matrix row visible.

Official HTML/JSON trees, where available, may provide independently bound comparison evidence. They must not supply the candidate OCR hierarchy or silently replace failed OCR input. Never read closed retrieval gold.

## Files and interfaces

- `src/legal_rag/corpus/structure.py`: existing `build_structure(extraction, declared_identity=None, role="consolidated")` and shared traversal/profile behavior. Inspect which parts transfer before adding rules.
- `src/legal_rag/corpus/pdf_extraction.py`: `pdf_tree(extraction, declared_identity, role)` connects normalized OCR to that engine and retains physical structure/uncertainties. Keep model decoding outside the structural parser.
- `src/legal_rag/corpus/compiler.py`: consume the same extraction index and AST; preserve permission checks and the official import route.
- `tests/legal_rag/corpus/test_ocr_structure.py`: authored cross-document structural examples and negative controls. Existing PDF/runtime/official-import tests remain regressions.
- `docs/assets/validate_ocr_structure.py`: explicit retained-input evaluation, independent control comparison and `parser-transfer-report/1`; no acquisition or inference in default tests.
- `data/m1/inputs/m1-04a/` and `data/m1/experiments/m1-04a/<run-id>/`: ignored input/split/control records, immutable trials, frozen versions, outputs and measurements.
- `docs/milestones/m1/04a/`: Russian experiment/acceptance reports with measured results, support matrix and limitations; update `docs/README.md` when adding them.

These are extension points, not instructions to rewrite every listed module. Add a separate production module only when the selected approach needs an independent responsibility.

## Task 1: Inventory existing outputs and acquire the experiment corpus

**Consumes:** existing M1-04 evidence/index, permitted source assets and source acquisition CLI.
**Produces:** hash-bound corpus inventory, development/reserved split and a Russian baseline report.

- [ ] Verify current M0 gate and the ten saved PDF/extraction bindings before using them.
- [ ] Run the current diagnostic `pdf_tree` on every existing saved extraction. Record nodes, unresolved blocks, wrong parents/numbers, annex/table ownership and cross-page failures; unchanged replay must produce identical IDs/hashes.
- [ ] Download the six additional acts through `sources`, preserve source metadata and permission, and record the split described above. Inspect/decode only development bodies while designing rules.
- [ ] Group observed failures by reusable structure class. Record the minimal proposed extension and why existing engine behavior is insufficient before changing production code. Do not label OCR text/sign errors as parser fixes.
- [ ] Retain the baseline report, update applicable instructions and commit the completed inventory/probe tooling.

## Task 2: Implement reusable OCR hierarchy reconstruction

**Consumes:** normalized extractions, the development corpus and failure classes from Task 1.
**Produces:** source-bound `legal-ast/2` through the existing `pdf_tree` interface, with explicit supported/unsupported structures.

- [ ] Add failing authored tests in `test_ocr_structure.py` for cross-page provision continuation; approving/approved/annex scopes; quoted foreign numbering; table/footnote ownership; and seal/header/page-number noise. Assert literal expected parent addresses and order, exact source substrings and exactly-once text accounting.
- [ ] Add tests for OCR category/spacing variation and negative tests for ambiguous numbering, missing scope, duplicate addresses, swapped parents and dropped text/regions. Ambiguity must remain unresolved; corrupted ownership must fail validation.
- [ ] Run the focused tests and record the expected failures before implementing the smallest shared engine/profile extensions.
- [ ] Add engine-neutral input controls: identical normalized content with different provider metadata and no native OCR fields must yield the same hierarchy/address relationships. This does not claim a second real OCR engine is qualified.
- [ ] Preserve raw text while using mapped whitespace/layout cues for structure. Record any normalization mapping; no silent number/date/sign repair or per-document patches.
- [ ] Run focused tests and existing native/official-import/PDF regressions. Verify the final engine consumes every selected full development document, not sample pages only; update instructions and commit.

## Task 3: Qualify the frozen parser on independent documents

**Consumes:** frozen final parser/profiles, saved normalized extractions and independently prepared source controls.
**Produces:** `parser-transfer-report/1`, repeated full compiler artifacts and a Russian review report.

- [ ] Implement the explicit validator with authored tests that reject a wrong parent/number, dropped region, mismatched extraction/control hash, unsupported critical structure and a development act presented as reserved evidence.
- [ ] Freeze code/profile, extraction, corpus split and control hashes. Evaluate all four reserved acts in full through the actual compiler; compare with the independent controls.
- [ ] For every supported family/OCR-format row, require two distinct non-pilot acts passing identity, numbering, parents/order, annex/table/footnote ownership, exactly-once accounting and exact source locators. Retain unresolved/failing cases and measured timing; a coverage percentage alone cannot pass a wrong hierarchy.
- [ ] Compile every input twice in separate output directories and replay into the same directory. Require identical IDs/hashes and `unchanged` replay for the same saved input/version; retain fresh OCR variability separately.
- [ ] Review examples for every observed structure class against page images and retain the actual structural review record. It is distinct from legal admission of a dated edition.
- [ ] Keep `pdf_structure_unqualified` on unsupported/unverified family-format routes. Any future relaxation must bind to passing qualification evidence and retain genuine unresolved findings.
- [ ] Run the full default suite, Ruff, `git diff --check` and M0 gate. Replay the official-JSON route unchanged, publish the support/failure matrix, update instructions and commit.

## Completion and downstream boundary

M1-04A completes only after the generic engine is connected to PDF compilation, the entire retained 103-page baseline has reviewed hierarchy/ownership controls and exactly-once accounting, both initial family/OCR rows pass the independent two-act checks and structural review is recorded. Critical unresolved hierarchy in a required supported input blocks completion. Downloads, successful OCR, a tree-shaped JSON or success on the known SanPiN alone do not complete it.

M1-06 consumes this engine and its qualification evidence for the complete SanPiN original/amendment bundle, including act-specific coverage and operation-target readiness. Further family extensions in M1-09/M1-11 must satisfy the same protocol. M1-05 still depends only on extraction from M1-04. The owner selected M1-04A as the next planned slice; implementation/downloads start in its execution turn.

Verification commands during execution (the new test/validator files are planned):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/legal_rag/corpus/test_ocr_structure.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check src tests docs/assets/validate_ocr_structure.py
git diff --check
.\.venv\Scripts\python.exe docs/assets/generate_m0_gate.py
```
