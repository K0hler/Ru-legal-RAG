"""Export ``{"page.index": owner_path}`` maps from the current OCR parser and Dedoc runs.

The paths use the gold syntax of ``evaluate_ocr_owner_gold.py``. Adapters only
rename existing addresses/tree nodes; they never infer a new parent.

* current: ``legal_rag.corpus.ocr_structure.build_ocr_structure`` region bindings;
  unresolved/excluded regions map to ``null``.
* dedoc: retained ``parsed-1.json`` API tree; a region belongs to the nearest
  numbered node (item/subitem/chapter/application) that carries its source uid.
"""

from __future__ import annotations

import argparse
import json
import re

ROMAN = re.compile(r"^([IVXLCХ]+)\.\s")


def roman_label(text):
    m = ROMAN.match(text.strip())
    if not m:
        return None
    s = m.group(1).replace("Х", "X")
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = sum(-vals[c] if i + 1 < len(s) and vals[s[i + 1]] > vals[c] else vals[c] for i, c in enumerate(s))
    out = ""
    for v, r in ((100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while total >= v:
            out, total = out + r, total - v
    return out


def region_keys(extraction):
    return {r["region_id"]: f"{p['page']}.{i}" for p in extraction["pages"] for i, r in enumerate(p["regions"])}


# ---------------------------------------------------------------- current parser

STOP = {"paragraph", "heading", "metadata", "table", "footnote", "note", "image", "title", "caption", "header",
        "signature", "quote", "text", "unresolved"}


def current_path(address, namespace="act"):
    if address is None:
        return None
    if not (address == namespace or address.startswith(namespace + "/")):
        return None
    seg = ["act"] + address[len(namespace):].strip("/").split("/") if address != namespace else ["act"]
    seg = [x for x in seg if x != ""]
    out = ["A"]
    i = 1
    while i + 1 < len(seg) + 1 and i < len(seg):
        kind = seg[i]
        value = seg[i + 1] if i + 1 < len(seg) else None
        if kind in STOP:
            break
        if kind == "approved":
            out[0] = "S" if value in (None, "1") else f"S{value}"
        elif kind == "annex":
            out.append(f"AN{value}" if value and value not in {"0"} else "AN")
        elif kind == "unnumbered_annex":
            out.append("AN")
        elif kind in {"section", "chapter"}:
            out.append(roman_label(f"{value}. x") or value)
        else:
            out.append(value)
        i += 2
    return "/".join(out)


def export_current(extraction, claim, role):
    from legal_rag.corpus.ocr_structure import build_ocr_structure

    tree = build_ocr_structure(extraction, claim, role)
    keys = region_keys(extraction)
    return {keys[b["region_id"]]: current_path(b["address"], tree["namespace"]) for b in tree["region_bindings"]}, {
        "nodes": len(tree["nodes"]), "unresolved_blocks": len(tree["unresolved_blocks"]),
        "parser_version": tree["parser_version"], "identity": tree["identity_decision"]["status"]}


# ---------------------------------------------------------------- dedoc

def dedoc_label(node, state):
    kind = node["metadata"].get("paragraph_type")
    text = node["text"].strip()
    if kind == "application":
        if re.search(r"УТВЕРЖДЕН", text[:40]) and not state["approved"]:
            state["approved"] = True
            return ("scope", "S")
        m = re.match(r"^(?:Приложение|ПРИЛОЖЕНИЕ)\s*(?:№\s*(\d+))?", text)
        return ("annex", f"AN{m.group(1)}" if m and m.group(1) else "AN")
    if kind in {"chapter", "section", "subsection", "раздел", "глава"}:
        return ("label", roman_label(text) or text[:12])
    if kind in {"item", "subitem", "subsubitem", "articlePart", "article", "paragraph", "subparagraph", "part",
                "пункт", "подпункт", "статья"}:
        m = re.match(r"^(\d+(?:\.\d+)*)\.?\s*$|^(\d+(?:\.\d+)*)[.)]|^([а-я])\)", text)
        if m:
            return ("label", m.group(1) or m.group(2) or m.group(3))
        return ("label", text[:8])
    return (None, None)


def export_dedoc(parsed, extraction):
    keys = region_keys(extraction)
    owners = {}
    state = {"approved": False}

    def walk(node, path):
        kind, value = dedoc_label(node, state)
        if kind == "scope":
            path = [value]
        elif kind == "annex":
            path = ["S" if state["approved"] else "A", value]
        elif kind == "label":
            path = path + [value]
        for ann in node.get("annotations", []):
            if ann["name"] == "dots_source_uid":
                rid = ann["value"].split(":")[0]
                owners.setdefault(keys.get(rid, rid), "/".join(path))
        for child in node["subparagraphs"]:
            walk(child, path)

    walk(parsed["content"]["structure"], ["A"])
    return owners


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction", required=True)
    parser.add_argument("--system", choices=["current", "dedoc"], required=True)
    parser.add_argument("--claim")
    parser.add_argument("--role", default="original")
    parser.add_argument("--dedoc-parsed")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    with open(args.extraction, encoding="utf-8") as handle:
        extraction = json.load(handle)
    if args.system == "current":
        owners, meta = export_current(extraction, args.claim, args.role)
    else:
        with open(args.dedoc_parsed, encoding="utf-8") as handle:
            parsed = json.load(handle)
        owners, meta = export_dedoc(parsed, extraction), {"dedoc_parsed": args.dedoc_parsed}
    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump({"owners": owners, "meta": meta}, handle, ensure_ascii=False, indent=1, sort_keys=True)


if __name__ == "__main__":
    main()
