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
- [Dense tables and rotated pages](milestones/m1/04/M1_04_DENSE_TABLES_2026-10-23.md) — batch-5 OCR failures, per-table grid degradation and the opt-in rotation retry.
- [M1-04B plan](plans/2026-10-23-m1-04b-ocr-runtime.md) — planned slice of the M1 plan, starts after M1-04A is complete: own minimal dots.mocr runtime in `ocr/dotsmocr/` with weights in ignored `data/ocr/dotsmocr/model/`, instead of the OCR-Lab test bench; only the safety patch (Task 0) is done.

### M1-04A: universal OCR structure parser

- [Plain-language problem brief](milestones/m1/04a/M1_04A_PROBLEM_BRIEF_2026-10-19.md) — standalone Russian explanation for readers outside the project: purpose, failure causes, tool results and remaining work.
- [Task and experiment plan](plans/2026-10-17-m1-04a-ocr-structure.md) — in progress: existing OCR files, additional official documents, reusable legal hierarchy and independent transfer checks. M1-06 consumes the resulting parser for full SanPiN coverage.
- Data layout: new M1-04A originals, OCR, gold and experiments live under local `data/m1/m1-04a/` (see `data/AGENTS.md`); `assets/build_m1_04a_catalog.py` rebuilds the hash-verified document copies.
- [Cycle 3 plan](plans/2026-10-22-m1-04a-cycle-3.md) — single-annex equivalence (owner 22.10.2026), scope-transfer check, provenance/freeze coverage, then prototype v2 (law and document annexes, «Раздел» level, subheadings, subpoint closing) with regression over 34 development documents.
- [Pool batch 4 plan](plans/2026-10-23-m1-04a-pool-batch-4.md) — first measure of frozen prototype v2 on 11 unseen acts (no codes left in the census), blind gold under convention v2, single-annex and `cross_scope_v2` by default, v1 for comparison.
- [Pool batch 3 plan](plans/2026-10-22-m1-04a-pool-batch-3.md) — tool cleanups, census of codes with an original portal publication, batch 3 with codes (≤500 pages) and government orders, blind gold under convention v2, first pass of frozen v1.
- [Source acquisition bug report](milestones/m1/04a/M1_04A_BUG_SOURCE_ACQUISITION_2026-10-22.md) — codes never selected, government orders with empty card names, whole feed days rejected, early-2011 non-PDF assets; handed to Codex for fixing.
- [Cycle 2 plan](plans/2026-10-21-m1-04a-cycle-2.md) — prototype v1 fixes for named law units, attached-document captions and requisites (16 development documents, no regression), then pool batch 2 with longer and more varied acts and no single-edition filter (amending acts excluded; the code quota was dropped by ruling), blind Codex gold and first-pass run.
- [Pool batch 1 plan](plans/2026-10-21-m1-04a-pool-batch-1.md) — metadata-only random selection of 8 diverse unamended acts, OCR by the executor, frozen first-pass run. The planned automatic gold from official pravo.gov.ru trees was replaced (owner, 21.10.2026) by agent (Codex) annotation of OCR region text, frozen before the run.
- [Pool batch 1 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_1_2026-10-21.md) — frozen `code-final` prototype on 8 new acts with agent-annotated gold, scored under annotation convention v1 (Picture regions excluded): 226/333 (67.9%) vs current `/7` 89/333 (26.7%, refuses 6/8 acts); all 363 regions: 237 vs 91. Continuation not independently measured; error classes, selection biases, 30-region [gold sample](milestones/m1/04a/M1_04A_POOL_BATCH_1_SAMPLE_2026-10-21.md). Not G13/Task 3.
- [Pool batch 2 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_2_2026-10-22.md) — frozen prototype v1 on 9 unseen acts (4 laws, decree, 2 resolutions, 2 orders; 1782 regions, blind Codex gold under convention v1): 1077 (60.4%) vs `code-final` 597 (33.5%) vs `/7` 123 (6.9%); 702/705 v1 errors silent, 558 cross-scope (law annexes 278, disputed nested-annex naming 280); on both disputed classes (nested-annex naming, «4.1.» depth) the prototype follows the earlier SanPiN 2.1.3684-21 development gold and the batch-2 gold departs from it — both go into convention v2 before batch 3; 5 new classes; continuation measured independently for the first time. Development re-score under convention v2 (section 10): v1 1464 (82.2%), `code-final` 980, `/7` 372; 60.4% stays the ledger entry. 30-region [gold sample](milestones/m1/04a/M1_04A_POOL_BATCH_2_SAMPLE_2026-10-22.md). Batch now development. Not G13/Task 3.
- [Pool batch 3 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_3_2026-10-22.md) — frozen prototype v1 on 9 unseen acts incl. the first code (KAS RF, 480 pages, 2855 of 4108 regions; census: the only code with an original portal publication), 2 laws, decree, 2 resolutions, government order, 2 orders; blind Codex gold under convention v2 (KAS in 5 stitched page-range parts): 4008 (97.6%) vs `code-final` 1125 (27.4%) vs `/7` 170 (4.1%); KAS 2847/2855 (99.7%; strict 9 — no «Раздел» level), without KAS 1161/1253 (92.7%); 99/100 v1 errors silent, 0 cross-scope by the evaluator but 30 regions of an attached document's annex silently given to its body; 3 new classes. 30-region [gold sample](milestones/m1/04a/M1_04A_POOL_BATCH_3_SAMPLE_2026-10-22.md). Batch now development. Not G13/Task 3.
- [Pool batch 4 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_4_2026-10-23.md) — first measure of frozen prototype v2 on 11 unseen acts (3 laws, award decree, 2 resolutions, 2 government orders, 3 ministry orders; 2465 regions, blind Codex gold under convention v2): v2 1579 (64.1%) vs v1 1546 (62.7%) vs `/7` 35 (1.4%); 864 of 886 v2 errors are «01., 02.» work lists under estimate tables read as points and nested into each other in two near-identical Mintrans orders (954 regions, 38.7%; blind gold agreement 464/464); without them 1489/1511 (98.5%). `cross_scope_v2` 20 (old `cross_scope` 20): a second attached document named `A/AN` vs gold `S2` (naming, owner decision pending); 1 new class, new-class counter 0. 30-region [gold sample](milestones/m1/04a/M1_04A_POOL_BATCH_4_SAMPLE_2026-10-23.md). Batch now development. Not G13/Task 3.
- [Pool batch 5 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_5_2026-10-23.md) — short Russian report: first measure of frozen prototype v3.1 (v2 for comparison) on 11 unseen acts (2268 regions, blind Codex gold under convention v2): v3.1 = v2 = 2144 (94.5%), without the coal Program rp-1099 (42.9% of regions) 1291/1296 (99.6%), `/7` 108; `cross_scope_v2` 3 (footnotes of a second list given to the first), 1 new class (section heading read by OCR as Text); v3.1 rules never fired; three table-heavy ministry orders failed OCR (selection bias, M1-04 finding). Not ready by protocol §7.
- [Pool batch 6 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_6_2026-10-24.md) — short Russian report: first measure of frozen prototype v4 (v3.1 for comparison) on 11 unseen acts (1925 regions, blind Codex gold under convention v2, memory-exposure limitation): v4 1844 (95.8%), v3.1 1830, `/7` 610; 78 of 81 v4 errors in Minekonomrazvitiya order No. 37 (without it 1634/1637, 99.8%); `cross_scope_v2` 0; 1 new class (missing dotted section number «5.2»: «5.3» nested in «5.1»), counter still 0; v4 table-row and `<sup>` rules fired, «N+1.» and Roman Text heading never; new OCR table handling untested (0 unresolved, 0 rotations). Not ready by protocol §7.
- [Pool batch 7 first-pass results](milestones/m1/04a/M1_04A_POOL_BATCH_7_2026-10-24.md) — short Russian report: first measure of frozen prototype v5 (v4 for comparison, identical owners) on 11 unseen acts (1477 regions, strictly blind Codex gold: memory off per run): 1394 (94.4%), `/7` 342; 62 of 83 errors in Minenergo order No. 90 (without it 1154/1175, 98.2%), all 62 `cross_scope_v2` (annexes of the Rules, themselves annex 1 to the order, numbered as order annexes); 1 new class, counter still 0 (owner question: new or reverse batch-2 form); no v3.1/v4/v5 rule fired. Not ready by protocol §7.
- [Prototype v1 development report](milestones/m1/04a/M1_04A_PROTOTYPE_V1_2026-10-21.md) — Russian owner report: frozen `ocr-logical-structure/1-experiment` fixes named law units, attached-document captions and requisite blocks; 1182/1182 on the 16 development documents (batch 1: 226 → 333 of 333). Development result, NOT progress; the real measure is batch 2. Known limitations listed.
- [Prototype v2 development report](milestones/m1/04a/M1_04A_PROTOTYPE_V2_2026-10-22.md) — Russian owner report: frozen `ocr-logical-structure/2-experiment` adds law/document annex captions, the «Раздел» level, section subheadings and subpoint closing; 7015/7072 on the 34 development documents (v1 6660), no document below v1. Development result, NOT progress; the real measure is batch 4. Rulings and known limitations listed.
- [Prototype v3 development report](milestones/m1/04a/M1_04A_PROTOTYPE_V3_2026-10-23.md) — short Russian owner report: frozen `ocr-logical-structure/3-experiment` adds leading-zero list lines, restarted numbering (untested on data), lines between tables and footer file codes; 9479/9537 on the 45 development documents (v2 8614), no document below v2. Development result, NOT progress. §8: v3.1 (`3.1-experiment`, final-review fix of the «10. after 09.» list rule) has the same scores and is what batch 5 measures.
- [Prototype v4 development report](milestones/m1/04a/M1_04A_PROTOTYPE_V4_2026-10-23.md) — short Russian owner report: frozen `ocr-logical-structure/4-experiment` adds table rows inside table annexes (owner decision 23.10.2026), `<sup>` footnote marks and Roman section headings read by OCR as Text (with a length/punctuation guard); 11754/11805 on the 56 development documents (v3.1 11623), `cross_scope_v2` 3 -> 0, no document below v3.1, 51 old errors left. Development result, NOT progress; batch 6 is the measure.
- [Prototype v5 development report](milestones/m1/04a/M1_04A_PROTOTYPE_V5_2026-10-24.md) — short Russian owner report: frozen `ocr-logical-structure/5-experiment` adds dotted-gap parent by prefix, footnote owner by the last mark (common owner across regions), the agreement signature block and the Roman sequence after table-row demotion; 13663/13730 on the 67 development documents (v4 13598), no document below v4, 16 batch-6 errors left (9-region unnumbered block in order No. 37 is an open annotation question). Development result, NOT progress; batch 7 is the measure.
- [Prototype v6 development report](milestones/m1/04a/M1_04A_PROTOTYPE_V6_2026-10-24.md) — short Russian owner report: frozen `ocr-logical-structure/6-experiment` adds annexes of an attached document (`A/AN<k>/AN<n>`), form fill-in lines without text, asterisk footnotes, the form signature heading and the v5 review minors; 15137/15207 on the 78 development documents (v5 15057), `cross_scope_v2` 62 -> 0, no document below v5, 6 batch-7 errors left. Development result, NOT progress. §8: final-review fix v6.1 `ocr-logical-structure/6.1-experiment` (nested annexes only outside an approved text, markdown emphasis is no asterisk mark), same 15137/15207; batch 8 measures v6.1.
- [Annotation convention v1](milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v1.md) — versioned owner-gold rules for the check pool: scored OCR categories (not Picture/noise), signatures and page marks, `+`, `owner-path/2`, designation aliases, approved text ≡ annex, blind annotator input without stage-2 output. Section 8 lists v2 proposals; items 1–2 were accepted on 22.10.2026.
- [Annotation convention v2](milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v2.md) — `m1-04a-annotation/v2` (22.10.2026, from batch 3): v1 plus two owner rules — annexes of an attached document are `S/AN<n>`; «N.M» after an existing «N.» nests (`…/4/4.1`), flat only without «N.», exceptions flagged in notes. §6 (23.10.2026): attached documents compared by order of appearance (`--attached-ordinal`), no table node. Proposals 3–5 stay not in force. Batch-2 gold is derived from frozen v1 by `assets/derive_m1_04a_gold_v2.py`; batch 1 is unchanged.
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

- [Legal AI: verified facts and project takeaways](research/ZAKON_LEGAL_AI_TAKEAWAYS_2026-10-23.md) — Russian brief on the 13 October Zakon.ru article, the checked court determination and Supreme Court concept; facts, project implications and hypotheses kept separate.
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
- [Own dots.mocr runtime, M1-04B](plans/2026-10-23-m1-04b-ocr-runtime.md)
- [Universal OCR structure parser, M1-04A](plans/2026-10-17-m1-04a-ocr-structure.md)

Diagram sources and rendered assets remain together in [assets/](assets/);
their [prompt record](assets/PROMPTS.md) is retained there too.
Read [AGENTS.md](AGENTS.md) before changing this documentation tree.
