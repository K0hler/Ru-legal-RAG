# Housing HTML parser implementation plan

**Goal:** implement the approved source-aware HTML parsing design for the supplied Housing Code, as a diagnostic tool without edition admission or date reconstruction.

**Architecture:** reuse the existing native HTML tokenizer and whitespace mappings, expose a separate raw UTF-8 HTML extraction profile, and add a bound Housing Code identity/structure profile. Keep the existing 59-FZ compiler and frozen source adapters unchanged. Unknown or ambiguous content remains unresolved; standalone notes have document scope unless explicitly resolved in later work.

**Tech stack:** Python 3.13, standard library, existing unittest/pytest/Ruff; no new runtime dependencies.

## Tracer bullets

1. Add a synthetic extraction regression in `tests/legal_rag/corpus/test_housing_html.py`; observe missing module failure. Implement `src/legal_rag/corpus/housing_html.py` extraction with raw-file character offsets, paragraph classes/anchors, entities, breaks, superscripts and original text. Verify every token locator and cleanup mapping.
2. Add a literal expected-tree test for sections, chapters, superscript articles, parts, items, lettered subitems, sibling paragraphs and notes. Observe failure. Implement the bound identity and stack-based AST. Assert exactly-once token accounting and explicit note scope.
3. Add negative tests for identity conflict, duplicate addresses/anchors, unknown headings and numbering, unsupported tables/lists and multi-marker paragraphs. Observe failures before the corresponding guards. Verify unsupported content cannot leak invented addresses.
4. Add CLI/replay tests. Implement `python -m legal_rag.corpus.housing_html --input ... --output-dir ...` writing deterministic extraction/AST/validation JSON and inert offline HTML into a new or hash-identical output. Refuse conflicting existing outputs and input/output overlap. Keep this CLI separate from permission-gated admitted compilation.
5. Run the complete supplied HTML to a fresh local ignored diagnostic directory; verify against independent DOM heading/annotation controls, original hash, all token locators and independent repeat. Do not read closed gold. Inspect anomalies and fix with synthetic failing regression tests.
6. Run all corpus/source tests, Ruff, typing on the new module, bytecode compilation and M0 gate. Document actual measured results/limitations in `docs/HOUSING_HTML_PARSER.md`, link it from `docs/README.md`, update nearest AGENTS module knowledge and commit only authored code/tests/docs.

## Verification commands

```bash
PYTHONPATH=src python -m pytest tests/legal_rag/corpus/test_housing_html.py -q
PYTHONPATH=src python -m unittest discover -s tests/legal_rag/corpus -p 'test_*.py'
PYTHONPATH=src python -m unittest discover -s tests/legal_rag/sources -p 'test_*.py'
python -m ruff check src/legal_rag/corpus/housing_html.py tests/legal_rag/corpus/test_housing_html.py
python docs/assets/generate_m0_gate.py
```

The 12/21/243 source heading counts are controls, not independent proof of legal correctness of every nested parent. No target date is inferred from the filename; valid_from/valid_to remain unknown. Other legal HTML formats, PDF/OCR, tables, annexes and images are outside this bound profile.
