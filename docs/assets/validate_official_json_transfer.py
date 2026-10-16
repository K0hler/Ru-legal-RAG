"""Offline independent-control preparation and frozen six-act full compiler replay."""

import argparse
from collections import Counter
from datetime import UTC, datetime
import importlib.util
import json
from pathlib import Path
import sys

from bs4 import BeautifulSoup

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from legal_rag.corpus.compiler import compile_input, load_input  # noqa: E402
from acquire_official_json_transfer import sha, write, verify  # noqa: E402

LAW_READER = PROJECT / "data/m1/pilot_runs/m1-03a-transfer-v4-controls-v2/controls.py"
GOV_READER = PROJECT / "data/m1/pilot_runs/m1-03a-original-four-v8/verify.py"


def readers():
    spec = importlib.util.spec_from_file_location("prior_independent_law_controls", LAW_READER)
    law = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(law)
    namespace = {"__file__": str(GOV_READER)}
    exec(GOV_READER.read_text(encoding="utf-8").split("protected = {}")[0], namespace)
    return law.source_controls, namespace["resolution_controls"]


def source_input(root, key):
    path = root / key / "archive/input.json"
    manifest, raw, _ = load_input(path, "2026-10-16")
    asset = next(a for a in manifest["assets"] if a["role"] == "consolidated")
    field = asset["evidence"]["locator"].removeprefix("$.").removeprefix("/")
    html = json.loads(raw[asset["sha256"]])[field]
    return path, manifest, raw, asset, html


def prepare(root):
    freeze = verify(root)
    law, government = readers()
    for act in freeze["documents"]:
        try:
            _, _, _, asset, html = source_input(root, act["key"])
            # These retained readers predate this route and take HTML only.
            control = (government if act["source"] == "ips" else law)(html)
            soup = BeautifulSoup(html, "html.parser")
            ps = soup.find_all("p")
            positions = {id(p): ordinal for ordinal, p in enumerate(ps, 1)}
            rows = []
            for row in control["rows"]:
                if row["kind"] in {"header", "paragraph", "table_cell", "footnote", "quote"}:
                    continue
                p = ps[row["paragraph"] - 1]
                if p.find_parent("table"):
                    continue
                if row["kind"] == "approved_text":
                    p = p.find_next("p", class_="T")
                    assert p is not None
                rows.append({**row, "paragraph": positions[id(p)], "html_id": p.get("id"),
                    "parent": row.get("parent", row.get("parent_address")), "excerpt": p.get_text()[:240]})
            write(root / act["key"] / "controls.json", {"schema_version": "official-json-independent-controls/1",
                "prepared_at": datetime.now(UTC).isoformat(), "produced_before_ast": True, "source_asset_sha256": asset["sha256"],
                "reader_sha256": sha(GOV_READER if act["source"] == "ips" else LAW_READER), "rows": rows,
                "method": "Retained independent HTML-only DOM/marker/parent readers; no sidecar or resulting AST supplied.",
                "original_control": control,
                "limits": "Inline quote/form/table granularity is optional; explicit own provisions, source parents and complete body/media are checked separately."})
            print(act["key"], "CONTROLS", len(rows), flush=True)
        except Exception as error:
            write(root / act["key"] / "controls-failure.json", {"type": type(error).__name__, "message": str(error)})
            print(act["key"], "CONTROL READER FAILED", str(error), flush=True)
    files = [Path(__file__), LAW_READER, GOV_READER,
             PROJECT / "src/legal_rag/corpus/html_preparation.py",
             *root.glob("*/controls*.json")]
    write(root / "controls-freeze.json", {"frozen_at": datetime.now(UTC).isoformat(),
        "before_ast": True, "sha256": {str(p): sha(p) for p in files}})
    verify(root)


def compare(tree, control, html, rows):
    soup = BeautifulSoup(html, "html.parser")
    for p in list(soup.select("script, style, label")):
        p.decompose()
    blocks = sorted([n for n in [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]
                     if n.get("block_id") is not None], key=lambda b: b["block_id"])
    def compact(text):
        return "".join(text.split())
    errors = []
    if compact(soup.body.get_text()) != compact("".join(b["original_text"] for b in blocks
            if b.get("exclusion_reason") not in {"non_document_text", "portal_control"})):
        errors.append({"kind": "whole_body_mismatch"})
    source = [n for n in tree["nodes"] if n.get("source_id")]
    if [n["source_id"] for n in source] != [r["id"] for r in rows]:
        errors.append({"kind": "sidecar_id_order_mismatch"})
    if any(n["source_structure_evidence"]["json_pointer"] != f"/data/{i}" for i, n in enumerate(source)):
        errors.append({"kind": "sidecar_pointer_mismatch"})
    regions = [*tree["parsed_regions"], *tree["unresolved_regions"]]
    tables = [r for r in regions if r["tag"] == "table"]
    actual_tables = (len(tables), sum(len(t["rows"]) for t in tables),
                     sum(len(r["cells"]) for t in tables for r in t["rows"]))
    expected_tables = (len(soup.find_all("table")), len(soup.find_all("tr")), len(soup.find_all(["td", "th"])))
    if actual_tables != expected_tables:
        errors.append({"kind": "table_counts_mismatch", "expected": expected_tables, "actual": actual_tables})
    if [i.get("src") for i in soup.find_all("img")] != [r["attributes"].get("src") for r in regions if r["tag"] == "img"]:
        errors.append({"kind": "image_mismatch"})
    if not tree["accounting"]["exactly_once"] or not tree["accounting"]["regions_exactly_once"]:
        errors.append({"kind": "accounting_failure"})
    if tree["unresolved_blocks"] or tree["unresolved_regions"] or tree["structural_issues"] or tree["structure_audit"]["critical_count"]:
        errors.append({"kind": "unresolved_structure", "blocks": len(tree["unresolved_blocks"]),
            "regions": len(tree["unresolved_regions"]), "issues": tree["structural_issues"],
            "audit_critical": tree["structure_audit"]["critical_count"]})
    if control is None:
        errors.append({"kind": "independent_controls_unavailable"})
    else:
        by_start = {}
        for block in blocks:
            by_start.setdefault(block["paragraph"], block["html_start"])
        containers = [n for n in tree["nodes"] if n.get("block_id") is None]
        mapping = {"act": "act"}
        for c in control["rows"]:
            matches = [n for n in containers if n["kind"] == c["kind"]
                       and n["source_span"]["char_start"] == by_start.get(c["paragraph"])]
            if len(matches) != 1:
                errors.append({"kind": "independent_marker_mismatch", "control": c,
                               "observed": [n["address"] for n in matches]})
                continue
            node = matches[0]
            if c["kind"] not in {"approved_text", "normative_note", "notes_section"}:
                number = c["address"].rsplit("/", 1)[-1]
                if node.get("number_canonical") != number:
                    errors.append({"kind": "independent_number_mismatch", "control": c, "observed": node["address"]})
            expected_parent = mapping.get(c["parent"])
            if expected_parent != node["parent_address"]:
                errors.append({"kind": "independent_parent_mismatch", "control": c,
                               "expected_parent": expected_parent, "observed": node["parent_address"]})
            mapping[c["address"]] = node["address"]
    return {"errors": errors, "table_counts": actual_tables, "images": len(soup.find_all("img")),
            "source_nodes": len(source), "independent_controls": len(control["rows"]) if control else 0,
            "audit": tree["structure_audit"], "accounting": tree["accounting"]}


def run(root):
    freeze = verify(root)
    cf = json.loads((root / "controls-freeze.json").read_bytes())
    assert all(sha(p) == h for p, h in cf["sha256"].items())
    archive_hashes = {str(p): sha(p) for p in root.glob("*/archive/**/*") if p.is_file()}
    results = []
    for act in freeze["documents"]:
        result = {**act, "status": "fail", "edition_admission": False}
        try:
            path, manifest, raw, asset, html = source_input(root, act["key"])
            cp = root / act["key"] / "controls.json"
            control = json.loads(cp.read_bytes()) if cp.exists() else None
            bundle = manifest["structure_bundle"]
            rows = json.loads(raw[bundle["structure_sha256"]])["data"]
            a = compile_input(path, "2026-10-16", root / act["key"] / "run-a")
            b = compile_input(path, "2026-10-16", root / act["key"] / "run-b")
            repeat = compile_input(path, "2026-10-16", root / act["key"] / "run-a")
            def files(folder):
                return {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob("*") if p.is_file()}
            identical = files(root / act["key"] / "run-a") == files(root / act["key"] / "run-b")
            assert identical and a["draft_id"] == b["draft_id"] and repeat == {**a, "result": "unchanged"}
            tree = json.loads(Path(a["draft"]).read_bytes())["content"]["trees"][0]
            checks = compare(tree, control, html, rows)
            if tree["identity_decision"]["family"] != act["family"]:
                checks["errors"].append({"kind": "family_mismatch"})
            result.update(status="fail" if checks["errors"] else "pass", checks=checks,
                draft=a["draft"], report=a["report"], source_url=asset["source_url"],
                source_sha256=asset["sha256"], structure_sha256=bundle["structure_sha256"],
                input_sha256=sha(path), controls_sha256=sha(cp) if cp.exists() else None,
                source_format="native-json-html+official-sidecar:" + ("redtext" if act["source"] == "actual" else "doctext"),
                profile_version=tree["profile_version"], repeat="two_full_builds_identical_and_repeat_unchanged")
        except Exception as error:
            result["error"] = {"type": type(error).__name__, "message": str(error)}
        write(root / act["key"] / "result.json", result)
        results.append(result)
        print(act["key"], result["status"], result.get("error", {"exceptions": len(result.get("checks", {}).get("errors", []))}), flush=True)
    verify(root)
    assert all(sha(p) == h for p, h in archive_hashes.items())
    assert all(sha(p) == h for p, h in cf["sha256"].items())
    matrix = Counter((r["family"], r.get("source_format")) for r in results if r["status"] == "pass")
    expected = {("federal_law", "native-json-html+official-sidecar:redtext"),
                ("code", "native-json-html+official-sidecar:redtext"),
                ("government_resolution", "native-json-html+official-sidecar:doctext")}
    status = "pass" if len(results) == 6 and all(matrix[k] == 2 for k in expected) else "fail"
    write(root / "parser-transfer-report.json", {"schema_version": "parser-transfer-report/1", "status": status,
        "profile_version": "official-structure/4", "freeze_sha256": sha(root / "freeze.json"),
        "controls_freeze_sha256": sha(root / "controls-freeze.json"), "results": results,
        "matrix": [{"family": family, "format": fmt, "passed": matrix[(family, fmt)], "required": 2} for family, fmt in sorted(expected)],
        "protected_files_unchanged": len(freeze["protected_sha256"]), "archive_files_unchanged": len(archive_hashes),
        "closed_gold_access": False, "edition_admission": False,
        "limitations": ["Only this preselected native official-JSON matrix; no legal admission, PDF/OCR or guarantee for arbitrary acts.",
                        "No sample replacement or production rule changes; failed readers and builds remain failures."]})
    print("TRANSFER", status, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("controls", "run"))
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    {"controls": prepare, "run": run}[args.phase](args.root.resolve())
