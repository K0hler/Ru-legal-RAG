"""Sample estimate of which IPS acts have an official structure tree, by act type and decade (owner request 28.10.2026).

The federal IPS base (c000000000) is listed in full per act type, then a seeded random sample is drawn inside every
stratum «type × organ × decade» so that each stratum's share has a 95% margin of at most 10 percentage points
(finite-population corrected; small strata are checked in full). A sampled act has a tree when the
`document_content` of its actual edition returns at least one structure node; `has_text` comes from the card's
redaction list. Shares per stratum carry a Wilson interval; a type's share is weighted by the exact stratum sizes
of the listing. Ministry orders and SanPiN are not in this base; regional acts are out of scope.

Phases (run in order from the repository root; every file is written once, `screen` resumes where it stopped):

  frame     search_counter + every search page for each type -> frame/<type>.json
  plan      strata and the seeded sample from the frame -> sample.json
  screen    card + document_content per sampled act (cached 25-26.10 screens reused) -> screened/<nd>.json
  estimate  per-stratum and per-type shares -> estimate.json, coverage.md

    python docs/assets/survey_ips_tree_coverage.py <phase> --out data/m1/m1-04a/experiments/20261028-ips-tree-coverage
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acquire_m1_04a_json_corpus as corpus  # noqa: E402  (shared IPS client, pause and write-once)

SEED = 20261028
MARGIN = 0.10
Z = 1.96
# Act types of the IPS type list as the owner saw it on ips.pravo.gov.ru (28.10.2026).
TYPES = (
    "Декларация", "Договор", "Доктрина", "Женевский акт", "Заключение", "Закон",
    "Закон Российской Федерации о поправке к Конституции Российской Федерации", "Заявление", "Кодекс", "Конвенция",
    "Конституция", "Марракешский договор", "Обращение", "Определение", "Основы законодательства",
    "Официальное разъяснение", "Официальное сообщение", "Послание", "Постановление", "Протокол",
    "Рамочное соглашение", "Распоряжение", "Регламент", "Резолюция", "Решение", "Совместное постановление",
    "Соглашение", "Сообщение", "Указ", "Федеральный закон", "Федеральный конституционный закон",
    "Федеративный договор",
)
# Issuing body groups read from the start of `adoption` after the type ("Постановление Правительства ...").
ORGANS = (
    ("Правительство", re.compile(r"^(Правительства|Совета Министров)")),
    ("Президент", re.compile(r"^Президента")),
    ("Государственная Дума", re.compile(r"^Государственной Думы")),
    ("Совет Федерации", re.compile(r"^Совета Федерации")),
    ("Конституционный Суд", re.compile(r"^Конституционного Суда")),
)
OTHER_ORGAN = "прочие"
# An organ group smaller than this inside a type is merged into «прочие» to keep strata meaningful.
MIN_ORGAN_GROUP = 200


def slug(text: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", "-", text.lower()).strip("-")


def organ_group(act_type: str, adoption: str) -> str:
    rest = adoption[len(act_type):].strip() if adoption.startswith(act_type) else adoption
    for name, pattern in ORGANS:
        if pattern.match(rest):
            return name
    return OTHER_ORGAN


def decade(docdate: str) -> str:
    year = int(docdate[-4:]) if re.fullmatch(r"\d\d\.\d\d\.\d{4}", docdate or "") else None
    if year is None:
        return "без даты"
    return "до 1990" if year < 1990 else f"{year // 10 * 10}-е"


def required_n(population: int, margin: float = MARGIN, z: float = Z) -> int:
    """Worst-case (p = 0.5) sample size for a 95% margin, with the finite-population correction."""
    if population <= 0:
        return 0
    n0 = z * z * 0.25 / (margin * margin)
    return min(population, math.ceil(n0 / (1 + (n0 - 1) / population)))


def strata(frame: dict) -> dict:
    """{type: [docs]} -> {(type, organ, decade): [docs]}; small organ groups merged into «прочие»."""
    out = defaultdict(list)
    for act_type, docs in frame.items():
        sizes = defaultdict(int)
        for d in docs:
            sizes[organ_group(act_type, d["adoption"])] += 1
        for d in docs:
            organ = organ_group(act_type, d["adoption"])
            if sizes[organ] < MIN_ORGAN_GROUP and organ != OTHER_ORGAN:
                organ = OTHER_ORGAN
            out[(act_type, organ, decade(d["docdate"]))].append(d)
    return dict(out)


def plan_sample(frame: dict, seed: int = SEED, margin: float = MARGIN) -> list[dict]:
    """Seeded sample: per stratum (sorted keys), docs sorted by nd, `required_n` of them drawn without replacement."""
    rng = random.Random(seed)
    rows = []
    groups = strata(frame)
    for key in sorted(groups):
        docs = sorted(groups[key], key=lambda d: d["nd"])
        n = required_n(len(docs), margin)
        picked = docs if n == len(docs) else rng.sample(docs, n)
        rows.append({"type": key[0], "organ": key[1], "decade": key[2], "population": len(docs), "n": n,
                     "census": n == len(docs), "docs": sorted(picked, key=lambda d: d["nd"])})
    return rows


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def stratified(cells: list[dict], z: float = Z) -> dict:
    """Weighted share over strata {population, n, k}; variance with the Agresti-Coull share so that 0/n and n/n
    strata still count, and the finite-population correction (a census stratum adds none)."""
    total = sum(c["population"] for c in cells)
    if not total:
        return {"population": 0, "share": None, "low": None, "high": None}
    share, var = 0.0, 0.0
    for c in cells:
        w = c["population"] / total
        if c["n"] == 0:
            continue
        share += w * c["k"] / c["n"]
        p = (c["k"] + 2) / (c["n"] + 4)
        fpc = 1 - c["n"] / c["population"] if c["population"] else 0.0
        var += w * w * p * (1 - p) / c["n"] * fpc
    half = z * math.sqrt(var)
    return {"population": total, "share": share, "low": max(0.0, share - half), "high": min(1.0, share + half)}


def screen_record(card: dict, content: dict) -> dict:
    """What one act tells: actual edition, text present, structure nodes and depth."""
    rdk = card.get("actualrdk")
    reds = card.get("redactions") or []
    actual = next((r for r in reds if str(r.get("id")) == str(rdk)), None)
    nodes = content.get("data") if isinstance(content.get("data"), list) else []
    return {"rdk": rdk, "has_text": bool(actual and actual.get("hascontent")), "nodes": len(nodes),
            "depth": max((n.get("lvl", 0) for n in nodes), default=-1) + 1, "message": content.get("message")}


# ------------------------------------------------------------------ phases (network: frame, screen)


def phase_frame(root: Path) -> None:
    client = corpus.Client(root / "requests.jsonl")
    for act_type in TYPES:
        out = root / "frame" / f"{slug(act_type)}.json"
        if out.exists():
            continue
        total, _ = corpus.count(client, {"type": act_type})
        docs, seen, page, pages = [], set(), 1, max(1, math.ceil(total / corpus.PAGE_LIMIT))
        while page <= pages:
            found, record = corpus.search(client, {"type": act_type}, page)
            if not found:
                break
            for d in found:
                if d.get("baseid") == corpus.BASE_ID and d["nd"] not in seen:
                    seen.add(d["nd"])
                    docs.append({k: d.get(k) for k in ("hash", "nd", "docdate", "adoption", "name", "state")})
            page += 1
        corpus.write_once(out, {"type": act_type, "total": total, "pages_read": page - 1, "listed": len(docs),
                                "listed_at": corpus.now(), "docs": docs})
        print(act_type, "total", total, "listed", len(docs), flush=True)


def load_frame(root: Path) -> dict:
    return {json.loads(f.read_text(encoding="utf-8"))["type"]: json.loads(f.read_text(encoding="utf-8"))["docs"]
            for f in sorted((root / "frame").glob("*.json"))}


def phase_plan(root: Path) -> None:
    rows = plan_sample(load_frame(root))
    corpus.write_once(root / "sample.json", {"schema_version": "ips-tree-coverage-sample/1", "seed": SEED,
                                             "margin": MARGIN, "z": Z, "min_organ_group": MIN_ORGAN_GROUP,
                                             "strata": rows})
    print("strata", len(rows), "acts", sum(r["n"] for r in rows), "census strata", sum(r["census"] for r in rows))


CACHED_SCREENS = [corpus.CORPORA / "20261025-v1" / "screen", corpus.CORPORA / "20261026-v2" / "screen"]


def cached(nd: str):
    for base in CACHED_SCREENS:
        folder = base / nd
        if (folder / "card.json").exists() and (folder / "document_content.json").exists():
            return (json.loads((folder / "card.json").read_text(encoding="utf-8")),
                    json.loads((folder / "document_content.json").read_text(encoding="utf-8")), str(folder))
    return None


def phase_screen(root: Path) -> None:
    sample = json.loads((root / "sample.json").read_text(encoding="utf-8"))
    client = corpus.Client(root / "requests.jsonl")
    done = 0
    for stratum in sample["strata"]:
        for d in stratum["docs"]:
            out = root / "screened" / f"{d['nd']}.json"
            if out.exists():
                continue
            hit = cached(d["nd"])
            try:
                if hit:
                    card, content, source = hit
                else:
                    card_raw, _ = client.request("document_card.json", {"hash": d["hash"]})
                    card = json.loads(card_raw.decode("utf-8"))
                    content_raw, _ = client.request("document_content",
                                                    {"nd": card["nd"], "rdk": card["actualrdk"], "bpa": card["baseid"]})
                    content, source = json.loads(content_raw.decode("utf-8")), "request"
                record = {**screen_record(card, content), "source": source}
            except Exception as error:  # recorded, not retried silently; a later run skips it too
                record = {"error": f"{type(error).__name__}: {error}", "source": "request"}
            corpus.write_once(out, {"nd": d["nd"], "screened_at": corpus.now(), **record})
            done += 1
            if done % 100 == 0:
                print("screened", done, flush=True)
    print("screened", done, flush=True)


def phase_estimate(root: Path) -> None:
    sample = json.loads((root / "sample.json").read_text(encoding="utf-8"))
    cells = []
    for s in sample["strata"]:
        results = [json.loads((root / "screened" / f"{d['nd']}.json").read_text(encoding="utf-8"))
                   for d in s["docs"]]
        ok = [r for r in results if "error" not in r]
        k, t = sum(r["nodes"] > 0 for r in ok), sum(r["has_text"] for r in ok)
        low, high = wilson(k, len(ok))
        cells.append({"type": s["type"], "organ": s["organ"], "decade": s["decade"], "population": s["population"],
                      "n": len(ok), "errors": len(results) - len(ok), "census": s["census"], "k": k,
                      "with_text": t, "share": k / len(ok) if ok else None, "low": low, "high": high})
    by_type = defaultdict(list)
    for c in cells:
        by_type[(c["type"], c["organ"])].append(c)
    types = [{"type": t, "organ": o, **stratified(cs), "n": sum(c["n"] for c in cs), "k": sum(c["k"] for c in cs)}
             for (t, o), cs in sorted(by_type.items())]
    corpus.write_once(root / "estimate.json", {"schema_version": "ips-tree-coverage-estimate/1", "cells": cells,
                                               "types": types})
    pct = lambda x: "—" if x is None else f"{100 * x:.0f}%"  # noqa: E731
    lines = ["| Вид | Орган | Актов в IPS | Проверено | С деревом | 95% интервал |", "|---|---|---:|---:|---:|---|"]
    for r in sorted(types, key=lambda r: -r["population"]):
        lines.append(f"| {r['type']} | {r['organ']} | {r['population']} | {r['n']} | {pct(r['share'])} | "
                     f"{pct(r['low'])}–{pct(r['high'])} |")
    lines += ["", "| Вид | Орган | Десятилетие | Актов | Проверено | С деревом | С текстом | 95% интервал |",
              "|---|---|---|---:|---:|---:|---:|---|"]
    for c in cells:
        lines.append(f"| {c['type']} | {c['organ']} | {c['decade']} | {c['population']} | {c['n']} | {c['k']} | "
                     f"{c['with_text']} | {pct(c['low'])}–{pct(c['high'])} |")
    with (root / "coverage.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    print("\n".join(lines[:2 + len(types)]))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("phase", choices=("frame", "plan", "screen", "estimate"))
    parser.add_argument("--out", required=True, type=Path, help="experiment directory")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    {"frame": phase_frame, "plan": phase_plan, "screen": phase_screen, "estimate": phase_estimate}[args.phase](args.out)


if __name__ == "__main__":
    main()
