# М1-04А, этап 2: слой логического текста `logical-text/1` — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** перенести проходы 1–2 прототипа (колонтитулы и логические абзацы с потоком сносок) из `docs/assets/ocr_logical_structure.py` в производственный модуль, который строит поверх `text-extraction/1` отдельный производный слой `logical-text/1` и измеряется своими метриками этапа 2.

**Architecture:** новый модуль `src/legal_rag/corpus/logical_text.py` — чистая функция `extraction → logical-text`, без изменения входа. Исходный текст, токены и координаты не меняются: абзац хранит фрагменты-указатели на исходные области и смещения. Ввод-вывод — только в отдельной функции записи и команде CLI. Этап 3 (`ocr_structure.py`, `/7`), `compile` и прототип не меняются; подключение слоя к этапу 3 — следующий план.

**Tech Stack:** Python 3 стандартной библиотеки, pytest 8.4 из `.venv`, ruff 0.14.

**Spec:** [протокол оценки](../milestones/m1/04a/M1_04A_EVALUATION_PROTOCOL_2026-10-20.md) (метрики этапа 2, раздел 5) и описание проходов 1–2 в [отчёте о прототипе](../milestones/m1/04a/M1_04A_LOGICAL_PARAGRAPHS_2026-10-17.md).

## Global Constraints

- Вход не мутируется; повторный запуск на тех же байтах даёт побайтно тот же результат и тот же `logical_text_id`.
- Каждый `text_node_id` входа учтён ровно один раз: во фрагменте абзаца или в области-колонтитуле. Иначе `ValueError("token accounting …")` до любой записи.
- Никаких условий под номер, дату, название, имя файла или хеш конкретного акта.
- Поведение совпадает с прототипом, кроме двух объявленных отклонений D1 и D2 (Task 2). Любое другое расхождение на сохранённых входах — дефект.
- Тесты — только на авторских данных; корпус, OCR и сеть в CI не используются.
- Команды запускаются в PowerShell из корня репозитория: `$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m pytest …`.
- Работа идёт прямо в `main`; каждый Task заканчивается коммитом.

## Review Focus

1. **Разрыв в физических страницах** (OCR сделан для стр. 1–8 и 20): продолжение не склеивается через пропуск — тест в Task 2.
2. **Пустая OCR-область** (картинка без расшифровки, `empty_region`) между концом страницы и продолжением: не становится открытым абзацем, к ней ничего не приклеивается — тест в Task 2.
3. **Подпись «УТВЕРЖДЕНЫ…» в категории `Page-header`**: не считается колонтитулом, даже если повторяется — тест в Task 1.
4. **Испорченный вход**: блок ссылается на несуществующую область, лишний токен, неверный `extraction_id` — отказ без записи файлов — тесты в Task 2 и Task 3.
5. **Сноска, ошибочно помеченная как `Text`**, на следующей странице: присоединяется к незаконченной сноске, а не к телу — тест в Task 2.

---

### Task 1: Области и колонтитулы (проход 1)

**Files:**
- Create: `src/legal_rag/corpus/logical_text.py`
- Test: `tests/legal_rag/corpus/test_logical_text.py`

**Interfaces:**
- Produces:
  - `SCHEMA = "logical-text/1"`, `BUILDER = "ocr-logical-text/1"`.
  - `match_view(text: str) -> str` — убирает ведущие `#{1,6}\s+` в каждой строке и схлопывает пробелы; только для сопоставления.
  - `is_caption(text: str) -> str | None` — `"approval"` для `^(УТВЕРЖДЕН[АЫО]?|Утвержден[аыо]?)\b(?:\s|$)` (с учётом регистра), `"annex"` для `^(?:ПРИЛОЖЕНИЕ|Приложение)(?:\s*№\s*(\d+))?(?:\s+(к\s.+))?$` при длине ≤ 120; иначе `None`. Регулярные выражения — как в прототипе.
  - `classify_regions(extraction: dict) -> list[dict]` — записи в порядке страниц и областей: `{"region_id", "page", "index", "category", "bbox", "text", "match_text", "text_node_ids", "role", "role_reason"}`. `text` — склейка `original_text` блоков области в исходном порядке. `role` ∈ `content | noise | picture | table`; `role_reason` ∈ `None | "page_number" | "repeated_running_text" | "empty_running_region"`.

- [ ] **Step 1: Написать падающие тесты.** В тестовом файле — помощник `extraction(pages)` по образцу `tests/legal_rag/corpus/test_ocr_logical_structure.py::extraction`, дополненный `schema_version="text-extraction/1"`, `coverage.requested_pages` и `extraction_id = content_hash(...)` из `legal_rag.corpus.compiler`. Тесты:
  - `test_page_number_and_repeated_running_text_are_noise`: `Page-header "2"` → `noise/page_number`; `Page-footer "2059534.doc"` на трёх страницах → `noise/repeated_running_text`; пустой `Page-footer` → `noise/empty_running_region`.
  - `test_caption_in_running_region_stays_content`: `Page-header "УТВЕРЖДЕНЫ\nпостановлением…"` на трёх страницах подряд → `role == "content"`.
  - `test_running_text_on_two_pages_stays_content`: одинаковый `Page-footer` на двух страницах → `content`.
  - `test_picture_and_table_roles`: `Picture` → `picture`, `Table` → `table`.
  - `test_match_view_strips_markdown_prefix_only`: `match_view("## I. Общие\n  положения") == "I. Общие положения"`, а `region["text"]` сохраняет `"## I. Общие\n  положения"`.
- [ ] **Step 2: Запустить и убедиться, что падают.** `$env:PYTHONPATH = "src"; .venv\Scripts\python.exe -m pytest tests/legal_rag/corpus/test_logical_text.py -q` → ImportError / FAIL.
- [ ] **Step 3: Реализовать** `match_view`, `is_caption`, `classify_regions`. Повтор считается по `re.sub(r"\d+", "#", match_text)` среди непустых `Page-header`/`Page-footer`; порог — не меньше 3 областей, как в прототипе. Номер страницы — `[-–\s]*\d+[-–\s]*`.
- [ ] **Step 4: Запустить тесты** той же командой → PASS.
- [ ] **Step 5: Commit.** `git add src/legal_rag/corpus/logical_text.py tests/legal_rag/corpus/test_logical_text.py; git commit -m "feat(corpus): classify OCR running regions for logical text"`

### Task 2: Логические абзацы, поток сносок и контракт (проход 2)

**Files:**
- Modify: `src/legal_rag/corpus/logical_text.py`
- Test: `tests/legal_rag/corpus/test_logical_text.py`

**Interfaces:**
- Consumes: `classify_regions`, `match_view`, `is_caption` (Task 1).
- Produces: `build_logical_text(extraction: dict) -> dict`:
  ```text
  {"schema_version": SCHEMA, "builder_version": BUILDER,
   "extraction_id", "source_asset_sha256",
   "regions": [{"region_id", "page", "index", "category", "role", "role_reason", "paragraph_id"}],
   "paragraphs": [{"paragraph_id", "flow": "body"|"footnote",
                   "kind": "text"|"footnote"|"table"|"picture"|"empty",
                   "fragments": [{"region_id", "page", "bbox", "text_node_ids", "start", "end", "join"}],
                   "text", "match_text", "features"}],
   "accounting": {"text_nodes", "in_paragraphs", "in_noise"},
   "logical_text_id"}
  ```
  - `paragraph_id` — порядковый номер абзаца (0…), абзацы идут в порядке первого фрагмента; у колонтитула `paragraph_id = None`.
  - `text` — тексты фрагментов через один `"\n"`; `text[f.start:f.end]` равно тексту области фрагмента.
  - `join` первого фрагмента — `None`, остальных — `"body_continuation_after_page_break"`, `"unnumbered_footnote_after_page_break"` или `"footnote_continuation_after_page_break"` (имена из прототипа).
  - `features`: `starts_lowercase` (первый символ строчный или `(`), `terminated` (как `terminated()` прототипа), `footnote_number` (ведущие надстрочные цифры → int или `None`), `footnote_refs` (int всех остальных групп надстрочных цифр в `match_text`, по порядку), `caption` (`is_caption` первого фрагмента).
  - `logical_text_id = content_hash(` результат без `logical_text_id` `)`.

Правила склейки — как `logical_paragraphs()` прототипа, с двумя объявленными отклонениями:
- **D1:** продолжение (тела или сноски) присоединяется, только если страница области равна странице последнего фрагмента + 1 (прототип допускает любую более позднюю страницу).
- **D2:** область без текста — отдельный абзац `kind="empty"`. Она не становится открытым абзацем тела или сноски и не принимает продолжений.

- [ ] **Step 1: Написать падающие тесты:**
  - `test_body_continuation_joins_across_page_break_and_noise`: стр. 1 кончается `"2. Документы передаются в составе, предусмотренном Правилами содержания,"`; стр. 2: `Page-header "2"`, затем `"утвержденных постановлением … № 491."` → один абзац из двух фрагментов, `join == "body_continuation_after_page_break"`, `features["caption"] is None`, а `"УТВЕРЖДЕН"` нигде не открывает отдельный абзац.
  - `test_terminated_or_marked_region_is_not_joined`: предыдущий абзац кончается `;` → новый абзац; продолжение со строчной буквы, но с маркером `"а) …"` → новый абзац.
  - `test_same_page_lowercase_region_is_not_joined`: строчная область не первая на странице → отдельный абзац.
  - `test_no_join_across_missing_physical_page` (D1): страницы 8 и 20, незаконченный абзац на 8 и строчное начало на 20 → два абзаца.
  - `test_empty_region_never_receives_continuation` (D2): стр. 1 — незаконченный абзац, затем пустой `Text`; стр. 2 начинается со строчной → продолжение приклеено к незаконченному абзацу, пустая область — свой абзац `kind="empty"`.
  - `test_footnote_flow_and_mislabelled_continuation`: данные из `test_footnote_owner_by_marker_and_cross_page_footnote_continuation` прототипа → `"(зарегистрирован Минюстом России 24.04.2017)."` — второй фрагмент сноски 2 с `join == "footnote_continuation_after_page_break"`; `footnote_number` равен 1, 2 и 3 у соответствующих абзацев; у `"1. Площадки обустраиваются¹."` `footnote_refs == [1]`.
  - `test_fragment_offsets_reproduce_source_text`: для каждого фрагмента `p["text"][f["start"]:f["end"]]` равно `original_text` его области.
  - `test_accounting_determinism_and_no_mutation`: вход после вызова равен глубокой копии; два вызова дают равные результаты и одинаковый `logical_text_id`; сумма `in_paragraphs + in_noise == text_nodes`.
  - `test_rejects_broken_accounting_and_unknown_region`: лишний `text_node` → `ValueError` с `"token accounting"`; блок с неизвестным `source_region_id` → `ValueError`.
- [ ] **Step 2: Запустить** → FAIL.
- [ ] **Step 3: Реализовать** `build_logical_text`. Проверку `schema_version` и `extraction_id` здесь не делать — она в Task 4.
- [ ] **Step 4: Запустить** тесты модуля и прототипа: `…pytest tests/legal_rag/corpus/test_logical_text.py tests/legal_rag/corpus/test_ocr_logical_structure.py -q` → PASS.
- [ ] **Step 5: Commit.** `feat(corpus): build logical-text/1 paragraphs and footnote flow`

### Task 3: Команда CLI и неизменяемая запись

**Files:**
- Modify: `src/legal_rag/corpus/logical_text.py`, `src/legal_rag/corpus/__main__.py`
- Test: `tests/legal_rag/corpus/test_logical_text.py`

**Interfaces:**
- Consumes: `build_logical_text` (Task 2); `content_hash`, `json_bytes`, `_write_once` из `compiler.py`.
- Produces:
  - `write_logical_text(extraction_path: Path, output_dir: Path) -> dict`. Читает JSON и проверяет `schema_version == "text-extraction/1"` и `extraction_id == content_hash(extraction без extraction_id)` — иначе `ValueError("extraction hash mismatch")` до любой записи. Пишет `output_dir/logical-text/<logical_text_id>.json` через `json_bytes` и `_write_once`. Возвращает `{"result": "new"|"unchanged", "logical_text_id", "path"}`; `unchanged`, если файл уже есть с теми же байтами.
  - CLI: `python -m legal_rag.corpus logical-text --extraction PATH --output-dir DIR`; ошибки — тем же JSON в stderr с кодом 2, что и у остальных команд.

- [ ] **Step 1: Написать падающие тесты** (`tmp_path`):
  - `test_cli_writes_once_then_reports_unchanged`: первый запуск `main([...])` → код 0, `result == "new"`; второй → `"unchanged"`, байты файла не изменились.
  - `test_cli_rejects_tampered_extraction_before_writing`: в записанной extraction изменена одна буква текста без пересчёта `extraction_id` → код 2, каталог `logical-text` не создан.
  - `test_cli_rejects_other_schema`: `schema_version="text-extraction/0"` → код 2.
- [ ] **Step 2: Запустить** → FAIL.
- [ ] **Step 3: Реализовать** `write_logical_text` и подкоманду в `__main__.py`, импортируя модуль лениво, как `extract`.
- [ ] **Step 4: Запустить** весь набор: `…pytest -q` → PASS (все прежние тесты тоже). Затем `.venv\Scripts\python.exe -m ruff check src tests` → без замечаний.
- [ ] **Step 5: Commit.** `feat(corpus): add logical-text CLI with verified extraction input`

### Task 4: Паритет с прототипом и метрики этапа 2 на сохранённых документах

**Files:**
- Create: `docs/assets/evaluate_logical_text.py`
- Create: `docs/milestones/m1/04a/M1_04A_LOGICAL_TEXT_2026-10-20.md`
- Modify: `docs/README.md`, `docs/AGENTS.md`, `src/legal_rag/corpus/AGENTS.md`, `tests/AGENTS.md`
- Test: `tests/legal_rag/corpus/test_logical_text.py`

**Interfaces:**
- Consumes: `build_logical_text`; из прототипа — `load_regions`, `logical_paragraphs`; из `evaluate_ocr_owner_gold.py` — `load_gold`. Загрузка скриптов — как в `test_ocr_logical_structure.py::load_script`.
- Produces: `evaluate_logical_text.py --inputs DIR --gold DIR --output DIR`:
  - **паритет**: для каждого `*.extraction.json` сравнить группировку областей (списки `region_id` по абзацам) и роли с прототипом; каждое расхождение получает метку `D1` (склейка через пропуск физических страниц), `D2` (затронута область без текста) или `unexpected`;
  - **метрики**: `continuation {tp, fp, fn}` — область считается продолжением, если она не первый фрагмент абзаца; эталон — флаг `+` в `load_gold`. `false_exclusion` — область есть в эталоне, но `role == "noise"`. `missed_exclusion` — `Page-header`/`Page-footer` вне эталона с `role == "content"` и `caption is None`;
  - пишет `summary.json` в новый каталог `--output` (существующий каталог — отказ). Код выхода 1, если есть хоть одно расхождение `unexpected`.

- [ ] **Step 1: Написать падающий тест** `test_evaluator_parity_labels_and_metrics`: на авторских входах с одним случаем D1 и одной склейкой эталон `"1.1 A"`, `"2.0 A +"` дают `continuation == {"tp": 1, "fp": 0, "fn": 0}`, расхождение получает метку `"D1"`, а код выхода равен 0.
- [ ] **Step 2: Запустить** → FAIL. **Step 3: Реализовать** скрипт. **Step 4:** тест → PASS.
- [ ] **Step 5: Прогнать на сохранённых данных:**
  `.venv\Scripts\python.exe docs/assets/evaluate_logical_text.py --inputs data/m1/experiments/m1-04a-20261017-logical-v1/inputs --gold data/m1/experiments/m1-04a-20261017-logical-v1/gold --output data/m1/experiments/m1-04a-20261020-logical-text-v1`
  Ожидается: код 0, ни одного `unexpected`. Склейки — 29 / 0 / 2 по 8 документам (как у прототипа); если D1 или D2 меняют эти числа, записать фактические значения и причину. `false_exclusion == 0`.
- [ ] **Step 6: Два прогона CLI** на `resolution-416.extraction.json` в два разных каталога: одинаковый `logical_text_id`; третий прогон в первый каталог → `unchanged`.
- [ ] **Step 7: Отчёт на русском** `M1_04A_LOGICAL_TEXT_2026-10-20.md`: что сделано, контракт, отклонения D1/D2 с фактическим числом случаев, метрики этапа 2, паритет, ограничения (этап 3 не подключён; таблицы через страницу и нормализация похожих букв в маркерах не сделаны; эталон одного разметчика). Добавить строку в `docs/README.md`. Дописать устойчивые факты в `src/legal_rag/corpus/AGENTS.md`, `tests/AGENTS.md` (что проверяет `test_logical_text.py`) и `docs/AGENTS.md`.
- [ ] **Step 8: Финальная проверка:** полный `pytest -q`, `ruff check src tests docs/assets`, `git diff --check`, `.venv\Scripts\python.exe docs/assets/generate_m0_gate.py` → 78/78.
- [ ] **Step 9: Commit.** `docs(corpus): record logical-text parity and stage-2 metrics`

## Вне этого плана

- Подключение `logical-text/1` к этапу 3 (`ocr_structure.py`) и к `compile` — следующий план, после решений владельца по разделу 9 протокола.
- Склейка таблиц, разорванных между страницами, — сначала нужен эталон для таблиц.
- Нормализация похожих букв в маркерах («Х»/«X», «І»/«I») и дат — относится к разбору маркеров этапа 3.
