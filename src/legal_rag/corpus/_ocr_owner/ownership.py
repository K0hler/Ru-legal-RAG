"""Body and footnote ownership inside established document scopes."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from .markers import (
    LABELLED_FIRST_EVIDENCE,
    POINT_KINDS,
    SUBPOINT_KINDS,
    UNIT_RANK,
    continues_list,
    labelled_first_items,
    leading_zero_list,
    letter_parts,
    list_number,
    mark_restarts,
    numeric_sections,
    parse_marker,
    point_references,
    quoted_markers,
    roman_sequence,
    solve_depths,
)
from .model import (
    Marker,
    Paragraph,
)
from .scopes import (
    SERVICE_TAIL_EVIDENCE,
)
from .tables import (
    TABLE_NUMBER,
    TABLE_ROW_EVIDENCE,
    between_tables,
    form_signature_blocks,
    table_block_sections,
    table_references,
    table_rows,
    table_rubrics,
    under_table_ids,
)
from .text import (
    ASTERISK_NOTE,
    BARCODE_EVIDENCE,
    BLANK_LINE,
    FIGURE_CAPTION,
    FILL_IN_EVIDENCE,
    NOISE_CATEGORIES,
    PAGE_BAND_EVIDENCE,
    PAGE_MARK_EVIDENCE,
    SUP,
    TOC_EVIDENCE,
    editorial_note_unit,
    editorial_only,
    field_line,
    fill_in_line,
    final_char,
    heading_evidence,
    is_caption,
    is_project_caption,
    provision_final,
    quote_balance,
    requisite_like,
    signature_caption,
    signature_like,
    strip_emphasis,
    strip_sup,
    terminated,
    toc_line,
)

SUBHEADING_MAX = 200  # a subheading printed as body text
SUBHEADING_HEADER_MAX = 500  # with OCR heading evidence (Section-header/Title): regulations print ~450
SUBHEADING_CORROBORATION = 2  # body-text subheadings need this many header-category ones in the scope
# Step 13 B1: in a corroborated scope a body-text subheading may be long (an administrative regulation's standard
# rubric «Показатели доступности и качества государственной услуги, в том числе …» runs to ~900 characters)
SUBHEADING_STYLED_MAX = 1000
# A labelled value line: «Адрес: …», «Почтовый адрес: …», «Телефон: …».
LABEL_LINE = re.compile(r"^\S+(?:\s\S+)?:\s")


def subheading_candidate(p: Paragraph, long: bool = False) -> bool:
    """An unmarked capitalised line that is not a sentence: no final «.;:!?», no broken tail («,»,
    hyphen). Not a figure/table/form caption (OCR category Caption or the text «Схема 1», «Рисунок
    1 - …», «Таблица 2», «Форма N 3»), a labelled value («Адрес: …»), a requisite or signature line,
    or a rejected annex caption («Приложение 2»). At most SUBHEADING_MAX characters as body text
    (SUBHEADING_STYLED_MAX with ``long``), SUBHEADING_HEADER_MAX with OCR heading evidence (Section-header/Title)."""
    text = strip_emphasis(p.text)  # step 24 C: a whole bold line can be a subheading even in a Text region
    header = heading_evidence(p, bold=True)
    limit = SUBHEADING_HEADER_MAX if header else SUBHEADING_STYLED_MAX if long else SUBHEADING_MAX
    # step 16 C3: an OCR heading may end with «:» («## Проведение проверки:» over «### Документарная проверка»)
    open_ = not terminated(text) or (header and final_char(text) == ":")
    return (p.kind == "text" and p.marker.kind == "none" and p.first.category != "Caption"
            and bool(text) and text[0].isupper()
            and len(text) <= limit and open_ and final_char(text) not in ",-–—"
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
    scope (the document's subheading style); otherwise an OCR-cut sentence would qualify. Step 13 B1: such a
    corroborated body-text run may also be longer than SUBHEADING_MAX, up to SUBHEADING_STYLED_MAX.
    Returns the changed body indices."""
    index = {id(p): k for k, p in enumerate(body)}
    # a table or picture in between blocks the rule; step 23 D: a page mark («компьютер /Ю.Р. /Прил-И301-1») does not
    seq = [p for p in items if p.flow == "body" and PAGE_MARK_EVIDENCE not in p.evidence]
    runs = []  # (run paragraphs, parent stack)
    k = 0
    while k < len(seq):
        if id(seq[k]) not in index or not subheading_candidate(seq[k], long=True):
            k += 1
            continue
        end = k
        while end + 1 < len(seq) and id(seq[end + 1]) in index and subheading_candidate(seq[end + 1], long=True):
            end += 1
        prev = seq[k - 1] if k else None
        nxt = seq[end + 1] if end + 1 < len(seq) else None
        # step 16 C3: a run of OCR headings also follows a point that lost its final «.»
        finished = final_char(prev.text) in ".;" if prev is not None else False
        if prev is not None and not finished and prev.marker.kind in POINT_KINDS and final_char(prev.text).isalnum():
            finished = all(heading_evidence(q, bold=True) for q in seq[k:end + 1])
        if (prev is not None and id(prev) in index and finished
                and nxt is not None and id(nxt) in index and nxt.marker.kind in POINT_KINDS):
            parent = stacks[index[id(nxt)]][:-1]
            # step 21.4 B (pp-1521-2014): a run of OCR headings between points of the scope root is the root's heading
            if (parent and parent[-1][0] in UNIT_RANK) or (not parent and all(heading_evidence(q, bold=True) for q in seq[k:end + 1])):
                runs.append((seq[k:end + 1], parent))
        k = end + 1
    styled = sum(any(heading_evidence(q, bold=True) for q in run) for run, _ in runs) >= SUBHEADING_CORROBORATION
    changed: set[int] = set()
    for run, parent in runs:
        if not styled and (not any(heading_evidence(q, bold=True) for q in run)
                           or not all(subheading_candidate(q) for q in run)):
            continue
        for q in run:
            j = index[id(q)]
            if stacks[j][:len(parent)] == parent:
                stacks[j] = parent
                changed.add(j)
                q.evidence.append({"subheading": "unmarked line before a numbered point -> its parent"})
    return changed


def continues_level(nxt: tuple, stack: tuple, level: int) -> bool:
    """The next marked paragraph stays in the list at ``level`` of ``stack`` (same parent, same kind,
    not a restarted numbering: a lower value there is a new list)."""
    return (len(nxt) > level and nxt[:level] == stack[:level] and nxt[level][0] == stack[level][0]
            and not (nxt[level][1] < stack[level][1] and isinstance(nxt[level][1], int)))


OWN_SENTENCE_MIN_WORDS = 8  # step 16 C2: a sentence after an unterminated subpoint, not the end of a cut one


def subpoint_level(stack: tuple, level: int) -> bool:
    """``stack[level]`` is a list subpoint «1)» / «а)». Step 17 (owner 28.10.2026): a dotted «4.3.26.» is no list
    item; a paragraph after the last one stays in it (the step-16 C2 dotted reading overfitted batch 15)."""
    return stack[level][0] in SUBPOINT_KINDS


# Step 21.7 G (prikaz-minkultury-1321-2016): «документов, указанных в пунктах 15 и 15.1 …» names «15.1» as a peer of «15»
PEER_POINTS = re.compile(r"\bпункт(?:ах|ами|ов|ы)\s+(\d+)\s+и\s+(\d+)\.(\d+)(?!\.?\d)")


def peer_points(body: list[Paragraph], stacks: list[tuple]) -> None:
    """A dotted point «N.M» the act itself names together with «N» as its peer («в пунктах 15 и 15.1») is not nested
    in «N» (convention v2 §5 exception, as the annotator recorded it): «N.M» and what lies under it move up a level."""
    peers = {(int(m.group(2)), int(m.group(3))) for p in body for m in PEER_POINTS.finditer(p.text)
             if m.group(1) == m.group(2)}
    if not peers:
        return
    for k, p in enumerate(body):
        stack = stacks[k]
        for i in range(1, len(stack)):
            if (stack[i][0] == "decimal" and tuple(stack[i][1]) in peers and stack[i - 1][0] == "int"
                    and stack[i - 1][1] == stack[i][1][0]):
                stacks[k] = stack[:i - 1] + stack[i:]
                if p.marker.kind == "decimal" and i == len(stack) - 1:
                    p.evidence.append({"peer_point": "«N.M» named together with «N» is its peer, not its subpoint"})
                break


def close_subpoints(body: list[Paragraph], stacks: list[tuple], keep: set[int]) -> None:
    """A paragraph after the last subpoint returns to the point. An unmarked paragraph inside a
    subpoint (``subpoint_level``) closes it when it starts with a capital letter and does not continue the
    enumeration: the previous paragraph ended with «.», or it ended with «;» and this paragraph is
    a sentence of its own (final «.»), or the subpoint lost its final «.» and this sentence is on its
    page. Only the list of the last subpoint is closed, when the next marked
    paragraph does not continue it; later unmarked paragraphs up to the next marker follow the point. A
    lowercase start, a «;» item, text after «:» or a list that goes on stay in the subpoint. Nothing
    closes inside a quotation: while a «…» opened in the subpoint (from its marked paragraph on) is
    unbalanced, or when the paragraph itself ends a quotation («…».» / «…»»), as in amending text
    («а) пункт 3 изложить в следующей редакции: «3. …»»)."""
    closed = None
    opened = 0  # quotation balance since the last marked paragraph
    dash_intro: tuple | None = None  # step 21.4 F: the stack of a dash item ending «:» that opened a letter list
    for k, p in enumerate(body):
        if p.marker.kind == "dash" and p.kind == "text":
            if (dash_intro is not None and len(stacks[k]) > len(dash_intro)
                    and stacks[k][:len(dash_intro)] == dash_intro):
                stacks[k] = dash_intro  # «- на долгосрочный период …» after «а)», «б)» opened by «- на очередной …:»
                p.evidence.append({"dash_sibling": "a dash item after the list its dash sibling opened"})
            dash_intro = stacks[k] if final_char(p.text) == ":" else None
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
        # step 21.3 C: a formula legend «где λ – …» after the list items closes like a sentence
        legend = p.text.startswith("где ")
        if not k or not stack or not subpoint_level(stack, len(stack) - 1) or not (p.text[:1].isupper() or legend):
            continue
        if p.first.category == "Caption" or TABLE_NUMBER.match(p.text) or FIGURE_CAPTION.match(p.text):
            continue  # step 21.3 A: «Таблица 7.1. …» under a subpoint is its table's caption, not a closing sentence
        if (inside_quote or strip_sup(p.text).rstrip(" .").endswith("»")
                or any("quoted" in e or "in_quotation" in e for e in p.evidence)):
            continue  # cycle 9 B4 / 11 B1: a quoted heading or paragraph (straight quotes too) closes nothing
        j = k - 1  # the previous provision text; a standalone editorial note in between does not count
        while j > 0 and editorial_only(body[j]):
            j -= 1
        before, own = provision_final(body[j].text), provision_final(p.text)
        # step 16 C2: the subpoint's marked paragraph lost its final «.» («19) … производственного контроля»),
        # then a sentence of its own on the same page; a short line («Российской Федерации.»), one across a page
        # break or after unmarked lines (a list of names) may end the cut sentence
        # step 21.3 B: after an unmarked «;» line (a formula legend «К = 10 – …;») the last line closes nothing
        semicolon = before == ";" and own == "." and (body[j].marker.kind not in {"none", "dash"}
                                                       or not body[j].text[:1].isupper())
        legend_close = legend and own == "." and before in ".;,"
        cut = (before.isalnum() and own == "." and body[j].marker.kind not in {"none", "dash"}
               and body[j].regions[-1].page == p.first.page
               and len(p.text.split()) >= OWN_SENTENCE_MIN_WORDS)
        if not (before == "." or semicolon or cut or legend_close):
            continue
        nxt = next((stacks[j] for j in range(k + 1, len(body)) if body[j].marker.kind not in {"none", "dash"}), ())
        # step 16 C2: only the list of the last subpoint closes; the paragraph goes to the owner of that list
        # («2)» for its «а)»-«д)»), not further up
        if not continues_level(nxt, stack, len(stack) - 1):
            closed = stacks[k] = stack[:-1]
            p.evidence.append({"subpoint_closed": "capitalised paragraph after the last subpoint -> the point"})
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
DOCUMENT_NOTE = re.compile(r"\bнастоящ\w*\s+(?:переч[её]?н|правил|порядк|положени|требовани|стандарт)", re.IGNORECASE)
ARTICLE_NOTE = re.compile(r"^Примечани[ея](?:\s*[.:]|$)")
# Cycle 10 B5: a standalone heading «Примечания» / «Примечание:» (nothing else on the line)
NOTES_HEADING = re.compile(r"Примечани[ея]\s*[.:]?")


def article_notes(body: list[Paragraph], stacks: list[tuple], under_tables: set[int] = frozenset()) -> None:
    """A note «Примечание. …» or «Примечания:» after the parts of an article belongs to the article, not to
    its last part; so do the numbered notes «N.» under it and editorial notes after them, up to the next named
    unit or any other marker. Outside an article a note keeps its owner, and so does a note under a point «5)» of
    an article (an amending law quoting a new article with its note). Cycle 10 B5: outside an article a standalone
    heading «Примечания» after the last point opens the notes of the document root, up to the next marker; step 20 C:
    not right under a table, where it starts the table's notes."""
    note = None  # the article's stack while inside its note block
    note_number = 1  # step 21.3 E: the next number of a document's numbered notes «1)», «2)»
    for k, p in enumerate(body):
        # «1)», «2)» notes stay notes; «1.», «2.» under «Примечания:» are points of the document (sanpin-31-2015 gold)
        numbered_note = (note == () and p.marker.kind == "paren" and p.marker.value == note_number)
        if numbered_note:
            note_number += 1
        elif note is not None and (p.marker.kind not in {"none", "int"} or (note == () and p.marker.kind != "none")):
            note = None
        quoted = any("quoted" in e or "in_quotation" in e for e in p.evidence)  # cycle 11 B4: a quoted form's notes
        # step 13 B2: «Примечания: 1. …» took the marker its label hid; in an article it still opens the note block
        unmarked = p.marker.kind == "none" or LABELLED_FIRST_EVIDENCE in p.evidence
        if note is None and p.kind == "text" and unmarked and ARTICLE_NOTE.match(p.text) and not quoted:
            level = next((i for i, e in enumerate(stacks[k]) if e[0] == "article"), None)
            below = stacks[k][level + 1:level + 2] if level is not None else ()
            # step 20 C: a singular «Примечание:» right under a table is the note of that table and stays with the
            # table's owner; the plural «Примечания» explains the whole form (cycle 10 B5)
            under_table = id(p) in under_tables
            if level is None and NOTES_HEADING.fullmatch(p.text.strip()) and not under_table:
                # cycle 10 B5: outside an article a standalone «Примечания» heading after the last point opens the
                # notes of the document (a form's explanations), not text of that point
                note = ()
                note_number = 1
                p.evidence.append({"notes_heading": "notes of the document after its last point"})
            elif level is None and DOCUMENT_NOTE.search(p.text):
                stacks[k] = ()  # step 21.4 C: «Примечание. … включенных в настоящий перечень …» is the document's note
                p.evidence.append({"document_note": "a note about the whole document"})
            elif level is not None and all(e[2].startswith("ч") for e in below):
                note = stacks[k][:level + 1]
                p.evidence.append({"article_note": "note block of the article"})
        if note is not None:
            stacks[k] = note


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


STAMP_TABLE = re.compile(r"ГОСУДАРСТВЕННОЙ\s+РЕГИСТРАЦИИ|ЗАРЕГИСТРИРОВАН")  # upper case: a stamp, not a reference
STAMP_TABLE_MAX = 400


def assign_body_owners(scope_path: str, items: list[Paragraph], points_are_parts: bool) -> None:
    body = [p for p in items if p.flow == "body" and p.kind == "text"]
    list_prev = None  # (delimiter, value, rolled over) when the previous body paragraph is a list line
    for k, p in enumerate(body):
        marker_text = p.text
        # Step 24 A: «1.1.» followed immediately by its parenthesised field caption is a form position;
        # a bare number over a table (professional standards) is not enough evidence to open a point.
        if re.fullmatch(r"\d{1,3}(?:\.\d{1,3})+\.", marker_text) and k + 1 < len(body):
            caption = body[k + 1]
            if (caption.first.page == p.regions[-1].page and caption.first.index == p.regions[-1].index + 1
                    and caption.text.startswith("(") and not signature_caption(caption.text)):
                marker_text += " " + caption.text  # matching view only; source regions stay separate
        p.marker = parse_marker(marker_text, p.first.category)
        if p.first.category in NOISE_CATEGORIES and p.marker.kind != "none":
            # step 12 B1: a page header/footer is outside the text flow and never opens a unit («1. Коприво …»)
            p.marker = Marker("none")
            p.evidence.append(dict(PAGE_BAND_EVIDENCE))
        if toc_line(p.text):
            p.marker = Marker("none")
            p.kind = "text"
            p.evidence.append(dict(TOC_EVIDENCE))
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
    point_references(body)
    rows = table_rows(scope_path, items) | table_rubrics(items)
    for p in body:
        if id(p) in rows:
            p.marker = Marker("none")
            p.kind = "text"
            p.evidence.append(dict(TABLE_ROW_EVIDENCE))
    labelled_first_items(items)
    quoted_markers(items)
    numeric_sections(body)
    roman_sequence(items, rows)
    letter_parts(body)
    mark_restarts(items)
    stacks = solve_depths([p.marker for p in body], article_parts=scope_path == "A")
    for p, stack in zip(body, stacks):
        alt = p.marker.alt
        if alt is not None and stack and stack[-1][:2] == (alt.kind, alt.value) and stack[-1][0] != p.marker.kind:
            p.evidence.append({"ocr_marker": f"«{p.marker.label})» read as «{alt.label})» by the sequence"})
            p.marker = replace(alt, restart=p.marker.restart)
    peer_points(body, stacks)
    close_subpoints(body, stacks, subheading_stacks(items, body, stacks))
    editorial_note_owners(body, stacks, points_are_parts)
    article_notes(body, stacks, under_table_ids(items))
    table_references(body, stacks)
    table_block_sections(scope_path, items, body, stacks)
    for k, p in enumerate(body):
        if TOC_EVIDENCE in p.evidence:
            stacks[k] = ()  # cycle 10 B4: a contents line belongs to the document root
    framed = between_tables(items)
    signatures = form_signature_blocks(items)
    # The requisite block: after the last numbered or named element of the scope, the
    # first unmarked paragraph that looks like a requisite (or a signature) opens it, and
    # everything from there to the end of the scope belongs to the scope root. Unmarked
    # text before that paragraph stays with the last point.
    last_marked = max((k for k, p in enumerate(body) if p.marker.kind not in {"none", "dash"}), default=-1)
    # cycle 10 B1: a page mark (file code, typist's mark) never opens the block, and a page header/footer
    # opens it only by its text, not by its position («X», «Компьютер /Н.Н./…» sit at the right edge)
    # cycle 11 B2: a paragraph of an amending quotation («(форма)» of a quoted form) opens no block by its
    # position either; by its text (a closing rule «____» after a quotation whose quote mark was lost) it still does
    # step 13 B3: a form's signature caption («(подпись)», «М.П.») opens it, but not inside an amending quotation
    # (a quoted form ends «М.П. (при наличии)".»)
    # step 22 D: a blank line right under a part heading («Г. Примечания» / «__________») is that part's field
    block = next((body[k] for k in range(last_marked + 1, len(body)) if body[k].text
                  and not (k == last_marked + 1 and body[last_marked].marker.kind == "letter_part"
                           and BLANK_LINE.match(body[k].text))
                  and PAGE_MARK_EVIDENCE not in body[k].evidence and not body[k].text[0].islower()
                  and (requisite_like(body[k].text)
                       or (signature_caption(body[k].text)
                           and not any("quoted" in e or "in_quotation" in e for e in body[k].evidence))
                       or (signature_like(body[k].first) and id(body[k]) not in framed
                           and body[k].first.category not in NOISE_CATEGORIES
                           and not any("quoted" in e or "in_quotation" in e for e in body[k].evidence)))), None)
    if block is not None and block.text.startswith("(") and not signature_caption(block.text):
        # step 21.5 C: a field caption «(серия, номер, дата выдачи …)» stays with its field; the block opens after it
        after = body.index(block) + 1
        block = body[after] if after < len(body) else None
    in_block = False
    blank = None  # (stack, parent path) of the last marked paragraph when it is a fill-in line «2. ___»
    fill_parent: dict[int, str] = {}
    for p, stack in zip(body, stacks):
        in_block = in_block or p is block or SERVICE_TAIL_EVIDENCE in p.evidence
        if p.marker.kind not in {"none", "dash"}:
            blank = (stack, path_of(scope_path, stack[:-1]), False) if fill_in_line(p.text) else (
                (stack, path_of(scope_path, stack[:-1]), True) if field_line(p.text) else None)
            if blank is not None:
                fill_parent[id(p)] = blank[1]
        if in_block:
            p.kind = "requisite"
            p.owner = scope_path
            p.evidence.append({"requisite_block": "after the last numbered or named element"})
        elif p.marker.kind == "none" and ((signature_like(p.first) and id(p) not in framed
                                           and not (p.text.startswith("(") and not signature_caption(p.text))
                                           and not any("in_quotation" in e for e in p.evidence))
                                          or BARCODE_EVIDENCE in p.evidence or PAGE_MARK_EVIDENCE in p.evidence):
            p.kind = "signature"
            p.owner = scope_path
        elif (p.marker.kind == "none" and blank is not None and stack == blank[0]
              and not (blank[2] and (p.text.startswith(("(", "*")) or BLANK_LINE.match(p.text)))):
            # step 22 D: a blank line under a field «2. Документы …, ______» is more room of that field
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
            if p.kind == "table" and len(p.text) <= STAMP_TABLE_MAX and STAMP_TABLE.search(p.text):
                p.owner = scope_path  # step 21.5 E: a registration stamp belongs to the scope root
    for p in items:
        if p.kind in {"approval", "annex"}:
            p.owner = scope_path
        if id(p) in signatures:
            p.owner = scope_path
            p.evidence.append({"form_signature": "name and signature before the numbered document-receipt field"})


def assign_footnote_owners(paragraphs: list[Paragraph], scopes: list[tuple[str, list[Paragraph]]]) -> None:
    # footnotes: owner = latest preceding body paragraph carrying the same superscript marker; a table
    # may print the mark as HTML «<sup>1</sup>» instead of «¹» (Review Focus 2: two lists numbering
    # their footnotes from «¹» each keep their own footnotes). Cycle 6 (Review Focus 2): the mark is looked up
    # region by region and only before the footnote: a paragraph continued on a later page carries marks of
    # that page's footnotes, which do not make it the owner of an earlier footnote. The same mark printed
    # more than once on the footnote's page (a point and its subpoint) refers to one footnote: it belongs to
    # their common owner when they are in one scope.
    scope_of = {id(q): scope_path for scope_path, items in scopes for q in items}
    page_marked: dict[int, bool] = {}  # footnote id -> its mark found on its own page
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
            page_marked[id(p)] = False
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
        page_marked[id(p)] = bool(page_hits)
    # step 21.3 F: a footnote whose mark is only on an earlier page follows the footnotes of its own page that found their
    # marks there (one table's notes); a footnote whose mark is nowhere belongs to the document of its page
    by_page: dict[int, list] = defaultdict(list)
    for p in paragraphs:
        if p.flow == "footnote":
            by_page[p.first.page].append(p)
    for notes in by_page.values():
        local = [q.owner for q in notes if page_marked.get(id(q)) and q.owner]
        one_table = len(set(local)) == 1  # the page's marked footnotes share one owner: the notes of one unit
        for q in notes:
            if q.owner is None or (one_table and not page_marked.get(id(q)) and q.footnote is not None):
                q.owner = common_owner(local) if local else scope_of.get(id(q))
                q.evidence.append({"footnote_owner_page": "the footnotes of its page, or the document of its page"})
