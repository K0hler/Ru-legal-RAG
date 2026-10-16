"""Immutable full replay with pre-AST DOM controls and negative mutations."""

import argparse
import copy
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from acquire_official_json_transfer import sha, write  # noqa: E402
from official_json_dom_controls import prepare, compare  # noqa: E402
from validate_official_json_transfer import source_input, compare as basic_compare  # noqa: E402
from legal_rag.corpus.compiler import compile_input  # noqa: E402
from legal_rag.corpus.official_structure import VERSION  # noqa: E402
from legal_rag.corpus.structure_audit import VERSION as AUDIT_VERSION  # noqa: E402


def files(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in folder.rglob("*") if p.is_file()}


def run(inputs, out, cohort, retained=None):
    out.mkdir(parents=True, exist_ok=False)
    documents = json.loads((inputs / "freeze.json").read_bytes())["documents"]
    code_paths = [*(PROJECT / "src/legal_rag").rglob("*.py"), Path(__file__),
                  Path(__file__).with_name("official_json_dom_controls.py")]
    code = {str(p): sha(p) for p in code_paths}
    protected = files(inputs)
    controls = {}
    # Every control is persisted before the first AST build in this run.
    for act in documents:
        key = act["key"]
        try:
            _, m, raw, _, html = source_input(inputs, key)
            rows = json.loads(raw[m["structure_bundle"]["structure_sha256"]])["data"]
            controls[key] = prepare(html, act["family"], rows)
            write(out / key / "controls.json", controls[key])
        except Exception as error:
            write(out / key / "controls-failure.json", {"error": type(error).__name__, "message": str(error)})
    write(out / "freeze.json", {"documents": documents, "cohort": cohort, "prepared_before_ast": retained is None,
        "at": datetime.now(UTC).isoformat(), "profile_version": VERSION, "scanner_version": AUDIT_VERSION,
        "code_sha256": code, "protected_sha256": protected, "input_root": str(inputs),
        "controls_sha256": {key: sha(out / key / "controls.json") for key in controls}})
    results, mutations = [], []
    for act in documents:
        key = act["key"]
        result = {**act, "status": "fail", "legal_admission": False}
        try:
            path, m, raw, _, html = source_input(inputs, key)
            rows = json.loads(raw[m["structure_bundle"]["structure_sha256"]])["data"]
            if retained is None:
                a = compile_input(path, "2026-10-16", out / key / "run-a")
                b = compile_input(path, "2026-10-16", out / key / "run-b")
                repeated = compile_input(path, "2026-10-16", out / key / "run-a")
                assert files(out / key / "run-a") == files(out / key / "run-b")
                assert repeated == {**a, "result": "unchanged"} and a["draft_id"] == b["draft_id"]
            else:
                assert cohort == "development", "Fresh qualification cannot reuse earlier builds"
                old_freeze = json.loads((retained / "freeze.json").read_bytes())
                assert all(sha(p) == digest for p, digest in old_freeze["code_sha256"].items() if Path(p).is_relative_to(PROJECT / "src"))
                old_result = json.loads((retained / key / "result.json").read_bytes())
                assert old_result["repeat_identical"] and files(retained / key / "run-a") == files(retained / key / "run-b")
                a = {"draft": old_result["draft"]}
            tree = json.loads(Path(a["draft"]).read_bytes())["content"]["trees"][0]
            basic = basic_compare(tree, None, html, rows)
            basic["errors"] = [e for e in basic["errors"] if e["kind"] != "independent_controls_unavailable"]
            checks = compare(tree, controls[key], html, rows)
            errors = [*basic["errors"], *checks["errors"]]
            assert tree["identity_decision"]["family"] == act["family"]
            result.update(status="fail" if errors else "pass", checks=checks, basic=basic,
                          repeat_identical=True, draft=a["draft"], errors=errors)
            # These mutations deliberately leave accounting and cached audit
            # unchanged; the independent verifier must still reject them.
            mutation_kinds = () if errors else ("paragraph", "number", "parent", "image", "table", "table_cell", "text", "original_text", "media_html", "coordinate")
            for kind in mutation_kinds:
                mutated = {**tree, "nodes": list(tree["nodes"])}
                if kind in {"paragraph", "text", "original_text", "coordinate"}:
                    target = next((n for n in mutated["nodes"] if n["kind"] == "paragraph" and n["parent_address"] != "act"), None)
                elif kind == "number":
                    target = next((n for n in mutated["nodes"] if n.get("source_id") and n.get("number_canonical")), None)
                elif kind == "parent":
                    target = next((n for n in mutated["nodes"] if n.get("source_id") and n["parent_address"] != "act"), None)
                elif kind == "media_html":
                    target = next((n for n in mutated["nodes"] if n["kind"] in {"image", "table"}), None)
                else:
                    target = next((n for n in mutated["nodes"] if n["kind"] == kind and (n.get("source_container_address") != "act" if kind == "table_cell" else n["parent_address"] != "act")), None)
                if target is None:
                    continue
                index = mutated["nodes"].index(target)
                target = copy.deepcopy(target)
                mutated["nodes"][index] = target
                if kind == "number":
                    target["number_canonical"] = "INVALID"
                elif kind == "text":
                    target["text"] += "MUTATED"
                elif kind == "original_text":
                    target["original_text"] += "MUTATED"
                elif kind == "media_html":
                    target["original_html"] = '<img src="WRONG.png">'
                elif kind == "coordinate":
                    span = target["source_span"]
                    start = span["char_start"]
                    span["char_start"] += 1
                    span["utf8_byte_start"] += len(html[start].encode("utf-8"))
                    span["locator"] = f"{span['json_pointer']}:chars:{span['char_start']}:{span['char_end']}"
                elif kind == "table_cell":
                    target["source_container_address"] = "act"
                else:
                    target["parent_address"] = "act"
                caught = compare(mutated, controls[key], html, rows)["errors"]
                mutations.append({"document": key, "mutation": kind, "detected": bool(caught),
                                  "error_kinds": sorted({e["kind"] for e in caught})})
        except Exception as error:
            result["error"] = {"type": type(error).__name__, "message": str(error)}
        write(out / key / "result.json", result)
        results.append(result)
        print(key, result["status"], result.get("error", {"errors": len(result.get("errors", []))}), flush=True)
    assert files(inputs) == protected
    assert all(sha(p) == digest for p, digest in code.items())
    status = "pass" if all(r["status"] == "pass" for r in results) and all(m["detected"] for m in mutations) else "fail"
    report = {"schema_version": "official-normalization-replay/1", "status": status,
        "cohort": cohort, "profile_version": VERSION, "scanner_version": AUDIT_VERSION,
        "retained_builds_revalidated": str(retained) if retained else None,
        "passed": sum(r["status"] == "pass" for r in results), "required": len(documents),
        "documents": results, "mutations": mutations, "protected_files_unchanged": len(protected),
        "code_files_unchanged": len(code), "closed_gold_access": False, "legal_admission": False,
        "limits": ["Raw HTML-only printed-context/paragraph/media checks plus independent replay of sidecar scope claims; hidden ordinals are not printed or independently legally reviewed.",
                   "Only the preselected native JSON+HTML scope; no arbitrary-document, PDF/OCR or dated legal applicability qualification."]}
    write(out / "results.json", report)
    print("RESULT", status, report["passed"], "/", report["required"], "mutations", len(mutations), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cohort", choices=("development", "qualification"), required=True)
    parser.add_argument("--retained", type=Path)
    args = parser.parse_args()
    run(args.inputs.resolve(), args.out.resolve(), args.cohort, args.retained.resolve() if args.retained else None)
