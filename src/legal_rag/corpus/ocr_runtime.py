"""Explicit local OCR execution and immutable, permission-bound saved-result import."""

import hashlib
from pathlib import Path
import subprocess
import uuid

from .compiler import _hash, _inside, _read, _write_once, content_hash, json_bytes, load_input
from .pdf_extraction import normalize_dotsmocr


def _digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _destination(path, root, protected=()):
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or any(resolved.is_relative_to(p) for p in protected):
        raise ValueError("OCR destination escapes output or overlaps protected state")


def _store(files, *, root, protected=()):
    for path, payload in files.items():
        _destination(path, root, protected)
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"immutable OCR artifact conflict: {path}")
    result = "unchanged" if all(path.exists() for path in files) else "new"
    for path, payload in files.items():
        if not path.exists():
            _write_once(path, payload)
    return result


def run_ocr_lab(config: dict, payload: bytes, digest: str, receipt_dir: Path) -> Path:
    """Run the already-installed external runtime; never install, pull or stop peers."""
    lab = Path(config["lab_root"]).resolve()
    if config.get("provider") != "ocr-lab" or config.get("engine") != "dotsmocr":
        raise ValueError("unsupported OCR provider/adapter")
    workers = config.get("workers", 16)
    if type(workers) is not int or not 1 <= workers <= 16:
        raise ValueError("OCR workers must be between 1 and 16")
    paths = ["compose.yaml", "docker/Dockerfile.dotsmocr", "scripts/new_ocr_pdf.py",
             "config/new_ocr_models.json", "config/dotsmocr_prompt.txt", "config/dotsmocr_picture_ocr.json"]
    fingerprint = {name: _digest(lab / name) for name in paths}
    snapshot = {name: (lab / name).read_bytes() for name in paths if name.startswith(("scripts/", "config/"))}
    picture_overrides = {}
    if "picture_ocr_max_tokens" in config:
        budget = config["picture_ocr_max_tokens"]
        if type(budget) is not int or not 1 <= budget <= 24000:
            raise ValueError("Picture OCR budget must be between 1 and 24000 tokens")
        picture_overrides["max_tokens"] = budget
    if "picture_ocr_failure_policy" in config:
        policy = config["picture_ocr_failure_policy"]
        if policy not in {"strict", "retain_unresolved"}:
            raise ValueError("unknown Picture OCR failure policy")
        picture_overrides["failure_policy"] = policy
        if policy == "retain_unresolved":
            picture_overrides["recover_repetitions"] = True
    if picture_overrides:
        picture = _read(lab / "config/dotsmocr_picture_ocr.json")
        snapshot["config/dotsmocr_picture_ocr.json"] = json_bytes({**picture, **picture_overrides})
    profile_id = content_hash({name: hashlib.sha256(payload).hexdigest() for name, payload in snapshot.items()})
    snapshot_root = lab / "results" / "legal-rag-runtime" / profile_id
    _store({snapshot_root / name: payload for name, payload in snapshot.items()}, root=lab)
    fingerprint["profile_id"] = profile_id
    state = subprocess.run(["docker", "inspect", "--format",
                            "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
                            "ocr-lab-dotsmocr"], capture_output=True, text=True, timeout=30)
    if state.returncode or state.stdout.strip() != "running healthy":
        raise RuntimeError("dots.mocr is unavailable; start Docker and OCR-Lab dotsmocr, then retry")
    image = subprocess.run(["docker", "inspect", "--format", "{{.Image}}", "ocr-lab-dotsmocr"],
                           capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    fingerprint["image_id"] = image
    (receipt_dir / "runtime.json").write_bytes(json_bytes(fingerprint))
    staged = lab / "input" / ("legal-rag-" + digest + ".pdf")
    _store({staged: payload}, root=lab)
    name = receipt_dir.name
    native = lab / "results" / "legal-rag" / name
    command = ["docker", "compose", "--project-directory", str(lab), "exec", "-T", "dotsmocr",
               "python3", f"/data/results/legal-rag-runtime/{profile_id}/scripts/new_ocr_pdf.py", "--engine", "dotsmocr",
               "/data/input/" + staged.name, "--output", "/data/results/legal-rag/" + name,
               "--workers", str(workers)]
    with (receipt_dir / "runtime.log").open("wb") as log:
        try:
            completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                       timeout=config.get("timeout_seconds", 3600), check=False)
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError(f"OCR command failed; see {receipt_dir / 'runtime.log'}") from error
    # Detect changed prompts/config/code across the run instead of attributing it to old hashes.
    if any(_digest(snapshot_root / name) != hashlib.sha256(payload).hexdigest() for name, payload in snapshot.items()):
        raise RuntimeError("OCR runtime snapshot changed during extraction")
    if completed.returncode:
        raise RuntimeError(f"OCR exited {completed.returncode}; native output retained at {native}")
    return native


def extract_input(input_path: Path, output_dir: Path, config_path: Path | None = None,
                  results_path: Path | None = None) -> dict:
    if (config_path is None) == (results_path is None):
        raise ValueError("select exactly one OCR config or saved-results map")
    declared = _read(input_path)
    manifest, raw, archive = load_input(input_path, declared["target_dates"][0])
    output = output_dir.resolve()
    protected = [(archive / name).resolve() for name in
                 ("raw", "assets", "items", "relations", "candidates", "approved")]
    if any(output.is_relative_to(path) for path in protected):
        raise ValueError("OCR output overlaps protected source/approved state")
    assets = [asset for asset in manifest["assets"] if asset["metadata"]["media_type"] == "application/pdf"]
    if not assets:
        raise ValueError("input contains no permitted PDF assets")
    mapping, config = {}, None
    if results_path is not None:
        saved = _read(results_path)
        if saved.get("schema_version") != "ocr-results/1" or not isinstance(saved.get("results"), dict):
            raise ValueError("invalid OCR saved-results map")
        mapping = {digest: (results_path.parent / path).resolve() for digest, path in saved["results"].items()}
        if set(mapping) != {asset["sha256"] for asset in assets}:
            raise ValueError("saved OCR results must match the exact PDF asset set")
    else:
        config = _read(config_path)
        if config.get("schema_version") != "ocr-provider/1":
            raise ValueError("unsupported OCR provider config version")
    files, entries, evidence_locations = {}, {}, {}
    for asset in assets:
        digest = asset["sha256"]
        if not raw[digest].startswith(b"%PDF-"):
            raise ValueError("source asset is not a PDF")
        receipt_dir = None
        observation = {"source_asset_sha256": digest, "status": "running"}
        try:
            if config is not None:
                receipt_dir = output / "ocr-runs" / uuid.uuid4().hex
                _destination(receipt_dir, output, protected)
                receipt_dir.mkdir(parents=True)
                (receipt_dir / "run.json").write_bytes(json_bytes(observation))
                native = run_ocr_lab(config, raw[digest], digest, receipt_dir)
            else:
                native = mapping[digest]
            document, run = _read(native / "document.json"), _read(native / "run.json")
            runtime_record = None
            if receipt_dir is not None:
                runtime_record = _read(receipt_dir / "runtime.json")
            elif (native / "provider-runtime.json").exists():
                runtime_record = _read(native / "provider-runtime.json")
            if runtime_record is not None:
                run = {**run, "runtime_fingerprint": content_hash(runtime_record)}
            extraction = normalize_dotsmocr(document, run, digest)
            if not extraction["coverage"]["all_source_pages"]:
                raise ValueError("full PDF extraction requires every source page")
            native_files = {}
            for path in sorted(native.rglob("*")):
                if path.is_symlink():
                    raise ValueError("OCR evidence must not contain symlinks")
                if path.is_file() and path.name != "evidence-manifest.json":
                    native_files[path.relative_to(native).as_posix()] = path.read_bytes()
            if runtime_record is not None:
                native_files["provider-runtime.json"] = json_bytes(runtime_record)
            evidence = {name: hashlib.sha256(payload).hexdigest() for name, payload in native_files.items()}
            evidence_id = content_hash(evidence)
            evidence_dir = output / "ocr-evidence" / evidence_id
            files.update({evidence_dir / name: payload for name, payload in native_files.items()})
            files[evidence_dir / "evidence-manifest.json"] = json_bytes(evidence)
            extraction_id = extraction["extraction_id"]
            files[output / "extractions" / (extraction_id + ".json")] = json_bytes(extraction)
            entries[digest] = {"path": extraction_id + ".json", "extraction_id": extraction_id,
                               "native_evidence_id": evidence_id}
            evidence_locations[digest] = str(evidence_dir)
            observation.update(status="complete", native_output=str(native), extraction_id=extraction_id)
        except (ValueError, OSError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
            observation.update(status="failed", error=str(error))
            if receipt_dir is not None:
                (receipt_dir / "run.json").write_bytes(json_bytes(observation))
            raise ValueError(f"PDF OCR failed for {digest}: {error}") from error
        if receipt_dir is not None:
            (receipt_dir / "run.json").write_bytes(json_bytes(observation))
    index = {"schema_version": "extraction-index/1", "input_hash": manifest["manifest_hash"],
             "permission_hash": manifest["processing_permission"]["sha256"], "extractions": entries}
    index["index_id"] = content_hash(index)
    index_path = output / "extractions" / ("index-" + index["index_id"] + ".json")
    files[index_path] = json_bytes(index)
    result = _store(files, root=output, protected=protected)
    return {"result": result, "index": str(index_path), "extractions": entries,
            "native_evidence": evidence_locations, "blockers": ["ocr_review_required", "pdf_structure_unqualified"]}


def load_extractions(index_path: Path, manifest: dict) -> dict:
    index = _read(index_path)
    if (index.get("schema_version") != "extraction-index/1"
            or index.get("input_hash") != manifest["manifest_hash"]
            or index.get("permission_hash") != manifest["processing_permission"]["sha256"]
            or index.get("index_id") != content_hash({k: v for k, v in index.items() if k != "index_id"})):
        raise ValueError("misbound or corrupt PDF extraction index")
    expected = {a["sha256"] for a in manifest["assets"] if a["metadata"]["media_type"] == "application/pdf"}
    if set(index["extractions"]) != expected:
        raise ValueError("PDF extraction index asset set mismatch")
    result = {}
    for digest, reference in index["extractions"].items():
        extraction = _read(_inside(index_path.parent, reference["path"]))
        if (extraction.get("source_asset_sha256") != digest
                or extraction.get("schema_version") != "text-extraction/1"
                or extraction.get("extraction_id") != reference["extraction_id"]
                or extraction["extraction_id"] != content_hash({k: v for k, v in extraction.items() if k != "extraction_id"})
                or not extraction["coverage"]["all_source_pages"]):
            raise ValueError("corrupt, incomplete or misbound PDF extraction")
        evidence_dir = index_path.parent.parent / "ocr-evidence" / _hash(reference["native_evidence_id"])
        evidence = _read(evidence_dir / "evidence-manifest.json")
        if (content_hash(evidence) != reference["native_evidence_id"]
                or any(_digest(_inside(evidence_dir, name)) != checksum for name, checksum in evidence.items())):
            raise ValueError("corrupt retained OCR native evidence")
        fingerprint = extraction.get("runtime_fingerprint")
        if fingerprint is not None and fingerprint != content_hash(_read(evidence_dir / "provider-runtime.json")):
            raise ValueError("OCR runtime fingerprint does not match retained evidence")
        run = _read(evidence_dir / "run.json")
        if fingerprint is not None:
            run = {**run, "runtime_fingerprint": fingerprint}
        if normalize_dotsmocr(_read(evidence_dir / "document.json"), run, digest) != extraction:
            raise ValueError("PDF extraction does not match its retained native evidence")
        result[digest] = extraction
    return result
