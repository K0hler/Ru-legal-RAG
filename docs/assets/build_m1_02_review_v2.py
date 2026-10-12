"""One offline review decision; factual checks and missing evidence stay with engineering."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "data/m1/reviews/m1-02-review-v1"
OUT = ROOT / "data/m1/reviews/m1-02-review-v2"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class Paragraphs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.current = [dict(attrs).get("id", ""), []]

    def handle_data(self, text):
        if self.current is not None:
            self.current[1].append(text)

    def handle_endtag(self, tag):
        if tag == "p" and self.current is not None:
            self.rows.append((self.current[0], "".join(self.current[1]).strip()))
            self.current = None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads((OLD / "packet.json").read_text("utf-8"))
    # Existing bookmarks in the cached v1 page still resolve while the preview runs.
    for directory in ("documents", "raw", "pages"):
        shutil.copytree(OLD / directory, OUT / directory, dirs_exist_ok=True)
    by_id = {doc["id"]: dict(doc) for doc in old["documents"]}
    source_views = {}
    for id, doc in by_id.items():
        raw = (OLD / doc["raw_file"]).read_bytes()
        view = (OLD / doc["file"]).read_bytes()
        assert sha(raw) == doc["sha256"], f"Changed original: {id}"
        assert sha(view) == doc["view_sha256"], f"Changed v1 view: {id}"
        if doc["file"].endswith(".html"):
            match = re.search(r"<article>(.*?)</article>", view.decode("utf-8"), re.S)
            assert match, id
            number = 0

            def anchor(match):
                nonlocal number
                number += 1
                return (
                    match[0]
                    if re.search(r"\bid=", match[0])
                    else match[0][:-1] + f' id="paragraph-{number}">'
                )

            body = re.sub(r"<p\b[^>]*>", anchor, match[1])
            source_views[id] = {"kind": "html", "body": body}
        else:
            # Render every page so the in-app browser does not need a PDF plugin/server.
            directory = OUT / "raster" / id
            directory.mkdir(parents=True, exist_ok=True)
            info = subprocess.check_output(
                ["pdfinfo", str(OLD / doc["file"])], text=True
            )
            page_count = int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])
            if len(list(directory.glob("page-*.jpg"))) != page_count:
                subprocess.run(
                    [
                        "pdftoppm",
                        "-jpeg",
                        "-jpegopt",
                        "quality=82",
                        "-scale-to",
                        "1200",
                        str(OLD / doc["file"]),
                        str(directory / "page"),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            pages = [
                "data:image/jpeg;base64,"
                + base64.b64encode(p.read_bytes()).decode("ascii")
                for p in sorted(directory.glob("page-*.jpg"))
            ]
            assert len(pages) == page_count, id
            source_views[id] = {
                "kind": "pdf",
                "pages": pages,
                "original": "data:application/pdf;base64,"
                + base64.b64encode(raw).decode("ascii"),
            }
            print(f"Rendered {id}: {len(pages)} pages", flush=True)

    def paragraphs(id):
        p = Paragraphs()
        p.feed(source_views[id]["body"])
        return p.rows

    def excerpt(id, predicate):
        matches = [(anchor, text) for anchor, text in paragraphs(id) if predicate(text)]
        assert len(matches) == 1, (id, len(matches))
        anchor, text = matches[0]
        return {
            "document": id,
            "anchor": anchor,
            "text": text,
            "source_sha256": by_id[id]["sha256"],
        }

    article1 = excerpt(
        "federal-law-59-current", lambda t: t.startswith("4.") and "Установленный" in t
    )
    article2 = excerpt(
        "federal-law-59-current",
        lambda t: t.startswith("1.") and "Граждане имеют право" in t,
    )
    historical = dict(paragraphs("federal-law-59-historical"))
    assert article1["text"] == historical[article1["anchor"]]
    assert article2["text"] == historical[article2["anchor"]]
    court1 = excerpt("ks19p", lambda t: t.startswith("1. Признать"))
    court2 = excerpt("ks19p", lambda t: t.startswith("2. Признать"))
    special = excerpt(
        "law48-current",
        lambda t: t.startswith("2.") and "При рассмотрении обращений" in t,
    )
    research = json.loads((OLD / "research.json").read_text("utf-8"))
    assert len(research["historical"]) == 4
    assert all(r["raw_sha256"] == r["second_sha256"] for r in research["historical"])
    proposal = "Для обеих целевых дат учитывать расширение круга заявителей и адресатов уже по части 4 статьи 1 и части 1 статьи 2 закона 59-ФЗ в редакции 80-ФЗ. Сохранить отдельную связь с КС №19-П: региональные гарантии могут дополнять федеральные, но не создавать новые обязанности или ограничения прав физических и юридических лиц. Отметку о КС учитывать как адресное толкование и связь с источником; сама по себе она не доказывает неправильность всего текста 59-ФЗ."
    facts = [
        {
            "title": "Целостность файлов",
            "finding": "Проверены все 30 хешей оригиналов и 30 хешей представлений для чтения.",
            "evidence": [],
        },
        {
            "title": "Четыре исторических кандидата",
            "finding": "Это отдельные ответы по идентификаторам из официальных списков редакций. Хеши первого и повторного ответа совпадают во всех четырёх случаях. Применимость каждой нормы ещё не объявлена подтверждённой.",
            "evidence": [
                "housing-code-history",
                "government-decree-354-history",
                "government-decree-491-history",
                "federal-law-59-history",
            ],
        },
        {
            "title": "59-ФЗ: поправки 80-ФЗ отражены в обеих версиях",
            "finding": "Тексты ч.4 ст.1 и ч.1 ст.2 совпадают посимвольно в сохранённых историческом и контрольном ответах; оба содержат ссылку на 80-ФЗ. Повторно накладывать эту текстовую поправку не требуется.",
            "evidence": [
                "federal-law-59-historical",
                "federal-law-59-current",
                "0001201305080015",
            ],
        },
        {
            "title": "48-ФЗ: прямо указан специальный порядок",
            "finding": "Часть 2 статьи 9 отсылает к 59-ФЗ с особенностями рассмотрения жалоб региональным уполномоченным. Это отдельное условие применения. В M0-10 эта классификация уже принята; повторного разрешения сейчас не запрашиваю.",
            "evidence": ["law48-current"],
        },
        {
            "title": "Прямо указанные даты и изменения",
            "finding": "№11: начало 31.12.2024 (п.4, стр.3); 547-ФЗ: 30.03.2025 (ст.2, стр.4); №1242: день опубликования (п.3, стр.1). №931 содержит территориальный перечень и условия применения, а не новую общую текстовую редакцию №354. Это документальная сверка инженера, без юридического допуска целых редакций.",
            "evidence": [
                "0001202412270033",
                "0001202412280052",
                "0001202609260011",
                "0001202607270025",
            ],
        },
    ]
    facts[3]["checked_excerpt"] = special
    open_items = [
        "Доказать полноту цепочек поправок и применимость четырёх исторических кандидатов. Более поздний текст не подставляется на 01.01.2025.",
        "Собрать полную цепочку №491 после 01.09.2025 и основание общей редакции №354; проверить условия специальных режимов №931 к контрольной дате.",
        "Проверить полноту девяти найденных поправок СанПиН, точные операции и специальные условия начала действия. Расчёты дат по общему правилу №763 остаются проектом инженера до проверки специальных норм.",
        "Подготовить полные диагностические/реконструированные тексты. Окончательный допуск всех пяти актов на обе даты останется отдельной проверкой по готовым результатам.",
    ]
    definition = {
        "schema": "m1-02-focused-human-packet/2",
        "embedded_content_sha256": sha(
            json.dumps(
                source_views, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        ),
        "prepared_on": "2026-10-12",
        "base_packet_hash": old["packet_hash"],
        "inventory_content_hash": old["inventory_content_hash"],
        "targets": old["targets"],
        "reviewer": "legal-reviewer-owner",
        "scope": "One human decision on the remaining 19-P effect after 80-FZ; factual verification and unfinished evidence collection stay with engineering. No edition admission.",
        "decision": {
            "id": "59-ks19p-after-80",
            "title": "Как учитывать оставшийся эффект КС №19-П после 80-ФЗ?",
            "proposal": proposal,
            "excerpts": [article1, article2, court1, court2],
            "evidence": [
                "ks19p",
                "0001201305080015",
                "federal-law-59-current",
                "federal-law-59-historical",
            ],
        },
        "facts": facts,
        "engineering_open_items": open_items,
        "documents": list(by_id.values()),
    }
    definition["packet_hash"] = sha(
        json.dumps(
            definition, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )
    (OUT / "packet.json").write_text(
        json.dumps(definition, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )

    def button(id, label=None, anchor="", page=1):
        doc = by_id[id]
        return f'<button type="button" class="source" data-document="{id}" data-anchor="{anchor}" data-page="{page}">{html.escape(label or doc["short_title"])}</button>'

    snippets = ""
    for label, part in [
        ("КС: пределы региональных гарантий, резолютивный пункт 1", court1),
        ("59-ФЗ: часть 4 статьи 1 (совпадает в обеих версиях)", article1),
        ("59-ФЗ: часть 1 статьи 2 (совпадает в обеих версиях)", article2),
    ]:
        snippets += f'<details class="excerpt"><summary>{html.escape(label)}</summary><blockquote>{html.escape(part["text"])}</blockquote>{button(part["document"], "Открыть весь документ на этом фрагменте", part["anchor"])}</details>'
    facts_html = "".join(
        '<article class="fact"><h3>'
        + html.escape(f["title"])
        + "</h3><p>"
        + html.escape(f["finding"])
        + '</p><div class="links">'
        + "".join(button(id) for id in f["evidence"])
        + "</div></article>"
        for f in facts
    )
    library = "".join("<li>" + button(id) + "</li>" for id in by_id)
    style = """
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:#f3f5f8;color:#233047;font:16px/1.6 'Segoe UI',Arial,sans-serif}main{max-width:1000px;margin:auto;padding:28px 24px 70px}h1{font-size:32px;line-height:1.2}h2{font-size:23px}h3{font-size:17px}p{margin:12px 0}button,textarea,select{font:inherit}button{cursor:pointer;border:1px solid #c1ccde;padding:9px 13px;border-radius:8px;background:#eef3fb;color:#264d94}button:hover{background:#e0eafa}button:focus-visible,select:focus-visible,textarea:focus-visible,a:focus-visible{outline:3px solid #b97700;outline-offset:3px}a{color:#264d94}.card{padding:25px;margin:20px 0;background:white;border:1px solid #dce3ee;border-radius:12px}.hero{border-top:5px solid #315ba5}.badge{font-size:13px;color:#49627e;letter-spacing:.4px}.proposal{padding:16px 20px;background:#eef4fd;border-left:4px solid #315ba5}.muted{color:#57677e}.links{display:flex;flex-wrap:wrap;gap:9px;margin:14px 0}summary{cursor:pointer;color:#264d94;font-weight:600;padding:10px 0}.excerpt{border-top:1px solid #dce3ee}.excerpt blockquote{margin:6px 0 12px;padding:12px 16px;background:#f6f8fc;border-left:3px solid #a4b9d8}label{display:block;font-weight:600;margin:16px 0 7px}select,textarea{width:100%;padding:11px;border:1px solid #aab9d0;border-radius:7px;background:white}textarea{min-height:75px;resize:vertical}.primary{background:#2f559d;color:white}.primary:hover{background:#244580}.fact{border-top:1px solid #e1e7f0;padding:12px 0}#report{min-height:170px}.source-list{list-style:none;padding:0}.source-list li{margin:8px 0}.viewer{width:min(1100px,96vw);max-height:94vh;border:1px solid #aab9d0;border-radius:12px;padding:0}.viewer::backdrop{background:#17243bb0}.viewer header{position:sticky;top:0;background:white;border-bottom:1px solid #dce3ee;padding:16px 22px;z-index:1}.viewer header h2{font-size:18px;margin:6px 0}.viewer-content{padding:20px 25px;overflow-wrap:anywhere}.viewer article .H{font-weight:700;font-size:20px}.viewer article .C{text-align:center}.viewer article .markx{color:#754528}.viewer table{border-collapse:collapse;max-width:100%;font-size:14px}.viewer td,.viewer th{border:1px solid #cad3e1;padding:8px;vertical-align:top}.viewer pre{white-space:pre-wrap}.page-image{display:block;width:100%;max-width:900px;margin:auto;height:auto}.pdf-controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.hash{font:12px/1.5 Consolas,monospace;overflow-wrap:anywhere}.highlight{background:#fff1a7}.message{color:#385987}.banner{padding:12px 16px;border-left:4px solid #8ba1c5;background:#f7f9fc}@media(max-width:650px){main{padding:16px 12px 40px}.card{padding:18px}h1{font-size:26px}.viewer-content{padding:14px}.viewer header{padding:12px}.viewer table{display:block;overflow:auto}}@media print{button,.viewer{display:none}.card{break-inside:avoid}body{background:white}main{padding:0}}
"""
    script = r"""
const data=DATA, views=VIEWS, documents=new Map(data.documents.map(d=>[d.id,d]));
const dialog=document.querySelector('#viewer'), pane=document.querySelector('#viewer-content');let current=null,page=1,returnFocus=null;
function showPage(){const v=views[current];pane.innerHTML='<img class="page-image" alt="Страница '+page+' официального PDF" src="'+v.pages[page-1]+'">';document.querySelector('#page-count').textContent=page+' / '+v.pages.length;document.querySelector('#previous').disabled=page===1;document.querySelector('#next').disabled=page===v.pages.length;dialog.scrollTop=0}
function openDocument(id,anchor='',selectedPage=1){const doc=documents.get(id),v=views[id];if(!doc||!v){document.querySelector('#status').textContent='Документ отсутствует в пакете: '+id;return}returnFocus=document.activeElement;current=id;page=Math.max(1,Math.min(selectedPage,v.pages?.length||1));document.querySelector('#source-title').textContent=doc.short_title;document.querySelector('#source-hash').textContent='SHA-256 оригинала: '+doc.sha256;document.querySelector('#source-origin').href=doc.url;document.querySelector('#pdf-controls').hidden=v.kind!=='pdf';document.querySelector('#document-search').hidden=v.kind!=='html';if(v.kind==='html')pane.innerHTML='<article>'+v.body+'</article>';else showPage();dialog.showModal();if(anchor){const part=pane.querySelector('#'+CSS.escape(anchor));if(part){part.classList.add('highlight');part.scrollIntoView({block:'center'})}}document.querySelector('#close-viewer').focus()}
document.querySelectorAll('[data-document]').forEach(b=>b.addEventListener('click',()=>openDocument(b.dataset.document,b.dataset.anchor,Number(b.dataset.page||1))));
document.querySelector('#close-viewer').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{pane.innerHTML='';returnFocus?.focus()});document.querySelector('#previous').onclick=()=>{page--;showPage()};document.querySelector('#next').onclick=()=>{page++;showPage()};
document.querySelector('#find').onsubmit=e=>{e.preventDefault();const q=document.querySelector('#search').value.trim().toLowerCase();pane.querySelectorAll('.highlight').forEach(e=>e.classList.remove('highlight'));if(!q)return;const match=[...pane.querySelectorAll('p,td,th,li')].find(e=>e.textContent.toLowerCase().includes(q));document.querySelector('#find-result').textContent=match?'Фрагмент найден':'Не найдено';if(match){match.classList.add('highlight');match.scrollIntoView({block:'center'})}};
document.querySelector('#download-pdf').onclick=()=>{const a=document.createElement('a');a.href=views[current].original;a.download=current+'.pdf';a.click()};
const key='legal-rag-focused-'+data.packet_hash;function answer(){return {decision:document.querySelector('#decision').value,comment:document.querySelector('#comment').value}}
function save(){try{localStorage.setItem(key,JSON.stringify(answer()));document.querySelector('#status').textContent='Черновик сохранён в этом браузере.'}catch(e){document.querySelector('#status').textContent='Автосохранение недоступно. Сформируйте и скопируйте отчёт перед закрытием.'}}
try{const a=JSON.parse(localStorage.getItem(key)||'null');if(a){document.querySelector('#decision').value=a.decision||'';document.querySelector('#comment').value=a.comment||''}}catch(e){}
for(const el of document.querySelectorAll('#decision,#comment'))el.addEventListener('input',save);
document.querySelector('#make-report').onclick=()=>{const a=answer();if(!a.decision){document.querySelector('#status').textContent='Выберите решение по одному вопросу.';return}if(a.decision!=='confirmed'&&!a.comment.trim()){document.querySelector('#status').textContent='Укажите поправку или недостающее доказательство.';return}const confirmed=a.decision==='confirmed';const report={schema:'m1-02-focused-human-review/2',packet_hash:data.packet_hash,base_packet_hash:data.base_packet_hash,inventory_content_hash:data.inventory_content_hash,reviewer:data.reviewer,role:'Legal Reviewer',recorded_at:new Date().toISOString(),time_basis:'Actual time the reviewer clicked Make report; no review duration inferred',targets:data.targets,scope:data.scope,question:data.decision.id,decision:a.decision,rationale:a.comment.trim()||(confirmed?'Подтверждаю предложенную юридическую квалификацию: '+data.decision.proposal:''),edition_admission:false,engineering_open_items:data.engineering_open_items};const labels={confirmed:'Подтверждаю',correction:'Нужна поправка',insufficient:'Недостаточно доказательств'};document.querySelector('#report').value='М1-02 · юридическое решение\nПроверяющий: '+data.reviewer+' (Legal Reviewer)\nВремя записи: '+report.recorded_at+'\nПакет: '+data.packet_hash+'\nВопрос: '+data.decision.title+'\nРешение: '+labels[a.decision]+'\nОснование: '+report.rationale+'\nЦели: 01.01.2025 и 01.10.2026\nОкончательный допуск редакций: не выдан. Полнота и применимость остаются отдельными открытыми задачами инженера.\n\nJSON для точной записи:\n'+JSON.stringify(report,null,2);document.querySelector('#status').textContent='Отчёт готов. Скопируйте поле ниже и отправьте его в этот чат.';document.querySelector('#report').focus();document.querySelector('#report').select();save()};
""".replace(
        "DATA", json.dumps(definition, ensure_ascii=False).replace("<", "\\u003c")
    ).replace(
        "VIEWS", json.dumps(source_views, ensure_ascii=False).replace("<", "\\u003c")
    )
    page = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>М1-02 · одна юридическая проверка</title><link rel="icon" href="data:,"><style>'
        + style
        + '</style></head><body><main><section class="card hero"><div class="badge">LEGAL RAG · М1-02 · ПАКЕТ v2 ОТ 12.10.2026</div><h1>Одна юридическая проверка.<br>Остальную сверку делаю я.</h1><p>Все 30 документов встроены в этот файл. Кнопки открывают тексты и страницы PDF здесь же: сервер, интернет и новые вкладки не нужны. Прежние ответы и пакет v1 сохранены отдельно.</p><p class="banner">Ваша роль уже назначена: <b>Legal Reviewer / legal-reviewer-owner</b>. Подтвердите только предложенную ниже юридическую квалификацию или укажите поправку. Для согласия писать обоснование заново не нужно: в отчёт попадёт точный подтверждённый вывод.</p><p><a href="#question">К единственному вопросу</a> · <a href="#facts">Что проверил я</a> · <a href="#my-work">Мои открытые задачи</a> · <a href="#library">Библиотека</a></p></section><section class="card" id="question"><div class="badge">ЕДИНСТВЕННЫЙ ОБЯЗАТЕЛЬНЫЙ ОТВЕТ</div><h2>'
        + html.escape(definition["decision"]["title"])
        + '</h2><p><b>Предложенный вывод</b></p><div class="proposal">'
        + html.escape(proposal)
        + '</div><p><b>Почему вопрос остаётся вам</b></p><p>Наличие поправок и совпадение текста я проверяю сам. Здесь нужно принять юридическую квалификацию оставшегося эффекта решения КС. По принятому в проекте порядку статус человеческого юридического решения присваиваете вы. Это требование нашего процесса проверки, а не отдельное законодательное разрешение на чтение закона.</p><p class="muted">Вам достаточно прочитать вывод и три коротких фрагмента ниже. Полные источники доступны по кнопкам; искать документы или сравнивать редакции заново не требуется.</p>'
        + snippets
        + '<div class="links">'
        + button("0001201305080015", "80-ФЗ: статья 2, оригинал PDF, стр.2", page=2)
        + button("ks19p", "КС: резолютивный пункт 2", court2["anchor"])
        + '</div><label for="decision">Ваше решение по этому выводу</label><select id="decision"><option value="">Выберите после чтения</option><option value="confirmed">Согласен с предложенной юридической квалификацией</option><option value="correction">Нужна поправка</option><option value="insufficient">Недостаточно доказательств</option></select><label for="comment">Поправка или замечание — только если требуется</label><textarea id="comment" placeholder="При согласии можно оставить пустым. При поправке укажите, какой вывод изменить; при нехватке — какое доказательство нужно."></textarea><div class="links"><button id="make-report" class="primary">Сформировать ответ для чата</button></div><p id="status" class="message" aria-live="polite"></p><label for="report">Готовый ответ: скопируйте и отправьте мне</label><textarea id="report" readonly></textarea><p class="muted">Вы подтверждаете этот конкретный вывод. Все десять редакций ещё не получают окончательного допуска; открытые вопросы сохраняются.</p></section><section class="card" id="facts"><h2>Что я проверил — повторного подтверждения не требуется</h2>'
        + facts_html
        + '</section><section class="card" id="my-work"><h2>Что ещё должен сделать я</h2><p>Эти пробелы не превращены в вопросы к вам и не считаются закрытыми.</p><ul>'
        + "".join("<li>" + html.escape(item) + "</li>" for item in open_items)
        + '</ul><p>После подготовки полных результатов я предъявлю конкретные оставшиеся сомнения. От вас сейчас не требуется заверять полноту непроверенных цепочек.</p></section><section class="card" id="library"><details><summary>Все 30 встроенных документов — справочно</summary><p>Тексты открываются в окне чтения, PDF — как изображения всех страниц с навигацией. Ссылки на официальные сайты внутри окна требуют интернет; приложенные материалы работают без него.</p><ul class="source-list">'
        + library
        + '</ul></details><p class="hash">Хеш этого пакета: '
        + definition["packet_hash"]
        + '</p></section></main><dialog class="viewer" id="viewer"><header><button id="close-viewer">Закрыть документ</button><h2 id="source-title"></h2><details><summary>Официальное происхождение</summary><p id="source-hash" class="hash"></p><a id="source-origin" href="https://pravo.gov.ru/">Открыть на официальном сайте — нужен интернет</a></details><div id="pdf-controls" class="pdf-controls" hidden><button id="previous">Предыдущая страница</button><span id="page-count"></span><button id="next">Следующая страница</button><button id="download-pdf">Сохранить оригинальный PDF</button></div><div id="document-search" hidden><form id="find"><label for="search">Поиск по тексту</label><input id="search"><button>Найти</button><span id="find-result"></span></form></div></header><div id="viewer-content" class="viewer-content"></div></dialog><script>'
        + script
        + "</script></body></html>"
    )
    (OUT / "index.html").write_text(page, "utf-8")
    (OUT / "ui.js").write_text(script, "utf-8")
    (OUT / "README.txt").write_text(
        "Откройте index.html в браузере. Это один самостоятельный файл со всеми документами: сервер и интернет не нужны.\nОбязателен один ответ. Прочитайте вывод и короткие фрагменты, выберите решение и нажмите «Сформировать ответ для чата». При согласии замечание необязательно.\nНе требуется повторно подтверждать технические проверки, искать поправки или заверять ещё не доказанную полноту. Открытые задачи инженера показаны отдельно.\nПакет v1 и его ответы не перезаписывались. Итоговый допуск всех пяти актов на две даты ещё не выдан.\n",
        "utf-8",
    )
    assert len(by_id) == 30
    assert all(
        p["anchor"] in source_views[p["document"]]["body"]
        for p in [article1, article2, court1, court2]
    )
    assert 'target="_blank"' not in page and ' src="documents/' not in page
    print(
        json.dumps(
            {
                "html": str(OUT / "index.html"),
                "html_bytes": len(page.encode("utf-8")),
                "documents": len(by_id),
                "required_decisions": 1,
                "packet_hash": definition["packet_hash"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
