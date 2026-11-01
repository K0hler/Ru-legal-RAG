"""Approving act, approved document and annex scope boundaries."""

from __future__ import annotations

import re

from .markers import (
    QUOTE_CLOSE,
    QUOTE_MAX_PARAGRAPHS,
    QUOTE_OPEN,
    parse_marker,
    self_closing,
    unbalanced_quotes,
)
from .model import (
    Paragraph,
)
from .text import (
    APPROVAL,
    APPROVE_CLAUSE,
    CAPTION_BLOCK_MAX,
    DOCUMENT_REFERENT,
    FORM_REFERENT,
    LOWERCASE_DOCUMENT_REFERENT,
    NOISE_CATEGORIES,
    PAGE_MARK_EVIDENCE,
    REPEAT_THRESHOLD,
    UNCAPTIONED_EVIDENCE,
    act_kind_of_approval,
    act_kind_of_header,
    annex_caption,
    annex_to_act,
    approval_caption,
    final_char,
    heading_evidence,
    is_caption,
    is_project_caption,
    requisite_like,
    running_caption,
    strip_sup,
)

FORM_REFERENT_STEM = 6  # «патрулирования» -> «патрул», «заявления» -> «заявле»


def form_annex_owner(reference: str, base: str, scopes: list, number: str | None) -> str | None:
    """Step 23 C: the annex of ``base`` printed last (``base/AN<k>``, or the one an annex of it was nested in) when the
    caption names a form «к акту патрулирования лесов» / «к форме заявления о выдаче …» whose next word (5+ letters) is
    in that annex's text, and its number does not go on the annexes of ``base`` (unnumbered or from 1 again; «Приложение
    2 к санитарным правилам» after «Приложение 1» is no such annex). None otherwise."""
    if not FORM_REFERENT.match(reference):
        return None
    siblings = [int(m.group(1)) for path, _ in scopes if (m := re.match(rf"^{re.escape(base)}/AN(\d+)$", path))]
    if number is not None and (not siblings or int(number) > max(siblings)):
        return None
    current = scopes[-1][0]
    m = re.match(rf"^{re.escape(base)}/AN\d*(?=/|$)", current)
    if m is None:
        return None
    owner = m.group(0)
    words = [w for w in re.findall(r"[а-яё]+", reference.lower())[2:] if len(w) >= 5]
    text = " ".join(q.text for path, members in scopes if path == owner for q in members).lower()
    return owner if words and words[0][:FORM_REFERENT_STEM] in text else None


# Step 21.5 B (prikaz-fas-553-2015): an approval sheet printed after the act's documents is a service tail of the act.
SERVICE_TAIL = re.compile(r"^Лист\s+согласования\b", re.IGNORECASE)
SERVICE_TAIL_EVIDENCE = {"service_tail": "the act's approval sheet after its documents"}


def carry_page_head(scopes: list, caption: "Paragraph") -> None:
    """Step 21.5 E: page marks at the end of the previous scope, printed on the caption's page before it (a declaration
    page head «1680 6016», «ИНН», «КПП»), belong to the scope the caption opens."""
    previous, current = scopes[-2][1], scopes[-1][1]
    moved = []
    while previous and PAGE_MARK_EVIDENCE in previous[-1].evidence and previous[-1].first.page == caption.first.page:
        moved.insert(0, previous.pop())
    current[0:0] = moved


def partition_scopes(paragraphs: list[Paragraph]) -> list[tuple[str, list[Paragraph]]]:
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
    # Cycle 11 B2: an amending quotation open in the body («… изложить в следующей редакции:» «"ПРИЛОЖЕНИЕ № 6 …»
    # … «…";»): annex captions inside it are quoted text, not annexes of the attached document.
    quote_open: int | None = None  # paragraphs since the quotation opened
    previous_text = ""
    # step 20 B: the act approved a document and was signed (page of the signature), no approved text open yet
    approves, signed_page = False, None
    service_tail = False  # step 21.5 B: «Лист согласования …» seen
    for q in paragraphs:
        if q.flow == "body" and q.kind == "text" and PAGE_MARK_EVIDENCE not in q.evidence:
            page_first.setdefault(q.first.page, q)
    for i, p in enumerate(paragraphs):
        if PAGE_MARK_EVIDENCE in p.evidence:
            scopes[-1][1].append(p)
            continue
        if service_tail:
            scopes[0][1].append(p)  # step 21.5 B: the act's approval sheet and everything after it
            if p.flow == "body":
                p.evidence.append(dict(SERVICE_TAIL_EVIDENCE))
            continue
        if p.flow == "body" and p.kind == "text" and SERVICE_TAIL.match(p.text) and len(scopes) > 1:
            service_tail = True
            scopes[0][1].append(p)
            p.evidence.append(dict(SERVICE_TAIL_EVIDENCE))
            continue
        if p.flow == "footnote" or p.kind in {"picture"}:
            scopes[-1][1].append(p)
            continue
        text = p.text
        if not approved_opened and act_kind is None and p.kind == "text":
            act_kind = act_kind_of_header(p.first.raw)
        quoted_here = False
        if p.flow == "body" and p.kind == "text" and text:
            quoted_here = quote_open is not None
            plain = strip_sup(text).rstrip()
            if quote_open is None:
                if (QUOTE_OPEN.match(text) and final_char(previous_text) == ":" and unbalanced_quotes(plain) > 0
                        and not self_closing(plain)):
                    quote_open = 0
            else:
                quote_open += 1
                if (QUOTE_CLOSE.search(plain) and unbalanced_quotes(plain) < 0) or quote_open > QUOTE_MAX_PARAGRAPHS:
                    quote_open = None
            previous_text = text
        # A running header/footer (same text on REPEAT_THRESHOLD+ regions) repeating a caption
        # of the current scope continues that scope instead of reopening it. A caption printed
        # only twice is not running: two approved texts may carry identical captions.
        running = p.first.category in NOISE_CATEGORIES and p.first.repeats >= REPEAT_THRESHOLD
        header_repeat = running and text in scope_captions
        caption_here = p.kind == "text" and not running_caption(p) and not header_repeat
        approval = caption_here and approval_caption(text) and len(text) < CAPTION_BLOCK_MAX and not text.endswith(".")
        project = caption_here and is_project_caption(text)
        if approval or project:
            p.kind = "approval"
            if approval and act_kind is None:
                act_kind = act_kind_of_approval(text)
            if project:
                p.evidence.append({"caption": "project", "rule": "standalone «Проект» opens an attached document"})
            previous = next((q for q in reversed(paragraphs[:i]) if q.flow == "body" and q.kind != "picture"
                             and PAGE_MARK_EVIDENCE not in q.evidence), None)
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
        nxt = next((q for q in paragraphs[i + 1:] if q.flow == "body" and q.kind == "text"
                    and PAGE_MARK_EVIDENCE not in q.evidence), None)
        m = annex_caption(p, nxt.text if nxt is not None else "", page_first.get(p.first.page) is p) \
            if caption_here else None
        if m:
            p.kind = "annex"
            # step 12 B2: a bare «Приложение № 2» (or one naming the act) heads the next approved document as well
            heads_approved = not approved_opened or not m.group("ref") or annex_to_act(m.group("ref"), act_kind)
            if nxt is not None and not running_caption(nxt) and (
                    (APPROVAL.match(nxt.text) and heads_approved) or is_project_caption(nxt.text)):
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
            if quoted_here and not to_act:
                p.kind = "text"  # cycle 11 B2: a caption quoted in an amendment; the act's own annex still opens
                p.evidence.append({"quoted_caption": "annex caption inside an amending quotation"})
                scopes[-1][1].append(p)
                continue
            base = approved_scope if approved_opened and not to_act else "A"
            # cycle 10 B2: a lowercase document word («к форме налоговой декларации») names the open act annex too
            nested = act_annex_document is not None and not to_act and bool(
                DOCUMENT_REFERENT.match(reference) or LOWERCASE_DOCUMENT_REFERENT.match(reference))
            if nested:
                base = act_annex_document
            # step 23 C: «Приложение 1 к акту патрулирования лесов», «Приложение к форме заявления о выдаче …» name the
            # form just printed as an annex of the attached document (its «АКТ патрулирования лесов», «ЗАЯВЛЕНИЕ о
            # выдаче …»): an annex of that annex
            owner_annex = None if to_act else form_annex_owner(reference, base, scopes, number)
            if owner_annex is not None:
                base, nested = owner_annex, True
                label = label if number else "AN1"  # the form's only annex «Приложение к форме …» is its annex 1
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
            carry_page_head(scopes, p)
            continue
        if p.flow == "body" and p.kind == "text" and scopes[-1][0] == "A" and not approved_opened and not quoted_here:
            if APPROVE_CLAUSE.match(text):
                approves = True
            elif approves and signed_page is None and requisite_like(text):
                signed_page = p.first.page
            elif approves and signed_page is not None and parse_marker(text, p.first.category).kind not in {"none", "roman"}:
                approves = False  # a point or an article after the signature: the act goes on, nothing to open
            elif (approves and signed_page is not None and p.first.page > signed_page and not is_caption(text)
                  and heading_evidence(p) and parse_marker(text, p.first.category).kind in {"none", "roman"}):
                # on a later page, before any point or article, an OCR heading («САНИТАРНЫЕ ПРАВИЛА», «I. Общие
                # положения») starts the approved text; lines before it stay in the act
                # step 20 B: one lost caption must not leave the whole approved document in the act
                approved_count += 1
                approved_opened = True
                scope = approved_scope = "S" if approved_count == 1 else f"S{approved_count}"
                act_annex_document = None
                scopes.append((scope, []))
                scope_captions = set()
                p.evidence.append(dict(UNCAPTIONED_EVIDENCE))
        scopes[-1][1].append(p)
    return scopes
