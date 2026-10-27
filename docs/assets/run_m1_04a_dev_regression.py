"""M1-04A regression runner: a prototype snapshot over the 111 development documents.

Scoring is convention v1 (Picture and running-noise regions are not scored) with the
``owner-path/2`` evaluator; ``no_section`` is the main metric. Cycle 3 (owner decision
22.10.2026): ``single_annex=True`` (``<doc>/AN`` == ``<doc>/AN1`` for a document with exactly
one annex) and ``cross_scope_v2`` (an owner in another document or annex than gold) is counted
per document. The summary also has a per-family breakdown (``FAMILIES``). Cycle 4 (owner
decision 23.10.2026, convention v2 §6): ``attached_ordinal=True`` by default (attached documents
and act annexes compared by order of appearance; ``--no-attached-ordinal`` turns it off).
The prototype is loaded from an explicit file so that a snapshot can be compared with ``code-final``.

    python docs/assets/run_m1_04a_dev_regression.py --prototype FILE --output NEW_DIR [--baseline SUMMARY]
        [--no-attached-ordinal]

Writes ``summary.json`` and ``errors.json`` into a new directory; an existing one is refused.
With ``--baseline`` (an earlier ``summary.json``) it also writes ``baseline-comparison.json``:
per document ``no_section``, ``strict`` and ``cross_scope_v2`` against the baseline. A document is
below baseline when ``no_section`` or ``strict`` fell, ``cross_scope_v2`` rose, its region count
changed or it is missing; the CLI then exits with status 1 (the track-B no-drop gate). Cycle 10:
``--frozen-families [FAMILY ...]`` (no names: every family except «приказы») also exits 1 when a document of
those families changes its error list against the baseline's ``errors.json`` (``frozen_family_changes``).
Documents: the 8 earlier development documents (``logical-v1/inputs`` + ``gold``), the 8 of
check-pool batch 1, the 9 + 9 of batches 2 (gold-v2) and 3 (gold as frozen) and the 11 of
batch 4 (gold as frozen in ``20261023-batch-04-gold-freeze``, cycle 4) and the 11 of batch 5 (gold as
frozen in ``20261023-batch-05-gold-freeze``, rp-1099 stitched from its two page-range parts, cycle 5) and
the 11 of batch 6 (gold as frozen in ``20261023-batch-06-gold-freeze``, cycle 6) and the 11 of batch 7
(gold as frozen in ``20261024-batch-07-gold-freeze``, cycle 7) and the 11 of batch 8 (``gold-forms``: the gold frozen
in ``20261025-batch-08-gold-freeze`` with convention v2 §6.1 forms merged into their annex by
``derive_m1_04a_gold_forms.py``, cycle 9) and the 11 of batch 9 (gold as frozen in
``20261026-batch-09-gold-freeze``, cycle 10) and the 11 of batch 10 (``20261026-batch-10-gold-freeze``; pp-728-2020
is the gold stitched from three page-range parts, cycle 11); all are development since their first
pass. Only gold keys are scored, so a gold that covers a
sample of regions (sanpin-3684) is scored on that sample.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "docs" / "assets"
OLD = ROOT / "data" / "m1" / "experiments" / "m1-04a-20261017-logical-v1"
POOL = ROOT / "data" / "m1" / "m1-04a"
OLD_NAMES = ("resolution-416", "sp-3597", "sanpin-3684", "resolution-1156", "sanpin-amendment-2bc8",
             "holdout2-3712bfea85ea", "holdout2-a0ee4eb3704e", "holdout2-d13680559014")
BATCH_1 = ("fz-22-2018", "fz-23-2018", "pp-1455-2022", "pp-884-2024", "prikaz-minobrazovaniya-901-2015",
           "prikaz-mintsifrovogo-173-2021", "rp-1378-2018", "ukaz-204-2016")
BATCH_2 = ("pp-667-2015", "fz-119-2016", "fz-151-2018", "fz-431-2018", "fz-433-2018", "pp-931-2022",
           "prikaz-favt-547-2023", "ukaz-919-2025", "prikaz-fsvfn-1310-2025")
BATCH_3 = ("code-21-2015", "fz-385-2016", "fz-49-2020", "pp-1967-2023", "pp-2249-2021", "prikaz-fsnson-282-2020",
           "prikaz-minkultury-1321-2016", "rp-1431-2014", "ukaz-980-2022")
BATCH_4 = ("fz-223-2015", "fz-544-2023", "fz-549-2023", "pp-1688-2021", "pp-813-2015", "prikaz-minselskogo-101-2018",
           "prikaz-mintransporta-107-2015", "prikaz-mintransporta-136-2015", "rp-2023-2020", "rp-2728-2020",
           "ukaz-481-2016")
BATCH_5 = ("rp-1099-2014", "prikaz-fsnson-1112-2022", "fz-364-2021", "ukaz-669-2016", "fz-334-2019", "fz-395-2023",
           "rp-3721-2020", "prikaz-minstroitelstva-135-2022", "prikaz-minnauki-697-2023", "pp-1759-2023",
           "pp-612-2016")
BATCH_6 = ("pp-887-2023", "fz-67-2012", "prikaz-minekonomicheskogo-37-2015", "fz-384-2019", "fz-367-2019",
           "rp-2390-2020", "rp-356-2022", "prikaz-minprosveshcheniya-211-2023", "prikaz-fns-957-2020", "pp-1438-2019",
           "ukaz-1711-2012")
BATCH_7 = ("prikaz-minenergetiki-90-2019", "fz-15-2013", "fz-410-2016", "fz-411-2016", "pp-1327-2019", "pp-1782-2025",
           "prikaz-fsetan-461-2017", "prikaz-minobrazovaniya-1126-2017", "rp-2299-2017", "rp-915-2019",
           "ukaz-410-2021")
BATCH_8 = ("fz-123-2012", "fz-125-2012", "fz-517-2022", "pp-2285-2022", "pp-48-2021", "prikaz-fas-553-2015",
           "prikaz-fsetan-494-2016", "prikaz-mintruda-141-2023", "rp-2192-2015", "rp-755-2016", "ukaz-1428-2012")
BATCH_9 = ("fz-161-2015", "fz-193-2025", "fz-488-2014", "pp-1464-2019", "pp-1521-2014", "prikaz-fns-815-2024",
           "prikaz-mintruda-553-2018", "prikaz-mintruda-687-2018", "rp-2612-2017", "rp-2738-2014", "ukaz-202-2017")
# Batch 10 without prikaz-minkultury-2782-2015 (OCR failed, refilled by prikaz-fas-690-2022).
BATCH_10 = ("fz-431-2015", "pp-1696-2023", "pp-728-2020", "prikaz-fas-1225-2015", "prikaz-fas-690-2022",
            "prikaz-minfinansov-198-2015", "prikaz-mintruda-742-2018", "prikaz-minzdravookhraneniya-369-2022",
            "rp-3053-2019", "ukaz-203-2018", "ukaz-404-2018")
METRICS = ("strict", "no_section", "numbers")
# Family = document type, from the slug prefix; the old 8 are named by content, so they are listed.
FAMILIES = ("законы", "кодексы", "постановления", "распоряжения", "приказы", "указы", "санитарные правила")
PREFIX_FAMILY = {"fz": "законы", "code": "кодексы", "pp": "постановления", "resolution": "постановления",
                 "rp": "распоряжения", "prikaz": "приказы", "ukaz": "указы", "sp": "санитарные правила",
                 "sanpin": "санитарные правила"}
# Chief sanitary doctor resolutions (approving or amending sanitary rules) count as sanitary rules.
FAMILY_OVERRIDE = {"holdout2-3712bfea85ea": "санитарные правила", "holdout2-a0ee4eb3704e": "санитарные правила",
                   "holdout2-d13680559014": "санитарные правила"}
CONVENTION = "v1"
# Higher is better for the first two, lower is better for cross_scope_v2.
COMPARED = ("no_section", "strict", "cross_scope_v2")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def family(name: str) -> str:
    if name in FAMILY_OVERRIDE:
        return FAMILY_OVERRIDE[name]
    return PREFIX_FAMILY[name.split("-", 1)[0]]


def extraction_path(slug: str) -> Path:
    (path,) = [p for p in (POOL / "ocr" / slug / "run-01" / "extractions").glob("*.json")
               if not p.name.startswith("index-")]
    return path


def development_documents() -> list[dict]:
    docs = [{"name": n, "group": "old-8", "extraction": OLD / "inputs" / f"{n}.extraction.json",
             "gold": OLD / "gold" / f"{n}.gold.txt"} for n in OLD_NAMES]
    for group, slugs, suffix in (("batch-1", BATCH_1, "gold"), ("batch-2", BATCH_2, "gold-v2"),
                                 ("batch-3", BATCH_3, "gold"), ("batch-4", BATCH_4, "gold"),
                                 ("batch-5", BATCH_5, "gold"), ("batch-6", BATCH_6, "gold"),
                                 ("batch-7", BATCH_7, "gold"), ("batch-8", BATCH_8, "gold-forms"),
                                 ("batch-9", BATCH_9, "gold"), ("batch-10", BATCH_10, "gold")):
        for slug in slugs:
            docs.append({"name": slug, "group": group, "extraction": extraction_path(slug),
                         "gold": POOL / "gold" / slug / f"agent-{slug}.{suffix}.txt"})
    return docs


def region_categories(extraction: dict) -> dict[str, str]:
    return {f'{p["page"]}.{i}': r["category"] for p in extraction["pages"] for i, r in enumerate(p["regions"])}


def recorded_path(path: Path) -> str:
    """A path as the summary records it: repo-relative with ``/`` inside the repository, else absolute."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


# Cycle 10 (owner decision 26.10.2026): rules for ministry orders must not change any owner in other families.
FROZEN_FAMILIES_DEFAULT = tuple(f for f in FAMILIES if f != "приказы")


def frozen_family_changes(rows: list[dict], errors: dict, base_errors: dict, frozen: tuple) -> list[str]:
    """Documents of a frozen family whose error list differs from the baseline's (any change, also a gain)."""
    return [r["name"] for r in rows if r["family"] in frozen and errors.get(r["name"]) != base_errors.get(r["name"])]


def compare_to_baseline(summary: dict, baseline: dict) -> dict:
    """Per-document comparison of ``summary`` with ``baseline`` on ``COMPARED``; lists the drops."""
    current = {r["name"]: r for r in summary["rows"]}
    rows, below = [], []
    for base in baseline["rows"]:
        name, row = base["name"], current.get(base["name"])
        entry = {"name": name, "family": base.get("family"), "regions": base["regions"],
                 "baseline": {m: base[m] for m in COMPARED}}
        if row is None:
            reasons = ["missing"]
        else:
            entry["current"] = {m: row[m] for m in COMPARED}
            entry["delta"] = {m: row[m] - base[m] for m in COMPARED}
            reasons = [m for m in ("no_section", "strict") if row[m] < base[m]]
            reasons += ["cross_scope_v2"] if row["cross_scope_v2"] > base["cross_scope_v2"] else []
            reasons += ["regions"] if row["regions"] != base["regions"] else []
        entry["below_baseline"] = reasons
        rows.append(entry)
        if reasons:
            below.append(name)
    added = sorted(set(current) - {b["name"] for b in baseline["rows"]})
    totals = {m: {"baseline": baseline["total"][m], "current": summary["total"][m]} for m in COMPARED}
    return {"schema_version": "m1-04a-dev-regression-comparison/1",
            "baseline_prototype_sha256": baseline.get("prototype_sha256"),
            "current_prototype_sha256": summary.get("prototype_sha256"),
            "rows": rows, "below_baseline": below, "not_in_baseline": added, "total": totals}


def run_dev_regression(prototype_path: Path, output: Path, documents: list[dict] | None = None,
                       baseline: Path | None = None, attached_ordinal: bool = True,
                       frozen_families: tuple | None = None) -> dict:
    prototype_path, output = Path(prototype_path).resolve(), Path(output)
    if output.exists():
        raise FileExistsError(f"output exists: {output}")
    base = json.loads(Path(baseline).read_text(encoding="utf-8")) if baseline is not None else None
    sys.path.insert(0, str(ROOT / "src"))
    first_pass = load("run_m1_04a_first_pass", ASSETS / "run_m1_04a_first_pass.py")
    evaluator = load("evaluate_ocr_owner_gold", ASSETS / "evaluate_ocr_owner_gold.py")
    prototype = load("m1_04a_regression_prototype", prototype_path)
    rows, errors, versions = [], {}, set()
    for doc in documents if documents is not None else development_documents():
        ext = json.loads(Path(doc["extraction"]).read_text(encoding="utf-8"))
        gold, removed = first_pass.apply_convention(evaluator.load_gold(doc["gold"]), ext, CONVENTION)
        built = prototype.build(ext)
        versions.add(built.get("parser_version"))
        owners, cont = evaluator.from_logical(built)
        result = evaluator.evaluate(gold, owners, cont, single_annex=True, attached_ordinal=attached_ordinal)
        attached, single = result["attached_count"], frozenset(result["single_annex_documents"])
        heads = None
        if attached_ordinal:
            heads = (result["attached_ordinal"]["gold"], result["attached_ordinal"]["predicted"])
        cross_v2 = sum(evaluator.cross_scope_v2(e["gold"], e["predicted"], attached, single, heads=heads)
                       for e in result["errors"])
        categories = region_categories(ext)
        row = {"name": doc["name"], "group": doc["group"], "family": doc.get("family") or family(doc["name"]),
               "regions": len(gold), "not_scored": removed, "cross_scope_v2": cross_v2}
        row.update({m: result[m]["correct"] for m in METRICS})
        rows.append(row)
        errors[doc["name"]] = [{"region": e["region"], "gold": e["gold"], "predicted": e["predicted"],
                                "category": categories.get(e["region"])} for e in result["errors"]]
    keys = ("regions", *METRICS, "cross_scope_v2")
    groups, families = {}, {}
    for r in rows:
        for table, key in ((groups, r["group"]), (families, r["family"])):
            g = table.setdefault(key, {"documents": 0, **{m: 0 for m in keys}})
            g["documents"] += 1
            for m in keys:
                g[m] += r[m]
    total = {"documents": len(rows), **{m: sum(r[m] for r in rows) for m in keys}}
    summary = {"schema_version": "m1-04a-dev-regression/1", "convention": CONVENTION,
               "prototype": recorded_path(prototype_path), "prototype_sha256": hashlib.sha256(prototype_path.read_bytes()).hexdigest(),
               "parser_version": versions.pop() if len(versions) == 1 else sorted(map(str, versions)),
               "single_annex_equivalence": True, "rows": rows, "groups": groups, "families": families,
               "total": total}
    if attached_ordinal:
        summary["attached_ordinal_equivalence"] = True
    outputs = [("summary.json", summary), ("errors.json", errors)]
    if base is not None:
        comparison = compare_to_baseline(summary, base)
        comparison["baseline"] = recorded_path(baseline)
        summary["baseline_comparison"] = {"baseline": comparison["baseline"],
                                          "below_baseline": comparison["below_baseline"]}
        if frozen_families is not None:
            base_errors = json.loads((Path(baseline).parent / "errors.json").read_text(encoding="utf-8"))
            changes = frozen_family_changes(rows, errors, base_errors, tuple(frozen_families))
            comparison["frozen_families"] = list(frozen_families)
            comparison["frozen_family_changes"] = changes
            summary["baseline_comparison"]["frozen_family_changes"] = changes
        outputs.append(("baseline-comparison.json", comparison))
    output.mkdir(parents=True)
    for name, data in outputs:
        with (output / name).open("x", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1, sort_keys=True)
    return summary


def main(argv=None, documents: list[dict] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--prototype", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, help="earlier summary.json; exit 1 if any document is below it")
    parser.add_argument("--attached-ordinal", action=argparse.BooleanOptionalAction, default=True,
                        help="attached documents and act annexes compared by order of appearance (default on)")
    parser.add_argument("--frozen-families", nargs="*", metavar="FAMILY",
                        help="with --baseline: exit 1 if a document of these families changes its error list "
                             "(no names: every family except «приказы»)")
    args = parser.parse_args(argv)
    frozen = None
    if args.frozen_families is not None:
        frozen = tuple(args.frozen_families) or FROZEN_FAMILIES_DEFAULT
    summary = run_dev_regression(args.prototype, args.output, documents=documents, baseline=args.baseline,
                                 attached_ordinal=args.attached_ordinal, frozen_families=frozen)
    print(json.dumps({"parser_version": summary["parser_version"], "groups": summary["groups"], "families": summary["families"],
                      "total": summary["total"], "baseline_comparison": summary.get("baseline_comparison")},
                     ensure_ascii=False))
    comparison = summary.get("baseline_comparison", {})
    if comparison.get("below_baseline") or comparison.get("frozen_family_changes"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
