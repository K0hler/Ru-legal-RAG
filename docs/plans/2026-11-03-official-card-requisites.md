# Official-card requisites implementation plan

> **For agentic workers:** Use superpowers:executing-plans for this single end-to-end item.

**Goal:** Use archived official-card requisites for PDF documents without requiring OCR identity agreement.

**Architecture:** Keep the PDF owner tree and its historical OCR identity diagnostic unchanged. During input validation, read the publication card bound by the PDF acquisition capture, validate its archived bytes and source membership, and expose its requisites in the draft/report. OCR identity does not block this PDF route; missing card evidence or required fields remain explicit.

**Tech stack:** Existing Python standard library, corpus compiler and offline pytest fixtures.

**Spec:** Owner decision in this chat on 3 November 2026, superseding mandatory OCR requisites comparison in `2026-10-31-npa-requisites-task.md`. The owner has authorized execution without additional design approval.

## Constraints

- Work on `main`; preserve frozen M0 adapters/contracts, raw archives and prior results.
- Card date, full number including suffix, document type and named issuing authorities are required. A substantive title is optional.
- Verify card/PDF/extraction linkage. Never replace OCR text with card text or infer legal applicability.
- The implemented source contract is publication.pravo PDF acquisition; retain explicit unavailable status for unsupported/missing card evidence. Native-text parsing is unchanged.
- Keep OCR/source/structural/temporal/legal-review guards independent.

## Review focus

- Incorrect OCR dates or unsupported OCR act types must not block valid card requisites.
- A foreign card ID, URL, archive membership or altered raw bytes must fail before output writes.
- Historical selected PDFs must use their captured card, never an unrelated latest-card pointer.
- A missing card or empty required field must produce an explicit status without fabricating data.
- Repeated builds must preserve inputs and produce identical IDs and reports.

## Task 1: Card-derived requisites in PDF compilation

**Files:**

- Modify `src/legal_rag/corpus/compiler.py`: validate captured card, attach requisites, replace the PDF-only OCR identity blocker, display card values.
- Create `tests/legal_rag/corpus/test_official_requisites.py`: authored archive/card/OCR replay with positive, missing-field, historical-binding and corruption cases.
- Modify `tests/legal_rag/corpus/test_ocr_owner_ast.py`: missing-card compilation expects its explicit source-metadata blocker.
- Update the source policy, task statement, result report, documentation index and nearest AGENTS instructions.

**Interfaces:**

- Consumes existing `corpus-input/1`/`2`, source items, archived asset metadata and extraction index; no new input fields.
- Produces optional `official_requisites` for PDF assets in normalized input and draft; existing owner trees remain unchanged.
- Status `official_card` means the four fields come from bound source evidence, not OCR verification or legal admission.

- [x] Write and run failing tests for card values despite unresolved OCR, optional title, missing fields, foreign/corrupt evidence and repeat builds.
- [x] Implement the smallest compiler change and confirm focused tests pass.
- [x] Replay retained scan inputs into a new ignored directory; verify unchanged source hashes, owner trees, deterministic repeats and the new statuses.
- [x] Update policy/task/result documentation with the superseding owner decision and measured limitations.
- [x] Run `pytest tests -q`, Ruff, M0 gate and `git diff --check`; obtain one fresh read-only review and resolve material findings.
- [x] Commit the completed item.

## Execution record

The initial 15 acceptance cases failed before implementation and passed afterward.
Three additional boundary cases pass. Final full suite: 1306 passed; Ruff and M0
78/78 passed. The 229-document replay preserves all trees/content hashes and 2064
source files, repeats 229/229 unchanged, and removes 159 OCR identity blockers while
retaining every other blocker. Fresh independent review found no issues.
Evidence: `data/requisites-20261103/card-policy-01/`. No rulings or deferred findings.
