"""Derive M1-04A gold under convention v2 §6.1 «a form without its own caption is part of its annex» (write-once).

For every act of a batch it writes ``agent-<slug>.gold-forms.txt`` and the receipt ``agent-<slug>.gold-forms.sha256``
next to the frozen gold. Acts without a map get an exact copy. An act with a hand-written map
``agent-<slug>.forms-map.json`` (``{"schema_version": "m1-04a-gold-forms-map/1", "gold_sha256": <frozen gold>,
"roots": {"S5": "S4", ...}}``) has every owner and alternative whose first segment is a mapped root renamed (the tail
is kept); the map is pinned to the frozen gold hash. The receipt lists the derived gold, the frozen gold and the map.

    python docs/assets/derive_m1_04a_gold_forms.py --slugs <slug> ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GOLD = Path(__file__).resolve().parents[2] / "data/m1/m1-04a/gold"
SUFFIX = "gold-forms"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rename(owner: str, roots: dict) -> str:
    head, _, tail = owner.partition("/")
    return roots.get(head, head) + ("/" + tail if tail else "")


def derive(slug: str) -> dict:
    folder = GOLD / slug
    frozen = folder / f"agent-{slug}.gold.txt"
    out = folder / f"agent-{slug}.{SUFFIX}.txt"
    receipt = folder / f"agent-{slug}.{SUFFIX}.sha256"
    mapping = folder / f"agent-{slug}.forms-map.json"
    lines = frozen.read_text(encoding="utf-8").split("\n")
    changed = 0
    if mapping.exists():
        spec = json.loads(mapping.read_text(encoding="utf-8"))
        if spec.get("schema_version") != "m1-04a-gold-forms-map/1" or spec["gold_sha256"] != sha(frozen):
            raise SystemExit(f"{mapping.name} is not pinned to the frozen gold")
        for k, line in enumerate(lines):
            if not line or line.startswith("#"):
                continue
            fields = line.split(" ")
            new_owner = "|".join(rename(o, spec["roots"]) for o in fields[1].split("|"))
            if new_owner != fields[1]:
                changed += 1
                fields[1] = new_owner
                lines[k] = " ".join(fields)
    data = "\n".join(lines).encode("utf-8")
    with out.open("xb") as handle:
        handle.write(data)
    rows = [f"{sha(out)}  {out.name}", f"{sha(frozen)}  {frozen.name}"]
    if mapping.exists():
        rows.append(f"{sha(mapping)}  {mapping.name}")
    with receipt.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(rows) + "\n")
    return {"slug": slug, "mapped": mapping.exists(), "changed_rows": changed}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--slugs", nargs="+", required=True)
    args = parser.parse_args(argv)
    print(json.dumps([derive(slug) for slug in args.slugs], ensure_ascii=False))


if __name__ == "__main__":
    main()
