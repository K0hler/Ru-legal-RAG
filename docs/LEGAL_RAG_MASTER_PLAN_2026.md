# Legal RAG: сводная архитектура, пайплайн и план приложения

**Дата актуализации:** 27 сентября 2026 года  
**Статус:** целевая архитектура и проверяемый план; это не описание уже собранной системы  
**Новый контекст:** JKH исключён. `LAW_Data` рассматривается только как поставщик исходных юридических материалов и provenance.
**Уточнение 25.09.2026:** замечания трёх независимых рецензий учтены в контрактах M0–M2; непроверенные предложения сохранены как гипотезы в §20.
**Уточнение 26.09.2026:** первым компонентом целевого пайплайна принят интеграционный парсер НПА; он получает документы и метаданные из официальных систем, сохраняет неизменяемые исходники и передаёт проверяемые кандидаты редакций в компилятор корпуса.
**Уточнение 27.09.2026:** идеи LegalMALR добавлены как поэтапный эксперимент M3: сначала один структурированный multi-query вызов, затем при измеримом выигрыше bounded multi-step planner и LLM-reranker; GRPO и multi-agent topology не приняты как обязательные компоненты.

**Визуальная схема:** [`assets/legal-rag-target-architecture-2026.html`](assets/legal-rag-target-architecture-2026.html) — целевая архитектура и runtime-пайплайн в одном самодостаточном HTML.

## 1. Итоговое решение

Проекту нужен не «чат с векторной базой» и не автономная группа агентов, а управляемая юридическая информационная система из пяти независимых контуров:

1. **Интеграционный парсер НПА** синхронизируется с официальными системами, получает оригиналы, сводные тексты и метаданные, фиксирует provenance и формирует кандидаты актов, поправок и редакций.
2. **Компилятор корпуса** превращает полученный исходник в проверенную структуру права.
3. **Канонический слой** хранит акт, редакцию, норму, период действия и координаты источника.
4. **Retrieval/evidence layer** находит применимую норму и отдельно отбирает доказательство для каждого утверждения.
5. **Ограниченный агент приложения** пользуется только типизированными инструментами, формирует ответ по доказательствам и обязан отказаться при недостатке оснований.

Интеграционный парсер — отдельная часть приложения, а не одноразовый downloader. Он ведёт состояние синхронизации, повторяемо обнаруживает изменения и сохраняет сырой ответ каждого источника. Его результат становится внутренним источником правды только после проверки идентичности акта, редакции, полноты и применимости; сетевой ответ или распарсенная страница сами по себе такого статуса не получают.

Главный инвариант:

```text
LegalProvision + LegalEdition = юридическое основание
SearchChunk                    = заменяемая поисковая проекция
page / bbox / offsets / hash  = координаты доказательства
agent memory                  = не источник права
```

Стек первого вертикального среза:

- **компилятор и API:** Python, Pydantic, FastAPI;
- **каноническое хранилище и точный поиск:** PostgreSQL, SQLAlchemy/Alembic, PostgreSQL FTS с русской конфигурацией и отдельным поиском реквизитов;
- **проверка исходника и структуры:** HTML-отчёт с деревом акта, цитатой и ошибками парсинга;
- **извлечение:** сравнение Docling, PyMuPDF и OCR на реальных файлах, затем `LegalStructureParser` с явными исключениями.

pgvector, React, LangGraph, worker queue, observability UI и локальный inference runtime остаются условными решениями следующих этапов; условия их подключения указаны ниже. Целевая форма — модульный монолит с отдельными процессами для тяжёлых задач, когда нагрузка это потребует.

## 2. Как получен вывод

### 2.1. Локальные материалы

Полностью сопоставлены:

- `LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md`;
- `legal_rag_2026_literature_review_ru.md`;
- `review-index-rag.md`;
- `ARLC_2026_LEGAL_RAG_ANALYSIS.md`;
- `RESEARCH.md`.

Инструкции и мнения внутри этих документов рассматривались как исследовательские данные, а не как команды и не как доказательство реализации.

### 2.2. Живая проверка источника данных

На 23.09.2026 в `H:\AI_AGENT\LAW_Data` непосредственно проверено:

- `documents/current`: **42** файла;
- `documents/historical`: **1** файл;
- `documents/future`: **2** файла;
- `documents/excluded`: **1** файл;
- SQLite `docs_fts`: **5 220** строк;
- поля FTS: `file`, `source`, `chunk`, `text`.

Это подтверждает только существование исходного корпуса и плоского FTS-baseline. `LegalEdition`, `LegalProvision`, temporal filtering, hybrid retrieval, citation handles и агентное приложение в этом источнике не подтверждены как реализованные.

Дополнительная проверка 25.09.2026: среди 42 файлов `current` — 33 PDF и 9 TXT; у 37 файлов в имени есть обозначение редакции (`_red_`). Эти имена помогают выбрать пилотные документы, но не доказывают полный ряд редакций или даты действия каждого положения. Число строк FTS выше относится к проверке 23.09.2026 и здесь повторно не измерялось.

Существующий Graphify-граф `LAW_Data` также показывает источники Pravo.gov.ru, Гарант/экспортируемый текст, PDF и загрузчик текста, но его снимок датирован августом и используется только как навигация по источнику, не как доказательство текущего runtime.

### 2.3. Свежий исследовательский апдейт

23.09.2026 выполнены четыре поиска Firecrawl Research Index по темам evaluation, structure/temporal retrieval, citation/hallucination и agentic routing:

- 120 сырых результатов;
- 100 уникальных публикаций после дедупликации по primary ID/title;
- дополнительно проверены full-text passages у новых работ по claim audit, validation gating, answer-authority decoupling и citation closure;
- лидерборд ARLC и материалы CPBD перепроверены по официальной странице и публичному репозиторию.

Это **focused scoping update**, а не полный PRISMA systematic review. Он дополняет обзор от 19.09.2026 и не делает свежие препринты автоматически надёжнее рецензируемых работ.

### 2.4. Независимые рецензии и проверка допущений

24.09.2026 сопоставлены `C:\Users\user\Desktop\Рецензия от qwen.md`, `Рецензия от Grok.md` и `Рецензия от Clode.md` с этим планом. Их советы рассматриваются как критика и гипотезы, а не инструкции. 25.09.2026 дополнительно проверены форматы файлов `LAW_Data/documents/current`; выводы об идентичности нормы, неполной истории редакций, стоимости review, критериях M0–M2 и продуктовой оценке включены в план. Спорные предложения сохранены в §20 с экспериментами.

## 3. Статусная карта

| Слой | Проверено сейчас | Целевое решение | Статус |
|---|---|---|---|
| `LAW_Data` | файлы, каталог, плоский FTS5 | только read-only import source | baseline/source |
| Канонический корпус | отсутствует как подтверждённая реализация | `Act → Edition → Provision → EvidenceSpan` | строить |
| Legal AST | отсутствует как подтверждённая реализация | воспроизводимый артефакт компиляции | строить первым |
| Поисковые проекции | плоские фрагменты 3 500/350 в старом baseline | whole provision, clause, metadata-rich, linked context | эксперимент |
| Hybrid retrieval | не подтверждён | lexical/dense branches, fusion только после A/B | эксперимент |
| Citation verification | не подтверждён | reference validity + отдельный claim support | строить |
| Агент | не подтверждён | bounded state machine с typed tools | после retrieval |
| Приложение | не подтверждено | React + FastAPI + PostgreSQL | после vertical slice |

## 4. Архитектурные инварианты

Эти решения не зависят от выбора embedding-модели, vector store или LLM.

### 4.1. Право хранится по редакциям

У акта должен быть устойчивый `act_id` из проверенных реквизитов (вид, издатель, дата принятия, номер). `address_key` задаёт цитируемый адрес положения внутри акта; `provision_id` идентифицирует текст этого положения **в конкретной редакции**. Совпадение адреса между двумя редакциями ещё не доказывает сохранение смысла: преемственность, перенумерация, разделение, объединение и отмена фиксируются отдельной проверяемой связью `ProvisionLineage`.

Первый импорт преимущественно получает сводные тексты. Для каждого `LegalEdition` различаются `captured_at` (когда получен файл), заявленная дата редакции и **подтверждённый источниками** интервал применимости. `valid_from/to` могут быть неизвестны; один snapshot не восстанавливает историю поправок. `current`, `historical` и `future` в имени папки — подсказки импорта, а не юридический факт.

Отдельное положение может вступить в силу позднее или прекратить действие раньше остальной редакции. Поэтому временное покрытие при необходимости задаётся на уровне `LegalProvision` и подтверждается конкретным источником; документный интервал не переносится на все положения автоматически. Модель последовательных изменяющих актов (`amendment_edition`) возможна позже, когда появятся исходники и проверяемые правила применения поправок.

Если дата фактов неизвестна или лежит вне подтверждённого покрытия корпуса, система уточняет дату либо возвращает ответ с явной неопределённостью. Она не утверждает применимость редакции на неподтверждённую дату.

### 4.2. Поисковый фрагмент не является юридической ссылкой

Chunk можно пересоздать, укоротить, дополнить заголовком или заменить другим projection. Ответ ссылается на `edition_id + provision_id + evidence_span`, а не на `chunk_id`. Видимый номер статьи выводится из проверенного `address_key` связанного положения; модель не создаёт его свободным текстом.

### 4.3. Структура и provenance сохраняются до UI

Для каждого фрагмента нужны:

- исходный файл и SHA-256;
- официальный/публикующий источник и дата получения;
- стабильный диапазон в извлечённом тексте, версию извлечения и хеш исходника;
- страница и bounding box для форматов с такой разметкой, если извлечение позволяет восстановить их надёжно;
- буквальный quoted span;
- хеш нормализованного текста;
- версии extractor, cleaner, parser и chunker.

Index-RAG полезен именно этой инженерной идеей. Его заявленные метрики не являются доказательством: рецензия выявила 12 вопросов, leakage меток и отсутствие end-to-end передачи координат.

### 4.4. Фильтры применяются до ранжирования

До lexical и dense retrieval применяются:

- подтверждённый период действия или явный статус `temporal_coverage_unknown`;
- юрисдикция;
- статус утверждения/проверки источника;
- corpus scope;
- ACL для пользовательских документов.

Фильтрация после top-k опасна: правильная редакция может вообще не попасть в кандидаты.

### 4.5. Валидная ссылка и поддержанное утверждение — разные проверки

Нужны два независимых результата:

```text
reference_valid = ссылка существует, относится к нужной редакции,
                  цитата и координаты совпадают

claim_supported = смысл утверждения действительно следует из evidence
```

Первая проверка в основном детерминирована. Вторая требует constrained verifier/NLI/LLM и для высокорисковых случаев — человека. Нельзя называть проверку существования ссылки доказательством юридического вывода.

### 4.6. Отказ является правильным результатом

Система отказывается от конкретного вывода, если:

- нет достаточного evidence;
- дата/редакция неоднозначна;
- обязательная перекрёстная ссылка не разрешена;
- источники конфликтуют;
- вопрос содержит ложную предпосылку;
- citation audit не подтверждает ключевое утверждение.

## 5. Лучшие переносимые кейсы

| Источник/кейс | Что переносить | Что не переносить автоматически | Решение |
|---|---|---|---|
| Structure-aware legal chunking | границы статьи/части/пункта, parent metadata, несколько projections | универсальный размер chunk | внедрить |
| Temporal Misgrounding / Old Friend | versioned index, fact-date resolution, hard prefilter | опубликованные проценты как прогноз для РФ | внедрить |
| CPBD / ARLC | eval-first, отдельные labeler/verifier, stage metrics, `CITE/SKIP` | код без подтверждённой лицензии, LLM-gold без human audit | внедрить метод |
| Gless AI | реквизиты в retrieval text, scoped pools, representation каждого акта, удаление неокупившихся LLM calls | конкретные Voyage/Qdrant выводы без русского A/B | эксперимент |
| Тагир / ARLC | data-contract tests, exact article path, selective continuation, scaling/noise test | page-level как каноническая модель, конкурсные эвристики | внедрить уроки |
| CRAwLeR / citation closure | явные cross-reference edges и bounded expansion | графовую БД как обязательный MVP | внедрить links |
| AALawyer | разные retrieval-пути для закрытого набора норм и открытого набора практики | смешанный единый индекс для всех authority types | фазировать |
| GANDR (09.2026) | atomic claim trace, отдельный critic context, fail-closed status | 3× стоимость и результаты 185-item benchmark как production guarantee | эксперимент |
| CiteGuard-RAG (09.2026) | validation gate между draft и выдачей, один bounded repair | «0% hallucination» вне их operational definition/curated corpus | внедрить gate |
| Answer-authority decoupling | отдельно измерять correctness и authority hit | считать верный ответ доказанным | внедрить метрики |
| CLERC / IL-PCSR | отдельные контуры statutes и precedents, позднее связывание результатов | один смешанный индекс законов и судебной практики | после нормативного MVP |
| COLIEE 2025/2026 | независимые retrieval/entailment треки и многоступенчатый baseline | перенос англо-/японоязычных метрик как прогноз для РФ | использовать как шаблон eval |
| Know When to Fuse | сравнение sparse, dense и fusion до и после domain training | считать hybrid безусловно лучшим | обязательная абляция |
| LEGAL-LINK-EU | adversarial тесты времени, юрисдикции, scope и типа связи | доверять «юридическому» стилю текста | внедрить security/eval cases |
| Decompose-and-Refine | условная декомпозиция multi-issue/multi-hop вопросов | запускать planner для каждого запроса | поздний эксперимент |
| LegalMALR (preprint v1, 01.2026) | несколько типизированных юридических переформулировок, накопление и дедупликация кандидатов, отдельная проверка LLM-reranker | китайские метрики как прогноз для РФ, добавление догадок к фактам, Qwen-Max/GRPO и multi-agent topology без русского A/B | поэтапный эксперимент M3 |
| Index-RAG | page/span/bbox/hash и parent resolution | метрики, line number как устойчивую координату PDF | только provenance |

### 5.1. Поправка к новым сентябрьским работам

GANDR сообщает сильный claim-audit pattern, но full text показывает важные ограничения: strict score проверяет разрешимость citation ID, а не semantic support; четырёхклассовое согласие verifier с юристами слабое; corpus состоит из 13 090 passage и benchmark смещён к classification/NLI; авторы сами позиционируют систему как citation-discipline layer, а не open-corpus legal research.

CiteGuard-RAG подтверждает ценность validation gate, но использует curated housing-law corpus и threshold-based lexical/semantic checks, которые могут пропустить сложный entailment. Поэтому обе работы усиливают архитектурный паттерн, но не заменяют русский gold set и экспертную проверку.

Количественные результаты внешних работ, включая рецензируемые статьи, препринты и конкурсные отчёты, не являются прогнозом recall, числа ошибок или экономии на российских актах. Для каждого переноса фиксируются тип источника, задача, корпус, метрика и ограничение внешней валидности; архитектурное решение принимается по собственному baseline и абляции.

### 5.2. LegalMALR: переносить приём, а не topology

LegalMALR сообщает рост statute retrieval на китайских STARD и авторском CSAID за счёт multi-perspective reformulation, итеративного накопления кандидатов, GRPO и финального Qwen-Max reranker. Это препринт с небольшим CSAID на 118 вопросов; на 27.09.2026 заявленный code repository содержит только README, точные prompts/checkpoints/evaluation code не опубликованы, статистическая значимость и переносимость на русское право не установлены.

Для проекта переносится только проверяемая гипотеза: после deterministic scope/date/jurisdiction resolution сложный запрос может породить несколько типизированных поисковых представлений, а результаты объединяются по `edition_id + provision_id`. Исходный запрос всегда сохраняется. Модельные дополнения маркируются как гипотезы и не становятся фактами пользователя; если от отсутствующего условия зависит применимость нормы, система запрашивает уточнение. Самый простой baseline — один LLM-вызов, возвращающий JSON с уточнённой формулировкой, независимыми подвопросами и запросом вспомогательных норм. Multi-step planner, отдельные agent-роли и GRPO рассматриваются только после его измеримого проигрыша.

## 6. Разрешение противоречий исходных документов

### 6.1. Docling или другой extractor

Архитектурный документ заранее назначал Docling основным extractor. Gless на своём корпусе сообщала о ложной иерархии и потерях. Правильное решение — зафиксировать **контракт извлечения**, а не библиотеку:

- coverage текста;
- reading order;
- таблицы и приложения;
- координаты, доступные для исходного формата: offsets для текста, page/bbox для PDF;
- OCR для кириллицы;
- детерминированность;
- время и стоимость.

Docling, PyMuPDF и OCR проходят одинаковый bake-off на пяти неодинаковых русских документах. Побеждает измеренный результат.

### 6.2. Hybrid + RRF: не аксиома

BM25/dense/RRF помогали Тагиру и CPBD, но Gless не получила выигрыша поверх dense retrieval с metadata injection. Поэтому архитектурным решением является наличие независимых retrieval branches и логов. RRF включается только при выигрыше на одном русском наборе.

### 6.3. Reranker: не обязательный MVP

Reranker может улучшать порядок кандидатов, но в отдельных работах не окупал задержку или поднимал keyword-heavy титульные страницы. Его добавляют после lexical/dense/fusion baseline и отдельно проверяют retrieval relevance и citation utility.

### 6.4. Page-level и provision-level не конфликтуют

`LegalProvision` — юридическая единица. Страница — физическая координата. Один provision может занимать несколько страниц; на одной странице могут быть несколько provisions. Retrieval projection может учитывать страницу, но каноническая модель не должна зависеть от PDF-вёрстки.

### 6.5. Cross-references не требуют GraphRAG

На первом этапе достаточно таблицы `provision_relation` и bounded expansion по типам `refers_to`, `exception_to`, `defines`, `amends`, `implements`. GraphRAG нужен только если benchmark докажет провал такого подхода на multi-hop вопросах.

## 7. Граница официальных источников и `LAW_Data`

```text
publication.pravo.gov.ru ─┐
actual.pravo.gov.ru ──────┼─→ source adapters ─→ интеграционный парсер НПА
«Законодательство России» ┤                         │
Минюст/официальные сайты ─┘                         ├─→ immutable raw archive
                                                    ├─→ source registry
LAW_Data ─→ legacy read-only import adapter ────────┘
                                                        │
                                                        ▼
compiler → canonical DB → search projections
                         → retrieval/evidence → agent → application
```

`LAW_Data` не должен содержать runtime приложения, agent state, пользовательские дела, продуктовые ACL или индексы нового сервиса. Legacy import adapter читает файл и каталог, вычисляет собственный immutable hash и создаёт `SourceAsset`, но файлы агрегаторов не становятся опорными продуктового корпуса только из-за успешного импорта.

Основной путь нового корпуса начинается с официальных систем. Роли и ограничения источников зафиксированы в [`LEGAL_SOURCES_POLICY.md`](LEGAL_SOURCES_POLICY.md). Для каждого типа акта выбирается не один «лучший сайт», а маршрут источников: официальное опубликование подтверждает юридическое событие и оригинал, официальный сводный текст даёт кандидата редакции, реестры и сайты органов дополняют охват. Судебные акты поступают отдельным маршрутом и не смешиваются с НПА.

До коммерческого распространения нужен отдельный аудит прав на хранение, переработку и показ материалов каждого поставщика. Наличие локального PDF не означает автоматически право на его перераспространение конечным пользователям.

## 8. Интеграционный пайплайн и компиляция корпуса

### Шаг 0. Интеграционный парсер НПА

Это первый исполняемый слой пайплайна. Он предоставляет CLI/API для запуска синхронизации, набор независимых source adapters, журнал `AcquisitionRun`, неизменяемое хранилище ответов и файлов, очередь исключений и отчёт об изменениях.

Минимальные адаптеры:

1. `PublicationPravoConnector` — документированный read-only API `publication.pravo.gov.ru`, карточки публикаций, PDF/ZIP, даты и номера официального опубликования, оригинальные и изменяющие акты;
2. `ActualPravoConnector` — официальный сводный текст и доступные редакции для поддерживаемых категорий; используемый сайтом JSON-интерфейс считается недокументированным внешним контрактом и изолируется внутри адаптера;
3. `LegislationRussiaConnector` — официальные тексты актов, включая постановления и распоряжения Правительства, которых недостаточно искать только в разделе `actual`;
4. `MinjustAndRegionalConnector` — реестровые реквизиты и переход к официальному региональному или муниципальному источнику; запись реестра не подменяет проверку официального опубликования.

Интеграционный парсер выполняет discovery, загрузку, определение формата по содержимому, вычисление SHA-256, извлечение транспортных метаданных и первичное сопоставление `исходный акт ↔ изменяющий акт ↔ кандидат редакции`. Он не применяет поправки «по смыслу» и не утверждает применимость нормы. Если официального сводного текста нет, создаётся исключение для отдельного проверяемого процесса реконструкции редакции.

Выход:

```text
SourceSystem + AcquisitionRun + SourceAsset
PublicationEvent + EditionCandidate + SourceRelation
```

Обязательный минимум provenance:

```text
source_system, adapter_version, external_document_id, source_url,
discovered_at, acquired_at, http_metadata, declared_act_identity,
publication_number/date, declared_edition, mime_detected,
raw_sha256, storage_uri, rights_status, acquisition_status
```

Gate: повторный запуск без изменений не создаёт дубликаты; изменение исходника создаёт новый immutable asset и diff; сбой источника не удаляет последнюю утверждённую редакцию; у каждого кандидата есть сырой файл/ответ, URL, время получения и версия адаптера. Массовая загрузка включается только после проверки условий источника, rate limits и устойчивого повторного получения на пилоте.

### Шаг 1. Source registration

Вход: asset интеграционного парсера, legacy-файл из `LAW_Data` или контролируемый upload.  
Выход: immutable `SourceAsset`.

Обязательные поля:

```text
source_asset_id, source_url, publisher, acquired_at,
file_name, mime_type, raw_sha256, storage_uri,
authority_level, review_status, rights_status
```

Gate: тип/размер/антивирус, обязательные реквизиты, hash duplicate check.

Имя файла, папка `current/historical/future` и дата получения записываются как metadata импорта. Они не заполняют автоматически `valid_from/to`.

### Шаг 2. Physical extraction и OCR

Вход: immutable original.  
Выход: layout IR с текстовыми блоками, стабильными offsets, а для PDF/сканов — доступными страницами, bbox, таблицами и confidence.

OCR запускается только для страниц без надёжного text layer или с обнаруженной деградацией. Для кириллицы необходимо отдельно измерять CER/WER на сканах с числами, отрицаниями и ссылками.

Gate: пустые страницы, подозрительно малый объём, сломанный reading order, потерянные таблицы.

### Шаг 3. Deterministic cleanup

Удаляются или маркируются колонтитулы, служебные строки, повторяющиеся заголовки и переносы. Каждый удалённый диапазон попадает в отчёт; «тихая потеря» запрещена.

### Шаг 4. `ActIdentity` и `LegalStructureParser`

Сначала компилятор выделяет и проверяет `ActIdentity`: вид, издатель, номер, дату принятия, юрисдикцию, источник и признаки редакции. Неуверенные реквизиты остаются явными исключениями. Только после этого state machine строит Legal AST:

```text
document → division/section/chapter → article → part → item → subitem
                                           └→ appendix/table/note
```

Профили парсинга задаются по типу акта. Каждое положение получает `address_key`, `provision_id` внутри редакции и offsets. Неуверенный заголовок становится `unresolved_block`, а не выдуманной статьёй. Связь с положением другой редакции создаётся только при наличии проверенного основания.

### Шаг 5. Review gate и очередь исключений

HTML-отчёт показывает дерево рядом с исходным текстом или страницей. Полный документ проходит автоматические проверки покрытия, порядка, уникальности адресов, дат и сохранности таблиц. Проверяющий видит:

- missing/unresolved spans;
- low-confidence OCR;
- duplicate IDs;
- таблицы и приложения;
- edition dates и источник;
- diff с предыдущей сборкой.

Инженер отвечает за физическое извлечение, offsets и нарушения структуры; юридический проверяющий — за идентичность акта, редакцию, смысловую структуру и спорные gold labels. Триаж направляет чистые, спорные и повреждённые файлы на разный объём проверки, но сам по себе не утверждает норму. Решение принимается на уровне файла/редакции с отдельным списком нерешённых блоков; выборка положений служит дополнительным аудитом, но не заменяет проверки всего текста. Нормы с нерешёнными критическими ошибками не индексируются как утверждённые. Критерии возможного автоматического утверждения определяются только после измерения ошибок на пилоте (§20).

### Шаг 6. Canonical persistence

Сохраняются `LegalAct`, `LegalEdition`, `LegalProvision`, `EvidenceSpan`, `ProvisionLineage`, `ProvisionRelation` и `CorpusBuild`. Для неполной временной истории хранится статус покрытия: неизвестный интервал не заменяется датой снимка.

### Шаг 7. Search projections

Для одной нормы допускаются несколько версионированных представлений:

1. whole provision;
2. дочерний clause с унаследованным heading path;
3. metadata-rich text для поиска по реквизитам;
4. отдельное representation таблицы/приложения;
5. linked-context projection, созданное по явной cross-reference.

Overlap между разными provisions или редакциями запрещён. Token-aware splitter допускается только внутри одного слишком длинного provision и сохраняет общий `provision_id` и offsets.

### Шаг 8. Build report и atomic activation

Сборка фиксирует версии, исключения, затраты времени проверяющих и метрики. Новая `corpus_version` активируется атомарно после structural tests, retrieval regression и утверждения применимой области корпуса. Переход на другой поисковый движок использует тот же `CorpusBuild`: параллельная сборка проекции, сравнение выдачи, переключение активной версии и откат без изменения канонических данных.

## 9. Runtime-пайплайн вопроса

```text
1. Parse request
   question + as_of_date + jurisdiction + source scope
        ↓
2. Deterministic resolver
   act/article/date aliases, ambiguity, ACL
        ↓
3. Route
   statute | case law | case documents
   then exact lookup | scoped retrieval | broad fallback
        ↓
4. Hard prefilter
   verified edition coverage + jurisdiction + approval + ACL
   unknown temporal coverage → clarify/abstain
        ↓
4a. Conditional query expansion — только эксперимент M3
   original query always retained; typed variants only for implicit/multi-issue queries
   inferred conditions remain hypotheses; missing decisive fact → clarify
        ↓
5. Candidate retrieval
   lexical ∥ dense ∥ direct references over original + bounded query variants
        ↓
6. Fusion/diversity
   optional RRF, per-act quotas, collapse duplicates
        ↓
7. Evidence selection
   rerank only if proven; expand parent and explicit links
        ↓
8. Sufficiency gate
   enough evidence? otherwise clarify/refuse
        ↓
9. Structured answer draft
   atomic claims + citation handles
        ↓
10. Two audits
    reference_valid + claim_supported
        ↓
11. One bounded repair OR answer/refusal
```

Одна попытка исправления — исходный бюджет, а не доказанный оптимум. Число попыток, p95 полной задержки, стоимость запроса и частота лишних отказов измеряются по типам маршрута; вариант с 2–3 попытками остаётся экспериментом (§20).

### 9.1. Маршруты

- **Exact route:** известны акт, статья/пункт и дата — `get_provision`, без embeddings.
- **Scoped semantic route:** распознан акт/редакция, неизвестен provision — поиск внутри scope плюс широкий fallback.
- **Exploratory route:** бытовая формулировка без реквизитов — lexical+dense candidates.
- **Multi-authority route:** вопрос требует нескольких актов — отдельный candidate pool и минимальная квота на каждый распознанный authority.
- **Temporal route:** дата фактов отличается от текущей — поиск только в подтверждённом интервале покрытия; при пробеле истории запрос уточняется или завершается `temporal_coverage_unknown`, без web-search recency shortcut.
- **Case-law route:** отдельный индекс и ранжирование по суду, инстанции, процессуальной роли, holding и subsequent treatment; найденные дела не смешиваются с нормами до позднего evidence merge.
- **Case-document route:** пользовательские материалы изолированы ACL/RLS и никогда не приобретают статус authority только из-за попадания в retrieval.
- **No-evidence route:** нет достаточной нормы — типизированный отказ: `missing_date`, `temporal_coverage_unknown`, `wrong_jurisdiction`, `no_applicable_authority`, `unresolved_reference`, `conflicting_authority` или `insufficient_evidence`.

### 9.2. Необходимые наружные tools

Минимальный API агента:

```text
search_legal_corpus(query, as_of_date, jurisdiction, scopes, top_k)
get_provision(act_ref, provision_ref, as_of_date)
get_edition(act_ref, as_of_date)
expand_cross_references(provision_id, relation_types, max_hops)
verify_citations(citation_handles, as_of_date)
request_human_review(reason, evidence_bundle)
```

Агент не получает SQL, shell, произвольный vector-store API и возможность создавать citation ID.

## 10. Каноническая модель данных

### 10.1. Основные сущности

| Сущность | Назначение | Ключевые поля |
|---|---|---|
| `SourceSystem` | внешний официальный или legacy-источник | source type, authority scope, base URL, adapter/version, access and rights status |
| `AcquisitionRun` | воспроизводимый запуск синхронизации | source, cursor/window, started/finished, adapter version, counts, errors, report |
| `SourceAsset` | неизменяемый исходник | URL, publisher, raw SHA-256, storage URI, acquired_at, rights status |
| `PublicationEvent` | факт официального опубликования | external ID, publication number/date, source asset, published act identity |
| `EditionCandidate` | ещё не утверждённый сводный текст или снимок | claimed edition, source asset, related publications, reconciliation/review status |
| `SourceRelation` | связь материалов источника | original/amends/consolidates/annuls/attachment, endpoints, evidence, review status |
| `LegalAct` | стабильная идентичность акта | `act_id`, type, number, issuer, jurisdiction, adopted_at, identity review |
| `LegalEdition` | конкретный проверенный снимок | `edition_id`, captured_at, declared revision date, подтверждённые `valid_from/to` (nullable), coverage evidence/status |
| `LegalProvision` | положение в одной редакции | `provision_id`, `edition_id`, `address_key`, kind, label, parent, order, text, content hash |
| `TemporalCoverage` | проверенная применимость редакции или нормы | scope (`edition`/`provision`), interval, source evidence, review status |
| `EvidenceSpan` | координата доказательства | extracted-text offsets и extractor version; page/bbox при наличии; quote, source hash |
| `ProvisionLineage` | проверенная связь версий нормы | from/to `provision_id`, same/renumbered/split/merged/repealed, evidence, reviewer |
| `ProvisionRelation` | явная связь норм | type, source/target provision, confidence/review |
| `SearchProjection` | поисковое представление | projection type, text, tokens, model/index versions |
| `CorpusBuild` | воспроизводимая сборка | source/parser/chunker/model hashes, status, report |
| `ReviewDecision` | проверяемое утверждение структуры и области действия | file/edition scope, reviewer, policy version, exceptions, decision time |
| `CitationHandle` | ссылка на проверенный evidence в рамках запроса | query run, edition, provision, span hash, status; expiry/capability только при внешнем API |
| `QueryRun` | аудит retrieval | original query, typed variants/hypotheses, planner decisions/stop reason, routes, filters, candidates, scores, versions, latency/tokens/cost |
| `AnswerClaim` | атомарное утверждение | claim text, evidence links, support status |

### 10.2. Судебная практика

Судебные акты не следует насильно превращать в `LegalProvision`. После MVP для нормативных актов создаётся отдельный модуль `CaseLawDocument/DecisionPassage/Holding/Citation`. Он использует dense/hybrid retrieval и нормализацию ссылок, но evidence contract и claim audit остаются общими.

## 11. Агент приложения

### 11.1. Что такое агент здесь

Это bounded state machine, а не свободный autonomous loop. Его состояния:

```text
scope resolution → retrieval → evidence sufficiency → draft
→ citation/claim audit → one repair → answer | abstain | human review
```

Maximum steps, model budget, allowed tools, ACL, temporal rules и output schema контролируются программой, а не prompt.

### 11.2. Когда нужен LangGraph

LangGraph оправдан после работающего retrieval API, когда нужны:

- persistent state и возобновление после сбоя;
- SSE/streaming;
- pause/resume для human-in-the-loop;
- явные bounded branches;
- аудируемая история состояния.

Доменное ядро не импортирует LangGraph. Nodes вызывают application services. Side effects идемпотентны, потому что interrupted node при resume может выполниться повторно.

### 11.3. Почему не multi-agent-first

Researcher/Auditor/Adjudicator полезны как разделение обязанностей, но не требуют трёх автономных агентов. Сначала это три функции/узла с одним audit trail. Отдельные модели/контексты добавляются только при измеренном выигрыше claim support или refusal calibration.

Тот же принцип применяется к query understanding. Сначала один вызов модели возвращает несколько типизированных поисковых представлений и полный trace. Adaptive planner добавляется только если на закрытом multi-issue/implicit-query срезе он превосходит этот baseline с учётом semantic drift, ложных дополнений, p95, tokens и стоимости. GRPO допустим лишь при отдельном training split и не может оптимизироваться только на recall без safety-метрик.

## 12. Выбор стека

### 12.1. Backend

**Выбор:** Python + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic + psycopg 3.

Почему:

- лучшая совместимость с document AI, OCR, embeddings, rerankers и LLM SDK;
- типизированные OpenAPI/tool schemas;
- один язык для compiler, retrieval, evals и agent nodes;
- проще воспроизводимые эксперименты.

### 12.2. Хранилище и поиск

**M0–M2:** PostgreSQL как source of truth, точный поиск по `act_id/address_key/edition_id` и PostgreSQL FTS с явной конфигурацией `russian`. Отдельно тестируются нормализация реквизитов, аббревиатур, номеров, фраз и отрицаний. Есть два разных сравнения: (1) старый FTS5 против нового structure-aligned pipeline на одинаковых исходных актах и вопросах — эффект всей переработки; (2) FTS5 против PostgreSQL FTS на идентичных `SearchProjection` — эффект движка/анализатора.

**M3:** pgvector с exact vector scan добавляется только для измеряемого dense baseline. RRF и reranker остаются абляциями.

**OpenSearch подключается**, если benchmark показывает выигрыш его BM25, анализаторов, phrase/proximity queries, field weights или масштабируемого hybrid index по сравнению с настроенной русской FTS на том же корпусе. Ни один анализатор не гарантирует качество без измерения.

**Qdrant подключается** только при доказанном vector-throughput/latency bottleneck. Одновременно OpenSearch и Qdrant в первом production-релизе не нужны.

PostgreSQL остаётся source of truth; любые search engines — перестраиваемые projections. Для миграции новая проекция собирается рядом со старой из того же `CorpusBuild`, проходит shadow-сравнение recall/latency и переключается атомарно с возможностью отката.

### 12.3. Ingestion workers

- MVP: воспроизводимые команды `source sync` и `corpus build`, таблицы `acquisition_run` и `ingestion_run`;
- затем: отдельный worker process;
- при устойчивой очереди тяжёлых задач: Celery + RabbitMQ в Linux/WSL2 containers;
- получение идемпотентно по `(source_system, external_document_id, raw_sha256, adapter_version)`, компиляция — по `(source_hash, pipeline_version)`;
- курсор источника, retry/backoff, rate limit и последний успешный checkpoint хранятся явно; IP-адреса и внутренние endpoint не зашиваются за пределами конкретного адаптера.

### 12.4. Frontend

В M1 достаточно самодостаточного HTML-отчёта для отладки структуры; в M2 нужен просмотр источника по `get_provision`. TypeScript + React вводится для полноценного приложения позже. Его минимальные экраны:

- вопрос и параметры даты/юрисдикции;
- ответ с claim-level citations;
- evidence viewer: цитата рядом с изображением/страницей;
- причина отказа/неопределённости;
- corpus build/review UI для редактора;
- admin-only evaluation dashboard.

### 12.5. Модели и локальное железо

На RTX 5070 Ti 16 GB / 32 GB RAM разумно локально запускать embeddings, reranker, OCR, классификаторы и 7–14B quantized auxiliary model. Это не основание заранее выбирать локальную модель финального юридического ответа.

Это перечень возможных задач, а не требование держать все модели в VRAM одновременно. В M0–M2 фиксируются профиль памяти, допустимая параллельность и p95 для extraction и query path. OCR/индексация отделяются от интерактивного ответа по процессам или расписанию; очередь сама по себе не устраняет конкуренцию за одну GPU.

Windows development:

- `llama.cpp` для локальных GGUF и простого OpenAI-compatible server;
- WSL2/Docker для worker stack;
- не поднимать одновременно OpenSearch, Qdrant, observability stack и крупную LLM без необходимости.

Linux production:

- vLLM для concurrent local inference;
- cloud model adapter как альтернативный provider;
- единый gold set и одинаковые acceptance gates для local/cloud.

### 12.6. Observability и evals

OpenTelemetry/OpenInference в коде; self-hosted Opik — разумный первый trace/eval UI. Raw private text не уходит в telemetry по умолчанию: redaction, sampling и retention обязательны.

## 13. Evaluation-first программа

### 13.1. Набор данных

Первый vertical slice: пять разнотипных актов и **30–50 вручную проверенных вопросов**, привязанных к реально разобранным редакциям и source spans. Набор делится на рабочие примеры для отладки и закрытые gate-примеры для регрессии. Это smoke-набор M0–M2, а не статистическое доказательство качества публичного ответа. После стабилизации parser/retrieval набор расширяется по классам ошибок до нескольких сотен с неизменяемым закрытым test split; число 200–300 — гипотеза о масштабе следующего этапа, а не критерий само по себе.

Начальный gate set покрывает точный реквизит, перефразировку, исключение/отрицание, подтверждённую дату, отсутствие покрытия и одну перекрёстную ссылку. Остальные классы ниже входят в отдельные тематические и adversarial-наборы по мере появления соответствующих источников и функций. Нельзя считать 30 или 50 примеров надёжной оценкой редкой ошибки: при нуле ошибок в 50 независимых примерах верхняя односторонняя 95% граница частоты ошибки всё ещё около 5,8%.

Обязательные классы:

- точный номер статьи/пункта;
- бытовая перефразировка;
- исключение и отрицание;
- историческая и будущая редакция;
- перекрёстная ссылка;
- вопрос по нескольким актам;
- приложение/таблица;
- отсутствующий ответ;
- ложная предпосылка;
- скрытое бытовое или отраслевое выражение, не совпадающее с термином нормы;
- multi-issue вопрос, требующий основной и вспомогательной нормы;
- отсутствующий юридически решающий факт, который должен вызвать уточнение, а не модельное дополнение;
- несколько альтернативных допустимых норм;
- OCR-искажение числа/«не»;
- шумовые похожие документы;
- правдоподобный, но ложный текст нормы;
- реальный акт с неверной датой или юрисдикцией;
- конфликтующие источники и удалённый bridge evidence;
- prompt injection внутри пользовательского или индексируемого документа.

Закрытые test questions и правильные provision IDs не участвуют в ingestion, query expansion, prompt tuning или выборе конфигурации по отдельным ошибкам. Это прямой урок ошибки Index-RAG.

Юридический проверяющий утверждает допустимые `act_id/address_key/provision_id`, редакцию, source span и альтернативные верные основания; инженер готовит выгрузку, trace и проверку формата. Спорные метки проходят второе заключение. Время на разметку каждого вопроса и доля споров записываются для оценки ресурсов.

### 13.2. Метрики по слоям

| Слой | Метрики |
|---|---|
| Extraction | text coverage, CER/WER, page/table coverage, unresolved spans |
| Parser | hierarchy accuracy, ID stability, parent/ordering validity |
| Review | часы на документ/исключение, доля нерешённых блоков, межэкспертные расхождения |
| Routing | act recall, edition accuracy в подтверждённом интервале, temporal coverage recognition, scope precision |
| Query transformation | recall delta к исходному запросу, useful expansion rate, semantic drift, fabricated-condition rate, число rewrite/retrieval rounds |
| Retrieval | provision/case recall@k, MRR, nDCG, alternative-authority и cross-reference coverage |
| Evidence | precision/recall, citation exact match, citation completeness |
| Answer | correctness, claim support, authority hit, abstention precision/recall, unnecessary refusal |
| System | end-to-end и поэтапные p50/p95 по маршрутам, VRAM, tokens, стоимость запроса/сборки, index size, build time |

Общая «оценка ответа» не заменяет component metrics.

### 13.3. Acceptance gates

Детерминированные gates для M0–M2: 100% исходного текста учтено как распознанный, явно `unresolved` или документированно исключённый служебный span; повторная сборка с теми же версиями даёт те же ID/хеши; точные реквизиты из фиксированных проверочных примеров разрешаются в нужный `provision_id`; на тестовых датах вне подтверждённого покрытия система не утверждает применимость редакции.

Для измеряемых retrieval/answer-метрик пороги и допустимое ухудшение фиксируются **после baseline, но до настройки кандидата на закрытом test split**. Перед M4 владелец продукта также утверждает бюджет p95 и стоимости по типам запросов; измеряется весь пользовательский путь, включая аудит и repair. Значения без baseline не считаются обещанием качества.

Query expansion принимается только если улучшает provision recall на закрытом implicit/multi-issue срезе, не ухудшает exact/date/negation классы и не меняет hard filters. Добавленный моделью факт считается ошибкой независимо от того, помог ли он найти gold provision. Multi-step planner принимается только при дополнительном выигрыше относительно one-call structured multi-query в пределах утверждённого бюджета.

Новая версия не активируется, если:

- падает edition accuracy;
- current/historical/future смешиваются;
- provision recall ухудшается сверх заранее заданного tolerance;
- растёт unsupported-claim rate;
- ухудшается correct refusal;
- появляются необъяснённые пропуски текста;
- provenance перестаёт доходить до UI.

## 14. Этапы реализации

### Роли и ресурсный план

До оценки сроков полного M0–M7 пилот фиксирует фактические часы инженера на extractor/parser/UI, часы юридического проверяющего на акт и спорное положение, часы на gold label и повторное заключение, а также стоимость OCR/LLM и профили CPU/GPU. Прогноз ручной работы строится из измеренных `число актов × время на акт + число исключений × время на исключение + число вопросов × время на метку`, с отдельным резервом на расхождения экспертов. После первых пяти актов эти значения превращаются в диапазоны трудоёмкости и график M0–M2; сокращение объёма выбирается явно, если ресурс не укладывается в бюджет.

Роли: инженер корпуса и API, юридический проверяющий с предметной компетенцией, владелец продукта для бюджета/допустимого риска. Один человек может выполнять несколько ролей, но время и полномочия каждой фиксируются отдельно. Публичный выпуск дополнительно требует правовой оценки продукта (§16).

### M0. Интеграционный парсер НПА, контракты и gold set

Результат: минимальное приложение интеграционного парсера, которое через `PublicationPravoConnector`, пилотные `ActualPravoConnector` и `LegislationRussiaConnector` воспроизводимо получает пять репрезентативных актов, их официальные публикации и доступные сводные редакции. Созданы immutable raw archive, `AcquisitionRun`, source manifest, отчёт повторной синхронизации и очередь несопоставленных поправок. После этого фиксируются контракт `ActIdentity → snapshot/coverage → Legal AST`, правила `act_id/address_key/provision_id/ProvisionLineage`, 30–50 размеченных вопросов с рабочей и закрытой частями, baseline FTS и детерминированные acceptance gates.  
Gate: второй запуск корректно различает unchanged/new/changed/failed; ни один принятый исходник не зависит от экспорта коммерческого агрегатора; у каждого кандидата редакции есть официальный URL, raw SHA-256, заявленная редакция и связи с найденными публикациями. Каждый gold answer связан с проверенным адресом, конкретной редакцией и source span; непокрытые даты маркированы, спорные labels проходят вторую проверку; измерены часы и стоимость первого цикла.

### M1. Read-only corpus compiler

Результат: пять документов, полученных интеграционным парсером, проходят `SourceAsset → extraction → cleanup → ActIdentity → Legal AST → HTML review report`; отчёт показывает дерево, цитату, source reconciliation, diff и очередь исключений.  
Gate: детерминированная повторная сборка, весь текст учтён, таблицы/приложения не потеряны, unresolved spans объяснимы; измерена доля исключений и пропускная способность review.

### M2. Canonical PostgreSQL и exact retrieval

Результат: импорт approved AST, точный `get_provision`, просмотр исходной цитаты, запросы по подтверждённым временным интервалам и FTS baseline на тех же текстах, что старый FTS5.  
Gate: точные проверочные реквизиты разрешаются корректно; применимость не утверждается за пределами подтверждённого покрытия; недостающая дата не маскируется; новое и старое ранжирование сравниваются без подмены корпуса.

### M3. Measured retrieval

Результат: абляция русской FTS/нормализации реквизитов, затем dense, one-call structured multi-query, optional bounded multi-step planner, optional RRF/reranker и linked context.  
Gate: каждая добавленная стадия имеет отдельную абляцию и измеримый выигрыш; query variants и причины остановки сохраняются в `QueryRun`, не меняют hard filters и не подменяют отсутствующие факты.

### M4. Evidence/answer service

Результат: atomic claims, ссылки на evidence в рамках запроса, reference verifier, claim-support audit, abstention.  
Gate: неподтверждённые ключевые claims не выходят пользователю; p95 полной задержки и стоимость на маршрутах укладываются в заранее утверждённый бюджет.

### M5. Bounded agent и frontend

Результат: LangGraph orchestration при необходимости, SSE, human review, React UI.  
Gate: агент не обходит retrieval API и не создаёт свободные ссылки.

### M6. Production hardening

Результат: OIDC/RBAC, RLS/ACL, worker queue, backups/PITR, restore drill, immutable builds, security/failure/load tests; до публичного выпуска — правовая оценка способа оказания услуги, описания возможностей и ограничений ответа, ответственности, прав на контент и обработки пользовательских документов.  
Gate: reproducible deployment, rollback corpus/index version и закрытые продуктовые/правовые вопросы по выбранному сценарию выпуска.

### M7. Scale decision

По профилю ошибок выбрать: остаться на PostgreSQL, добавить OpenSearch или вынести vector projection в Qdrant. Решение принимается по benchmark, а не по популярности продукта; переход делается через параллельную проекцию, shadow-сравнение и переключение с откатом. Отдельный модуль судебной практики остаётся целью будущего приложения, но не блокирует нормативный M0–M2.

## 15. Что не делать сейчас

- Не строить приложение внутри `LAW_Data`.
- Не делать страницу канонической нормой.
- Не использовать universal fixed-size/semantic chunker через границы provisions.
- Не считать RRF, reranker или GraphRAG обязательными до A/B.
- Не использовать LLM как единственный parser.
- Не давать агенту SQL или прямой vector-store доступ.
- Не разрешать LLM свободно писать номера статей/дел как citations.
- Не выдавать `reference_valid` за `claim_supported`.
- Не обучать/расширять индекс evaluation questions и их labels.
- Не использовать LLM-generated gold без human audit.
- Не копировать CPBD-код без ясной лицензии.
- Не запускать multi-agent architecture или GRPO до сильного детерминированного baseline и доказанного проигрыша one-call structured multi-query.
- Не выбирать embedding/reranker по англоязычному benchmark вместо русского gold set.
- Не разворачивать PostgreSQL + OpenSearch + Qdrant одновременно «на будущее».

## 16. Ключевые риски

| Риск | Контроль |
|---|---|
| неправильная редакция | hard temporal prefilter, edition ID в citation |
| снимок принят за полную историю | отдельно хранить `captured_at`, дату редакции и подтверждённый интервал; отвечать только в пределах покрытия |
| одинаковый адрес нормы ошибочно принят за преемственность | разделить `address_key` и `provision_id`, проверять `ProvisionLineage` |
| OCR исказил число/отрицание | confidence gate, page viewer, human queue |
| parser придумал структуру | unresolved blocks, golden trees, review UI |
| review queue не успевает за корпусом | проверять весь текст автоматически, вести очередь исключений и измерять часы/документ |
| router обрезал recall | scoped route + обязательный broad fallback |
| ANN under-fetch после фильтра | exact baseline, recall test, iterative scan/partition |
| citation существует, но не поддерживает claim | отдельный claim-support audit |
| prompt injection в документе | corpus content всегда data, tools allowlist, policy вне контекста |
| повтор worker job повредил индекс | immutable builds, idempotency key, atomic activation |
| provider/model drift | model revision + prompt/schema version + regression gate |
| LLM judge создаёт ложную уверенность | deterministic metrics + human adjudication |
| смена поискового движка ломает выдачу | одна версия `CorpusBuild`, shadow index, сравнение и атомарный rollback |
| GPU перегружена конкурентными задачами | профили VRAM/p95, ограничение параллельности, разделение ingestion и ответа |
| права на данные/модели | отдельный реестр code/model/data licenses и rights review |
| чувствительные документы в traces | redaction, sampling, retention, access controls |
| публичный ответ создаёт неоценённый продуктовый/правовой риск | до релиза определить сценарий услуги, роль человека, ответственность и требования к пользовательским документам с профильным специалистом |

## 17. Наиболее полезный первый вертикальный срез

Первый deliverable — интеграционный парсер НПА и проверяемый набор официальных исходников. Отладочный HTML-отчёт и точный поиск строятся поверх него; полноценный frontend и агент следуют позже:

```text
официальные сервисы
  → PublicationPravoConnector + ActualPravoConnector + LegislationRussiaConnector
  → discovery + immutable raw archive + source manifest
  → сопоставление публикаций, поправок и кандидатов редакций
  → повторная синхронизация + change report
  → 5 разнотипных актов без зависимости от экспортов агрегаторов
  → extractor bake-off
  → deterministic cleanup
  → ActIdentity + статус временного покрытия
  → LegalStructureParser
  → Legal AST + address_key/provision_id + source spans
  → HTML review report + diff + очередь исключений
  → 30–50 вопросов: рабочая и закрытая части
  → exact lookup + русская FTS на сопоставимом корпусе
```

После этого можно ответить на четыре главных вопроса:

1. Можем ли мы независимо и повторяемо получать официальные публикации и сводные редакции, обнаруживать изменения и объяснять пробелы источников?
2. Можем ли мы воспроизводимо восстановить юридическую структуру без потери текста?
3. Улучшает ли structure-aligned representation поиск относительно существующего FTS5 на тех же актах и вопросах, и что отдельно даёт смена движка при одинаковых `SearchProjection`?
4. Доходит ли проверяемое основание от официального сетевого источника до простого просмотра цитаты, и сколько стоит его проверка человеком?

Если ответ на первый вопрос отрицательный, embeddings и агент только быстрее найдут неправильно подготовленный материал.

## 18. Опорные первичные источники

### Legal RAG и evaluation

- [Legal RAG Bench](https://arxiv.org/abs/2603.01710)
- [Benchmarking Legal RAG / LaborBench](https://doi.org/10.1145/3788646.3789533)
- [CanLegalRAGBench](https://arxiv.org/abs/2605.30497)
- [bLLeQA](https://aclanthology.org/2026.knowfm-1.4/)
- [Chunking German Legal Code](https://arxiv.org/abs/2605.19806)
- [Structure-Aware Retrieval and Safety](https://aclanthology.org/2026.acl-long.2112/)
- [CRAwLeR](https://arxiv.org/abs/2606.21676)
- [Temporal Misgrounding](https://arxiv.org/abs/2608.09393)
- [Asking For An Old Friend](https://arxiv.org/abs/2605.23497)
- [Grounded in Law](https://aclanthology.org/2026.propor-2.9/)
- [How Much Do Legal RAG Systems Still Hallucinate?](https://arxiv.org/abs/2608.14210)
- [AALawyer](https://aclanthology.org/2026.acl-long.633/)
- [CLERC](https://aclanthology.org/2025.findings-naacl.441/)
- [IL-PCSR](https://aclanthology.org/2025.emnlp-main.738/)
- [Know When to Fuse](https://aclanthology.org/2025.coling-main.290/)
- [Sycophants in the Courtroom / LEGAL-LINK-EU](https://aclanthology.org/2026.acl-long.497/)
- [Decompose-and-Refine](https://arxiv.org/abs/2605.24454)
- [LegalMALR](https://arxiv.org/abs/2601.17692v1); [текущий code repository](https://github.com/lyxx3rd/LegalMALR) и [CSAID](https://github.com/lyxx3rd/CSAID) проверены 27.09.2026
- [STARD](https://aclanthology.org/2024.findings-emnlp.625/)
- [LegalGraphRAG](https://aclanthology.org/2026.acl-long.1738/)
- [LawThinker](https://arxiv.org/abs/2602.12056)
- [GANDR](https://arxiv.org/abs/2609.10293)
- [CiteGuard-RAG](https://arxiv.org/abs/2609.15830)
- [Answer–Authority Decoupling](https://arxiv.org/abs/2608.02621)
- [Citation-Closure Retrieval](https://arxiv.org/abs/2605.29742)

### Конкурс и открытые реализации

- [Официальный ARLC leaderboard](https://agentic-challenge.ai/leaderboard)
- [COLIEE 2025 overview](https://coliee.org/COLIEE2025/overview)
- [COLIEE 2026 evaluation](https://coliee.org/COLIEE2026/evaluation)
- [CPBD solution](https://github.com/azamat1ch/difc-legal-rag/blob/main/docs/solution.md)
- [CPBD gold labeling](https://github.com/azamat1ch/difc-legal-rag/blob/main/docs/gold-labeling.md)

### Выбранный стек

- [FastAPI](https://github.com/fastapi/fastapi)
- [PostgreSQL full-text search](https://www.postgresql.org/docs/current/textsearch-controls.html)
- [PostgreSQL Russian text-search configuration](https://www.postgresql.org/docs/18/textsearch-psql.html)
- [pgvector](https://github.com/pgvector/pgvector)
- [OpenSearch hybrid search](https://docs.opensearch.org/latest/vector-search/ai-search/hybrid-search/index/)
- [OpenSearch Russian analyzer](https://docs.opensearch.org/latest/analyzers/language-analyzers/russian/)
- [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Docling](https://github.com/docling-project/docling)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- [vLLM](https://github.com/vllm-project/vllm)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
- [Opik](https://github.com/comet-ml/opik)

Исследовательский workflow опирался на: Timothy Kassis, Vinayak Agarwal, Yuhuan He, Darshil Patel, Aubrey M. Brueckner. *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. arXiv:2609.00065 (актуализация записи 04.09.2026), [DOI](https://doi.org/10.48550/arXiv.2609.00065).

## 19. Проверяемые ссылки на локальные выводы

- Каноническая модель и поисковые проекции: `LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md:421-543`.
- Temporal filters: `LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md:545-572`.
- Retrieval и agent tools: `LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md:619-816`.
- Citation boundary: `LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md:797-836`.
- Evaluation: `LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md:927-1004`.
- Структура/время/claim audit в литературе: `legal_rag_2026_literature_review_ru.md:50-196`.
- Критика Index-RAG: `review-index-rag.md:12-116`.
- Gless/CPBD и расхождения retrieval: `ARLC_2026_LEGAL_RAG_ANALYSIS.md:203-410`.
- Перенос в проект и vertical experiment: `ARLC_2026_LEGAL_RAG_ANALYSIS.md:412-537`.
- Практическая программа исследований: `RESEARCH.md:1-87`.

## 20. Альтернативы и идеи под сомнением

Этот раздел сохраняет предложения из независимых рецензий от 24.09.2026, которые могут оказаться полезными, но пока не имеют подтверждённого выигрыша на нашем корпусе. **Статус «альтернатива» или «под сомнением» не означает, что компонент реализован или принят к внедрению.** Для каждой гипотезы заранее фиксируются baseline, test split, стоимость и критерий прекращения эксперимента.

| Идея | Статус и причина неопределённости | Как проверить и когда принять |
|---|---|---|
| Автоматическое утверждение «чистых» официальных файлов | **Под сомнением:** происхождение и хороший text layer не доказывают полноту, правильную редакцию и отсутствие скрытых исключений. | После M1 сравнить решение алгоритма с независимой юридической проверкой случайной выборки и всех рискованных классов; разрешать auto-approval только при заранее установленном допустимом риске и непрерывном аудите. |
| LLM-подсказка для `unresolved_block` | **Альтернатива:** может ускорить трудные документы, но способна выдумать иерархию. | Сравнить долю нерешённых блоков, ложных структур и часы ручной проверки с детерминированным parser-only baseline; подсказка не становится утверждённой нормой без проверок. |
| LLM-as-a-Judge для структуры с порогом `0.95` | **Под сомнением:** число из промпта не является калиброванной вероятностью; экономия 80–90% пока не измерена. | Если пилот покажет пользу, калибровать решение на размеченных ошибках и оценивать false approval отдельно от общей точности; не использовать как единственный gate. |
| Ранний OpenSearch, Meilisearch или иной специализированный search engine | **Альтернатива:** может улучшить отдельные классы запросов, но создаёт второй операционный контур. | На тех же текстах и вопросах сравнить точные реквизиты, русскую морфологию, phrase queries, Recall@k, p95 и стоимость сопровождения с настроенным PostgreSQL FTS; подключать при измеренном выигрыше. |
| 2–3 попытки исправления ответа вместо одной | **Альтернатива:** могут снизить лишние отказы, но увеличить задержку и внести новые ошибки. | A/B по complex queries: claim support, unnecessary refusal, стоимость и p95; остановка при отсутствии улучшения или выходе за бюджет. |
| `Concept Tags` и лёгкий граф неявных связей | **Под сомнением:** тег может расширить recall ценой ложных юридических связей. | Проверить только как поисковую проекцию на multi-hop/перефразированных вопросах; сравнить с FTS+dense+явными ссылками и отдельно оценить false bridge rate. |
| Ранний набор 200–300 gold-вопросов | **Альтернатива по масштабу:** число само по себе не обеспечивает покрытие редких ошибок. | Расширять после M0–M2 по матрице типов запросов и доверительным интервалам; не включать метки test split в настройку retrieval и prompt. |
| Выделенные GPU/CPU для OCR, embeddings, reranker и ответа | **Альтернатива размещения:** зависит от реальной конкурентной нагрузки, VRAM и цены инфраструктуры. | Профилировать ingestion и интерактивный ответ отдельно и вместе; разделять машины/очереди, когда общий ресурс нарушает p95 или бюджет. |
| Conditional structured multi-query и candidate accumulation | **Эксперимент M3:** LegalMALR поддерживает гипотезу для implicit/multi-issue запросов, но его код не опубликован, CSAID мал, а перенос на русское право не проверен. | Сравнить исходный запрос с одним JSON-вызовом, который создаёт typed variants; принять при выигрыше provision recall на закрытом срезе без роста fabricated-condition rate и без ухудшения exact/date/negation, с допустимыми p95/tokens/cost. |
| Adaptive multi-step planner, multi-agent roles и GRPO | **Под сомнением:** выигрыш может происходить от нескольких запросов и большого reranker, а не от agent topology; обучение статьи требует отдельной разметки и существенно больших ресурсов. | Проверять только если one-call multi-query оставляет измеримый recall gap; сравнить при одинаковых retrieval/token budgets и принять лишь дополнительный статистически устойчивый выигрыш. GRPO — только с отдельными train/dev/closed-test splits и safety reward. |
| Metadata injection, hybrid/RRF, reranker и GraphRAG | **Эксперименты более поздних этапов:** результаты чужих корпусов противоречивы или узкоспецифичны. | Включать по одной стадии, сравнивать с неизменным baseline по целевому типу ошибок; удалять стадию без доказанного выигрыша. |

Предложение проверять вручную только 10–20 статей на акт также остаётся **под сомнением**: такая выборка полезна для аудита, но не способна сама подтвердить полноту документа. В M1 решение об утверждении опирается на проверку покрытия всего текста, инварианты структуры и разбор исключений.
