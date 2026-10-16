# M1-01: fixture-to-draft contract and replay

**Implemented:** 2 October 2026. This is a diagnostic fixture path, not legal
parsing of the pilot acts, amendment reconstruction or corpus admission.

## Implemented boundary

`python -m legal_rag.corpus compile` validates `corpus-input/1`, reads immutable
source assets, checks a separate `processing-permission/1`, extracts UTF-8 plain
text and produces `text-extraction/1`, `legal-ast/1`, `edition-draft/1` and an
offline HTML report. No external dependency is required. JSON/HTML source
profiles and PDF/OCR extraction belong to M1-03/M1-04.

The input has two distinct kinds: `official_consolidated` (one snapshot) and
`original_amendments` (one original, zero or more separately identified
amendments). A bundle only produces diagnostic trees; it does not apply edits or
verify applicability. The fixture deliberately records an incomplete amendment
inventory and unverified dates.

A consolidated input may reference a frozen `edition-candidate/1` by path and
exact byte hash. The loader verifies its content ID, retained assets, source
items, reconciliation, relations and review attribution without rewriting the
candidate. A stale candidate cannot be wrapped. A separate permitted diagnostic
asset input can retain stale/rejected source status, source unresolved items and
the recorded admission blockers. It creates no `consolidates` relation and never
changes the frozen source handoff.

Paths to permission/candidate records and raw metadata resolve within the
declared archive root, including resolved symlinks. Archive root itself locates
the archive and may be relative to the input file. Asset hashes, membership,
identity, byte length, evidence URL and native byte locator are checked before
any output. Permission is hash-bound to the act and the exact assets being
extracted; its diagnostic scope is separate from legal admission.

The fixture parser first compares the declared identity with the first text
line. A match yields a stable identity draft, title and unique single-line
`Статья N. ...` nodes. Unknown identity, duplicate addresses and unsupported
lines remain unresolved. Blank lines are explicitly excluded as whitespace.
Every source character and UTF-8 byte is accounted for, with original CRLF/LF,
source hash and half-open character/byte spans. No cleanup is performed. These
rules are a fixture profile, not a general legal parser.

## Serialization and identity

JSON artifacts use UTF-8, sorted keys, two-space indentation and a final LF.
Content IDs use SHA-256 of compact sorted JSON with unescaped Unicode and no
non-finite numbers. The versioned [input fixture](../../../tests/legal_rag/corpus/fixtures/corpus_input_v1.json)
specifies the required fields. Unknown fields/versions fail closed.

`manifest_hash` excludes `archive_root`, itself and permission/candidate path
strings; their exact byte hashes remain included. Assets, target dates, blockers
and questions are sorted for hashing. Validated assets are ordered original or
consolidated first, then amendments by hash; source status is sorted by item ID.
Extraction IDs include source hash, extractor version/configuration and ordered
text. Draft IDs bind the validated input/evidence/permission, extraction/parser
versions, target date, content and blockers. No local absolute path, run UUID or
new wall-clock observation enters an ID. A different target produces a distinct
draft even when source text is identical.

Derived records are written atomically without replacing existing records.
Before writing, every destination is checked for conflicting bytes and path
escape into source or approved state. An exact repeat reports `unchanged` and
writes no content. A conflicting artifact fails visibly rather than being
repaired silently. The compiler never activates an approved build.

## Fixture provenance and reproduction

The [text](../../../tests/legal_rag/corpus/fixtures/sample_act.txt),
[metadata](../../../tests/legal_rag/corpus/fixtures/sample_act.json),
[permission](../../../tests/legal_rag/corpus/fixtures/processing_permission.json) and
input are project-authored synthetic fixtures, created on 2 October 2026;
redistribution is permitted. All dates, URLs and permission attribution are
fixture values, not an official act or an actual legal-review decision.
Raw text SHA-256:
`2a6ad78f04f0cb3c782ce899b77cd83849ed01bfb47f479274633cf60a19a1a6`.
Exact raw text and permission bytes are protected from Git newline conversion.

```powershell
$env:PYTHONPATH = "src"
python -m legal_rag.sources acquire-fixture --fixture tests/legal_rag/corpus/fixtures/sample_act.txt --metadata tests/legal_rag/corpus/fixtures/sample_act.json --data-dir data/m1
New-Item -ItemType Directory -Path data/m1/inputs,data/m1/reviews -Force
Copy-Item tests/legal_rag/corpus/fixtures/corpus_input_v1.json data/m1/inputs/fixture.json
Copy-Item tests/legal_rag/corpus/fixtures/processing_permission.json data/m1/reviews/fixture-permission.json
python -m legal_rag.corpus compile --input data/m1/inputs/fixture.json --target-date 2025-01-01 --output-dir data/m1
python -m legal_rag.corpus compile --input data/m1/inputs/fixture.json --target-date 2025-01-01 --output-dir data/m1
python -m unittest discover -s tests/legal_rag/corpus -p "test_*.py"
python -m unittest discover -s tests/legal_rag/sources -p "test_*.py"
python -m ruff check src tests
python -m compileall -q src tests
python docs/assets/generate_m0_gate.py
```

## Retained acceptance evidence

The actual CLI replay is retained under ignored `data/m1/`:

- Input: `inputs/fixture.json`; first/second CLI observations:
  `fixture-replay-first.json`, `fixture-replay-second.json`.
- Manifest hash: `5486e99e82ad2cb36a5410bda919de46ab268e075af9a245dc46fa5038f607ed`.
- Draft ID: `8311ca1a0663b3608eaef56e746d93a9a12e19ed1554b829fba7e72f288a8b70`;
  `drafts/<draft-id>/manifest.json`, `input.json`, `report.html`.
- Content hash: `0395b2cf868a7a5d673bd73fbfb463dc67ffba01025aba3a04fd835e6f7736be`.
- First/second compile results: `new`, `unchanged`; IDs and content hashes match.

Focused tests cover permission/version failures, asset corruption/removal,
identity conflict, path escape, wrong evidence, protected destinations,
immutable-output conflict, stale/rejected diagnostics, unchanged frozen
candidate bytes, source stale refusal, portable IDs, separate amendment trees,
unresolved identity, duplicate addresses, exact CRLF spans and HTML escaping.
The real five-act/date legal checks remain work for later slices.
