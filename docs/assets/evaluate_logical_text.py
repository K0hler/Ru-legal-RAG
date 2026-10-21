"""Compare ``logical-text/1`` with the M1-04A prototype and score stage-2 metrics.

For every ``<name>.extraction.json`` in ``--inputs`` (gold ``<name>.gold.txt`` in
``--gold``):

parity       region roles and region grouping into paragraphs versus the
             prototype ``ocr_logical_structure.logical_paragraphs``. Differing
             groups that share regions form one difference, labelled ``D1``
             (the prototype joins across a missing physical page), ``D2`` (an
             empty-text content region is involved) or ``unexpected``. Every
             role difference is ``unexpected``.
continuation a region is a continuation when it is not the first fragment of
             its paragraph; scored over gold regions against the gold ``+``.
false_exclusion   gold region whose role is ``noise``.
missed_exclusion  Page-header/Page-footer outside the gold, role ``content``
                  and no caption.

Writes ``summary.json`` into a new ``--output`` directory (an existing one is
refused). Exit code 1 when any difference is ``unexpected``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from legal_rag.corpus.logical_text import (  # noqa: E402
    NOISE_CATEGORIES,
    build_logical_text,
    classify_regions,
    is_caption,
)


def load_script(name: str):
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve their module during class creation
    spec.loader.exec_module(module)
    return module


PROTOTYPE = load_script("ocr_logical_structure")
GOLD = load_script("evaluate_ocr_owner_gold")


def label_component(prototype: list[tuple], ours: list[tuple], empty: set, page_of: dict) -> str:
    """Label one connected set of differing groups (tuples of region ids)."""
    if any(rid in empty for group in prototype + ours for rid in group):
        return "D2"
    for group in prototype:
        if any(page_of[b] - page_of[a] > 1 for a, b in zip(group, group[1:])):
            return "D1"
    return "unexpected"


def grouping_diffs(prototype: list[tuple], ours: list[tuple], empty: set, page_of: dict) -> list[dict]:
    only_p = [g for g in prototype if g not in set(ours)]
    only_o = [g for g in ours if g not in set(prototype)]
    diffs, pending = [], [("p", g) for g in only_p] + [("o", g) for g in only_o]
    while pending:
        component = [pending.pop(0)]
        seen = set(component[0][1])
        grew = True
        while grew:
            grew = False
            for item in list(pending):
                if seen & set(item[1]):
                    pending.remove(item)
                    component.append(item)
                    seen |= set(item[1])
                    grew = True
        p = [g for side, g in component if side == "p"]
        o = [g for side, g in component if side == "o"]
        diffs.append({"kind": "grouping", "label": label_component(p, o, empty, page_of),
                      "prototype": [list(g) for g in p], "ours": [list(g) for g in o]})
    return diffs


def evaluate_document(extraction: dict, gold: dict) -> dict:
    result = build_logical_text(extraction)
    proto_regions = PROTOTYPE.load_regions(extraction)
    proto_groups = [tuple(r.region_id for r in p.regions) for p in PROTOTYPE.logical_paragraphs(proto_regions)]
    our_groups = [tuple(f["region_id"] for f in p["fragments"]) for p in result["paragraphs"]]
    page_of = {r["region_id"]: r["page"] for r in result["regions"]}
    empty = {f["region_id"] for p in result["paragraphs"] if p["kind"] == "empty" for f in p["fragments"]}

    diffs = [{"kind": "role", "label": "unexpected", "region_id": r["region_id"],
              "prototype": pr.role, "ours": r["role"]}
             for r, pr in zip(result["regions"], proto_regions) if r["role"] != pr.role]
    diffs += grouping_diffs(proto_groups, our_groups, empty, page_of)

    key = {r["region_id"]: f"{r['page']}.{r['index']}" for r in result["regions"]}
    continued = {key[f["region_id"]] for p in result["paragraphs"] for f in p["fragments"][1:]}
    regions = {key[r["region_id"]]: r for r in result["regions"]}
    missing = sorted(set(gold) - set(regions))
    if missing:
        raise ValueError(f"gold regions absent from the extraction: {missing}")
    continuation = {
        "tp": sum(1 for k, g in gold.items() if g["continuation"] and k in continued),
        "fp": sum(1 for k, g in gold.items() if not g["continuation"] and k in continued),
        "fn": sum(1 for k, g in gold.items() if g["continuation"] and k not in continued),
    }
    texts = {r["region_id"]: r["match_text"] for r in classify_regions(extraction)}
    false_exclusion = sorted(k for k in gold if regions[k]["role"] == "noise")
    missed_exclusion = sorted(k for k, r in regions.items()
                              if k not in gold and r["category"] in NOISE_CATEGORIES and r["role"] == "content"
                              and is_caption(texts[r["region_id"]]) is None)
    joins = {}
    for p in result["paragraphs"]:
        for f in p["fragments"][1:]:
            joins[f["join"]] = joins.get(f["join"], 0) + 1
    return {
        "extraction_id": extraction.get("extraction_id"), "logical_text_id": result["logical_text_id"],
        "regions": len(result["regions"]), "gold_regions": len(gold), "paragraphs": len(result["paragraphs"]),
        "prototype_paragraphs": len(proto_groups),
        "empty_paragraphs": sum(1 for p in result["paragraphs"] if p["kind"] == "empty"),
        "roles": {role: sum(1 for r in result["regions"] if r["role"] == role)
                  for role in ("content", "noise", "picture", "table")},
        "joins": dict(sorted(joins.items())), "continuation": continuation,
        "false_exclusion": len(false_exclusion), "false_exclusion_regions": false_exclusion,
        "missed_exclusion": len(missed_exclusion), "missed_exclusion_regions": missed_exclusion,
        "diffs": diffs,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error(f"refusing to write into existing output {args.output}")
    inputs = sorted(args.inputs.glob("*.extraction.json"))
    if not inputs:
        parser.error(f"no *.extraction.json in {args.inputs}")
    documents = []
    for path in inputs:
        name = path.name[: -len(".extraction.json")]
        extraction = json.loads(path.read_text(encoding="utf-8"))
        gold = GOLD.load_gold(args.gold / f"{name}.gold.txt")
        documents.append({"name": name, **evaluate_document(extraction, gold)})
    summary = {
        "schema_version": "logical-text-evaluation/1",
        "documents": documents,
        "continuation": {m: sum(d["continuation"][m] for d in documents) for m in ("tp", "fp", "fn")},
        "false_exclusion": sum(d["false_exclusion"] for d in documents),
        "missed_exclusion": sum(d["missed_exclusion"] for d in documents),
        "parity": {label: sum(1 for d in documents for x in d["diffs"] if x["label"] == label)
                   for label in ("D1", "D2", "unexpected")},
    }
    args.output.mkdir(parents=True)
    with open(args.output / "summary.json", "x", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: summary[k] for k in ("continuation", "false_exclusion", "missed_exclusion", "parity")},
                     ensure_ascii=False))
    return 1 if summary["parity"]["unexpected"] else 0


if __name__ == "__main__":
    sys.exit(main())
