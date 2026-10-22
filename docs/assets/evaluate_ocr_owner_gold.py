"""Compare region owner paths of a structure run with the hand-made M1-04A gold.

Gold lines: ``<page>.<region-index> <owner>[|<alternative>...] [+]``.
``R`` (approved Rules) and ``S`` (approved text) are the same scope.
Grammar ``owner-path/2``: scope ``A`` | ``S``, ``S2``... | ``A/AN<n>``; typed
segments ``гл<n>``, ``ст<n>``, ``§<n>``, ``ч<n>``, ``разд<n>``, ``абз<n>``; Roman
numerals are sections. With one attached document ``S`` == ``A/AN`` == ``A/AN1``.
Opt-in ``--single-annex`` (owner decision 22.10.2026): when a document (the act
``A`` or an attached document ``S<k>``) has exactly one annex in the gold, and
that annex is ``AN`` or ``AN1``, ``<doc>/AN`` == ``<doc>/AN1`` in every variant.
With two or more annexes the numbering must match. Without the flag scores are
those of ``owner-path/2`` as before.
``scope_v2`` is the nearest document or annex (``A``, ``A/AN<n>``, ``S<k>``,
``S<k>/AN<n>``); an error whose gold and predicted ``scope_v2`` differ is a
scope transfer (``cross_scope_v2`` in the error classes; ``first_scope`` and the
old ``cross_scope`` are unchanged).
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
RAZD_SEG = re.compile(r"^разд\d+$")
ATTACHED_SCOPE = re.compile(r"^S\d*$")
ANNEX_SEG = re.compile(r"^AN(\d*)$")


def alias_annex(path):
    """Owner decision: the approved text and the act annex are one kind, so
    ``A/AN`` and ``A/AN1`` -> ``S`` (only meaningful with one attached document)."""
    parts = norm(path).split("/")
    if parts[0] == "A" and len(parts) > 1 and parts[1] in {"AN", "AN1"}:
        return "/".join(["S", *parts[2:]])
    return "/".join(parts)


def first_scope(path):
    """Attached-document scope of an owner path, or None (act ``A`` itself).

    ``S``, ``S2``... are attached documents; ``A/AN<n>`` is annex n to the act
    (``AN1`` is counted as ``S``). ``S/AN4`` is a unit inside the approved text."""
    parts = alias_annex(path).split("/")
    if ATTACHED_SCOPE.match(parts[0]):
        return parts[0]
    if parts[0] == "A" and len(parts) > 1 and ANNEX_SEG.match(parts[1]):
        return f"A/{parts[1]}"
    return None


def attached_count(gold):
    """Number of attached documents in one document's gold."""
    scopes = {first_scope(o) for g in gold.values() for o in g["owners"]}
    scopes.discard(None)
    return len(scopes)


def single_annex_documents(gold):
    """Documents (``A``, ``S``, ``S2``...) whose only annex in the gold is ``AN`` or ``AN1``.

    Annexes are counted per document over all gold owners and alternatives;
    ``AN`` and ``AN1`` count as one annex. A document whose single annex has
    another number (``S/AN4`` only, e.g. a sampled gold) is not included."""
    labels = {}
    for g in gold.values():
        for owner in g["owners"]:
            parts = norm(owner).split("/")
            if len(parts) > 1 and ANNEX_SEG.match(parts[1]):
                labels.setdefault(parts[0], set()).add(parts[1] if parts[1] != "AN" else "AN1")
    return frozenset(doc for doc, found in labels.items() if found == {"AN1"})


def number_single_annex(path, single):
    """``<doc>/AN/...`` -> ``<doc>/AN1/...`` for a document in ``single``."""
    parts = norm(path).split("/")
    if len(parts) > 1 and parts[1] == "AN" and parts[0] in single:
        parts[1] = "AN1"
    return "/".join(parts)


def canonical(path, attached, single=frozenset()):
    """With exactly one attached document ``A/AN``, ``A/AN1`` -> ``S``; with
    ``single`` (``single_annex_documents``) also ``<doc>/AN`` -> ``<doc>/AN1``."""
    if path is None:
        return None
    if single:
        path = number_single_annex(path, single)
    return alias_annex(path) if attached == 1 else norm(path)


def scope_v2(path):
    """Nearest document or annex of a canonical owner path: ``A``, ``A/AN<n>``,
    ``S<k>`` or ``S<k>/AN<n>`` (None for no owner)."""
    if path is None:
        return None
    parts = norm(path).split("/")
    if len(parts) > 1 and ANNEX_SEG.match(parts[1]):
        return "/".join(parts[:2])
    return parts[0]


def cross_scope_v2(gold_path, predicted_path, attached, single=frozenset()):
    """An owner was given, in another document or annex than gold (``scope_v2``)."""
    if predicted_path is None:
        return False
    return scope_v2(canonical(gold_path, attached, single)) != scope_v2(canonical(predicted_path, attached, single))


def equivalent(gold_path, predicted_path, attached_count, name="strict", single=frozenset()):
    if gold_path is None or predicted_path is None:
        return gold_path is predicted_path
    return variant(canonical(gold_path, attached_count, single), name) == variant(
        canonical(predicted_path, attached_count, single), name
    )


def variant(path, name):
    """strict: full path; no_section: drop section segments (Roman numerals and
    ``разд<n>``; some parsers keep points as siblings of section headings);
    numbers: also drop the leading scope letter ``A``/``S`` (``S2`` and the
    annex segment of ``A/AN<n>`` stay)."""
    if path is None or name == "strict":
        return path
    parts = [p for p in path.split("/") if not (ROMAN_SEG.match(p) or RAZD_SEG.match(p))]
    if name == "numbers" and parts and parts[0] in {"A", "S"}:
        parts = parts[1:]
    return "/".join(parts)


def evaluate(gold, predicted, continuation=None, attached=None, single_annex=False):
    if attached is None:
        attached = attached_count(gold)
    result = {"regions": len(gold), "attached_count": attached}
    single = frozenset()
    if single_annex:
        single = single_annex_documents(gold)
        result["single_annex_documents"] = sorted(single)
    for name in ("strict", "no_section", "numbers"):
        ok, rows = 0, []
        for key, g in gold.items():
            p = norm(predicted.get(key))
            hit = any(equivalent(o, p, attached, name, single) for o in g["owners"])
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
    parser.add_argument("--single-annex", action="store_true",
                        help="<doc>/AN == <doc>/AN1 when the document has exactly one annex (owner decision 22.10.2026)")
    args = parser.parse_args(argv)
    with open(args.run, encoding="utf-8") as handle:
        run = json.load(handle)
    if "regions" in run and isinstance(run["regions"], list):
        owners, cont = from_logical(run)
    else:
        owners, cont = run.get("owners", run), run.get("continuation")
    result = evaluate(load_gold(args.gold), owners, cont, single_annex=args.single_annex)
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.output:
        with open(args.output, "x", encoding="utf-8") as handle:
            handle.write(text)
    print(json.dumps({k: v for k, v in result.items() if k != "errors"}, ensure_ascii=False))
    for row in result["errors"][:60]:
        print(f"  {row['region']:>7}  gold={row['gold']:<22} got={row['predicted']}")


if __name__ == "__main__":
    main()
