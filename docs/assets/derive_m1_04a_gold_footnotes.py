"""Derive M1-04A gold under the owner decision «a footnote belongs to the point carrying its mark» (write-once).

For every act of a batch it writes ``agent-<slug>.gold-footnotes.txt`` and the receipt
``agent-<slug>.gold-footnotes.sha256`` next to the frozen gold. Acts without a map get an exact copy. An act with a
hand-written map ``agent-<slug>.footnotes-map.json`` (``{"schema_version": "m1-04a-gold-footnotes-map/1",
"gold_sha256": <frozen gold>, "regions": {"<page>.<index>": {"from": <frozen owner>, "owner": <new owner field>,
"mark": <region(s) with the mark>}, ...}}``) has the owner field of each listed region replaced; the continuation
flag is kept. The map is pinned to the frozen gold hash, and every listed region must exist with the frozen owner
field ``from``. The receipt lists the derived gold, the frozen gold and the map.

    python docs/assets/derive_m1_04a_gold_footnotes.py --slugs <slug> ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GOLD = Path(__file__).resolve().parents[2] / "data/m1/m1-04a/gold"
SUFFIX = "gold-footnotes"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive(slug: str) -> dict:
    folder = GOLD / slug
    frozen = folder / f"agent-{slug}.gold.txt"
    out = folder / f"agent-{slug}.{SUFFIX}.txt"
    receipt = folder / f"agent-{slug}.{SUFFIX}.sha256"
    mapping = folder / f"agent-{slug}.footnotes-map.json"
    lines = frozen.read_text(encoding="utf-8").split("\n")
    changed = 0
    if mapping.exists():
        spec = json.loads(mapping.read_text(encoding="utf-8"))
        if spec.get("schema_version") != "m1-04a-gold-footnotes-map/1" or spec["gold_sha256"] != sha(frozen):
            raise SystemExit(f"{mapping.name} is not pinned to the frozen gold")
        index = {line.split(" ")[0]: k for k, line in enumerate(lines) if line and not line.startswith("#")}
        for region, change in spec["regions"].items():
            if region not in index:
                raise SystemExit(f"{mapping.name}: region {region} is not in the gold")
            fields = lines[index[region]].split(" ")
            if fields[1] != change["from"]:
                raise SystemExit(f"{mapping.name}: region {region} has owner {fields[1]}, not {change['from']}")
            if not change["owner"] or " " in change["owner"]:
                raise SystemExit(f"{mapping.name}: region {region} has a malformed owner")
            fields[1] = change["owner"]
            lines[index[region]] = " ".join(fields)
            changed += 1
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
