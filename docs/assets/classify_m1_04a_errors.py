"""Record the reviewer's error-class reading for the prototype's strict errors (M1-04A pool batch 1).

Committed port of ``experiments/20261021-batch-01-first-pass/code/classify_errors.py``
(sha256 ``74ee920f…``). The assignment was made by reading each error with its
OCR text; the rules below only write that reading down and are specific to
batch 1 (they name its acts), not a parser rule. Primary class = the cause of
the wrong owner; secondary = further causes that would remain after fixing the
primary one. Errors are taken from the **strict** variant.

Change against the local copy: the former class «Реквизиты и служебные отметки
под последней нормой» is split by region evidence into
  (a) page marks: OCR category ``Picture``/``Page-footer``/``Page-header``, a
      region without a Cyrillic word (barcode, hex certificate number, printing
      code, separator line) or an electronic-signature stamp line;
  (b) the signature block after the last norm (signer, place and date, «Верно»,
      certifying official).

Batch 2 and later (``batch`` in the run's ``freeze.json`` is not ``batch-01``):
the reading is written as evidence rules over the gold path, the predicted path,
the OCR category and the region text (``classify_evidence``); no act is named.
Classes new in batch 2 (first example in the protocol, section 6): annex of an
attached document named ``S<k>`` in gold but ``S/AN<n>`` by the prototype;
dotted point «4.1.» nested under «4.»; point continued on a new page given to
the parent; numbered list of a scheme description read as points; OCR misread
of a marker digit («б)» for «6)»). Batch-2 forms of protocol classes: unknown
scope form (law annex «Приложение N к Федеральному закону» not opened), table
owner (caption or scale line left at the annex root), amendment quote
(numbering of the quoted new wording opened parts), footnote owner (no owner). Each error
also records ``cross_scope`` (silent: owner given, in another attached-document
scope than gold, by the evaluator's ``first_scope``).

Batch 3 adds evidence rules that fire only where the batch-2 rules found no class
(batch-1/2 class files reproduce byte for byte): «РАЗДЕЛ N» of a code (also strict-only
errors whose paths differ just by the roman section), single unnumbered annex of an
attached document ``S/AN`` vs gold ``S/AN1``, annex of an attached document not opened,
unnumbered subheading inside a section given to a point, closing paragraph of a point
left in its last subpoint, and a form-field caption «(…)» left at the annex root.

Batch 4 adds evidence rules (batch-1/2/3 class files reproduce byte for byte): a second
attached document named ``S<k>`` in gold but ``A/AN`` by the prototype (new class); a numbered
work list «01.», «02.»… restarted under every table and nested under the previous one (sections
ignored; protocol class «Перезапуск нумерации»); a line between tables given to the document
root instead of its section (table owner); a page-footer code without Cyrillic words given to a
point (page mark).

Batch 5 adds two rules that fire only where the earlier rules found no class (batch-1..4 class
files reproduce byte for byte): a roman section heading «V. …» that OCR gave as plain ``Text``
opens nothing, so the heading and the points after it stay in the previous section (the heading
region itself, and errors whose paths differ only by the roman section; new class); a footnote
(``Footnote`` region or a line starting with a superscript mark) given by its mark to another
document or annex that uses the same marks (footnote owner).

A rescore directory (no ``freeze.json``) takes the batch from the run it was
rescored from. ``--gold-suffix gold-v2`` reads ``agent-<slug>.gold-v2.txt`` (gold
derived under annotation convention v2) for the attached-document count and must
match the gold recorded in the rescore summary; under v2 a scheme-description
list may sit in an annex of an attached document (``S/AN<n>``) as well as in ``S<k>``.

Cycle 3 (22.10.2026). A rescore with ``single_annex_equivalence`` in its summary
(``run_m1_04a_first_pass.py rescore --single-annex``) is classified with the same
equivalence: for a document with exactly one annex (``AN``/``AN1``) in the gold,
``<doc>/AN`` in the error's gold and predicted path is read as ``<doc>/AN1`` before
the evidence rules. Such a run, or ``--cross-scope-v2`` on any batch-2+ run, also
records ``cross_scope_v2`` per error and in total: the evaluator's ``scope_v2``
(nearest document or annex: ``A``, ``A/AN<n>``, ``S<k>``, ``S<k>/AN<n>``) differs
between gold and the given owner. The old ``cross_scope`` is computed as before.
Without either, outputs are unchanged.

Cycle 4 (23.10.2026). A rescore or run with ``attached_ordinal_equivalence`` in its summary
(``--attached-ordinal``, convention v2 §6) is classified with the ordinal names its
evaluator recorded (``attached_ordinal`` in ``eval/<system>-<slug>.json``): the error's gold
and predicted top-level scopes (``S``, ``S<k>``, ``A/AN``, ``A/AN<n>``) are renamed before the
evidence rules, and ``cross_scope_v2`` compares the renamed paths. Such a run always records
``cross_scope_v2``. Without it, outputs are unchanged.

    python docs/assets/classify_m1_04a_errors.py --run <first-pass dir> --output <new json> [--system prototype-v1]
        [--gold-suffix gold-v2] [--cross-scope-v2]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "data" / "m1" / "m1-04a"
PAGE_MARK = "Реквизиты под последней нормой: отметка страницы (картинка, штрихкод, отметка ЭП, типографский код, черта)"
SIGNATURE = "Реквизиты под последней нормой: подписной блок (подпись, место и дата, «Верно», заверение)"
ARTICLE = "Неизвестный вид маркера («Статья N»)"
SCOPE = "Неизвестная форма области (приложенный проект соглашения без грифа)"
HEADER = "Шапка приложения распознана OCR как колонтитул"
MARK_CATEGORIES = {"Picture", "Page-footer", "Page-header"}
LAW_ANNEX = "Неизвестная форма области: «Приложение N к Федеральному закону» не открывает приложение"
NESTED_ANNEX = ("Приложение к приложенному документу: в эталоне отдельный документ `S<k>`, "
                "у прототипа `S/AN<n>` (соглашение v1 не задаёт; прецедент: sanpin-3684 S/AN<n>)")
DOTTED = "Дробный номер пункта («4.1.») вложен в пункт «4.»; в эталоне — прямо в разделе"
CAPTION_ROOT = ("Владелец таблицы: подпись таблицы или рисунка («Таблица 1.1», «Масштаб», «Условные обозначения») "
                "отнесена к корню приложения")
PAGE_CONTINUATION = "Продолжение пункта на новой странице отнесено к родителю"
SCHEME_LIST = "Нумерованный перечень в описании схемы прочитан как пункты (в эталоне — не пункты)"
QUOTE = "Цитата поправки: нумерация цитируемой новой редакции (поправки) открыла части изменяющей статьи"
OCR_MARKER = "Ошибка OCR в маркере пункта («б)» вместо «6)»)"
FOOTNOTE = "Владелец сноски: сноска осталась без владельца"
SECTION_MARKER = "Неизвестный вид маркера: «РАЗДЕЛ N» кодекса не открывает раздел"
UNNUMBERED_ANNEX = ("Единственное ненумерованное приложение приложенного документа: в эталоне `S/AN1`, "
                    "у прототипа `S/AN` (соглашение v2 их не приравнивает)")
ATTACHED_ANNEX = ("Неизвестная форма области: «Приложение к Порядку» обычным текстом не открывает "
                  "приложение приложенного документа")
SUBHEADING = "Ненумерованный подзаголовок внутри раздела отнесён к пункту"
CLOSING = "Не закрыт последний подпункт: следующий абзац пункта (вывод, заключительная фраза) отнесён к подпункту"
SECOND_ATTACHED = ("Второй приложенный документ («ПРИЛОЖЕНИЕ к постановлению» после утверждённого текста): "
                   "в эталоне `S<k>`, у прототипа `A/AN` (равенство `S` = `A/AN` задано только для одного "
                   "приложенного документа)")
LIST_RESTART = ("Перезапуск нумерации: перечень «01.», «02.»… (состав работ под каждой таблицей) прочитан как "
                "пункты, и каждый следующий перечень с «01.» вложен в предыдущий")
TABLE_LINE_ROOT = ("Владелец таблицы: строка между таблицами («Стоимостные показатели») отнесена к корню "
                   "документа, а не к разделу")
SECTION_AS_TEXT = ("Заголовок раздела «V. …» распознан OCR как обычный текст (Text) и не открыл раздел: "
                   "заголовок и пункты после него остались в прежнем разделе")
FOOTNOTE_OTHER_SCOPE = ("Владелец сноски: сноска отдана по знаку («¹», «²») другому приложению или документу "
                        "с теми же знаками")
ROMAN = re.compile(r"^[IVXLC]+$")
ROMAN_HEADING = re.compile(r"^#*\s*[IVXLC]+\.\s+\S")
SUPERSCRIPT_MARK = re.compile(r"^[¹²³⁴⁵⁶⁷⁸⁹⁰*]")
SCOPE_HEAD = re.compile(r"^(A|S\d*)(/AN\d*)?(?=/|$)")
PADDED = re.compile(r"^0\d+$")
SECTION_SEGMENT = re.compile(r"^(разд\d+|[IVXLC]+)$")
MARKER_START = re.compile(r"^(\d+(\.\d+)*[.)]|[а-я]\))")
OTHER = "Не классифицировано"
CONFUSABLE = {"6": "б", "3": "з", "0": "о"}
CYRILLIC_WORD = re.compile(r"[А-Яа-яЁё]{2}")
EP_STAMP = re.compile(r"^(ДОКУМЕНТ ПОДПИСАН|Сертификат|Действителен|Владелец)", re.IGNORECASE)


def requisite_kind(category: str, text: str) -> str:
    """(a) page mark or (b) signature block, from the region's OCR category and text."""
    text = " ".join(text.split())
    if category in MARK_CATEGORIES or not CYRILLIC_WORD.search(text) or EP_STAMP.match(text):
        return PAGE_MARK
    return SIGNATURE


def classify(slug: str, error: dict, requisite: str) -> tuple[str, list[str]]:
    gold = error["gold"]
    if slug.startswith("fz-"):
        return (ARTICLE, []) if "ст" in gold else (requisite, [])
    if slug == "rp-1378-2018":
        secondary = []
        if "ст" in gold:
            secondary.append(ARTICLE)
        if error["region"] in {"5.7", "5.8"}:
            secondary.append(requisite)
        return SCOPE, secondary
    if slug == "prikaz-mintsifrovogo-173-2021" and gold.startswith("S"):
        return HEADER, []
    return requisite, []


def _canon(path: str) -> str:
    """``A/AN``/``A/AN1`` of a single-annex act -> ``S`` (as the evaluator does)."""
    return re.sub(r"^A/AN1?(?=/|$)", "S", path)


def _nested_alias(path: str) -> str:
    """``S/AN<n>/...`` -> ``S<n+1>/...``: the gold naming of an attached document's annexes."""
    m = re.match(r"^S/AN(\d+)(/.*)?$", path)
    return f"S{int(m.group(1)) + 1}{m.group(2) or ''}" if m else path


def _without_dotted_parents(path: str) -> str:
    """Drop a segment ``4`` that directly holds ``4.1`` (``II/4/4.1`` -> ``II/4.1``)."""
    seg = path.split("/")
    return "/".join(x for i, x in enumerate(seg)
                    if not (i + 1 < len(seg) and re.match(rf"^{re.escape(x)}\.\d+$", seg[i + 1])))


def _without_sections(path: str) -> str:
    return "/".join(x for x in path.split("/") if not ROMAN.match(x))


def _drops_subitem(gold: str, predicted: str) -> tuple[bool, bool]:
    """(predicted is gold plus one extra numbered/lettered segment, that holds only via dotted nesting)."""
    seg = predicted.split("/")
    for i in range(1, len(seg)):
        if not re.match(r"^(\d+|[а-я])$", seg[i]):
            continue
        candidate = "/".join(seg[:i] + seg[i + 1:])
        if candidate == gold:
            return True, False
        if _without_dotted_parents(candidate) == gold:
            return True, True
    return False, False


def _restarted_list(gold: str, predicted: str) -> bool:
    """Batch 4: predicted is gold (sections ignored) plus a chain that holds a zero-padded number («01.»)."""
    g = [x for x in gold.split("/") if not SECTION_SEGMENT.match(x)]
    p = [x for x in predicted.split("/") if not SECTION_SEGMENT.match(x)]
    return len(p) > len(g) and p[:len(g)] == g and any(PADDED.match(x) for x in p[len(g):])


def _only_section_differs(gold: str, predicted: str) -> bool:
    """Same depth, every differing segment a roman section number (``S/V/20`` vs ``S/IV/20``)."""
    g, p = gold.split("/"), predicted.split("/")
    pairs = [(x, y) for x, y in zip(g, p) if x != y]
    return len(g) == len(p) and bool(pairs) and all(ROMAN.match(x) and ROMAN.match(y) for x, y in pairs)


def _batch5_cause(gold: str, predicted: str, category: str, text: str) -> str:
    """Batch 5: classes for errors no earlier rule explains (earlier class files are unchanged)."""
    if category != "Section-header" and ROMAN.match(gold.split("/")[-1]) and ROMAN_HEADING.match(text):
        return SECTION_AS_TEXT
    if _only_section_differs(gold, predicted):
        return SECTION_AS_TEXT
    g, p = SCOPE_HEAD.match(gold), SCOPE_HEAD.match(predicted)
    if ((category == "Footnote" or SUPERSCRIPT_MARK.match(text)) and g and p
            and g.group(0) != p.group(0) and gold == g.group(0)):
        return FOOTNOTE_OTHER_SCOPE
    return OTHER


def classify_evidence(error: dict, category: str, text: str, single_annex: bool) -> tuple[str, list[str]]:
    """Batch 2+: reviewer's reading as rules over paths, OCR category and text (no act names).

    Batch-3 forms (rules apply only where the batch-2 rules found no class; batch-2 class files
    reproduce byte for byte): «РАЗДЕЛ N» of a code (header or a path that differs only by
    the roman section), unnumbered single annex of an attached document ``S/AN`` vs ``S/AN1``,
    annex of an attached document not opened, unnumbered subheading inside a section given to a
    point, closing paragraph of a point given to its last subpoint."""
    gold, predicted = error["gold"], error["predicted"]
    text = " ".join(text.split())
    if predicted is None:
        return (FOOTNOTE if category == "Footnote" else OTHER), []
    if (any(ROMAN.match(x) for x in gold.split("/")) and not any(ROMAN.match(x) for x in predicted.split("/"))
            and (_without_sections(gold) == predicted
                 or (ROMAN.match(gold.split("/")[-1]) and re.match(r"^#*\s*РАЗДЕЛ\s+\S+", text)))):
        return SECTION_MARKER, []
    if re.match(r"^S\d*/AN1(/|$)", gold) and re.sub(r"^(S\d*/AN)1(?=/|$)", r"\1", gold) == predicted:
        return UNNUMBERED_ANNEX, []
    if re.match(r"^S\d*/AN\d+(/|$)", gold) and not any(x.startswith("AN") for x in predicted.split("/")):
        return ATTACHED_ANNEX, []
    if (re.match(r"^A/AN\d+(/|$)", gold) and not single_annex
            and re.match(r"^A(/(?!AN)[^/]+)*$", predicted)):
        return LAW_ANNEX, []
    second = re.match(r"^S\d+(/.*)?$", gold)
    if second and re.match(r"^A/AN\d*(/|$)", predicted) and re.sub(r"^A/AN\d*", "", predicted) == (second.group(1) or ""):
        return SECOND_ATTACHED, []
    secondary: list[str] = []
    primary = None
    g = _canon(gold) if single_annex else gold
    p = _canon(predicted) if single_annex else predicted
    if re.match(r"^S\d+(/|$)", g) and p.startswith("S/AN"):
        primary, p = NESTED_ANNEX, _nested_alias(p)
        if p == g:
            return primary, []
    g_seg, p_seg = g.split("/"), p.split("/")
    if any(s.startswith("ст") for s in g_seg) and not any(s.startswith("ст") for s in p_seg):
        cause = ARTICLE
    elif g_seg[-1] in CONFUSABLE and CONFUSABLE[g_seg[-1]] in p_seg:
        cause = OCR_MARKER
    elif any(s.startswith("ст") for s in g_seg) and p.startswith(g + "/ч"):
        cause = QUOTE
    elif _without_dotted_parents(p) == g:
        cause = DOTTED
    elif p.startswith(g + "/") and text.startswith("(") and re.search(r"подпис|фамилия|должност", text):
        cause = SIGNATURE
    elif p.startswith(g + "/") and category in MARK_CATEGORIES and not CYRILLIC_WORD.search(text):
        cause = PAGE_MARK  # batch 4: a typographic file code «200716A9.doc» in a page footer
    elif p.startswith(g + "/") and re.match(r"^S(\d*|/AN\d+)$", g):
        cause = SCHEME_LIST
    elif p.startswith(g + "/") and g in {"A", "S"}:
        cause = requisite_kind(category, text)
    elif g.startswith(p + "/") and (category == "Caption" or re.match(r"^(Таблица|Рисунок|Масштаб|Условные обозначения)\b", text)):
        cause = CAPTION_ROOT
    elif g.startswith(p + "/") and text[:1].islower():
        cause = PAGE_CONTINUATION
    elif p.startswith(g + "/") and ROMAN.match(g_seg[-1]) and not MARKER_START.match(text):
        cause = SUBHEADING
    elif g.startswith(p + "/") and text.startswith("("):
        cause = CAPTION_ROOT  # caption of a form field, e.g. «(серия, номер, дата выдачи)»
    elif _restarted_list(g, p):
        cause = LIST_RESTART
        if any(s.startswith("разд") for s in g_seg) and not any(s.startswith("разд") for s in p_seg):
            secondary.append(SECTION_MARKER)
    elif _drops_subitem(g, p)[0]:
        cause = CLOSING
        if _drops_subitem(g, p)[1]:
            secondary.append(DOTTED)
    elif (g.startswith(p + "/") and all(SECTION_SEGMENT.match(x) for x in g[len(p) + 1:].split("/"))
          and not MARKER_START.match(text)):
        cause = TABLE_LINE_ROOT
    else:
        cause = _batch5_cause(g, p, category, text)
    if primary is None:
        return cause, secondary
    return primary, [cause]


def read_paths(evaluator, error: dict, single: frozenset, heads: tuple[dict, dict] | None,
               attached: int | None = None) -> dict:
    """The error as the evidence rules read it: single annex numbered, ordinal heads renamed.

    The heads are keyed by canonical paths (``attached_ordinal_heads``), so under heads each path
    is first made canonical (``A/AN1`` -> ``S`` with one attached document) and then renamed."""
    if not single and heads is None:
        return error
    gold, predicted = error["gold"], error["predicted"]
    if heads is not None:
        gold = evaluator.rename_head(evaluator.canonical(gold, attached, single), heads[0])
        predicted = evaluator.rename_head(evaluator.canonical(predicted, attached, single), heads[1])
    else:
        gold = evaluator.number_single_annex(gold, single)
        predicted = None if predicted is None else evaluator.number_single_annex(predicted, single)
    return {**error, "gold": gold, "predicted": predicted}


def cross_scope(evaluator, error: dict, attached: int, single: frozenset,
                heads: tuple[dict, dict] | None = None) -> bool:
    """``cross_scope_v2`` of one error (with the run's ordinal heads, if any)."""
    return evaluator.cross_scope_v2(error["gold"], error["predicted"], attached, single, heads=heads)


def regions(slug: str) -> dict[str, tuple[str, str]]:
    (path,) = [p for p in (M / "ocr" / slug / "run-01" / "extractions").glob("*.json")
               if not p.name.startswith("index-")]
    ext = json.loads(path.read_text(encoding="utf-8"))
    text: dict[str, str] = {}
    for block in ext["blocks"]:
        text[block["source_region_id"]] = text.get(block["source_region_id"], "") + block["display_text"]
    return {f'{p["page"]}.{i}': (r["category"], text.get(r["region_id"], ""))
            for p in ext["pages"] for i, r in enumerate(p["regions"])}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--run", required=True, help="first-pass directory with summary.json and eval/")
    parser.add_argument("--output", required=True, help="new JSON file")
    parser.add_argument("--system", default="prototype", help="eval prefix, e.g. prototype-v1 (batch 2+)")
    parser.add_argument("--gold-suffix", default="gold", help="gold file agent-<slug>.<suffix>.txt, e.g. gold-v2")
    parser.add_argument("--cross-scope-v2", action="store_true",
                        help="also record cross_scope_v2 (implied by a --single-annex or --attached-ordinal run)")
    args = parser.parse_args(argv)
    run = Path(args.run)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    if summary.get("gold", "agent-<slug>.gold.txt") != f"agent-<slug>.{args.gold_suffix}.txt":
        raise SystemExit(f"run was scored against {summary.get('gold')}, not --gold-suffix {args.gold_suffix}")
    freeze = run / "freeze.json"
    if not freeze.exists() and "rescored_from" in summary:
        freeze = ROOT / summary["rescored_from"] / "freeze.json"
    batch = json.loads(freeze.read_text(encoding="utf-8")).get("batch", "batch-01") if freeze.exists() else "batch-01"
    single_annex = summary.get("single_annex_equivalence", False)
    ordinal = summary.get("attached_ordinal_equivalence", False)
    scope_v2 = single_annex or ordinal or args.cross_scope_v2 or batch not in ("batch-01", "batch-02", "batch-03")
    evaluator = None
    if batch != "batch-01":
        import importlib.util

        spec = importlib.util.spec_from_file_location("m1_04a_classify_evaluator",
                                                      ROOT / "docs" / "assets" / "evaluate_ocr_owner_gold.py")
        evaluator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(evaluator)
    rows, counts = [], {}
    for row in summary["rows"]:
        slug = row["slug"]
        info = regions(slug)
        result = json.loads((run / "eval" / f"{args.system}-{slug}.json").read_text(encoding="utf-8"))
        errors = result["errors"]
        heads = None
        if ordinal:
            heads = (result["attached_ordinal"]["gold"], result["attached_ordinal"]["predicted"])
        attached, single = None, frozenset()
        if evaluator is not None:
            gold_path = M / "gold" / slug / f"agent-{slug}.{args.gold_suffix}.txt"
            gold_map = evaluator.load_gold(gold_path)
            attached = evaluator.attached_count(gold_map)
            if single_annex:
                single = evaluator.single_annex_documents(gold_map)
        for error in errors:
            category, text = info[error["region"]]
            if evaluator is None:
                primary, secondary = classify(slug, error, requisite_kind(category, text))
                extra = {}
            else:
                read = read_paths(evaluator, error, single, heads, attached)
                primary, secondary = classify_evidence(read, category, text, attached == 1)
                g = evaluator.canonical(error["gold"], attached)
                p = evaluator.canonical(error["predicted"], attached)
                extra = {"cross_scope": p is not None and evaluator.first_scope(g) != evaluator.first_scope(p)}
                if scope_v2:
                    extra["cross_scope_v2"] = cross_scope(evaluator, error, attached, single, heads)
            rows.append({"slug": slug, **error, "category": category, "class": primary, "secondary": secondary,
                         **extra})
            counts.setdefault(primary, {}).setdefault(slug, 0)
            counts[primary][slug] += 1
    record = {"schema_version": "m1-04a-error-classes/2", "system": "prototype code-final",
              "variant": "strict", "convention": summary.get("convention", "all-regions"),
              "run": str(run).replace("\\", "/"), "counts": counts, "errors": rows}
    if evaluator is not None:
        record.update({"schema_version": "m1-04a-error-classes/3", "system": args.system, "batch": batch,
                       "cross_scope": sum(1 for r in rows if r["cross_scope"])})
        if scope_v2:
            record["cross_scope_v2"] = sum(1 for r in rows if r["cross_scope_v2"])
        if single_annex:
            record["single_annex_equivalence"] = True
        if ordinal:
            record["attached_ordinal_equivalence"] = True
        if args.gold_suffix != "gold":
            record["gold"] = f"agent-<slug>.{args.gold_suffix}.txt"
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: sum(v.values()) for k, v in counts.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
