# M0 Implementation Plan — official-source acquisition and contracts

**Дата:** 27 сентября 2026 года
**Статус:** опубликован в Linear для исполнения
**Основание:** [PRD v0.1](PRODUCT_REQUIREMENTS.md), [source policy](LEGAL_SOURCES_POLICY.md), [master plan](LEGAL_RAG_MASTER_PLAN_2026.md)

## 1. Цель M0

M0 должен доказать, что Legal RAG может независимо и воспроизводимо получить пять пилотных НПА из официальных систем, сохранить неизменяемые исходники и provenance, обнаружить повторное получение и изменения, сформировать проверяемых кандидатов редакций и подготовить handoff-контракт для M1.

M0 считается завершённым не по количеству написанного кода, а когда второй запуск пилота корректно различает `new / unchanged / changed / failed`, не создаёт дубликаты, не повреждает последнее успешное состояние и выдаёт проверяемый gate report.

## 2. Scope

### Входит

- минимальный Python-пакет и CLI для запуска acquisition;
- `PublicationPravoConnector`;
- пилотные `ActualPravoConnector` и `LegislationRussiaConnector`;
- immutable content-addressed raw archive;
- `SourceSystem`, `AcquisitionRun`, `SourceAsset`, source manifest и source relations;
- повторная синхронизация, change report и exception queue;
- пять пилотных актов: ЖК РФ, ПП РФ № 354, ПП РФ № 491, 59-ФЗ и один зарегистрированный ведомственный акт с приложениями;
- M0 handoff `ActIdentity claim → snapshot/coverage claim → source evidence` для M1;
- 30–50 вручную проверенных вопросов с рабочей и закрытой частями;
- измерение времени, ошибок, сетевой устойчивости и ручной проверки;
- итоговый M0 gate report.

### Не входит

- применение поправок по смыслу и построение полной истории редакций;
- утверждение юридической применимости коннектором;
- полный Legal AST и extraction pipeline M1;
- PostgreSQL, FTS и retrieval M2;
- FastAPI, UI, фоновые workers и scheduler;
- embeddings, reranker, агент и answer generation;
- обход TLS, фиксированные IP или недокументированные способы снятия ограничений источника;
- импорт кода, индексов или runtime state из исключённых локальных проектов.

## 3. Реализационные решения

### Runtime

- Python 3.13 как текущая стабильная локальная версия проекта.
- Один пакет `legal_rag.sources`; M0 не создаёт преждевременные модули UI, agent или retrieval.
- CLI является единственной исполняемой границей M0. API добавляется только при реальном потребителе.
- Стандартная библиотека используется для hashing, файловых операций, JSON, HTTP и тестов; новая dependency добавляется только при доказанной необходимости.

### Local persistence

- Raw bytes адресуются SHA-256 и сохраняются один раз в ignored `data/`.
- Metadata raw asset, source manifest и run report сохраняются отдельно как versioned JSON records.
- Запись завершается через temporary file и atomic replace; частично записанный файл не считается asset.
- `failed` run не меняет указатель на последнее успешное состояние источника.
- Одинаковый source item и тот же SHA-256 дают `unchanged`; новый SHA-256 для того же source item даёт `changed`; первый успешный asset даёт `new`.
- Run ID может быть уникальным и недетерминированным; content identity и сериализуемые domain records должны быть детерминированными.

### Source boundary

- Connector только получает и описывает внешний материал.
- Connector возвращает bytes, transport metadata и заявленные source claims; он не присваивает `reviewed`, не вычисляет юридический `valid_from/to` без evidence и не создаёт Legal AST.
- Недокументированный endpoint изолируется внутри соответствующего connector и не протекает в domain contracts.
- Retry/backoff ограничены и наблюдаемы; постоянная ошибка заканчивается `failed`, а не бесконечным повтором.

### Fixtures and live checks

- Default test suite не использует сеть.
- Малые redistributable fixtures коммитятся только с URL, датой capture, условиями использования и ожидаемым SHA-256.
- Полные документы, live responses и generated reports остаются в ignored `data/`.
- Live smoke checks запускаются явно и не определяют результат unit test suite.

## 4. Domain contracts M0

Минимальные записи:

| Запись | Обязательные данные |
|---|---|
| `SourceSystem` | stable key, authority scope, base URL, adapter version, access/rights status |
| `AcquisitionRun` | run ID, source, request window/cursor, started/finished UTC, adapter version, counts, errors, result |
| `SourceAsset` | SHA-256, byte length, media type, captured UTC, source URL, transport metadata, local archive key |
| `SourceItem` | source system, external ID, declared act identity, declared edition label, latest successful asset |
| `SourceRelation` | from/to source item or asset, relation type, asserted by source, evidence reference, review state |
| `EditionCandidate` | claimed act identity, claimed edition date/label, assets, publications/amendments, temporal evidence, unresolved items |
| `ExceptionItem` | stage, source/item, machine-readable reason, diagnostic message, retryability, created UTC |

Allowed acquisition result values are fixed to `new`, `unchanged`, `changed`, `failed`.

`EditionCandidate` is a handoff candidate, not `LegalEdition`. M1 may accept, reject or split it after extraction and legal review.

## 5. Delivery strategy

Работа ведётся tracer bullets: сначала один fixture-backed путь, затем один live publication, затем failure/change, source reconciliation и расширение до пяти актов. Не допускается горизонтальная реализация «всех моделей», «всех connector interfaces» или «всего storage» без законченного проверяемого сценария.

```text
M0-01 fixture acquisition
  ├─→ M0-02 live publication
  └─→ M0-03 resync failures/changes
        M0-02 → M0-04 publication relations
        M0-04 → M0-05 actual edition candidate
        M0-04 → M0-06 government decree candidate
M0-07 human pilot decisions ─────────────────────────┐
M0-04 → M0-08 source-to-corpus handoff              │
M0-03 + M0-05 + M0-06 + M0-07 + M0-08 → M0-09 pilot
M0-09 → M0-10 legal review
M0-10 → M0-11 gold set
M0-11 → M0-12 M0 gate report
```

## 6. Implementation slices

### M0-01 — Fixture-backed acquisition lifecycle

**Type:** AFK
**Blocked by:** none
**User stories:** 1–6
**Implementation status:** completed and verified offline on 27.09.2026

Deliver one end-to-end CLI path that reads a deterministic fixture through a connector, writes raw bytes to the content-addressed archive, records `SourceAsset` and `AcquisitionRun`, and returns `new` on the first run and `unchanged` on the second.

Acceptance:

- a clean checkout can run the focused test command without network access;
- first run writes exactly one raw asset and a complete run record;
- second identical run does not duplicate raw bytes and reports `unchanged`;
- SHA-256 is computed from original bytes and verified by the test;
- interrupted metadata write cannot make a partial asset visible;
- CLI output identifies run ID, source item, result and report location.

### M0-02 — One live publication end to end

**Type:** AFK
**Blocked by:** M0-01
**User stories:** 1–4, 8
**Implementation status:** completed and live-smoke verified on 27.09.2026 for publication `0001202511280030`

Acquire one pilot act through the documented publication.pravo.gov.ru contract and persist its official publication metadata and original asset through the same lifecycle proven by M0-01.

Acceptance:

- connector maps one stable external ID to a source item without parsing legal applicability;
- explicit live smoke command stores raw bytes, URL, capture time, transport metadata and declared publication details;
- network timeout and HTTP failure produce diagnostic `failed` runs;
- default tests replay a documented small fixture and require no network;
- no fixed IP, TLS bypass or silent fallback is introduced.

### M0-03 — Safe change and failure resynchronization

**Type:** AFK
**Blocked by:** M0-01
**User stories:** 5–7, 10
**Implementation status:** completed and verified offline on 28.09.2026

Extend the complete fixture path with changed bytes and transport failure so a source item moves through all four acquisition outcomes without losing its latest successful asset.

Acceptance:

- new content for the same source item reports `changed` and preserves both immutable assets;
- a simulated timeout reports `failed` and retains the latest successful pointer;
- run counts and exception items match the observed outcomes;
- change report contains old/new hashes and source identity without embedding full raw content;
- one focused regression test covers every result branch.

### M0-04 — Publication and amendment relations for one act

**Type:** AFK
**Blocked by:** M0-02
**User stories:** 8–10
**Implementation status:** completed and verified offline on 28.09.2026

Resolve one pilot act from publication records to its official original and discovered amendment publications, preserving each relation as a source claim with evidence.

Acceptance:

- act, publication and amendment source items remain separately identifiable;
- relation type, asserting source and evidence reference are recorded;
- missing or ambiguous relation becomes an exception item rather than a guessed link;
- rerun is idempotent;
- a human-readable report shows the relation chain and unresolved gaps.

### M0-05 — Consolidated-edition candidate from actual.pravo.gov.ru

**Type:** AFK
**Blocked by:** M0-04
**User stories:** 8–10, 21
**Implementation status:** completed and verified offline and by explicit live smoke on 28.09.2026

For one supported pilot act, acquire an available consolidated-text candidate and link it to the act/publication chain without treating the claimed edition as verified temporal coverage.

Acceptance:

- undocumented transport details remain private to the connector;
- raw response and declared edition label are preserved;
- candidate links to its act identity claim and supporting source assets;
- missing effective-date evidence produces `temporal_coverage_unknown` or an unresolved item;
- tests use captured or synthetic fixtures; live access is an explicit smoke check.

### M0-06 — Government-decree candidate from «Законодательство России»

**Type:** AFK
**Blocked by:** M0-04
**User stories:** 8–10, 21
**Implementation status:** completed and reverified offline and by explicit live smoke on 28.09.2026 after replacing the legacy HTML route with the portal card and selected-edition `documenttext` responses

Acquire and reconcile one Government decree candidate through «Законодательство России», binding the portal card to one selected `documenttext` edition through `hash`, `nd`, `baseid`, and `rdk`, while using the same domain contracts and reports as other sources.

Acceptance:

- connector-specific parsing does not change shared domain meanings;
- one of ПП РФ № 354 or № 491 has an archived official candidate and source relations;
- absent or conflicting edition metadata remains explicit;
- repeated acquisition is idempotent;
- failure does not remove prior successful state.

### M0-07 — Approve pilot act and review policy

**Type:** HITL
**Blocked by:** none
**User stories:** 8, 16, 29
**Implementation status:** completed by product-owner approval on 28.09.2026; SanPiN edition coverage remains an explicit M0-09/M0-10 review item

Record the human decisions required to finish the M0 pilot: the fifth registered agency act, source access/rights constraints, reviewer authority and the second-review rule for disputed gold labels.

Acceptance:

- the fifth act is named with official source route and reason it exercises appendices/non-trivial structure;
- every M0 source has recorded access/rights status and rate-limit assumption;
- a named role may assign `reviewed` or `rejected`;
- disputed gold labels require an independent second decision;
- unresolved decisions are explicitly marked as blockers, not filled by engineering assumptions.

### M0-08 — Source-to-corpus candidate handoff

**Type:** AFK
**Blocked by:** M0-04
**User stories:** 8–10, 19–21
**Implementation status:** completed and verified offline on 29.09.2026

Produce a serialized `EditionCandidate` for one reconciled act that M1 can consume without importing connector internals or mistaking source claims for verified legal facts.

Acceptance:

- handoff separates act identity claim, edition claim, temporal evidence and unresolved items;
- all claims link back to source assets and relations;
- serialization is deterministic for identical input records;
- candidate cannot carry `reviewed` without an explicit review decision;
- contract test proves connector-specific fields do not leak into the shared handoff.

### M0-09 — Five-act repeat-sync pilot

**Type:** AFK
**Blocked by:** M0-03, M0-05, M0-06, M0-07, M0-08
**User stories:** 1–10, 31–32
**Implementation status:** completed and verified offline and live on 29.09.2026

Run the complete M0 acquisition path for all five pilot acts twice and publish one reproducible report of coverage, outcomes, exceptions and acquisition cost.

Acceptance:

- pilot includes ЖК РФ, ПП РФ № 354, ПП РФ № 491, 59-ФЗ and the approved agency act;
- first and second run reports are retained and comparable;
- second run classifies every source item as `new / unchanged / changed / failed` without duplicates;
- report identifies missing consolidated editions, amendments and temporal evidence;
- elapsed time, request counts, bytes, retries and failures are recorded;
- raw assets remain outside Git.

Live verification used 14 source items across the five acts. The first pass
reported 14 `new`; the second reported 14 `unchanged`, added zero raw assets and
reported no duplicate source items. The two passes made 60 requests, received
21,306,570 bytes in 58.749 seconds, and required no retry. The generated report
keeps SanPiN consolidated coverage, four amendment chains, and temporal evidence
for all five acts explicitly unresolved rather than treating source labels as
legal applicability.

### M0-10 — Legal review of pilot candidates

**Type:** HITL
**Blocked by:** M0-09
**User stories:** 8–10, 16, 21, 29, 32
**Implementation status:** completed on 29.09.2026 with one rejected candidate,
four unresolved candidates and a documented timing-measurement deviation

Review the five pilot candidates for act identity, declared edition, source relations, temporal evidence and unresolved gaps, and measure the human effort required.

Acceptance:

- every candidate receives `reviewed`, `rejected` or explicitly unresolved status with rationale;
- reviewer does not infer coverage from file name, capture time or consolidated-text label alone;
- critical gaps prevent approval;
- review start/finish time and exception handling time are recorded per act;
- disputed decisions are sent to the second-review path.

The recorded decisions and evidence are in
[M0-10 legal review](M0_10_LEGAL_REVIEW.md). Human comparison took approximately
80 minutes. Exact per-act start/finish timestamps and exception-only minutes
were not collected by the simplified checklist, so that measurement criterion
is `partial`; no timestamps were inferred after the fact.

### M0-11 — Working and closed gold-question sets

**Type:** HITL
**Blocked by:** M0-10
**User stories:** 29–30

Create 30–50 manually checked questions tied to the reviewed pilot material, split into a working set and an immutable closed gate set for later parser/retrieval evaluation.

Acceptance:

- each item has query class, expected act/address, edition claim, source span or explicit no-answer label;
- set covers exact reference, paraphrase, exception/negation, confirmed date, missing coverage and one cross-reference;
- working and closed membership is recorded before retrieval tuning;
- disputed labels receive a second review;
- closed labels are not exposed to implementation-time tuning;
- licensing and storage decision for the dataset is recorded.

### M0-12 — M0 gate report and contract freeze

**Type:** AFK
**Blocked by:** M0-11
**User stories:** 31–33

Generate the final M0 report from recorded runs, reviews and gold-set metadata, then freeze the acquisition and source-to-corpus contracts used to enter M1.

Acceptance:

- report evaluates every M0 acceptance criterion as pass, fail or unresolved with evidence;
- report includes source coverage, outcome counts, exceptions, review hours and acquisition cost;
- schema/adapter versions and fixture hashes are recorded;
- M1 handoff contract is versioned and reproducible;
- failed gate blocks M1 instead of being converted to a future TODO;
- no FTS, vector search, UI or agent work is included to make the gate appear complete.

## 7. Verification matrix

| Behavior | Default automated check | Explicit live/HITL check |
|---|---|---|
| Raw immutability and hash | fixture bytes → expected SHA-256 | inspect one archived official asset |
| Idempotency | same fixture twice → `new`, then `unchanged` | repeat one live acquisition |
| Change detection | alternate fixture → `changed` | compare a naturally updated item when available |
| Failure safety | timeout fixture → `failed`, latest success unchanged | controlled unreachable endpoint |
| Source relations | deterministic relation fixture | reviewer inspects one publication chain |
| Temporal uncertainty | missing evidence → unknown/unresolved | reviewer checks source evidence |
| Five-act coverage | report schema and counts | legal review of all five candidates |
| Gold split | schema, uniqueness and frozen membership | second review of disputed labels |

## 8. M0 gate

M0 passes only when:

- the second pilot run classifies all acquisition outcomes without corrupting successful state;
- every candidate has official provenance and raw SHA-256;
- no accepted candidate depends on a commercial-aggregator export;
- missing edition, amendment or temporal evidence remains explicit;
- five-act human review and 30–50 gold questions are completed under the recorded policy;
- actual time, cost and error data exist for planning M1–M2;
- the versioned M1 handoff contract can be regenerated from retained records.

## 9. Stop conditions

- Source terms or access restrictions prohibit the intended capture pattern.
- Ordinary DNS/HTTP access to the documented source services cannot be made reliable without unsafe workarounds.
- A pilot act cannot be tied to an official publication or reviewable candidate edition.
- No authorized legal reviewer is available for the gate.
- Raw bytes or provenance cannot be reproduced from a clean run.

At a stop condition the corresponding issue remains blocked and the project records the evidence; scope is not silently weakened.

## 10. Linear tracking

Проект: [Legal RAG](https://linear.app/rulegalrag/project/legal-rag-503b96f26269)
Milestone: `M0 — Official-source acquisition`

| Slice | Linear | Type |
|---|---|---|
| M0-01 | [RUL-1](https://linear.app/rulegalrag/issue/RUL-1/m0-01-prove-the-fixture-backed-acquisition-lifecycle) | AFK |
| M0-02 | [RUL-3](https://linear.app/rulegalrag/issue/RUL-3/m0-02-acquire-one-official-publication-end-to-end) | AFK |
| M0-03 | [RUL-4](https://linear.app/rulegalrag/issue/RUL-4/m0-03-make-change-and-failure-resynchronization-safe) | AFK |
| M0-04 | [RUL-5](https://linear.app/rulegalrag/issue/RUL-5/m0-04-reconcile-publication-and-amendment-relations-for-one-act) | AFK |
| M0-05 | [RUL-6](https://linear.app/rulegalrag/issue/RUL-6/m0-05-capture-a-consolidated-edition-candidate-from-actualpravogovru) | AFK |
| M0-06 | [RUL-7](https://linear.app/rulegalrag/issue/RUL-7/m0-06-capture-a-government-decree-candidate-from-legislation-russia) | AFK |
| M0-07 | [RUL-2](https://linear.app/rulegalrag/issue/RUL-2/m0-07-approve-the-pilot-act-and-review-policy) | HITL |
| M0-08 | [RUL-8](https://linear.app/rulegalrag/issue/RUL-8/m0-08-produce-the-source-to-corpus-candidate-handoff) | AFK |
| M0-09 | [RUL-9](https://linear.app/rulegalrag/issue/RUL-9/m0-09-run-the-five-act-repeat-sync-pilot) | AFK |
| M0-10 | [RUL-10](https://linear.app/rulegalrag/issue/RUL-10/m0-10-review-the-five-pilot-candidates) | HITL |
| M0-11 | [RUL-11](https://linear.app/rulegalrag/issue/RUL-11/m0-11-create-working-and-closed-gold-question-sets) | HITL |
| M0-12 | [RUL-12](https://linear.app/rulegalrag/issue/RUL-12/m0-12-publish-the-m0-gate-report-and-freeze-contracts) | AFK |
