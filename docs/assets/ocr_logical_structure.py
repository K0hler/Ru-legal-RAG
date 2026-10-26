"""M1-04A experiment: logical paragraphs + marker-sequence depth over text-extraction/1.

Prototype only (not a compiler entry point). Three passes:

1. physical: drop page numbers / repeated running headers, keep every token;
2. logical paragraphs: join cross-region / cross-page continuations of the body
   and of footnotes, without touching source text, tokens or locators;
3. structure: caption-driven scopes (approving act -> approved text -> annexes)
   and a beam search over marker sequences that picks depths by sequence
   continuity (idea from 18F regparser.tree.depth), not by local regexes.

Output paths use a neutral syntax shared with the hand-made gold:
``A`` approving act, ``S`` approved text, ``S/AN4`` annex 4,
``S/II/4/в`` subpoint в) of point 4 in section II; named law units use typed
segments: ``A/гл2/ст5/ч1/3`` point 3) of part 1. of article 5 in chapter 2.

Requisites: after the last numbered or named element of a scope, the first short
unterminated requisite line (signer, «Москва, Кремль», date, number, registration,
«Совершено в …», «За …», barcode) opens a requisite block; its paragraphs get kind
``requisite`` with evidence ``requisite_block`` and, with everything after them in the
scope, belong to the scope root. A barcode that is the last body line of its page is
a ``signature`` paragraph of the root (evidence ``barcode``) anywhere in the scope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

VERSION = "ocr-logical-structure/8-experiment"

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


def sup_value(marks: str) -> int:
    return int("".join(SUP_DIGIT[c] for c in marks)) if marks else 0


def strip_sup(text: str) -> str:
    return re.sub(rf"[{SUP}]+", "", text).rstrip()


# --------------------------------------------------------------------------- pass 1


@dataclass
class Region:
    order: int
    page: int
    index: int
    region_id: str
    category: str
    bbox: list
    page_size: list
    raw: str
    text: str
    text_node_ids: list
    role: str = "content"  # content | noise | picture | table
    repeats: int = 0  # running header/footer: regions with exactly the same text
    repeat_index: int = 0  # 0 for the first of those regions in reading order
    row_cell: bool = False  # cycle 10 B3: a right-hand cell of a printed row that starts with a table or long text


ROW_LEFT_TEXT_MIN = 40  # a left cell this long is a row of a card or table, not a signer's title


def mark_row_cells(regions: list[Region]) -> None:
    """Cycle 10 B3: a body region whose printed row (vertical overlap of at least half the lower height) also holds
    a table or a long text («Контроль технического состояния … оборудования» | «Код» | «А/01.4»; «Код оригинала» |
    «Регистрационный номер профессионального стандарта» in a professional standard's card) is a cell of that row:
    its right position is no signature evidence. Page headers/footers are never cells."""
    by_page = defaultdict(list)
    for r in regions:
        by_page[r.page].append(r)
    for page in by_page.values():
        for r in page:
            if r.category in NOISE_CATEGORIES:
                continue
            for q in page:
                if q is r or q.category in NOISE_CATEGORIES:
                    continue
                overlap = min(r.bbox[3], q.bbox[3]) - max(r.bbox[1], q.bbox[1])
                height = min(r.bbox[3] - r.bbox[1], q.bbox[3] - q.bbox[1])
                wide = q.category == "Table" or len(q.text) > ROW_LEFT_TEXT_MIN
                if height > 0 and overlap * 2 >= height and wide:
                    r.row_cell = True
                    break


def load_regions(extraction: dict) -> list[Region]:
    raw = defaultdict(str)
    nodes = defaultdict(list)
    for block in extraction["blocks"]:
        raw[block["source_region_id"]] += block["original_text"]
        nodes[block["source_region_id"]].extend(block["text_node_ids"])
    regions = []
    for page in extraction["pages"]:
        for index, region in enumerate(page["regions"]):
            rid = region["region_id"]
            regions.append(Region(len(regions), page["page"], index, rid, region["category"], region["bbox"],
                                  page["image_size"], raw.get(rid, ""), view(raw.get(rid, "")), nodes.get(rid, [])))
    mark_row_cells(regions)
    running = Counter(re.sub(r"\d+", "#", r.text) for r in regions if r.category in NOISE_CATEGORIES and r.text)
    # Exact repeats (not digit-normalised): «Приложение № 1 …» and «Приложение № 2 …»
    # are different captions, while the same caption on every page is a running header.
    exact = Counter(r.text for r in regions if r.category in NOISE_CATEGORIES and r.text)
    seen: Counter = Counter()
    for r in regions:
        if r.category in NOISE_CATEGORIES and r.text:
            r.repeats = exact[r.text]
            r.repeat_index = seen[r.text]
            seen[r.text] += 1
        if r.category == "Picture":
            r.role = "picture"
        elif r.category == "Table":
            r.role = "table"
        elif r.category in NOISE_CATEGORIES:
            # Running headers/footers are noise only when they carry no caption:
            # a bare page number, or text repeated on three or more pages.
            repeated = (not r.text or re.fullmatch(r"[-–\s]*\d+[-–\s]*", r.text)
                        or running[re.sub(r"\d+", "#", r.text)] >= REPEAT_THRESHOLD)
            if repeated and not is_caption(r.text):
                r.role = "noise"
    return regions


# --------------------------------------------------------------------------- captions and markers


# Case-sensitive capitalised word. «ОДОБРЕН распоряжением …» (an endorsed agreement) only in capitals: the law
# requisite «Одобрен Советом Федерации» is no caption.
APPROVAL = re.compile(r"^(УТВЕРЖДЕН[АЫО]?|Утвержден[аыо]?|ОДОБРЕН[АЫО]?)\b(?:\s|$)")
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
    return bool(APPROVAL.match(text)) or (bool(ANNEX.match(text)) and len(text) <= CAPTION_MAX)


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
    long_allowed = text.startswith("ПРИЛОЖЕНИЕ") or DOCUMENT_REFERENT.match(reference)
    limit = CAPTION_UPPER_MAX if m.group("sign") and long_allowed else CAPTION_BLOCK_MAX
    if len(text) < limit and (p.first.category == "Page-header" or ACT_REFERENT.match(reference)
                              or DOCUMENT_REFERENT.match(reference)):
        return m
    return None


def running_caption(p) -> bool:
    """A later repeat of a caption printed as a running header/footer (same text on three
    or more regions). Controller ruling: the first occurrence still opens the scope."""
    r = p.first
    return r.category in NOISE_CATEGORIES and r.repeats >= REPEAT_THRESHOLD and r.repeat_index > 0


@dataclass
class Marker:
    # roman | decimal | int | paren | letter | dash | none, and named law units:
    # section_named | chapter | paragraph_sign | article
    kind: str = "none"
    value: object = None
    label: str = ""
    # «1.» after a table or an unmarked heading that follows an «N.» of the same scope: the
    # numbering may start again (RESTART_COST) instead of nesting into the last point
    restart: bool = False
    # inserted unit «2¹.», «3²)», «е¹)»: value is the base number, sup the superscript index
    sup: int = 0


# Named law units, recognised only at the start of a paragraph. Hierarchy:
# section (named or Roman) > chapter > paragraph § > article.
# Uppercase «СТАТЬЯ»/«ГЛАВА» as in codes; chapter numbers may carry OCR Cyrillic Х / Ukrainian І.
# «Статья 5¹», «Статья 12.1», and a compound inserted number «Статья 115¹⁻¹» (superscript minus).
ARTICLE = re.compile(r"^(?:Статья|СТАТЬЯ)\s+(\d+(?:[.¹²³⁴⁵⁶⁷⁸⁹][\d⁰¹²³⁴⁵⁶⁷⁸⁹⁻]*)*)\.?(?=\s|$)")
# An inserted chapter/section/§ carries a superscript like an article: «Глава 24¹», «Раздел I¹».
CHAPTER = re.compile(rf"^(?:Глава|ГЛАВА)\s+((?:\d+|[{ROMAN_CHARS}]+)[{SUP}]*)\.?(?=\s|$)")
# «Раздел II.» or uppercase «РАЗДЕЛ I ОБЩИЕ ПОЛОЖЕНИЯ» (codes print it without a dot); the Roman
# number may carry OCR Cyrillic Х / Ukrainian І («РАЗДЕЛ ІХ»).
SECTION_NAMED = re.compile(rf"^(?:Раздел|РАЗДЕЛ)\s+((?:\d+|[{ROMAN_CHARS}]+)[{SUP}]*)\.?(?=\s|$)")
PARAGRAPH_SIGN = re.compile(rf"^§\s*(\d+[{SUP}]*)\.?(?=\s|$)")
# A code's top division «ЧАСТЬ ВТОРАЯ. БЮДЖЕТНАЯ СИСТЕМА …» (uppercase ordinal word; «часть 2 статьи» is a
# reference) and its section subdivision «ПОДРАЗДЕЛ II. ИСКОВОЕ ПРОИЗВОДСТВО».
CODE_PART_ORDINALS = {"ПЕРВАЯ": 1, "ВТОРАЯ": 2, "ТРЕТЬЯ": 3, "ЧЕТВЕРТАЯ": 4, "ЧЕТВЁРТАЯ": 4, "ПЯТАЯ": 5,
                      "ШЕСТАЯ": 6, "СЕДЬМАЯ": 7, "ВОСЬМАЯ": 8, "ДЕВЯТАЯ": 9, "ДЕСЯТАЯ": 10}
CODE_PART = re.compile(rf"^ЧАСТЬ\s+({'|'.join(CODE_PART_ORDINALS)})\.?(?=\s|$)")
SUBSECTION = re.compile(rf"^(?:ПОДРАЗДЕЛ|Подраздел)\s+(\d+|[{ROMAN_CHARS}]+)\.?(?=\s|$)")
UNIT_RANK = {"code_part": -1, "roman": 0, "section_named": 0, "subsection": 0.5, "chapter": 1,
             "paragraph_sign": 2, "article": 3}


def named_unit(text: str, category: str) -> Marker | None:
    """A heading of a named law unit: «Статья 5¹», «Статья 12.1. Название», «Глава 2»,
    «Раздел II», «§ 3». A sentence that starts with such words («Статья 17 закона
    применяется ...») is not a heading: after the number comes nothing, a dot and a
    title, or the paragraph must look like a heading."""
    for kind, pattern in (("article", ARTICLE), ("chapter", CHAPTER),
                          ("section_named", SECTION_NAMED), ("paragraph_sign", PARAGRAPH_SIGN),
                          ("code_part", CODE_PART), ("subsection", SUBSECTION)):
        m = pattern.match(text)
        if not m:
            continue
        rest = text[m.end():].strip()
        if rest and not m.group(0).endswith(".") and not heading_like(text, category):
            return None
        number = m.group(1).rstrip(".")
        if kind == "article":
            return Marker(kind, number, f"ст{number}")
        if kind == "code_part":
            value = CODE_PART_ORDINALS[number]
            return Marker(kind, value, f"разд{value}")
        if kind == "subsection":
            value = int(number) if number.isdigit() else roman_value(number)
            return Marker(kind, value, to_roman(value))
        base, sup = strip_sup(number), number[len(strip_sup(number)):]
        if kind == "paragraph_sign":
            return Marker(kind, int(base), f"§{base}{sup}")
        value = int(base) if base.isdigit() else roman_value(base)
        if kind == "chapter":
            return Marker(kind, value, f"гл{value}{sup}")
        return Marker(kind, value, (f"разд{value}" if base.isdigit() else to_roman(value)) + sup)
    return None


LIST_NUMBER = re.compile(r"^(\d{1,3})([.)])\s+\S")


def leading_zero_list(text: str) -> bool:
    """A marker with a leading zero («01.», «02)», «001.»), as in «Состав работ: 01. …, 02. …» under
    an estimate table, numbers a list line: legal points are never printed that way. It opens no
    unit and the line stays in the current one."""
    m = LIST_NUMBER.match(text)
    return bool(m) and len(m.group(1)) > 1 and m.group(1).startswith("0")


def list_number(text: str) -> tuple[str, int] | None:
    """(delimiter, value) of a «N.» / «N)» marker, for following a zero-padded list past «09.»."""
    m = LIST_NUMBER.match(text)
    return (m.group(2), int(m.group(1))) if m else None


def continues_list(number: tuple[str, int] | None, prev: tuple[str, int, bool] | None) -> bool:
    """«N+1» right after a list line continues the zero-padded list only past a digit rollover
    («10.» after «09.», «100.» after «099.») or once the list has rolled over («11.» after «10.»):
    «5.» after «04.» is the next legal point, since the list would have printed «05.»."""
    if number is None or prev is None or number != (prev[0], prev[1] + 1):
        return False
    return prev[2] or len(str(number[1])) > len(str(prev[1]))


def parse_marker(text: str, category: str) -> Marker:
    named = named_unit(text, category)
    if named is not None:
        return named
    m = re.match(rf"^([{ROMAN_CHARS}]+)\.\s+\S", text)
    if m and roman_value(m.group(1)) and heading_like(text, category):
        v = roman_value(m.group(1))
        return Marker("roman", v, to_roman(v))
    m = re.match(r"^(\d{1,3}(?:\.\d{1,3})+)\.?\s+\S", text)
    if m:
        parts = tuple(int(p) for p in m.group(1).split("."))
        return Marker("decimal", parts, ".".join(map(str, parts)))
    if re.match(r"^\d{1,2}\.\s?\d{1,2}\.\s?\d{4}\b", text):
        return Marker("none")  # a date such as "12. 02. 2026", not point 12
    if leading_zero_list(text):
        return Marker("none")  # «01. …», «02) …»: a list line of the current unit, not a point
    # An inserted unit carries a superscript after its number: «2¹.», «3²)», «е¹)».
    m = re.match(rf"^(\d{{1,3}})([{SUP}]*)\.\s+\S", text)
    if m:
        return Marker("int", int(m.group(1)), m.group(1) + m.group(2), sup=sup_value(m.group(2)))
    m = re.match(rf"^(\d{{1,3}})([{SUP}]*)\)\s+\S", text)
    if m:
        return Marker("paren", int(m.group(1)), m.group(1) + m.group(2), sup=sup_value(m.group(2)))
    m = re.match(rf"^([а-я])([{SUP}]*)\)\s+\S", text)
    if m and m.group(1) in LETTERS:
        return Marker("letter", LETTERS.index(m.group(1)) + 1, m.group(1) + m.group(2), sup=sup_value(m.group(2)))
    if re.match(r"^[-–—]\s+\S", text):
        return Marker("dash")
    return Marker("none")


ROMAN_START = re.compile(rf"^([{ROMAN_CHARS}]+)\.\s+[А-ЯЁA-Z]")
# Guard of next_roman_section: a section heading OCR gave a body category may be long (590 characters in
# development: a heading listing who approves what) but stays one unterminated phrase.
ROMAN_TEXT_MAX = 1000


def next_roman_section(text: str, romans: set[int]) -> int | None:
    """Review Focus 3: a section heading that OCR gave a body category and that is too long or otherwise
    does not look like a heading («V. Согласование проекта …», category Text, 590 characters). «V.» at
    the start of the paragraph, followed by a capitalised word, opens section V only when sections I to
    V-1 are already open in the same scope; a Roman number inside a sentence never matches. Guard: at most
    ``ROMAN_TEXT_MAX`` characters and not ending like a sentence or a list item («.», «;», «:», «!», «?», «,»;
    the endings ``heading_like`` rejects, plus the comma), so a numbered «V. …» of running text stays text."""
    if len(text) > ROMAN_TEXT_MAX or strip_sup(text).rstrip(" »\")").endswith(tuple(TERMINAL + ",")):
        return None
    m = ROMAN_START.match(text)
    value = roman_value(m.group(1)) if m else None
    if value is None or value < 2 or not all(v in romans for v in range(1, value)) or max(romans) != value - 1:
        return None
    return value


ROMAN_SEQUENCE_EVIDENCE = {"roman_sequence": "«N.» after sections I to N-1 of the scope opens section N"}


def roman_sequence(items: list[Paragraph], rows: set[int]) -> None:
    """Applies ``next_roman_section`` in reading order after the table rows of the scope are known (cycle 6,
    v4 §4.7): rubrics «I.», «II.» demoted to table rows are no sections of the sequence, and a row is never
    promoted. An unmarked «V. …» that follows an unterminated text paragraph (no table or heading between)
    continues that sentence («… в соответствии с разделом» / «V. Порядка …») and opens nothing."""
    romans: set[int] = set()  # Roman sections seen in the scope
    previous = None  # the previous body item (pictures skipped)
    for p in items:
        if p.flow != "body" or p.kind == "picture":
            continue
        if p.kind in {"text", "heading"} and id(p) not in rows:
            open_sentence = previous is not None and previous.kind == "text" and not terminated(previous.text)
            if p.marker.kind == "none" and romans and not open_sentence:
                roman = next_roman_section(p.text, romans)
                if roman is not None:
                    p.marker = Marker("roman", roman, to_roman(roman))
                    p.kind = "heading"
                    p.evidence.append(dict(ROMAN_SEQUENCE_EVIDENCE))
            if p.marker.kind == "roman":
                romans.add(p.marker.value)
        previous = p


def heading_like(text: str, category: str) -> bool:
    return category in {"Section-header", "Title"} or (len(text) < 250 and not text.rstrip().endswith((".", ";", ":")))


def terminated(text: str) -> bool:
    t = strip_sup(text).rstrip(" »\")")
    return bool(t) and t[-1] in TERMINAL


def starts_continuation(text: str) -> bool:
    """A lowercase or «(» start continues the previous paragraph, except a standalone editorial note of a
    consolidated edition («(Статья в редакции …)» at the top of a page is no continuation)."""
    return bool(text) and (text[0].islower() or (text[0] == "(" and not editorial_note_unit(text)))


def footnote_number(text: str) -> int | None:
    m = re.match(rf"^([{SUP}]+)", text)
    return int("".join(SUP_DIGIT[c] for c in m.group(1))) if m else None


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
    re.compile(r"^Совершено\s+в\b"),  # closing formula of an agreement
    re.compile(r"^[_\-–—\s]{3,}$"),  # a closing rule line
)
# signer title or agreement signature place («За Правительство ...», «От Правительства ...»): a short
# unterminated line; «От Сторон» names both parties, not one signature place
SIGNER = re.compile(r"^(?:(?:Президент|Председатель|Заместитель Председателя|Первый заместитель|Руководитель|Министр"
                    r"|Временно исполняющий обязанности|Главный государственный санитарный врач)\b"
                    r"|(?:За|От)\s+(?!Сторон(?![а-яё]))[А-ЯЁ][а-яё]+)")
# the heading of an agreement's signature block: «Подписи и реквизиты Сторон», «Адреса и реквизиты сторон»
SIGNATURE_HEADING = re.compile(r"^(?:(?:юридические\s+)?адреса|подписи|(?:банковские\s+)?реквизиты)"
                               r"(?:,?\s+(?:и\s+)?(?:(?:юридические\s+)?адреса|подписи|(?:банковские\s+)?реквизиты))*"
                               r"\s+сторон$", re.IGNORECASE)
INITIALS = r"[А-ЯЁ]\.\s?(?:[А-ЯЁ]\.\s?)?[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?"
# the signature heading of a form: «Подписи членов рабочей комиссии:», «Подпись руководителя:» (a few words, a colon)
FORM_SIGNATURE_HEADING = re.compile(r"^Подпис[иь](?:\s+[а-яё]+){1,5}:$")


PAGE_MARK = re.compile(r"[\w-]+(?:\.[\w-]+)*\.(?:docx?|rtf|odt)", re.IGNORECASE)
# Cycle 10 B1: a typist's mark «Компьютер /Н.Н./При-К7552-3», «21.08.2024 15:44 kompburo /Н.И./П-К7552»: a word,
# initials between slashes and a job code; OCR reads the word differently on every page, so it is not running noise.
PRINT_MARK = re.compile(r"^(?:[\d.:\s]+)?[\w.]+\s*/\s*[А-ЯЁA-Z]\.\s?(?:[А-ЯЁA-Z]\.)?\s*/\s*[\w.-]*$")
PAGE_MARK_EVIDENCE = {"page_mark": "file name printed in a page header/footer"}
BARCODE_EVIDENCE = {"barcode": "last body line on its page"}


def page_mark(region: Region) -> bool:
    """A service file code printed in a page header/footer («200716A9.doc») or a typist's mark
    («Компьютер /Н.Н./При-К7552-3»), not repeated often enough to be running noise: a mark of the page,
    never text of the unit it happens to follow."""
    return region.category in NOISE_CATEGORIES and bool(PAGE_MARK.fullmatch(region.text) or PRINT_MARK.match(region.text))


def barcode_like(text: str) -> bool:
    """A printed barcode number: one run of 12-14 digits or EAN-13 grouping «2 100039 06204 3»."""
    return bool(re.fullmatch(r"\d{12,14}|\d\s\d{6}\s\d{5}\s\d", text))


def requisite_like(text: str) -> bool:
    """A requisite line of a signature block: signer title (optionally with initials and
    surname), initials and surname, «Москва, Кремль»/«Москва», date, number, registration
    mark, agreement closing formula, signature heading («Подписи и реквизиты Сторон») and signature
    places («За …», «От …»), barcode. Text-only."""
    if barcode_like(text) or any(p.match(text) for p in REQUISITE_LINES) or re.fullmatch(INITIALS, text):
        return True
    if SIGNATURE_HEADING.match(text) or FORM_SIGNATURE_HEADING.match(text):
        return True
    return bool(SIGNER.match(text)) and len(text) < 120 and not terminated(text)


# A footnote marked by asterisks instead of a number: «*- с точностью до 10 см;», «** …».
ASTERISK_NOTE = re.compile(r"^(\*{1,3})(?!\*)\s*[-–—]?\s*\S")
# OCR markdown emphasis («*курсив*», «**Примечание**»): a balanced pair inside one line and one table cell.
EMPHASIS = re.compile(r"(?<!\*)(\*{1,3})(?=[^\s*])([^*\n<>]+?)(?<=\S)\1(?!\*)")


def strip_emphasis(text: str) -> str:
    """Text without balanced markdown emphasis pairs, so they are not read as asterisk footnote marks."""
    return EMPHASIS.sub(r"\2", text)


# A numbered fill-in line of a form: the marker and only a blank («2. __________», «3) .......»).
FILL_IN = re.compile(r"^\d{1,3}[.)]\s*(?=[_.…])[_.…\s]{3,}$")
FILL_IN_EVIDENCE = {"fill_in_line": "after a numbered fill-in line of a form: its parent (the line holds no text)"}


def fill_in_line(text: str) -> bool:
    return bool(FILL_IN.match(text.strip()))


# --------------------------------------------------------------------------- pass 2


@dataclass
class Paragraph:
    flow: str  # body | footnote
    regions: list = field(default_factory=list)
    marker: Marker = field(default_factory=Marker)
    kind: str = "text"  # text | heading | approval | annex | table | signature | requisite | footnote | picture
    footnote: int | None = None
    owner: str | None = None
    evidence: list = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(r.text for r in self.regions)

    @property
    def first(self) -> Region:
        return self.regions[0]


def logical_paragraphs(regions: list[Region]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    open_body: Paragraph | None = None
    open_note: Paragraph | None = None
    by_page = defaultdict(list)
    for r in regions:
        if r.role == "content":
            by_page[r.page].append(r)
    for r in regions:
        if r.role == "noise":
            continue
        if r.role in {"picture", "table"}:
            paragraphs.append(Paragraph("body", [r], kind=r.role))
            continue
        page_content = by_page[r.page]
        first_on_page = page_content and page_content[0] is r
        if r.category == "Footnote" or footnote_number(r.text) is not None:
            number = footnote_number(r.text)
            if number is None and open_note and open_note.first.page < r.page and not terminated(open_note.text):
                open_note.regions.append(r)
                open_note.evidence.append({"join": "unnumbered_footnote_after_page_break", "region": r.region_id})
                continue
            p = Paragraph("footnote", [r], kind="footnote", footnote=number)
            paragraphs.append(p)
            open_note = p
            continue
        # Body text. Join a continuation only with an unterminated open paragraph
        # across a page break, never on the same page (OCR keeps those together).
        if starts_continuation(r.text) and parse_marker(r.text, r.category).kind == "none":
            # A footnote continued on the next page, mislabelled as Text: it sits
            # after the page body, directly before the page's footnotes (or at the end),
            # the previous page's last footnote is unterminated, and it cannot be a
            # body continuation because body continuations open the page.
            later = [x for x in page_content if x.order > r.order]
            before_notes = all(x.category == "Footnote" for x in later)
            body_open_here = open_body is not None and open_body.regions[-1].page == r.page and not terminated(open_body.text)
            if (open_note is not None and open_note.regions[-1].page == r.page - 1 and not terminated(open_note.text)
                    and not first_on_page and before_notes and (r.text[0] == "(" or body_open_here)):
                open_note.regions.append(r)
                open_note.evidence.append({"join": "footnote_continuation_after_page_break", "region": r.region_id})
                continue
            if open_body and open_body.regions[-1].page < r.page and first_on_page and not terminated(open_body.text):
                open_body.regions.append(r)
                open_body.evidence.append({"join": "body_continuation_after_page_break", "region": r.region_id})
                continue
        p = Paragraph("body", [r])
        paragraphs.append(p)
        if page_mark(r):
            # a file code in the footer belongs to the scope root and never opens a continuation
            p.evidence.append(dict(PAGE_MARK_EVIDENCE))
            continue
        body_here = [x for x in page_content if x.category != "Footnote" and footnote_number(x.text) is None]
        if barcode_like(r.text) and body_here and body_here[-1] is r:
            # a barcode as the last body line of its page is a page requisite, not open text:
            # the next page continues the paragraph before it
            p.evidence.append(dict(BARCODE_EVIDENCE))
            continue
        open_body = p
    return paragraphs


# --------------------------------------------------------------------------- pass 3


def next_letter_ok(prev: int, new: int) -> bool:
    return new == prev + 1


SUBPOINT_KINDS = {"paren", "letter"}  # «1)» / «а)» subpoints
POINT_KINDS = {"int", "decimal"}  # «N.» / «N.M» points
ABANDON_ARTICLE = 0.5  # a point that leaves an open article without a new heading
RESTART_COST = 1.0  # «1.» restarting a numbering at the level of «N.» (below the unexplained-nesting 10.0)


def label_under(marker: Marker, parent: tuple | None, article_parts: bool = True) -> str:
    """An ``int`` marker «1.» directly inside an article.

    Controller ruling (M1-04A cycle 2): in the act's own text (scope ``A``: laws and
    codes) it is a part ``ч<n>``; inside an attached document (``S``, ``S2``, annexes
    ``S/AN…``/``A/AN…``: agreements, treaties) it is a plain point number, because such
    documents cite themselves as «пункт 1 статьи 1 Соглашения»."""
    if marker.kind == "int" and article_parts and parent is not None and parent[0] == "article":
        return f"ч{marker.label}"
    return marker.label


def abandons_article(stack: tuple, keep: int) -> bool:
    return any(entry[0] == "article" for entry in stack[keep:])


def transitions(stack: tuple, marker: Marker, last_int: int | None, article_parts: bool = True):
    """Yield (new_stack, cost) for one marker. Stack items: (kind, value, label)."""
    for new_stack, cost in _transitions(stack, marker, last_int, article_parts):
        # Explicit preference instead of an order-dependent tie: only a named heading may
        # close an open article; a point that drops it pays ABANDON_ARTICLE.
        keep = len(new_stack) - 1
        if marker.kind not in UNIT_RANK and abandons_article(stack, keep):
            cost += ABANDON_ARTICLE
        yield new_stack, cost


def _transitions(stack: tuple, marker: Marker, last_int: int | None, article_parts: bool):
    depth = len(stack)
    if marker.kind in UNIT_RANK and marker.kind != "roman":
        # A named unit heading is explicit: it closes every open unit of the same
        # or lower rank (and all points) and nests under the nearest higher unit.
        rank = UNIT_RANK[marker.kind]
        keep = depth
        while keep and not (stack[keep - 1][0] in UNIT_RANK and UNIT_RANK[stack[keep - 1][0]] < rank):
            keep -= 1
        yield stack[:keep] + ((marker.kind, marker.value, marker.label),), 0.0
        return
    for keep in range(depth, -1, -1):  # keep = number of stack entries retained below the new one
        parent = stack[keep - 1] if keep else None
        sibling = stack[keep] if keep < depth else None
        item = (marker.kind, marker.value, label_under(marker, parent, article_parts))
        if sibling is not None:
            # continue the sequence at this level
            if sibling[0] == marker.kind:
                if marker.kind in {"int", "paren", "letter", "roman"}:
                    gap = marker.value - sibling[1]
                    if gap == 1 or (gap == 0 and marker.sup):
                        # «2¹» after «2» or «2¹»: an inserted sibling; the stack keeps the base value,
                        # so «3» follows it as usual
                        yield stack[:keep] + (item,), 0.0 + 0.01 * (depth - keep)
                    elif 1 < gap <= 3:
                        yield stack[:keep] + (item,), 2.0 + gap
                    elif (marker.restart and marker.kind in {"int", "paren", "letter"} and marker.value == 1
                          and sibling[1] > 1):
                        # numbering started again after a table/heading («N.») or after a sentence that
                        # closed the list («N)»/«а)»): the level of the last item, not inside it
                        yield stack[:keep] + (item,), RESTART_COST + 0.01 * (depth - keep)
                elif marker.kind == "decimal":
                    a, b = sibling[1], marker.value
                    if len(a) == len(b) and a[:-1] == b[:-1] and b[-1] == a[-1] + 1:
                        yield stack[:keep] + (item,), 0.0 + 0.01 * (depth - keep)
                    elif len(a) == len(b) and a[:-1] == b[:-1] and 1 < b[-1] - a[-1] <= 3:
                        # a skipped number («5.3» after «5.1»): the parent of «N.M» is «N.» by its prefix,
                        # so «5.3» is a sibling of «5.1», not its subpoint (the gap costs as for «N.»)
                        yield stack[:keep] + (item,), 2.0 + b[-1] - a[-1]
                    elif len(a) == len(b) and a[:-1] != b[:-1] and b[-1] == 1:
                        yield stack[:keep] + (item,), 1.5  # e.g. 2.4 -> 3.1 under a flat section
            if not (marker.kind == "decimal" and sibling[0] in SUBPOINT_KINDS):
                continue
            # a dotted «8.1» closes an open «4)» / «б)» subpoint and opens under the point
        # open a new child level under `parent`
        if marker.kind == "roman":
            if parent is None:
                yield (item,), 0.0 if marker.value == 1 else 1.0
            continue
        if parent is not None and parent[0] == marker.kind and marker.kind != "decimal":
            continue  # same type nested in itself is implausible
        if marker.kind in {"paren", "letter"}:
            if marker.value == 1:
                yield stack[:keep] + (item,), 0.5 if parent is None or parent[0] == "roman" else 0.0
        elif marker.kind == "int":
            if parent is not None and parent[0] == "article":
                yield stack[:keep] + (item,), 0.0 if marker.value == 1 else 3.0
            elif parent is None or parent[0] == "roman":
                if marker.value == 1 or (last_int is not None and marker.value == last_int + 1):
                    yield stack[:keep] + (item,), 0.0
                elif last_int is None:
                    yield stack[:keep] + (item,), 3.0
        elif marker.kind == "decimal":
            v = marker.value
            child_of_decimal = parent is not None and parent[0] == "decimal" and v[:-1] == parent[1] and v[-1] == 1
            child_of_int = parent is not None and parent[0] == "int" and len(v) == 2 and v[0] == parent[1] and v[1] == 1
            if child_of_decimal or child_of_int:
                yield stack[:keep] + (item,), 0.0
            elif (parent is None or parent[0] == "roman") and len(v) == 2 and v[1] == 1:
                matches = parent is not None and parent[1] == v[0]
                yield stack[:keep] + (item,), 0.0 if matches else 1.0
            elif (parent is None or parent[0] == "roman") and len(v) == 2:
                yield stack[:keep] + (item,), 4.0


def solve_depths(markers: list[Marker], beam: int = 64, article_parts: bool = True) -> list[tuple]:
    """Beam search over the whole marker sequence of one scope; returns stacks."""
    states = [(0.0, (), None, [])]  # cost, stack, last_int, history
    for marker in markers:
        if marker.kind in {"none", "dash"}:
            states = [(c, s, li, h + [s]) for c, s, li, h in states]
            continue
        nxt = []
        for cost, stack, last_int, hist in states:
            options = list(transitions(stack, marker, last_int, article_parts))
            if not options:
                options = [(stack + ((marker.kind, marker.value, marker.label),), 10.0)]  # unexplained: deep penalty
            for new_stack, c in options:
                li = marker.value if marker.kind == "int" and len(new_stack) and new_stack[-1][0] == "int" and \
                    (len(new_stack) == 1 or new_stack[-2][0] == "roman") else last_int
                nxt.append((cost + c, new_stack, li, hist + [new_stack]))
        nxt.sort(key=lambda s: s[0])
        seen, states = set(), []
        for s in nxt:
            if s[1] not in seen:
                seen.add(s[1])
                states.append(s)
            if len(states) >= beam:
                break
    return states[0][3]


SUBHEADING_MAX = 200  # a subheading printed as body text
SUBHEADING_HEADER_MAX = 500  # with OCR heading evidence (Section-header/Title): regulations print ~450
SUBHEADING_CORROBORATION = 2  # body-text subheadings need this many header-category ones in the scope
HEADING_CATEGORIES = {"Section-header", "Title"}
# A figure/table/form caption by its text: «Схема 2», «Рисунок 1 - Знак …», «Рис. 3», «Таблица 3», «Форма N 2».
FIGURE_CAPTION = re.compile(r"^(?:Схема|Рисунок|Рис\.|Таблица|Форма|Диаграмма|График)\s*(?:№|N)?\s*\d")
# A labelled value line: «Адрес: …», «Почтовый адрес: …», «Телефон: …».
LABEL_LINE = re.compile(r"^\S+(?:\s\S+)?:\s")


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


def heading_evidence(p: Paragraph) -> bool:
    return p.first.category in HEADING_CATEGORIES


def subheading_candidate(p: Paragraph) -> bool:
    """An unmarked capitalised line that is not a sentence: no final «.;:!?», no broken tail («,»,
    hyphen). Not a figure/table/form caption (OCR category Caption or the text «Схема 1», «Рисунок
    1 - …», «Таблица 2», «Форма N 3»), a labelled value («Адрес: …»), a requisite or signature line,
    or a rejected annex caption («Приложение 2»). At most SUBHEADING_MAX characters as body text,
    SUBHEADING_HEADER_MAX with OCR heading evidence (Section-header/Title)."""
    text = p.text
    limit = SUBHEADING_HEADER_MAX if heading_evidence(p) else SUBHEADING_MAX
    return (p.kind == "text" and p.marker.kind == "none" and p.first.category != "Caption"
            and bool(text) and text[0].isupper()
            and len(text) <= limit and not terminated(text) and final_char(text) not in ",-–—"
            and not FIGURE_CAPTION.match(text) and not LABEL_LINE.match(text)
            and not requisite_like(text) and not signature_like(p.first) and not is_caption(text)
            and not is_project_caption(text))


def subheading_stacks(items: list[Paragraph], body: list[Paragraph], stacks: list[tuple]) -> set[int]:
    """Review Focus 5: unnumbered subheadings inside a section. A run of subheading candidates that
    follows a finished body paragraph (final «.» or «;») and is immediately followed by a numbered
    point («N.» or «N.M», no table, picture or caption in between) belongs to that point's parent
    when the parent is a section or another named unit («II.», «Раздел 2», «Глава 3»): the
    enclosing section, not the previous point or subpoint. Without an enclosing section (points
    directly in the scope root) such a line stays with the open point: there it is as likely a
    sentence cut by OCR. A run printed as body text (no Section-header/Title region) also needs
    corroboration: at least SUBHEADING_CORROBORATION such runs with heading evidence in the same
    scope (the document's subheading style); otherwise an OCR-cut sentence would qualify.
    Returns the changed body indices."""
    index = {id(p): k for k, p in enumerate(body)}
    seq = [p for p in items if p.flow == "body"]  # a table or picture in between blocks the rule
    runs = []  # (run paragraphs, parent stack)
    k = 0
    while k < len(seq):
        if id(seq[k]) not in index or not subheading_candidate(seq[k]):
            k += 1
            continue
        end = k
        while end + 1 < len(seq) and id(seq[end + 1]) in index and subheading_candidate(seq[end + 1]):
            end += 1
        prev = seq[k - 1] if k else None
        nxt = seq[end + 1] if end + 1 < len(seq) else None
        if (prev is not None and id(prev) in index and final_char(prev.text) in ".;"
                and nxt is not None and id(nxt) in index and nxt.marker.kind in POINT_KINDS):
            parent = stacks[index[id(nxt)]][:-1]
            if parent and parent[-1][0] in UNIT_RANK:
                runs.append((seq[k:end + 1], parent))
        k = end + 1
    styled = sum(any(heading_evidence(q) for q in run) for run, _ in runs) >= SUBHEADING_CORROBORATION
    changed: set[int] = set()
    for run, parent in runs:
        if not styled and not any(heading_evidence(q) for q in run):
            continue
        for q in run:
            j = index[id(q)]
            if stacks[j][:len(parent)] == parent:
                stacks[j] = parent
                changed.add(j)
                q.evidence.append({"subheading": "unmarked line before a numbered point -> its parent"})
    return changed


def quote_balance(text: str) -> int:
    return text.count("«") - text.count("»")


def continues_level(nxt: tuple, stack: tuple, level: int) -> bool:
    """The next marked paragraph stays in the list at ``level`` of ``stack`` (same parent, same kind,
    not a restarted numbering: a lower value there is a new list)."""
    return (len(nxt) > level and nxt[:level] == stack[:level] and nxt[level][0] == stack[level][0]
            and not (nxt[level][1] < stack[level][1] and isinstance(nxt[level][1], int)))


def close_subpoints(body: list[Paragraph], stacks: list[tuple], keep: set[int]) -> None:
    """A paragraph after the last subpoint returns to the point. An unmarked paragraph inside a
    «1)» / «а)» subpoint closes it when it starts with a capital letter and does not continue the
    enumeration: the previous paragraph ended with «.», or it ended with «;» and this paragraph is
    a sentence of its own (final «.»). Only list levels that the next marked paragraph does not
    continue are closed; later unmarked paragraphs up to the next marker follow the point. A
    lowercase start, a «;» item, text after «:» or a list that goes on stay in the subpoint. Nothing
    closes inside a quotation: while a «…» opened in the subpoint (from its marked paragraph on) is
    unbalanced, or when the paragraph itself ends a quotation («…».» / «…»»), as in amending text
    («а) пункт 3 изложить в следующей редакции: «3. …»»)."""
    closed = None
    opened = 0  # quotation balance since the last marked paragraph
    for k, p in enumerate(body):
        if p.marker.kind not in {"none", "dash"}:
            closed = None
            opened = quote_balance(p.text)
            continue
        inside_quote = opened > 0
        opened += quote_balance(p.text)
        if k in keep or p.kind != "text":
            continue
        if closed is not None:
            stacks[k] = closed
            continue
        stack = stacks[k]
        if not k or not stack or stack[-1][0] not in SUBPOINT_KINDS or not p.text[:1].isupper():
            continue
        if inside_quote or strip_sup(p.text).rstrip(" .").endswith("»") or any("quoted" in e for e in p.evidence):
            continue  # cycle 9 B4: a quoted heading («Статья 11.» inside the quotation) closes nothing
        j = k - 1  # the previous provision text; a standalone editorial note in between does not count
        while j > 0 and editorial_only(body[j]):
            j -= 1
        before, own = provision_final(body[j].text), provision_final(p.text)
        if not (before == "." or (before == ";" and own == ".")):
            continue
        nxt = next((stacks[j] for j in range(k + 1, len(body)) if body[j].marker.kind not in {"none", "dash"}), ())
        depth = len(stack)
        while depth and stack[depth - 1][0] in SUBPOINT_KINDS and not continues_level(nxt, stack, depth - 1):
            depth -= 1
        if depth < len(stack):
            closed = stacks[k] = stack[:depth]
            p.evidence.append({"subpoint_closed": "capitalised paragraph after the last subpoint -> the point"})


# An editorial note of a consolidated edition names the unit it is about: «(Статья в редакции …)»,
# «(Часть 2 утратила силу …)», «(Дополнение пунктом - …)», «(Особенности применения статьи 3 - …)».
EDITORIAL_NOTE = re.compile(
    r"^\((?:(?P<unit>Статья|Глава|Раздел|Часть|Пункт|Подпункт)\s+(?:\S+\s+)?"
    r"(?:в\s+редакции|утратил|утратила|утратило|исключен|признан)"
    r"|Дополнен(?:ие|а|о|ы)?\s+(?P<added>статьей|главой|разделом|частью|пунктом|подпунктом)"
    r"|Особенности\s+применения\s+(?P<applied>статьи|главы|раздела|части|пункта|подпункта)"
    r"|Положения\s+(?P<provisions>статьи|главы|раздела|части|пункта|подпункта)\s)")
EDITORIAL_NOTE_MAX = 400
NOTE_UNIT = {"стат": "article", "глав": "chapter", "разд": "section", "част": "part", "пунк": "point",
             "подп": "subpoint"}


def note_unit_level(stack: tuple, unit: str) -> int | None:
    """Index of the deepest open entry of the named kind, or None. A part is «N.» right under an
    article; a point is «N.»/«N.M»/«N)» that is not a part; a subpoint is «а)»/«N)» under a point."""
    for i in range(len(stack) - 1, -1, -1):
        kind, parent = stack[i][0], stack[i - 1][0] if i else None
        part = kind == "int" and parent == "article"
        if ((unit == "article" and kind == "article") or (unit == "chapter" and kind == "chapter")
                or (unit == "section" and kind in {"section_named", "roman"}) or (unit == "part" and part)
                or (unit == "point" and kind in {"int", "decimal", "paren"} and not part)
                or (unit == "subpoint" and kind in {"letter", "paren"} and parent in {"int", "decimal", "paren"})):
            return i
    return None


ARTICLE_POINT_REFERENCE = re.compile(r"\bпункт\w*\s+\d+[^\s]*\s+настоящей\s+статьи")
ARTICLE_PART_REFERENCE = re.compile(r"\bчаст\w*\s+\d+[^\s]*\s+настоящей\s+статьи")


def points_are_article_parts(texts: list[str]) -> bool:
    """The act calls «N.» inside an article a «пункт» (Budget and Tax Codes: «пункт 3 настоящей статьи»)
    rather than a «часть» (Labour Code, most laws): its notes «(Дополнение пунктом …)» then name «N.» and
    «подпункт» names «N)»."""
    joined = " ".join(texts)
    return len(ARTICLE_POINT_REFERENCE.findall(joined)) > len(ARTICLE_PART_REFERENCE.findall(joined))


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


def editorial_note_owners(body: list[Paragraph], stacks: list[tuple], points_are_parts: bool = False) -> None:
    """An editorial note that names its unit belongs to the deepest open unit of that kind, not to the
    last point or subpoint it follows. A note naming no open unit of its kind keeps its owner. In an act
    whose «N.» in an article is a «пункт», «пункт» names that part and «подпункт» its «N)»."""
    for k, p in enumerate(body):
        if p.kind != "text" or p.marker.kind != "none":
            continue
        word = editorial_note_unit(p.text)
        if word is None:
            continue
        unit = NOTE_UNIT[word[:4]]
        if points_are_parts and unit in {"point", "subpoint"} and any(e[0] == "article" for e in stacks[k]):
            unit = "part" if unit == "point" else "point"
        level = note_unit_level(stacks[k], unit)
        if level is not None and level + 1 < len(stacks[k]):
            stacks[k] = stacks[k][:level + 1]
            p.evidence.append({"editorial_note": f"names the {unit} -> that unit"})


# Cycle 9 B2: a code's article note «Примечание. Положение части 3 …» / «Примечания:» followed by «1. …», «2¹. …».
ARTICLE_NOTE = re.compile(r"^Примечани[ея](?:\s*[.:]|$)")


def article_notes(body: list[Paragraph], stacks: list[tuple]) -> None:
    """A note «Примечание. …» or «Примечания:» after the parts of an article belongs to the article, not to
    its last part; so do the numbered notes «N.» under it and editorial notes after them, up to the next named
    unit or any other marker. Outside an article a note keeps its owner, and so does a note under a point «5)» of
    an article (an amending law quoting a new article with its note)."""
    note = None  # the article's stack while inside its note block
    for k, p in enumerate(body):
        if note is not None and p.marker.kind not in {"none", "int"}:
            note = None
        if note is None and p.kind == "text" and p.marker.kind == "none" and ARTICLE_NOTE.match(p.text):
            level = next((i for i, e in enumerate(stacks[k]) if e[0] == "article"), None)
            below = stacks[k][level + 1:level + 2] if level is not None else ()
            if level is not None and all(e[2].startswith("ч") for e in below):
                note = stacks[k][:level + 1]
                p.evidence.append({"article_note": "note block of the article"})
        if note is not None:
            stacks[k] = note


# Amending text quotes the new wording over several paragraphs: «… изложить в следующей редакции:» then
# «"5²) …» … «12) …";» (or «…»). Inside such a quotation numbers and headings are quoted text.
QUOTE_OPEN = re.compile(r"^[«\"„“]")
QUOTE_CLOSE = re.compile(r"[»\"“”][.;,)]*$")
QUOTE_MAX_PARAGRAPHS = 300  # an OCR-lost closing quote must not swallow the rest of the document


FORM_LINE = re.compile(r"_{5,}")


def unbalanced_quotes(text: str) -> int:
    """+1 when the paragraph leaves a quotation open, -1 when it closes one opened before, 0 when its own
    quote marks pair up (a quoted name or term inside a quotation). Straight quotes pair by parity; «…»
    and „…“ by count, the sign of the surplus deciding."""
    straight = text.count('"')
    angled = text.count("«") + text.count("„") - text.count("»") - text.count("“")
    if angled:
        return 1 if angled > 0 else -1
    if straight % 2:
        return 1 if QUOTE_OPEN.match(text) else -1
    return 0


def marker_number(marker: Marker) -> int | None:
    """The plain integer of a marker («5)», «3.», «Статья 11»); None for letters, «1.1» or «25¹⁷»."""
    if isinstance(marker.value, int):
        return marker.value
    plain = isinstance(marker.value, str) and re.fullmatch(r"[0-9]+", marker.value) and not marker.sup
    return int(marker.value) if plain else None


def quoted_markers(items: list[Paragraph]) -> None:
    """Paragraphs after the first one of a multi-paragraph amending quotation keep no marker: «48³¹)»,
    «1.», «Статья 5» there are quoted text of the unit that introduces the quotation. The quotation opens
    with a paragraph that starts with a quote mark right after a paragraph ending with «:» and does not
    end with a closing quote itself; it ends with the first paragraph ending with a quote mark (optionally
    followed by «.;,)»). Counting «…» balance is not used: OCR merges or drops nested closing quotes. The
    next number of the introducing list («д)» after «г)») ends an open quotation; after a quoted form
    or table (where the closing quote is often lost) so does the next number of any list open before
    the quotation («2.» after «1.»). A number that goes on the quotation's own list («6)» after a quoted «5)»)
    never ends it. A heading inside the quotation («Статья 11.») is quoted text too; the act's own next article
    or chapter heading ends the quotation."""
    open_from, last, previous = None, {}, None  # last: marker kind -> value seen outside quotations
    introducer, formish = None, False
    inner = {}  # marker kind -> value of the quotation's own numbered lines
    for p in items:
        if p.flow != "body":
            continue
        heading = p.kind == "heading"
        if p.kind != "text" and not heading:
            formish = formish or open_from is not None
            continue
        if heading and open_from is None:
            if marker_number(p.marker) is not None:
                last[p.marker.kind] = marker_number(p.marker)  # the act's own articles and chapters
            previous = p
            continue
        text = strip_sup(p.text).rstrip() if p.text else ""
        if open_from is not None:
            formish = formish or bool(FORM_LINE.search(p.text or ""))
            number = marker_number(p.marker)
            continues = isinstance(last.get(p.marker.kind), int) and number == last[p.marker.kind] + 1
            # Cycle 9 B3: «6)» right after the quotation's own «5)» goes on the quoted list, even when the
            # introducing point is «5)» too
            own = isinstance(inner.get(p.marker.kind), int) and number == inner[p.marker.kind] + 1
            # Cycle 9 B4: a heading inside the quotation is quoted («Статья 11.» after a quoted «Статья 10.»)
            # unless it is the act's own next article or chapter («Статья 2» after «Статья 1»)
            nxt = continues and not own and (formish or heading
                                             or (introducer is not None and p.marker.kind == introducer.kind))
            if nxt or open_from > QUOTE_MAX_PARAGRAPHS:
                open_from = None
            else:
                open_from += 1
                if p.marker.kind not in {"none", "dash"}:
                    inner[p.marker.kind] = number
                if p.marker.kind != "none":
                    p.marker = Marker("none")
                    p.kind = "text"
                    p.evidence.append({"quoted": "inside an amending quotation; text of the introducing unit"})
                if QUOTE_CLOSE.search(text) and unbalanced_quotes(text) < 0:
                    open_from = None
                previous = p
                continue
        if (QUOTE_OPEN.match(p.text or "") and previous is not None and final_char(previous.text) == ":"
                and unbalanced_quotes(text) > 0 and not QUOTE_CLOSE.search(text)):
            open_from, formish, inner = 0, False, {}
        if p.marker.kind not in {"none", "dash"}:
            last[p.marker.kind] = p.marker.value
            introducer = p.marker
        previous = p


def mark_restarts(items: list[Paragraph]) -> None:
    """Restarted numbering: an «1.» whose previous «N.» paragraph in the scope is separated from it
    by a table or an unmarked heading (OCR Section-header/Title) may restart the numbering at the
    level of that «N.» (the solver checks N > 1 at that level). Without such a break, or for «1)»/
    «а)» subpoints and «1.1», nothing changes."""
    broken = False
    last = None  # value of the previous «N.» in the scope
    # A «1)»/«а)» list closed by a sentence of its own: after the last item ended with «.», an unmarked
    # paragraph starting with a capital letter (outside a quotation) ends the list, so a later «1)»/«а)»
    # starts a new list at the level of the old one instead of nesting into its last item.
    last_sub: dict = {}  # kind -> value of the previous «N)»/«а)» in the scope
    sub_closed = False
    previous = None  # previous body text paragraph
    opened = 0  # quotation balance since the last marked paragraph
    for p in items:
        if p.flow != "body":
            continue
        if p.kind == "table" or (p.kind == "text" and p.marker.kind == "none" and heading_evidence(p)):
            broken = True
        elif p.kind == "text" and p.marker.kind == "int":
            if p.marker.value == 1 and broken and last is not None and last > 1:
                p.marker.restart = True
                p.evidence.append({"restart": "«1.» after a table or heading; may take the level of the last «N.»"})
            broken = False
            last = p.marker.value
        if p.kind == "text" and p.marker.kind in SUBPOINT_KINDS:
            if (p.marker.value == 1 and sub_closed and (last_sub.get(p.marker.kind) or 0) > 1):
                p.marker.restart = True
                p.evidence.append({"restart": "list item 1 after a closing sentence; may take the level of the last item"})
            last_sub[p.marker.kind] = p.marker.value
        if p.kind == "text" and p.marker.kind not in {"none", "dash"}:
            sub_closed = False
            opened = quote_balance(p.text)
        elif p.kind == "text":
            inside = opened > 0
            opened += quote_balance(p.text)
            if (last_sub and not inside and p.text[:1].isupper() and previous is not None
                    and provision_final(previous.text) == "." and not strip_sup(p.text).rstrip(" .").endswith("»")):
                sub_closed = True
        if p.kind == "text" and not editorial_only(p):
            previous = p


def between_tables(items: list[Paragraph]) -> set[int]:
    """Ids of text paragraphs whose neighbouring body items on both sides are tables: a short line
    there («Стоимостные показатели», «Норма расхода ресурсов») labels the table part, so its right
    position is no signature evidence."""
    seq = [p for p in items if p.flow == "body" and p.kind != "picture"]
    return {id(p) for k, p in enumerate(seq)
            if p.kind == "text" and 0 < k < len(seq) - 1 and seq[k - 1].kind == "table" and seq[k + 1].kind == "table"}


TABLE_ROW_EVIDENCE = {"table_row": "marker between parts of the table that opens the annex; text of the annex"}
ANNEX_SCOPE = re.compile(r"(?:^|/)AN\d*$")


def table_rows(scope_path: str, items: list[Paragraph]) -> set[int]:
    """Ids of marked body paragraphs that are rows of a table annex (owner decision 23.10.2026,
    convention v2 §6). When an annex scope (`…/AN<n>`) opens with a table (no marked paragraph before
    its first table), OCR often cuts the table's rubrics («I. Подпрограмма …») and numbered rows
    («1.», «14.», «1.1») out of it as Section-header, List-item or Text regions between the table
    parts. Such a marker between the first and the last table of the annex opens no section or point:
    it is text of the annex. Named units («Раздел», «Глава», «Статья», «§») keep their meaning. An
    annex whose first marker precedes its first table keeps ordinary numbering, markers after the last
    table are unchanged, and an approved text that is itself a table (`S`) keeps the previous reading."""
    if not ANNEX_SCOPE.search(scope_path):
        return set()
    seq = [p for p in items if p.flow == "body" and p.kind not in {"picture", "approval", "annex"}]
    tables = [k for k, p in enumerate(seq) if p.kind == "table"]
    if not tables or any(p.marker.kind not in {"none", "dash"} for p in seq[:tables[0]] if p.kind != "table"):
        return set()
    return {id(p) for p in seq[tables[0] + 1:tables[-1]]
            if p.kind in {"text", "heading"} and p.marker.kind not in {"none", "dash"}
            and (p.marker.kind not in UNIT_RANK or p.marker.kind == "roman")}


def common_owner(owners: list[str]) -> str:
    """The longest common path prefix of owners in one scope («S/6» of «S/6» and «S/6/1»)."""
    parts = [o.split("/") for o in owners]
    common = []
    for level in zip(*parts):
        if len(set(level)) > 1:
            break
        common.append(level[0])
    return "/".join(common)


def path_of(scope: str, stack: tuple) -> str:
    return "/".join([scope] + [entry[2] for entry in stack])


def build(extraction: dict) -> dict:
    regions = load_regions(extraction)
    points_are_parts = points_are_article_parts([r.text for r in regions])
    paragraphs = logical_paragraphs(regions)

    # scopes: approving act until the first approval caption, then approved text,
    # each annex caption opens an annex scope inside the approved text. A standalone
    # «Проект» mark opens an attached draft (S, S2, ...) exactly like «УТВЕРЖДЕН...»:
    # directly after an approval caption it is part of it, and a preceding «Приложение»
    # caption joins it. A caption repeated as a running header on three or more pages
    # opens nothing (it stays a content paragraph of the current scope).
    scope = "A"
    scopes: list[tuple[str, list[Paragraph]]] = [("A", [])]
    pending_annex_caption = None
    approved_opened = False
    approved_count = 0
    approved_scope = "S"
    scope_captions: set[str] = set()  # caption texts of the current scope
    # An attached document printed as an act annex («Приложение № 1 к приказу»): its own annexes
    # («Приложение № 1 к Правилам …») open under it, `A/AN<n>/AN<m>`, until the next act annex.
    act_annex_document = None
    act_kind = None  # the act's own kind: a header line, else the first approval caption
    page_first: dict[int, Paragraph] = {}  # the first body text paragraph of each page
    for q in paragraphs:
        if q.flow == "body" and q.kind == "text":
            page_first.setdefault(q.first.page, q)
    for i, p in enumerate(paragraphs):
        if p.flow == "footnote" or p.kind in {"picture"}:
            scopes[-1][1].append(p)
            continue
        text = p.text
        if not approved_opened and act_kind is None and p.kind == "text":
            act_kind = act_kind_of_header(p.first.raw)
        # A running header/footer (same text on REPEAT_THRESHOLD+ regions) repeating a caption
        # of the current scope continues that scope instead of reopening it. A caption printed
        # only twice is not running: two approved texts may carry identical captions.
        running = p.first.category in NOISE_CATEGORIES and p.first.repeats >= REPEAT_THRESHOLD
        header_repeat = running and text in scope_captions
        caption_here = p.kind == "text" and not running_caption(p) and not header_repeat
        approval = caption_here and bool(APPROVAL.match(text)) and len(text) < CAPTION_BLOCK_MAX and not text.endswith(".")
        project = caption_here and is_project_caption(text)
        if approval or project:
            p.kind = "approval"
            if approval and act_kind is None:
                act_kind = act_kind_of_approval(text)
            if project:
                p.evidence.append({"caption": "project", "rule": "standalone «Проект» opens an attached document"})
            previous = next((q for q in reversed(paragraphs[:i]) if q.flow == "body" and q.kind != "picture"), None)
            if previous is None or previous.kind != "approval" or previous is pending_annex_caption:
                approved_count += 1
                approved_opened = True
                scope = "S" if approved_count == 1 else f"S{approved_count}"
                approved_scope = scope
                act_annex_document = None
                scopes.append((scope, []))
                scope_captions = set()
                if pending_annex_caption is not None:
                    scopes[-2][1].remove(pending_annex_caption)
                    scopes[-1][1].append(pending_annex_caption)
                    scope_captions.add(pending_annex_caption.text)
                    pending_annex_caption = None
            scopes[-1][1].append(p)
            scope_captions.add(text)
            continue
        nxt = next((q for q in paragraphs[i + 1:] if q.flow == "body" and q.kind == "text"), None)
        m = annex_caption(p, nxt.text if nxt is not None else "", page_first.get(p.first.page) is p) \
            if caption_here else None
        if m:
            p.kind = "annex"
            if nxt is not None and not running_caption(nxt) and (
                    (APPROVAL.match(nxt.text) and not approved_opened) or is_project_caption(nxt.text)):
                # "Приложение / УТВЕРЖДЕНЫ ..." on the approved text, or "Приложение / Проект"
                # on an attached draft: part of its approval caption
                p.kind = "approval"
                pending_annex_caption = p
                scopes[-1][1].append(p)
                continue
            number = m.group("number")
            label = f"AN{number}" if number else "AN"
            reference = m.group("ref") or (nxt.text if nxt is not None and nxt.text.startswith("к ") else "")
            to_act = annex_to_act(reference, act_kind)
            base = approved_scope if approved_opened and not to_act else "A"
            # cycle 10 B2: a lowercase document word («к форме налоговой декларации») names the open act annex too
            nested = act_annex_document is not None and not to_act and bool(
                DOCUMENT_REFERENT.match(reference) or LOWERCASE_DOCUMENT_REFERENT.match(reference))
            if nested:
                base = act_annex_document
            if running and f"{base}/{label}" == scopes[-1][0]:
                p.kind = "text"  # the current annex's caption repeated in a header: no new scope
                scopes[-1][1].append(p)
                continue
            scope = f"{base}/{label}"
            p.evidence.append({"annex_reference": reference or None, "attached_to": base,
                               "act_kind": act_kind,
                               "rule": "reference to the act (its own kind or «настоящему») -> act; "
                                       "otherwise the current approved text"})
            if nested:
                p.evidence.append({"nested_annex": "annex of the attached document printed as an act annex"})
            else:
                # only an act annex opened before any approved text: inside «УТВЕРЖДЕН … ПОРЯДОК» an act annex
                # (a form «к приказу») leaves «Приложение № 1 к Порядку …» to the approved text (`S/AN1`)
                act_annex_document = scope if base == "A" and to_act and not approved_opened else None
            scopes.append((scope, [p]))
            scope_captions = {text}
            continue
        scopes[-1][1].append(p)

    for scope_path, items in scopes:
        body = [p for p in items if p.flow == "body" and p.kind == "text"]
        list_prev = None  # (delimiter, value, rolled over) when the previous body paragraph is a list line
        for p in body:
            p.marker = parse_marker(p.text, p.first.category)
            number = list_number(p.text)
            if p.marker.kind == "none" and leading_zero_list(p.text):
                p.evidence.append({"list_line": "leading-zero marker, stays in the current unit"})
                list_prev = None if number is None else (*number, False)
            elif p.marker.kind in {"int", "paren"} and continues_list(number, list_prev):
                # «10.» right after «09.»: the zero-padded list goes on past two digits
                p.marker = Marker("none")
                p.evidence.append({"list_line": "continues the leading-zero list of the previous paragraph"})
                list_prev = (*number, True)
            else:
                list_prev = None
            if p.marker.kind in UNIT_RANK:
                p.kind = "heading"
        rows = table_rows(scope_path, items)
        for p in body:
            if id(p) in rows:
                p.marker = Marker("none")
                p.kind = "text"
                p.evidence.append(dict(TABLE_ROW_EVIDENCE))
        quoted_markers(items)
        roman_sequence(items, rows)
        mark_restarts(items)
        stacks = solve_depths([p.marker for p in body], article_parts=scope_path == "A")
        close_subpoints(body, stacks, subheading_stacks(items, body, stacks))
        editorial_note_owners(body, stacks, points_are_parts)
        article_notes(body, stacks)
        framed = between_tables(items)
        # The requisite block: after the last numbered or named element of the scope, the
        # first unmarked paragraph that looks like a requisite (or a signature) opens it, and
        # everything from there to the end of the scope belongs to the scope root. Unmarked
        # text before that paragraph stays with the last point.
        last_marked = max((k for k, p in enumerate(body) if p.marker.kind not in {"none", "dash"}), default=-1)
        # cycle 10 B1: a page mark (file code, typist's mark) never opens the block, and a page header/footer
        # opens it only by its text, not by its position («X», «Компьютер /Н.Н./…» sit at the right edge)
        block = next((body[k] for k in range(last_marked + 1, len(body)) if body[k].text
                      and PAGE_MARK_EVIDENCE not in body[k].evidence and not body[k].text[0].islower()
                      and (requisite_like(body[k].text)
                           or (signature_like(body[k].first) and id(body[k]) not in framed
                               and body[k].first.category not in NOISE_CATEGORIES))), None)
        in_block = False
        blank = None  # (stack, parent path) of the last marked paragraph when it is a fill-in line «2. ___»
        fill_parent: dict[int, str] = {}
        for p, stack in zip(body, stacks):
            in_block = in_block or p is block
            if p.marker.kind not in {"none", "dash"}:
                blank = (stack, path_of(scope_path, stack[:-1])) if fill_in_line(p.text) else None
                if blank is not None:
                    fill_parent[id(p)] = blank[1]
            if in_block:
                p.kind = "requisite"
                p.owner = scope_path
                p.evidence.append({"requisite_block": "after the last numbered or named element"})
            elif p.marker.kind == "none" and ((signature_like(p.first) and id(p) not in framed)
                                              or BARCODE_EVIDENCE in p.evidence or PAGE_MARK_EVIDENCE in p.evidence):
                p.kind = "signature"
                p.owner = scope_path
            elif p.marker.kind == "none" and blank is not None and stack == blank[0]:
                p.owner = blank[1]  # a fill-in line holds no text: what follows it belongs to its parent
                p.evidence.append(dict(FILL_IN_EVIDENCE))
            else:
                p.owner = path_of(scope_path, stack)
        # headings/titles before the first marker belong to the scope root (stack empty);
        # tables, captions, pictures follow the current owner; inside the requisite block
        # they belong to the scope root; after a fill-in line they follow its parent
        current = scope_path
        for p in items:
            if p.flow == "body" and p.kind in {"text", "heading", "requisite"}:
                current = fill_parent.get(id(p), p.owner)
            elif p.kind == "signature":
                continue
            elif p.flow == "body":
                p.owner = current
        for p in items:
            if p.kind in {"approval", "annex"}:
                p.owner = scope_path

    # footnotes: owner = latest preceding body paragraph carrying the same superscript marker; a table
    # may print the mark as HTML «<sup>1</sup>» instead of «¹» (Review Focus 2: two lists numbering
    # their footnotes from «¹» each keep their own footnotes). Cycle 6 (Review Focus 2): the mark is looked up
    # region by region and only before the footnote: a paragraph continued on a later page carries marks of
    # that page's footnotes, which do not make it the owner of an earlier footnote. The same mark printed
    # more than once on the footnote's page (a point and its subpoint) refers to one footnote: it belongs to
    # their common owner when they are in one scope.
    scope_of = {id(q): scope_path for scope_path, items in scopes for q in items}
    body_seen = []  # (region, paragraph) of body text seen so far
    for p in paragraphs:
        if p.flow == "body":
            body_seen.extend((r, p) for r in p.regions)
            continue
        number = p.footnote
        stars = ASTERISK_NOTE.match(strip_emphasis(p.text))
        if number is None and stars is None:
            p.owner = None
            p.evidence.append({"footnote_owner": "unnumbered"})
            continue
        if number is None:
            # «*- с точностью до 10 см», «** …»: the same run of asterisks, only on the footnote's page
            mark = re.compile(rf"(?<!\*){re.escape(stars.group(1))}(?!\*)")
        else:
            token = "".join(SUP[int(d)] for d in str(number))
            mark = re.compile(rf"(?<![{SUP}]){token}(?![{SUP}])|<sup>\s*{number}\s*</sup>")
        hits = sorted(((r, q) for r, q in body_seen if r.order < p.first.order
                       and mark.search(r.text if number is not None else strip_emphasis(r.text))
                       and (number is not None or r.page == p.first.page)), key=lambda hit: hit[0].order)
        p.owner = hits[-1][1].owner if hits else None
        page_hits = [q for r, q in hits if r.page == p.first.page]
        if (len({q.owner for q in page_hits}) > 1
                and len({scope_of.get(id(q)) for q in page_hits}) == 1
                and all(q.owner for q in page_hits)):
            p.owner = common_owner([q.owner for q in page_hits])
            p.evidence.append({"footnote_owner_common": "mark repeated on the footnote's page"})
        p.evidence.append({"footnote_owner": "marker" if hits else "unresolved", "candidates": len(hits)})

    region_owner = {}
    region_cont = {}
    for p in paragraphs:
        for k, r in enumerate(p.regions):
            region_owner[r.region_id] = p.owner
            region_cont[r.region_id] = k > 0
    # preservation: every OCR token belongs to exactly one region entry
    covered = Counter(t for r in regions for t in r.text_node_ids)
    expected = Counter(t["text_node_id"] for t in extraction["text_nodes"])
    if covered != expected:
        raise ValueError("token accounting mismatch")
    return {
        "schema": "ocr-logical-structure-experiment/0",
        "parser_version": VERSION,
        "source_asset_sha256": extraction["source_asset_sha256"],
        "paragraphs": [{
            "flow": p.flow, "kind": p.kind, "owner": p.owner,
            "marker": None if p.marker.kind in {"none"} else [p.marker.kind, p.marker.label],
            "regions": [{"page": r.page, "index": r.index, "region_id": r.region_id, "category": r.category}
                        for r in p.regions],
            "text_node_ids": [t for r in p.regions for t in r.text_node_ids],
            "text_preview": p.text[:90], "evidence": p.evidence,
        } for p in paragraphs],
        "regions": [{"page": r.page, "index": r.index, "region_id": r.region_id, "category": r.category,
                     "role": r.role, "owner": region_owner.get(r.region_id),
                     "continuation": region_cont.get(r.region_id, False)} for r in regions],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    with open(args.input, "rb") as handle:
        raw = handle.read()
    result = build(json.loads(raw))
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
