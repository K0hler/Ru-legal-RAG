"""M1-04A second layer: baseline of a frozen prototype on clean official text (JSON corpus).

Phases (repository root, PYTHONPATH=src;docs/assets; every phase writes once into --out):

  project  per dev act: HTML -> regions (one per paragraph, one per table) -> pseudo extraction in the
           OCR `text-extraction` shape; official tree -> owner-path/2 gold per region; freeze.json
  run      the frozen prototype on every pseudo extraction (sha256 checked), scored against the gold

Gold rules (projection of the IPS tree, not convention v2 itself):
- a region's owner is the deepest covering node; nodes that are not structure for our convention are
  transparent (owner from the parent): attachment captions «Указ», «Преамбула», «Примечание», unknown
  units, and part/point/subpoint nodes whose number is not printed at the start of their first paragraph;
- attachment (`вложение`) at level 0 -> S, S2, ...; nested -> <parent>/AN<k>; `приложение` -> <parent>/AN<n>;
- статья -> ст<N>, глава -> гл<N>, часть -> ч<N>, § -> §<N>, раздел/подраздел -> roman (digits: разд<N>),
  code-level «ЧАСТЬ ПЕРВАЯ…» -> разд<N>; superscripts are written `^k` (prototype output normalised alike).
Pseudo layout: 10 regions per A4 page; CSS classes T/Z/H -> Section-header, tables -> Table, else Text;
alignment from the class (S/R right, C/T/Z/E centre) sets bbox x.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from evaluate_ocr_owner_gold import evaluate

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data/m1/m1-04a/json-corpus/20261025-v1"
SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
REGIONS_PER_PAGE = 10
PAGE = [1654, 2339]
HEADER_CLASSES = {"T", "Z", "H"}
RIGHT_CLASSES = {"S", "R"}
CENTRE_CLASSES = {"C", "T", "Z", "E"}
TRANSPARENT_CAPTIONS = {"указ", "преамбула", "примечание"}
ORDINALS = {"первая": 1, "вторая": 2, "третья": 3, "четвертая": 4, "четвёртая": 4, "пятая": 5,
            "шестая": 6, "седьмая": 7, "восьмая": 8, "девятая": 9, "десятая": 10}
ROMAN = re.compile(r"^[IVXLC]+$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_once(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(data)


SUP_MINUS = "⁻"


def sup_text(digits: str) -> str:
    """Digits (and, projection 3, hyphens of a compound index «1-1») as Unicode superscripts."""
    return "".join(SUP_MINUS if c in "-–" else SUP[int(c)] for c in digits)


def norm_sup(path: str | None) -> str | None:
    """Unicode superscripts -> ^k (a compound «¹⁻¹» -> ^1-1) so prototype and gold spell inserted numbers alike."""
    if path is None:
        return None
    return re.sub(rf"([{SUP}][{SUP}{SUP_MINUS}]*)",
                  lambda m: "^" + "".join("-" if c == SUP_MINUS else str(SUP.index(c)) for c in m.group(1)), path)


def roman_value(text: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    return sum(-values[c] if i + 1 < len(text) and values[text[i + 1]] > values[c] else values[c]
               for i, c in enumerate(text))


# ------------------------------------------------------------------ HTML -> regions


def flat_text(element) -> str:
    """Element text without separators between inline nodes (keeps «29¹.» whole); <br> became a
    line break as in OCR text; spaces inside lines collapsed."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in element.get_text("").split("\n")]
    return "\n".join(line for line in lines if line)


def html_regions(html: str, compound_sup: bool = False):
    """Regions in document order: each id'd <p> outside tables, each table with id'd rows. With
    ``compound_sup`` (projection 3) a compound index «1-1» (Budget Code «Статья 115¹⁻¹») is kept as
    superscripts too; projections 1-2 flattened it to «1151-1»."""
    soup = BeautifulSoup(html, "html.parser")
    # Superscripts are <sup> or spans whose class has vertical-align:super in the document CSS (W9, WB).
    super_classes = set(re.findall(r"\.(\w+)\s*\{[^}]*vertical-align:\s*super", html))
    marks = soup.find_all("sup") + [e for e in soup.find_all("span") if super_classes & set(e.get("class") or [])]
    for s in marks:
        mark = s.get_text()
        index = mark.isdigit() or (compound_sup and re.fullmatch(r"\d+(?:[-–]\d+)+", mark) is not None)
        s.replace_with(sup_text(mark) if index else mark)
    for br in soup.find_all("br"):
        br.replace_with("\n")
    regions, seen_tables = [], set()
    for e in soup.find_all(id=re.compile(r"^[pr]\d+$")):
        table = e.find_parent("table")
        if table is not None:
            if id(table) in seen_tables:
                continue
            seen_tables.add(id(table))
            rows = [r for r in table.find_all(id=re.compile(r"^[pr]\d+$"))]
            text = " | ".join(" ".join(flat_text(c) for c in r.find_all(["td", "th"])) or flat_text(r) for r in rows)
            regions.append({"kind": "table", "ids": [r["id"] for r in rows], "cls": "", "text": text})
        else:
            text = flat_text(e)
            regions.append({"kind": "p", "ids": [e["id"]], "cls": " ".join(e.get("class") or []), "text": text})
    return [r for r in regions if r["text"].replace("|", "").strip()]


def paragraph_order(html: str):
    soup = BeautifulSoup(html, "html.parser")
    return {e["id"]: i for i, e in enumerate(soup.find_all(id=re.compile(r"^[pr]\d+$")))}


# ------------------------------------------------------------------ tree -> owner paths


def split_number(text: str):
    """'11<sup>1</sup>' / '11' -> ('11', '1' | None)."""
    m = re.match(r"^\s*([\dIVXLC]+(?:\.\d+)*|[а-я])(?:<sup>(\d+)</sup>)?", text)
    return (m.group(1), m.group(2)) if m else (None, None)


def printed(first_text: str, number: str, sup: str | None) -> str | None:
    """The delimiter («.» or «)») after the node's number at the start of its first paragraph, else None."""
    mark = re.escape(number) + (re.escape(sup_text(sup)) if sup else "")
    m = re.match(rf"^\s*{mark}\s*([.)])", first_text.replace("\xa0", " "))
    return m.group(1) if m else None


def node_paths(nodes, order, first_text, projection=1):
    """Per node: owner path (None = transparent), using non-transparent ancestors; with projection 2
    also an alternative owner for unprinted parts/points (the previous printed sibling)."""
    stack, out, alts = [], {}, {}
    last_child: dict = {}
    attached = 0
    child_annexes: Counter = Counter()
    for n in nodes:
        del stack[n["lvl"]:]
        parent = next((s["path"] for s in reversed(stack) if s["path"] is not None), "A")
        sibling_key = stack[-1]["id"] if stack else None
        unit, cap = n.get("unit", ""), n["caption"]
        seg = None
        if unit == "вложение":
            own_caption = projection >= 4 and re.match(r"^УТВЕРЖДЕН", first_text.get(n["np"], ""))
            if cap.strip().lower() in TRANSPARENT_CAPTIONS:
                seg = None
            elif parent == "A" or own_caption:
                # projection 4: a document with its own approval caption is attached to the act even when
                # IPS nests it in the previous document (convention v2 §6.1)
                attached += 1
                n["path"] = "S" if attached == 1 else f"S{attached}"
                stack.append(n)
                out[n["id"]] = n["path"]
                continue
            else:
                child_annexes[parent] += 1
                seg = f"AN{child_annexes[parent]}"
        elif unit == "приложение":
            m = re.search(r"№\s*(\d+)", cap)
            child_annexes[parent] += 1
            seg = f"AN{m.group(1) if m else child_annexes[parent]}"
        elif unit == "статья":
            index = r"\d+(?:-\d+)*" if projection >= 3 else r"\d+"  # projection 3: «115<sup>1-1</sup>»
            m = re.match(rf"^(?:Статья|СТАТЬЯ)\s+(\d+(?:\.\d+)*)(?:<sup>({index})</sup>)?", cap)
            seg = f"ст{m.group(1)}" + (f"^{m.group(2)}" if m.group(2) else "") if m else None
        elif unit == "глава":
            m = re.match(r"^(?:Глава|ГЛАВА)\s+(\d+|[IVXLC]+)(?:<sup>(\d+)</sup>)?", cap)
            if m:
                value = m.group(1) if m.group(1).isdigit() else str(roman_value(m.group(1)))
                seg = f"гл{value}" + (f"^{m.group(2)}" if m.group(2) else "")
        elif unit in ("раздел", "подраздел"):
            m = re.match(r"^(Раздел|РАЗДЕЛ|Подраздел|ПОДРАЗДЕЛ)?\s*(\d+|[IVXLC]+)(?:<sup>(\d+)</sup>)?", cap)
            if m:
                # projection 5: a bare «1.» without the word «Раздел» is a point (convention v2 §6.1, 26.10.2026)
                point = projection >= 5 and m.group(2).isdigit() and not m.group(1)
                seg = (m.group(2) if ROMAN.match(m.group(2)) or point else f"разд{m.group(2)}") + (
                    f"^{m.group(3)}" if m.group(3) else "")
        elif unit == "§":
            m = re.match(r"^§\s*(\d+)", cap)
            seg = f"§{m.group(1)}" if m else None
        elif unit == "часть":
            m = re.match(r"^ЧАСТЬ\s+([А-ЯЁ]+)", cap)
            if m and m.group(1).lower() in ORDINALS:
                seg = f"разд{ORDINALS[m.group(1).lower()]}"
            else:
                number, sup = split_number(cap.removeprefix("часть "))
                if number and printed(first_text.get(n["np"], ""), number, sup):
                    seg = f"ч{number}" + (f"^{sup}" if sup else "")
                elif number and projection >= 2:
                    alts[n["id"]] = last_child.get(sibling_key)
        elif unit in ("пункт", "подпункт"):
            number, sup = split_number(cap.removeprefix(unit + " ").strip().strip('"').replace('"', ""))
            delim = printed(first_text.get(n["np"], ""), number, sup) if number else None
            if delim:
                seg = number + (f"^{sup}" if sup else "")
                # Projection 2: «N.» directly inside an article of the act's own text is a part (convention
                # v2 §4 note; the IPS tree calls it «пункт» in some codes and laws).
                if (projection >= 2 and unit == "пункт" and delim == "." and parent.split("/")[0] == "A"
                        and parent.split("/")[-1].startswith("ст")):
                    seg = "ч" + seg
            elif number and projection >= 2:
                alts[n["id"]] = last_child.get(sibling_key)
        n["path"] = parent + "/" + seg if seg else None
        if n["path"]:
            last_child[sibling_key] = n["path"]
        stack.append(n)
        out[n["id"]] = n["path"]
    return (out, alts) if projection >= 2 else out


def paragraph_owners(nodes, order, first_text, projection=1):
    if projection < 2:
        paths = node_paths(nodes, order, first_text)
        fill = ["A"] * len(order)
        # Shallow nodes first, deeper ones overwrite: each paragraph keeps its deepest non-transparent node.
        for n in sorted(nodes, key=lambda n: n["lvl"]):
            if paths.get(n["id"]) and n["np"] in order and n["npe"] in order:
                for i in range(order[n["np"]], order[n["npe"]] + 1):
                    fill[i] = paths[n["id"]]
        return {pid: fill[i] for pid, i in order.items()}
    paths, alts = node_paths(nodes, order, first_text, projection)
    fill = [("A", None)] * len(order)
    for n in sorted(nodes, key=lambda n: n["lvl"]):
        if n["np"] not in order or n["npe"] not in order:
            continue
        for i in range(order[n["np"]], order[n["npe"]] + 1):
            if paths.get(n["id"]):
                fill[i] = (paths[n["id"]], None)
            elif alts.get(n["id"]):
                fill[i] = (fill[i][0], alts[n["id"]])
    return {pid: fill[i] for pid, i in order.items()}


# ------------------------------------------------------------------ projection 4 (convention v2 §6.1)

STRUCTURE_UNITS = {"пункт", "подпункт", "раздел", "подраздел", "статья", "глава", "часть", "§"}
NUMBERED = re.compile(r"^\s*(?:\d{1,3}[¹²³⁴⁵⁶⁷⁸⁹⁰]*[.)]|[IVXLC]+\.|[а-я]\))\s")
LIST_ITEM = re.compile(r"^\s*(?:\d+|[а-я])[¹²³⁴⁵⁶⁷⁸⁹⁰⁻]*\)\s")
SCOPE_SEGMENT = re.compile(r"^(?:A|S\d*|AN\d*)$")


def tree_children(nodes):
    stack, kids = [], {n["id"]: [] for n in nodes}
    for n in nodes:
        del stack[n["lvl"]:]
        if stack:
            kids[stack[-1]["id"]].append(n)
        stack.append(n)
    return kids


def unstructured_documents(nodes, order, text):
    """Paragraph ids of attached documents (forms, agreements) that IPS leaves without inner structure
    although their own text is numbered: IPS gives no evidence there, so they are not scored."""
    ids = sorted(order, key=order.get)
    kids, excluded = tree_children(nodes), set()
    for n in nodes:
        if n.get("unit") not in ("вложение", "приложение") or n["np"] not in order or n["npe"] not in order:
            continue
        if any(c.get("unit") in STRUCTURE_UNITS for c in kids[n["id"]]):
            continue
        inner = set()
        for c in kids[n["id"]]:
            if c["np"] in order and c["npe"] in order:
                inner |= set(range(order[c["np"]], order[c["npe"]] + 1))
        own = [i for i in range(order[n["np"]], order[n["npe"]] + 1) if i not in inner]
        if sum(bool(NUMBERED.match(text.get(ids[i], ""))) for i in own) >= 2:
            excluded |= {ids[i] for i in own}
    return excluded


def after_last_item(nodes, order, text, paths):
    """Paragraphs after the first one of a final «N)»/«а)» list item, from the first capitalised sentence
    after a full stop: the parent owns them (convention v2 §6.1); IPS stretches the item's range, so the
    item stays an accepted alternative. Returns pid -> (parent path, item path)."""
    ids = sorted(order, key=order.get)
    kids, out = tree_children(nodes), {}
    for parent in nodes:
        items = kids[parent["id"]]
        if not items:
            continue
        last = items[-1]
        path = paths.get(last["id"])
        if (not path or "/" not in path or last["np"] not in order or last["npe"] not in order
                or not LIST_ITEM.match(text.get(last["np"], ""))
                or text.get(last["np"], "").rstrip().endswith(":")):
            continue  # an item ending «:» introduces its own content (a list or an amending quotation)
        start, end = order[last["np"]], order[last["npe"]]
        closed = False
        for i in range(start + 1, end + 1):
            t, before = text.get(ids[i], ""), text.get(ids[i - 1], "")
            if (not closed and t[:1].isupper() and not t.startswith("(") and not LIST_ITEM.match(t)
                    and re.sub(r"\s*\([^()]*\)\s*$", "", before).rstrip().endswith(".")):
                closed = True
            if closed:
                out[ids[i]] = (path.rsplit("/", 1)[0], path)
    return out


def scope_root(path: str) -> str:
    parts = path.split("/")
    keep = max(k for k, s in enumerate(parts) if SCOPE_SEGMENT.match(s))
    return "/".join(parts[:keep + 1])


# ------------------------------------------------------------------ phases


def pseudo_extraction(slug, regions):
    pages, blocks, text_nodes = [], [], []
    for i, r in enumerate(regions):
        page_no, index = i // REGIONS_PER_PAGE + 1, i % REGIONS_PER_PAGE
        if index == 0:
            pages.append({"page": page_no, "image_size": PAGE, "regions": []})
        x0 = 1000 if r["cls"] in RIGHT_CLASSES else 500 if r["cls"] in CENTRE_CLASSES else 150
        category = "Table" if r["kind"] == "table" else "Section-header" if r["cls"] in HEADER_CLASSES else "Text"
        rid = f"r{i}"
        y0 = 150 + index * 200
        pages[-1]["regions"].append({"region_id": rid, "category": category, "bbox": [x0, y0, 1500, y0 + 150]})
        blocks.append({"source_region_id": rid, "original_text": r["text"], "text_node_ids": [f"t{i}"]})
        text_nodes.append({"text_node_id": f"t{i}"})
    return {"schema_version": "m1-04a-json-pseudo-extraction/1", "source_asset_sha256": sha(slug.encode()),
            "pages": pages, "blocks": blocks, "text_nodes": text_nodes}


def split_slugs(split: dict, part: str) -> list[str]:
    """Acts of a corpus part; ``all`` is dev then holdout (the holdout is development since its measure, 25.10.2026)."""
    return split["dev"] + split["holdout"] if part == "all" else split[part]


def phase_project(out: Path, projection: int = 1, part: str = "dev"):
    split = json.loads((CORPUS / "split.json").read_text(encoding="utf-8"))
    files, stats = {}, {}
    for slug in split_slugs(split, part):
        doc = CORPUS / "docs" / slug
        html = (doc / "document.html").read_text(encoding="utf-8")
        nodes = json.loads((doc / "document_content.json").read_text(encoding="utf-8"))["data"]
        order = paragraph_order(html)
        regions = html_regions(html, compound_sup=projection >= 3)
        first_text = {pid: r["text"] for r in regions for pid in r["ids"][:1]}
        owners = paragraph_owners(nodes, order, first_text, projection)
        excluded, trailing = set(), {}
        if projection >= 4:
            text = {pid: r["text"] for r in regions for pid in r["ids"]}
            excluded = unstructured_documents(nodes, order, text)
            paths, _ = node_paths(nodes, order, first_text, projection)
            trailing = {pid: pair for pid, pair in after_last_item(nodes, order, text, paths).items()
                        if pid in owners and owners[pid][0] == pair[1]}
        header = "# convention: projected IPS tree (m1_04a_json_baseline.py)"
        if projection >= 2:
            header += f", projection {projection}"
        gold, last = [header], "A"
        for i, r in enumerate(regions):
            key = f"{i // REGIONS_PER_PAGE + 1}.{i % REGIONS_PER_PAGE}"
            if projection < 2:
                owner = Counter(owners.get(pid, last) for pid in r["ids"]).most_common(1)[0][0]
                gold.append(f"{key} {owner}")
            else:
                owner = Counter(owners[pid][0] if pid in owners else last for pid in r["ids"]).most_common(1)[0][0]
                alt = owners[r["ids"][0]][1] if r["ids"][0] in owners else None
                if projection >= 4:
                    if r["ids"][0] in excluded:
                        last = owner
                        continue  # inside a form/agreement IPS does not structure: no evidence
                    if r["ids"][0] in trailing:
                        owner, alt = trailing[r["ids"][0]]
                    if re.fullmatch(r"[_\s]+", r["text"]):
                        owner, alt = scope_root(last), None  # a separator marks its document's page (§2)
                gold.append(f"{key} {owner}" + (f"|{alt}" if alt and alt != owner else ""))
            last = owner
        extraction = pseudo_extraction(slug, regions)
        for name, value in ((f"{slug}/extraction.json", extraction),
                            (f"{slug}/gold.txt", ("\n".join(gold) + "\n").encode())):
            write_once(out / name, value)
            files[name] = sha((out / name).read_bytes())
        stats[slug] = {"regions": len(regions), "tables": sum(r["kind"] == "table" for r in regions),
                       "owners": len(set(gold[1:]))}
        print(slug, stats[slug], flush=True)
    write_once(out / "freeze.json", {"schema_version": "m1-04a-json-baseline-freeze/1", "projection": projection,
                                     "split_sha256": sha((CORPUS / "split.json").read_bytes()),
                                     **({"split_part": part} if part != "dev" else {}),
                                     "script_sha256": sha(Path(__file__).read_bytes()), "files": files,
                                     "stats": stats})


def phase_run(out: Path, label: str, prototype: Path, expected_sha: str):
    freeze = json.loads((out / "freeze.json").read_text(encoding="utf-8"))
    for name, digest in freeze["files"].items():
        if sha((out / name).read_bytes()) != digest:
            raise SystemExit(f"frozen file changed: {name}")
    if sha(prototype.read_bytes()) != expected_sha:
        raise SystemExit("prototype hash differs from the frozen copy")
    rows = {}
    for slug in freeze["stats"]:
        result_path = out / label / f"{slug}.json"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run([sys.executable, str(prototype), "--input", str(out / slug / "extraction.json"),
                               "--output", str(result_path)], capture_output=True, text=True)
        if proc.returncode:
            rows[slug] = {"error": proc.stderr.strip().splitlines()[-1] if proc.stderr else "failed"}
            print(slug, "ERROR", rows[slug]["error"], flush=True)
            continue
        run = json.loads(result_path.read_text(encoding="utf-8"))
        predicted = {f"{r['page']}.{r['index']}": norm_sup(r["owner"]) for r in run["regions"]}
        gold = {}
        for line in (out / slug / "gold.txt").read_text(encoding="utf-8").splitlines()[1:]:
            key, owner = line.split()
            gold[key] = {"owners": owner.split("|"), "continuation": False}
        res = evaluate(gold, predicted, single_annex=True, attached_ordinal=True)
        rows[slug] = {"regions": res["regions"], **{v: res[v]["correct"] for v in ("strict", "no_section", "numbers")},
                      "errors": res["errors"]}
        print(slug, res["regions"], res["no_section"], flush=True)
    ok = {s: r for s, r in rows.items() if "error" not in r}
    total = sum(r["regions"] for r in ok.values())
    summary = {"label": label, "prototype_sha256": expected_sha, "documents": len(rows), "failed": len(rows) - len(ok),
               "regions": total}
    for v in ("strict", "no_section", "numbers"):
        summary[v] = {"micro": round(sum(r[v] for r in ok.values()) / total, 4),
                      "macro": round(statistics.mean(r[v] / r["regions"] for r in ok.values()), 4),
                      "perfect_documents": sum(r[v] == r["regions"] for r in ok.values())}
    write_once(out / f"{label}-results.json", {"summary": summary, "documents": rows})
    print(json.dumps(summary, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("project", "run"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default="v5")
    parser.add_argument("--projection", type=int, choices=(1, 2, 3, 4, 5), default=5,
                        help="1: the frozen 20261025 run; 2: «N.» in an article -> ч<N>, unprinted parts/points "
                             "also accept the previous printed sibling; 3: 2 + compound superscript indices "
                             "(«Статья 115¹⁻¹», `ст115^1-1`) in text and gold; 4: 3 + convention v2 §6.1 (unstructured "
                             "forms/agreements not scored, abzac after the last list item -> parent|item, separator "
                             "-> its document, own approval caption -> separate document); 5: 4 + a bare numbered «1.» "
                             "(sub)section (no word «Раздел») is a point (convention v2 §6.1, 26.10.2026)")
    parser.add_argument("--split", choices=("dev", "holdout", "all"), default="dev",
                        help="corpus part to project; the holdout was measured once (25.10.2026) and is development "
                             "now; all: the 100 acts, dev then holdout")
    parser.add_argument("--prototype")
    parser.add_argument("--prototype-sha256")
    args = parser.parse_args(argv)
    out = Path(args.out)
    if args.phase == "project":
        phase_project(out, args.projection, args.split)
    else:
        phase_run(out, args.label, Path(args.prototype), args.prototype_sha256)


if __name__ == "__main__":
    main()
