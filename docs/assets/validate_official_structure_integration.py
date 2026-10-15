"""Explicit offline integration replay over the owner's seven retained inputs."""

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

from bs4 import BeautifulSoup

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from legal_rag.corpus.compiler import compile_input, json_bytes, load_input, manifest_digest  # noqa: E402
from legal_rag.sources.acquisition import _persist_asset  # noqa: E402

PREFLIGHT = PROJECT / "data/m1/experiments/official-structure-20261015-v1/preflight.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(record))


def prepare(record, destination, live_bundles):
    old_path = PROJECT / record["input"]
    normalized, _, archive = load_input(old_path, record["target_date_claim"])
    old = json.loads(old_path.read_bytes())
    reference = old["assets"][0]
    item_key = hashlib.sha256(reference["source_item"].encode()).hexdigest()
    item = json.loads((archive / "items" / (item_key + ".json")).read_bytes())
    old_text = json.loads((archive / "raw" / reference["sha256"]).read_bytes())
    old_structure = json.loads((PROJECT / record["response_file"]).read_bytes())
    live = None
    for source, bundle in live_bundles:
        origin = source.parent.parent
        if (bundle["source_item"] == reference["source_item"]
                and json.loads((origin / "raw" / bundle["text_sha256"]).read_bytes()) == old_text
                and json.loads((origin / "raw" / bundle["structure_sha256"]).read_bytes())["data"] == old_structure["data"]):
            live = source, bundle
            break
    if live:
        source, live_bundle = live
        archive = source.parent.parent
        item = json.loads((archive / "items" / (item_key + ".json")).read_bytes())
        reference = {**reference, "sha256": live_bundle["text_sha256"],
                     "evidence": {**reference["evidence"], "source_asset_sha256": live_bundle["text_sha256"]}}
        old["assets"][0] = reference
    actual = item["source_system"] == "actual.pravo.gov.ru"
    evidence = item["supporting_assets"]["declared_editions" if actual else "legislation_card"]
    root = destination / "archive"
    for digest in (reference["sha256"], evidence):
        for relative in (f"raw/{digest}", f"assets/{digest}.json"):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(archive / relative, target)
    timestamp = datetime.now(UTC).isoformat()
    payload = (PROJECT / record["response_file"]).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == record["response_sha256"]
    if live:
        digest = live_bundle["structure_sha256"]
        for relative in (f"raw/{digest}", f"assets/{digest}.json"):
            shutil.copyfile(archive / relative, root / relative)
    else:
        digest = _persist_asset(data_dir=root, raw_bytes=payload, captured_at=timestamp,
            media_type="application/json", rights_status="Owner-authorized diagnostic import of retained official response",
            source_url=reference["source_url"], transport_metadata={"request_url": record["url"], "http_status": 200},
            role="official_structure")
    assert json.loads((root / "raw" / digest).read_bytes())["data"] == old_structure["data"]
    item["asset_sha256s"] = list(dict.fromkeys([*item["asset_sha256s"], digest]))
    item["supporting_assets"]["official_structure"] = digest
    write(root / "items" / (item_key + ".json"), item)
    edition = json.loads((root / "raw" / evidence).read_bytes())
    if actual:
        selector = {"database": "ebpi", "document_id": str(edition["docid"]), "edition_id": record["edition"]["redid"]}
    else:
        selector = {"database": edition["baseid"], "document_id": edition["nd"], "edition_id": record["edition"]["id"]}
    bundle = {"schema_version": "official-structure-bundle/1", "source_system": item["source_system"],
        "source_item": reference["source_item"], "document_hash": item["external_id"], "source_url": reference["source_url"],
        "selector": selector, "text_sha256": reference["sha256"], "structure_sha256": digest, "edition_evidence_sha256": evidence}
    if live:
        bundle = live_bundle
    bundle_path = root / "structure_bundles/binding.json"
    write(bundle_path, bundle)
    old.update(schema_version="corpus-input/2", archive_root=".")
    old.pop("edition_candidate", None)
    old["assets"].append({**reference, "sha256": digest, "role": "official_structure",
        "evidence": {"locator": "$.data", "source_asset_sha256": digest, "source_url": reference["source_url"]}})
    permission = {"schema_version": "processing-permission/1", "decision": "allowed", "scope": "diagnostic",
        "act_identity": normalized["act_identity_claim"]["declared_identity"],
        "source_asset_sha256s": sorted([reference["sha256"], digest]), "authorized_by": "product-owner",
        "authorized_at": timestamp, "rights_basis": "Owner confirmed official-structure integration in the current chat; recording time, not message time or legal admission."}
    permission_path = root / "reviews/integration-permission.json"
    write(permission_path, permission)
    old["processing_permission"] = {"path": "reviews/integration-permission.json", "sha256": sha(permission_path)}
    old["structure_bundle"] = {"path": "structure_bundles/binding.json", "sha256": sha(bundle_path)}
    old["manifest_hash"] = manifest_digest(old)
    path = root / "input.json"
    write(path, old)
    write(destination / "import-receipt.json", {"original_input": record["input"], "original_input_sha256": sha(old_path),
        "live_bundle": str(live[0]) if live else None, "bundle_version": bundle["schema_version"],
        "original_text_sha256": record["source_sha256"], "compiled_text_sha256": reference["sha256"],
        "decoded_json_equivalence_verified": bool(live),
        "trace_scope": "per-capture request and response" if live else "legacy retained request; final response URL was not recorded"})
    return path


def controls(tree, record):
    html = json.loads((PROJECT / record["source_file"]).read_bytes())[record["locator"][2:]]
    soup = BeautifulSoup(html, "html.parser")
    source = [n for n in tree["nodes"] if n.get("source_id")]
    rows = json.loads((PROJECT / record["response_file"]).read_bytes())["data"]
    blocks = sorted([n for n in [*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]]
                     if n.get("block_id") is not None], key=lambda n: n["block_id"])
    for element in soup.select("script, style, label"):
        element.decompose()
    def compact(text):
        return "".join(text.split())
    body_matches = compact(soup.body.get_text()) == compact("".join(b["original_text"] for b in blocks
        if b.get("exclusion_reason") not in {"non_document_text", "portal_control"}))
    regions = [*tree["parsed_regions"], *tree["unresolved_regions"]]
    tables = [r for r in regions if r["tag"] == "table"]
    dom_counts = (len(soup.find_all("table")), len(soup.find_all("tr")), len(soup.find_all(["td", "th"])))
    parsed_counts = (len(tables), sum(len(r["rows"]) for r in tables), sum(len(row["cells"]) for r in tables for row in r["rows"]))
    result = {"source_nodes": len(source), "all_source_ids_preserved": [n["source_id"] for n in source] == [r["id"] for r in rows],
        "whole_body_matches_dom": body_matches, "tables_match_dom": dom_counts == parsed_counts,
        "images_match_dom": [i.get("src") for i in soup.find_all("img")] == [r["attributes"].get("src") for r in regions if r["tag"] == "img"],
        "table_counts": parsed_counts, "images": len(soup.find_all("img")), "counts_by_kind": tree["accounting"]["counts_by_kind"],
        "tokens_exactly_once": tree["accounting"]["exactly_once"], "regions_exactly_once": tree["accounting"]["regions_exactly_once"],
        "unresolved_blocks": len(tree["unresolved_blocks"]), "structural_issues": tree["structural_issues"]}
    result["technical_pass"] = all(result[k] for k in ("all_source_ids_preserved", "whole_body_matches_dom", "tables_match_dom",
                                                       "images_match_dom", "tokens_exactly_once", "regions_exactly_once"))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--live-bundles-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError("use a new output directory; prior attempts are immutable")
    preflight = json.loads(PREFLIGHT.read_bytes())
    live_bundles = []
    if args.live_bundles_dir:
        for path in sorted(args.live_bundles_dir.glob("*/structure_bundles/*.json")):
            bundle = json.loads(path.read_bytes())
            if bundle["schema_version"] == "official-structure-bundle/2":
                live_bundles.append((path, bundle))
    # This integration intentionally modifies compiler.py. Preserve the original
    # experiment's freeze, record that one approved delta, and verify all others.
    protected = {p: h for p, h in preflight["protected_files_sha256"].items()
                 if Path(p) != Path("src/legal_rag/corpus/compiler.py")}
    for path, expected in protected.items():
        assert sha(PROJECT / path) == expected, path
    results, trees = [], {}
    for record in preflight["records"]:
        destination = args.output_dir / record["document"]
        try:
            path = prepare(record, destination, live_bundles)
            target = record["target_date_claim"]
            a = compile_input(path, target, destination / "run-a")
            b = compile_input(path, target, destination / "run-b")
            repeat = compile_input(path, target, destination / "run-a")
            assert sha(Path(a["draft"])) == sha(Path(b["draft"])) and repeat == {**a, "result": "unchanged"}
            tree = json.loads(Path(a["draft"]).read_bytes())["content"]["trees"][0]
            trees[record["document"]] = tree
            check = controls(tree, record)
            legacy = None
            if record["document"] in {"federal-law-59", "housing-code", "government-decree-354", "government-decree-491"}:
                old = compile_input(PROJECT / record["input"], target, destination / "v1-replay")
                legacy = sha(Path(old["draft"])) == sha(PROJECT / record["baseline"])
                assert legacy, "v1 replay differs"
            write(destination / "controls.json", check)
            result = {"document": record["document"], "controls": check, "v1_replay_identical": legacy,
                      "repeat_identical": True, "draft": a["draft"], "legal_admission": False}
        except (ValueError, OSError, KeyError, TypeError, AssertionError) as error:
            result = {"document": record["document"], "error": str(error)}
        results.append(result)
        print(json.dumps({"document": record["document"], "error": result.get("error"),
                          "controls": result.get("controls")}, ensure_ascii=False), flush=True)
        write(args.output_dir / "progress.json", results)
    witnesses = {}
    if "energy-saving" in trees:
        tree = trees["energy-saving"]
        for number in ("9.16", "23.71"):
            nodes = [n for n in tree["nodes"] if n["kind"] == "article" and n.get("number_canonical") == number]
            witnesses["quoted_article_" + number] = len(nodes) == 1 and "/quote/" in nodes[0]["address"]
    if "housing-status" in trees:
        nodes = [n for n in trees["housing-status"]["nodes"] if n["kind"] == "list_item" and "/annex/2/" in n["address"]]
        witnesses["form_a_to_d"] = [n["number_canonical"] for n in nodes] == list("абвгд")
    if "housing-code" in trees:
        nodes = trees["housing-code"]["nodes"]
        parent = next(n for n in nodes if n.get("source_id") == "si_h1_a12_j2:1~")
        witnesses["housing_superscript_children"] = parent["number_display"] == "2¹" and [n["number_canonical"] for n in nodes
            if n.get("source_id") and n["parent_address"] == parent["address"]] == list("абвгдеж")
    if "gas" in trees:
        annex = next(n for n in trees["gas"]["nodes"] if n.get("source_id") == "zf1_uf2")
        witnesses["unnumbered_annex_preserved"] = annex["number_canonical"] is None
    for path, expected in protected.items():
        assert sha(PROJECT / path) == expected, path
    summary = {"schema_version": "official-structure-integration-check/1", "documents": results, "witnesses": witnesses,
        "protected_files_verified": len(protected), "closed_gold_access": False,
        "approved_code_delta": "compiler.py integration; original experiment code hashes remain unchanged in its preflight",
        "source_nodes": sum(r.get("controls", {}).get("source_nodes", 0) for r in results),
        "code_sha256s": {str(p.relative_to(PROJECT)): sha(p) for p in [Path(__file__),
            *sorted((PROJECT / "src/legal_rag/corpus").glob("*.py")), PROJECT / "src/legal_rag/sources/structure_bundle.py"]}}
    summary["technical_pass"] = all(r.get("controls", {}).get("technical_pass") for r in results) and all(witnesses.values()) and len(witnesses) == 5
    summary["structural_readiness"] = all(not r.get("controls", {}).get("unresolved_blocks")
        and not r.get("controls", {}).get("structural_issues") and "error" not in r for r in results)
    write(args.output_dir / "results.json", summary)
    return 0 if summary["technical_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
