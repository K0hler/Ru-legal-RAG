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

A rescore directory (no ``freeze.json``) takes the batch from the run it was
rescored from. ``--gold-suffix gold-v2`` reads ``agent-<slug>.gold-v2.txt`` (gold
derived under annotation convention v2) for the attached-document count and must
match the gold recorded in the rescore summary; under v2 a scheme-description
list may sit in an annex of an attached document (``S/AN<n>``) as well as in ``S<k>``.

    python docs/assets/classify_m1_04a_errors.py --run <first-pass dir> --output <new json> [--system prototype-v1]
        [--gold-suffix gold-v2]
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


def classify_evidence(error: dict, category: str, text: str, single_annex: bool) -> tuple[str, list[str]]:
    """Batch 2+: reviewer's reading as rules over paths, OCR category and text (no act names)."""
    gold, predicted = error["gold"], error["predicted"]
    text = " ".join(text.split())
    if predicted is None:
        return (FOOTNOTE if category == "Footnote" else OTHER), []
    if (re.match(r"^A/AN\d+(/|$)", gold) and not single_annex
            and re.match(r"^A(/(?!AN)[^/]+)*$", predicted)):
        return LAW_ANNEX, []
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
    elif p.startswith(g + "/") and re.match(r"^S(\d*|/AN\d+)$", g):
        cause = SCHEME_LIST
    elif p.startswith(g + "/") and g in {"A", "S"}:
        cause = requisite_kind(category, text)
    elif g.startswith(p + "/") and (category == "Caption" or re.match(r"^(Таблица|Рисунок|Масштаб|Условные обозначения)\b", text)):
        cause = CAPTION_ROOT
    elif g.startswith(p + "/") and text[:1].islower():
        cause = PAGE_CONTINUATION
    else:
        cause = OTHER
    if primary is None:
        return cause, secondary
    return primary, [cause]


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
    args = parser.parse_args(argv)
    run = Path(args.run)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    if summary.get("gold", "agent-<slug>.gold.txt") != f"agent-<slug>.{args.gold_suffix}.txt":
        raise SystemExit(f"run was scored against {summary.get('gold')}, not --gold-suffix {args.gold_suffix}")
    freeze = run / "freeze.json"
    if not freeze.exists() and "rescored_from" in summary:
        freeze = ROOT / summary["rescored_from"] / "freeze.json"
    batch = json.loads(freeze.read_text(encoding="utf-8")).get("batch", "batch-01") if freeze.exists() else "batch-01"
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
        errors = json.loads((run / "eval" / f"{args.system}-{slug}.json").read_text(encoding="utf-8"))["errors"]
        attached = None
        if evaluator is not None:
            gold_path = M / "gold" / slug / f"agent-{slug}.{args.gold_suffix}.txt"
            attached = evaluator.attached_count(evaluator.load_gold(gold_path))
        for error in errors:
            category, text = info[error["region"]]
            if evaluator is None:
                primary, secondary = classify(slug, error, requisite_kind(category, text))
                extra = {}
            else:
                primary, secondary = classify_evidence(error, category, text, attached == 1)
                g = evaluator.canonical(error["gold"], attached)
                p = evaluator.canonical(error["predicted"], attached)
                extra = {"cross_scope": p is not None and evaluator.first_scope(g) != evaluator.first_scope(p)}
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
        if args.gold_suffix != "gold":
            record["gold"] = f"agent-<slug>.{args.gold_suffix}.txt"
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: sum(v.values()) for k, v in counts.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
