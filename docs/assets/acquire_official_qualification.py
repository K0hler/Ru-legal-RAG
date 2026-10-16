"""Preselect a new diagnostic cohort after a successful development replay."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess

import acquire_official_json_transfer as base
from legal_rag.corpus.official_structure import VERSION
from legal_rag.corpus.structure_audit import VERSION as AUDIT_VERSION


class SelectedActual(base.DiagnosticActual):
    adapter_version = "diagnostic-selected-cohort/2"

    def fetch(self, document_hash):
        return {**super().fetch(document_hash), "adapter_version": self.adapter_version}


class SelectedIPS(base.DiagnosticIPS):
    adapter_version = "diagnostic-selected-cohort/2"

    def fetch(self, document_hash):
        return {**super().fetch(document_hash), "adapter_version": self.adapter_version}


def initialize(root, selection, development):
    report = json.loads(development.read_bytes())
    assert report["status"] == "pass" and report["passed"] == report["required"] == 6
    assert report["profile_version"] == VERSION and report["scanner_version"] == AUDIT_VERSION
    documents = json.loads(selection.read_bytes())
    assert len(documents) == 6 and len({d["key"] for d in documents}) == 6
    old = {(d["number"], d["date"]) for d in report["documents"]}
    assert all((d["number"], d["date"]) not in old for d in documents)
    root.mkdir(parents=True, exist_ok=False)
    paths = [*(base.PROJECT / "src/legal_rag").rglob("*.py"), Path(__file__),
             Path(base.__file__), Path(__file__).with_name("official_json_dom_controls.py"),
             Path(__file__).with_name("replay_official_normalization.py"), selection, development]
    base.write(root / "freeze.json", {"schema_version": "official-json-transfer-freeze/2", "documents": documents,
        "frozen_at": datetime.now(UTC).isoformat(), "selected_before_bodies": True,
        "development_report": str(development), "development_sha256": base.sha(development),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=base.PROJECT, text=True).strip(),
        "profile_version": VERSION, "scanner_version": AUDIT_VERSION,
        "diagnostic_wrapper_version": SelectedActual.adapter_version,
        "protected_sha256": {p.resolve().relative_to(base.PROJECT).as_posix(): base.sha(p) for p in paths},
        "authorization": "Owner requested additional official documents only after the previous six pass completely; bounded syntax diagnostic, no legal admission."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("init", "discover", "acquire"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--selection", type=Path)
    parser.add_argument("--development", type=Path)
    args = parser.parse_args()
    base.DiagnosticActual, base.DiagnosticIPS = SelectedActual, SelectedIPS
    if args.phase == "init":
        initialize(args.root.resolve(), args.selection.resolve(), args.development.resolve())
    elif args.phase == "discover":
        base.discover(args.root.resolve())
    else:
        base.acquire(args.root.resolve())
