"""M1-04A regression runner: a prototype snapshot over the 34 development documents.

Scoring is convention v1 (Picture and running-noise regions are not scored) with the
``owner-path/2`` evaluator; ``no_section`` is the main metric. Cycle 3 (owner decision
22.10.2026): ``single_annex=True`` (``<doc>/AN`` == ``<doc>/AN1`` for a document with exactly
one annex) and ``cross_scope_v2`` (an owner in another document or annex than gold) is counted
per document. The summary also has a per-family breakdown (``FAMILIES``). The prototype is loaded
from an explicit file so that a snapshot can be compared with ``code-final``.

    python docs/assets/run_m1_04a_dev_regression.py --prototype FILE --output NEW_DIR

Writes ``summary.json`` and ``errors.json`` into a new directory; an existing one is refused.
Documents: the 8 earlier development documents (``logical-v1/inputs`` + ``gold``), the 8 of
check-pool batch 1 and the 9 + 9 of batches 2 (gold-v2) and 3 (gold as frozen); all are
development since their first pass. Only gold keys are scored, so a gold that covers a
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
                                 ("batch-3", BATCH_3, "gold")):
        for slug in slugs:
            docs.append({"name": slug, "group": group, "extraction": extraction_path(slug),
                         "gold": POOL / "gold" / slug / f"agent-{slug}.{suffix}.txt"})
    return docs


def region_categories(extraction: dict) -> dict[str, str]:
    return {f'{p["page"]}.{i}': r["category"] for p in extraction["pages"] for i, r in enumerate(p["regions"])}


def run_dev_regression(prototype_path: Path, output: Path, documents: list[dict] | None = None) -> dict:
    prototype_path, output = Path(prototype_path).resolve(), Path(output)
    if output.exists():
        raise FileExistsError(f"output exists: {output}")
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
        result = evaluator.evaluate(gold, owners, cont, single_annex=True)
        attached, single = result["attached_count"], frozenset(result["single_annex_documents"])
        cross_v2 = sum(evaluator.cross_scope_v2(e["gold"], e["predicted"], attached, single)
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
               "prototype": str(prototype_path), "prototype_sha256": hashlib.sha256(prototype_path.read_bytes()).hexdigest(),
               "parser_version": versions.pop() if len(versions) == 1 else sorted(map(str, versions)),
               "single_annex_equivalence": True, "rows": rows, "groups": groups, "families": families,
               "total": total}
    output.mkdir(parents=True)
    for name, data in (("summary.json", summary), ("errors.json", errors)):
        with (output / name).open("x", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1, sort_keys=True)
    return summary


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--prototype", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    summary = run_dev_regression(args.prototype, args.output)
    print(json.dumps({"parser_version": summary["parser_version"], "groups": summary["groups"], "families": summary["families"],
                      "total": summary["total"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
