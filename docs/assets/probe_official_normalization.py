"""Development probe; always writes a fresh immutable attempt directory."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from acquire_official_json_transfer import ACTS, write  # noqa: E402
from validate_official_json_transfer import source_input  # noqa: E402
from legal_rag.corpus.native_text import extract_native  # noqa: E402
from legal_rag.corpus.official_structure import build_official_tree  # noqa: E402


def main(root, out):
    out.mkdir(parents=True, exist_ok=False)
    for act in ACTS:
        key = act["key"]
        try:
            _, manifest, raw, asset, html = source_input(root, key)
            extraction = extract_native(asset, raw[asset["sha256"]])
            bundle = manifest["structure_bundle"]
            tree = build_official_tree(asset, extraction, html, raw[bundle["structure_sha256"]],
                                      bundle["structure_sha256"], bundle["source_system"])
            write(out / (key + "-tree.json"), tree)
            result = {"blocks": len(tree["unresolved_blocks"]), "regions": len(tree["unresolved_regions"]),
                      "issues": tree["structural_issues"], "audit": tree["structure_audit"]["critical_count"]}
        except Exception as error:
            result = {"type": type(error).__name__, "message": str(error)}
            tb = error.__traceback__
            while tb:
                if tb.tb_frame.f_code.co_name == "normalized_units":
                    values = tb.tb_frame.f_locals
                    result.update(row=values.get("row"), source_text=values.get("source_text"))
                tb = tb.tb_next
        write(out / (key + ".json"), result)
        print(key, {k: v for k, v in result.items() if k != "source_text"}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    main(args.root, args.out)
