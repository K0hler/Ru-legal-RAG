"""Derive M1-04A gold under convention v2 §6.1 «a document quoted in an amendment is quoted text» (write-once).

Owner decision 27.10.2026 (scan batch 11, rp-2417-2015): a whole document restated inside an amendment («2. Программу …
изложить в следующей редакции: "ОДОБРЕНА … ПРОГРАММА …"») is text of the amendment point that introduces the quotation,
not a separate attached document. For every act of a batch it writes ``agent-<slug>.gold-quoted.txt`` and the receipt
``agent-<slug>.gold-quoted.sha256`` next to the frozen gold. Acts without a map get an exact copy. An act with a
hand-written map ``agent-<slug>.quoted-map.json`` (``{"schema_version": "m1-04a-gold-quoted-map/1", "gold_sha256":
<frozen gold>, "collapse": {"S2": "S/2"}}``) has every owner and alternative whose first segment is a mapped root replaced
by the target as a whole (the quoted document's sections, points and annexes all become the introducing point); the map
is pinned to the frozen gold hash. The receipt lists the derived gold, the frozen gold and the map.

    python docs/assets/derive_m1_04a_gold_quoted.py --slugs <slug> ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

GOLD = Path(__file__).resolve().parents[2] / "data/m1/m1-04a/gold"
SUFFIX = "gold-quoted"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collapse(owner: str, roots: dict) -> str:
    head = owner.partition("/")[0]
    return roots.get(head, owner)


def derive(slug: str) -> dict:
    folder = GOLD / slug
    frozen = folder / f"agent-{slug}.gold.txt"
    out = folder / f"agent-{slug}.{SUFFIX}.txt"
    receipt = folder / f"agent-{slug}.{SUFFIX}.sha256"
    mapping = folder / f"agent-{slug}.quoted-map.json"
    lines = frozen.read_text(encoding="utf-8").split("\n")
    changed = 0
    if mapping.exists():
        spec = json.loads(mapping.read_text(encoding="utf-8"))
        if spec.get("schema_version") != "m1-04a-gold-quoted-map/1" or spec["gold_sha256"] != sha(frozen):
            raise SystemExit(f"{mapping.name} is not pinned to the frozen gold")
        for k, line in enumerate(lines):
            if not line or line.startswith("#"):
                continue
            fields = line.split(" ")
            owners = list(dict.fromkeys(collapse(o, spec["collapse"]) for o in fields[1].split("|")))
            new_owner = "|".join(owners)
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
