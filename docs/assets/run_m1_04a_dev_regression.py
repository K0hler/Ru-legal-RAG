"""M1-04A regression runner: a prototype snapshot over the 16 development documents.

Scoring is convention v1 (Picture and running-noise regions are not scored) with the
``owner-path/2`` evaluator; ``no_section`` is the main metric. The prototype is loaded
from an explicit file so that a snapshot can be compared with ``code-final``.

    python docs/assets/run_m1_04a_dev_regression.py --prototype FILE --output NEW_DIR

Writes ``summary.json`` and ``errors.json`` into a new directory; an existing one is refused.
Documents: the 8 earlier development documents (``logical-v1/inputs`` + ``gold``) and the
8 documents of check-pool batch 1 (development since its first pass). Only gold keys are
scored, so a gold that covers a sample of regions (sanpin-3684) is scored on that sample.
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
METRICS = ("strict", "no_section", "numbers")
CONVENTION = "v1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def development_documents() -> list[dict]:
    docs = [{"name": n, "group": "old-8", "extraction": OLD / "inputs" / f"{n}.extraction.json",
             "gold": OLD / "gold" / f"{n}.gold.txt"} for n in OLD_NAMES]
    for slug in BATCH_1:
        (path,) = [p for p in (POOL / "ocr" / slug / "run-01" / "extractions").glob("*.json")
                   if not p.name.startswith("index-")]
        docs.append({"name": slug, "group": "batch-1", "extraction": path,
                     "gold": POOL / "gold" / slug / f"agent-{slug}.gold.txt"})
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
        result = evaluator.evaluate(gold, owners, cont)
        categories = region_categories(ext)
        row = {"name": doc["name"], "group": doc["group"], "regions": len(gold), "not_scored": removed}
        row.update({m: result[m]["correct"] for m in METRICS})
        rows.append(row)
        errors[doc["name"]] = [{"region": e["region"], "gold": e["gold"], "predicted": e["predicted"],
                                "category": categories.get(e["region"])} for e in result["errors"]]
    groups = {}
    for r in rows:
        g = groups.setdefault(r["group"], {"regions": 0, **{m: 0 for m in METRICS}})
        g["regions"] += r["regions"]
        for m in METRICS:
            g[m] += r[m]
    total = {"regions": sum(r["regions"] for r in rows), **{m: sum(r[m] for r in rows) for m in METRICS}}
    summary = {"schema_version": "m1-04a-dev-regression/1", "convention": CONVENTION,
               "prototype": str(prototype_path), "prototype_sha256": hashlib.sha256(prototype_path.read_bytes()).hexdigest(),
               "parser_version": versions.pop() if len(versions) == 1 else sorted(map(str, versions)),
               "rows": rows, "groups": groups, "total": total}
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
    print(json.dumps({"parser_version": summary["parser_version"], "groups": summary["groups"],
                      "total": summary["total"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
