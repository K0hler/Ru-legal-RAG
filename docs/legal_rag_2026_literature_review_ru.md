# Legal RAG в 2026 году: быстрый обзор литературы

**Дата поиска:** 19 сентября 2026 года  
**Тип обзора:** rapid scoping review (не полный PRISMA systematic review)  
**Фокус:** retrieval-augmented generation для права: поиск норм и судебной практики, структура и редакции правовых актов, проверяемые ссылки, grounding, hallucination и abstention.

## Краткий вывод

Главный сдвиг 2026 года — от вопроса «какую векторную базу и LLM выбрать?» к вопросу «как доказать, что система нашла правильную норму, правильную редакцию и действительно опирается на неё». Самые убедительные работы сходятся в пяти пунктах:

1. Качество retrieval часто задаёт верхний предел качества всего legal RAG.
2. Нормативный текст нельзя безнаказанно превращать в одинаковые фрагменты: полезно сохранять статью, часть, пункт, иерархию и перекрёстные ссылки.
3. Дата действия нормы должна быть жёстким фильтром, а не пожеланием в prompt.
4. Корректность ссылки, поддержка каждого утверждения источником и корректный отказ — разные метрики.
5. Даже хорошие RAG-системы продолжают выдавать отдельные неподтверждённые утверждения; post-generation citation audit практически значим.

Для проекта с каноническими `LegalProvision` и `LegalEdition` это скорее подтверждение выбранного направления, чем аргумент в пользу замены архитектуры готовым GraphRAG-фреймворком.

## Что читать в первую очередь

### 1. Retrieval и end-to-end оценка

**Butler & Butler — [Legal RAG Bench: an end-to-end benchmark for legal RAG](https://arxiv.org/abs/2603.01710)** — препринт, 2 марта 2026.

- 4 876 фрагментов Victorian Criminal Charge Book, 100 экспертно составленных сложных вопросов.
- Полный факторный эксперимент: три embedding-модели × две LLM, отдельно оцениваются retrieval accuracy, correctness и groundedness.
- Авторы сообщают, что выбор retriever влиял сильнее выбора генератора; доменный embedder улучшил retrieval accuracy на 34 пункта, correctness на 17,5 и groundedness на 4,5 пункта.
- Практический смысл: ошибки retrieval нельзя прятать внутри общей метрики ответа.

**Afane et al. — [Benchmarking Legal RAG: The Promise and Limits of AI Statutory Surveys](https://arxiv.org/abs/2603.03300)** — ACM CS&Law 2026, DOI [10.1145/3788646.3789533](https://doi.org/10.1145/3788646.3789533).

- Проверка multi-jurisdictional statutory research на LaborBench.
- Специализированная STARA достигла 83% по исходной разметке; после обнаружения пропусков в «золотом» обзоре юристов DOL скорректированная оценка составила 92%.
- Заявленные авторами результаты коммерческих систем: 58% Westlaw AI и 64% Lexis+ AI.
- Особенно ценна работа с ошибками ground truth: юридический gold set тоже нуждается в аудите.

**Zhao et al. — [CanLegalRAGBench: Evaluating Retrieval-Augmented Generation on Canadian Case Law](https://arxiv.org/abs/2605.30497)** — препринт, 28 мая 2026, обновлён 18 августа.

- Реалистичные запросы и экспертные ответы по канадской судебной практике.
- Открытые embeddings оказались конкурентоспособны с закрытыми.
- В сгенерированных ответах 8–29% утверждений не поддерживались найденными документами.
- Авторы показывают недостаток автоматической оценки: она может штрафовать альтернативный, но релевантный источник.

**Banar et al. — [bLLeQA: Benchmarking LLMs for Grounded Legal Question-Answering in French and Dutch](https://aclanthology.org/2026.knowfm-1.4/)** — KnowFM 2026, DOI [10.18653/v1/2026.knowfm-1.4](https://doi.org/10.18653/v1/2026.knowfm-1.4).

- Билингвальный benchmark по бельгийскому праву с вопросами, ответами и поддерживающими статьями.
- Раздельно проверяются retrieval, извлечение цитат, отказ и generation.
- Даже лучший end-to-end вариант дал около 20% дефектных ответов; способность отказаться при неполных источниках оставалась слабой.

### 2. Структура нормы, chunking и перекрёстные ссылки

**Chae et al. — [Evaluating Structure-Aware Retrieval and Safety in Statute-Centric Legal QA](https://aclanthology.org/2026.acl-long.2112/)** — ACL 2026; arXiv-версия: [2604.06173](https://arxiv.org/abs/2604.06173).

- SearchFireSafety проверяет statutory QA, где доказательства распределены по иерархически связанным документам.
- Совместно оцениваются citation-aware retrieval и безопасный отказ при неполном контексте.
- Graph-guided retrieval улучшает результат, но доменно адаптированные модели могут увереннее галлюцинировать, если ключевой фрагмент отсутствует.

**Prior, Milanova & Schultz — [Chunking German Legal Code](https://arxiv.org/abs/2605.19806)** — принято в ASAIL/ICAIL 2026.

- Сравнены sections, subsections, sentences, propositions, fixed windows, contextual chunking, semantic clustering, Lumber и RAPTOR.
- На German Civil Code лучшие recall и вычислительную эффективность дали простые chunks, совпадающие с юридической структурой — прежде всего section/subsection.
- Более сложные LLM-интенсивные методы, разрушающие естественную структуру, выступили хуже.

**Jalocha & Michelsen — [CRAwLeR: Cross-Reference Aware Legal Retrieval](https://arxiv.org/abs/2606.21676)** — препринт, 19 июня 2026.

- Два набора данных по датскому и польскому праву специально проверяют retrieval, требующий перехода по перекрёстной ссылке.
- В ручной проверке около 80% выборки действительно требовали контекста.
- Лучший Recall@10 — 55% и 59%; задача далека от решения.

**Tleubayeva et al. — [Document Segmentation in Legal Retrieval-Augmented Generation: An Empirical Study on Kazakh Legal Texts](https://doi.org/10.1109/SIST61674.2026.11596467)** — IEEE SIST 2026.

- Structure-aware semantic chunking сохраняет юридическую иерархию и затем ограничивает длину внутри структурных границ.
- Улучшена стабильность раннего ранжирования (nDCG@10 и MRR); cross-encoder reranking не дал стабильного выигрыша и увеличил задержку.

### 3. Редакция нормы и время

**Cymbler, Guez & Fabre — [Temporal Misgrounding in Legal RAG: A Versioned-Corpus Benchmark for French Tax Law](https://arxiv.org/abs/2608.09393)** — препринт, 10 августа 2026.

- FiscalQA Pro: 32 436 версий статей французского налогового кодекса за 1938–2031 годы; 209 оцениваемых экспертных вопросов.
- На специально трудной temporal-выборке parametric QA дала 3,0% strict accuracy, статический RAG только по текущей редакции — 2,7%, а end-to-end поиск по versioned index — 98,3%.
- Это диагностический stress test, а не общая оценка legal RAG: почти во всех вопросах текущая редакция намеренно не содержала правильный исторический ответ.
- Сильный инженерный вывод: настоящая, но не применимая по дате цитата всё равно является юридической ошибкой.

**Prior, Schultz & Grabmair — [Asking For An Old Friend: Diagnosing and Mitigating Temporal Failure Modes in LLM-based Statutory Question Answering](https://arxiv.org/abs/2605.23497)** — препринт, 22 мая 2026.

- 312 экспертно проверенных вопросов по немецкому праву: post-cutoff amendments, pre-amendment и multi-provision historical questions.
- RAG с извлечением даты факта и фильтрацией редакций существенно улучшил результат; обычный web search давал нестабильный выигрыш и recency bias.
- Временная применимость трактуется как hard constraint.

### 4. Проверка цитат, grounding и hallucination

**Figueiredo et al. — [Grounded in Law: A Multi-Stage Anti-Hallucination Pipeline for Legal RAG Systems in Brazilian Portuguese](https://aclanthology.org/2026.propor-2.9/)** — PROPOR 2026.

- Production pipeline: hybrid retrieval, citation-constrained generation и отдельный Reference Audit с нормализацией и проверкой по официальным базам.
- Телеметрия: 184 895 ответов и 43 175 извлечённых правовых ссылок.
- Разрешались 81,7% ссылок на законодательство, но лишь 47,1% ссылок на судебную практику; fidelity audit исправил 6,5% проверенных ответов до выдачи пользователю.
- Это короткая industry paper, но масштаб production-телеметрии делает её полезной для проектирования контроля ссылок.

**Das, Abualhaija & Bianculli — [How Much Do Legal RAG Systems Still Hallucinate?](https://arxiv.org/abs/2608.14210)** — препринт, 14 августа 2026.

- Восемь комбинаций retriever + generator, два корпуса: GDPR на английском и гражданское право на французском.
- На answer level лучший вариант галлюцинировал примерно в 8–20% ответов в зависимости от корпуса; худшие — почти в половине.
- Большинство ошибок локальны и затрагивают одно утверждение, но встречаются и тяжёлые multi-claim hallucinations.
- False-premise questions особенно опасны; вывод подтверждён на отдельном наборе из 142 вопросов юристов.

**Elganayni & Saleh — [Re-Ranking Through an Attribution Lens for Citation Quality in Legal QA](https://arxiv.org/abs/2606.03728)** — ASAIL 2026.

- На AQuAECHR semantic similarity плохо соответствовала тому, какие passages модель фактически использует для цитирования; в candidate pool similarity ranking мог быть хуже случайного выбора по gold citation paragraphs.
- Cross-encoder, обученный на attribution scores, повысил citation faithfulness.
- Практический вывод: reranker для ответа и reranker для проверяемой цитаты могут оптимизировать разные цели.

**Huang et al. — [Mitigating Legal Hallucinations via Symbolic Constraints and Analogical Precedents](https://aclanthology.org/2026.acl-long.633/)** — ACL 2026, DOI [10.18653/v1/2026.acl-long.633](https://doi.org/10.18653/v1/2026.acl-long.633).

- AALawyer разделяет два пространства: закрытый набор статей и открытый набор судебных прецедентов.
- Для норм используется symbolic constrained retrieval, для прецедентов — dense analogical retrieval.
- Это полезная архитектурная идея: тип источника должен определять способ retrieval, а не только общий vector score.

**Chen, Yin & Zhou — [LegalCiteBench: Evaluating Citation Reliability in Legal Language Models](https://arxiv.org/abs/2605.10186)** — препринт, 11 мая 2026.

- Около 24 тыс. примеров из 1 000 судебных решений США; retrieval, completion, error detection, case matching и verification/correction.
- Closed-book citation recovery остаётся почти нерешённой: лучшие модели набрали менее 7/100 по retrieval/completion, а prompt об uncertainty не исправил цитаты.
- Это не RAG benchmark в узком смысле, но сильное обоснование обязательного внешнего retrieval и проверки реквизитов.

### 5. GraphRAG, многоуровневые источники и multilingual retrieval

**Chen et al. — [LegalGraphRAG: Multi-Agent Graph Retrieval-Augmented Generation for Reliable Legal Reasoning](https://aclanthology.org/2026.acl-long.1738/)** — ACL 2026, DOI [10.18653/v1/2026.acl-long.1738](https://doi.org/10.18653/v1/2026.acl-long.1738).

- Hierarchical legal graph разделяет факты, нормы и более абстрактные принципы.
- Researcher ищет доказательства, Auditor сверяет их с первоисточниками, Adjudicator формирует результат.
- Важно переносить не «мультиагентность» саму по себе, а разделение retrieval, evidence validation и synthesis.

**Baba Ahmadi et al. — [LEMUR: A Corpus for Robust Fine-Tuning of Multilingual Law Embedding Models for Retrieval](https://arxiv.org/abs/2602.09570)** — EACL SRW 2026.

- 24 953 официальных документа EUR-Lex на 25 языках.
- Авторы отдельно измеряют потери PDF-to-text относительно официального HTML.
- Domain fine-tuning embeddings улучшил Top-k retrieval, особенно для low-resource languages; наблюдался transfer на невиденные языки.

**van Drie et al. — [QuALA-NL: Question & Answer with Legal Attribution in Dutch](https://aclanthology.org/2026.lrec-1.49/)** — LREC 2026, DOI [10.63317/5i9bqybga69e](https://doi.org/10.63317/5i9bqybga69e).

- 101 QA-пара по трём нидерландским законам с атрибуцией к тексту нормы и её формализации.
- Knowledge-based RAG дал лучший retrieval, но text-based RAG — лучший generation result.
- Graph/формализация не гарантируют лучшего ответа без качественной передачи evidence в генератор.

**Ali, Oprea & Bâra — [Engineering Trustworthy Retrieval-Augmented Generation for EU Electricity Market Regulation](https://doi.org/10.3390/electronics15040749)** — *Electronics*, 2026.

- Девять актов ЕС; три стратегии chunking × две embedding-модели; pre-retrieval selection нормативных актов.
- Faithfulness достигала 0,96, но answer relevance заметно зависела от embedding и chunking; в их setting sliding window + bge-small-en-v1.5 был сильнейшим по rank-sensitive retrieval.
- Важно не универсализировать этот результат: корпус мал и доменно узок, а automated evaluation опирается на LLM-as-judge/RAGAS.

## Дополнительные релевантные работы

- Li et al. — [Legal-DC: Benchmarking Retrieval-Augmented Generation for Legal Documents](https://arxiv.org/abs/2603.11772): 480 китайских правовых документов, 2 475 QA с clause-level references, adaptive clause-boundary indexing.
- Ren et al. — [Automated data synthesis and retrieval-augmented generation for legal large language models](https://doi.org/10.1016/j.knosys.2026.116267), *Knowledge-Based Systems*: синтетические legal QA pairs, LLM-as-a-judge и Elo-ranking для подготовки данных retrieval/generation.
- Stammbach et al. — [Legal Retrieval for Public Defenders](https://arxiv.org/abs/2601.14348), forthcoming TMLR: реальный workflow public defenders, query taxonomy и human-annotated retrieval benchmark.
- Su et al. — [CoAL-RAG: A Complexity-Aware Legal Retrieval-Augmented Generation Method](https://arxiv.org/abs/2608.17536), accepted ICSS 2026: adaptive routing между retrieval-стратегиями по сложности вопроса.
- Franzone et al. — [Building Legal Reward Models for Grounding and Abstention](https://arxiv.org/abs/2609.14739), ICML AI4Law Workshop 2026: LegalRewardBench и reward models для noisy/insufficient retrieval; length-balanced training дал до +25,6 п.п. относительно baseline.
- Li et al. — [Fine-grained Claim-level RAG Benchmark for Law](https://arxiv.org/abs/2605.21071): claim-level оценка вместо одной оценки на весь ответ.
- Silva — [When Semantic Similarity Fails: Analyzing Metric Divergence in Legal RAG Evaluation](https://doi.org/10.1007/978-3-032-21324-2_43), ECIR 2026: расхождение semantic и legal-correctness metrics.
- Giang et al. — [Optimizing Retrieval Strategies for Vietnamese Legal RAG Systems](https://doi.org/10.1007/978-3-032-14674-8_9): hybrid sparse+dense retrieval и legal-document chunking для вьетнамского права.
- Bati et al. — [Mitigating Context Loss in Legal RAG: A Metadata-Aware Chunking Strategy for Hierarchical Indian Statutes](https://doi.org/10.1109/ICKECS70176.2026.11528014): metadata-rich child chunks с расширением до parent section.
- Farias et al. — [Retrieval-Augmented Generation and Knowledge Graphs in Portuguese-Language Legal Documents](https://aclanthology.org/2026.propor-1.1/), PROPOR 2026: GraphRAG по 203 нормативным резолюциям, структурные nodes/edges и evidence paths.

## Тематический синтез

### Retrieval важнее «ещё одной LLM», но не решает всё

Legal RAG Bench, LaborBench/STARA и CanLegalRAGBench показывают, что ошибка часто возникает до генерации. Но ClaimRAG-LAW-анализ 2026 года показывает обратную границу: даже при retrieval остаются локальные неподтверждённые утверждения. Следовательно, нельзя выбирать между retrieval evaluation и answer audit — нужны оба слоя.

### Юридическая структура — это данные, а не декоративный metadata field

German Legal Code, SearchFireSafety, CRAwLeR, Kazakh segmentation и индийская metadata-aware работа сходятся в одном: статья/часть/пункт, parent-child relationship и cross-reference влияют на retrieval. Универсального победителя между structural chunks и overlapping windows нет: результаты зависят от того, распределена ли норма по связанным положениям. Архитектурно безопаснее хранить каноническую структуру и строить несколько search projections, чем уничтожать структуру одним способом chunking.

### Temporal validity — отдельная ось корректности

Две независимые работы на французском и немецком праве показывают, что current-law retrieval может уверенно давать настоящую, но неприменимую редакцию. Версия, интервал действия и дата фактов должны участвовать в фильтрации до ranking; ссылка без редакции недостаточна.

### Citation verification нельзя свести к наличию URL

Production-данные из Бразилии, LegalCiteBench и attribution-aware re-ranking различают по меньшей мере четыре задачи: ссылка существует; её реквизиты нормализованы; источник действительно поддерживает утверждение; источник применим к юрисдикции и времени. Исправление одной задачи не гарантирует остальных.

### Abstention и false-premise tests становятся обязательными

SearchFireSafety, bLLeQA, LegalRewardBench и hallucination analysis показывают слабость моделей при неполном контексте и ложной предпосылке. Нужны явные no-answer cases, incomplete-context cases и отдельная метрика correct refusal.

## Что это означает для вашей архитектуры legal RAG

Ниже — переносимые выводы применительно к ранее обсуждавшейся модели `LegalProvision` / `LegalEdition` / `SearchChunk`. Живое состояние репозитория в этом обзоре не проверялось.

1. **Сохранить канонический слой права.** `LegalProvision` и `LegalEdition` должны оставаться источником истины; `SearchChunk` — только поисковая проекция.
2. **Индексировать редакции раздельно.** У каждого search record нужны `valid_from`, `valid_to`, идентификатор редакции, статус и источник официальной публикации. Фильтр по применимой дате должен выполняться до lexical и vector retrieval.
3. **Делать structure-aware projections.** Минимум: норма целиком; мелкий clause-level chunk с унаследованным заголовком/реквизитами; expanded context с parent и обязательными cross-references.
4. **Разделить нормы и практику.** Для закрытого множества норм полезны lexical/symbolic constraints и точное сопоставление реквизитов; для открытого множества дел/прецедентов — dense/hybrid retrieval и отдельная нормализация citations.
5. **Не путать retrieval score и legal support.** После генерации нужен claim-level audit: каждое правовое утверждение → конкретная норма/редакция → проверка entailment/fidelity → ссылка.
6. **Оценивать каскад по слоям.** Рекомендуемый набор метрик: provision recall@k; edition accuracy; cross-reference coverage; citation exact match; claim support; answer correctness; correct refusal; latency/cost.
7. **Добавить adversarial gold cases.** Историческая редакция, исключение, отрицание, разнесённая по нескольким нормам обязанность, ложная предпосылка, отсутствующая норма и альтернативный допустимый источник.
8. **Graph/agents добавлять после baseline.** Сначала измеримый hybrid retrieval и citation verifier; графовые переходы и второй агентный поиск — только там, где benchmark показывает провал на иерархии или cross-references.

## Ограничения обзора

- 2026 год ещё не завершён; новые ACL/JURIX/ICAIL и journal records могут появиться или сменить статус.
- Значительная часть свежих работ — препринты или workshop papers; цитируемость пока почти ничего не говорит о качестве.
- Большинство исследований относится к Китаю, ЕС, Германии, Канаде, США, Бразилии и другим юрисдикциям. Перенос на российское право требует отдельного русскоязычного gold set.
- Метрики и корпуса несопоставимы напрямую; нельзя объявить один retriever/chunking/GraphRAG универсально лучшим.
- Многие работы используют LLM-as-a-judge; для ключевых юридических полей предпочтительны deterministic checks и экспертный аудит.

## Методика поиска

### Источники

1. Firecrawl Research Index: четыре семантических запроса по legal RAG, statutory/case-law retrieval, citation, temporal validity, hallucination и benchmarks; по 40 результатов; 86 уникальных записей после дедупликации внутри выдачи.
2. arXiv API: прямой запрос по `retrieval augmented generation` и `legal/law/statute/regulatory`, дата 2026-01-01—2026-09-19; 129 записей до screening.
3. OpenAlex: поиск и title/abstract screening публикаций 2026 года; title search дал 138 records, включая дубликаты arXiv/DataCite, datasets и непрофильные материалы.
4. Crossref: проверка DOI, типа публикации, даты и venue для journal/conference papers.
5. ACL Anthology и страницы издателей: финальная проверка venue, DOI, авторов, abstracts и publication status.

### Критерии включения

- Первая публикация в 2026 году, а не только обновление старого препринта.
- Юридический или тесно связанный regulatory corpus/task.
- Эмпирическая оценка retrieval, end-to-end RAG, grounding/citation, temporal validity, hallucination или abstention.
- Доступная первичная страница статьи и проверяемые bibliographic metadata.

### Исключения

- Общие RAG papers без юридической оценки.
- Блоги, product pages и проекты без связанной статьи.
- Записи 2025 года, лишь обновлённые в 2026 году.
- Низкоточные keyword matches без legal corpus или legal task.

### Оценка качества

- **Выше доверие:** peer-reviewed/accepted paper, первичная страница venue, реалистичный или экспертно проверенный benchmark, отдельные retrieval/generation/citation metrics, открытые данные/код.
- **Среднее доверие:** эмпирический препринт с прозрачным dataset и воспроизводимыми метриками.
- **Осторожно:** узкий или намеренно adversarial benchmark, малый sample, human-verification-pending data, proprietary system без полного воспроизведения, только LLM-as-a-judge.

## Использованный исследовательский workflow

Обзор выполнен с процедурой literature-review из Scientific Agent Skills:

Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065). arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065
