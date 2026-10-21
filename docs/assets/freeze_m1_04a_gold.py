"""Freeze M1-04A agent gold before any parser run (write-once).

Port of the controller's inline script that wrote
``experiments/20261021-batch-01-gold-freeze/freeze.json`` (``09c342d1…``,
schema ``m1-04a-gold-freeze/1``). Differences: acts are named explicitly, the
annotation convention and the annotator input (``*.regions.tsv`` and
``manifest.json`` from ``build_m1_04a_annotation_input.py``) are hashed too
(schema ``/2``), and an existing ``agent-<slug>.sha256`` that disagrees with the
gold is an error instead of being silently kept.

    python docs/assets/freeze_m1_04a_gold.py --output data/m1/m1-04a/experiments/<date>-batch-NN-gold-freeze \
        --annotation-input data/m1/m1-04a/experiments/<date>-batch-NN-annotation-input \
        --annotator "..." --slugs <slug> ...
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLD = Path("data/m1/m1-04a/gold")
CONVENTION = "m1-04a-annotation/v1"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def freeze(output: Path, slugs: list[str], annotation_input: Path, annotator: str,
           root: Path = ROOT, convention: str = CONVENTION) -> dict:
    """Hash gold, notes and annotator input; write per-act ``.sha256`` once and ``freeze.json`` once."""
    gold_root = root / GOLD
    files, pending = {}, []
    for slug in slugs:
        d = gold_root / slug
        for name in (f"agent-{slug}.gold.txt", "annotation-notes.md"):
            files[rel(d / name, root)] = sha(d / name)
        line = f"{files[rel(d / f'agent-{slug}.gold.txt', root)]}  agent-{slug}.gold.txt\n"
        receipt = d / f"agent-{slug}.sha256"
        if receipt.exists():
            if receipt.read_text(encoding="utf-8") != line:
                raise SystemExit(f"{rel(receipt, root)} disagrees with the gold file")
        else:
            pending.append((receipt, line))
    tsvs = sorted(annotation_input.glob("*.regions.tsv"))
    missing = [s for s in slugs if annotation_input / f"{s}.regions.tsv" not in tsvs]
    if missing or not (annotation_input / "manifest.json").exists():
        raise SystemExit(f"annotation input incomplete: missing {missing or ['manifest.json']}")
    inputs = {rel(p, root): sha(p) for p in [*tsvs, annotation_input / "manifest.json"]}
    record = {"schema_version": "m1-04a-gold-freeze/2",
              "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "annotator": annotator, "annotation_convention": convention,
              "prototype_runs_before_freeze": 0, "slugs": slugs,
              "files": files, "annotation_input": inputs}
    output.mkdir(parents=True, exist_ok=False)
    with (output / "freeze.json").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, indent=1) + "\n")
    for receipt, line in pending:
        with receipt.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
    return record


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--output", required=True, help="new experiment directory (must not exist)")
    parser.add_argument("--annotation-input", required=True, help="directory with <slug>.regions.tsv + manifest.json")
    parser.add_argument("--annotator", required=True, help="who annotated, from which input")
    parser.add_argument("--slugs", nargs="+", required=True)
    args = parser.parse_args(argv)
    freeze(Path(args.output).resolve(), args.slugs, Path(args.annotation_input).resolve(), args.annotator)
    print(sha(Path(args.output) / "freeze.json"))


if __name__ == "__main__":
    main()
