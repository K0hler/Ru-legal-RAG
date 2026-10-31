"""Table and form boundaries used to refine paragraph ownership."""

from __future__ import annotations

import re

from .markers import (
    POINT_KINDS,
    UNIT_RANK,
    numbering_gaps,
)
from .model import (
    Paragraph,
)
from .text import (
    FIGURE_CAPTION,
    PAGE_MARK_EVIDENCE,
    final_char,
    heading_evidence,
    terminated,
    view,
)

# Step 20 D (batch 19): «… представлены в таблицах 6.1, 6.2; … в таблице 6.3» names tables; a caption «Таблица 6.1».


# Step 20 D (batch 19): «… представлены в таблицах 6.1, 6.2; … в таблице 6.3» names tables; a caption «Таблица 6.1».
TABLE_REFERENCE = re.compile(r"таблиц\w*\s+((?:№\s*)?\d+(?:\.\d+)*(?:\s*(?:,|и)\s*(?:№\s*)?\d+(?:\.\d+)*)*)")
TABLE_CAPTION = re.compile(r"^Таблица\s*(?:№\s*)?(\d+(?:\.\d+)*)\.?$")
TABLE_REFERENCE_EVIDENCE = {"table_reference": "a table printed away from its reference belongs to the point naming it"}


def referenced_tables(text: str) -> set[str]:
    return {n for m in TABLE_REFERENCE.finditer(text) for n in re.findall(r"\d+(?:\.\d+)*", m.group(1))}


def table_references(body: list[Paragraph], stacks: list[tuple]) -> None:
    """Step 20 D: a caption «Таблица N» named by an earlier point («в таблицах N, M») but printed under another point
    (the tables of section VI after section VII) belongs, with what follows it up to the next marker, to the latest
    point that names it. A caption under the point naming it, or named by nobody, keeps its owner."""
    named: dict[str, tuple] = {}  # table number -> stack of the latest marked paragraph naming it
    owner: tuple | None = None
    point: tuple = ()
    for k, p in enumerate(body):
        if p.marker.kind not in {"none", "dash"}:
            owner = None
            point = stacks[k]
        m = TABLE_CAPTION.match(p.text.strip()) if p.marker.kind == "none" else None
        if m and m.group(1) in named and named[m.group(1)] != point[:len(named[m.group(1)])]:
            owner = named[m.group(1)]
        elif m:
            owner = None
        if owner is not None:
            stacks[k] = owner
            p.evidence.append(dict(TABLE_REFERENCE_EVIDENCE))
        for number in referenced_tables(p.text):
            named[number] = point if p.marker.kind == "none" else stacks[k]


TABLE_NUMBER = re.compile(r"^Таблица\s*(?:№\s*)?(\d+(?:\.\d+)*)")  # «Таблица 2.1. Оптимальные величины …» too
TABLE_BLOCK_EVIDENCE = {"table_block": "a table with its own heading between points -> the section (owner 29.10.2026)"}


def table_head(q: Paragraph) -> bool:
    """An unmarked line heading a table: an OCR heading or caption, or a «Таблица N» / «Рисунок N» caption text."""
    text = q.text.strip()
    return (q.kind == "text" and q.marker.kind == "none" and bool(text)
            and (heading_evidence(q) or q.first.category == "Caption" or bool(TABLE_CAPTION.match(text))
                 or bool(FIGURE_CAPTION.match(text))))


TABLE_TITLE_MAX = 400  # step 21.7 B: «Предельно допустимые концентрации (ПДК) … аквапарков» has 307


def table_title(seq: list[Paragraph], k: int) -> bool:
    """Step 21.6 (sanpin-2-2021): an unmarked, unterminated body line right before a «Таблица N» caption that heads a
    table is that table's title («Предельно допустимые концентрации (ПДК) химических веществ …» / «Таблица 3.13»)."""
    q = seq[k]
    text = q.text.strip()
    nxt = seq[k + 1] if k + 1 < len(seq) else None
    return (q.kind == "text" and q.marker.kind == "none" and bool(text) and text[:1].isupper()
            and len(text) <= TABLE_TITLE_MAX and not terminated(text) and final_char(text) not in ",-–—"
            and nxt is not None and nxt.kind == "text" and bool(TABLE_NUMBER.match(nxt.text.strip())))


def formula_body(text: str) -> str:
    """Step 21.7 B: a formula line «$$ Ксі - коэффициент … загрязнения. $$» ends where its body ends («.}» too)."""
    t = text.strip()
    return t.strip("$").strip().rstrip("}").rstrip() if t.startswith("$$") and t.endswith("$$") else text


def gap_sibling(stack: tuple, heads: list[Paragraph], rest: list[Paragraph]) -> bool:
    """Step 21.7 E (prikaz-minekonomicheskogo-37-2015, annex 5): an unnumbered heading over a table between «5.1.» and the
    next «5.3.» stands for the missing «5.2» («Пусковые расходы¹,²»): the block is a sibling of «5.1», not its text."""
    if not stack or stack[-1][0] != "decimal" or not heads:
        return False
    text = heads[0].text.strip()
    if len(text) > TABLE_RUBRIC_MAX or terminated(text):
        return False
    value = stack[-1][1]
    nxt = next((q for q in rest if q.kind != "table" and q.marker.kind not in {"none", "dash"}), None)
    return (nxt is not None and nxt.marker.kind == "decimal" and len(nxt.marker.value) == len(value)
            and nxt.marker.value[:-1] == value[:-1] and nxt.marker.value[-1] == value[-1] + 2)


def table_block_sections(items: list[Paragraph], body: list[Paragraph], stacks: list[tuple]) -> None:
    """Step 21 (owner 29.10.2026 «Разделу», batch 20): after a finished point («.» or «;»), a table with its own heading
    («Вещества, обладающие эффектом суммации», «Таблица 1.3.») belongs to the section: the heading lines and the
    unmarked lines after the table up to the next marker go to the enclosing named unit («II.», «Раздел 2»). The next
    heading-and-table block right after such a table goes there too, also when the point names it («приведены в таблице
    3.13», owner 29.10.2026 «Разделу» again; rule D's displaced table too). A table the point introduces with a final
    «:» stays with the point; without an enclosing unit it stays."""
    index = {id(q): k for k, q in enumerate(body)}
    seq = [q for q in items if q.flow == "body" and q.kind != "picture"]
    last_text = None  # the last body text before the current position (point or unmarked line)
    moved: tuple | None = None  # the section of the block being moved
    i = 0
    while i < len(seq):
        q = seq[i]
        if q.kind == "table":
            i += 1
            continue
        if id(q) not in index:
            i += 1
            continue
        k = index[id(q)]
        if q.marker.kind not in {"none", "dash"}:
            moved, last_text = None, q
            i += 1
            continue
        if moved is not None and not table_head(q):
            stacks[k] = moved  # a line after the moved table, before the next marker
            q.evidence.append(dict(TABLE_BLOCK_EVIDENCE))
            last_text = q
            i += 1
            continue
        end = i
        titles = set()  # step 21.6: a plain-text table title right before «Таблица N»
        while end < len(seq) and id(seq[end]) in index and (table_head(seq[end]) or table_title(seq, end)):
            if not table_head(seq[end]):
                titles.add(id(seq[end]))
            end += 1
        if end > i and end < len(seq) and seq[end].kind == "table":
            heads = seq[i:end]
            stack = stacks[k]
            unit = next((n for n in range(len(stack) - 1, -1, -1) if stack[n][0] in UNIT_RANK), None)
            # its own heading: an OCR heading line over the caption («Вещества, обладающие эффектом суммации»), or the
            # next block of a moved run; a caption line alone («Таблица 2.1. Оптимальные величины …») stays with the point
            own_heading = moved is not None or any(heading_evidence(h) or id(h) in titles
                                                   or (h.first.category == "Caption" and not TABLE_NUMBER.match(h.text.strip()))
                                                   for h in heads)
            prev = seq[i - 1] if i else None
            finished = moved is not None or (prev is not None and prev.kind != "table" and last_text is not None
                                             and final_char(formula_body(last_text.text)) in ".;")
            gap = gap_sibling(stack, heads, seq[end:])
            if gap or (unit is not None and unit + 1 < len(stack) and finished and own_heading):
                moved = stack[:-1] if gap else stack[:unit + 1]
                for h in heads:
                    stacks[index[id(h)]] = moved
                    h.evidence.append(dict(TABLE_BLOCK_EVIDENCE))
            elif moved is None:
                pass
            else:
                moved = None
            last_text = seq[end - 1]
            i = end
            continue
        last_text = q
        i += 1


def under_table_ids(items: list[Paragraph]) -> set[int]:
    """Ids of notes headings that start a table's notes: right under a table (pictures aside), a singular
    «Примечание» (step 20 C) or any notes heading followed by footnote regions (step 21.3 D, «Примечания.» over
    «¹ С – северное; …»)."""
    seq = [q for q in items if q.kind != "picture"]
    body = [q for q in seq if q.flow == "body"]
    after = {id(a): b for a, b in zip(seq, seq[1:])}
    return {id(q) for prev, q in zip(body, body[1:]) if prev.kind == "table"
            and (q.text.strip().startswith("Примечание") or getattr(after.get(id(q)), "flow", None) == "footnote")}


def between_tables(items: list[Paragraph]) -> set[int]:
    """Short unmarked caption runs between tables on one page are table fields, not positional signatures."""
    seq = [p for p in items if p.flow == "body" and p.kind != "picture"]
    framed, pending, previous = set(), [], None
    for p in seq:
        if p.kind == "table":
            if previous is not None and previous.regions[-1].page == p.first.page:
                framed.update(id(q) for q in pending)
            previous, pending = p, []
        elif p.kind == "text" and p.marker.kind == "none" and len(p.text) < 120:
            pending.append(p)
        else:
            previous, pending = None, []
    return framed


def form_signature_blocks(items: list[Paragraph]) -> set[int]:
    """Step 24 E: a name/signature block before a numbered document-receipt field signs the whole form.
    OCR can keep the name caption and blank signature boxes as separate tables."""
    seq = [p for p in items if p.flow == "body" and p.kind != "picture" and PAGE_MARK_EVIDENCE not in p.evidence]
    signatures, previous = set(), None
    for k, p in enumerate(seq):
        if p.marker.kind == "none":
            continue
        parent, previous = previous, p
        if p.marker.kind not in POINT_KINDS or not re.search(r"\b(?:при[её]м[а-яё]*|получени[а-яё]*)\s+документ", p.text):
            continue
        if parent is not None and re.search(r"\bподпис[ьи]\b", parent.text, re.IGNORECASE):
            continue  # an explicitly numbered signature position keeps its own name and signature captions
        j, signed = k - 1, False
        while j >= 0 and seq[j].first.page == p.first.page and seq[j].marker.kind == "none":
            q = seq[j]
            text = view(re.sub(r"<[^>]*>", " ", q.text))  # matching view only
            if q.kind not in {"text", "table"} or len(text) >= 120:
                break
            signed = signed or text.casefold() == "подпись"
            if signed and re.match(r"^фамилия,\s+инициалы(?:\s|$)", text, re.IGNORECASE):
                signatures.update(id(s) for s in seq[j:k])
                break
            j -= 1
    return signatures


TABLE_ROW_EVIDENCE = {"table_row": "marker between parts of the table that opens the annex; text of the annex"}
ANNEX_SCOPE = re.compile(r"(?:^|/)AN\d*$")
TABLE_DOCUMENT_SCOPE = re.compile(r"S\d*$")  # step 21.7 H: an approved text, read as a table annex when it opens with one


def table_rows(scope_path: str, items: list[Paragraph]) -> set[int]:
    """Ids of marked body paragraphs that are rows of a table annex (owner decision 23.10.2026,
    convention v2 §6). When an annex scope (`…/AN<n>`) opens with a table (no marked paragraph before
    its first table), OCR often cuts the table's rubrics («I. Подпрограмма …») and numbered rows
    («1.», «14.», «1.1») out of it as Section-header, List-item or Text regions between the table
    parts. Such a marker between the first and the last table of the annex opens no section or point:
    it is text of the annex. Named units («Раздел», «Глава», «Статья», «§») keep their meaning. An
    annex whose first marker precedes its first table keeps ordinary numbering, markers after the last
    table are unchanged unless they go on from the last row («3.» after «2.», step 16 C4). Step 21.7 H (owner 29.10.2026
    «Часть таблицы»): an approved text that is itself a table (`S`, `S2`) is read the same way, and there a first marker
    after the last table that starts no numbering («4.15. Контрольное событие 4.15. …», not «1.») is its last row."""
    if not (ANNEX_SCOPE.search(scope_path) or TABLE_DOCUMENT_SCOPE.match(scope_path)):
        return set()
    seq = [p for p in items if p.flow == "body" and p.kind not in {"picture", "approval", "annex"}]
    tables = [k for k, p in enumerate(seq) if p.kind == "table"]
    if not tables or any(p.marker.kind not in {"none", "dash"} for p in seq[:tables[0]] if p.kind != "table"):
        return set()
    if not ANNEX_SCOPE.search(scope_path) and any(p.marker.kind in UNIT_RANK for p in seq) and not numbering_gaps(
            [p.marker for p in seq[tables[0] + 1:tables[-1]] if p.kind != "table"]):
        # an approved text with sections («I. Общие сведения», Mintrud standards) is no table document; step 22 B: it
        # is one when the markers between its tables skip numbers («I.» then «III.», row «1.» then «32.», rp-22-2015):
        # the rows in between stayed inside the table cells
        return set()
    rows = [p for p in seq[tables[0] + 1:tables[-1]]
            if p.kind in {"text", "heading"} and p.marker.kind not in {"none", "dash"}
            and (p.marker.kind not in UNIT_RANK or p.marker.kind == "roman")]
    # step 16 C4: after the last table part, «3.», «4.» … that go on from the last cut-out row «2.» are rows too
    last = rows[-1].marker if rows else None
    for p in seq[tables[-1] + 1:]:
        if p.marker.kind in {"none", "dash"}:
            continue
        if not (last is not None and p.kind == "text" and p.marker.kind == last.kind == "int"
                and p.marker.value == last.value + 1):
            break
        rows.append(p)
        last = p.marker
    if not rows and TABLE_DOCUMENT_SCOPE.match(scope_path):
        first = next((p for p in seq[tables[-1] + 1:] if p.marker.kind not in {"none", "dash"}), None)
        if (first is not None and first.kind == "text" and first.marker.kind in {"int", "decimal"}
                and first.marker.value not in {1, (1,), (1, 1)}):
            rows.append(first)
    return {id(p) for p in rows}


TABLE_RUBRIC_MAX = 200
TABLE_GRID_RUBRIC = re.compile(r"<caption>\s*\d+\.\d+\.?\s")


def table_rubrics(items: list[Paragraph]) -> set[int]:
    """Step 21.7 C (sanpin-2-2021, table 5.25): a short unterminated «2. Учреждения общего образования …» printed between
    two parts of one table, numbered back from the open point (87), is the table's rubric, not a point."""
    seq = [p for p in items if p.flow == "body" and p.kind not in {"picture", "approval", "annex"}]
    rubrics, last = set(), None
    # step 21.7 D (prikaz-minzdravookhraneniya-369-2022): where OCR kept a dotted rubric inside a table's grid
    # («<caption>2.2. Хирургические … методы лечения</caption>»), the dotted «1.1. Прием …» lines it cut out right
    # above a table are rubrics of those tables too (convention v2 §6: rubrics inside a table make no points)
    if any(q.kind == "table" and TABLE_GRID_RUBRIC.search(q.text) for q in seq):
        rubrics |= {id(p) for k, p in enumerate(seq[:-1]) if p.marker.kind == "decimal" and seq[k + 1].kind == "table"
                    and len(p.text.strip()) <= TABLE_RUBRIC_MAX and not terminated(p.text.strip())}
    for k, p in enumerate(seq):
        if p.kind == "table" or p.marker.kind != "int":
            continue
        text = p.text.strip()
        between = 0 < k < len(seq) - 1 and seq[k - 1].kind == "table" and seq[k + 1].kind == "table"
        if (between and last is not None and p.marker.value <= last - 2 and len(text) <= TABLE_RUBRIC_MAX
                and not terminated(text)):
            rubrics.add(id(p))
            continue
        last = p.marker.value
    return rubrics
