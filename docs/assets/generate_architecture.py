"""Generate the labeled Legal RAG architecture atlas as a standalone HTML file."""

from html import escape
from pathlib import Path


OUT = Path(__file__).with_name("legal-rag-architecture.html")
PAPER = "#f5f5f5"
INK = "#2d3142"
MUTED = "#4f5d75"
SOFT = "#7a8399"
ACCENT = "#eb6c36"
LINK = "#2e5aa8"


def svg_start(slug: str, title: str, desc: str) -> list[str]:
    return [
        f'<svg class="diagram" viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">',
        f'<title id="{slug}-title">{escape(title)}</title>',
        f'<desc id="{slug}-desc">{escape(desc)}</desc>',
        "<defs>",
        f'<marker id="{slug}-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="{MUTED}"/></marker>',
        f'<marker id="{slug}-arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="{ACCENT}"/></marker>',
        f'<marker id="{slug}-arrow-link" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0,8 3,0 6" fill="{LINK}"/></marker>',
        "</defs>",
        f'<rect width="1280" height="720" fill="{PAPER}"/>',
    ]


def zone(x: int, y: int, w: int, h: int, label: str) -> str:
    mask_w = max(96, len(label) * 6 + 20)
    return (
        f'<rect class="zone" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>'
        f'<rect x="{x+20}" y="{y-4}" width="{mask_w}" height="16" fill="{PAPER}"/>'
        f'<text class="zone-label" x="{x+28}" y="{y+8}">{escape(label)}</text>'
    )


def edge_h(slug: str, x1: int, x2: int, y: int, label: str = "") -> str:
    line = f'<line class="edge" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" marker-end="url(#{slug}-arrow)"/>'
    if not label:
        return line
    mid = (x1 + x2) // 2
    width = min(x2 - x1 - 8, max(28, len(label) * 5 + 8))
    return (
        line
        + f'<rect x="{mid-width//2}" y="{y-20}" width="{width}" height="12" rx="2" fill="{PAPER}"/>'
        + f'<text class="edge-label" x="{mid}" y="{y-11}" text-anchor="middle">{escape(label)}</text>'
    )


def edge_path(slug: str, d: str, optional: bool = False) -> str:
    cls = "edge optional-edge" if optional else "edge"
    return f'<path class="{cls}" d="{d}" marker-end="url(#{slug}-arrow)"/>'


def node(
    x: int,
    y: int,
    w: int,
    h: int,
    tag: str,
    title: str | list[str],
    sub: list[str],
    kind: str = "",
) -> str:
    titles = [title] if isinstance(title, str) else title
    cls = f"box {kind}".strip()
    tag_cls = "tag" if kind == "focal" else "tag muted"
    parts = [
        f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>',
        f'<text class="{tag_cls}" x="{x+12}" y="{y+20}">{escape(tag)}</text>',
    ]
    title_y = y + 46
    for i, line in enumerate(titles):
        parts.append(f'<text class="node-title" x="{x+12}" y="{title_y+i*16}">{escape(line)}</text>')
    sub_y = y + (68 if len(titles) == 1 else 82)
    for i, line in enumerate(sub):
        parts.append(f'<text class="node-sub" x="{x+12}" y="{sub_y+i*15}">{escape(line)}</text>')
    return "".join(parts)


def note(x: int, y: int, message: str) -> str:
    return f'<text class="small-note" x="{x}" y="{y}">{escape(message)}</text>'


def legend(items: list[str]) -> str:
    chunks = ['<line class="legend-rule" x1="48" y1="650" x2="1232" y2="650"/>']
    cursor = 52
    for item in items:
        chunks.append(f'<text class="legend-text" x="{cursor}" y="675">{escape(item)}</text>')
        cursor += max(116, len(item) * 6 + 32)
    return "".join(chunks)


def today() -> str:
    slug = "legal-rag-today"
    a = svg_start(
        slug,
        "Текущее состояние LAW_Data и JKH",
        "LAW_Data строит отдельный полнотекстовый индекс нормативных актов. JKH отдельно ищет по материалам дела для чата и по собственному нормативному индексу для черновиков жалоб.",
    )
    a += [
        zone(48, 72, 1184, 232, "LAW_Data · НПА"),
        zone(48, 332, 1184, 296, "JKH · ДЕЛО"),
        note(80, 112, "Отдельный корпус и CLI-поиск"),
        note(80, 372, "Два независимых пути внутри локального приложения"),
    ]
    for y, labels in [
        (196, ["ИЗВЛЕЧЬ", "ИНДЕКС"]),
        (440, ["BM25", "КОНТЕКСТ"]),
        (556, ["ПОИСК", "НОРМЫ"]),
    ]:
        a += [edge_h(slug, 336, 464, y, labels[0]), edge_h(slug, 736, 864, y, labels[1])]
    a += [
        node(80, 156, 256, 80, "ИСТОЧНИК", "Файлы НПА", ["current · historical"], "input"),
        node(464, 156, 272, 80, "СБОРКА", "Извлечение и нарезка", ["build_index.py · 3500/350"]),
        node(864, 156, 320, 80, "ХРАНИЛИЩЕ", "SQLite FTS5 + CLI-поиск", ["43 файла · 5 220 фрагментов*"], "store"),
        node(80, 400, 256, 80, "ФАКТЫ ДЕЛА", "Загруженные файлы", ["письма · акты · фото"], "input"),
        node(464, 400, 272, 80, "ПОИСК", "Haystack BM25", ["по материалам дела"]),
        node(864, 400, 320, 80, "ПРОДУКТ", "Чат JKH", ["ответ по загруженным файлам"], "focal"),
        node(80, 516, 256, 80, "ОТДЕЛЬНЫЙ ИНДЕКС", "Нормативный SQLite FTS5", ["12 файлов · 2 003 фрагмента*"], "store"),
        node(464, 516, 272, 80, "СЕРВИС", "Legal search provider", ["поиск правового контекста"]),
        node(864, 516, 320, 80, "ПРОДУКТ", "Черновики жалоб", ["ComplaintPipeline · validation"]),
        legend(["СЕЙЧАС", "Сплошная стрелка — работающий путь", "* Числа по сверке от 21.09.2026"]),
        "</svg>",
    ]
    return "".join(a)


def corpus() -> str:
    slug = "legal-rag-corpus"
    a = svg_start(
        slug,
        "Целевая сборка нормативного корпуса",
        "Подлинник и manifest проходят извлечение, структурный разбор и сохранение акта, редакции и положения. От нормы создаются поисковые фрагменты и индексы.",
    )
    a.append(zone(40, 164, 1200, 312, "КАНОНИЧЕСКИЙ КОНТУР → ПОИСК"))
    for x1, x2, label in [(204, 252, "ВХОД"), (404, 452, "ТЕКСТ"), (604, 652, "AST"), (804, 852, "ЧАНК"), (1004, 1052, "FTS")]:
        a.append(edge_h(slug, x1, x2, 320, label))
    a += [
        node(52, 264, 152, 112, "01 · ИСТОЧНИК", "Подлинник НПА", ["Manifest: URL · хеш", "даты · статус"], "input"),
        node(252, 264, 152, 112, "02 · ИЗВЛЕЧЬ", "Текст и страницы", ["таблицы · координаты", "очистка · QA"]),
        node(452, 264, 152, 112, "03 · РАЗОБРАТЬ", "Legal AST", ["статья → пункт", "LegalStructureParser"]),
        node(652, 264, 152, 112, "04 · ОСНОВАНИЕ", ["Act · Edition", "· Provision"], ["адрес + период"], "focal"),
        node(852, 264, 152, 112, "05 · ПРОЕКЦИЯ", "SearchChunk", ["привязан к норме", "и редакции"]),
        node(1052, 264, 152, 112, "06 · ПОИСК", "FTS + векторы", ["с метаданными", "применимости"], "store"),
        note(72, 420, "Ручная проверка: неизвестная структура, неполное извлечение, реквизиты и дата действия."),
        legend(["ПЛАН", "Акцент — каноническое правовое основание", "SearchChunk — средство поиска, не ссылка в ответе"]),
        "</svg>",
    ]
    return "".join(a)


def retrieval() -> str:
    slug = "legal-rag-retrieval"
    a = svg_start(
        slug,
        "Поиск применимой нормы",
        "Вопрос и дата проходят предварительный фильтр редакции, статуса и доступа, затем лексический и возможный векторный поиск, объединение кандидатов, раскрытие полной нормы и создание citation handle.",
    )
    a.append(zone(40, 136, 1200, 400, "ПРИМЕНИМОСТЬ ДО РАНЖИРОВАНИЯ"))
    a += [
        edge_h(slug, 204, 252, 336, "ДАТА"),
        edge_path(slug, "M404 308 H420 Q428 308 428 300 V252 Q428 244 436 244 H452"),
        edge_path(slug, "M404 364 H432 Q440 364 440 372 V420 Q440 428 448 428 H452", True),
        edge_path(slug, "M604 244 H620 Q628 244 628 252 V300 Q628 308 636 308 H652"),
        edge_path(slug, "M604 428 H632 Q640 428 640 420 V372 Q640 364 648 364 H652", True),
        edge_h(slug, 804, 852, 336, "ТОП-K"),
        edge_h(slug, 1004, 1052, 336, "АДРЕС"),
        node(52, 280, 152, 112, "01 · ВХОД", "Вопрос + факты", ["дата события", "тип вопроса"], "input"),
        node(252, 280, 152, 112, "02 · ФИЛЬТР", "Применимость", ["редакция · статус", "scope · ACL"], "focal"),
        node(452, 188, 152, 112, "03А · БАЗОВЫЙ", "Лексический", ["слова · реквизиты", "FTS"]),
        node(452, 372, 152, 112, "03Б · ПОЗЖЕ", "Векторный", ["перефразировки", "после A/B-теста"], "optional"),
        node(652, 280, 152, 112, "04 · КАНДИДАТЫ", "RRF / reranker", ["объединить", "и упорядочить"]),
        node(852, 280, 152, 112, "05 · КОНТЕКСТ", "Полная норма", ["редакция + соседи", "и исключения"]),
        node(1052, 280, 152, 112, "06 · РЕЗУЛЬТАТ", "CitationHandle", ["акт · редакция", "пункт · источник"], "focal"),
        note(72, 506, "При известной статье и дате get_provision обращается к норме напрямую, без RRF и reranker."),
        legend(["ПЛАН", "Штриховая ветка — только после проверки на gold set", "Фильтр действует до поиска"]),
        "</svg>",
    ]
    return "".join(a)


def answer() -> str:
    slug = "legal-rag-answer"
    a = svg_start(
        slug,
        "Подготовка и проверка ответа в JKH",
        "Норма, материалы дела, состояние проекта и память диалога поступают к агенту с разными уровнями доверия. Ответ проходит сверку цитат и проверку поддержки каждого правового вывода до выдачи ответа, уточнения или отказа.",
    )
    a.append(zone(40, 64, 1200, 548, "ЧЕТЫРЕ РОЛИ ДАННЫХ"))
    a += [
        edge_path(slug, "M276 148 H304 Q312 148 312 156 V288 Q312 296 320 296 H360"),
        edge_path(slug, "M276 268 H292 Q300 268 300 276 V312 Q300 320 308 320 H360"),
        edge_path(slug, "M276 388 H316 Q324 388 324 380 V352 Q324 344 332 344 H360"),
        edge_path(slug, "M276 508 H328 Q336 508 336 500 V376 Q336 368 344 368 H360", True),
        edge_h(slug, 576, 648, 332, "CIT:id"),
        edge_h(slug, 864, 936, 332, "РЕШЕНИЕ"),
        node(56, 108, 220, 80, "ПРАВОВОЕ ОСНОВАНИЕ", "Норма + редакция", ["CitationHandle · источник"], "focal"),
        node(56, 228, 220, 80, "ФАКТЫ ДЕЛА", "Материалы дела", ["файлы и происхождение"], "input"),
        node(56, 348, 220, 80, "РАБОЧЕЕ СОСТОЯНИЕ", "Backend JKH", ["дело · статусы · доступ"], "store"),
        node(56, 468, 220, 80, "КОНТЕКСТ ДИАЛОГА", "Память агента", ["не источник права"], "input"),
        node(360, 264, 216, 136, "ФОРМУЛИРОВКА", "Агент", ["короткий ответ", "по отобранным данным"]),
        node(648, 264, 216, 136, "КОНТРОЛЬ", "Проверка ответа", ["ID · дата · текст цитаты", "+ поддержка вывода"], "focal"),
        node(936, 264, 264, 136, "ВЫДАЧА", "Ответ с источниками", ["или уточнение", "или корректный отказ"]),
        note(360, 454, "Та же проверка нужна для ответа и черновика жалобы."),
        note(360, 478, "Спорную поддержку смысла следует передавать на ручную проверку."),
        legend(["ПЛАН", "Право, факты и состояние — разные роли", "Штриховой вход — память лишь для контекста"]),
        "</svg>",
    ]
    return "".join(a)


def section(anchor: str, status: str, heading: str, lead: str, graphic: str, notes: list[str]) -> str:
    paragraphs = "".join(f"<p>{line}</p>" for line in notes)
    status_class = "status" if anchor == "today" else "status target"
    return (
        f'<section id="{anchor}"><p class="{status_class}">{status}</p>'
        f"<h2>{heading}</h2><p class=\"section-note\">{lead}</p>"
        f'<div class="figure-wrap">{graphic}</div><div class="explain">{paragraphs}</div></section>'
    )


CSS = f"""
:root{{--paper:{PAPER};--ink:{INK};--muted:{MUTED};--soft:{SOFT};--accent:{ACCENT};--link:{LINK};}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Geist,Arial,sans-serif}}
main{{max-width:1400px;margin:0 auto;padding:42px 32px 64px}}
.eyebrow{{color:var(--muted);font:500 11px 'Geist Mono',Consolas,monospace;letter-spacing:.15em;text-transform:uppercase}}
h1{{margin:8px 0 12px;font:400 clamp(34px,4vw,54px)/1.08 'Instrument Serif','Noto Serif',Georgia,serif}}
.intro{{max-width:900px;color:var(--muted);line-height:1.55;font-size:16px}}
nav{{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0 34px}}
nav a{{border:1px solid #bfc0c0;border-radius:6px;padding:8px 12px;color:var(--ink);text-decoration:none;font-size:13px;background:#fff}}
nav a:hover{{border-color:var(--accent)}}
section{{border-top:1px solid #bfc0c0;padding-top:28px;margin-top:36px}}
section h2{{margin:0 0 7px;font-size:24px;font-weight:600}}
.status{{color:var(--accent);font:500 11px 'Geist Mono',Consolas,monospace;letter-spacing:.08em;text-transform:uppercase}}
.status.target{{color:var(--link)}}.section-note{{margin:10px 0 16px;color:var(--muted);line-height:1.5;max-width:1000px}}
.figure-wrap{{overflow-x:auto}}svg.diagram{{display:block;width:100%;min-width:980px;height:auto}}
svg .zone{{fill:rgba(45,49,66,.02);stroke:rgba(45,49,66,.15);stroke-width:1}}
svg .box{{fill:#fff;stroke:var(--ink);stroke-width:1.2}}
svg .box.store{{fill:rgba(45,49,66,.05);stroke:var(--muted)}}
svg .box.input{{fill:rgba(79,93,117,.10);stroke:var(--soft)}}
svg .box.focal{{fill:rgba(235,108,54,.08);stroke:var(--accent);stroke-width:1.8}}
svg .box.optional{{fill:#fff;stroke:var(--soft);stroke-dasharray:5 4}}
svg .zone-label{{fill:var(--muted);font:500 10px 'Geist Mono',Consolas,monospace;letter-spacing:.1em}}
svg .node-title{{fill:var(--ink);font:600 12px Geist,Arial,sans-serif}}
svg .node-sub{{fill:var(--muted);font:400 9px 'Geist Mono',Consolas,monospace}}
svg .tag{{fill:var(--accent);font:500 8px 'Geist Mono',Consolas,monospace;letter-spacing:.04em}}
svg .tag.muted{{fill:var(--muted)}}
svg .edge{{fill:none;stroke:var(--muted);stroke-width:1.5}}
svg .edge.optional-edge{{stroke-dasharray:5 4;stroke-width:1}}
svg .edge-label{{fill:var(--muted);font:500 8px 'Geist Mono',Consolas,monospace}}
svg .small-note{{fill:var(--muted);font:400 12px Geist,Arial,sans-serif}}
svg .legend-rule{{stroke:rgba(45,49,66,.15);stroke-width:1}}
svg .legend-text{{fill:var(--muted);font:400 10px 'Geist Mono',Consolas,monospace}}
.explain{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 28px;max-width:1180px;margin:8px 0 0}}
.explain p{{margin:0;line-height:1.5;color:var(--muted);font-size:14px}}.explain strong{{color:var(--ink)}}
.callout{{margin-top:18px;max-width:1120px;border-left:3px solid var(--accent);padding:9px 14px;line-height:1.55;color:var(--ink);background:#fff}}
footer{{border-top:1px solid #bfc0c0;margin-top:48px;padding-top:18px;color:var(--muted);line-height:1.5;font-size:13px}}
footer a{{color:var(--link)}}
@media(max-width:700px){{main{{padding:24px 16px 40px}}.explain{{grid-template-columns:1fr}}}}
@media print{{main{{max-width:none;padding:12mm}}nav{{display:none}}section{{break-inside:avoid}}svg.diagram{{min-width:0}}}}
"""


def main() -> None:
    body = [
        '<p class="eyebrow">Архитектурный атлас · 22.09.2026</p>',
        "<h1>Legal RAG: от корпуса и дела к проверяемому ответу</h1>",
        '<p class="intro">Четыре схемы показывают отдельно то, что уже работает, и целевую цепочку: подготовку нормативного корпуса, поиск применимой редакции и подготовку ответа в JKH. Подписи у блоков объясняют роль каждого компонента; стрелки показывают передачу данных.</p>',
        '<nav aria-label="Разделы схемы"><a href="#today">1. Что есть сейчас</a><a href="#corpus">2. Сборка корпуса</a><a href="#retrieval">3. Поиск нормы</a><a href="#answer">4. Ответ и контроль</a><a href="../GLOSSARY.md">Словарь терминов</a></nav>',
        section(
            "today", "Подтверждено по коду и атласу", "1. Сейчас: два отдельных контура",
            "LAW_Data собирает и ищет нормативные тексты. JKH отдельно ведёт дела: чат использует файлы дела, а подготовка жалобы обращается к собственному правовому индексу. Общего Legal Retrieval API между ними пока нет. Dify и RAGFlow остаются экспериментальными платформами вне работающего пути.",
            today(),
            [
                "<strong>LAW_Data:</strong> текущая нарезка опирается на длину текста. В ней пока нет отдельных сущностей редакции и точной нормы.",
                "<strong>JKH:</strong> предупреждение по ссылке проверяет найденные правовые фрагменты, но не доказывает поддержку каждого утверждения точной нормой и редакцией.",
            ],
        ),
        section(
            "corpus", "Целевая архитектура · план", "2. Компиляция нормативного корпуса",
            "Цель — превратить исходный акт в адресуемые положения с редакцией и координатами первоисточника. Индекс получает поисковую проекцию, а не заменяет канонический текст.",
            corpus(),
            [
                "<strong>Редакция и дата:</strong> текст положения имеет смысл для ответа только вместе с периодом его действия и источником.",
                "<strong>Граница чанка:</strong> длинную норму можно делить внутри самой нормы; соседние статьи и редакции не смешиваются.",
            ],
        ),
        section(
            "retrieval", "Целевая архитектура · план", "3. Вопрос → применимая норма",
            "Сначала определяется дата и область вопроса. Фильтры применимости ставятся перед обеими ветками поиска. Из найденного фрагмента раскрывается целое положение, после чего сервис выдаёт проверяемый адрес источника.",
            retrieval(),
            [
                "<strong>Дата:</strong> старую редакцию можно искать для старого события. Для текущего события она не должна попадать в допустимые результаты.",
                "<strong>Точный путь:</strong> get_provision нужен для запросов по известной статье или пункту; общий поиск остаётся для вопросов без точного адреса.",
            ],
        ),
        section(
            "answer", "Целевая архитектура · план", "4. Ответ в JKH и проверка каждого вывода",
            "Норма и материалы дела входят в ответ с разными ролями. Агент формулирует текст, а контроль отдельно проверяет адрес цитаты и то, поддерживает ли источник смысл каждого юридического утверждения.",
            answer(),
            [
                "<strong>Правовое основание:</strong> только конкретное положение применимой редакции может подтвердить юридический вывод.",
                "<strong>Факты и память:</strong> файл дела сообщает факты; память поддерживает диалог и не служит источником права.",
            ],
        ),
        '<div class="callout"><strong>Главное правило:</strong> ссылка должна вести к конкретному положению нужной редакции, а процитированный текст должен поддерживать именно тот вывод, который написан в ответе. Если применимой нормы или существенной даты нет, система уточняет вопрос либо отказывается от правового вывода.</div>',
        '<footer>Основание: <a href="../README.md">README.md</a>, <a href="../PIPELINE.md">PIPELINE.md</a> и <a href="../SOURCES.md">SOURCES.md</a>; текущие контуры JKH дополнительно сверены по коду 22.09.2026. Числа фрагментов взяты из атласа от 21.09.2026. Полный <a href="../GLOSSARY.md">словарь терминов</a> дан отдельно. Схемы описывают систему и её план, а не актуальность конкретных норм права.</footer>',
    ]
    page = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Legal RAG — подробная схема проекта</title>'
        '<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500;600&family=Noto+Serif:ital@0;1&display=swap" rel="stylesheet">'
        f"<style>{CSS}</style></head><body><main>{''.join(body)}</main></body></html>"
    )
    OUT.write_text(page, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
