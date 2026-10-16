"""Summarize a frozen cohort without changing its parser or control decisions."""

import json
from pathlib import Path
import sys

from acquire_official_json_transfer import sha, verify, write
from validate_official_json_transfer import source_input


def main(inputs, validation):
    freeze = verify(inputs)
    result_path = validation / "results.json"
    results = json.loads(result_path.read_bytes())
    records = []
    for r in results["documents"]:
        path, manifest, raw, asset, _ = source_input(inputs, r["key"])
        records.append({**{k: r[k] for k in ("key", "number", "date", "family", "source", "status")},
            "technical_pass": bool(r.get("repeat_identical") and not r["basic"]["errors"]),
            "source_url": asset["source_url"], "source_sha256": asset["sha256"],
            "structure_sha256": manifest["structure_bundle"]["structure_sha256"],
            "source_nodes": len(json.loads(raw[manifest["structure_bundle"]["structure_sha256"]])["data"]),
            "input_sha256": sha(path), "result_sha256": sha(validation / r["key"] / "result.json"),
            "error": r.get("error"), "errors": r.get("errors", []), "legal_admission": False})
    matrix = [{"family": family, "format": "native-json-html+official-sidecar:" + field,
               "passed": sum(r["status"] == "pass" and r["family"] == family for r in records), "required": 2}
              for family, field in [("federal_law", "redtext"), ("code", "redtext"), ("government_resolution", "doctext")]]
    report = {"schema_version": "parser-transfer-report/1", "status": results["status"],
        "scope": "M1-03A official native JSON/HTML, three declared families; not milestone-wide G13",
        "profile_version": freeze["profile_version"], "scanner_version": freeze["scanner_version"],
        "code_commit": freeze["commit"], "freeze_sha256": sha(inputs / "freeze.json"),
        "validation_sha256": sha(result_path), "summarizer_sha256": sha(__file__),
        "selected_before_bodies": freeze["selected_before_bodies"],
        "passed": results["passed"], "required": results["required"],
        "technical_passed": sum(r["technical_pass"] for r in records),
        "matrix": matrix, "results": records, "mutations": results["mutations"],
        "protected_files_unchanged": results["protected_files_unchanged"],
        "closed_gold_access": False, "legal_admission": False,
        "limits": results["limits"]}
    write(validation / "parser-transfer-report.json", report)
    print(json.dumps({"status": report["status"], "passed": report["passed"],
                      "technical_passed": report["technical_passed"], "matrix": matrix}, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
