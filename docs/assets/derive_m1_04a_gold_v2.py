"""Derive M1-04A owner gold under annotation convention v2 from a frozen v1 gold file.

Convention: ``docs/milestones/m1/04a/M1_04A_ANNOTATION_CONVENTION_v2.md``
(``m1-04a-annotation/v2``). The v1 gold is never modified; the derivation is
mechanical and applies only the two rules v2 adds:

  (i)  annex of an attached document: an attached-document scope that is an
       annex of another attached document is renamed by an explicit per-document
       map (``S2`` -> ``S/AN1`` ...). The map is data, written next to the gold
       as ``agent-<slug>.v2-map.json``; nothing here names an act.
  (ii) nested dotted point: a pure-number segment ``N.M`` whose parent node
       ``N`` exists under the same parent path in the same gold is nested in it
       (``S/II/4.1`` -> ``S/II/4/4.1``); a flat ``N.M`` stays when ``N`` does not
       exist. Typed segments (``ст12.1``, ``ч1``) are never touched.

Phases:
  derive --slug-dir DIR   -> DIR/agent-<slug>.gold-v2.txt and agent-<slug>.gold-v2.sha256
                             (write-once; needs DIR/agent-<slug>.v2-map.json whose
                             ``source_gold_sha256`` matches the v1 gold)
                             Optional ``flat_dotted`` (list of owner paths ``S/II/4.1`` that stay flat)
                             in the map and/or ``DIR/exceptions.json``
                             (``{"schema_version": "m1-04a-gold-v2-exceptions/1", "flat_dotted": [...]}``).
  check  --slug-dir DIR   -> prints what would change; writes nothing (map optional)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

CONVENTION = "m1-04a-annotation/v2"
MAP_SCHEMA = "m1-04a-gold-v2-map/1"
EXCEPTIONS_SCHEMA = "m1-04a-gold-v2-exceptions/1"
DOTTED = re.compile(r"^\d+(?:\.\d+)+$")
ANNEX_TARGET = re.compile(r"^S/AN\d+$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def map_scope(path: str, annexes: dict[str, str]) -> str:
    """Rule (i): rename the leading attached-document scope by the explicit map."""
    head, sep, rest = path.partition("/")
    if head in annexes:
        return annexes[head] + (sep + rest if sep else "")
    return path


def node_prefixes(paths) -> set[tuple[str, ...]]:
    """Every node of a gold: each owner path and all of its prefixes."""
    out: set[tuple[str, ...]] = set()
    for path in paths:
        seg = tuple(path.split("/"))
        out.update(seg[:i] for i in range(1, len(seg) + 1))
    return out


def nest_dotted(path: str, nodes: set[tuple[str, ...]], flat: frozenset = frozenset()) -> str:
    """Rule (ii): nest ``N.M`` under an existing sibling node ``N`` (recursively for ``N.M.K``).

    ``flat`` holds owner paths (``S/II/4.1``) the annotator declared flat: such a segment
    is never nested, though paths below it still nest under it.
    """

    def nested(seg: tuple[str, ...]) -> tuple[str, ...]:
        out: tuple[str, ...] = ()
        for i, s in enumerate(seg):
            parent = s.rsplit(".", 1)[0] if DOTTED.match(s) else None
            if parent is not None and seg[: i + 1] not in flat and (*seg[:i], parent) in nodes:
                out = nested((*seg[:i], parent)) + (s,)
            else:
                out = out + (s,)
        return out

    return "/".join(nested(tuple(path.split("/"))))


def validate_map(annexes: dict[str, str]) -> None:
    for source, target in annexes.items():
        if not re.match(r"^S\d+$", source) or source == "S" or not ANNEX_TARGET.match(target):
            raise ValueError(f"bad annex map entry {source!r} -> {target!r}")
    if len(set(annexes.values())) != len(annexes):
        raise ValueError("annex map targets are not unique")


def validate_flat(flat_dotted) -> frozenset:
    out = set()
    for path in flat_dotted:
        segments = path.split("/") if isinstance(path, str) else []
        if not segments or not all(segments) or not DOTTED.match(segments[-1]):
            raise ValueError(f"bad flat_dotted entry {path!r}: expected an owner path ending in N.M")
        out.add(tuple(segments))
    return frozenset(out)


def derive_lines(lines: list[str], annexes: dict[str, str], flat_dotted=()) -> tuple[list[str], dict]:
    """Map gold lines (comments kept verbatim); returns new lines and change counts."""
    validate_map(annexes)
    flat = validate_flat(flat_dotted)
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            rows.append((line, None))
            continue
        key, owners, *rest = stripped.split()
        rows.append((line, (key, owners.split("|"), rest)))
    original = {o for _, row in rows if row for o in row[1]}
    missing = set(annexes) - {o.split("/")[0] for o in original}
    if missing:
        raise ValueError(f"annex map names scopes absent from the gold: {sorted(missing)}")
    taken = [t for t in annexes.values() if any(o == t or o.startswith(t + "/") for o in original)]
    if taken:
        raise ValueError(f"annex map target already used in the gold: {taken}")
    scoped = [[map_scope(o, annexes) for o in row[1]] for _, row in rows if row]
    nodes = node_prefixes({o for owners in scoped for o in owners})
    # Entries are written in v1-gold scope; accept the post-mapping form too.
    flat = frozenset(tuple(map_scope("/".join(e), annexes).split("/")) for e in flat)
    unmatched = sorted("/".join(e) for e in flat if e not in nodes)
    if unmatched:
        raise ValueError(f"flat_dotted entries match no owner path in the gold: {unmatched}")
    out, counts, it = [], {"lines": 0, "scope": 0, "nested": 0, "changed": 0}, iter(scoped)
    for line, row in rows:
        if row is None:
            out.append(line)
            continue
        key, owners, rest = row
        counts["lines"] += 1
        mapped = next(it)
        final = [nest_dotted(o, nodes, flat) for o in mapped]
        counts["scope"] += mapped != owners
        counts["nested"] += final != mapped
        if final == owners:
            out.append(line)
        else:
            counts["changed"] += 1
            out.append(" ".join([key, "|".join(final), *rest]))
    return out, counts


def gold_paths(slug_dir: Path) -> tuple[str, Path, Path, Path, Path]:
    slug = slug_dir.name
    return (slug, slug_dir / f"agent-{slug}.gold.txt", slug_dir / f"agent-{slug}.v2-map.json",
            slug_dir / f"agent-{slug}.gold-v2.txt", slug_dir / f"agent-{slug}.gold-v2.sha256")


def read_map(map_path: Path, gold_bytes: bytes) -> dict:
    record = json.loads(map_path.read_text(encoding="utf-8"))
    if record.get("schema_version") != MAP_SCHEMA:
        raise SystemExit(f"{map_path}: schema_version must be {MAP_SCHEMA}")
    if record.get("source_gold_sha256") != sha(gold_bytes):
        raise SystemExit(f"{map_path}: source_gold_sha256 does not match the v1 gold")
    return record["attached_annexes"]


def read_flat_dotted(map_path: Path, exceptions_path: Path) -> list[str]:
    """Optional ``flat_dotted`` from the map plus the annotator's ``exceptions.json`` (union)."""
    found: list[str] = []
    if map_path.exists():
        record = json.loads(map_path.read_text(encoding="utf-8"))
        if record.get("schema_version") != MAP_SCHEMA:
            raise SystemExit(f"{map_path}: schema_version must be {MAP_SCHEMA}")
        found += record.get("flat_dotted", [])
    if exceptions_path.exists():
        record = json.loads(exceptions_path.read_text(encoding="utf-8"))
        if record.get("schema_version") != EXCEPTIONS_SCHEMA:
            raise SystemExit(f"{exceptions_path}: schema_version must be {EXCEPTIONS_SCHEMA}")
        found += record.get("flat_dotted", [])
    return sorted(set(found))


def derive(slug_dir: Path, write: bool) -> dict:
    slug, gold, map_path, out_path, sha_path = gold_paths(slug_dir)
    raw = gold.read_bytes()
    if write or map_path.exists():
        annexes = read_map(map_path, raw)
    else:
        annexes = {}
    text = raw.decode("utf-8")
    newline = "\r\n" if "\r\n" in text else "\n"
    exceptions_path = slug_dir / "exceptions.json"
    flat = read_flat_dotted(map_path, exceptions_path)
    lines, counts = derive_lines(text.splitlines(), annexes, flat)
    report = {"slug": slug, "annexes": annexes, **counts, **({"flat_dotted": flat} if flat else {})}
    if not write:
        return report
    header = [f"# convention: {CONVENTION}",
              f"# derived: docs/assets/derive_m1_04a_gold_v2.py from {gold.name} (sha256 {sha(raw)}) "
              f"with {map_path.name} (sha256 {sha(map_path.read_bytes())}); "
              f"{counts['changed']} of {counts['lines']} owner lines changed "
              f"(annex-of-attached {counts['scope']}, nested dotted {counts['nested']}); "
              "the v1 comments below are kept verbatim as provenance."]
    if flat:
        header.insert(1, "# flat dotted exceptions (annotator): " + ", ".join(flat))
    body = newline.join(header + lines) + (newline if text.endswith(("\n", "\r")) else "")
    with out_path.open("x", encoding="utf-8", newline="") as handle:
        handle.write(body)
    with sha_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{sha(out_path.read_bytes())}  {out_path.name}\n")
        handle.write(f"{sha(map_path.read_bytes())}  {map_path.name}\n")
        if exceptions_path.exists():
            handle.write(f"{sha(exceptions_path.read_bytes())}  {exceptions_path.name}\n")
    return report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("phase", choices=("derive", "check"))
    parser.add_argument("--slug-dir", nargs="+", required=True, help="gold/<slug> directories")
    args = parser.parse_args(argv)
    for slug_dir in args.slug_dir:
        print(json.dumps(derive(Path(slug_dir).resolve(), args.phase == "derive"), ensure_ascii=False))


if __name__ == "__main__":
    main()
