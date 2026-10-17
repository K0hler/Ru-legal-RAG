"""Run inside pinned Dedoc Docker: saved OCR only, no PDF reading or inference."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

from dedoc import DedocManager
import dedoc


def write(path, value):
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if path.exists():
        raise ValueError(f"preserve previous experiment: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


started = time.perf_counter()
manager = DedocManager()
rows = []
for source in sorted(Path("/input").glob("*/" + (sys.argv[1] if len(sys.argv) > 1 else "source.txt"))):
    parameters = {"document_type": "law", "structure_type": "tree", "with_attachments": "false", "encoding": "utf-8",
                  "handle_invisible_table": "true" if "--tables" in sys.argv else "false"}
    results = []
    tick = time.perf_counter()
    for attempt in (1, 2):
        payload = manager.parse(str(source), parameters=parameters).to_api_schema().model_dump()
        write(Path("/output") / source.parent.name / f"parsed-{attempt}.json", payload)
        results.append(payload)
    nodes = []

    def walk(node, parent=None):
        nodes.append({"id": node["node_id"], "parent": parent,
                      "kind": node["metadata"]["paragraph_type"], "text": node["text"]})
        for child in node["subparagraphs"]:
            walk(child, node["node_id"])

    walk(results[0]["content"]["structure"])
    write(Path("/output") / source.parent.name / "nodes.json", nodes)
    rows.append({"source_asset_sha256": source.parent.name,
                 "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                 "parameters": parameters, "kinds": dict(Counter(n["kind"] for n in nodes)),
                 "content_repeat_identical": results[0]["content"] == results[1]["content"],
                 "seconds_two_runs": time.perf_counter() - tick})
    print(json.dumps(rows[-1]), flush=True)
write(Path("/output/summary.json"), {"schema_version": "dedoc-ocr-probe/1", "dedoc": dedoc.__version__,
      "documents": rows, "seconds": time.perf_counter() - started,
      "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
      "network": "none", "legal_admission": False,
      "limit": "TXT is an evaluation projection; original layout/table/source locators retained separately."})
