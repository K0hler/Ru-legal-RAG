# Legal RAG documentation

Start with the [product requirements](overview/PRODUCT_REQUIREMENTS.md),
[master plan](overview/LEGAL_RAG_MASTER_PLAN_2026.md) and current
[M1 implementation plan](milestones/m1/M1_IMPLEMENTATION_PLAN.md).
Completed engineering slices do not imply legal admission of editions.
Experiment reports retain the results and limitations of their own dated runs.

| Folder | Contents |
|---|---|
| [overview/](overview/) | Product scope, architecture, roadmap and terminology |
| [policies/](policies/) | Source-admission policy |
| [milestones/m0/](milestones/m0/) | Acquisition plan, reviews, gold metadata and frozen gate records |
| [milestones/m1/](milestones/m1/) | Corpus plan and implementation records; parser history in `03a/`, OCR in `04/` |
| [guides/](guides/) | Setup and usage of implemented diagnostic tools |
| [research/](research/) | Literature, source research and earlier architecture proposals |
| [plans/](plans/) | Individual implementation and experiment plans |
| [assets/](assets/) | Diagrams, generators, validators, examples and offline viewers |

## Overview

- [Product requirements](overview/PRODUCT_REQUIREMENTS.md)
- [Master plan and target architecture](overview/LEGAL_RAG_MASTER_PLAN_2026.md)
- [Project atlas](overview/PROJECT_ATLAS.md) — dated project snapshot.
- [Target pipeline](overview/PIPELINE.md)
- [Glossary](overview/GLOSSARY.md)

## Policies

- [Official-source admission policy](policies/LEGAL_SOURCES_POLICY.md)
- The M0 pilot-specific review policy is retained with the [M0 records](milestones/m0/M0_07_PILOT_AND_REVIEW_POLICY.md).

## M0: acquisition and frozen contracts

- [Implementation plan](milestones/m0/M0_IMPLEMENTATION_PLAN.md)
- [Pilot and review policy](milestones/m0/M0_07_PILOT_AND_REVIEW_POLICY.md)
- [Legal review decisions](milestones/m0/M0_10_LEGAL_REVIEW.md)
- [Gold-set review](milestones/m0/M0_11_GOLD_SET.md) and [tracked split metadata](milestones/m0/M0_11_GOLD_SPLIT.json)
- [Gate report](milestones/m0/M0_GATE_REPORT.md) and [assessment](milestones/m0/M0_GATE_ASSESSMENT.json)
- [Frozen contracts](milestones/m0/M0_CONTRACTS.md) and [hash manifest](milestones/m0/M0_CONTRACT_FREEZE.json)
- [Documentation relocation receipt](milestones/m0/DOCUMENTATION_RELOCATION_2026-10-16.json) — old/new paths and hashes; acceptance criteria and decisions are unchanged.

The gate command remains `python docs/assets/generate_m0_gate.py`.

## M1: corpus compilation

- [Implementation plan and milestone gates](milestones/m1/M1_IMPLEMENTATION_PLAN.md)
- [M1-01: fixture draft and contracts](milestones/m1/M1_01_FIXTURE_DRAFT.md)
- [M1-02: input routes](milestones/m1/M1_02_INPUT_ROUTES.md)
- [M1-02: closure](milestones/m1/M1_02_CLOSURE.md)
- [M1-03: native-text extraction](milestones/m1/M1_03_NATIVE_TEXT.md)

### M1-03A: legal structure and official JSON

Read the [accepted closure](milestones/m1/03a/M1_03A_CLOSURE_2026-10-16.md)
for the current official-JSON contract. The earlier reports below preserve
development failures, experiments and superseded approaches.

- [Shared native structure engine](milestones/m1/03a/M1_03A_SHARED_STRUCTURE.md)
- [Official structure integration](milestones/m1/03a/M1_03A_OFFICIAL_STRUCTURE_INTEGRATION_2026-10-15.md)
- [Independent structure audit](milestones/m1/03a/M1_03A_STRUCTURE_AUDIT_2026-10-15.md)
- [Structure-gap analysis](milestones/m1/03a/M1_03A_STRUCTURE_GAP_TRIAGE_2026-10-15.md)
- [Parser handoff snapshot](milestones/m1/03a/M1_03A_PARSER_HANDOFF_2026-10-15.md)
- [Parser options research](milestones/m1/03a/M1_03A_PARSER_OPTIONS_2026-10-15.md)
- [Documind experiment](milestones/m1/03a/M1_03A_DOCUMIND_EXPERIMENT_2026-10-15.md)
- [Official structure experiment](milestones/m1/03a/M1_03A_OFFICIAL_STRUCTURE_EXPERIMENT_2026-10-15.md)
- [Official JSON transfer qualification](milestones/m1/03a/M1_03A_OFFICIAL_JSON_TRANSFER_2026-10-16.md)
- [Official JSON normalization](milestones/m1/03a/M1_03A_OFFICIAL_NORMALIZATION_2026-10-16.md)
- [Offline source/JSON/failure viewer](assets/official-json-visual-review-20261016/index.html)

### M1-04: local PDF/OCR

- [Setup and saved-result replay](milestones/m1/04/M1_04_PDF_OCR.md)
- [Accepted engineering scope and recovery](milestones/m1/04/M1_04_ACCEPTANCE_2026-10-16.md) — current acceptance with explicit owner exceptions.
- [Initial qualification](milestones/m1/04/M1_04_QUALIFICATION_2026-10-16.md) — historical failures before the agreed exceptions.
- [Region probes](milestones/m1/04/M1_04_REGION_PROBES_2026-10-16.md) — bounded diagnostic experiments.

### M1-04A: universal OCR structure parser

- [Plain-language problem brief](milestones/m1/04a/M1_04A_PROBLEM_BRIEF_2026-10-19.md) — standalone Russian explanation for readers outside the project: purpose, failure causes, tool results and remaining work.
- [Task and experiment plan](plans/2026-10-17-m1-04a-ocr-structure.md) — in progress: existing OCR files, additional official documents, reusable legal hierarchy and independent transfer checks. M1-06 consumes the resulting parser for full SanPiN coverage.
- Data layout: new M1-04A originals, OCR, gold and experiments live under local `data/m1/m1-04a/` (see `data/AGENTS.md`); `assets/build_m1_04a_catalog.py` rebuilds the hash-verified document copies.
- [Cycle 2 plan](plans/2026-10-21-m1-04a-cycle-2.md) — prototype v1 fixes for named law units, attached-document captions and requisites (16 development documents, no regression), then pool batch 2 without the single-edition filter (longer, amended acts and codes), blind Codex gold and first-pass run.
- [Pool batch 1 plan](plans/2026-10-21-m1-04a-pool-batch-1.md) — metadata-only random selection of 8 diverse unamended acts, OCR by the executor, frozen first-pass run. The planned automatic gold from official pravo.gov.ru trees was replaced (owner, 21.10.2026) by agent (Codex) annotation of OCR region text, frozen before the run.
- [Pool batch 1 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_1_2026-10-21.md) — frozen `code-final` prototype on 8 new acts with agent-annotated gold, scored under annotation convention v1 (Picture regions excluded): 226/333 (67.9%) vs current `/7` 89/333 (26.7%, refuses 6/8 acts); all 363 regions: 237 vs 91. Continuation not independently measured; error classes, selection biases, 30-region [gold sample](milestones/m1/04a/M1_04A_POOL_BATCH_1_SAMPLE_2026-10-21.md). Not G13/Task 3.
- [Prototype v1 development report](milestones/m1/04a/M1_04A_PROTOTYPE_V1_2026-10-21.md) — Russian owner report: frozen `ocr-logical-structure/1-experiment` fixes named law units, attached-document captions and requisite blocks; 1182/1182 on the 16 development documents (batch 1: 226 → 333 of 333). Development result, NOT progress; the real measure is batch 2. Known limitations listed.
- [Annotation convention v1](milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v1.md) — versioned owner-gold rules for the check pool: scored OCR categories (not Picture/noise), signatures and page marks, `+`, `owner-path/2`, designation aliases, approved text ≡ annex, blind annotator input without stage-2 output.
- [Logical-text layer plan](plans/2026-10-20-m1-04a-logical-text.md) — stage 2 in production: `logical-text/1` over `text-extraction/1`, prototype parity with declared deviations D1/D2 and stage-2 metrics; not yet connected to stage 3.
- [Initial baseline and Dedoc trials](milestones/m1/04a/M1_04A_BASELINE_2026-10-17.md) — 103 retained pages, frozen six-act corpus and explicit hierarchy limitations.
- [First shared OCR implementation](milestones/m1/04a/M1_04A_STRUCTURE_2026-10-17.md) — 205 full development pages, deterministic compilation and remaining blockers; M1-04A/G13 remain open.
- [Direct dots.mocr JSON trials](milestones/m1/04a/M1_04A_DIRECT_JSON_2026-10-17.md) — full 205-page Dedoc/Docling API runs with geometry, source mappings, actual stage outputs and explicit preservation/hierarchy failures.
- [Failure classes and document scopes](milestones/m1/04a/M1_04A_FAILURE_CLASSES_2026-10-17.md) — impact-based priorities, complete development inventory and the reusable scope-boundary follow-up.
- [Two additional PDF runs](milestones/m1/04a/M1_04A_TWO_PDF_2026-10-17.md) — 26 fresh OCR pages through compilation/replay, selected image controls and direct Dedoc/Docling JSON comparisons; ordinary-reference false approval remains unresolved.
- [Logical paragraphs and marker-sequence depth](milestones/m1/04a/M1_04A_LOGICAL_PARAGRAPHS_2026-10-17.md) — experiment outside the compiler: hand-made owner gold for 8 documents/849 regions, two frozen-code holdouts; 100% vs 88.0% current `/7` and 80.4% Dedoc foiv on owner paths. Not qualification.
- [Evaluation protocol](milestones/m1/04a/M1_04A_EVALUATION_PROTOCOL_2026-10-20.md) — how stage-3 progress is measured: development/regression/check-pool/qualification-reserve split, gold before runs, first-pass ledger, per-stage metrics, error classes; stop thresholds await the owner.
- [Logical-text layer, stage 2](milestones/m1/04a/M1_04A_LOGICAL_TEXT_2026-10-20.md) — `logical-text/1` in `src/`: prototype parity on 8 saved documents (no D1/D2/unexpected differences), continuation 29/0/2, 0 false/missed header exclusions; stage 3 not connected, not qualification.

## Tool guides

- [Parser-independent HTML preparation](guides/HTML_PREPARATION.md)
- [Housing Code HTML diagnostic parser](guides/HOUSING_HTML_PARSER.md)

## Research and historical context

- [Research map](research/RESEARCH.md)
- [Legal RAG literature review, 2026](research/legal_rag_2026_literature_review_ru.md)
- [ARLC 2026 analysis](research/ARLC_2026_LEGAL_RAG_ANALYSIS.md)
- [Index-RAG review](research/review-index-rag.md)
- [SanPiN 2.1.3684-21 source coverage](research/SANPIN_2_1_3684_21_SOURCE_COVERAGE.md)
- [Historical source and chat register](research/SOURCES.md)
- [Earlier architecture proposal](research/LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md) — historical context, not the current implementation plan.

## Individual plans

- [Housing Code HTML parser](plans/2026-10-13-housing-html-parser.md)
- [Independent structure audit](plans/2026-10-15-independent-structure-audit.md)
- [Official structure integration](plans/2026-10-15-official-structure-integration.md)
- [Official JSON transfer](plans/2026-10-16-official-json-transfer.md)
- [Official JSON normalization](plans/2026-10-16-official-normalization.md)
- [Local dots.mocr integration](plans/2026-10-16-m1-04-dotsmocr.md)
- [Universal OCR structure parser, M1-04A](plans/2026-10-17-m1-04a-ocr-structure.md)

Diagram sources and rendered assets remain together in [assets/](assets/);
their [prompt record](assets/PROMPTS.md) is retained there too.
Read [AGENTS.md](AGENTS.md) before changing this documentation tree.
