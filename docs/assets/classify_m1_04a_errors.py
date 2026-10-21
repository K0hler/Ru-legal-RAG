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

    python docs/assets/classify_m1_04a_errors.py --run <first-pass dir> --output <new json>
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
    args = parser.parse_args(argv)
    run = Path(args.run)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    rows, counts = [], {}
    for row in summary["rows"]:
        slug = row["slug"]
        info = regions(slug)
        errors = json.loads((run / "eval" / f"prototype-{slug}.json").read_text(encoding="utf-8"))["errors"]
        for error in errors:
            category, text = info[error["region"]]
            primary, secondary = classify(slug, error, requisite_kind(category, text))
            rows.append({"slug": slug, **error, "category": category, "class": primary, "secondary": secondary})
            counts.setdefault(primary, {}).setdefault(slug, 0)
            counts[primary][slug] += 1
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump({"schema_version": "m1-04a-error-classes/2", "system": "prototype code-final",
                   "variant": "strict", "convention": summary.get("convention", "all-regions"),
                   "run": str(run).replace("\\", "/"), "counts": counts, "errors": rows},
                  handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: sum(v.values()) for k, v in counts.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
