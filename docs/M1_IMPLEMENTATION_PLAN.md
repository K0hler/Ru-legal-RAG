# M1 Implementation Plan: reviewable, dated legal editions

**Prepared:** 2 October 2026.
**Revised:** 16 October 2026: the owner accepted official source granularity and requested disabling reconstruction and closing M1-03A. The plan retains 16 slices, 13 milestone gates and ten legal admissions; the official-JSON acceptance contract is explicitly revised below.
**Status:** M1-01 through M1-03A are complete within their diagnostic engineering scope. M1-03A's current paired-JSON route imports the source tree verbatim; historical native grammar evidence remains separate. M1-04–M1-15 remain planned. No pilot edition is legally accepted by this document. Current decision/evidence: [M1-03A closure](M1_03A_CLOSURE_2026-10-16.md).
**Historical official-JSON reconstruction:** the `/4` and subsequent `/5` frozen cohorts each passed only **2/6** full controls; these failures are preserved in the [normalization report](M1_03A_OFFICIAL_NORMALIZATION_2026-10-16.md) and [transfer report](M1_03A_OFFICIAL_JSON_TRANSFER_2026-10-16.md). The owner-approved replacement is `official-json-import/1`, not a claim that those failed semantic-parser versions now qualify.
**Basis:** [PRD v0.2](PRODUCT_REQUIREMENTS.md), [source policy](LEGAL_SOURCES_POLICY.md), [master plan](LEGAL_RAG_MASTER_PLAN_2026.md), [frozen M0 contracts](M0_CONTRACTS.md).
**Task board:** [Legal RAG - M1](https://trello.com/b/45X665tC/legal-rag-m1). The initial 2 October publication had 15 slice cards, 62 slice acceptance items and 12 milestone gate items. The 13 October correction adds [M1-03A](https://trello.com/c/icH6oqSj), its acceptance checks and G13, and updates affected dependencies/checklists. Publication is not implementation or legal acceptance; verify live card state before updating it.
**Entry check:** the M0 gate was regenerated while preparing this plan: `pass`, 78/78 criteria, no evidence problems. Its recorded acceptance date remains 1 October 2026.

## 1. Outcome And Scope

M1 turns retained official materials into a reviewable Legal AST and, after a separate human legal decision, an immutable canonical build. It supports both a suitable official consolidated text and reconstruction from an original plus reviewed amendments. Acquisition state and raw assets remain read-only to the compiler.

The agreed pilot is the full text of all five acts, including tables and annexes:

| Act | Historical check | Control check | Required result |
|---|---|---|---|
| Housing Code of the Russian Federation (ЖК РФ) | `2025-01-01` | `2026-10-01` | Verified dated editions through an official snapshot or reconstruction |
| Government Resolution No. 354 (ПП РФ № 354) | `2025-01-01` | `2026-10-01` | Verified approving act, Rules, tables and annexes |
| Government Resolution No. 491 (ПП РФ № 491) | `2025-01-01` | `2026-10-01` | Verified approving act and all approved texts, with amendments reconciled |
| Federal Law No. 59-FZ (59-ФЗ) | `2025-01-01` | `2026-10-01` | Verified dated editions and explicit application conditions |
| SanPiN 2.1.3684-21 | `2025-01-01` | `2026-10-01` | Mandatory reconstruction from the original and a verified amendment bundle |

These are ten independent admission checks, not a requirement for ten different texts. Identical text may share content artifacts, but evidence and applicability must cover each date separately. Neither target date means "current today" or proves an interval between the dates.

Included: local CLI, versioned JSON, native text extraction, shared PDF/OCR, deterministic cleanup, identity and legal structure, human-confirmed amendment operations, date-specific reconstruction, a self-contained HTML review report, legal admission, measurements and a gate report.

M1 also delivers a shared `LegalStructureParser` with reusable act-type profiles: federal law, code, government resolution, and sanitary rules with their approving act. Reuse must be demonstrated on additional real acts outside the five-act pilot. These are engineering validation inputs, not additional dated-edition admission checks. Supported source formats and structure classes are explicit; M1 does not promise correct parsing of every legal document or automatic amendment interpretation.

Excluded: PostgreSQL/FTS and retrieval (M2), chunking, embeddings, LLM-based legal interpretation, universal amendment automation, a complete edition history, court-practice ingestion, continuous monitoring, a web service, React, queues, agents and import of other local projects. A known court-related admission blocker is not waived by this exclusion.

## 2. Starting Evidence And Missing Inputs

The following are retained M0 findings, not a new legal assessment of live sources. See [M0-10](M0_10_LEGAL_REVIEW.md) and [SanPiN source coverage](SANPIN_2_1_3684_21_SOURCE_COVERAGE.md).

| Act | Retained finding | First M1 input decision |
|---|---|---|
| Housing Code | Candidate identity/display checked; amendment and temporal coverage unresolved | Find evidence-backed snapshots for both dates or enumerate the reconstruction route |
| No. 354 | Candidate rejected: displayed revision does not establish the general text's date; territorial effects are separate | Replace the unsuitable input; distinguish general text, effective dates and territorial conditions |
| No. 491 | Candidate rejected/stale after discovery of Resolution No. 1242 | Reconcile that official publication and its effective-date evidence; acquire a suitable replacement and historical basis |
| 59-FZ | Candidate unresolved: amendment/temporal evidence, special application and a case-law-sensitive effect are incomplete | Establish both dated inputs and obtain an explicit decision on the existing admission blocker |
| SanPiN | Original plus nine located official amendments; no verified consolidated edition | Confirm completeness for both dates, identify missing publications, and review all relevant operations |

The existing consolidated-source adapters select a source-declared edition; they do not provide an implemented, verified historical-edition interface. Availability of a `2025-01-01` input is therefore a task, not an assumption. Prefer a suitable official historical snapshot for the four non-SanPiN acts when its coverage can be proved. Do not reverse a later text by guessing deleted wording.

Missing material is acquired through `sources`, using its archive/provenance lifecycle. If a historical selector is needed, verify the actual official endpoint and a retained response first, then make only that bounded connector extension with replay tests. Do not introduce a universal historical crawler. A failed search leaves a blocker; it does not reduce the five-act scope.

Processing permission and legal admission are different records. Rights/access uncertainty that prevents processing must be resolved before extraction. A permitted `rejected`, `stale` or `unreviewed` asset may produce a diagnostic draft, with its blockers intact. It must not be relabeled as an admitted edition or passed through the frozen handoff by disabling its checks.

## 3. Implementation Decisions

### Runtime And Persistence

- Keep the Python modular monolith and the existing `sources / corpus / retrieval` boundaries. Implement the CLI in `src/legal_rag/corpus/`; introduce files only when a slice needs them.
- Use Python 3.13, standard-library JSON, hashing, atomic file writes and `unittest`. Add external dependencies only for the qualified extraction engine; do not introduce a new package manager or service.
- Keep full documents, questions, reviewer records, extracted text, model caches and reports under ignored local data. Commit only permissible small fixtures with provenance and focused tests.
- Use deterministic UTF-8 canonical JSON and content hashes. Fix serialization, list ordering and hash inputs in M1-01. Wall-clock timings, local absolute paths and run UUIDs are observations, not content identity.
- Persist drafts separately from approved data. Compilation must not activate, overwrite or mutate a previously approved build. An approval command validates a separate decision bound to exact content/evidence hashes.

Planned local layout, not directories to pre-create now:

```text
data/m1/
  inputs/          versioned references to retained source archives
  extractions/     shared extraction records and source page previews
  drafts/          immutable draft ASTs, operation journals and reports
  reviews/         processing permissions and human legal decisions
  approved/        immutable canonical build manifests and payloads
  pilot_runs/      observations, repeat-run comparisons and measurements
```

Original bytes remain in their existing source archive. Paths resolve relative to a declared archive root; the raw SHA-256 is authoritative. Reject path escape, missing metadata, wrong length/hash or evidence pointing to another asset before building output.

### Shared Extraction Baseline

**Selected baseline for qualification, not a proven deployment:** Docling's standard PDF pipeline for layout and tables, with explicit RapidOCR ONNX and a pinned PP-OCRv5 Cyrillic recognition model/dictionary. Start on CPU. Preserve usable native PDF text; use OCR for scanned/failed text regions. Record the chosen mode per page. No `auto` engine selection, Tesseract fallback, VLM conversion or remote document processing.

This choice is grounded in primary documentation checked on 2 October 2026: Docling describes layout bounding boxes and TableFormer cell structure in its [model catalog](https://github.com/docling-project/docling/blob/main/docs/usage/model_catalog.md); its [OCR documentation](https://github.com/docling-project/docling/blob/main/docs/concepts/OCR_native.md) lists PP-OCRv5 Cyrillic support including Russian and English. Language aliases and configuration must be verified against the installed release, not guessed from model names. Use the engine's PDF rendering backend without application-side Poppler subprocesses.

M1-04 must select a released compatible version, pin dependencies, model revisions, weight/dictionary hashes and configuration, and verify all code/model/backend licenses and download/storage permissions. The upstream [package metadata](https://github.com/docling-project/docling/blob/main/packages/docling/pyproject.toml) declares Windows/Python 3.13 support; that is not proof of a working local installation or Russian legal OCR accuracy. Use an isolated environment without changing the current interpreter's global packages. Record install/model size and memory/time on the actual machine; GPU acceleration is optional only after a measured need.

If installation, table recovery, provenance or repeatability fails, retain the qualification report, keep affected slices blocked, and make an explicit plan decision before replacing the baseline. Do not silently fall back or expand into an OCR-engine comparison project. A small deterministic human transcription/correction record may resolve a specific reviewed region; it never changes the immutable source or hides the extractor error.

The shared result is our own versioned artifact, not a Docling object in the legal domain. `sources` consumes this artifact through a small reader; it does not import the heavy compiler/OCR runtime. Integration is an explicit staged CLI workflow: acquire PDF, extract it, then replay bounded discovery against the matching extraction. A missing extraction produces an actionable exception, not an inferred amendment target.

### Shared Legal Structure And Transfer Checks

**Owner-approved exception, 16 October 2026:** paired official JSON-tree + same-edition HTML uses `official-json-import/1`. Copy source rows/types/captions/levels/ranges, preserve all text/media and bind opaque source addresses. Do not infer canonical legal numbers, rebuild quoted articles/forms, recover omitted nodes or apply the reconstruction audit. Unknown source types are supported as source data. Missing/reversed/crossing ranges stay unchanged with visible integrity findings and review blockers; uncertain branches do not provide precise text ownership. The owner accepts source granularity. Repeated retained-input preservation controls establish this contract; they are not fresh heldout qualification. The reconstruction/heldout protocol below applies to formats that require inferred structure, including future PDF/OCR work. See the [PRD amendment](PRODUCT_REQUIREMENTS.md) and [closure](M1_03A_CLOSURE_2026-10-16.md).

Source-format adapters produce `text-extraction/1`; the shared structure engine consumes that artifact and an explicit act-type profile. Keep JSON/HTML decoding and PDF/OCR outside legal numbering and parent selection. Reuse ordered traversal, addresses, source mappings, accounting, exceptions and deterministic serialization across profiles. Profile rules describe a document family, never a particular act number, date, title, filename or source hash.

Extract identity fields from the document and compare them with the evidence-bound input claim before assigning addresses. The expected identity is input data, not a production-code constant. A new act within a supported family/format must use the same versioned engine and profile without code changes, act-specific configuration or per-document correction rules. Source-format differences require an explicit adapter, not another legal parser for each act. Unsupported or ambiguous content remains visible and prevents a claim of supported coverage.

For every declared family/source-format combination, retain full diagnostic runs on at least **two distinct non-pilot acts** not used to develop its rules. Different editions of one act, amendments to a pilot act, synthetic identity substitutions and fragments of one document do not count as different validation acts. Acquire official assets through `sources`, bind URLs/hashes and processing permission, and freeze engine/profile versions before parsing the validation bodies. This corpus is separate from closed retrieval gold; do not read closed questions or labels.

Validate full text/region accounting, extracted identity, numbering, sibling order, parent relationships, tables/annexes where supported, unresolved content and source locators against independently prepared structural controls. An output with all text unresolved, a false address/parent or an unresolved critical structure cannot pass. Run each full input twice with identical versions and compare content IDs/hashes. If a failure requires a rule change, retain the failed run, add a regression and use two other reserved acts to validate the new version; do not relabel development examples as transfer evidence.

Record the matrix of supported families/formats and validation assets in `parser-transfer-report/1`, with version/hash bindings, structural-control results, exceptions, repeat comparisons and explicit limitations. M1-03A owns the native profiles needed for all four original HTML inputs, including government resolutions. M1-06 and M1-09 extend qualification for the additional source formats and dated compilation in their scope. M1-14 reruns the complete matrix, and M1-15 rejects missing or failed mandatory evidence under G13. Engineering transfer success never grants legal admission.

### Minimal Persistent Contracts

These are decisions for M1; schemas and fixtures are introduced with their first consumer, not as a model-only framework.

| Record/version | Required semantics |
|---|---|
| `corpus-input/1` | `kind` = `official_consolidated` or `original_amendments`; act claim, target dates, archive references with official URLs/hashes, relations/evidence, processing-permission reference, retained admission blockers, unresolved questions and manifest hash |
| `text-extraction/1` | Source hash, extractor/config/model versions and hashes; ordered pages/blocks/text; original text locators; PDF coordinates and table cells; unresolved regions, extraction mode and available confidence, or null if unavailable |
| `legal-ast/1` | Identity decision and draft tree; explicit namespace for approving act versus approved Rules/annex; stable address keys, ordered nodes, source spans, cleanup/correction mapping, accounting and unresolved blocks |
| `amendment-ledger/1` | Original/AST hashes; each operation's source spans, target, expected-before hash, replacement payload, effective-date/condition evidence, dependencies, scope and human decision; complete amendment inventory and disposition |
| `edition-draft/1` | Input/extraction/parser/ledger hashes and versions, target date and scope, resulting tree, included/excluded/unresolved operations, lineage, content hash and blockers |
| `corpus-review/1` | Exact draft/evidence/ledger hashes, reviewer/role, decision, rationale, UTC time with offset, admitted date/scope and conditions, exception dispositions and independent decision when disputed |
| `corpus-build/1` | Immutable approved canonical payload references, review-decision hashes, supported act/date checks and explicit limitations; no unreviewed draft hidden inside approved output |
| `parser-transfer-report/1` | Declared act-family/source-format coverage; engine/profile/extractor versions and hashes; two distinct non-pilot validation acts per supported combination with permission/source/control bindings; structural results, exceptions and repeat comparisons |
| `m1-pilot-report/1`, `m1-gate/1` | Ten-check matrix, repeat comparisons, measurements and evidence-backed criteria; missing or unresolved mandatory evidence cannot produce `pass` |

Do not modify the meaning of `edition-candidate/1`. M1-01 consumes a valid non-stale frozen candidate where available, or uses the new diagnostic manifest for a retained asset/bundle. The latter has its own evidence/permission validation and does not impersonate a `consolidates` relation. Connector-specific `nd`, `rdk`, `baseid` and transport internals stay outside shared contracts.

Locator rules: PDF pages are 1-based; bounding boxes declare units, page dimensions and coordinate origin, then normalize to one documented convention. Native HTML/JSON text uses the raw asset hash, JSON pointer/text-node locator and half-open Unicode text offsets; do not invent physical page numbers or recover raw byte offsets from decoded character counts. AST text maps back through cleanup to extraction and raw evidence. Table cell locators include row/column and spans.

IDs separate stable act identity, address within an edition and provision identity in that edition. A renumbering gets explicit lineage rather than silently changing an old provision ID. Drafts are not legally admitted `LegalEdition` entities. Admission creates the canonical edition with evidence-backed applicability, not inferred validity from capture time or a displayed revision label.

### Date And Operation Rules

- The human-reviewed ledger defines replacement, insertion, deletion, renumbering and table/annex changes for this pilot. An operation is an exact transformation with preconditions, not an instruction for an LLM to interpret.
- Evaluate confirmed effective dates and conditions, including provision-level differences. Publication order/date alone does not determine applicability or operation order. Dependency order must be explicit and conflict-free.
- Define interval boundaries with the Legal Reviewer; store a documented convention and test the day before, on and after a reviewed effective date. Do not extrapolate approval to unreviewed dates or territories.
- Every located amendment and operation gets a disposition for each target: applied, not yet effective, outside the reviewed scope, superseded with evidence, or unresolved. Unknown date, ambiguous target, missing dependency, conflicting edits or an uncovered legal effect blocks the affected edition.
- Apply each eligible operation once. Validate expected-before content; preserve replaced/deleted text in the journal. For a renumbering, retain old/new addresses and flag affected references rather than automatically rewriting legal cross-references.
- Historical output excludes future-effective insertions, replacements, deletions and renumberings, even when published before `2025-01-01`. Report both the excluded operation and the historical wording it did not change.
- Unchanged output spans point to the original; changed spans point to the reviewed operation and official amending text. Derived quotations are labeled as such and expose all supporting spans, including the base text needed to understand an edit.

## 4. Delivery Order

AFK means engineering can implement and verify the slice independently; it never grants legal authority. HITL means a human lawyer acting as Legal Reviewer is required. The previously accepted reviewer assignment is retained; disputes need the independent second reviewer required by M0 policy.

| Slice | Type | Depends on | Retained deliverable |
|---|---|---|---|
| M1-01 | AFK | passing M0 gate | Versioned fixture-to-draft CLI and minimal report |
| M1-02 | HITL + bounded acquisition | M1-01 | Ten-check source/permission/coverage matrix |
| M1-03 | AFK | M1-01; permitted text input from M1-02 | Full 59-FZ diagnostic AST with native locators |
| M1-03A | AFK + structural review | M1-03; permitted native validation inputs | Shared structure engine, all four original native HTML inputs and native profile transfer evidence |
| M1-04 | AFK + reviewed transcription | M1-01; permitted PDF inputs from M1-02 | Qualified shared PDF/OCR extraction and runtime record |
| M1-05 | AFK + contract review | M1-04 | Discovery migration, M0 compatibility replay |
| M1-06 | AFK + structural review | M1-03A, M1-04; permitted SanPiN/validation inputs | Sanitary-rules profile, full trees and transfer evidence |
| M1-07 | HITL | M1-02, M1-06 | Reviewed SanPiN operations and date evidence |
| M1-08 | AFK | M1-07 | SanPiN reconstruction for both target dates |
| M1-09 | AFK + HITL | M1-02, M1-03A, M1-04, M1-08 | Government profile/transfer evidence, No. 354 dated drafts |
| M1-10 | AFK + HITL | M1-02, M1-05, M1-09 | No. 491 dated drafts, stale-source reconciliation |
| M1-11 | AFK + HITL | M1-02, M1-03A, M1-08 | Housing Code and 59-FZ dated drafts using shared profiles |
| M1-12 | AFK | M1-08 through M1-11 | Complete review report and hash-bound approval path |
| M1-13 | HITL | M1-12 | Ten legal admission decisions or explicit blockers |
| M1-14 | AFK + measured HITL | M1-03A, M1-05, M1-13; all profile transfer checks | Two-pass full pilot, transfer matrix and measurement report |
| M1-15 | AFK + acceptance decision | M1-14 | Evidence-backed M1 gate and M2 handoff |

Start M1-02 as soon as M1-01 finishes; missing inputs for one act do not prevent independent diagnostic engineering for another permitted input. A dependency on that inventory requires the verified route/permission for the act being processed, not resolution of unrelated rows. Record unresolved matrix rows instead of pretending every input route is complete. Implement and commit one engineering slice before starting the next; the table is not authorization to spawn agents or parallel development threads.

M1-03A is closed with the owner-approved official-tree import contract. The next slice is M1-04, physical PDF/OCR extraction qualification. Later slices reuse paired official trees where available; formats requiring inferred structure extend qualified profiles and keep their transfer checks.

For each completed slice: update its actual status here with the check and retained artifact path, update the nearest applicable `AGENTS.md`, run focused acceptance/regression checks, and make a focused commit on `main`. Never mark legal acceptance from an engineering test. Keep the plan rolling; change a later slice only when observed evidence warrants it.

## 5. Implementation Slices

### M1-01: Fixture To Reviewable Draft

**Type:** AFK. **Dependencies:** regenerated passing M0 gate. **Status:** implemented on 2 October 2026; diagnostic fixture only, no legal admission.

Implement the smallest complete corpus CLI path with a project-authored act fixture: validated `corpus-input/1`, one text extraction, an identity/structure draft, accounting, a minimal HTML report and repeated `new` then `unchanged`. Keep uncertain structure as an unresolved block. Only add the records used by this path.

Acceptance:
- A valid frozen `edition-candidate/1` can be wrapped without changing its bytes; a synthetic original/amendments manifest uses the separate kind/version.
- Missing permission, unknown version, corrupt/missing raw asset, conflicting identity, path escape and misbound evidence fail visibly. No failure mutates raw or approved state.
- Rejected/stale diagnostic inputs retain their status; the original source handoff still refuses a stale candidate. Unsupported text becomes visible unresolved content, not silent loss.
- Two CLI runs on retained `data/m1/` produce the same manifest/draft IDs and content hashes without duplicate content. The report opens offline and shows evidence and blockers.

Verify: new focused `tests/legal_rag/corpus/test_input_and_compile.py`, existing candidate-handoff tests, and retained fixture CLI replay. Full legal parsing and approval are not claimed here.

Implemented evidence: [contracts and replay](M1_01_FIXTURE_DRAFT.md), eight
focused offline corpus tests and retained `data/m1/fixture-replay-first.json` /
`fixture-replay-second.json` (`new` then `unchanged`, identical hashes/IDs).
The original source handoff and frozen fixture remain unchanged. M0 entry gate
was regenerated at implementation start: `pass`, 78/78, no evidence problems.

### M1-02: Establish The Ten Input Routes

**Type:** HITL plus bounded acquisition. **Dependencies:** M1-01. **Status:** completed input-route inventory on 12 October 2026, with the owner's accepted unresolved edition rows and diagnostic authorization. Ten rows, 463 evidence bindings, 27 newly acquired publications (`new` then `unchanged`), fresh two-pass pilot, six validated diagnostic compiler inputs and the actual `legal-reviewer-owner` 19-P decision are retained in [the closure report](M1_02_CLOSURE.md). Independent historical candidates replace the earlier missing-source state without claiming final applicability. Unfinished structure, operations, coverage/application review and all ten edition admissions remain explicit downstream blockers. The permitted 59-FZ control input is ready for M1-03.

Prepare a local inventory for every act/date: official text route, required originals/amendments, URLs/hashes, search coverage and known gaps, permission, date/territory evidence, responsible reviewer and original M0-10 decision. The human lawyer confirms completeness and legal evidence, not the engineer or extractor.

Acceptance:
- All ten matrix rows have a chosen route or an explicit unresolved blocker; SanPiN uses reconstruction for both dates.
- Nine located SanPiN amendments are checked for completeness, not treated as a closed list. Each newly required document is acquired and retained with the existing source lifecycle.
- Historical inputs are independently justified; a later consolidated snapshot is not silently reused. Any bounded historical-adapter extension has an official response fixture, acquisition replay and reviewed M0 contract impact.
- Permission to process and edition admission are separate. Legal Reviewer and owner explicitly address the retained 59-FZ case-law-sensitive blocker without inventing a court subsystem or silently reducing scope.

Verify: human-signed inventory/permission records and raw-hash validation for each usable route; new acquisitions show `new` then `unchanged`. An incomplete row remains blocked throughout later reports and the final gate.

### M1-03: Full Native-Text Diagnostic Path For 59-FZ

**Type:** AFK. **Dependencies:** M1-01 and a permitted retained text input. **Status:** implemented on 12 October 2026; full control-target diagnostic snapshot, no legal admission.

Extract the saved JSON/HTML response through its explicit source format profile (`redtext`, then HTML text nodes), perform recorded deterministic cleanup, build `ActIdentity` before the legal tree, and compile the entire retained 59-FZ text as a diagnostic snapshot.

Acceptance:
- Headers, articles, parts, numbered items, notes and nested provisions retain order and distinct addresses; unknown structure is unresolved, never inferred from legal meaning.
- Every source text node/character range is accounted for. Entity decoding, whitespace and line-wrap cleanup have mappings; headings and meaningful notes are not deleted as noise.
- Numbers and negations remain unchanged unless an explicit evidence-bound correction is recorded. Each provision opens the original text and its locator in the report.
- Golden-tree tests use small permitted/synthetic examples and reviewed expected structure, not the closed question set. The retained full-text build is repeatable and still carries M0 admission blockers.

Verify: focused extraction, cleanup, identity and AST tests plus two full retained builds. This is not yet the historical or control edition's legal approval.

Implemented evidence: [native profile, accounting and replay](M1_03_NATIVE_TEXT.md),
eight synthetic native tests and local `data/m1/pilot_runs/m1-03/verification-v4.json`.
Two independent full builds are byte-identical; a same-directory repeat is
`unchanged`. All 293 source tokens are accounted for, including all 18 articles,
50 parts, 21 numbered items and 24 notes, with no structural exceptions in the
retained text. The source archive, input permission, original blockers and
frozen fixture/handoff remain unchanged.

### M1-03A: Official Tree Import And Native Structure

**Type:** AFK plus structural review. **Dependencies:** M1-03, existing Housing Code HTML implementation and permitted native validation inputs. **Status:** closed on 16 October 2026 under the owner-approved source-preserving contract. Evidence: [closure](M1_03A_CLOSURE_2026-10-16.md). The 14 October native grammar acceptance and all later failed cohorts remain historical evidence in the [shared structure report](M1_03A_SHARED_STRUCTURE.md) and subsequent reports.

Current paired-source path: acquire and bind official HTML + structure JSON from the same edition, then import source nodes without semantic reconstruction. Source `unit`, `caption`, `lvl`, IDs and all additional fields remain unchanged. The initial four inputs (59-FZ, Housing Code, No.354 and No.491) remain mandatory regression inputs. Identity is evidence-bound input data, never an act-specific production selector. The previous native-only route stays compatible, and earlier drafts remain immutable.

Final implementation:
- [x] Disable the semantic adapter in the v2 compiler; import the official tree with `official-json-import/1`.
- [x] Preserve raw source rows, text/media, locators, parent/order relationships, identity, same-edition binding and processing permission. Accept unrecognized types and source granularity.
- [x] Record source-boundary defects without repairing them or assigning precise ownership to affected branches.
- [x] Replay the retained official cohorts twice, verify source/text/media independently and preserve all old outputs; confirm four v1 manifests remain byte-identical.
- [x] Run the complete test suite, M0 gate and review; record the explicit PRD/G13 contract change and closure evidence.

Historical native-engine implementation sequence (retained):
- [x] Add focused regressions in `tests/legal_rag/corpus/test_structure.py`: two different consistent act identities use the same profile; a conflicting identity stays unresolved; section/chapter/article/part/item numbering and superscripts preserve parents and source spans. Demonstrate the current act-bound failure before replacing it.
- [x] Introduce the common traversal/profile entry point in `src/legal_rag/corpus/structure.py`; adapt `native_text.py`, `housing_html.py` and `compiler.py` only where necessary to delegate structure. Keep profile rules together until a real separation is needed; no plugin framework, per-act modules or new runtime dependency.
- [x] Re-run retained 59-FZ and Housing Code inputs with the new version. Check semantic structure/locator equivalence, every source token/region, notes, unsupported content and immutable-output behavior; old IDs/hashes need not match a new parser version, but each version must repeat deterministically.
- [x] Freeze the native family/format matrix and profile versions; validate two other full federal laws and two other full codes using the transfer protocol above. Retain independently checked structural controls, failures, repeat comparisons and `parser-transfer-report/1` under ignored `data/m1/pilot_runs/`.
- [x] Support the native `/doctext` resolution inputs in the common pipeline and validate their approved-text/annex hierarchy, numbering, complete source accounting and table/formula/image handling. All four original retained HTML documents pass in `m1-03a-original-four-v8`; preparation-only or additional law/code runs cannot replace these inputs.
- [x] Run corpus regressions, frozen source/handoff checks and the M0 gate; update actual scope/status and nearest `AGENTS.md`, then commit the completed slice on `main`. Final evidence: 189 tests, Ruff, M0 78/78; `m1-03a-resolution-transfer-v5` passes the six-act native matrix.

Acceptance:
- Paired official JSON/HTML imports preserve every source row/type/caption/level, parent/order relationship, all text/media and evidence coordinates; the original four documents are included in the full retained regression set.
- No semantic reconstruction, type whitelist, inferred numbering, quote/form subdivision, automatic boundary correction or per-act production rules run on this route. Coarser source granularity is accepted by the owner.
- Actual source-integrity defects remain visible with unchanged source records and review blockers. A flagged branch is not a verified precise citation target. Unknown source types alone do not create defects.
- Binding, identity, permissions, determinism, immutable archives/old outputs and v1 compatibility pass. Diagnostic success never grants dated legal admission.
- Earlier parser/reader failures stay failed historical results. New-contract retained controls do not claim fresh heldout transfer; future inferred-structure formats retain their own G13 protocol.

Verify: `test_official_import.py`, all corpus/source/handoff tests, `docs/assets/validate_official_import.py <new-output-directory>`, four v1 manifest comparisons, Ruff and `python docs/assets/generate_m0_gate.py`. PDF/OCR and additional inferred-structure families remain the responsibility of M1-04/M1-06/M1-09.

### M1-04: Qualify And Retain Shared PDF/OCR

**Type:** AFK with human-reviewed transcription. **Dependencies:** M1-01 and permitted PDFs. **Status:** planned.

Qualify the selected extraction baseline on representative real pages: a scan, native text, an amendment target, a table with merged/multiline cells, and an annex boundary. Then extract every page of the retained 75-page SanPiN original and all required amendment PDFs. Add only the dependency/configuration artifacts needed for this path, including a pinned `requirements-corpus.txt` once qualification succeeds.

Acceptance:
- Record released package/transitive dependency versions, model/dictionary hashes, configuration, license checks, offline model reuse, actual runtime and memory. Installation and model download are separate from compilation.
- Produce `text-extraction/1` with page/region coverage, text, table cell topology, coordinates and uncertainties. Blank/image-only/failed pages cannot disappear from accounting. Human corrections stay separate and replayable.
- A reviewed page sample yields measured character/word error rates and a categorized list of critical numeral, negation and table errors. Confidence is diagnostic, never legal approval.
- Two fresh extractions with the pinned configuration are compared after defined canonicalization. A cache hit alone does not prove engine determinism. Unexplained output drift blocks qualification.
- Failed, corrupted or unsupported PDFs give structured exceptions and preserve prior artifacts. Focused default tests consume saved/synthetic extraction fixtures without downloading weights or requiring the OCR runtime.
- The retained `text-extraction/1` output feeds the M1-03A structure engine; extraction never embeds act-specific legal numbering or identity rules. PDF support is declared only for family/format combinations later validated through the same transfer protocol.

Verify: extractor contract/error tests, an explicit offline-with-models runtime smoke, fresh-run comparison and full-document extraction report. Do not invent an OCR accuracy threshold before this baseline; no unresolved critical error may reach approval.

### M1-05: Replace Discovery's Temporary OCR

**Type:** AFK plus reviewed contract change. **Dependencies:** M1-04. **Status:** planned.

Replace `_extract_pdf_pages` and its Poppler/Tesseract subprocess path with consumption of the shared extraction artifact. Add an explicit extraction-directory/reference argument for the staged discovery workflow. Missing or wrong-hash artifacts remain actionable exceptions until extraction and replay complete.

Acceptance:
- Bounded discovery for `2026-09-26` still finds the publication of Resolution No. 1242 from the feed, without a pre-known publication number, and derives its No. 491 target from official document text.
- The relation exposes the official PDF hash/page and shared extraction ID. Replay with prepared artifacts is idempotent; the stale candidate remains blocked after discovery and resync.
- Wrong source hash, absent page/locator and ambiguous target cannot create a trusted relation. `sources` does not import Docling or execute a corpus compiler implicitly.
- Remove obsolete application calls, specialized dependency checks/tests and active installation instructions, including relevant source-module/root README instructions. Preserve behavior-level discovery tests and historical M0 evidence; do not erase the audit trail.
- Follow the existing contract change rule: preserve the old baseline in Git, document the compatibility diff and replay, review any freeze update, then reassess M0. Do not merely regenerate hashes to conceal drift. An incompatible public event/handoff change needs a new version and migration.

Verify: source tests, both discovery stages on retained official PDFs, frozen candidate byte fixture, and regenerated M0 gate after the reviewed compatible update. No production monitoring is added.

### M1-06: Full SanPiN Base And Amendment Structure

**Type:** AFK plus structural review. **Dependencies:** M1-03A, M1-04 and permitted pilot/validation inputs. **Status:** planned.

Compile the original and amendment texts with the shared engine and a reusable sanitary-rules profile. Distinguish the approving resolution, the sanitary rules and their nine retained original annexes; verify actual document boundaries rather than assuming every annex is present. SanPiN 2.1.3684-21 is a pilot instance, not a hard-coded profile identity.

Acceptance:
- Full page/text accounting, legal numbering and order, table row/column/cell spans, units, footnotes and annex boundaries are visible. Repeated page headers are only excluded with an explicit service-text reason.
- Duplicate addresses in different approved texts do not collide. Identity/structure uncertainty blocks operation targeting while remaining visible in the draft.
- Reviewer-checked tree/table examples cover each observed structure class; all full documents, not only sample pages, undergo coverage reconciliation and exception review.
- A correction references exact source/extraction spans and records before/after values; no "cleanup" silently repairs a legal number or wording.
- Validate the sanitary-rules family on two distinct non-pilot acts for each declared input format, including supported annex/table structure, and extend `parser-transfer-report/1`. Reuse the shared engine rather than implementing a SanPiN-specific traversal.

Verify: SanPiN AST/table/accounting tests, complete retained compilation twice, and a structural review record. Structural review is necessary but not sufficient for dated legal admission.

### M1-07: Review The SanPiN Amendment Ledger

**Type:** HITL. **Dependencies:** M1-02, M1-06. **Status:** planned.

The human lawyer prepares/confirms the exact operations and their effective dates/conditions for both targets. Engineering may populate an operation proposal with locators, but cannot decide ambiguous wording or applicability.

Acceptance:
- Every required amendment is represented, including ones excluded on a target date. Every operation has official evidence, exact target/precondition, payload, reviewed ordering/dependencies and date/scope evidence.
- The ledger accounts for replacements, insertions, exclusions, renumbering and actual table/annex edits. Unsupported or conflicting operations remain unresolved and block the affected dated result.
- Human confirmation binds to the original/AST, operation payload and evidence hashes. A subsequent edit invalidates that confirmation; disputes require the independent second Legal Reviewer.
- The reviewer confirms bundle completeness separately for each date. Uncertain retroactive, provision-level or territorial effects are not reduced to a publication-date cutoff.

Verify: ledger schema/precondition/evidence checks and retained human decisions. This slice is not completed by generating an operation list alone.

### M1-08: Reconstruct SanPiN At Both Dates

**Type:** AFK. **Dependencies:** M1-07. **Status:** planned.

Replay the reviewed ledger from the immutable original to `2025-01-01` and `2026-10-01`. Produce both full edition drafts, a semantic/address diff, source lineage and an operation journal.

Acceptance:
- Each eligible operation applies once in the verified dependency order. Preconditions, overlapping edits, cycles, ambiguous/absent targets and unsupported changes fail closed without publishing a partial approved edition.
- Tests cover each operation type, future-effective changes published earlier, reviewed interval boundaries, unknown dates, scope exclusions, and renumbered/deleted targets used by later operations.
- Every operation has a per-date disposition. The historical edition retains the wording that future replacements/deletions would have changed; absence of a future insertion alone is not the whole temporal test.
- Both full outputs are reproducible from retained inputs without manual edits to generated text. Changed/unchanged/deleted spans have auditable lineage and before/after text.

Verify: reconstruction/temporal negative tests, two independent rebuilds per target and a review-ready diff. Legal approval still waits for M1-13.

### M1-09: Government Resolution No. 354 At Both Dates

**Type:** AFK plus HITL. **Dependencies:** M1-02, M1-03A, M1-04, M1-08. **Status:** planned.

Prefer the accepted same-edition official JSON-tree/HTML import where available. Use the retained native government-resolution profile only for inputs requiring inferred structure and qualify any new formats in this slice. Reuse common extraction/operation behavior and compile a suitable official snapshot or reviewed reconstruction for each date; No.354 is an input identity, not a parser rule.

Acceptance:
- Separate approving act, Rules and annex namespaces; preserve the complete text, tables, notes and ordering. Add focused golden-tree cases for newly observed structure only.
- The retained unsuitable snapshot's displayed date does not become verified coverage. The replacement route reconciles required amendments and explicit territorial/provision conditions with official evidence and human decisions.
- Both dates have full drafts, change dispositions, evidence-backed diff and repeated identical content hashes; historical coverage is independent of the current connector's selection.
- Freeze the government profile and validate two distinct resolutions outside the five-act pilot for each supported format; check approving act, approved texts, tables/annexes and numbering under the shared transfer protocol.

Verify: No. 354 profile/temporal tests and retained full-text builds for both dates. Unresolved general-versus-territorial coverage remains an admission blocker.

### M1-10: Government Resolution No. 491 At Both Dates

**Type:** AFK plus HITL. **Dependencies:** M1-02, M1-05, M1-09. **Status:** planned.

Reuse the government profile from M1-09 without No. 491-specific parser rules, and reconcile the discovered No. 1242 amendment and every other required change against suitable inputs for both target dates. A new structural class requires a reviewed family-profile extension and renewed transfer evidence; identity differences alone require no code change.

Acceptance:
- Old stale/rejected input remains historical diagnostic evidence. New acquisition and legal review, not a flag reset, establish a replacement route.
- Review determines the discovered amendment's target and actual applicability to each target date; publication/discovery alone does not authorize applying it.
- All approved texts/annexes are accounted for. Both full dated drafts rebuild deterministically and explain their included/excluded changes and differences.

Verify: retained discovery-to-new-input regression, No. 491 profile/effective-date tests and two builds for each date. Frozen source handoff still rejects the old stale candidate.

The 12 October M1-02 acquisition now supplies an official 26.09.2026 candidate
including No. 1242. Prefer that newly acquired source when its dated coverage is
verified; keep the original 01.09.2025 candidate rejected/stale. See
[source hashes and comparison](M1_02_CLOSURE.md).

### M1-11: Housing Code And Dated 59-FZ

**Type:** AFK plus HITL. **Dependencies:** M1-02, M1-03A, M1-08. **Status:** planned.

Complete the remaining four act/date checks using the accepted official JSON-tree/HTML route where available, or qualified native profiles for inputs requiring inferred structure. No Housing Code/59-FZ identity constants select production behavior. Prefer proved official historical snapshots; use the reviewed operation path only where needed. Diagnostic structure is prior engineering evidence, not completion of these dated-edition checks.

Acceptance:
- Complete texts, numbering (including inserted article numbers), nested provisions, notes and references preserve identity and source locators. New parser rules have small tests and retained full-text validation.
- Both routes reconcile date-specific amendments and application conditions; a matching displayed date or text comparison is not alone an admission decision.
- The existing 59-FZ special-application/case-law-sensitive issue has a specific, evidenced human disposition or remains a blocker. Do not bypass it by declaring court practice outside scope or suppressing affected text.
- Full dated drafts and explainable diffs exist for both acts; repeated builds match. If text is identical, separately prove coverage for both dates.
- Any new source format or structural rule extends the relevant family/format matrix and repeats its two-act transfer checks. A later pilot run cannot rely on transfer evidence from a different parser/profile version.

Verify: code/federal-law profile tests, full retained builds and explicit applicability records. No court-practice module or arbitrary scope reduction is introduced.

Reuse the evidence-bound 12 October M1-02 human decision for the 19-P-after-80-FZ
classification; it is not a runtime relation import or approval of a complete
dated edition. Do not repeat that decision for unchanged evidence and scope.

### M1-12: Complete Review Report And Approval Boundary

**Type:** AFK. **Dependencies:** M1-08 through M1-11. **Status:** planned.

Complete the initial report for full-structure, source reconciliation, two-date diff, table/annex inspection, operation evidence and exception decisions. Implement importing a human review record and publishing an immutable `corpus-build/1` only after hash/scope/gate validation.

Acceptance:
- Report contains the full text/tree, original evidence and review-needed page previews/crops, declared versus verified dates, per-document accounting, amendment dispositions, before/after edits and original M0/new M1 decisions separately.
- It opens offline without CDN/network dependencies; quote/source locators can be inspected without another service. Raw originals remain separately hash-addressed. Measure report size rather than substituting external links for review evidence.
- Source text and URLs are untrusted data: escape markup and validate link schemes. Malicious source HTML cannot execute scripts, issue requests or masquerade as reviewer actions.
- Approval requires the proper human role, matching hashes/date/scope, no unresolved critical blocker and an independent decision for disputes. Missing, wrong-hash, stale-decision and rejected records cannot publish approved data.
- Canonical approved payload/provenance is immutable; failed publication leaves the last approved build unchanged. Review observations do not alter deterministic draft identities.

Verify: report escaping/offline rendering and approval failure/atomic-write tests; inspect a long text, table, reconstruction and unresolved report in the browser at desktop and narrow widths. A successful technical approval fixture is not real legal admission.

### M1-13: Legal Admission Of All Ten Checks

**Type:** HITL. **Dependencies:** M1-12. **Status:** planned.

The human lawyer examines full coverage, critical extraction/structure errors, identity, amendment completeness, operations, effective dates, applicability and evidence. Record decisions against the exact report/draft hashes, with actual review and exception-handling time.

Acceptance:
- Every mandatory act/date has its own admitted scope or explicit rejection/unresolved reason. All ten need positive legal admission for the baseline M1 gate; technical completion or a partial success cannot waive this.
- Table values, units, negations, deleted/replaced text, numbering and excluded future changes are checked against official evidence. A sample-only check cannot establish full-document completeness.
- Reopening an M0 blocker records the new evidence and human rationale; the old decision is not overwritten. Engineering disputes go to the independent second Legal Reviewer.
- The 15 working gold questions may test whether evidence/addresses remain traceable. Their existing labels are snapshot evidence, not approval of a new edition or both dates; disagreements get legal review. Do not read/tune on the 15 closed queries or labels in M1.

Verify: hash-bound human review records, ten-check admission matrix and exception dispositions. If a required check is unresolved, report the blocker and continue permissible independent work; M1 is not accepted.

### M1-14: Two-Pass Pilot And Measured Cost

**Type:** AFK plus measured HITL. **Dependencies:** M1-03A, M1-05, M1-13 and all profile transfer checks. **Status:** planned.

Run the full retained five-act/two-date workflow through the real CLI, not only temporary tests. Publish the reviewed canonical build, repeat with identical inputs/versions/decisions, and retain comparisons and measurements.

Acceptance:
- All ten checks reference approved immutable payloads and actual legal decisions. Second run reports unchanged content, identical IDs/hashes and no duplicate raw/derived content; run observations may be new.
- Measure acquisition separately from extraction/OCR, compilation, reconstruction, report generation, review and exception resolution. Record page/asset/provision counts, exceptions, OCR modes, elapsed time, peak RAM/VRAM where measured, output/model sizes and monetary cost or `not_applicable` with rationale.
- Record cold/fresh and cached paths distinctly, sample counts and hardware/runtime. Do not present cache latency as OCR speed, derive p95 from two runs, or reuse the accepted M0 timing placeholders as M1 measurements.
- Inject a failure after a previously approved build and prove that raw files, approved payloads and any published-build pointer remain unchanged. Reverify shared-discovery evidence and the source contract replay.
- Re-run the complete transfer matrix with the same final engine/profile versions used for the pilot: two distinct non-pilot acts per supported family/format, independent structural controls and identical repeated content. Measure engineering validation separately from the ten legal admission checks; preserve diagnostic status of validation documents.

Verify: retained `m1-pilot-report/1`, machine-readable repeat comparisons, measured reviewer records and focused failure/replay tests. Set further numeric performance targets only after reviewing this measured baseline.

### M1-15: Gate Report And M2 Handoff

**Type:** AFK plus acceptance decision. **Dependencies:** M1-14. **Status:** planned.

Implement `docs/assets/generate_m1_gate.py`, tracked criterion/contract records and `docs/M1_GATE_REPORT.md`, following the evidence-driven M0 reporting pattern. Preserve private source/review content under ignored data; the tracked report contains only permissible summary/reference/hash data.

Acceptance:
- Every criterion below is rendered with `pass`, `fail` or `unresolved`, evidence references/hashes and a rationale. Missing/corrupt evidence, a missing act/date, scope mismatch or legal blocker prevents `pass`; exit `2` blocks M2.
- Checks bind the report to input/schema/extractor/parser/model versions, exact approved build and review hashes. Negative tests demonstrate that deleting a mandatory review or altering an asset invalidates acceptance. G13 validates the current route-specific contract: missing preservation evidence rejects official-tree import; missing/failed heldout evidence, development acts relabelled as heldout, or parser/profile drift rejects inferred-structure qualification.
- Closed gold content is not deserialized; if continuity requires its hash, read bytes only. M1 does not run a closed retrieval evaluation without a retrieval system.
- M2 receives only `corpus-build/1` approved entities/provisions, evidence locators, supported date/scope and review references. No database or retrieval implementation is added to prove this handoff.
- Update actual component status and plan completion after evidence passes. Owner records milestone acceptance; a request to reduce scope requires an explicit earlier PRD/criterion change, not a post-hoc waiver.

Verify: offline gate positive/negative tests, regenerated M0 compatibility gate, full M1 gate and retained approved-build load/replay. No automatic transition to M2 implementation in this slice.

## 6. CLI And Verification Contract

`compile` is implemented for the M1-01 UTF-8 diagnostic fixture and M1-03 saved `redtext` JSON/HTML profile. The separate Housing Code HTML CLI is diagnostic. Shared act-type dispatch belongs to M1-03A; `extract`, `approve` and `run-pilot` below remain planned. Implement commands only in the slice that owns their behavior. Use existing `sources` commands for acquisition; do not duplicate them in corpus.

```powershell
$env:PYTHONPATH = "src"

# M1-01 onward: input references immutable retained assets.
python -m legal_rag.corpus compile --input data/m1/inputs/<manifest>.json --target-date 2025-01-01 --output-dir data/m1
python -m legal_rag.corpus compile --input data/m1/inputs/<manifest>.json --target-date 2026-10-01 --output-dir data/m1

# M1-04 onward: shared artifact producer, also usable before discovery replay.
python -m legal_rag.corpus extract --input data/m1/inputs/<manifest>.json --output-dir data/m1

# M1-12 onward: consumes an explicit human decision, never creates it.
python -m legal_rag.corpus approve --draft data/m1/drafts/<draft-id>/manifest.json --review data/m1/reviews/<decision>.json --output-dir data/m1

# M1-14 onward: compare all ten retained builds with the first pass.
python -m legal_rag.corpus run-pilot --inputs data/m1/inputs/<pilot>.json --output-dir data/m1
```

`compile` verifies that the requested target is declared in the input; it never defaults to today's date. It reuses matching extraction artifacts or performs explicit extraction if the runtime is available. The pilot runs both targets regardless of any identical text. Success output exposes result, deterministic ID, absolute artifact/report paths and blockers; legal blockers remain visible in a successfully produced diagnostic draft.

Current M0 checks (runnable now):

```powershell
python -m unittest discover -s tests/legal_rag/sources -p "test_*.py" -v
python docs/assets/generate_m0_gate.py
```

Implemented M1-01 checks:

```powershell
python -m unittest discover -s tests/legal_rag/corpus -p "test_*.py" -v
```

Future M1 milestone check, once its file exists:

```powershell
python docs/assets/generate_m1_gate.py
```

Default tests are offline and weight-free, using versioned extraction fixtures. Qualified OCR runtime smokes and retained full-pilot tests are explicit separate checks. Measure genuine fresh extraction twice separately from cache/idempotency replay. Use project-authored temporal fixtures for boundary/error tests and reviewer-confirmed full pilot outputs for acceptance; neither replaces the other.

Text accounting has two layers: every source page/region/text node is located or explicitly unresolved/excluded, then every extracted text range is reconciled through cleanup into AST or a documented exclusion. A blank OCR result cannot prove a page was blank. 100% accounting does not imply 100% accurate OCR; unresolved critical text/table evidence still blocks approval.

## 7. M1 Gate Criteria

These thirteen criteria operationalize PRD section 10. G13 records the 13 October parser-transfer requirement and the explicit owner-approved 16 October official-tree contract amendment; the ten legal admission checks are unchanged. M1-15 expands the current criteria into evidence checks, not new discretionary quality thresholds.

| ID | Criterion | Principal evidence/slices |
|---|---|---|
| G01 | All five full acts at both dates have positive legal admission with explicit applicability | M1-02, M1-09 through M1-14; ten-check matrix and review hashes |
| G02 | SanPiN is reconstructed and legally approved for both dates | M1-06 through M1-08, M1-13; bundle, ledger, full drafts and decisions |
| G03 | 100% source/extracted-text accounting for every input, including tables/annexes and removed/replaced text | M1-03, M1-04, M1-06, M1-09 through M1-13; accounting and journals |
| G04 | Identical inputs/versions produce identical content IDs/hashes and no duplicate content | M1-01, M1-04, M1-08, M1-14; fresh extraction and repeated builds |
| G05 | Structure, order, numbering, tables and annex boundaries are reviewable and checked | Profile golden trees, full-coverage reconciliation and structural review |
| G06 | Every resulting span has original/operation provenance down to official source coordinates | Extraction/cleanup mappings, source hashes, lineage and report |
| G07 | Amendment completeness, target dates and conditions are confirmed; critical unresolved issues cannot enter admitted scope | Input inventory, reviewed ledger, dated decisions and exception dispositions |
| G08 | Historical output excludes all future-effective change types and explains its diff with the control output | Temporal tests, both full editions, per-date amendment dispositions and review |
| G09 | Critical errors, misbound evidence and invalid decisions block approval without damaging prior approved data | Approval negative tests and retained failure-after-approval replay |
| G10 | Self-contained review report supports independent text/operation/date/evidence inspection | Offline report checks, reviewer record and escaping tests |
| G11 | Actual compilation/OCR, review and exception costs are measured, with run context and limitations | M1-04, M1-13, M1-14 measurement records |
| G12 | Bundle input is versioned/replayable; shared extraction replaces temporary OCR and preserves M0-10A behavior | Contract fixtures, discovery replay, reviewed freeze change and M0 reassessment |
| G13 | Paired official JSON/HTML preserves the source tree/text/media with bound locators, visible integrity defects and repeatable builds under the owner-approved 16 October contract. Formats requiring inferred structure pass two distinct non-pilot acts per declared family/format without code changes, act-specific rules or unresolved critical structure | M1-03A closure and `official-import-replay/1`; M1-06, M1-09, M1-11, M1-14 retain final-version transfer reports for inferred structure. The milestone-wide gate remains open until those slices and final pilot checks finish |

A missing required source, unresolved rights, unknown legal date/condition, unsupported critical structure/edit, disputed legal decision or absent reviewer evidence blocks the relevant check and therefore M1 acceptance. Engineering tasks can progress independently, but no partial success is called a complete five-act pilot.

Missing or failed mandatory transfer evidence also blocks M1 acceptance and the M2 handoff. Success on the five pilot acts alone cannot satisfy G13, and passing transfer checks cannot substitute for their ten legal admissions.

## 8. Effort And Stop Conditions

Do not give a fixed calendar promise before seeing the historical inputs and OCR/operation inventory. The largest uncertainties are acquisition of usable historical text, SanPiN/table accuracy, number/dependencies of reviewed edits and legal review of the full documents, not the number of CLI commands.

Re-estimate after M1-02 (input routes/gaps), M1-04 (pages, speed, errors and runtime), and M1-07 (operations and human-review effort). Each estimate separates engineering, acquisition/permissions, human legal work and unresolved blockers. The accepted M0 review-time deviation is historical and does not excuse new M1 measurement.

The 13 October revision adds real-document acquisition, structural controls and transfer runs; include their engineering/review effort separately, and re-estimate after M1-03A. Do not reuse the earlier five-act estimate as if these checks cost nothing.

If the shared OCR baseline is unsuitable, stop its integration and record the replacement decision. If a historical basis cannot be obtained, keep that act/date unresolved. If the known case-law-sensitive issue cannot be resolved within the approved boundary, take the specific evidence and scope decision to the human reviewer/owner; do not invent approval. If the full five-act gate becomes infeasible, only an explicit new owner decision can change the PRD before acceptance assessment.

**Next native-parser task:** address the independent official-JSON transfer failures with shared rules, preserve the failed cohort, then qualify the frozen new version on reserved acts. The four original native inputs and historical native matrix already have their recorded acceptance; the new route's 2/6 is not closure. M1-02's unresolved legal evidence remains blocked for final acceptance. This document grants no legal approval or M2 transition.
