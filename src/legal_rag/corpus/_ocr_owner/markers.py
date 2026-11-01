"""Numbered markers, quotation/restart preparation and sequence depth solving."""

from __future__ import annotations

import re
from dataclasses import replace

from .model import (
    Marker,
    Paragraph,
)
from .text import (
    LETTERS,
    PAGE_MARK_EVIDENCE,
    ROMAN_CHARS,
    SUP,
    TERMINAL,
    editorial_only,
    fill_in_line,
    final_char,
    heading_evidence,
    heading_like,
    provision_final,
    quote_balance,
    roman_value,
    strip_sup,
    sup_value,
    terminated,
    to_roman,
)

# Named law units, recognised only at the start of a paragraph. Hierarchy:
# section (named or Roman) > chapter > paragraph § > article.
# Uppercase «СТАТЬЯ»/«ГЛАВА» as in codes; chapter numbers may carry OCR Cyrillic Х / Ukrainian І.
# «Статья 5¹», «Статья 12.1», and a compound inserted number «Статья 115¹⁻¹» (superscript minus).
# step 23 A (rp-1622-2020): an international treaty numbers its articles in Roman figures («Статья I» … «Статья VIII»)


# Named law units, recognised only at the start of a paragraph. Hierarchy:
# section (named or Roman) > chapter > paragraph § > article.
# Uppercase «СТАТЬЯ»/«ГЛАВА» as in codes; chapter numbers may carry OCR Cyrillic Х / Ukrainian І.
# «Статья 5¹», «Статья 12.1», and a compound inserted number «Статья 115¹⁻¹» (superscript minus).
# step 23 A (rp-1622-2020): an international treaty numbers its articles in Roman figures («Статья I» … «Статья VIII»)
ARTICLE = re.compile(rf"^(?:Статья|СТАТЬЯ)\s+(\d+(?:[.¹²³⁴⁵⁶⁷⁸⁹][\d⁰¹²³⁴⁵⁶⁷⁸⁹⁻]*)*|[{ROMAN_CHARS}]+)\.?(?=\s|$)")
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
UNIT_RANK = {"code_part": -1, "roman": 0, "section_named": 0, "letter_part": 0, "subsection": 0.5, "chapter": 1,
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
            if not number[0].isdigit():
                value = roman_value(number)
                if not value:
                    return None
                number = str(value)  # «Статья IV» is article 4 (`ст4`)
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
    # step 22 A (rp-1829-2015): a form's part «А. Персональные данные», «Б. Примечание» (kept by ``letter_parts``)
    m = re.match(r"^([А-ЯЁ])\.\s+[А-ЯЁ][а-яё]", text)
    if m and m.group(1).lower() in LETTERS and heading_like(text, category):
        letter = m.group(1).lower()
        return Marker("letter_part", LETTERS.index(letter) + 1, letter)
    m = re.match(r"^(\d{1,3}(?:\.\d{1,3})+)\.?\s+\S", text)
    if m:
        parts = tuple(int(p) for p in m.group(1).split("."))
        return Marker("decimal", parts, ".".join(map(str, parts)))
    if re.match(r"^\d{1,2}\.\s?\d{1,2}\.\s?\d{4}\b", text):
        return Marker("none")  # a date such as "12. 02. 2026", not point 12
    if leading_zero_list(text):
        return Marker("none")  # «01. …», «02) …»: a list line of the current unit, not a point
    # An inserted unit carries a superscript after its number: «2¹.», «3²)», «е¹)».
    # step 21.2 D (fz-435-2020, the owner's known class «6.Сообщение»): the number may be glued to a capitalised word
    m = re.match(rf"^(\d{{1,3}})([{SUP}]*)\.(?:\s+\S|(?=[А-ЯЁ][а-яё]))", text)
    if m:
        return Marker("int", int(m.group(1)), m.group(1) + m.group(2), sup=sup_value(m.group(2)))
    m = re.match(rf"^(\d{{1,3}})([{SUP}]*)\)\s+\S", text)
    if m:
        return with_ocr_reading(Marker("paren", int(m.group(1)), m.group(1) + m.group(2), sup=sup_value(m.group(2))))
    m = re.match(rf"^([а-я])([{SUP}]*)\)\s+\S", text)
    if m and m.group(1) in LETTERS:
        return with_ocr_reading(Marker("letter", LETTERS.index(m.group(1)) + 1, m.group(1) + m.group(2),
                                       sup=sup_value(m.group(2))))
    if re.match(r"^[-–—]\s+\S", text):
        return Marker("dash")
    return Marker("none")


# Step 16 C1: subpoint markers OCR confuses — Cyrillic «б» and digit «6», «з» and «3» (batches 7, 13, 14, 15).
OCR_CONFUSED = {"б": "6", "6": "б", "з": "3", "3": "з"}
OCR_READING_COST = 0.5  # above a tie-break (0.01 per level), below any gap (2.0+) or unexplained nesting (10.0)


def with_ocr_reading(marker: Marker) -> Marker:
    """Attach the other reading of a one-character «б)»/«6)», «з)»/«3)» subpoint marker (a superscript is kept)."""
    base = strip_sup(marker.label)
    other = OCR_CONFUSED.get(base) if len(base) == 1 else None
    if other is not None:
        tail = marker.label[1:]
        marker.alt = (Marker("paren", int(other), other + tail, sup=marker.sup) if other.isdigit()
                      else Marker("letter", LETTERS.index(other) + 1, other + tail, sup=marker.sup))
    return marker


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


LETTER_PART_EVIDENCE = {"letter_part": "«А.», «Б.» … in sequence: parts of the document, each with its own points"}


def letter_parts(body: list[Paragraph]) -> None:
    """Step 22 A: «А. …», «Б. …», «В. …» heading lines are parts of a form (rp-1829-2015 readmission forms: «А.
    Персональные данные» with points 1-12, «Б. Особые обстоятельства …» with its own 1, 2) only as a run that starts
    at «А.» and goes on with «Б.»; any other such line («А. Иванов» under a signature) is text."""
    marks = [k for k, p in enumerate(body) if p.marker.kind == "letter_part"]
    keep, expected = set(), 1
    run: list[int] = []
    for k in marks:
        value = body[k].marker.value
        if value == expected:
            run.append(k)
            expected += 1
            continue
        if len(run) >= 2:
            keep.update(run)
        run, expected = ([k], 2) if value == 1 else ([], 1)
    if len(run) >= 2:
        keep.update(run)
    for k in marks:
        if k in keep:
            body[k].kind = "heading"
            body[k].evidence.append(dict(LETTER_PART_EVIDENCE))
        else:
            body[k].marker = Marker("none")


def numeric_sections(body: list[Paragraph]) -> None:
    """Mixed Arabic/Roman section numbering needs both heading and sequence evidence."""
    for k, p in enumerate(body[:-1]):
        if (p.marker.kind != "int" or p.first.category not in {"Section-header", "Title"}
                or not heading_like(p.text, p.first.category) or terminated(p.text)
                or any(q.marker.kind in {"roman", "section_named"} for q in body[:k])):
            continue
        following = next((q.marker for q in body[k + 1:] if q.marker.kind != "none"), None)
        if (following is not None and following.kind == "decimal" and following.value[:1] == (p.marker.value,)
                and any(q.marker.kind == "roman" and q.marker.value == p.marker.value + 1 for q in body[k + 1:])):
            p.marker = Marker("roman", p.marker.value, "разд" + p.marker.label)
            p.kind = "heading"
            p.evidence.append({"numeric_section": "heading, matching decimal points and next Roman section"})


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
    if marker.kind == "decimal" and len(marker.value) > 2:
        prefix = marker.value[:-1]
        if not any(entry[0] == "decimal" and entry[1] == prefix for entry in stack):
            keep = 0
            for k, entry in enumerate(stack):
                if (entry[0] in UNIT_RANK
                        or (entry[0] == "int" and entry[1] == marker.value[0])
                        or (entry[0] == "decimal" and marker.value[:len(entry[1])] == entry[1])):
                    keep = k + 1
            yield stack[:keep] + ((marker.kind, marker.value, marker.label),), 5.0
            return
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
            if (marker.kind == "int" and parent is not None and parent[0] in UNIT_RANK
                    and sibling[0] == "decimal" and marker.value == sibling[1][0] + 1):
                yield stack[:keep] + (item,), 0.01 * (depth - keep)
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
                    if a == b:
                        yield stack[:keep] + (item,), 0.01 * (depth - keep)
                    elif len(a) == len(b) and a[:-1] == b[:-1] and b[-1] == a[-1] + 1:
                        yield stack[:keep] + (item,), 0.0 + 0.01 * (depth - keep)
                    elif len(a) == len(b) and a[:-1] == b[:-1] and b[-1] - a[-1] > 1:
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
        alt = replace(marker.alt, restart=marker.restart) if marker.alt is not None else None
        for cost, stack, last_int, hist in states:
            options = list(transitions(stack, marker, last_int, article_parts))
            if alt is not None:
                options += [(st, c + OCR_READING_COST) for st, c in transitions(stack, alt, last_int, article_parts)]
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


IN_QUOTATION_EVIDENCE = {"in_quotation": "unmarked paragraph inside an amending quotation"}


QUOTED_UNIT_HEADING = re.compile(r"^[«\"„“]\s*(?:Статья|Глава|Раздел)\s+\d")


def self_closing(text: str) -> bool:
    """An opener that also ends the quotation. With «…» it is the final closing mark (OCR merges or drops nested
    closing marks, cycle 8 C9); cycle 11: with straight quotes only an even count closes — an odd count with a final
    quote («"1. … программы "Развитие образования".») ends a quoted title inside the still open quotation."""
    if not QUOTE_CLOSE.search(text):
        return False
    # step 21.4 G (fz-119-2016): a quoted article, chapter or section heading whose last «»» closes an inner title
    # («… Федеральным законом «Об особенностях …»») and no «.;,» follows it opens the quoted unit, it closes nothing
    if QUOTED_UNIT_HEADING.match(text) and not re.search(r"[»\"“”][.;,)]+$", text):
        return False
    if '"' in text and not any(mark in text for mark in "«»„“"):
        return text.count('"') % 2 == 0
    return True


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
        if p.flow != "body" or PAGE_MARK_EVIDENCE in p.evidence:
            continue  # step 23 B: a page footer «4557147.doc» between «… в следующей редакции:» and «"Статья VI» splits nothing
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
                else:
                    # cycle 11 B1: an unmarked paragraph of the quotation (also its closing one) is quoted text too
                    p.evidence.append(dict(IN_QUOTATION_EVIDENCE))
                if QUOTE_CLOSE.search(text) and unbalanced_quotes(text) < 0:
                    open_from = None
                previous = p
                continue
        if (QUOTE_OPEN.match(p.text or "") and previous is not None and final_char(previous.text) == ":"
                and unbalanced_quotes(text) > 0 and not self_closing(text)):
            open_from, formish, inner = 0, False, {}
            # cycle 11 B3: an opener «"б) …;» starts the quotation's own list with its «б)»
            own = parse_marker(QUOTE_OPEN.sub("", p.text, count=1), p.first.category)
            if own.kind not in {"none", "dash"} and marker_number(own) is not None:
                inner[own.kind] = marker_number(own)
        if p.marker.kind not in {"none", "dash"}:
            last[p.marker.kind] = p.marker.value
            introducer = p.marker
        previous = p


# Step 13 B2: a list whose first item is printed on the line of its label: «Приложение: 1. Копии документов …»,
# then «2. Опись прилагаемых документов.» (a form's list of enclosures). A capitalised label of one or two words.
LABELLED_FIRST = re.compile(r"^[А-ЯЁ][а-яё]+(?:\s[а-яё]+)?:\s+1([.)])\s+\S")
LABELLED_FIRST_EVIDENCE = {"labelled_first": "«<Label>: 1. …» right before «2. …» is item 1 of that list"}


def labelled_first_items(items: list[Paragraph]) -> None:
    """An unmarked paragraph «<Label>: 1. …» followed by a body paragraph «2. …» (or «1) …» by «2) …»; pictures
    skipped, nothing else between) is item 1 of that list: it takes the marker the label hid."""
    seq = [p for p in items if p.flow == "body" and p.kind != "picture"]
    for p, nxt in zip(seq, seq[1:]):
        m = LABELLED_FIRST.match(p.text) if p.kind == "text" and p.marker.kind == "none" else None
        kind = "int" if m and m.group(1) == "." else "paren"
        if m and nxt.kind == "text" and nxt.marker.kind == kind and nxt.marker.value == 2:
            p.marker = Marker(kind, 1, "1")
            p.evidence.append(dict(LABELLED_FIRST_EVIDENCE))


def mark_restarts(items: list[Paragraph]) -> None:
    """Restarted numbering: an «1.» whose previous «N.» paragraph in the scope is separated from it
    by a table or an unmarked heading (OCR Section-header/Title) may restart the numbering at the
    level of that «N.» (the solver checks N > 1 at that level). Without such a break, or for «1)»/
    «а)» subpoints and «1.1», nothing changes."""
    broken = False
    last = None  # value of the previous «N.» in the scope
    last_blank = False  # the previous «N.» is a fill-in line
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
            # step 23 F (prikaz-fns-269-2020): a fill-in line «2. ______;» holds no text, so a later «1. ______;» is
            # never its subpoint — a second fill-in list of the form
            if p.marker.value == 1 and (broken or last_blank) and last is not None and last > 1:
                p.marker.restart = True
                p.evidence.append({"restart": "«1.» after a table or heading; may take the level of the last «N.»"})
            broken = False
            last = p.marker.value
            last_blank = fill_in_line(p.text)
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


# Step 17 B (owner 28.10.2026, batch 16): a line of point references inside a point («2.1.42 и 2.2.7 в части наличия
# вкладных резервуаров;», «2.1.34, 4.1.4, 4.3.11 в части …»): a dotted number without its final dot, then «,», «и» and
# another number, or a lowercase word.
POINT_REFERENCES = re.compile(r"^\d{1,3}(?:\.\d{1,3})+(?:,\s*\d|\s+и\s+\d|\s+[а-яё]|\s*[-–—]\s*\d)")  # step 21.4 A: «10.10 - 10.17)»
POINT_REFERENCES_EVIDENCE = {"point_references": "numbers of points referred to, not a point of its own"}


def goes_on_from(value: tuple, prev: Marker | None) -> bool:
    """A dotted ``value`` continues the numbering after the marker ``prev``: its child («12.1» after «12.»,
    «2.1.1» after «2.1.»), its sibling («12.2» after «12.1») or a sibling of its parent («2.2» after «2.1.5»)."""
    if prev is None:
        return False
    if prev.kind == "int":
        return len(value) == 2 and value[0] == prev.value
    if prev.kind != "decimal":
        return False
    return value[:-1] == prev.value or value[:-1] == prev.value[:-1] or value[:-1] == prev.value[:-2]


def point_references(body: list[Paragraph]) -> None:
    """Step 17 B: a reference line (``POINT_REFERENCES``) whose number does not go on from the last marker
    is text of the open point. A dotless subpoint that does go on («12.1 принятие решения …» after «12.», or
    «7.1.8 Организации …» with a capital) keeps its marker."""
    prev = None
    for p in body:
        if p.marker.kind in {"none", "dash"}:
            continue
        if (p.kind == "text" and p.marker.kind == "decimal" and POINT_REFERENCES.match(strip_sup(p.text))
                and not goes_on_from(p.marker.value, prev)):
            p.marker = Marker("none")
            p.evidence.append(dict(POINT_REFERENCES_EVIDENCE))
            continue
        prev = p.marker


def numbering_gaps(markers: list[Marker]) -> bool:
    """Step 22 B: two successive «I.»-sections or «N.» points of the list skip a number (III after I, 32 after 1)."""
    last: dict[str, int] = {}
    for m in markers:
        if m.kind in {"roman", "int"}:
            if m.kind in last and m.value > last[m.kind] + 1:
                return True
            last[m.kind] = m.value
    return False
