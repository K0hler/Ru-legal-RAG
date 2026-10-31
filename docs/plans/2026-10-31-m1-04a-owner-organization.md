# Owner parser organization implementation plan

> **For agentic workers:** use `superpowers:executing-plans`; implementation is delegated to the assigned worker, followed by the parent's independent review. Leave changes unstaged for the parent's focused commit.

**Goal:** organize the maintained OCR owner parser without changing any parser result, rule, version or compiler behavior.

**Architecture:** retain `ocr_owner_structure.py` as the public `build(extraction)`, `VERSION` and CLI entry point, with explicit compatibility exports for existing callers. Move existing functions into the private `_ocr_owner` package and extract the existing orchestration stages without reordering their rules.

**Tech stack:** existing Python and standard library; no new dependencies.

**Scope:** the owner's 31 October 2026 request to organize the maintained parser. This does not change identity verification, source admission, the compiler adapter or frozen prototypes.

## Boundaries

- `model.py`: `Region`, `Marker` and `Paragraph` records.
- `text.py`: matching views and text/category predicates, captions, requisites and editorial-note recognition.
- `markers.py`: marker recognition, quotation/restart preparation and sequence depth solving.
- `paragraphs.py`: physical regions and logical paragraph joining.
- `scopes.py`: approving act, approved texts and annex scopes.
- `tables.py`: table/form boundaries and ownership helpers.
- `ownership.py`: body-owner refinement and footnote ownership.
- `ocr_owner_structure.py`: stage orchestration, source accounting, serialization, compatibility exports and CLI.

Dependencies point from orchestration toward these helpers; no wildcard imports or circular imports. Existing exported helpers used by the authored test suite remain available. Direct script execution and file-based prototype loading remain supported.

## Constraints and review focus

- Preserve `VERSION`, every output field/value, source order, joins, evidence order and token accounting.
- Keep `docs/assets/ocr_logical_structure.py`, frozen copies, `ocr_structure.py`, `ocr_owner_ast.py` and compiler code unchanged.
- Use only the 237 existing development extractions selected by `development_documents()`; do not open reserved Task 3 bodies, fetch sources or run OCR.
- Keep new local evidence in a new experiment directory. Do not repeat the costly full compiler replay without a specific concern.
- This is structural organization, with no measured speedup claim and no new qualification.
- Preserve first-pass freeze coverage after introducing a nested package: use recursive Python-file discovery in `run_m1_04a_first_pass.py`, with a synthetic check that a changed nested module is rejected before running. Existing freeze outputs stay unchanged. The historical native official-integration replay is outside this OCR change.

## Single implementation item

- [x] Regenerate M0 gate before implementation: `python docs/assets/generate_m0_gate.py` — 78 pass, no evidence problems, M1 allowed.
- [x] Move functions and constants by responsibility, preserving their bodies; extract scope/body/footnote stages and keep explicit compatibility exports.
- [x] Extend the current first-pass freeze to nested Python modules; verify the inclusion and pre-run refusal with the focused synthetic regression (RED: missing nested hash; GREEN: changed nested module rejected).
- [x] Verify full parser JSON equality against the retained prototype on all 237 development extractions; compare every document's metrics and complete error list with `20261031-owner-production-regression/`.
- [x] Run focused owner-rule/adapter tests (231 pass), the full suite (975 pass), Ruff, direct/module CLI checks, `git diff --check`, and regenerate M0 gate (78 pass).
- [x] Self-review the moved function bodies and module dependencies; update scoped instructions and record actual file sizes, checks and remaining limits in [the result report](../milestones/m1/04a/M1_04A_OWNER_ORGANIZATION_2026-10-31.md).
- [x] Independent reviewer and parent review the complete item: no findings; unchanged operations, acyclic imports, CLI and nested-freeze refusal confirmed.
- [x] Parent commits the complete item.

Existing tests supply the behavior-preserving refactor checks; no parser rule or behavior is being added. A regression is a defect to repair before delivery, not an accepted change to the baseline.
