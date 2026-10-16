"""Supplement frozen transfer results with independent lexical-owner checks."""

import argparse
import copy
import json
from pathlib import Path

from acquire_official_json_transfer import sha, verify, write


def check_owners(tree, control):
    """Compare source HTML paragraph context, not a duplicated sidecar parent."""
    by_address = {n["address"]: n for n in tree["nodes"]}
    containers, blocks = {}, {}
    for n in tree["nodes"]:
        if n.get("block_id") is None:
            containers.setdefault((n["source_span"]["char_start"], n["kind"]), []).append(n)
        elif n["kind"] != "note":
            blocks.setdefault(n["paragraph"], []).append(n)
    mapping = {"act": "act"}
    for c in control["rows"]:
        bs = blocks.get(c["paragraph"], [])
        if bs:
            ns = containers.get((bs[0]["html_start"], c["kind"]), [])
            if len(ns) == 1:
                mapping[c["address"]] = ns[0]["address"]
    errors, checked = [], 0
    for c in control["original_control"]["rows"]:
        if "parent_address" not in c:
            return {"errors": [{"kind": "independent_payload_context_unavailable"}], "paragraphs_checked": 0}
        target = c["parent_address"] if c["kind"] in {"paragraph", "header"} else c["address"]
        expected = mapping.get(target)
        bs = blocks.get(c["paragraph"], [])
        if expected is None or not bs:
            errors.append({"kind": "payload_context_unresolved", "paragraph": c["paragraph"], "expected": target})
            continue
        checked += 1
        for b in bs:
            address = b["parent_address"]
            seen = set()
            while address != "act" and address not in seen:
                seen.add(address)
                node = by_address.get(address)
                if node is None or node.get("source_id") or node.get("structure_origin") == "html_recovery":
                    break
                address = node["parent_address"]
            if address != expected:
                errors.append({"kind": "independent_payload_parent_mismatch", "html_id": b.get("html_id"),
                    "paragraph": c["paragraph"], "block_id": b["block_id"], "expected": expected, "observed": address})
    # Media-bearing inputs require their own independent ownership controls.
    if tree["parsed_regions"] or tree["unresolved_regions"]:
        errors.append({"kind": "independent_media_ownership_controls_required"})
    return {"errors": errors, "paragraphs_checked": checked}


def main(root):
    freeze = verify(root)
    report_path = root / "parser-transfer-report.json"
    report = json.loads(report_path.read_bytes())
    cf = json.loads((root / "controls-freeze.json").read_bytes())
    assert all(sha(p) == h for p, h in cf["sha256"].items())
    for result in report["results"]:
        if result["status"] != "pass":
            continue
        tree = json.loads(Path(result["draft"]).read_bytes())["content"]["trees"][0]
        control = json.loads((root / result["key"] / "controls.json").read_bytes())
        check = check_owners(tree, control)
        # Pin the review finding: text moved from a part to its article must fail.
        mutated = copy.deepcopy(tree)
        by_address = {n["address"]: n for n in mutated["nodes"]}
        block = next(n for n in mutated["nodes"] if n["kind"] == "paragraph"
                     and by_address.get(n["parent_address"], {}).get("kind") == "part")
        block["parent_address"] = by_address[block["parent_address"]]["parent_address"]
        mutated_check = check_owners(mutated, control)
        assert any(e["kind"] == "independent_payload_parent_mismatch" for e in mutated_check["errors"])
        check.update(mutation_wrong_payload_parent_detected=True, checker_sha256=sha(Path(__file__)),
                     input_draft_sha256=sha(result["draft"]), independent_controls_sha256=sha(root / result["key"] / "controls.json"))
        write(root / result["key"] / "payload-owner-check.json", check)
        result["payload_owner_check"] = check
        if check["errors"]:
            result["status"] = "fail"
        print(result["key"], result["status"], check["paragraphs_checked"], len(check["errors"]), flush=True)
    report.update(reviewed_from_sha256=sha(report_path), payload_checker_sha256=sha(Path(__file__)),
                  review_note="Original frozen verifier had no lexical-owner check; this separate supplement preserves its evidence and tests the known false-pass mutation.")
    for cell in report["matrix"]:
        cell["passed"] = sum(r["status"] == "pass" and r["family"] == cell["family"]
            and r.get("source_format") == cell["format"] for r in report["results"])
    report["status"] = "pass" if all(c["passed"] == c["required"] for c in report["matrix"]) else "fail"
    report["protected_files_unchanged"] = len(freeze["protected_sha256"])
    write(root / "parser-transfer-report-reviewed.json", report)
    verify(root)
    print("REVIEWED TRANSFER", report["status"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    main(parser.parse_args().root.resolve())
