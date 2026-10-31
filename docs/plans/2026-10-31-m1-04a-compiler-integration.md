# M1-04A owner parser integration

**Goal:** Make ordinary PDF compilation consume the owner hierarchy developed after П23, preserving every source
fragment and retaining the independent-qualification blocker. User approved connecting this parser on 31 October.

**Scope:** Known development scans only; no reserved bodies, fresh OCR, new dependencies, source acquisition,
legal admission or Task 3 qualification. Work directly on main.

## Approach

Promote the existing algorithm into a standard-library-only production module, retaining the experiment script and
all frozen snapshots as historical baselines. The production module is the maintained implementation thereafter.
Convert its owners into `legal-ast/2` in a separate adapter. Point the compiler's PDF branch at that adapter; retain
the old `pdf_tree` diagnostic entry point for historical comparisons. Native/official JSON compilation is unchanged.
This avoids importing repository experiment files from installed production code or changing historical snapshots.

## Implementation and checks

1. Add authored tests for owner-preserving AST conversion, exact source accounting and locators, tables/images/noise,
   ambiguous owners, duplicate printed addresses, deterministic output and actual `compile_input` dispatch.
   Watch the tests fail before implementation.
2. Promote `docs/assets/ocr_logical_structure.py` (working SHA-256
   `ea7f4d95d7553b10cf34bd6f3ee52ace2ef9714038ea99abbe0991b16f1d3d38`) to
   `src/legal_rag/corpus/ocr_owner_structure.py`; reuse the existing authored rule tests against this maintained
   module and compare its output with the retained experiment. Add `ocr_owner_ast.py` for source-bound conversion
   and validation; change only the compiler's PDF dispatch. Unknown identity and inferred/missing boundaries remain
   visible, and every compiled PDF retains `pdf_structure_unqualified`.
3. Replay every one of the 237 development scans through the adapter, compare region owners against the saved
   prototype results, and verify no mutation, exactly-once text, physical-region/table preservation and stable hashes.
   Compile saved permitted development inputs twice and replay unchanged. Do not inspect any reserved act.
4. Run the full tests, Ruff, diff checks and M0 gate; review the change, update scoped AGENTS and the task map/report,
   then commit the connected route. Preserve prior outputs in new experiment directories.

## Review focus

- Hierarchy containers must not duplicate text owned by content leaves.
- Multi-page paragraphs keep separate source spans rather than a fabricated aggregate locator.
- Missing parents, unknown owners, duplicate printed numbers and unknown identity stay explicit.
- Tables keep nested topology and exact raw text; noise is retained with a reason.
- Tests of the old diagnostic parser must not be presented as tests of the new compiler route.

## Completed evidence

Connected on 31 October. All 237 known development scans retain identical owner proposals; 229 permitted inputs
compile twice with identical IDs and replay unchanged, and eight legacy scans pass adapter checks only.
After an HTML-only source-order correction, all 229 reports were rendered/replayed separately with source
order/locators checked. Final checks: 974 tests, Ruff, M0 78/78, diff checks and independent review.
160 documents retain unresolved identity; this connection does not qualify Task 3 or grant legal admission.
Details and retained artifacts: [connection report](../milestones/m1/04a/M1_04A_COMPILER_INTEGRATION_2026-10-31.md).
