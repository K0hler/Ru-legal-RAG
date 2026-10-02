"""Build the bounded, local M1-02 human source-review packet from retained evidence."""

from __future__ import annotations

import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile, ZIP_DEFLATED

PROJECT = Path(__file__).resolve().parents[2]
PACKET = PROJECT / "data/m1/reviews/m1-02-review-v1"
ARCHIVE = PROJECT / "data/m1-02-sources"


def read(path: Path):
    return json.loads(path.read_text("utf-8-sig"))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class ReadingHTML(HTMLParser):
    """Keep legal text/tables and native anchors, removing active source-page content."""

    tags = set(
        "p div span pre b strong i em u sup sub table tbody thead tr td th br h1 h2 h3 h4 ol ul li blockquote".split()
    )

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}:
            self.skip += 1
        if self.skip or tag not in self.tags:
            return
        allowed = [
            (k, v) for k, v in attrs if k in {"id", "class", "colspan", "rowspan"} and v
        ]
        self.parts.append(
            "<"
            + tag
            + "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in allowed)
            + ">"
        )

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"}:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in self.tags and tag != "br":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(html.escape(data))


STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f4f5f8;color:#202735;font:16px/1.6 'Segoe UI',Arial,sans-serif}a{color:#244da5}a:hover{color:#122c67}button,input,select,textarea{font:inherit}button,.button{padding:10px 16px;border:1px solid #cad2e2;border-radius:9px;background:white;color:#233f75;cursor:pointer;text-decoration:none}button.primary{background:#284d9b;color:white;border-color:#284d9b}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #f0ae3b;outline-offset:3px}.layout{display:grid;grid-template-columns:240px minmax(0,1fr);max-width:1440px;margin:auto}nav{position:sticky;top:0;height:100vh;padding:28px 18px;background:#e9edf5;overflow:auto}nav a{display:block;padding:9px 12px;margin:3px 0;border-radius:8px;text-decoration:none}nav a:hover{background:#dce4f4}nav small,.muted{color:#5a6375}.main{min-width:0;padding:28px 40px 80px;max-width:1120px}h1{font-size:34px;line-height:1.2;letter-spacing:-.7px}h2{margin-top:44px}h3{font-size:21px;line-height:1.35;margin:0 0 16px}.eyebrow{color:#31589e;font-weight:700;letter-spacing:1px;font-size:12px}.hero,.card{background:white;border:1px solid #dde2eb;border-radius:14px;padding:26px;margin:18px 0}.hero{border-top:5px solid #31589e}.note{border-left:4px solid #c28b22;background:#fff8e8;padding:13px 17px;margin:14px 0}.proposal{border-left:4px solid #5e7baa;background:#eff4fb;padding:14px 18px}.label{font-weight:700;font-size:13px;color:#536077;margin:18px 0 6px}.links{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0}.links a{padding:7px 11px;background:#edf2fa;border-radius:7px;text-decoration:none}.answer{border-top:1px solid #dde2eb;padding-top:15px;margin-top:22px}label{display:block;font-weight:600;margin:10px 0 5px}select,input[type=text],input[type=number],textarea{width:100%;padding:10px 12px;border:1px solid #aebacf;border-radius:7px;background:white;color:#202735}textarea{min-height:85px;resize:vertical}.fields{display:grid;grid-template-columns:1fr 1fr;gap:18px}.status{padding:10px 0;color:#31589e;font-weight:600}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;vertical-align:top;text-align:left;border-bottom:1px solid #dce2eb}th{background:#edf1f7}table.ledger{min-width:680px}.ledger td:first-child{width:160px}.ledger select{min-width:180px}.pill{display:inline-block;border-radius:20px;padding:3px 10px;background:#fff0c7;color:#775300;font-size:12px}details{margin:12px 0}summary{cursor:pointer;color:#31589e;font-weight:600}.hash{font:12px/1.5 Consolas,monospace;overflow-wrap:anywhere}img.scan{width:100%;max-width:720px;height:auto;border:1px solid #ccd3df}.export{position:sticky;bottom:0;background:#f4f5f8ee;padding:12px;border-top:1px solid #cbd4e3;display:flex;flex-wrap:wrap;gap:10px;align-items:center}#report-text{min-height:180px}.source-list{font-size:14px}.source-list li{margin:12px 0}section,.card{scroll-margin-top:20px}@media(max-width:800px){.layout{display:block}nav{position:relative;height:auto;padding:15px;display:flex;flex-wrap:wrap;gap:3px}nav strong,nav small{width:100%}nav a{padding:5px 9px;font-size:14px}.main{padding:18px 16px 60px}h1{font-size:28px}.hero,.card{padding:18px}.fields{grid-template-columns:1fr}.export{position:relative}}@media print{nav,.export,button,.links{display:none}.layout{display:block}.main{max-width:none;padding:0}.card,.hero{break-inside:avoid}.answer{break-inside:avoid}body{background:white}select,textarea{border:1px solid #888}.note{background:white}}
"""


def main():
    inventory_path = PROJECT / "data/m1/inputs/m1-02/inventory.json"
    inventory = read(inventory_path)
    research = read(PACKET / "research.json")
    docs: list[dict] = []
    (PACKET / "documents").mkdir(exist_ok=True)
    (PACKET / "raw").mkdir(exist_ok=True)

    def source(key, title, raw_path, sha, url, content=None, note="", locator=""):
        raw = raw_path.read_bytes()
        assert digest(raw) == sha, f"Raw hash mismatch: {key}"
        copy = PACKET / "raw" / sha
        if copy.exists():
            assert copy.read_bytes() == raw
        else:
            copy.write_bytes(raw)
        filename = key + (".pdf" if raw.startswith(b"%PDF") else ".html")
        target = PACKET / "documents" / filename
        if raw.startswith(b"%PDF"):
            target.write_bytes(raw)
        else:
            assert isinstance(content, str) and content.strip(), key
            safe = ReadingHTML()
            safe.feed(content)
            reader = (
                '<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'
                + html.escape(title)
                + "</title><style>"
                + STYLE
                + '.reading{max-width:1000px;margin:auto;background:white;padding:28px}.reading table{display:table}.reading .H{font-weight:700;font-size:20px}.reading .C{text-align:center}.reading .markx{color:#754528}.hit{background:#fff0a2}.reading p{overflow-wrap:anywhere}.reading pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><body><main class="reading"><a href="../index.html#library">← К пакету проверки</a><h1>'
                + html.escape(title)
                + "</h1><p>"
                + html.escape(note)
                + '</p><p><a href="'
                + html.escape(url, quote=True)
                + '" target="_blank" rel="noopener">Официальный источник</a> · <a href="../raw/'
                + sha
                + '" download>Сырой ответ</a></p><details><summary>Происхождение и точные координаты</summary><p class="hash">SHA-256: '
                + sha
                + "</p><p>"
                + html.escape(locator)
                + '</p></details><form id="find"><label for="search">Найти в документе</label><input id="search" type="text"><button>Показать первый фрагмент</button><span id="found"></span></form><hr><article>'
                + "".join(safe.parts)
                + '</article></main><script>function findText(q){document.querySelectorAll(".hit").forEach(e=>e.classList.remove("hit"));const matches=[...document.querySelectorAll("article p,article li,article h1,article h2")].filter(e=>e.textContent.toLowerCase().includes(q.toLowerCase()));document.querySelector("#found").textContent=q?" Найдено: "+matches.length:"";if(q&&matches.length){matches.forEach(e=>e.classList.add("hit"));matches[0].scrollIntoView({block:"center"})}}document.querySelector("#find").addEventListener("submit",e=>{e.preventDefault();findText(document.querySelector("#search").value)});const q=new URLSearchParams(location.search).get("q");if(q){document.querySelector("#search").value=q;findText(q)}</script></body></html>'
            )
            target.write_text(reader, "utf-8")
        docs.append(
            dict(
                id=key,
                title=title,
                sha256=sha,
                url=url,
                file="documents/" + filename,
                raw_file="raw/" + sha,
                note=note,
                locator=locator,
                view_sha256=digest(target.read_bytes()),
            )
        )

    act_keys = {
        "housing-code": "ЖК РФ",
        "federal-law-59": "59-ФЗ",
        "government-decree-354": "ПП РФ №354",
        "government-decree-491": "ПП РФ №491",
    }
    history_by_act = {}
    for key, doc in inventory["documents"].items():
        if doc["role"] != "consolidated_edition":
            source(
                key.split(":")[-1],
                doc["declared_identity"],
                ARCHIVE / "raw" / doc["primary_sha256"],
                doc["primary_sha256"],
                doc["source_url"],
                locator="Official PDF; page numbers refer to the PDF sequence.",
            )
            continue
        act = next(
            a
            for a in act_keys
            if (
                a == "housing-code"
                and key.startswith("actual.")
                and "188-ФЗ" in doc["declared_identity"]
            )
            or (a == "federal-law-59" and "59-ФЗ" in doc["declared_identity"])
            or (
                a.startswith("government")
                and a.split("-")[-1] in doc["declared_identity"]
            )
        )
        raw_path = ARCHIVE / "raw" / doc["primary_sha256"]
        payload = read(raw_path)
        field = "redtext" if "redtext" in payload else "doctext"
        source(
            act + "-current",
            act_keys[act] + " — сводный кандидат для 01.10.2026",
            raw_path,
            doc["primary_sha256"],
            doc["source_url"],
            payload[field],
            "Источник заявляет: "
            + doc["edition_claim"]["claimed_edition_label"]
            + ". Упрощённое представление для чтения; разметка исходного ответа доступна отдельно. Это кандидат, юридический допуск не выдан.",
            "$." + field,
        )
        row = next(r for r in research["historical"] if r["source_item"] == key)
        history_by_act[act] = row
        old_path = PACKET / "raw" / row["raw_sha256"]
        old = read(old_path)
        edition = row["selected_source_claim"]
        label = edition.get("redcaption", edition.get("redname"))
        source(
            act + "-historical",
            act_keys[act] + " — исторический кандидат для 01.01.2025",
            old_path,
            row["raw_sha256"],
            row["public_url"],
            old[field],
            "Источник заявляет: "
            + label
            + ". Ближайшая заявленная редакция не позже цели. Повтор загрузки: "
            + row["replay"]
            + ". Метка требует проверки применимости.",
            "$." + field,
        )
        selector = ARCHIVE / "raw" / row["selector_sha256"]
        history = "<p>Жёлтым отмечен отдельно полученный исторический кандидат. Даты и статусы ниже заявлены источником. Они требуют юридической проверки.</p><table><thead><tr><th>Дата / метка редакции</th><th>Изменяющий акт (если указан источником)</th><th>Идентификатор редакции</th></tr></thead><tbody>"
        for edition_row in read(selector)["redactions"]:
            selected = edition_row.get("redid", edition_row.get("id")) == edition.get(
                "redid", edition.get("id")
            )
            history += (
                "<tr"
                + (' class="hit"' if selected else "")
                + "><td>"
                + html.escape(
                    edition_row.get("redcaption", edition_row.get("redname", ""))
                )
                + "</td><td>"
                + html.escape(
                    edition_row.get("refadoption") or "Не указан в этой карточке"
                )
                + "</td><td>"
                + str(edition_row.get("redid", edition_row.get("id")))
                + "</td></tr>"
            )
        history += "</tbody></table>"
        source(
            act + "-history",
            act_keys[act] + " — сведения источника о редакциях",
            selector,
            row["selector_sha256"],
            row["public_url"],
            history,
            "Читаемое представление списка редакций. Исходный JSON сохранён рядом; метки не являются юридическим подтверждением дат.",
            "$.redactions",
        )

    for path in (PACKET / "acquisition/items").glob("*.json"):
        item = read(path)
        source(
            item["external_id"],
            item["declared_act_identity"],
            PACKET / "acquisition/raw" / item["latest_successful_asset"],
            item["latest_successful_asset"],
            item["declared_publication"]["official_publication_url"],
            locator="Official PDF; pages count: "
            + str(item["declared_publication"]["pages_count"]),
        )
    for key, title, sha, url, field, note in [
        (
            "law48-current",
            "48-ФЗ — сводный текст для проверки специального порядка",
            "a8937a767c797a5bea07f9e9e516e0388deb37fe425c1f697473e21e504f4339",
            "http://ips.pravo.gov.ru/search/e1a7d76abfd409ca7d2cc0188226889cc76f796f651d171d42ece8014910f008",
            "doctext",
            "Заявленная редакция от 19.08.2024. Статьи 9–11; проверить пригодность для обеих целей. Оригинальная публикация 2020 года тоже включена.",
        ),
        (
            "decree763",
            "Указ Президента №763 — общий порядок вступления в силу",
            "2008c23f442a512ab63d0392b3b8ba01b73c8333ed2eb7faa5c6924c3a01e06d",
            "http://pravo.gov.ru/proxy/ips/?docbody=&nd=102041458",
            None,
            "Legacy bank, observed edition selector rdk=8 (03.03.2022). Проверить пункт 12 и возможные специальные правила.",
        ),
    ]:
        p = PACKET / "raw" / sha
        content = read(p)[field] if field else p.read_bytes().decode("cp1251")
        source(
            key,
            title,
            p,
            sha,
            url,
            content,
            note,
            "$." + field if field else "HTML body; paragraph 12",
        )
    rg = next(r for r in research["web"] if "rg.ru" in r["url"])
    rg_raw = (PACKET / "raw" / rg["sha256"]).read_text("utf-8")
    plain = re.sub(
        "<[^>]+>",
        "\n",
        re.sub(r"<(script|style)\b.*?</\1>", "", rg_raw, flags=re.S | re.I),
    )
    plain = html.unescape(plain)
    start, end = (
        plain.find("Именем Российской Федерации"),
        plain.find("Российская газета - Федеральный выпуск"),
    )
    assert 0 <= start < end, "Cannot isolate the official court decision"
    decision_text = plain[start:end]
    source(
        "ks19p",
        "КС РФ №19-П от 18.07.2012 — текст официальной публикации",
        PACKET / "raw" / rg["sha256"],
        rg["sha256"],
        rg["url"],
        "".join(
            "<p>" + html.escape(x.strip()) + "</p>"
            for x in decision_text.splitlines()
            if x.strip()
        ),
        "Текст постановления из официального опубликования в «Российской газете». Для проверки начать с резолютивной части, пунктов 1–3. Страница КС недоступна из-за ошибки проверки сертификата; ошибка сохранена.",
        "Retained RG HTML, official decision only; operative part points 1–3",
    )

    by_id = {d["id"]: d for d in docs}
    assert len(by_id) == len(docs), "Duplicate evidence ID"
    for d in docs:
        match = re.search(r"от\s+(\d{2}\.\d{2}\.\d{4})\s+№\s+(\S+)", d["title"])
        d["short_title"] = (
            (
                ("СанПиН: " if "санитарного врача" in d["title"] else "")
                + "№"
                + match[2]
                + " от "
                + match[1]
                + " · PDF"
            )
            if match
            else d["title"]
        )

    def link(key, label=None, query="", page=None):
        d = by_id[key]
        target = (
            d["file"]
            + ("?q=" + quote(query) if query else "")
            + ("#page=" + str(page) if page else "")
        )
        return (
            '<a href="'
            + html.escape(target, quote=True)
            + '" target="_blank" rel="noopener">'
            + html.escape(label or d["short_title"])
            + "</a>"
        )

    checks = []

    def check(id, group, title, scope, proposal, evidence, inspect, gap=""):
        checks.append(
            dict(
                id=id,
                group=group,
                title=title,
                scope=scope,
                proposal=proposal,
                evidence=evidence,
                inspect=inspect,
                gap=gap,
            )
        )

    for act, title in act_keys.items():
        hist = history_by_act[act]
        label = hist["selected_source_claim"].get(
            "redcaption", hist["selected_source_claim"].get("redname")
        )
        extra = (
            "Для 59-ФЗ отдельно сверить 547-ФЗ: он опубликован в декабре 2024, но статья 2 устанавливает вступление в силу 30.03.2025."
            if act == "federal-law-59"
            else "Проверить будущие положения и условия действия из изменяющих актов, а также отсутствие пропущенных изменений до 01.01.2025."
        )
        check(
            act + "-2025",
            act,
            title + ": источник на 01.01.2025",
            "01.01.2025; выбор входного основания",
            "Предлагаю использовать полученный отдельный исторический текст ("
            + label.strip()
            + ") как кандидат исходного основания. Он не заменён более поздним текстом.",
            [act + "-historical", act + "-history"]
            + (["0001202412280052"] if act == "federal-law-59" else []),
            "Сверить реквизиты акта, выбранную строку списка редакций, полноту текста и все применимые приложения. "
            + extra,
            "Выбор ближайшей метки источника ещё не доказывает применимость каждого положения. Если цепочки дат недостаточно — отметить, какие изменяющие акты нужно добавить.",
        )

    check(
        "housing-code-2026",
        "housing-code",
        "ЖК РФ: источник на 01.10.2026",
        "01.10.2026; выбор входного основания",
        "Сводный текст с меткой 01.09.2026 оставить кандидатом; не включать будущие изменения как действующие. Отдельно учесть территориальные условия статьи 155 из №931.",
        ["housing-code-current", "housing-code-history", "0001202607270025"],
        "Проверить разделы, главы, статьи и примечания. Сверить будущие положения, а для №931 — пункт 2(a), пункт 3 и перечень субъектов.",
        "Полная цепочка поправок ЖК РФ пока не собрана в этом пакете. Общую применимость редакции нельзя подтвердить только датой в заголовке.",
    )
    check(
        "government-decree-354-2026",
        "government-decree-354",
        "№354: текст и территориальное применение",
        "01.10.2026; источник и условия применения",
        "Сохранить решение M0: метка 27.07.2026 не становится датой общей текстовой редакции. №931 оформить отдельным условием применения к указанным территориям; затронуты абз. 2–3 п.80, подп. «а» п.117 и п.119 Правил.",
        [
            "government-decree-354-current",
            "government-decree-354-history",
            "0001202607270025",
        ],
        "№931: пункты 2(б), 3, 4 и перечень четырёх субъектов. В №354 проверить само постановление, утверждённые Правила и все приложения; дату общей редакции обосновать отдельно.",
        "Пакет содержит официальный текст №931, но не доказательство отмены/продолжения каждого специального режима к 01.10.2026. Указать недостающий акт, если условие требует его проверки.",
    )
    check(
        "government-decree-491-2026",
        "government-decree-491",
        "№491: устаревший источник и поправка №1242",
        "01.10.2026; выбор базы реконструкции",
        "Сводный текст с меткой 01.09.2025 использовать только как диагностическую базу. В цепочку для 01.10.2026 включить №1242 от 26.09.2026: приложение, пункт 2; начало действия — день официального опубликования по пункту 3 постановления.",
        [
            "government-decree-491-current",
            "government-decree-491-history",
            "0001202609260011",
        ],
        "Открыть №1242: PDF стр.1, пункт 3; стр.3, пункт 2 изменений. Проверить подпункт о микрогенерации по изображению оригинала, включая точный индекс. Учесть оба комплекта Правил, утверждённых №491.",
        "Наличие одной найденной поправки не доказывает полноту всей цепочки после 01.09.2025. Для положительного подтверждения основания нужно исключить другие пропуски.",
    )
    check(
        "federal-law-59-2026",
        "federal-law-59",
        "59-ФЗ: текст на 01.10.2026 и граница 30.03.2025",
        "01.10.2026; текстовый источник",
        "Текст с меткой 30.03.2025 оставить сводным кандидатом. Изменения 547-ФЗ учесть с 30.03.2025; исторический вариант на 01.01.2025 сверять отдельно.",
        ["federal-law-59-current", "federal-law-59-history", "0001202412280052"],
        "547-ФЗ: статья 1 — изменяемые положения, статья 2 — дата действия. Сверить список изменяющих документов и статьи 4, 7, 10 закона 59-ФЗ.",
        "Нужно подтвердить отсутствие более поздних применимых поправок до контрольной даты. Специальные условия и решение КС проверяются в следующих двух карточках.",
    )
    check(
        "59-special-48",
        "federal-law-59",
        "59-ФЗ и 48-ФЗ: специальный порядок",
        "Обе даты; применимость к региональному уполномоченному",
        "Это специальный порядок для обращений к уполномоченному по правам человека в субъекте РФ. Предлагаю сохранить ссылку на 59-ФЗ с условиями статей 9–11 закона 48-ФЗ; не распространять специальные правила на любые обращения.",
        [
            "law48-current",
            "0001202003180028",
            "federal-law-59-current",
            "federal-law-59-historical",
        ],
        "48-ФЗ: статья 9, часть 2 — отсылка к 59-ФЗ с особенностями; статья 10 — условия жалобы; статья 11 — рассмотрение и сроки. Проверить редакцию этих норм на обе даты.",
        "При необходимости уточнить точные условия и адресатов в комментарии. Полный текст 59-ФЗ сохраняется; окончательный допуск редакции здесь не запрашивается.",
    )
    check(
        "59-ks19p",
        "federal-law-59",
        "59-ФЗ и КС №19-П: что уже учтено законодателем",
        "Обе даты; эффект на статьи 1–3",
        "Сопоставить резолютивные пункты 1–3 решения КС с 80-ФЗ. Статья 2 закона 80-ФЗ добавила часть 4 статьи 1 и изменила часть 1 статьи 2; эти положения видны в обоих сводных кандидатах. Предлагаю отдельно сохранить конституционное толкование и региональные гарантии, а уже внесённую поправку не применять повторно.",
        [
            "ks19p",
            "0001201305080015",
            "federal-law-59-historical",
            "federal-law-59-current",
        ],
        "КС: резолютивные пункты 1, 2, 3; 80-ФЗ: статья 2, PDF стр.2–3; 59-ФЗ: часть 4 статьи 1, часть 1 статьи 2 и статья 3. Сформулировать, остаётся ли неучтённый эффект и какие положения/условия он затрагивает.",
        "Это новый проект вывода по новым доказательствам. Прежний блокер остаётся до вашего решения; отсутствие ещё реализованной связи в коде не является само по себе доказательством неправильности текста закона.",
    )
    check(
        "sanpin-chain",
        "sanpin",
        "СанПиН: полнота исходника и цепочки",
        "Обе даты; обязательный комплект",
        "Включить постановление №3 полностью, утверждённые санитарные правила, девять приложений и таблицы, а также все девять найденных поправок. №25 в официальном PDF ссылается на предыдущие восемь; это подтверждение найденной цепочки.",
        ["0001202102050027", "0001202609240014"],
        "Сверить список ниже с ссылками в №25, PDF стр.1–2, и с самостоятельным поиском на официальном портале. Если известен ещё один акт, указать его реквизиты/ссылку.",
        "Перечисление в поздней поправке и пустые поисковые результаты не доказывают отсутствия пропусков. Положительный вывод о полноте требует вашей проверки; можно оставить недостаточность доказательств.",
    )
    for target in ["2025", "2026"]:
        check(
            "sanpin-" + target,
            "sanpin",
            "СанПиН: основание на "
            + ("01.01.2025" if target == "2025" else "01.10.2026"),
            ("01.01.2025" if target == "2025" else "01.10.2026") + "; реконструкция",
            "Выбран путь реконструкции от оригинала. Требуемый комплект и предложенные даты/условия перечислены в таблице ниже. "
            + (
                "№11 учесть: пункт 4 прямо устанавливает 31.12.2024. Поправки 2025–2026 к этой цели не относятся."
                if target == "2025"
                else "№25 не включать как действующее изменение к 01.10.2026, если подтверждён расчёт по пункту 12 Указа №763 (предлагаемое начало 05.10.2026)."
            ),
            ["0001202102050027", "0001202412270033", "0001202609240014", "decree763"],
            "Проверить строки таблицы для выбранной даты и условия действия. Это проверка входного комплекта; точный журнал всех текстовых операций и полный результат реконструкции поступят в M1-07/M1-13.",
            "Полная реконструированная редакция ещё не создана. Ответ на эту карточку не является утверждением её текста.",
        )

    ledger = [
        (
            "0001202107070011",
            "№16 · 26.06.2021",
            "18.07.2021 — расчёт по п.12 №763; проверить специальные правила",
            "Учесть",
            "Учесть",
            "Вставка п.35(1); срок в его тексте затем изменён №6 с 2022 на 2027. Читать последовательность, не объявлять пункт истёкшим в 2022.",
            3,
        ),
        (
            "0001202112300125",
            "№37 · 14.12.2021",
            "01.01.2022 — пункт 2, PDF стр.2",
            "Учесть",
            "Учесть в цепочке",
            "Меняет пункт 5 постановления №3; позднее его снова меняет №11, а №21 отменяет. До 01.03.2027 — условие действия самой поправки.",
            2,
        ),
        (
            "0001202202170032",
            "№6 · 14.02.2022",
            "18.02.2022 — день после опубликования, пункт 2, PDF стр.2",
            "Учесть",
            "Учесть",
            "Пункт 35(1): заменить 2022 на 2027; приложение, PDF стр.3.",
            3,
        ),
        (
            "0001202412270033",
            "№11 · 15.11.2024",
            "31.12.2024 — пункт 4, PDF стр.3",
            "Учесть",
            "Учесть в цепочке",
            "Пункт 3 поправки изменяет пункт 5 постановления №3: 01.01.2025 → 01.09.2025; потом №10/№21 меняют эту цепочку.",
            3,
        ),
        (
            "0001202507240013",
            "№10 · 17.06.2025",
            "31.08.2025 — пункт 2, PDF стр.2; внутри операции есть дата 01.09.2025",
            "Не учесть",
            "Учесть",
            "Изменяется само постановление №3, включая добавление п.4(1) и изменение п.5. Не смешивать старые СанПиН из отменяемого перечня с текущим текстом.",
            4,
        ),
        (
            "0001202507250037",
            "№13 · 25.06.2025",
            "05.08.2025 — расчёт по п.12 №763; проверить специальные правила",
            "Не учесть",
            "Учесть",
            "Второе предложение п.134 заменяется; сама поправка действует до 01.03.2027. Это срок окончания, не дата начала.",
            2,
        ),
        (
            "0001202512300004",
            "№21 · 29.12.2025",
            "31.12.2025 — пункт 2, PDF стр.2",
            "Не учесть",
            "Учесть",
            "Приложение, п.5, PDF стр.4: пункт 5 постановления №3 признан утратившим силу. Не считать утратившим силу весь СанПиН.",
            4,
        ),
        (
            "0001202602270023",
            "№2 · 12.02.2026",
            "10.03.2026 — расчёт по п.12 №763; проверить специальные правила",
            "Не учесть",
            "Учесть",
            "PDF стр.3: изменения п.272, 282, 286 СанПиН; изменения другого документа СП 2.2.3670-20 не включать в этот текст.",
            3,
        ),
        (
            "0001202609240014",
            "№25 · 10.09.2026",
            "05.10.2026 — расчёт по п.12 №763; проверить специальные правила",
            "Не учесть",
            "Не учесть как действующее",
            "PDF стр.3: новый абзац п.34 о складировании снега в районах Крайнего Севера и приравненных местностях. Условие территории сохранять.",
            3,
        ),
    ]
    definitions = {
        "schema": "m1-02-human-packet/1",
        "inventory_content_hash": inventory["inventory_hash"],
        "inventory_file_sha256": digest(inventory_path.read_bytes()),
        "scope": "M1-02 source routes, amendment completeness and date/application evidence; no final LegalEdition admission",
        "targets": ["2025-01-01", "2026-10-01"],
        "reviewer": "legal-reviewer-owner",
        "checks": checks,
        "amendments": [
            dict(
                id="amend-" + n,
                document=n,
                title=t,
                proposed_effective_date=d,
                proposed_2025=a,
                proposed_2026=b,
                reason=c,
                page=p,
            )
            for n, t, d, a, b, c, p in ledger
        ],
        "documents": docs,
        "research_records": [
            "research.json",
            "supplement.json",
            "final-sources.json",
            "931-search.json",
            "931-bank.json",
            "two-publications.json",
            "547-acquisition.json",
        ],
    }
    packet_hash = digest(
        json.dumps(
            definitions, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    definitions["packet_hash"] = packet_hash
    (PACKET / "packet.json").write_text(
        json.dumps(definitions, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    options = '<option value="">Выберите после проверки</option><option value="confirmed">Подтверждаю предложенный вывод</option><option value="correction">Нужна поправка</option><option value="insufficient">Недостаточно доказательств</option>'

    def answer(id, title):
        return (
            '<div class="answer" data-answer="'
            + id
            + '"><label for="decision-'
            + id
            + '">Ваше решение</label><select id="decision-'
            + id
            + '" data-field="decision">'
            + options
            + '</select><label for="comment-'
            + id
            + '">Основание / поправка / недостающий документ</label><textarea id="comment-'
            + id
            + '" data-field="comment" placeholder="Для подтверждения: что сверили и с каким источником. Для поправки: точный пункт и правильный вывод. При нехватке: какой документ нужен."></textarea></div>'
        )

    groups = [
        ("federal-law-59", "1. 59-ФЗ"),
        ("sanpin", "2. СанПиН"),
        ("government-decree-354", "3. Постановление №354"),
        ("government-decree-491", "4. Постановление №491"),
        ("housing-code", "5. Жилищный кодекс"),
    ]
    body = ""
    for group, title in groups:
        body += '<section id="' + group + '"><h2>' + title + "</h2>"
        for c in checks:
            if c["group"] != group:
                continue
            body += (
                '<div class="card" id="'
                + c["id"]
                + '"><span class="eyebrow">'
                + html.escape(c["id"])
                + "</span><h3>"
                + html.escape(c["title"])
                + '</h3><span class="pill">'
                + html.escape(c["scope"])
                + '</span><p class="label">Мой предварительный вывод — для вашей проверки</p><div class="proposal">'
                + html.escape(c["proposal"])
                + '</div><p class="label">Откройте документы</p><div class="links">'
                + "".join(link(k) for k in c["evidence"])
                + '</div><p class="label">Что именно сверить</p><p>'
                + html.escape(c["inspect"])
                + '</p><div class="note">'
                + html.escape(c["gap"])
                + "</div>"
                + answer(c["id"], c["title"])
                + "</div>"
            )
        if group == "sanpin":
            body += (
                '<div class="card" id="amendments"><h3>Девять поправок: даты и действия на обе цели</h3><p>Каждая строка — отдельный ответ. «Учесть в цепочке» сохраняет историю операции; последующий акт может заменить её результат. Даты по общему правилу №763 остаются предложением до проверки специальных норм. Полный журнал операций будет проверяться позже.</p><div class="links">'
                + link("decree763", "Открыть пункт 12 Указа №763", query="12.")
                + '</div><div class="table-scroll"><table class="ledger"><thead><tr><th>Документ</th><th>Начало действия / основание</th><th>01.01.2025</th><th>01.10.2026</th></tr></thead><tbody>'
            )
            for n, t, d, a, b, c, p in ledger:
                body += (
                    "<tr><td>"
                    + html.escape(t)
                    + "<br>"
                    + link(n, "PDF, страница " + str(p), page=p)
                    + "</td><td>"
                    + html.escape(d)
                    + "</td><td>"
                    + html.escape(a)
                    + "</td><td>"
                    + html.escape(b)
                    + '</td></tr><tr><td colspan="4"><p>'
                    + html.escape(c)
                    + "</p><details><summary>Сверить изображение страницы "
                    + str(p)
                    + '</summary><img class="scan" loading="lazy" src="pages/'
                    + n
                    + "-"
                    + str(p)
                    + '.png" alt="Официальная страница '
                    + str(p)
                    + " поправки "
                    + html.escape(t)
                    + '"></details>'
                    + answer("amend-" + n, t)
                    + "</td></tr>"
                )
            body += "</tbody></table></div></div>"
        body += "</section>"
    library = (
        '<section id="library"><h2>Библиотека документов</h2><p>Оригиналы PDF сохранены без изменений. Представления сводных текстов упрощены для чтения; исходные JSON/HTML и их хеши доступны рядом. В библиотеке '
        + str(len(docs))
        + ' документов.</p><ul class="source-list">'
    )
    for d in docs:
        library += (
            "<li>"
            + link(d["id"])
            + ' · <a href="'
            + html.escape(d["url"], quote=True)
            + '" target="_blank" rel="noopener">на официальном сайте</a><details><summary>Происхождение</summary><p>'
            + html.escape(d["note"])
            + "</p><p>"
            + html.escape(d["locator"])
            + '</p><p class="hash">'
            + d["sha256"]
            + '</p><a href="'
            + d["raw_file"]
            + '" download>Скачать неизменённый ответ</a></details></li>'
        )
    library += "</ul></section>"
    script = r"""
const packet=PACKET;const key='legal-rag-review-'+packet.packet_hash;let start=null,answers={};const ids=[...packet.checks,...packet.amendments].map(c=>c.id);const label={confirmed:'Подтверждаю',correction:'Нужна поправка',insufficient:'Недостаточно доказательств'};
function collect(){const out={};for(const el of document.querySelectorAll('[data-answer]'))out[el.dataset.answer]={decision:el.querySelector('select').value,comment:el.querySelector('textarea').value};return out}
function state(){return {packet_hash:packet.packet_hash,reviewer:document.querySelector('#reviewer').value,started_at:start,review_minutes:document.querySelector('#minutes').value,completed:document.querySelector('#completed').checked,answers:collect()}}
function update(){answers=collect();document.querySelector('#progress').textContent=Object.values(answers).filter(x=>x.decision&&x.comment.trim()).length+' / '+ids.length+' ответов с основанием';try{localStorage.setItem(key,JSON.stringify(state()));document.querySelector('#save-status').textContent='Черновик сохранён в этом браузере. Регулярно скачивайте отчёт.'}catch(e){document.querySelector('#save-status').textContent='Браузер не разрешил автосохранение. Скачайте отчёт перед закрытием.'}}
function restore(s){if(s.packet_hash!==packet.packet_hash)throw Error('Отчёт относится к другому пакету');document.querySelector('#reviewer').value=s.reviewer||'';start=s.started_at||null;document.querySelector('#minutes').value=s.review_minutes||'';document.querySelector('#completed').checked=!!s.completed;for(const el of document.querySelectorAll('[data-answer]')){let a=(s.answers||{})[el.dataset.answer]||{};el.querySelector('select').value=a.decision||'';el.querySelector('textarea').value=a.comment||''}update()}
function report(){const s=state();const missing=ids.filter(id=>!s.answers[id].decision||!s.answers[id].comment.trim());if(!s.reviewer.trim())throw Error('Укажите идентификатор проверяющего');if(s.completed&&missing.length)throw Error('Для завершённого отчёта заполните решение и основание для '+missing.length+' оставшихся ответов. Можно снять отметку завершения и скачать черновик.');return {schema:'m1-02-human-source-review/1',packet_hash:packet.packet_hash,inventory_content_hash:packet.inventory_content_hash,reviewer:s.reviewer,role:'Legal Reviewer',scope:packet.scope,targets:packet.targets,status:s.completed?'submitted':'draft',exported_at:new Date().toISOString(),started_at:s.started_at,review_minutes:s.review_minutes?Number(s.review_minutes):null,time_basis:'started_at is the reviewer start-button time; exported_at is actual export time; review_minutes is reviewer-reported, not inferred',edition_admission:false,answers:s.answers}}
function textReport(r){let t='М1-02 — отчёт проверки источников\nПроверяющий: '+r.reviewer+'\nСтатус: '+r.status+'\nЭкспорт: '+r.exported_at+'\nПакет: '+r.packet_hash+'\nЦели: '+r.targets.join(', ')+'\nОбласть: проверка входных источников и доказательств; окончательный допуск редакций не выдаётся.\n\n';for(const c of [...packet.checks,...packet.amendments]){const a=r.answers[c.id];t+=c.id+' — '+c.title+'\nПредложение: '+(c.proposal||c.proposed_effective_date+'; 2025: '+c.proposed_2025+'; 2026: '+c.proposed_2026+'; '+c.reason)+'\nРешение: '+(label[a.decision]||'Не проверено')+'\nОснование: '+(a.comment||'Не заполнено')+'\n\n'}return t}
function download(name,type,content){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([content],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000)}
document.querySelector('#start').onclick=()=>{if(!start)start=new Date().toISOString();document.querySelector('#start').textContent='Начало записано';update()};
document.querySelector('#export').onclick=()=>{try{const r=report();document.querySelector('#report-text').value=textReport(r);document.querySelector('#report').scrollIntoView({block:'start'});document.querySelector('#message').textContent='Отчёт сформирован. Скопируйте текст ниже и отправьте его в этот чат.'}catch(e){document.querySelector('#message').textContent=e.message;document.querySelector('#message').scrollIntoView({block:'center'})}};
document.querySelector('#json-export').onclick=()=>{try{download('M1-02-review.json','application/json;charset=utf-8',JSON.stringify(report(),null,2))}catch(e){document.querySelector('#message').textContent=e.message}};
document.querySelector('#text-export').onclick=()=>{try{const r=report();download('M1-02-review.txt','text/plain;charset=utf-8',textReport(r))}catch(e){document.querySelector('#message').textContent=e.message}};
document.querySelector('#import').onchange=async e=>{try{const r=JSON.parse(await e.target.files[0].text());restore(r);document.querySelector('#message').textContent='Ответы из отчёта восстановлены'}catch(e){document.querySelector('#message').textContent='Не удалось восстановить: '+e.message}};
document.querySelectorAll('select,textarea,input:not([type=file])').forEach(e=>e.addEventListener('input',update));try{const s=localStorage.getItem(key);if(s)restore(JSON.parse(s));else update()}catch(e){update()}
""".replace(
        "PACKET", json.dumps(definitions, ensure_ascii=False).replace("<", "\\u003c")
    )
    page = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>М1-02 — пакет вашей юридической проверки</title><style>'
        + STYLE
        + '</style></head><body><div class="layout"><nav><strong>Legal RAG · М1-02</strong><small>Проверка источников<br>Пакет от 02.10.2026</small><a href="#intro">Как проверить</a>'
        + "".join('<a href="#' + g + '">' + t + "</a>" for g, t in groups)
        + '<a href="#amendments">Таблица поправок</a><a href="#library">Все документы</a><a href="#report">Ваш отчёт</a></nav><main class="main"><section class="hero" id="intro"><div class="eyebrow">ПАКЕТ ДЛЯ LEGAL REVIEWER</div><h1>Проверить источники.<br>Зафиксировать выводы.</h1><p>Вы выполняете согласованную роль Legal Reviewer. Здесь собраны документы и вопросы по оставшимся проверкам М1-02 для пяти актов на две даты.</p><div class="note">Все решения оставлены пустыми. Мои выводы предварительные. Этот отчёт проверяет входные основания; полный текст реконструкции и окончательный допуск десяти редакций будут проверяться позже.</div><ol><li>Откройте документы рядом с вопросом. Точные пункты и страницы указаны в карточке; PDF сохранены в пакете.</li><li>Выберите решение и напишите основание: что сверили, что исправить или какой источник добавить.</li><li>В таблице СанПиН проверьте каждую из девяти строк для обеих дат.</li><li>Нажмите «Сформировать отчёт», скопируйте текст и передайте его мне в этом чате. Можно возвращать частями; незаполненные ответы останутся открытыми.</li></ol><div class="fields"><div><label for="reviewer">Проверяющий</label><input id="reviewer" type="text" value="legal-reviewer-owner"></div><div><label for="minutes">Фактическое время проверки, минут (если измеряли)</label><input id="minutes" type="number" min="0" step="1" placeholder="Можно оставить пустым"></div></div><p><button id="start">Начать проверку — записать время</button></p><div id="progress" class="status" aria-live="polite"></div><p id="save-status" class="muted"></p><details><summary>Границы доказательств и подготовки</summary><p>Исторические кандидаты получены отдельно и повторно загрузились без изменения байтов. Это разовые материалы для человека, производственные адаптеры и замороженные контракты M0 не менялись. Цепочки поправок ЖК РФ/№354/№491 ещё не доказаны полностью. Ошибки официального поиска и доступа сохранены в журнале. OCR применялся только как вспомогательное чтение сканов; решения сверяются с оригинальными страницами, производственный OCR M1-04 не реализован.</p><p class="hash">Хеш пакета: '
        + packet_hash
        + "</p></details></section>"
        + body
        + library
        + '<section class="card" id="report"><h2>Ваш отчёт</h2><label><input id="completed" type="checkbox"> Проверка этого пакета завершена: для каждого ответа указаны решение и основание</label><p>«Недостаточно доказательств» — полноценный результат проверки. Он сохраняет вопрос открытым. Для частичного ответа оставьте отметку завершения пустой.</p><label for="report-text">Текст отчёта для копирования в чат</label><textarea id="report-text" readonly placeholder="Нажмите «Сформировать отчёт» — текст появится здесь."></textarea><p><label for="import">Восстановить ответы из ранее скачанного JSON</label><input id="import" type="file" accept=".json,application/json"></p><p id="message" role="status" aria-live="polite"></p></section><div class="export"><button id="export" class="primary">Сформировать отчёт</button><button id="json-export">Скачать JSON</button><button id="text-export">Скачать отчёт TXT</button><button onclick="window.print()">Печать</button><span class="muted">Отправьте отчёт в этот чат</span></div></main></div><script>'
        + script
        + "</script></body></html>"
    )
    (PACKET / "index.html").write_text(page, "utf-8")
    template = (
        "# М1-02 — форма ответа\n\nПроверяющий: legal-reviewer-owner\n\nХеш пакета: "
        + packet_hash
        + "\n\nЦели: 01.01.2025 и 01.10.2026. Проверка источников; окончательный допуск редакций не выдаётся.\n\nДля каждого пункта: подтверждаю / нужна поправка / недостаточно доказательств; основание и точный источник. Можно отвечать частями.\n\n"
    )
    for c in checks + definitions["amendments"]:
        template += (
            "## "
            + c["id"]
            + " — "
            + c["title"]
            + "\n\nРешение: \n\nОснование / поправка / недостающий документ: \n\n"
        )
    (PACKET / "Форма-ответа.md").write_text(template, "utf-8")
    (PACKET / "README.txt").write_text(
        "Начните с index.html — откройте в браузере. Пакет работает без интернета; внешние официальные ссылки требуют сети.\n\n1. Прочитайте вопрос и предварительный вывод. Откройте приложенный источник.\n2. Заполните решение и основание.\n3. В таблице СанПиН заполните все девять строк.\n4. Скачайте JSON или TXT и отправьте его в чат. Если удобнее обычный текст, заполните Форма-ответа.md.\n\nСначала распакуйте ZIP целиком. Автосохранение зависит от браузера и места открытия: для переноса используйте экспорт/восстановление JSON.\n\nПакет не изменяет исходную инвентаризацию и решения M0. Никакое решение не проставлено заранее.\n",
        "utf-8",
    )
    # Keep one runnable integrity check with the artifact builder.
    for d in docs:
        assert digest((PACKET / d["raw_file"]).read_bytes()) == d["sha256"]
        assert (PACKET / d["file"]).is_file()
    assert len(checks) == 13 and len(ledger) == 9
    assert all(k in by_id for c in checks for k in c["evidence"])
    assert all(
        (PACKET / f"pages/{n}-{p}.png").is_file() for n, _, _, _, _, _, p in ledger
    )
    files = {
        p
        for base in ["documents", "raw", "pages", "acquisition"]
        for p in (PACKET / base).rglob("*")
        if p.is_file()
    }
    files.update(PACKET / p for p in definitions["research_records"])
    files.update(
        PACKET / p
        for p in ["index.html", "packet.json", "README.txt", "Форма-ответа.md"]
    )
    with ZipFile(PACKET / "M1-02-review-package.zip", "w", ZIP_DEFLATED) as z:
        for path in sorted(files):
            z.write(path, path.relative_to(PACKET).as_posix())
    print(
        json.dumps(
            {
                "packet": str(PACKET / "index.html"),
                "documents": len(docs),
                "questions": len(checks),
                "amendment_rows": len(ledger),
                "packet_hash": packet_hash,
                "zip_bytes": (PACKET / "M1-02-review-package.zip").stat().st_size,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
