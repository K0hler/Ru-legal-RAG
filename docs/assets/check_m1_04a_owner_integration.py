"""Replay the maintained owner parser and the compiler on known M1-04A development scans only."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from legal_rag.corpus.compiler import compile_input, content_hash  # noqa: E402
from legal_rag.corpus.ocr_owner_ast import build_owner_tree  # noqa: E402
from legal_rag.corpus import ocr_owner_structure  # noqa: E402
from run_m1_04a_dev_regression import development_documents, POOL  # noqa: E402


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", required=True, type=Path)
    output = cli.parse_args().output.resolve()
    if output.exists():
        raise FileExistsError(f"output exists: {output}")
    output.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("retained_owner_reference", ROOT / "docs/assets/ocr_logical_structure.py")
    reference = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reference
    spec.loader.exec_module(reference)
    rows = []
    for doc in development_documents():
        started = time.perf_counter()
        row = {"name": doc["name"], "group": doc["group"]}
        try:
            extraction = json.loads(doc["extraction"].read_text(encoding="utf-8"))
            before = content_hash(extraction)
            expected = reference.build(extraction)
            if ocr_owner_structure.build(extraction) != expected:
                raise ValueError("maintained owner parser differs from the retained prototype")
            if doc["group"] == "old-8":
                tree = build_owner_tree(extraction, None, "original")
                row["compiler"] = "adapter_only_legacy_input"
            else:
                batch = "batch-" + f"{int(doc['group'].split('-')[1]):02d}"
                path = POOL / "documents/pool" / batch / doc["name"] / "input.json"
                manifest = json.loads(path.read_text(encoding="utf-8"))
                saved = json.loads((POOL / "ocr" / doc["name"] / "run-01-extract-result.json").read_text(encoding="utf-8"))
                kwargs = {"extraction_index": Path(saved["index"])}
                print(json.dumps({"name": doc["name"], "phase": "first_build"}), flush=True)
                a = compile_input(path, manifest["target_dates"][0], output / doc["name"] / "a", **kwargs)
                print(json.dumps({"name": doc["name"], "phase": "same_directory_replay"}), flush=True)
                again = compile_input(path, manifest["target_dates"][0], output / doc["name"] / "a", **kwargs)
                print(json.dumps({"name": doc["name"], "phase": "separate_build"}), flush=True)
                b = compile_input(path, manifest["target_dates"][0], output / doc["name"] / "b", **kwargs)
                if again["result"] != "unchanged" or len({r["draft_id"] for r in (a, again, b)}) != 1:
                    raise ValueError("compiler IDs or saved replay changed")
                tree, = json.loads(Path(a["draft"]).read_text(encoding="utf-8"))["content"]["trees"]
                if not tree["parser_version"].startswith("ocr-owner-ast/"):
                    raise ValueError("compiler did not dispatch to the maintained parser")
                row.update(compiler="two_builds_and_unchanged_replay", draft_id=a["draft_id"])
            got = {b["region_id"]: b["owner_path"] for b in tree["region_bindings"]}
            if got != {r["region_id"]: r["owner"] for r in expected["regions"]}:
                raise ValueError("compiler region owners differ from the retained prototype")
            if content_hash(extraction) != before:
                raise ValueError("saved extraction mutated")
            if "pdf_structure_unqualified" not in tree["structural_issues"]:
                raise ValueError("qualification blocker missing")
            row.update(passed=True, regions=len(got), nodes=len(tree["nodes"]),
                       unresolved_blocks=len(tree["unresolved_blocks"]), identity=tree["identity_decision"]["status"])
        except Exception as error:
            row.update(passed=False, error=f"{type(error).__name__}: {error}")
        row["seconds"] = round(time.perf_counter() - started, 3)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    report = {"schema_version": "m1-04a-owner-compiler-integration/1", "documents": len(rows),
              "passed": sum(r["passed"] for r in rows), "rows": rows,
              "qualification": "not_performed", "reserved_documents_read": False}
    (output / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["passed"] != report["documents"] or not rows:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
