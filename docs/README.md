# Документация Legal RAG

## Основные документы

- [PRD v0.2](PRODUCT_REQUIREMENTS.md) — итоги M0, границы обработки и допуска, проверяемые редакции пяти актов на 01.10.2026 и 01.01.2025 в M1 и критерии первого инкремента M0-M2.
- [M0 implementation plan](M0_IMPLEMENTATION_PLAN.md) — tracer-bullet задачи, зависимости и gate первого этапа.
- [M1 implementation plan](M1_IMPLEMENTATION_PLAN.md) — 15 проверяемых шагов: extraction/OCR, реконструкция, human review и допуск пяти актов на две даты; реализация ещё не начата.
- [M0-07 pilot and review policy](M0_07_PILOT_AND_REVIEW_POLICY.md) — утверждённый пятый акт, ограничения источников и полномочия юридической проверки.
- [M0-10 legal review](M0_10_LEGAL_REVIEW.md) — решения по пяти пилотным кандидатам, затраты времени и оставшиеся блокеры допуска.
- [M0-11 gold set](M0_11_GOLD_SET.md) — 30 проверенных Legal Reviewer вопросов v2, фиксированный split 15/15 и одобренное локальное хранение.
- [M0 gate report](M0_GATE_REPORT.md) — 70 критериев пунктов и 8 условий milestone; итог `pass`, М1 разрешён, плейсхолдеры времени М0-10 приняты владельцем проекта.
- [Frozen M0 contracts](M0_CONTRACTS.md) — версии acquisition/handoff, воспроизведение и [хеши кода и fixtures](M0_CONTRACT_FREEZE.json).
- [Анализ покрытия СанПиН 2.1.3684-21](SANPIN_2_1_3684_21_SOURCE_COVERAGE.md) — различия старого и нового банков, роль CNTD и цепочка официальных поправок.
- [Сводный план и архитектура](LEGAL_RAG_MASTER_PLAN_2026.md) — главный проектный документ и этапы M0-M7.
- [Политика официальных источников](LEGAL_SOURCES_POLICY.md) — правила допуска материалов в продуктовый корпус.
- [Целевой пайплайн](PIPELINE.md) — краткая схема движения данных и границ доверия.
- [Словарь](GLOSSARY.md) — термины канонической модели, поиска и проверки ответа.
- [Атлас проекта](PROJECT_ATLAS.md) — текущая граница, статус компонентов и маршрут M0-M2.

## Исследования и прежние планы

- [Анализ ARLC 2026](ARLC_2026_LEGAL_RAG_ANALYSIS.md)
- [Обзор литературы Legal RAG 2026](legal_rag_2026_literature_review_ru.md)
- [Исследовательские выводы](RESEARCH.md)
- [Реестр источников](SOURCES.md)
- [Разбор Index-RAG](review-index-rag.md)
- [Предыдущий архитектурный план](LEGAL_AGENT_ARCHITECTURE_AND_PLAN.md)

Диаграммы, их генераторы и промпты находятся в [`assets/`](assets/).

