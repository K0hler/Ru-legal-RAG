"""Matching views and text/category predicates; source text is never replaced."""

from __future__ import annotations

import re

from .model import (
    Paragraph,
    Region,
)

SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
SUP_DIGIT = {c: str(i) for i, c in enumerate(SUP)}
LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"  # legal lettering skips ё, й, ъ, ы, ь
ROMAN_CHARS = "IVXLCХІ"  # Cyrillic Х and Ukrainian І appear in OCR
TERMINAL = ".;:!?"
NOISE_CATEGORIES = {"Page-header", "Page-footer"}


def roman_value(text: str) -> int | None:
    text = text.upper().replace("Х", "X").replace("І", "I")
    if not text or any(c not in "IVXLC" for c in text):
        return None
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    for i, c in enumerate(text):
        v = values[c]
        total += -v if i + 1 < len(text) and values[text[i + 1]] > v else v
    return total


def to_roman(n: int) -> str:
    out = ""
    for v, s in ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s
            n -= v
    return out


def view(text: str) -> str:
    """Whitespace/Markdown view for matching only; source text is never replaced."""
    lines = [re.sub(r"^\s*#{1,6}\s+", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def sup_value(marks: str) -> int | str:
    number = "".join("-" if c == "⁻" else SUP_DIGIT[c] for c in marks)
    return number if "-" in number else int(number) if number else 0


def strip_sup(text: str) -> str:
    return re.sub(rf"[{SUP}⁻]+", "", text).rstrip()


# Case-sensitive capitalised word. «ОДОБРЕН распоряжением …» (an endorsed agreement) only in capitals: the law
# requisite «Одобрен Советом Федерации» is no caption.
APPROVAL = re.compile(r"^(УТВЕРЖДЕН[АЫО]?|Утвержден[аыо]?|ОДОБРЕН[АЫО]?)\b(?:\s|$)")
# Step 20 A (batch 19): OCR may print the word «Приложение» (with or without a number) and the approval caption in
# one region: «Приложение ⏎ Утверждены ⏎ постановлением …». The approval word right after it makes the caption.
ANNEX_BEFORE_APPROVAL = re.compile(r"^(?:ПРИЛОЖЕНИЕ|Приложение)(?:\s*(?:№|N)?\s*\d+)?\s+(?=(?:УТВЕРЖДЕН|Утвержден|ОДОБРЕН))")


# Step 20 B: a point of the act that approves a document («1. Утвердить санитарные правила …»).
APPROVE_CLAUSE = re.compile(r"^(?:\d{1,2}[.)]\s*)?Утвердить\b")
UNCAPTIONED_EVIDENCE = {"approved_without_caption": "the act approves a document and is signed; its text starts on "
                                                    "the next page without a recognised caption -> approved document"}


def approval_caption(text: str) -> bool:
    return bool(APPROVAL.match(ANNEX_BEFORE_APPROVAL.sub("", text, count=1)))
# The number follows a number sign («№», Latin «N», Cyrillic «Н», OCR Greek «Ν») or a plain space:
# «Приложение № 2», «Приложение N 2», «Приложение 2». A bare number needs more evidence (annex_caption).
ANNEX = re.compile(r"^(?:ПРИЛОЖЕНИЕ|Приложение)(?:\s*(?P<sign>№|N|Н|Ν)?\s*(?P<number>\d+))?(?:\s+(?P<ref>к\s.+))?$")
# A caption is not a sentence: a final dot only after a date («г.», «01.02.2020.») or a number «№ 5н.».
CAPTION_FINAL_DOT = re.compile(r"(?:\sг\.|\d{1,2}\.\d{1,2}\.\d{4}\.|(?:№|N)\s*\d[\w/-]*\.)$")
# A caption ends in a noun, a quote, a date or a number, never mid-phrase: a final comma, hyphen or a
# function word («которые», «и», «в») is a broken sentence («Приложение 3 к Порядку содержит формы, которые»).
CAPTION_BROKEN_TAIL = re.compile(r"(?:[,\-–—]|(?<![А-Яа-яЁё])(?:который|которая|которое|которые|которых|что|и|или|а"
                                 r"|но|в|во|на|с|со|по|для|к|о|об|из|за|при|без|не))$")


# A standalone draft mark: «Проект» / «ПРОЕКТ», optionally followed by one word that
# names the draft («Проект соглашения»), and nothing else.
PROJECT = re.compile(r"^(?:ПРОЕКТ|Проект)(?:\s+[А-Яа-яЁё-]+)?$")
REPEAT_THRESHOLD = 3  # a header/footer text on this many regions is running text
CAPTION_MAX = 120  # an annex caption in the body
CAPTION_BLOCK_MAX = 300  # an approval caption; an annex caption printed as a page header
CAPTION_UPPER_MAX = 600  # «ПРИЛОЖЕНИЕ № N к <Документ с длинным названием>»
PROJECT_MAX = 40


def is_caption(text: str) -> bool:
    return (approval_caption(text) or (bool(ANNEX.match(text)) and len(text) <= CAPTION_MAX)
            or bool(re.fullmatch(r"\(?Рекомендуемый образец\)?", text, re.IGNORECASE)))


def is_project_caption(text: str) -> bool:
    """A standalone «Проект»/«ПРОЕКТ» mark of an attached draft (agreement, treaty): the
    word alone or with one naming word, at most 40 characters, so neither «Проект
    постановления подлежит ...» nor «Проект решения рассмотрен» is a caption."""
    return bool(PROJECT.match(text)) and len(text) <= PROJECT_MAX


# The referent of an annex caption «Приложение [№] N к <referent>». The act itself: a law,
# code, resolution, order, decree, directive or decision («к Федеральному закону», «к
# настоящему приказу»). Any other referent is a document: an attached document named by its
# kind («к Правилам», «к Порядку», «к Административному регламенту») or its designation («к
# СП 2.1.3684-21»), which a capitalised word right after «к» (and «настоящ…») marks.
ACT_REFERENT = re.compile(r"^к\s+(?:настоящему\s+)?(?:(?:федеральному\s+)?(?:конституционному\s+)?закону"
                          r"|кодексу|постановлению|приказу|указу|распоряжению|решению)(?![а-яё])", re.IGNORECASE)
DOCUMENT_REFERENT = re.compile(r"^к\s+(?:настоящ[а-яё]+\s+)?[А-ЯЁA-Z]")
# Cycle 10 B2: «к форме налоговой декларации», «к порядку заполнения …» — a document named by a lowercase noun (not the
# act itself, which ACT_REFERENT catches first)
LOWERCASE_DOCUMENT_REFERENT = re.compile(r"^к\s+(?:настоящ[а-яё]+\s+)?[а-яё]{3,}")
# Step 12 B3: «…, утвержденному приказом Министерства …»: the caption names its document by the act approving it
APPROVED_DOCUMENT = re.compile(r"утвержденн[а-яё]+\s+(?:приказом|постановлением|распоряжением|указом|решением)")


# The kind of the act itself, from a header line («ПОСТАНОВЛЕНИЕ», «ПРИКАЗ», «ФЕДЕРАЛЬНЫЙ ЗАКОН») or
# from the approval caption («УТВЕРЖДЕН приказом …»); it decides whether «к приказу» names the act.
ACT_KIND_DATIVE = {"закону": "закон", "кодексу": "кодекс", "постановлению": "постановление", "приказу": "приказ",
                   "указу": "указ", "распоряжению": "распоряжение", "решению": "решение"}
ACT_HEADER = re.compile(r"^(?:#+\s*)?(?:ФЕДЕРАЛЬНЫЙ\s+(?:КОНСТИТУЦИОННЫЙ\s+)?)?(ЗАКОН|ПОСТАНОВЛЕНИЕ|ПРИКАЗ|УКАЗ"
                        r"|РАСПОРЯЖЕНИЕ|РЕШЕНИЕ)$")
APPROVED_BY = re.compile(r"(?<![а-яё])(законом|постановлением|приказом|указом|распоряжением|решением)(?![а-яё])",
                         re.IGNORECASE)
INSTRUMENTAL_KIND = {"законом": "закон", "постановлением": "постановление", "приказом": "приказ", "указом": "указ",
                     "распоряжением": "распоряжение", "решением": "решение"}


def act_kind_of_header(raw: str) -> str | None:
    """A whole header line naming the act's own kind: «ПОСТАНОВЛЕНИЕ», «ФЕДЕРАЛЬНЫЙ ЗАКОН»."""
    for line in raw.splitlines():
        m = ACT_HEADER.match(line.strip())
        if m:
            return m.group(1).lower()
    return None


def act_kind_of_approval(text: str) -> str | None:
    """The act kind of an approval caption: «УТВЕРЖДЕНЫ постановлением Правительства» -> постановление."""
    m = APPROVED_BY.search(text)
    return INSTRUMENTAL_KIND[m.group(1).lower()] if m else None


def annex_to_act(reference: str, act_kind: str | None = None) -> bool:
    """The reference names the act itself: «к настоящему приказу», or an act word of the act's own
    kind («к приказу …» in an order). Another kind («к приказу Минфина …» inside a resolution) is
    a foreign act, so the annex stays with the current attached document. With an unknown act
    kind any act word names the act."""
    m = ACT_REFERENT.match(reference)
    if not m:
        return False
    words = m.group(0).lower().split()
    if "настоящему" in words or act_kind is None:
        return True
    return ACT_KIND_DATIVE[words[-1]] == act_kind


def annex_caption(p, next_text: str = "", first_on_page: bool = False) -> re.Match | None:
    """An annex caption paragraph «Приложение [№] N [к <referent>]», never a sentence: a final
    dot only after a date or a number (CAPTION_FINAL_DOT) and no broken tail (CAPTION_BROKEN_TAIL).
    A bare number without a number sign («Приложение 2») needs evidence: a «к …» reference on
    the line or in the next paragraph, a page-header category, or the first text paragraph of its
    page (a table or picture above it does not count).
    A body caption is short (<= CAPTION_MAX). A longer one, up to CAPTION_BLOCK_MAX, is a caption
    when it is printed as a page header (positional evidence) or when its reference names the
    act or a capitalised document («Приложение 1 к Федеральному закону "О бюджете …"»,
    «Приложение к Порядку …, утвержденному приказом …»). A reference inside a sentence
    («согласно приложению 1») does not start the paragraph and opens nothing."""
    text = p.text
    m = ANNEX.match(text)
    if not m or (text.endswith(".") and not CAPTION_FINAL_DOT.search(text)) or CAPTION_BROKEN_TAIL.search(text):
        return None
    if m.group("number") and not m.group("sign") and not (
            m.group("ref") or next_text.startswith("к ") or p.first.category == "Page-header" or first_on_page):
        return None
    if len(text) <= CAPTION_MAX:
        return m
    reference = m.group("ref") or ""
    # «ПРИЛОЖЕНИЕ № N к <Документ> …» is a caption even when the document's full name is long (an agreement
    # title: 373 characters in development); sentences never start with it. Cycle 9: so is the title-case
    # «Приложение № N к Административному регламенту по предоставлению …, утвержденному приказом … № 494»
    # (328 characters): a numbered caption naming a capitalised document, never a sentence (no final dot).
    # Step 12 B3: «Приложение № 2 к порядку представления …, утвержденному приказом … № 791» (OCR Text): a numbered
    # caption naming a lowercase document approved by an act, never a sentence
    approved_document = bool(m.group("sign") and LOWERCASE_DOCUMENT_REFERENT.match(reference)
                             and APPROVED_DOCUMENT.search(text))
    document_reference = bool(DOCUMENT_REFERENT.match(reference) or (
        text.startswith("ПРИЛОЖЕНИЕ") and LOWERCASE_DOCUMENT_REFERENT.match(reference)))
    long_allowed = text.startswith("ПРИЛОЖЕНИЕ") or DOCUMENT_REFERENT.match(reference) or approved_document
    limit = CAPTION_UPPER_MAX if long_allowed and (m.group("sign") or text.startswith("ПРИЛОЖЕНИЕ")) else CAPTION_BLOCK_MAX
    # step 23 E (prikaz-fns-269-2020): «Приложение к форме свидетельства от «21» 04 2020г. № … о регистрации … Форма» —
    # a caption naming a form (FORM_REFERENT) whose long tail is the form's own date, number and title
    if len(text) < limit and (p.first.category == "Page-header" or ACT_REFERENT.match(reference)
                              or document_reference or approved_document
                              or FORM_REFERENT.match(reference)):
        return m
    return None


def running_caption(p) -> bool:
    """A later repeat of a caption printed as a running header/footer (same text on three
    or more regions). Controller ruling: the first occurrence still opens the scope."""
    r = p.first
    return r.category in NOISE_CATEGORIES and r.repeats >= REPEAT_THRESHOLD and r.repeat_index > 0


def heading_like(text: str, category: str) -> bool:
    return category in {"Section-header", "Title"} or (len(text) < 250 and not text.rstrip().endswith((".", ";", ":")))


def terminated(text: str) -> bool:
    t = strip_sup(text).rstrip(" »\")")
    return bool(t) and t[-1] in TERMINAL


def starts_continuation(text: str) -> bool:
    """A lowercase or «(» start continues the previous paragraph, except a standalone editorial note of a
    consolidated edition («(Статья в редакции …)» at the top of a page is no continuation)."""
    return bool(text) and (text[0].islower() or (text[0] == "(" and not editorial_note_unit(text)))


def continues_reference(tail: str, head: str) -> bool:
    """A printed legal citation split inside its title, date, act kind or unit list."""
    dated = bool(re.search(r"\bот$", tail) and re.match(r"\d{1,2}\.\d{1,2}\.\d{4}\b", head))
    act_reference = re.search(r"\b(?:постановлени\w*|закон\w*|приказ\w*|указ\w*|распоряжени\w*|решени\w*)\b",
                              tail, re.IGNORECASE)
    act_title = bool(head.startswith(('"', '«')) and re.search(r"(?:№|N)\s*\d[\w./-]*$", tail)
                     and act_reference)
    open_title = bool(head[:1].isupper() and act_reference
                      and re.search(r"(?:№|N)\s*\d[\w./-]*\s+«[^»]*$", tail))
    act_kind = bool(re.search(r"\b(?:стать\w*|пункт\w*|част\w*|глав\w*)\s+\d[\d.]*$", tail, re.IGNORECASE)
                    and re.match(r"(?:Федерального\s+(?:конституционного\s+)?закона|Кодекса)\b", head))
    unit_list = bool(re.search(r"\b(?:стать\w*|пункт\w*|подпункт\w*|част\w*|глав\w*)\s+\d", tail, re.IGNORECASE)
                     and re.search(r"\d+(?:\.\d+)+,$", tail) and re.match(r"\d+(?:\.\d+)+,", head))
    return dated or act_title or open_title or act_kind or unit_list


def footnote_number(text: str) -> int | None:
    m = re.match(rf"^([{SUP}]+)", text)
    return int("".join(SUP_DIGIT[c] for c in m.group(1))) if m else None


# Step 21.2 A (sanpin-81-2016, sanpin-44-2017): a Footnote region whose number OCR printed as plain digits («15 СП …»).
PLAIN_FOOTNOTE_NUMBER = re.compile(r"^(\d{1,3})\.?\s+(?=[«\"А-Яа-яЁёA-Za-z])")


def region_footnote_number(region: "Region", *, allow_plain: bool = False) -> int | None:
    number = footnote_number(region.text)
    if number is None and (region.category == "Footnote" or allow_plain):
        m = PLAIN_FOOTNOTE_NUMBER.match(region.text)
        number = int(m.group(1)) if m else None
    return number


def signature_like(region: Region) -> bool:
    text = region.text
    right = region.bbox[0] > region.page_size[0] * 0.55
    initials = re.fullmatch(r"[А-ЯЁ]\.\s?(?:[А-ЯЁ]\.\s?)?[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?", text)
    title = re.match(r"^(Председатель|Руководитель|Министр|Главный государственный санитарный врач)\b", text)
    # title and right-edge lines must be short unterminated lines that do not start lowercase:
    # «Руководитель органа обеспечивает исполнение.» or a right-aligned «… ассигнований;» is text
    line = bool(text) and not text[0].islower() and not terminated(text)
    # cycle 10 B1: a table/figure caption («Таблица 4.4» on a landscape page; OCR Caption or the text itself) is
    # never a signature by its position alone
    figure = region.category == "Caption" or bool(FIGURE_CAPTION.match(text)) or region.row_cell
    return bool(initials or (line and title and len(text) < 120)
                or (line and right and len(text) < 40 and not is_caption(text) and not figure))


# Requisites of an act or of an attached document, recognised from text alone (no X
# coordinate): signer, place, date, number, registration, closing formula, barcode.
MONTHS = "января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря"
DATE = rf"(?:«?\s*\d{{1,2}}\s*»?\s+(?:{MONTHS})\s+\d{{4}}\s*(?:г\.|года)?|\d{{1,2}}\.\s?\d{{1,2}}\.\s?\d{{4}}(?:\s*г\.)?)"
NUMBER = r"(?:№|N)\s*\d[\w./-]*"
REQUISITE_LINES = (
    re.compile(rf"^(?:от\s+)?{DATE}(?:\s+{NUMBER})?$"),  # «19 февраля 2018 года», «28.08.2015 № 901»
    re.compile(rf"^{NUMBER}$"),  # «№ 23-ФЗ», «N 204»
    re.compile(rf"^(?:г\.\s*)?(?:Москва|МОСКВА)(?:,\s*Кремль)?(?:\s+{DATE})?(?:\s+{NUMBER})?$"),
    re.compile(r"^Зарегистрирован[оа]?\s+в\s+Мин"),  # «Зарегистрировано в Минюсте России ...»
    re.compile(r"^Совершено(?:\s+в\b|\s*_{2,})"),  # actual or blank agreement closing formula
    re.compile(r"^(?:Составлен[ао]?|Ответ\s+на\s+запрос\s+прошу\s+направить)\s+_{2,}"),  # step 24 D: form tail
    re.compile(r"^[_\-–—\s]{3,}$"),  # a closing rule line
)
# signer title or agreement signature place («За Правительство ...», «От Правительства ...»): a short
# unterminated line; «От Сторон» names both parties, not one signature place; step 12 B4: the signature place of a
# sample form «Высшее должностное лицо субъекта Российской Федерации (уполномоченное им лицо)»; step 13 B3: the head
# of a federal service signs as «Директор» («Директор» / «А.Бортников»)
SIGNER = re.compile(r"^(?:(?:Президент|Председатель|Заместитель Председателя|Первый заместитель|Руководитель|Министр"
                    r"|(?:Генеральный\s+)?Директор"
                    r"|Временно исполняющий обязанности|Исполняющий обязанности|Врио|И\.\s?о\.|Главный государственный санитарный врач"
                    r"|(?:Высшее\s+должностное|Должностное)\s+лицо)\b"
                    r"|(?:За|От)\s+(?!Сторон(?![а-яё]))[А-ЯЁ][а-яё]+)")
# the heading of an agreement's signature block: «Подписи и реквизиты Сторон», «Адреса и реквизиты сторон»
SIGNATURE_HEADING = re.compile(r"^(?:(?:юридические\s+)?адреса|подписи|(?:банковские\s+)?реквизиты)"
                               r"(?:,?\s+(?:и\s+)?(?:(?:юридические\s+)?адреса|подписи|(?:банковские\s+)?реквизиты))*"
                               r"\s+сторон$", re.IGNORECASE)
INITIALS = r"[А-ЯЁ]\.\s?(?:[А-ЯЁ]\.\s?)?[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?"
# the signature heading of a form: «Подписи членов рабочей комиссии:», «Подпись руководителя:» (a few words, a colon)
FORM_SIGNATURE_HEADING = re.compile(r"^Подпис[иь](?:\s+[а-яё]+){1,5}:$")
# step 22 D (rp-1829-2015 readmission forms): the signature line «Подпись представителя центрального компетентного органа
# государства запрашивающей Стороны» under a form's last part
FORM_SIGNER_LINE = re.compile(r"^Подпись\s+[а-яё]+(?:\s+\S+){0,15}$")
FORM_SIGNER_LINE_MAX = 200
BLANK_LINE = re.compile(r"^[_\s]{3,}$")
# Step 13 B3: the captions under a form's signature lines — «(подпись)», «(наименование должности», «(инициалы,
# фамилия)» — and the seal place «М.П.» («М.П. (при наличии)»). Not «(фамилия, имя, отчество)»: that captions a
# field of the form («Я, ______,»), not its signature.
# step 21.4 D, E: «(место для подписи …)», «(фамилия, имя, отчество … должностного лица, заполнившего …)» and the date
# line ««___» ______ 20__ г.» sign a form (the bare «(фамилия, имя, отчество)» of a field «Я, ___» does not)
SIGNATURE_CAPTION = re.compile(r"^\((?:подпись|наименование\s+должности|инициалы|место\s+для\s+подписи"
                               r"|фамилия,\s+имя,\s+отчество.*?(?:должностного\s+лица|заполнившего|подписавшего))"
                               r"|^М\.\s?П\.(?:\s|$)|^«\s*_{2,}\s*»\s*_{2,}", re.IGNORECASE)


PAGE_MARK = re.compile(r"[\w-]+(?:\.[\w-]+)*\.(?:docx?|rtf|odt)", re.IGNORECASE)
# Cycle 10 B1: a typist's mark «Компьютер /Н.Н./При-К7552-3», «21.08.2024 15:44 kompburo /Н.И./П-К7552»: a word,
# initials between slashes and a job code; OCR reads the word differently on every page, so it is not running noise.
PRINT_MARK = re.compile(r"^(?:[\d.:\s]+)?[\w.]+\s*/\s*[А-ЯЁA-Z]\.\s?(?:[А-ЯЁA-Z]\.)?\s*/\s*[\w.-]*$")
# Step 12 B1: OCR reads such a mark beyond recognition («1. Коприво ИНМ / Прип-ГВ108-0», «Г. конфликт /ИН И /Прип.
# Г0198-3»); what survives is the job code at the end, after a slash: a short word, maybe a dot or hyphen, letters and
# digits, maybe a sheet number («Прил-ГВ198-3», «Прим. 18198-7», «П-К7552», «Прип-СВ199 5»). Without the slash
# («И.И. Прын-ТВ108-1», «(Прим-Г8198-2)») the code needs its hyphen and three digits («Стр. 12» is no job code).
JOB_CODE = re.compile(r"/[^/]*?[А-ЯЁA-Z][А-Яа-яЁёA-Za-z]{0,4}\.?\s*-?\s*[А-ЯЁA-Z0-9]{0,3}\s?\d{2,5}(?:[-\s]\d)?$"
                      r"|(?:^|[\s(.])[А-ЯЁA-Z][А-Яа-яЁёA-Za-z]{0,4}-[А-ЯЁA-Z0-9]{0,3}\d{3,5}(?:-\d)?\)?$")
PAGE_MARK_EVIDENCE = {"page_mark": "file name printed in a page header/footer"}
# Step 21.2 B (pp-931-2022, pp-996-2022): the document's page code printed as body text at the page foot, «5590030 (1.4)».
PAGE_CODE_LINE = re.compile(r"\d{6,8}\s*\(\s*\d[\d.\s]*\)")
BARCODE_EVIDENCE = {"barcode": "last body line on its page"}
PAGE_BAND_EVIDENCE = {"page_band": "a page header/footer opens no unit"}


# Step 21.5 E (prikaz-fns-815-2024): a time stamp of the typist's mark, and the head of a declaration page — its page
# barcode «1680 6016» and the fields «ИНН», «КПП», «Стр.» — printed as body text near the top of a page.
TIME_STAMP = re.compile(r"\d{2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}")
FORM_PAGE_HEAD = re.compile(rf"\d{{4}}\s\d{{4}}|(?:ИНН|КПП)[{SUP}]*|ИНН\s+КПП\s+Стр\.|Стр\.(?:\s[\d\s]+)?")
FORM_HEAD_ZONE = 8  # the first regions of a page
FORM_SERVICE_MARK = re.compile(r"(?:(?:лицевая|оборотная)\s+сторона\s+листа\s+№\s*\d+"
                               r"|Место\s+для\s+служебных\s+отметок(?:\s+.+)?)", re.IGNORECASE)


def page_mark(region: Region) -> bool:
    """A service file code printed in a page header/footer («200716A9.doc») or a typist's mark
    («Компьютер /Н.Н./При-К7552-3»), not repeated often enough to be running noise: a mark of the page,
    never text of the unit it happens to follow. Step 16 C5: also a footer line printed on two pages («ФГОС ВО
    культурология -05»; on three it is running noise)."""
    text = region.text.strip()
    if is_caption(text):
        return False
    if FORM_SERVICE_MARK.fullmatch(text):
        return True  # step 24 B: a sheet side or service-stamp place is not text of the preceding form field
    if region.category == "Text":
        return bool(PRINT_MARK.match(text) or TIME_STAMP.fullmatch(text)
                    or (region.index <= FORM_HEAD_ZONE and FORM_PAGE_HEAD.fullmatch(text)))
    return region.category in NOISE_CATEGORIES and bool(PAGE_MARK.fullmatch(region.text) or PRINT_MARK.match(region.text)
                                                        or (region.category == "Page-footer" and re.fullmatch(r"\d{6,8}", text))
                                                        or (len(region.text) <= 100 and JOB_CODE.search(region.text))
                                                        or (region.category == "Page-footer" and region.repeats == 2)
                                                        or "компьют" in text.lower() or 0 < len(text) <= 2)


def barcode_like(text: str) -> bool:
    """A printed barcode number: one run of 12-14 digits or EAN-13 grouping «2 100039 06204 3»."""
    return bool(re.fullmatch(r"\d{12,14}|\d\s\d{6}\s\d{5}\s\d", text))


def signature_caption(text: str) -> bool:
    return bool(SIGNATURE_CAPTION.match(text)) and len(text) < 120


def requisite_like(text: str) -> bool:
    """A requisite line of a signature block: signer title (optionally with initials and
    surname), initials and surname, «Москва, Кремль»/«Москва», date, number, registration
    mark, agreement closing formula, signature heading («Подписи и реквизиты Сторон») and signature
    places («За …», «От …»), barcode. Text-only."""
    if barcode_like(text) or any(p.match(text) for p in REQUISITE_LINES) or re.fullmatch(INITIALS, text):
        return True
    if SIGNATURE_HEADING.match(text) or FORM_SIGNATURE_HEADING.match(text):
        return True
    if FORM_SIGNER_LINE.match(text) and len(text) <= FORM_SIGNER_LINE_MAX and not terminated(text):
        return True
    return bool(SIGNER.match(text)) and len(text) < 120 and not terminated(text)


# A footnote marked by asterisks instead of a number: «*- с точностью до 10 см;», «** …».
ASTERISK_NOTE = re.compile(r"^(\*{1,3})(?!\*)\s*[-–—]?\s*\S")
# OCR markdown emphasis («*курсив*», «**Примечание**»): a balanced pair inside one line and one table cell.
EMPHASIS = re.compile(r"(?<!\*)(\*{1,3})(?=[^\s*])([^*\n<>]+?)(?<=\S)\1(?!\*)")


def strip_emphasis(text: str) -> str:
    """Text without balanced markdown emphasis pairs, so they are not read as asterisk footnote marks."""
    return EMPHASIS.sub(r"\2", text)


# Cycle 10 B4: a table-of-contents line — words, then a dot leader and maybe a page number («I. Общие сведения
# ………… 1», «3.1. Обобщенная трудовая функция «…» ……»).
TOC_LEADER = re.compile(r"(?:\s*\.){5,}\s*\d{0,4}\s*$|…{2,}\s*\d{0,4}\s*$")
TOC_EVIDENCE = {"toc_line": "table-of-contents line (dot leader): text of the document root"}


def toc_line(text: str) -> bool:
    """A contents line: a dot leader at the end and at least three letters before it (a fill-in line
    «2. ……………» has none)."""
    m = TOC_LEADER.search(text or "")
    return bool(m) and len(re.findall(r"[А-Яа-яЁёA-Za-z]", text[:m.start()])) >= 3


# A numbered fill-in line of a form: the marker and only a blank («2. __________», «3) .......»).
FILL_IN = re.compile(r"^\d{1,3}[.)]\s*(?=[_.…])[_.…\s]{3,}[;.]?$")  # step 23 D: «1. ______;» (fns-269 form)
FILL_IN_EVIDENCE = {"fill_in_line": "after a numbered fill-in line of a form: its parent (the line holds no text)"}


def fill_in_line(text: str) -> bool:
    return bool(FILL_IN.match(text.strip()))


# Step 21.5 C (prikaz-minkultury-1321-2016): a numbered field line with labels and blanks ending in a blank
# («20. Телефон/факс __________ Адрес электронной почты __________»): a sentence after it is the form's, the field's
# caption «(…)» stays with the field.
# step 22 C (pp-648-2016): a field may end with a date blank «"__" __________ 20__ г.»
FIELD_LINE = re.compile(r"^\d{1,3}[.)]\s+\S.*_{5,}\s*(?:\d{2}_{2}\s*г\.?)?\s*$")


def field_line(text: str) -> bool:
    return bool(FIELD_LINE.match(text.strip()))
HEADING_CATEGORIES = {"Section-header", "Title"}
# A figure/table/form caption by its text: «Схема 2», «Рисунок 1 - Знак …», «Рис. 3», «Таблица 3», «Форма N 2».
FIGURE_CAPTION = re.compile(r"^(?:Схема|Рисунок|Рис\.|Таблица|Форма|Диаграмма|График)\s*(?:№|N)?\s*\d")


def final_char(text: str) -> str:
    t = strip_sup(text).rstrip(" »\")")
    return t[-1] if t else ""


# A consolidated edition appends notes to a provision: «… Кодекса). (В редакции Федерального закона от …)».
EDITORIAL_TAIL = re.compile(
    r"\s*\((?:В\s+редакции|Дополнен|Утратил|Утратила|Исключен|Признан|"
    r"(?:Статья|Глава|Раздел|Часть|Пункт|Подпункт|Абзац)\s+(?:\S+\s+)?(?:в\s+редакции|утратил|утратила|исключен))"
    r"[^()]*(?:\([^()]*\)[^()]*)*\)\s*$")


def provision_final(text: str) -> str:
    """Final character of a provision's own text, ignoring trailing editorial notes of a consolidated edition."""
    stripped = text
    while True:
        cut = EDITORIAL_TAIL.sub("", stripped)
        if cut == stripped:
            return final_char(stripped)
        stripped = cut


def editorial_only(p: "Paragraph") -> bool:
    return bool(p.text) and p.marker.kind == "none" and (
        not EDITORIAL_TAIL.sub("", p.text).strip() or editorial_note_unit(p.text) is not None)


def heading_evidence(p: Paragraph, bold: bool = False) -> bool:
    emphasis = EMPHASIS.fullmatch(p.text) if bold else None
    return p.first.category in HEADING_CATEGORIES or bool(emphasis and len(emphasis.group(1)) >= 2)


def quote_balance(text: str) -> int:
    return text.count("«") - text.count("»")


# An editorial note of a consolidated edition names the unit it is about: «(Статья в редакции …)»,
# «(Часть 2 утратила силу …)», «(Дополнение пунктом - …)», «(Особенности применения статьи 3 - …)».
EDITORIAL_NOTE = re.compile(
    r"^\((?:(?P<unit>Статья|Глава|Раздел|Часть|Пункт|Подпункт)\s+(?:\S+\s+)?"
    r"(?:в\s+редакции|утратил|утратила|утратило|исключен|признан)"
    r"|Дополнен(?:ие|а|о|ы)?\s+(?P<added>статьей|главой|разделом|частью|пунктом|подпунктом)"
    r"|Особенности\s+применения\s+(?P<applied>статьи|главы|раздела|части|пункта|подпункта)"
    r"|Положения\s+(?P<provisions>статьи|главы|раздела|части|пункта|подпункта)\s)")
EDITORIAL_NOTE_MAX = 400


# Other notes name their unit inside: «(Приостановлено … действие пункта 1 - Федеральный закон …)»,
# «(До 1 января 2027 года не применяются положения пункта 3 …)», «(О несоответствии Конституции … статьи 242¹
# - Постановление Конституционного Суда …)». They cite the amending or deciding act.
NOTE_SOURCE = re.compile(r"(?:Федеральн\w*\s+(?:конституционн\w*\s+)?закон\w*|Постановлени\w+|Распоряжени\w+|"
                         r"Указ\w*|Решени\w+)\s+(?:от|Правительства|Президента|Конституционного|Совета)")
NOTE_UNIT_WORD = re.compile(r"\b(стать[яиюей]|глав[аыуе]|раздел[аеу]?|част[ьию]|пункт[аеуом]*|подпункт[аеуом]*)\b",
                            re.IGNORECASE)


def editorial_note_unit(text: str) -> str | None:
    """The unit word an editorial note names (lowercase), or None for any other paragraph."""
    if not text.startswith("(") or len(text) > EDITORIAL_NOTE_MAX or not strip_sup(text).rstrip().endswith(")"):
        return None
    m = EDITORIAL_NOTE.match(text)
    if m:
        return (m.group("unit") or m.group("added") or m.group("applied") or m.group("provisions")).lower()
    if NOTE_SOURCE.search(text):
        w = NOTE_UNIT_WORD.search(text)
        return w.group(1).lower() if w else None
    return None


FORM_REFERENT = re.compile(r"^к\s+(?:акту|форме|заявлению|протоколу|свидетельству|справке|журналу|отчету|отчёту)\s")
