# Рецензия на статью «Index-RAG: Storing Text Locations in Vector Databases for Question-Answering Tasks»

## Метаданные

- **Автор:** Praneeth Vadlapati, Independent Researcher
- **Статус:** препринт, версия 1; опубликован 25 марта 2026 года; рецензирование не пройдено
- **DOI:** [10.20944/preprints202603.2025.v1](https://doi.org/10.20944/preprints202603.2025.v1)
- **Область:** information retrieval, retrieval-augmented generation, provenance/citation tracking
- **Тип работы:** эмпирическая системная работа с открытым исходным кодом
- **Материалы проверки:** [текст препринта](https://www.preprints.org/manuscript/202603.2025), [PDF](https://www.preprints.org/frontend/manuscript/0b445298e81a7f7562166dd3950d5387/download_pub), [репозиторий Index-RAG](https://github.com/Pro-GenAI/Index-RAG), [страница использованного датасета](https://huggingface.co/datasets/dwb2023/ragas-golden-dataset-v2)

## Краткий вывод

Статья ставит важную практическую задачу: сохранить происхождение извлечённого фрагмента и передать в ответ имя файла, страницу и строку. Базовая инженерная идея здравая: координаты источника действительно следует хранить вместе с векторной записью и не поручать языковой модели придумывать их. Плюсами работы являются простота концепции, опубликованный код и внимание к проверяемости ответов.

Однако основные экспериментальные выводы в текущем виде недостоверны. Заявленные результаты получены всего на **12 синтетических вопросах**, хотя статья говорит о загрузке «до 1500» пар из `validation`-split. В действительности датасет имеет только один `train`-split из 12 строк. Ещё важнее, Index-RAG строит query-expansion записи из **самих оценочных вопросов и их правильных document IDs**. Удаление только текущего вопроса оставляет в индексе остальные тестовые вопросы и их метки, то есть протокол остаётся трансдуктивным и использует сведения из тестового набора.

Центральное утверждение о точности цитирования экспериментально не проверено: оценка измеряет ранжирование идентификаторов текстовых контекстов, но загружаемые benchmark-записи не содержат filename/page/line. Опубликованный рабочий RAG-код также не реализует описанный end-to-end путь: question-векторы отбрасываются после top-k поиска, а metadata с координатами не включается в prompt генератора. Поэтому рекомендация — **Reject в текущем виде**, с возможностью новой подачи после полностью переработанной оценки.

## Заявленные вклады

1. Хранение filename/page/line как metadata рядом с embedding для точной локализации источника.
2. Несколько векторов на фрагмент: embedding исходного текста и embeddings синтетических вопросов.
3. Сокращение дублирования исходного текста за счёт ссылок на канонический документ.
4. Улучшение retrieval-метрик относительно single-vector baseline.
5. Применимость к регулируемым областям, где требуется аудит происхождения ответа.

## Проверка основных утверждений

| Утверждение | Представленное доказательство | Оценка доказательства |
|---|---|---|
| Precision@1 улучшена с 66,7% до 83,3% | Один запуск на RAGAS Golden Dataset v2 | **Слабое:** это 8/12 против 10/12 вопросов; нет доверительных интервалов, повторов или теста значимости |
| Precision@5 улучшена с 36,7% до 38,3% | Таблица 2 | **Тривиально малый эффект:** при 12 запросах и `k=5` это 22 против 23 релевантных попаданий из 60 позиций |
| Улучшение отражает обобщение query expansion | Текущий вопрос исключается из совпадения с самим собой | **Не подтверждено:** остальные тестовые вопросы и их правильные документы всё равно используются при построении индекса |
| Система даёт точные filename/page/line citations | Проверяется совпадение document ID | **Не проверено:** benchmark loader не создаёт page/line/file metadata, а координатная точность не является метрикой |
| LLM «не может галлюцинировать цитаты» | Координаты якобы передаются вместе с контекстом | **Неверная гарантия:** модель всё равно может неверно связать утверждение и источник; в опубликованном коде metadata вообще не передаётся в prompt |
| Нет роста latency, overhead мал, масштабируемость высокая | Качественные утверждения | **Не подтверждено:** нет измерений latency, throughput, RAM, размера индекса или стоимости ingestion |
| Подход обеспечивает готовность к GDPR/HIPAA/EU AI Act | Общие ссылки на регулирование | **Переоценено:** эти акты не устанавливают общее требование page/line citations для RAG-ответов |

## Сильные стороны

### S1. Практически важная постановка задачи

Работа правильно отделяет наличие релевантного контекста от проверяемости его происхождения. Для юридических, медицинских и исследовательских сценариев ссылка на конкретный фрагмент действительно полезнее ссылки только на документ.

### S2. Простая и совместимая архитектурная идея

Хранение координат как metadata совместимо с обычными vector stores и не требует нового retrieval-движка. Это делает идею лёгкой для внедрения и независимой от конкретной embedding-модели.

### S3. Открытый код позволяет провести содержательный аудит

Наличие [репозитория](https://github.com/Pro-GenAI/Index-RAG) — существенный плюс. Благодаря ему можно увидеть реальный loader, индексирование, формулу смешивания и production retrieval path, а не оценивать только декларации статьи.

### S4. Авторы признают часть границ применимости

В разделе Limitations отмечены отсутствие проверки на юридических, медицинских и многоязычных корпусах, а также отсутствие проверки faithfulness сгенерированного ответа. Эти оговорки корректны, хотя они не согласуются с более сильными заявлениями в Abstract, Discussion и Conclusion.

## Основные недостатки

### W1. Использование тестовых вопросов и меток при построении индекса

Функция [`_queries_pointing_to_doc`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/scripts/evaluate.py#L262-L273) собирает для каждого документа вопросы из всего `dataset.queries`, используя `relevant_document_ids`. Затем [`build_index_rag_retriever`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/scripts/evaluate.py#L275-L313) помещает эти вопросы в оцениваемый индекс. При тестировании исключается лишь строка текущего вопроса, но сведения от остальных тестовых примеров остаются.

Это не моделирует заявленный production pipeline, в котором вопросы должны генерироваться из документа без знания будущих пользовательских запросов и их правильных ответов. Leave-one-out уменьшает самый очевидный self-match, но не создаёт независимый test set. Нужен разрез по документам: expansions генерируются только из training/ingestion content, а test queries и labels не доступны до оценки.

### W2. Фактический размер датасета — 12, а не «до 1500»

[Карточка датасета](https://huggingface.co/datasets/dwb2023/ragas-golden-dataset-v2) показывает один `train`-split и 12 строк; сама карточка прямо называет малый размер известным ограничением. Код также задаёт [`hf_split = "train"`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/scripts/eval_datasets.py#L33-L43), тогда как статья говорит о `validation`-split.

Число 1500 в коде — только верхний предел CLI (`DEFAULT_MAX_EXAMPLES`), а не фактически использованная выборка. Значения Precision@1 точно соответствуют 8/12 и 10/12. Абсолютное улучшение равно 16,7 процентного пункта, но результат изменился всего на два top-1 исхода. Без доверительных интервалов и paired significance test вывод о стабильном преимуществе делать нельзя.

Дополнительный статический аудит parquet-файла дал 23 связи query-context, 22 уникальных контекста и только один контекст, повторяющийся в двух вопросах. Это крайне хрупкая основа для оценки multi-vector query expansion.

### W3. «Citation accuracy» фактически не измеряется

Статья утверждает, что benchmark содержит ground-truth paragraph locations. Но loader превращает каждый `reference_context` в текстовый document ID и задаёт только `metadata={"dataset": name}`; filename, page и line отсутствуют ([код загрузки](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/scripts/eval_datasets.py#L123-L153)). Метрики проверяют попадание правильного document ID в ranking, а не:

- совпадение страницы;
- совпадение строки или диапазона;
- попадание в правильный evidence span;
- корректность привязки каждого утверждения ответа к цитате;
- полноту цитирования всех проверяемых утверждений.

Это retrieval evaluation, но не citation evaluation. Для последней нужны отдельные ground-truth координаты и метрики correctness/completeness. Например, [ALCE](https://aclanthology.org/2023.emnlp-main.398/) специально разделяет качество ответа и качество цитирования.

### W4. Оцениваемый метод не совпадает с описанным методом

В Methods заявлены paragraph-level segmentation и вопросы, сгенерированные GPT-OSS-20B. В evaluation оба retriever используют одинаковые fixed-token chunks 512/64, а expansions берутся не из генератора, а из размеченных evaluation queries. Код прямо маркирует вариант Index-RAG как [`chunks_plus_question_expansions`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/scripts/evaluate.py#L468-L485).

Следовательно, эксперимент не проверяет описанный ingestion pipeline и не позволяет приписать результат paragraph segmentation, GPT-OSS-20B или генерации вопросов из документов. Нужны отдельные абляции: metadata-only, paragraph chunking, generated expansions, score blending и их комбинации.

### W5. Опубликованный end-to-end код не выдаёт заявленные точные цитаты

Ingestion действительно прикрепляет `file`, `page`, `line_start`, `line_end` к каждой записи ([`ingestion.py`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/utils/ingestion.py#L52-L70)). Но затем production retriever:

1. запрашивает top-k среди paragraph и question записей;
2. **после поиска удаляет все question results**;
3. не разрешает question hit обратно в родительский paragraph.

Это видно в [`retrieval_utils.py`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/utils/retrieval_utils.py#L59-L85). Синтетические вопросы могут занять top-k, после чего будут выброшены, сократив число возвращаемых параграфов.

Далее [`format_docs`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/utils/llm_utils.py#L42-L50) объединяет только `doc.page_content` и не включает metadata. Модель получает инструкцию цитировать источники, но не получает имени файла, страницы или строки. Это прямо противоречит Section III.F и центральному заявлению статьи.

### W6. Ненадёжное вычисление «строк» PDF

[`load_paragraphs`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/utils/ingestion.py#L9-L29) делает `page.extract_text()`, делит результат по `\n\n` и считает строки через число символов `\n`. PDF обычно не содержит семантически стабильных строк текста: порядок и переводы строк зависят от extraction engine, колонок, таблиц, headers и layout. Кроме того, разделители `\n\n`, по которым выполнен split, не учитываются в последующем счётчике.

Поэтому «line 45» не гарантирует ни видимую строку PDF, ни воспроизводимый адрес при другой версии extractor. Для устойчивой цитаты лучше хранить page + bounding box/character offsets + quoted span + hash версии файла.

### W7. Нет доказательств storage, latency и scalability claims

Evaluation использует in-memory linear scan, а production path — Pinecone. Ни один из вариантов не сопровождается измерением latency, throughput или размера индекса. Query expansion создаёт до пяти дополнительных embeddings на paragraph, поэтому overhead embedding storage может быть существенным даже без копирования исходного paragraph text. Утверждения «no increase in query latency», «modest overhead» и «high scalability» требуют сравнительных измерений на нескольких масштабах корпуса.

### W8. Недостаточная воспроизводимость конфигурации

Статья называет `all-MiniLM-L12-v2`, но [`.env.example`](https://github.com/Pro-GenAI/Index-RAG/blob/main/.env.example#L4-L6) задаёт `text-embedding-ada-002`, тогда как локальный host передаёт это имя в [`SentenceTransformer`](https://github.com/Pro-GenAI/Index-RAG/blob/main/index_rag/host_models.py#L26-L31). Не опубликованы полный evaluation report, per-query ranks, embedding cache, seed, точная версия моделей и зависимости lockfile. Нет тестов, подтверждающих корректность page/line extraction и end-to-end citation flow.

### W9. Регуляторные заявления требуют существенного смягчения

Точное provenance полезно для аудита, но оно само по себе не делает систему GDPR-, HIPAA- или EU-AI-Act-compliant. Например, EU AI Act требует для определённых high-risk systems logging, transparency и human oversight, но не вводит общего требования сопровождать каждое утверждение RAG-ответа номером страницы и строки ([официальный текст Regulation (EU) 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)). HIPAA прежде всего регулирует privacy/security и использование или раскрытие protected health information; [официальные материалы HHS](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html) не подтверждают сформулированную в статье обязанность точного source citation.

Корректная формулировка: traceable evidence **может помогать** выполнению отдельных требований аудита и human oversight в конкретном deployment, но соответствие определяется областью применения, классификацией системы, процессами и совокупностью контролей.

## Оценка методологии

| Критерий | Оценка | Обоснование |
|---|:---:|---|
| Soundness | **1/5** | Центральная оценка использует evaluation queries и labels при построении индекса; citation accuracy не измерена |
| Novelty | **2/5** | Полезная сборка известных элементов: vector metadata, synthetic questions и multi-vector retrieval; новый алгоритмический вклад ограничен |
| Reproducibility | **1/5** | Код доступен, но расходится со статьёй; отсутствуют config/report/lockfile/tests; пример embedding-конфигурации противоречив |
| Experimental Design | **1/5** | 12 синтетических вопросов, один узкий домен, нет независимого test split, абляций и сильных baseline |
| Statistical Rigor | **1/5** | Нет uncertainty, significance, повторов или анализа чувствительности; проценты маскируют изменение двух запросов |
| Scalability | **1/5** | Заявлена, но не измерена; evaluation выполняет linear scan, storage/latency/cost не представлены |

## Позиционирование относительно литературы

Генерация вопросов для улучшения retrieval не нова. Работа Sachan et al. уже оценивала [zero-shot question generation для passage retrieval](https://aclanthology.org/2022.emnlp-main.249/) на нескольких open-domain datasets. Doc2Query и последующие методы document expansion также должны быть включены как непосредственные предшественники, причём литература обсуждает query drift, hallucinated expansions и рост индекса.

Точное цитирование тоже уже имеет устоявшуюся декомпозицию. [ALCE](https://aclanthology.org/2023.emnlp-main.398/) оценивает end-to-end ответы, корректность и полноту цитат; [RAGAS](https://aclanthology.org/2024.eacl-demo.16/) отдельно рассматривает retrieval, faithfulness и generation quality. Index-RAG полезно позиционировать не как решение «ранее нерешённой» задачи, а как простую provenance-oriented реализацию, которую ещё требуется сравнить с citation-aware и document-expansion baselines.

Сама возможность хранить metadata рядом с embedding уже является штатной функцией vector databases, что признаёт и статья. Потенциальная ценность работы — не в этом механизме как таковом, а в проверенном end-to-end протоколе координат, родительских связей и цитирования. Именно такой протокол пока не продемонстрирован.

## Вопросы автору

1. Почему в статье указаны `validation` и до 1500 примеров, если код использует `train`, а датасет содержит 12 строк?
2. Почему query expansions строятся из evaluation questions с известными relevant document IDs, а не генерируются из документов до открытия test set?
3. Как именно оценялись page и line accuracy, если loader benchmark не создаёт эти поля?
4. Какие per-query изменения дали прирост Precision@1 с 8/12 до 10/12? Можно ли опубликовать полный report и ranks?
5. Где результаты абляций paragraph segmentation, query expansion, 0.6/0.4 blending и metadata-only варианта?
6. Как question-vector hit в production pipeline преобразуется в родительский paragraph, если код просто отбрасывает question results?
7. Как координаты источника попадают в prompt, если `format_docs` передаёт только `page_content`?
8. На каких корпусах и объёмах измерялись latency, storage overhead и scalability?
9. Чем обоснован выбор line number как устойчивого адреса для PDF вместо bounding boxes, spans и content hashes?

## Мелкие замечания

- После Section V Discussion снова идёт Section V Conclusion; Conclusion должна быть Section VI.
- В Related Work текст ссылается на «Table 2», но качественная таблица подписана как Table 1.
- Термины paragraph-level segmentation и fixed-size 512-token chunking используются непоследовательно.
- Ссылка `[29,30]` при описании датасета, судя по списку литературы PDF, указывает не на обе ожидаемые позиции dataset + RAGAS.
- Утверждение «cannot hallucinate citations» следует заменить на проверяемое и ограниченное: система предоставляет retrieved coordinates, но не гарантирует корректность использования цитаты генератором.
- «Exact line» следует формально определить: extractor line, visual line, source line или character-offset-derived line.
- Качественная таблица сравнения архитектур выставляет i-RAG оценки Exact/Fast/High без эмпирического основания и должна быть заменена измерениями.

## Рекомендуемый корректный эксперимент

1. **Зафиксировать ingestion:** независимый набор документов; page/span/bbox/hash metadata; expansions генерируются только из текста фиксированной моделью и prompt до появления test queries.
2. **Разделить данные по документам:** train/dev/test без пересечения документов, пассажей и перефразированных вопросов.
3. **Использовать несколько наборов:** крупный open-domain benchmark, long-document benchmark и отдельные юридический/медицинский/multilingual наборы с ручной проверкой координат.
4. **Добавить baseline:** BM25, dense single-vector, paragraph dense, Doc2Query, HyDE, late-interaction/multi-vector и metadata-only.
5. **Провести абляции:** segmentation; число synthetic questions; генератор; filtering; blend weight; parent retrieval; reranking.
6. **Измерить citations end-to-end:** location accuracy, evidence-span recall, citation entailment/correctness, citation completeness и answer faithfulness.
7. **Дать статистику:** число запросов, bootstrap confidence intervals, paired significance tests, несколько seeds и per-query results.
8. **Измерить систему:** index size, ingestion time/cost, p50/p95 latency, throughput, RAM и влияние числа expansions.
9. **Исправить production path:** question hit должен ссылаться на parent paragraph; prompt должен включать структурированные coordinates; parser должен проверять, что каждая выданная citation существует в retrieved set.
10. **Опубликовать артефакты:** lockfile/container, exact config, model revisions, seeds, generated expansions и полный JSON report.

## Итоговая рекомендация

**Overall Assessment: Reject (в текущем виде).**

**Confidence: High.** Вывод основан на полном тексте статьи, опубликованном коде и фактической структуре использованного датасета. Главные проблемы непосредственно видны в протоколе оценки и не зависят от субъективной интерпретации результатов.

**Contribution Level: Below threshold.** Идея инженерно полезна, но её новизна умеренно-низкая, а заявленные retrieval, citation, latency и compliance преимущества не подтверждены корректным экспериментом.

Для новой подачи нужны не косметические правки, а независимая переоценка метода и исправление end-to-end реализации.

## Ограничения этой рецензии

Я не перезапускал embedding evaluation: репозиторий не содержит опубликованного cache/report с per-query результатами, а запуск требует внешнего embedding endpoint и точной, незафиксированной авторами конфигурации. Численные выводы о размере выборки и дискретности метрик проверены по открытому parquet-файлу; выводы о leakage и отсутствии citation metadata получены статическим аудитом текущей публичной версии кода. Формальные доказательства в статье отсутствуют.
