"""M1-04A check-pool first pass: frozen prototype and current /7 against frozen agent gold.

Committed port of ``experiments/20261021-batch-01-first-pass/code/run_first_pass.py``
(sha256 ``62f34f25…``, the copy that produced batch 1). Behaviour of ``freeze`` and
``run`` is unchanged except that paths are arguments and a scoring convention is
applied. Every phase writes once into a new directory and never overwrites.

Phases:
  freeze   --out DIR --gold-freeze F --batch B --slugs ... [--prototype LABEL=PATH ...]
           -> DIR/freeze.json (prototype, evaluator, exporter, this runner, gold
              freeze, production corpus code, every extraction/gold/notes/source)
  run      --out DIR [--convention v1]
           -> DIR/prototype/, current/, eval/, summary.json (one run, no retries)

Prototypes: without ``--prototype`` the freeze pins ``docs/assets/ocr_logical_structure.py``
to ``code-final`` and the run writes ``prototype/`` exactly as batch 1 did (schema /2).
With one or more explicit ``--prototype LABEL=PATH`` the freeze records each file's
SHA-256 (schema /3) and the run writes ``prototype-LABEL/``, ``eval/prototype-LABEL-<slug>.json``
and summary rows keyed ``prototype-LABEL``; ``sample`` then takes ``--system prototype-LABEL``.
  rescore  --out DIR --source RUN_DIR [--convention v1]
           -> re-scores the saved outputs of an earlier run under a convention
              (systems are not re-run); checks that the all-regions rescore
              reproduces the source summary rows.
  sample   --out FILE --source RUN_DIR --seed N --size K
           -> random gold sample with OCR text for owner review (+ ``--markdown``)

Scoring conventions (``docs/milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v1.md``):
  all-regions  every gold region is scored (how batch 1 was first reported);
  v1           regions whose OCR category is ``Picture`` and running noise are
               not scored, as in the earlier logical-paragraph gold.

Current /7 export: ``export_owner_maps.export_current`` for families that
``build_ocr_structure`` supports; otherwise the production fallback
``pdf_extraction.pdf_tree`` (generic ``build_structure``) with region keys taken
from the extraction's block -> source_region_id map. Generic typed kinds get
the gold prefixes (article->ст, part->ч, chapter->гл, subchapter->§); no parent
is inferred. No system code is changed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
M = ROOT / "data" / "m1" / "m1-04a"
PROTOTYPE = ROOT / "docs" / "assets" / "ocr_logical_structure.py"
EVALUATOR = ROOT / "docs" / "assets" / "evaluate_ocr_owner_gold.py"
EXPORTER = ROOT / "docs" / "assets" / "export_owner_maps.py"
CODE_FINAL = ROOT / "data" / "m1" / "experiments" / "m1-04a-20261017-logical-v1" / "code-final.sha256"
CONVENTIONS = ("all-regions", "v1")
METRICS = ("strict", "no_section", "numbers")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def extraction(slug: str) -> Path:
    (path,) = [p for p in (M / "ocr" / slug / "run-01" / "extractions").glob("*.json")
               if not p.name.startswith("index-")]
    return path


def gold(slug: str) -> Path:
    return M / "gold" / slug / f"agent-{slug}.gold.txt"


def source(batch: str, slug: str) -> Path:
    return M / "documents" / "pool" / batch / slug / "source.json"


def write_new(path: Path, data) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1, sort_keys=True)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- scoring convention


def excluded_keys(extraction_data: dict, convention: str) -> set[str]:
    """Region keys that a convention does not score."""
    if convention not in CONVENTIONS:
        raise ValueError(f"unknown convention {convention!r}")
    if convention == "all-regions":
        return set()
    from legal_rag.corpus.logical_text import classify_regions

    return {f'{r["page"]}.{r["index"]}' for r in classify_regions(extraction_data)
            if r["category"] == "Picture" or r["role"] == "noise"}


def apply_convention(gold_map: dict, extraction_data: dict, convention: str) -> tuple[dict, list[str]]:
    """Gold restricted to scored regions, and the removed gold keys (in gold order)."""
    skip = excluded_keys(extraction_data, convention)
    removed = [key for key in gold_map if key in skip]
    return {key: value for key, value in gold_map.items() if key not in skip}, removed


def score(evaluator, g: dict, owners: dict, cont: dict | None = None) -> tuple[dict, dict]:
    res = evaluator.evaluate(g, owners, cont)
    row = {k: res[k]["correct"] for k in METRICS}
    if cont is not None:
        row["continuation"] = res.get("continuation")
    row["false_exclusion"] = sum(1 for k in g if owners.get(k) is None)
    return res, row


def systems(rows: list[dict]) -> list[str]:
    """Scored systems of a summary: ``prototype`` (or ``prototype-LABEL``...) and ``current``."""
    return [k for k in rows[0] if k == "current" or k.startswith("prototype")] if rows else []


def totals(rows: list[dict]) -> dict:
    total = {"regions": sum(r["regions"] for r in rows)}
    for system in systems(rows):
        total[system] = {k: sum(r[system][k] for r in rows) for k in (*METRICS, "false_exclusion")}
    return total


# --------------------------------------------------------------------------- freeze / run


def tracked(batch: str, slugs: list[str], gold_freeze: Path, extra: tuple[Path, ...] = ()) -> dict:
    files = [PROTOTYPE, EVALUATOR, EXPORTER, Path(__file__).resolve(), gold_freeze, *extra]
    files += sorted((ROOT / "src" / "legal_rag" / "corpus").glob("*.py"))
    for slug in slugs:
        files += [extraction(slug), gold(slug), M / "gold" / slug / "annotation-notes.md", source(batch, slug)]
    return {rel(p): sha(p) for p in files}


def parse_prototypes(specs: list[str] | None) -> dict[str, Path]:
    """``LABEL=PATH`` arguments -> {label: resolved path}; labels are unique."""
    out: dict[str, Path] = {}
    for spec in specs or []:
        label, sep, path = spec.partition("=")
        if not sep or not label or not path or label in out or any(c in label for c in "/\\"):
            raise SystemExit(f"bad --prototype {spec!r}: expected unique LABEL=PATH")
        out[label] = Path(path).resolve()
    return out


def do_freeze(out: Path, batch: str, slugs: list[str], gold_freeze: Path, convention: str,
              prototypes: dict[str, Path] | None = None) -> None:
    code_final = {}
    for line in CODE_FINAL.read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            code_final[name.lstrip("*").strip()] = digest
    expected = code_final["docs/assets/ocr_logical_structure.py"]
    if not prototypes and sha(PROTOTYPE) != expected:
        raise SystemExit("prototype differs from code-final")
    for name, digest in json.loads(gold_freeze.read_text(encoding="utf-8"))["files"].items():
        if sha(ROOT / name) != digest:
            raise SystemExit(f"gold changed after freeze: {name}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()
    record = {"schema_version": "m1-04a-first-pass-freeze/2",
              "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "git_head": head, "prototype": "code-final", "prototype_sha256": expected,
              "prototype_matches_code_final": True, "batch": batch, "convention": convention,
              "gold_freeze": rel(gold_freeze), "gold_freeze_sha256": sha(gold_freeze),
              "gold_matches_gold_freeze": True, "runs_before_freeze": 0, "slugs": slugs,
              "files": tracked(batch, slugs, gold_freeze)}
    if prototypes:
        for key in ("prototype", "prototype_sha256", "prototype_matches_code_final"):
            del record[key]
        record["schema_version"] = "m1-04a-first-pass-freeze/3"
        record["prototypes"] = [{"label": label, "path": rel(path), "sha256": sha(path),
                                 "matches_code_final": sha(path) == expected}
                                for label, path in prototypes.items()]
        record["files"] = tracked(batch, slugs, gold_freeze, tuple(prototypes.values()))
    out.mkdir(parents=True, exist_ok=False)
    write_new(out / "freeze.json", record)
    print(sha(out / "freeze.json"))


PREFIX = {"article": "ст", "part": "ч", "chapter": "гл", "subchapter": "§"}


def typed(address: str | None) -> str | None:
    """Prefix generic article/part/chapter/subchapter values (rename only)."""
    if address is None:
        return None
    seg = address.split("/")
    for i in range(len(seg) - 1):
        if seg[i] in PREFIX:
            seg[i + 1] = PREFIX[seg[i]] + seg[i + 1]
    return "/".join(seg)


def export_current(exporter, ext: dict, claim: str) -> tuple[dict, dict]:
    from legal_rag.corpus.ocr_structure import build_ocr_structure
    from legal_rag.corpus.pdf_extraction import pdf_tree

    if build_ocr_structure(ext, claim, "original") is not None:
        owners, meta = exporter.export_current(ext, claim, "original")
        return owners, {**meta, "route": "build_ocr_structure"}
    keys = exporter.region_keys(ext)
    tree = pdf_tree(ext, claim, "original")
    region_of = {b["block_id"]: b["source_region_id"] for b in ext["blocks"]}
    owners = {key: None for key in keys.values()}
    for entry in [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]:
        region = region_of.get(entry.get("block_id"))
        if region in keys and entry.get("address"):
            owners[keys[region]] = exporter.current_path(typed(entry["address"]), tree["namespace"])
    return owners, {"route": "pdf_tree_fallback_build_structure", "nodes": len(tree["nodes"]),
                    "unresolved_blocks": len(tree["unresolved_blocks"]),
                    "parser_version": tree["parser_version"], "identity": tree["identity_decision"]["status"]}


def do_run(out: Path) -> None:
    freeze_path = out / "freeze.json"
    record = json.loads(freeze_path.read_text(encoding="utf-8"))
    for name, digest in record["files"].items():
        if sha(ROOT / name) != digest:
            raise SystemExit(f"changed after freeze: {name}")
    convention, batch = record["convention"], record["batch"]
    sys.path.insert(0, str(ROOT / "src"))
    exporter = load("export_owner_maps", EXPORTER)
    evaluator = load("evaluate_ocr_owner_gold", EVALUATOR)
    if "prototypes" in record:
        runs = [(f'prototype-{p["label"]}', ROOT / p["path"]) for p in record["prototypes"]]
    else:
        runs = [("prototype", PROTOTYPE)]
    for name in (*(name for name, _ in runs), "current", "eval"):
        (out / name).mkdir()
    rows = []
    for slug in record["slugs"]:
        ext_path = extraction(slug)
        ext = json.loads(ext_path.read_text(encoding="utf-8"))
        g, removed = apply_convention(evaluator.load_gold(gold(slug)), ext, convention)
        row = {"slug": slug, "regions": len(g), "not_scored": removed}
        for name, prototype in runs:
            proto_out = out / name / f"{slug}.json"
            subprocess.run([sys.executable, str(prototype), "--input", str(ext_path), "--output", str(proto_out)],
                           check=True)
            owners, cont = evaluator.from_logical(json.loads(proto_out.read_text(encoding="utf-8")))
            res, row[name] = score(evaluator, g, owners, cont)
            write_new(out / "eval" / f"{name}-{slug}.json", res)
        claim = json.loads(source(batch, slug).read_text(encoding="utf-8"))["declared_identity"]
        try:
            cur, meta = export_current(exporter, ext, claim)
        except Exception as error:  # recorded once, not retried
            cur, meta = {}, {"route": "error", "error": f"{type(error).__name__}: {error}"}
        write_new(out / "current" / f"{slug}.json", {"owners": cur, "meta": meta})
        res, row["current"] = score(evaluator, g, cur)
        row["current"]["meta"] = meta
        write_new(out / "eval" / f"current-{slug}.json", res)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    write_new(out / "summary.json", {"schema_version": "m1-04a-first-pass-summary/2", "convention": convention,
                                     "freeze_sha256": sha(freeze_path),
                                     "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                     "rows": rows, "total": totals(rows)})
    print(json.dumps(totals(rows), ensure_ascii=False))


# --------------------------------------------------------------------------- rescore


def do_rescore(out: Path, src: Path, convention: str) -> None:
    """Score the saved outputs of ``src`` under ``convention``; systems are not re-run."""
    sys.path.insert(0, str(ROOT / "src"))
    evaluator = load("evaluate_ocr_owner_gold", EVALUATOR)
    src_freeze = json.loads((src / "freeze.json").read_text(encoding="utf-8"))
    src_summary = json.loads((src / "summary.json").read_text(encoding="utf-8"))
    for name, digest in json.loads((ROOT / rel_from_record(src_freeze)).read_text(encoding="utf-8"))["files"].items():
        if sha(ROOT / name) != digest:
            raise SystemExit(f"gold changed after freeze: {name}")
    inputs = {rel(p): sha(p) for p in [src / "freeze.json", src / "summary.json", EVALUATOR, Path(__file__).resolve()]}
    out.mkdir(parents=True, exist_ok=False)
    (out / "eval").mkdir()
    rows, check = [], {}
    for src_row in src_summary["rows"]:
        slug = src_row["slug"]
        ext_path = extraction(slug)
        inputs[rel(ext_path)] = sha(ext_path)
        ext = json.loads(ext_path.read_text(encoding="utf-8"))
        full = evaluator.load_gold(gold(slug))
        proto_path, cur_path = src / "prototype" / f"{slug}.json", src / "current" / f"{slug}.json"
        inputs[rel(proto_path)], inputs[rel(cur_path)] = sha(proto_path), sha(cur_path)
        owners, cont = evaluator.from_logical(json.loads(proto_path.read_text(encoding="utf-8")))
        current = json.loads(cur_path.read_text(encoding="utf-8"))
        # The all-regions rescore must reproduce the source run row exactly.
        _, p_all = score(evaluator, full, owners, cont)
        _, c_all = score(evaluator, full, current["owners"])
        check[slug] = (p_all == src_row["prototype"]
                       and c_all == {k: v for k, v in src_row["current"].items() if k != "meta"}
                       and len(full) == src_row["regions"])
        g, removed = apply_convention(full, ext, convention)
        row = {"slug": slug, "regions": len(g), "not_scored": removed}
        res, row["prototype"] = score(evaluator, g, owners, cont)
        write_new(out / "eval" / f"prototype-{slug}.json", res)
        res, row["current"] = score(evaluator, g, current["owners"])
        row["current"]["meta"] = current["meta"]
        write_new(out / "eval" / f"current-{slug}.json", res)
        rows.append(row)
    if not all(check.values()):
        raise SystemExit(f"all-regions rescore differs from the source run: {check}")
    write_new(out / "summary.json", {
        "schema_version": "m1-04a-first-pass-summary/2", "convention": convention,
        "rescored_from": rel(src), "systems_rerun": False, "all_regions_matches_source": True,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": inputs, "rows": rows, "total": totals(rows),
        "source_total_all_regions": src_summary["total"]})
    print(json.dumps(totals(rows), ensure_ascii=False))


def rel_from_record(freeze_record: dict) -> str:
    """Gold freeze path of a first-pass freeze (schema /1 stored only its hash)."""
    if "gold_freeze" in freeze_record:
        return freeze_record["gold_freeze"]
    (name,) = [n for n in freeze_record["files"] if n.endswith("-gold-freeze/freeze.json")]
    return name


# --------------------------------------------------------------------------- owner-review sample


def region_text(ext: dict, page: int, index: int) -> tuple[str, str]:
    """OCR category and display text of one region (tables keep their line breaks)."""
    region = next(p for p in ext["pages"] if p["page"] == page)["regions"][index]
    blocks = [b for b in ext["blocks"] if b.get("source_region_id") == region["region_id"]]
    if region["category"] == "Table":
        return region["category"], "\n".join(b["display_text"].strip() for b in blocks)
    return region["category"], " ".join(b["display_text"].strip().replace("\n", " ") for b in blocks)


def build_sample(src: Path, seed: int, size: int, system: str = "prototype") -> dict:
    """``random.Random(seed).sample`` over gold rows in gold-file order, slugs in freeze order.

    ``prototype_ok`` is read from the strict errors in ``eval/<system>-<slug>.json``."""
    slugs = json.loads((src / "freeze.json").read_text(encoding="utf-8"))["slugs"]
    rows = []
    for slug in slugs:
        for line in gold(slug).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                rows.append((slug, line.split()))
    picked, cache, out = random.Random(seed).sample(rows, size), {}, []
    for slug, fields in picked:
        if slug not in cache:
            errors = json.loads((src / "eval" / f"{system}-{slug}.json").read_text(encoding="utf-8"))["errors"]
            cache[slug] = (json.loads(extraction(slug).read_text(encoding="utf-8")), {e["region"] for e in errors})
        ext, errors = cache[slug]
        page, index = map(int, fields[0].split("."))
        category, text = region_text(ext, page, index)
        out.append({"slug": slug, "region": fields[0], "gold": fields[1], "continuation": "+" in fields[2:],
                    "category": category, "text": text, "prototype_ok": fields[0] not in errors})
    return {"seed": seed, "population": len(rows), "order": "gold file order, slugs in freeze order", "sample": out}


def sample_markdown(sample: dict) -> str:
    """Table rows of the owner-review sample file (text cut at 200 characters)."""
    lines = ["| № | Акт | Область | Тип OCR | Текст | Владелец | Прототип |", "|---:|---|---|---|---|---|---|"]
    for n, e in enumerate(sample["sample"], start=1):
        text = " ".join(e["text"].split()).replace("|", "¦")
        text = text if len(text) <= 200 else text[:200] + "…"
        text = text or "(изображение без распознанного текста)"
        owner = f'`{e["gold"]}`' + (" (+)" if e["continuation"] else "")
        lines.append(f'| {n} | {e["slug"]} | {e["region"]} | {e["category"]} | {text} | {owner} | '
                     f'{"да" if e["prototype_ok"] else "нет"} |')
    return "\n".join(lines) + "\n"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("phase", choices=("freeze", "run", "rescore", "sample"))
    parser.add_argument("--out", required=True, help="new run directory (sample: new output file)")
    parser.add_argument("--source", help="earlier run directory (rescore, sample)")
    parser.add_argument("--gold-freeze", help="gold freeze.json (freeze)")
    parser.add_argument("--batch", default="batch-01")
    parser.add_argument("--slugs", nargs="+")
    parser.add_argument("--convention", choices=CONVENTIONS, default="v1")
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--size", type=int, default=30)
    parser.add_argument("--markdown", help="sample: also write the Markdown table to this new file")
    parser.add_argument("--prototype", action="append", metavar="LABEL=PATH",
                        help="freeze: explicit prototype file (repeatable); default pins code-final")
    parser.add_argument("--system", default="prototype", help="sample: eval prefix, e.g. prototype-v1")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    if args.phase == "freeze":
        if not (args.gold_freeze and args.slugs):
            parser.error("freeze needs --gold-freeze and --slugs")
        do_freeze(out, args.batch, args.slugs, Path(args.gold_freeze).resolve(), args.convention,
                  parse_prototypes(args.prototype))
    elif args.phase == "run":
        do_run(out)
    elif args.phase == "rescore":
        do_rescore(out, Path(args.source).resolve(), args.convention)
    else:
        sample = build_sample(Path(args.source).resolve(), args.seed, args.size, args.system)
        _write_sample(out, sample)
        if args.markdown:
            with open(args.markdown, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(sample_markdown(sample))


def _write_sample(path: Path, sample: dict) -> None:
    # Batch 1's sample-30.json: indent 1, insertion order, CRLF (Windows text mode), no final newline.
    with path.open("x", encoding="utf-8", newline="\r\n") as handle:
        json.dump(sample, handle, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
