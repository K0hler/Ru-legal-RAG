"""Replay retained inputs against the owner-approved source-preserving contract."""

import copy
from datetime import UTC, datetime
import hashlib
import heapq
import json
from pathlib import Path
import re
import sys

from bs4 import BeautifulSoup

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from legal_rag.corpus.compiler import compile_input, load_input  # noqa: E402
from legal_rag.corpus.official_import import VERSION  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files(root):
    return {str(p): sha(p) for p in root.rglob("*") if p.is_file()}


def write(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify(tree, html, rows):
    """BS4 DOM plus raw slices; no reconstruction/parser/audit helpers."""
    soup = BeautifulSoup(html, "html.parser")
    line_starts = [0, *(m.end() for m in re.finditer("\n", html))]
    anchors = {}
    for tag in soup.find_all(id=True):
        start = line_starts[tag.sourceline - 1] + tag.sourcepos
        end = html.index(">", start) + 1
        if not tag.is_empty_element:
            depth = 1
            pattern = re.compile(r"</?" + re.escape(tag.name) + r"\b[^>]*>", re.I)
            for match in pattern.finditer(html, end):
                depth += -1 if match[0].startswith("</") else 1
                if depth == 0:
                    end = match.end()
                    break
            else:
                raise AssertionError("unclosed independent DOM anchor")
        assert tag["id"] not in anchors
        anchors[tag["id"]] = (start, end)
    units = [n for n in tree["nodes"] if n["kind"] == "source_unit"]
    assert [n["source_record"] for n in units] == rows, "source records/order"
    assert [n["source_id"] for n in units] == [r["id"] for r in rows], "source IDs"
    stack, parents, bad, prior, spans = [], {}, set(), {}, {}
    for row, node in zip(rows, units, strict=True):
        while len(stack) > row["lvl"]:
            stack.pop()
        assert len(stack) == row["lvl"]
        parent = stack[-1] if stack else None
        pid = parent["source_id"] if parent else None
        parents[row["id"]] = pid
        assert node["parent_source_id"] == pid
        assert node["parent_address"] == (parent["address"] if parent else "act"), "parent"
        assert node["caption"] == row["caption"] and node["source_unit"] == row["unit"]
        assert node["number_canonical"] is None
        assert node["source_structure_evidence"]["json_pointer"] == f"/data/{len(parents)-1}"
        pair = (anchors[row["np"]][0], anchors[row["npe"]][1]) if all(row[k] in anchors for k in ("np", "npe")) else None
        spans[row["id"]] = pair
        if pair is None:
            bad.add(row["id"])
            assert node["source_span"] is None, "invented range"
        else:
            assert (node["source_span"]["char_start"], node["source_span"]["char_end"]) == pair, "range"
            if pair[0] >= pair[1] or pid and spans[pid] and not (spans[pid][0] <= pair[0] < pair[1] <= spans[pid][1]):
                bad.add(row["id"])
            previous = prior.get(pid)
            if previous and spans[previous] and spans[previous][1] > pair[0]:
                bad.update((previous, row["id"]))
        previous = prior.get(pid)
        if pair and pair[0] < pair[1] and (previous is None or pair[1] > spans[previous][1]):
            prior[pid] = row["id"]
        stack.append(node)
    for row in rows:
        if parents[row["id"]] in bad:
            bad.add(row["id"])
    assert {f["source_id"] for f in tree["source_integrity"]["findings"]} == bad, "integrity warnings"
    assert {n["source_id"] for n in units if n["range_status"] == "unresolved"} == bad
    assert bool(tree["structural_issues"]) == bool(bad)
    lexical = sorted([n for n in [*tree["nodes"], *tree["excluded_blocks"]] if n.get("block_id") is not None],
                     key=lambda n: n["source_span"]["char_start"])
    assert len({n["block_id"] for n in lexical}) == len(lexical)
    def compact(value):
        return "".join(value.split())
    normative = [n for n in lexical if not n.get("exclusion_reason")]
    for n in normative:
        s = n["source_span"]
        fragment = html[s["char_start"]:s["char_end"]]
        expected = compact(BeautifulSoup(fragment, "html.parser").get_text())
        assert compact(n["text"]) == expected, "text/coordinate"
        assert compact(n["original_text"]) == expected, "original text"
        assert n["original_html"] == html[n["html_start"]:n["html_end"]], "original HTML"
    for tag in list(soup.select("script, style, label")):
        tag.decompose()
    assert compact("".join(n["text"] for n in normative)) == compact(soup.body.get_text()), "full document text"
    regions = [n for n in tree["nodes"] if n["kind"] in {"table", "image"}]
    assert len(regions) == len(soup.select("table, img")), "media count"
    for n in regions:
        s = n["source_span"]
        assert n["original_html"] == html[s["char_start"]:s["char_end"]], "media HTML"
    by_address = {n["address"]: n for n in tree["nodes"]}
    assert len(by_address) == len(tree["nodes"])
    intervals = sorted(((*spans[n["source_id"]], n["level"], n["address"]) for n in units
                        if n["source_id"] not in bad), key=lambda value: value[0])
    active, expires, cursor = {}, [], 0
    for node in sorted([*[n for n in normative if "parent_address" in n], *regions],
                       key=lambda n: n["source_span"]["char_start"]):
        start, end = (node["source_span"][key] for key in ("char_start", "char_end"))
        while cursor < len(intervals) and intervals[cursor][0] <= start:
            entry = intervals[cursor]
            active[entry[3]] = entry
            heapq.heappush(expires, (entry[1], entry[3]))
            cursor += 1
        while expires and expires[0][0] <= start:
            _, address = heapq.heappop(expires)
            active.pop(address, None)
        owner = max((entry for entry in active.values() if entry[1] >= end),
                    key=lambda entry: entry[2], default=None)
        expected = owner[3] if owner else "act"
        assert node.get("source_container_address", node["parent_address"]) == expected, "source owner"
        physical = min((n for n in regions if n["kind"] == "table"
                        and n["source_span"]["char_start"] <= start < end <= n["source_span"]["char_end"]),
                       key=lambda n: n["source_span"]["char_end"] - n["source_span"]["char_start"], default=None)
        assert node["parent_address"] == (physical["address"] if physical and node["kind"] == "table_cell" else expected), "physical owner"
    children = {}
    for node in tree["nodes"]:
        children.setdefault(node["parent_address"], []).append(node["address"])
    for n in tree["nodes"]:
        expected = sorted(children.get(n["address"], []),
                          key=lambda a: (by_address[a].get("source_span") or {}).get("char_start", -1))
        assert n["children"] == expected, "children/source order"
    assert tree["accounting"]["exactly_once"] and tree["accounting"]["regions_exactly_once"]
    assert not tree["unresolved_blocks"] and not tree["unresolved_regions"]
    return {"source_nodes": len(units), "lexical_blocks": len(lexical), "regions": len(regions),
            "source_integrity_affected_nodes": len(bad), "full_text": True, "source_records_and_parents": True}


def main(out):
    out.mkdir(parents=True, exist_ok=False)
    roots = [PROJECT / "data/m1/pilot_runs" / name for name in (
        "official-json-qualification-20261016-v1", "official-json-transfer-20261016-v1",
        "independent-structure-audit-20261015-v2")]
    inputs = [p for root in roots for p in sorted(root.glob("*/archive/input.json"))]
    protected = {k: v for root in roots for k, v in files(root).items()}
    code = {str(p): sha(p) for p in [*PROJECT.glob("src/**/*.py"), Path(__file__)]}
    write(out / "freeze.json", {"at": datetime.now(UTC).isoformat(), "version": VERSION,
        "scope": "Retained regression replay; owner-approved contract change, not fresh heldout qualification.",
        "code_sha256": code, "protected_sha256": protected, "inputs": [str(p) for p in inputs]})
    results = []
    for index, path in enumerate(inputs):
        key = path.parent.parent.name
        destination = out / f"{index:02d}-{key}"
        date = json.loads(path.read_bytes())["target_dates"][0]
        manifest, raw, _ = load_input(path, date)
        asset = next(a for a in manifest["assets"] if a["role"] == "consolidated")
        field = asset["evidence"]["locator"].removeprefix("$.").removeprefix("/")
        html = json.loads(raw[asset["sha256"]])[field]
        rows = json.loads(raw[manifest["structure_bundle"]["structure_sha256"]])["data"]
        a = compile_input(path, date, destination / "a")
        b = compile_input(path, date, destination / "b")
        assert a["draft_id"] == b["draft_id"]
        assert compile_input(path, date, destination / "a") == {**a, "result": "unchanged"}
        assert {Path(k).relative_to(destination / "a"): v for k, v in files(destination / "a").items()} == {
            Path(k).relative_to(destination / "b"): v for k, v in files(destination / "b").items()}
        draft = json.loads(Path(a["draft"]).read_bytes())
        tree = draft["content"]["trees"][0]
        checks = verify(tree, html, rows)
        assert draft["legal_admission"] == "not_requested"
        caught = []
        if index == 0:
            for mutation in ("source_record", "parent", "text", "coordinate", "missing_node", "text_owner"):
                changed = copy.deepcopy(tree)
                unit = next(n for n in changed["nodes"] if n["kind"] == "source_unit" and n["parent_address"] != "act")
                block = next(n for n in changed["nodes"] if n["kind"] == "paragraph" and n["parent_address"] != "act")
                if mutation == "source_record":
                    unit["source_record"]["caption"] = "CORRUPTED"
                elif mutation == "parent":
                    unit["parent_address"] = "act"
                elif mutation == "text":
                    block["text"] += "CORRUPTED"
                elif mutation == "coordinate":
                    block["source_span"]["char_start"] += 1
                elif mutation == "missing_node":
                    changed["nodes"].remove(unit)
                else:
                    block["parent_address"] = block["source_container_address"] = "act"
                    for n in changed["nodes"]:
                        n["children"] = [a for a in n["children"] if a != block["address"]]
                try:
                    verify(changed, html, rows)
                except AssertionError:
                    caught.append(mutation)
            assert len(caught) == 6
        result = {"input": str(path), "document": key, "draft": a["draft"], "status": "pass",
                  "repeat_identical": True, "checks": checks, "mutations_caught": caught}
        write(destination / "checks.json", result)
        results.append(result)
        print(key, checks, flush=True)
    assert all(sha(p) == digest for p, digest in {**protected, **code}.items())
    write(out / "results.json", {"schema_version": "official-import-replay/1", "status": "pass",
        "version": VERSION, "documents": results, "passed": len(results), "protected_unchanged": len(protected),
        "code_unchanged": len(code), "closed_gold_access": False, "legal_admission": False})


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
