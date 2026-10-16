"""Replay seven retained bundles and byte-compare four frozen v1 outputs."""

import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "src"))
from acquire_official_json_transfer import sha, write  # noqa: E402
from replay_official_normalization import files  # noqa: E402
from validate_official_json_transfer import compare  # noqa: E402
from legal_rag.corpus.compiler import compile_input, load_input  # noqa: E402


def main(out):
    old = PROJECT / "data/m1/pilot_runs/independent-structure-audit-20261015-v2"
    protected = files(old)
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for r in json.loads((old / "results.json").read_bytes())["documents"]:
        key = r["document"]
        path = old / key / "archive/input.json"
        date = json.loads(path.read_bytes())["target_dates"][0]
        m, raw, _ = load_input(path, date)
        a = compile_input(path, date, out / key / "run-a")
        b = compile_input(path, date, out / key / "run-b")
        assert a["draft_id"] == b["draft_id"]
        assert compile_input(path, date, out / key / "run-a") == {**a, "result": "unchanged"}
        assert files(out / key / "run-a") == files(out / key / "run-b")
        t = json.loads(Path(a["draft"]).read_bytes())["content"]["trees"][0]
        asset = next(a for a in m["assets"] if a["role"] == "consolidated")
        html = json.loads(raw[asset["sha256"]])[asset["evidence"]["locator"].removeprefix("$.").removeprefix("/")]
        rows = json.loads(raw[m["structure_bundle"]["structure_sha256"]])["data"]
        checks = compare(t, None, html, rows)
        checks["errors"] = [e for e in checks["errors"] if e["kind"] != "independent_controls_unavailable"]
        assert not checks["errors"], (key, checks["errors"])
        assert checks["source_nodes"] == r["controls"]["source_nodes"]
        v1 = None
        if r["v1_replay_identical"]:
            original = PROJECT / f"data/m1/inputs/m1-02-completion/inputs/{key}-2026-10-01.json"
            result = compile_input(original, "2026-10-01", out / key / "v1-replay")
            expected = next((old / key / "v1-replay/drafts").glob("*/manifest.json"))
            v1 = sha(result["draft"]) == sha(expected)
            assert v1, key
        results.append({"document": key, "status": "pass", "checks": checks, "v1_byte_identical": v1})
        print(key, "PASS", "v1", v1, flush=True)
    assert files(old) == protected
    write(out / "results.json", {"status": "pass", "documents": results, "protected_unchanged": len(protected)})


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
