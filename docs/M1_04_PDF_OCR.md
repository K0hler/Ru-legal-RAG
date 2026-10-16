# Shared PDF/OCR extraction

M1-04 uses the owner-selected local dots.mocr pipeline already installed in
OCR-Lab. The Legal RAG host adapter uses Python 3.13's standard library; it does
not install inference packages, download weights, start containers or stop other
engines. The external container owns rasterization and inference. Keep its
image/model/configuration evidence with each run.

## Run

Copy `docs/assets/m1_04_ocr_config.example.json` to ignored
`data/m1/ocr.local.json` and set `lab_root`. Start Docker and OCR-Lab's dotsmocr
service explicitly. The adapter requires `running healthy`.

The example selects `picture_ocr_failure_policy: retain_unresolved`. This needs
the compatible OCR-Lab client change in [the retained patch](assets/ocr_lab_picture_policy.patch),
already applied to the local lab used for qualification. On another checkout,
check/apply it from the lab root with
`git apply --unidiff-zero --ignore-space-change <patch>`.
Use `strict` to retain the laboratory's original failure behavior. An incomplete
Picture response is never accepted as text: the selected policy preserves its
native response and an explicit unresolved-region finding.

In the current client, `retain_unresolved` also enables bounded Picture recovery
in the copied configuration: cancel a repeated stream after at least 128
characters with eight repeated tail units, then make at most one retry with
128-pixel padding. The original 28-pixel crop stays first, so successful date
OCR is unchanged. Keep every completed attempt before requesting another one.
If neither attempt completes, preserve the raw responses and unresolved region
and continue the document. Primary page OCR and the lab's strict default retain
their existing behavior. The retained patch includes this client support.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m legal_rag.corpus extract `
  --input data/m1/inputs/m1-04/sanpin-original-amendments.json `
  --ocr-config data/m1/ocr.local.json `
  --output-dir data/m1/ocr-run

.\.venv\Scripts\python.exe -m legal_rag.corpus compile `
  --input data/m1/inputs/m1-04/sanpin-original-amendments.json `
  --target-date 2025-01-01 `
  --extraction-index data/m1/ocr-run/extractions/index-<id>.json `
  --output-dir data/m1/ocr-run
```

The input is an existing `corpus-input/1` with retained PDF asset references and
exact diagnostic processing permission. `extract` is independent of a target
edition date. `compile` still requires an explicitly declared date. Hash-named
copies go into the configured lab's input directory; original archives and
previous OCR results stay unchanged. Every fresh OCR invocation uses a new
output directory. A missing runtime returns an actionable error and failed
receipt; the adapter does not silently use cached results.

## Replay without OCR

Create an ignored results map with exact PDF hashes and paths to saved native
result directories (relative to the map or absolute):

```json
{
  "schema_version": "ocr-results/1",
  "results": {"<source-sha256>": "../ocr-run/ocr-evidence/<evidence-id>"}
}
```

Pass `--ocr-results <map.json>` instead of `--ocr-config`. The mapping must cover
exactly the permitted PDF asset set, and each directory needs `document.json`
and `run.json`. Fresh runtime fingerprints survive replay through the retained
`provider-runtime.json`. An older standalone lab result without that sidecar
has no verified runtime fingerprint; importing it does not invent one.

## Outputs and boundaries

- `extractions/<id>.json`: versioned `text-extraction/1` with all selected
  physical pages, ordered source regions, text blocks, unknown source fields,
  table topology and image/text uncertainties. Full input extraction requires
  every source page.
- `ocr-evidence/<id>/`: original JSON/Markdown/page images/native responses,
  a file hash manifest and the provider fingerprint when available.
- `ocr-runs/<uuid>/`: execution status, runtime fingerprint and command log.
  Observational run receipts are separate from immutable content artifacts.
- `extractions/index-<id>.json`: exact input/permission binding and extraction
  references, revalidated before PDF compilation.

The client, prompt and model/Picture configuration are snapshotted under the
lab's `results/legal-rag-runtime/<profile-id>/` before execution. Overrides
change that copy only. Compilation re-normalizes the native evidence and
compares it with the declared extraction, in addition to checking file hashes.

`document_tree` is a physical document -> pages -> regions -> cells hierarchy.
The separate shared legal grammar can produce diagnostic nodes, but inferred
PDF legal structure remains `pdf_structure_unqualified`; sanitary-rules profile
qualification belongs to M1-06. No tree output grants legal admission.

Region boxes are pixels of the exact submitted image. A text span additionally
locates a string in `document.json` by JSON pointer and local Unicode offsets;
the grammar's global offsets are explicitly an OCR projection, never PDF bytes.
Cell boxes are `null` when the model only supplies HTML cell structure. Preserve
rowspan/colspan and blank cells; do not fabricate cell geometry or repair signs.

The normalizer does not copy volatile API IDs, timestamps or local source paths
into content identity. Real text, category or coordinate changes remain visible
and change extraction IDs. A cache replay is not evidence of fresh OCR
determinism. The existing OCR-Lab text reference says `human_review=false`.
The owner subsequently confirmed page 1 through a separate hash-bound record;
that decision does not confirm the remaining reference pages.

To replace dots.mocr, add a normalizer for the new engine and its execution
adapter/configuration. Consumers continue to read `text-extraction/1` and the
extraction index, without importing model-specific packages or JSON fields.

## Retained qualification

The [initial 16 October report](M1_04_QUALIFICATION_2026-10-16.md) records two complete
10-PDF / 103-page passes, the confirmed page-1 transcription, runtime/license
metadata, offline execution and native-route regressions. Its original scope
left fresh-output drift, table-sign errors and incomplete Picture OCR open.
The [subsequent owner-scoped acceptance](M1_04_ACCEPTANCE_2026-10-16.md) records
the implemented recovery and passing revised diagnostic scope. Legal admission
remains unresolved.

That report records the original acceptance scope. The owner subsequently
accepted round-seal text as noncritical and excluded the source-bound page-75
table from OCR quality grading. Fresh OCR is versioned; saved replay stays
deterministic. Supply `--acceptance-scope <quality-scope.json>` to the comparison
tool to apply that explicit owner record while preserving failed measurements.
Use `--comparison-kind saved_replay` for a saved-result replay; changed runtime,
models/configuration, missing provenance or changed replay content still block.

Explicit external-client checks (authored streams/images; no inference):

```powershell
.\.venv\Scripts\python.exe docs/assets/check_ocr_lab_recovery.py H:/AI_AGENT/OCR-Lab
```

To reproduce the read-only comparison into a new report directory:

```powershell
.\.venv\Scripts\python.exe docs/assets/verify_m1_04.py `
  --input data/m1/inputs/m1-04/sanpin-original-amendments.json `
  --first data/m1/pilot_runs/m1-04-seal-recovery-20261016-v1/fresh `
  --second data/m1/pilot_runs/m1-04-seal-recovery-20261016-v1/replay `
  --lab-root H:/AI_AGENT/OCR-Lab `
  --transcription-review data/m1/pilot_runs/m1-04-20261016-v1/human-transcription-review/human-review.json `
  --acceptance-scope data/m1/pilot_runs/m1-04-seal-recovery-20261016-v1/quality-scope.json `
  --comparison-kind saved_replay `
  --output-dir data/m1/pilot_runs/m1-04-report-replay
```

## Checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests/legal_rag/corpus -p test_pdf_extraction.py
.\.venv\Scripts\python.exe -m unittest discover -s tests/legal_rag/corpus -p test_ocr_runtime.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe docs/assets/generate_m0_gate.py
```

Default tests use authored saved results and a subprocess-boundary double; no
live network, Docker, model or closed retrieval gold is required.
