"""Compare region owner paths of a structure run with the hand-made M1-04A gold.

Gold lines: ``<page>.<region-index> <owner>[|<alternative>...] [+]``.
``R`` (approved Rules) and ``S`` (approved text) are the same scope.
Metrics:
  owner_accuracy      share of gold regions whose predicted owner path matches;
  continuation P/R    regions predicted as a continuation of the previous
                      logical paragraph versus gold ``+`` (only for systems
                      that report logical paragraphs).
"""

from __future__ import annotations

import argparse
import json
import re


def norm(path: str | None) -> str | None:
    if path is None:
        return None
    parts = path.split("/")
    if parts[0] == "R":
        parts[0] = "S"
    return "/".join(parts)


def load_gold(path):
    gold = {}
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        gold[fields[0]] = {"owners": [norm(x) for x in fields[1].split("|")], "continuation": "+" in fields[2:]}
    return gold


ROMAN_SEG = re.compile(r"^[IVXLC]+$")


def variant(path, name):
    """strict: full path; no_section: drop section segments (some parsers keep
    points as siblings of section headings); numbers: also drop the A/S scope
    letter (for engines without an approving-act/approved-text distinction)."""
    if path is None or name == "strict":
        return path
    parts = [p for p in path.split("/") if not ROMAN_SEG.match(p)]
    if name == "numbers":
        parts = parts[1:] if parts and parts[0] in {"A", "S"} else parts
    return "/".join(parts)


def evaluate(gold, predicted, continuation=None):
    result = {"regions": len(gold)}
    for name in ("strict", "no_section", "numbers"):
        ok, rows = 0, []
        for key, g in gold.items():
            p = norm(predicted.get(key))
            hit = variant(p, name) in {variant(o, name) for o in g["owners"]}
            ok += hit
            rows.append({"region": key, "gold": g["owners"][0], "predicted": p, "ok": hit})
        result[name] = {"correct": ok, "accuracy": round(ok / len(gold), 4)}
        if name == "strict":
            result["errors"] = [r for r in rows if not r["ok"]]
    if continuation is not None:
        tp = sum(1 for k, g in gold.items() if g["continuation"] and continuation.get(k))
        fp = sum(1 for k, g in gold.items() if not g["continuation"] and continuation.get(k))
        fn = sum(1 for k, g in gold.items() if g["continuation"] and not continuation.get(k))
        result["continuation"] = {"tp": tp, "fp": fp, "fn": fn}
    return result


def from_logical(run):
    owners = {f"{r['page']}.{r['index']}": r["owner"] for r in run["regions"]}
    cont = {f"{r['page']}.{r['index']}": r["continuation"] for r in run["regions"]}
    return owners, cont


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True)
    parser.add_argument("--run", required=True, help="ocr-logical-structure output or {region: owner} JSON map")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    with open(args.run, encoding="utf-8") as handle:
        run = json.load(handle)
    if "regions" in run and isinstance(run["regions"], list):
        owners, cont = from_logical(run)
    else:
        owners, cont = run.get("owners", run), run.get("continuation")
    result = evaluate(load_gold(args.gold), owners, cont)
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.output:
        with open(args.output, "x", encoding="utf-8") as handle:
            handle.write(text)
    print(json.dumps({k: v for k, v in result.items() if k != "errors"}, ensure_ascii=False))
    for row in result["errors"][:60]:
        print(f"  {row['region']:>7}  gold={row['gold']:<22} got={row['predicted']}")


if __name__ == "__main__":
    main()
