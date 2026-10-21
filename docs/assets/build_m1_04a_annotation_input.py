"""Build the M1-04A annotator input: one ``<slug>.regions.tsv`` per act plus ``manifest.json``.

Two modes, both write once into a new output directory:

* default (annotation convention v1, see
  ``docs/milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v1.md``): reads only the
  stage-1 OCR extraction. Columns ``key``, ``category``, ``text``; regions in
  page/region order. Regions of OCR category ``Picture`` and running noise
  (``legal_rag.corpus.logical_text.classify_regions`` role ``noise``) are not
  annotated and are listed in a trailing comment. No stage-2 paragraph id or
  continuation join is shown, so the gold ``+`` mark stays independent of the
  logical-text layer.
* ``--legacy-batch-01``: byte-for-byte port of the controller's inline script
  that produced ``experiments/20261021-batch-01-annotation-input`` on
  21.10.2026 (columns ``key``, ``category``, ``P``, ``join``, ``text`` from the
  stage-2 logical text, Picture regions included). Kept only to reproduce that
  input; do not use it for new batches.

Run from the repository root with ``PYTHONPATH=src``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path("data/m1/m1-04a")
CONVENTION = "m1-04a-annotation/v1"
NOT_ANNOTATED_CATEGORIES = frozenset({"Picture"})


def _cell(text: str) -> str:
    return text.replace("\t", " ").replace("\n", " ⏎ ")


# --------------------------------------------------------------------------- legacy (batch 1)


def legacy_tsv(slug: str, logical_text: dict) -> bytes:
    """The batch-1 TSV exactly as the controller built it (includes stage-2 P/join)."""
    regs = {r["region_id"]: r for r in logical_text["regions"]}
    lines = [f"# {slug}: content regions in reading order. key=<page>.<region-index>; P=<paragraph_id>; "
             "join=continuation joined by logical-text layer",
             "# key\tcategory\tP\tjoin\ttext"]
    for p in logical_text["paragraphs"]:
        for f in p["fragments"]:
            r = regs[f["region_id"]]
            txt = _cell(p["text"][f["start"]:f["end"]])
            lines.append(f'{r["page"]}.{r["index"]}\t{r["category"]}\tP{p["paragraph_id"]}\t{f["join"] or "-"}\t{txt}')
    noise = [f'{r["page"]}.{r["index"]}' for r in logical_text["regions"] if r["role"] == "noise"]
    lines.append("# noise regions (page numbers/running text, not annotated): " + " ".join(noise))
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_legacy(out: Path, slugs: list[str] | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    ocr = ROOT / BASE / "ocr"
    slugs = slugs or sorted(p.name for p in ocr.iterdir() if p.is_dir())
    manifest = {}
    for slug in slugs:
        (lt,) = sorted((ocr / slug / "run-01" / "logical-text").glob("*.json"))
        data = legacy_tsv(slug, json.loads(lt.read_text(encoding="utf-8")))
        (out / f"{slug}.regions.tsv").write_bytes(data)
        d = json.loads(lt.read_text(encoding="utf-8"))
        manifest[slug] = {"logical_text": str(lt.relative_to(ROOT)).replace("\\", "/"),
                          "sha256": hashlib.sha256(data).hexdigest(), "paragraphs": len(d["paragraphs"])}
    # The original manifest was written with Path.write_text on Windows (CRLF, no final newline).
    text = json.dumps(manifest, ensure_ascii=False, indent=1).replace("\n", "\r\n")
    (out / "manifest.json").write_bytes(text.encode("utf-8"))
    return manifest


# --------------------------------------------------------------------------- convention v1


def region_text(extraction: dict) -> dict[str, str]:
    """Region id -> OCR text (block ``original_text`` concatenated in block order)."""
    text: dict[str, str] = {}
    for block in extraction["blocks"]:
        text[block["source_region_id"]] = text.get(block["source_region_id"], "") + block["original_text"]
    return text


def excluded_regions(extraction: dict) -> dict[str, list[str]]:
    """Region keys that convention v1 neither annotates nor scores."""
    from legal_rag.corpus.logical_text import classify_regions

    out: dict[str, list[str]] = {"picture": [], "noise": []}
    for r in classify_regions(extraction):
        key = f'{r["page"]}.{r["index"]}'
        if r["category"] in NOT_ANNOTATED_CATEGORIES:
            out["picture"].append(key)
        elif r["role"] == "noise":
            out["noise"].append(key)
    return out


def v1_tsv(slug: str, extraction: dict) -> tuple[bytes, dict]:
    """Annotator TSV under convention v1 and its accounting (no stage-2 output)."""
    excluded = excluded_regions(extraction)
    skip = set(excluded["picture"]) | set(excluded["noise"])
    text = region_text(extraction)
    lines = [f"# {slug}: annotation input, convention {CONVENTION}. key=<page>.<region-index>; "
             "regions in page order; category = OCR category; ⏎ = line break inside the region",
             "# key\tcategory\ttext"]
    rows = 0
    for page in extraction["pages"]:
        for index, region in enumerate(page["regions"]):
            key = f'{page["page"]}.{index}'
            if key in skip:
                continue
            lines.append(f'{key}\t{region["category"]}\t{_cell(text.get(region["region_id"], "").strip())}')
            rows += 1
    lines.append("# not annotated (Picture): " + " ".join(excluded["picture"]))
    lines.append("# not annotated (noise: page numbers/running text): " + " ".join(excluded["noise"]))
    return ("\n".join(lines) + "\n").encode("utf-8"), {"regions": rows, "excluded": excluded}


def extraction_path(slug: str) -> Path:
    (path,) = [p for p in (ROOT / BASE / "ocr" / slug / "run-01" / "extractions").glob("*.json")
               if not p.name.startswith("index-")]
    return path


def build_v1(out: Path, slugs: list[str]) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    acts = {}
    for slug in slugs:
        path = extraction_path(slug)
        raw = path.read_bytes()
        data, info = v1_tsv(slug, json.loads(raw.decode("utf-8")))
        with (out / f"{slug}.regions.tsv").open("xb") as handle:
            handle.write(data)
        acts[slug] = {"extraction": str(path.relative_to(ROOT)).replace("\\", "/"),
                      "extraction_sha256": hashlib.sha256(raw).hexdigest(),
                      "sha256": hashlib.sha256(data).hexdigest(), **info}
    manifest = {"schema_version": "m1-04a-annotation-input/1", "convention": CONVENTION, "acts": acts}
    with (out / "manifest.json").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    return manifest


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--output", required=True, help="new directory (must not exist)")
    parser.add_argument("--slugs", nargs="+", help="acts under data/m1/m1-04a/ocr (v1: required)")
    parser.add_argument("--legacy-batch-01", action="store_true",
                        help="reproduce the 21.10.2026 batch-1 input (stage-2 P/join, Picture included)")
    args = parser.parse_args(argv)
    out = Path(args.output)
    if args.legacy_batch_01:
        manifest = build_legacy(out, args.slugs)
    else:
        if not args.slugs:
            parser.error("--slugs is required in v1 mode")
        manifest = build_v1(out, args.slugs)
    print(json.dumps({"output": str(out), "acts": len(manifest.get("acts", manifest))}))


if __name__ == "__main__":
    main()
