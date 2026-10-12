from datetime import date, datetime
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import tempfile


EXTRACTOR_VERSION = "fixture-utf8/1"
PARSER_VERSION = "fixture-lines/1"


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def content_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def manifest_digest(manifest: dict) -> str:
    """Hash portable content; paths locate evidence but are not its identity."""
    payload = {key: value for key, value in manifest.items() if key not in {"archive_root", "manifest_hash"}}
    for key in ("processing_permission", "edition_candidate"):
        if payload.get(key) is not None:
            payload[key] = {"sha256": payload[key]["sha256"]}
    for key in ("assets", "admission_blockers", "unresolved_questions", "target_dates"):
        payload[key] = sorted(payload[key], key=lambda item: json_bytes(item))
    return content_hash(payload)


def _object(value: object, fields: set[str], *, optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict) or fields - value.keys() or value.keys() - fields - optional:
        raise ValueError(f"expected object fields {sorted(fields)}; optional {sorted(optional)}")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("expected non-empty text")
    return value


def _hash(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("expected SHA-256")
    return value


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("expected a list of unique strings")
    values = [_text(item) for item in value]
    if len(set(values)) != len(values):
        raise ValueError("expected a list of unique strings")
    return sorted(values)


def _date(value: object) -> str:
    value = _text(value)
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("expected YYYY-MM-DD date")
    return value


def _inside(root: Path, relative: str) -> Path:
    relative = _text(relative)
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError(f"path escape: {relative}")
    return path


def _read(path: Path) -> dict:
    value = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _reference(root: Path, reference: object) -> tuple[dict, str]:
    reference = _object(reference, {"path", "sha256"})
    payload = _inside(root, reference["path"]).read_bytes()
    digest = _hash(reference["sha256"])
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("reference hash mismatch")
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("reference must contain an object")
    return value, digest


def _asset(root: Path, digest: str) -> tuple[dict, bytes]:
    digest = _hash(digest)
    asset = _read(_inside(root, f"assets/{digest}.json"))
    payload = _inside(root, _text(asset.get("archive_key"))).read_bytes()
    if (
        asset.get("sha256") != digest
        or asset.get("archive_key") != f"raw/{digest}"
        or type(asset.get("byte_length")) is not int
        or asset["byte_length"] != len(payload)
        or hashlib.sha256(payload).hexdigest() != digest
    ):
        raise ValueError(f"invalid source asset: {digest}")
    public = {field: asset.get(field) for field in (
        "sha256", "archive_key", "byte_length", "captured_at", "media_type", "rights_status", "source_url"
    )}
    for field in ("captured_at", "media_type", "rights_status", "source_url"):
        _text(public[field])
    return public, payload


def load_input(path: Path, target_date: str) -> tuple[dict, dict[str, bytes], Path]:
    """Validate all evidence and permission before creating any derived files."""
    manifest = _object(_read(path), {
        "schema_version", "kind", "act_identity_claim", "target_dates", "archive_root", "assets",
        "processing_permission", "admission_status", "admission_blockers", "unresolved_questions",
        "manifest_hash",
    }, optional={"edition_candidate"})
    if manifest["schema_version"] != "corpus-input/1":
        raise ValueError("unknown corpus-input version")
    if _text(manifest["kind"]) not in {"official_consolidated", "original_amendments"}:
        raise ValueError("unknown input kind")
    identity = _text(_object(manifest["act_identity_claim"], {"declared_identity"})["declared_identity"])
    dates = [_date(value) for value in _strings(manifest["target_dates"])]
    if _date(target_date) not in dates:
        raise ValueError("target date is not declared in the input")
    if _text(manifest["admission_status"]) not in {"unreviewed", "unresolved", "rejected"}:
        raise ValueError("input admission_status must remain diagnostic")
    blockers = _strings(manifest["admission_blockers"])
    questions = _strings(manifest["unresolved_questions"])
    root = (path.resolve().parent / _text(manifest["archive_root"])).resolve()
    if not isinstance(manifest["assets"], list) or not manifest["assets"]:
        raise ValueError("assets must be a non-empty list")
    assets, raw, statuses = [], {}, []
    for reference in manifest["assets"]:
        reference = _object(reference, {"sha256", "source_item", "source_url", "role", "declared_identity", "evidence"})
        digest = _hash(reference["sha256"])
        if digest in raw:
            raise ValueError("duplicate input asset")
        if _text(reference["role"]) not in {"consolidated", "original", "amendment"}:
            raise ValueError("unknown asset role")
        asset, payload = _asset(root, digest)
        source_item = _text(reference["source_item"])
        item_id = hashlib.sha256(source_item.encode("utf-8")).hexdigest()
        item = _read(_inside(root, f"items/{item_id}.json"))
        declared = _text(reference["declared_identity"])
        if item.get("source_item") != source_item or item.get("declared_act_identity") != declared:
            raise ValueError("conflicting source identity")
        if reference["role"] != "amendment" and declared != identity:
            raise ValueError("conflicting act identity")
        if digest not in item.get("asset_sha256s", []):
            raise ValueError("asset does not belong to source item")
        evidence = _object(reference["evidence"], {"source_asset_sha256", "source_url", "locator"})
        if evidence["source_asset_sha256"] != digest or evidence["source_url"] != asset["source_url"]:
            raise ValueError("misbound evidence")
        if reference["source_url"] != asset["source_url"]:
            raise ValueError("misbound source URL")
        locator = _text(evidence["locator"])
        if asset["media_type"] == "text/plain; charset=utf-8":
            span = re.fullmatch(r"utf8:bytes:([0-9]+):([0-9]+)", locator)
            if span is None or not 0 <= int(span[1]) <= int(span[2]) <= len(payload):
                raise ValueError("misbound native-text evidence locator")
        unresolved = item.get("unresolved_items", [])
        if not isinstance(unresolved, list) or any(not isinstance(entry, dict) for entry in unresolved):
            raise ValueError("source unresolved_items must be a list of objects")
        for entry in unresolved:
            _text(entry.get("reason"))
        statuses.append({
            "source_item": source_item,
            "candidate_status": _text(item.get("candidate_status", "unreviewed")),
            "review_status": _text(item.get("review_status", "unreviewed")),
            "unresolved_items": sorted(unresolved, key=json_bytes),
        })
        assets.append({**reference, "metadata": asset})
        raw[digest] = payload
    roles = [asset["role"] for asset in assets]
    if manifest["kind"] == "official_consolidated" and roles != ["consolidated"]:
        raise ValueError("official_consolidated requires one consolidated asset")
    if manifest["kind"] == "original_amendments" and (roles.count("original") != 1 or "consolidated" in roles):
        raise ValueError("original_amendments requires one original and optional amendments")
    permission, permission_hash = _reference(root, manifest["processing_permission"])
    _object(permission, {
        "schema_version", "decision", "scope", "act_identity", "source_asset_sha256s",
        "authorized_by", "authorized_at", "rights_basis",
    })
    if permission["schema_version"] != "processing-permission/1":
        raise ValueError("unknown processing permission version")
    if permission["decision"] != "allowed" or permission["scope"] != "diagnostic":
        raise ValueError("processing permission does not allow diagnostic extraction")
    if permission["act_identity"] != identity or _strings(permission["source_asset_sha256s"]) != sorted(raw):
        raise ValueError("processing permission scope mismatch")
    for field in ("authorized_by", "rights_basis"):
        _text(permission[field])
    if datetime.fromisoformat(_text(permission["authorized_at"]).replace("Z", "+00:00")).utcoffset() is None:
        raise ValueError("permission timestamp needs a UTC offset")
    candidate = None
    if manifest.get("edition_candidate") is not None:
        if manifest["kind"] != "official_consolidated":
            raise ValueError("original/amendments input cannot impersonate a consolidated candidate")
        candidate, _ = _reference(root, manifest["edition_candidate"])
        _validate_candidate(root, candidate, assets[0], identity)
    if _hash(manifest["manifest_hash"]) != manifest_digest(manifest):
        raise ValueError("manifest hash mismatch")
    normalized = {
        "schema_version": "corpus-input/1", "manifest_hash": manifest["manifest_hash"],
        "kind": manifest["kind"], "act_identity_claim": manifest["act_identity_claim"],
        "target_dates": dates, "assets": sorted(assets, key=lambda asset: (asset["role"] == "amendment", asset["sha256"])),
        "processing_permission": {"sha256": permission_hash, "record": permission},
        "admission_status": manifest["admission_status"], "admission_blockers": blockers,
        "unresolved_questions": questions, "source_statuses": sorted(statuses, key=lambda item: item["source_item"]),
        "edition_candidate": candidate,
        "candidate_bytes_sha256": manifest.get("edition_candidate", {}).get("sha256") if candidate else None,
    }
    return normalized, raw, root


def _validate_candidate(root: Path, candidate: dict, asset: dict, identity: str) -> None:
    _object(candidate, {"schema_version", "candidate_id", "act_identity_claim", "edition_claim",
                        "reconciliation_id", "review_decision", "review_status", "source_evidence",
                        "temporal_evidence", "unresolved_items"})
    if candidate.get("schema_version") != "edition-candidate/1":
        raise ValueError("unknown edition-candidate version")
    if candidate.get("candidate_id") != content_hash({key: value for key, value in candidate.items() if key != "candidate_id"}):
        raise ValueError("candidate content ID mismatch")
    if candidate.get("act_identity_claim", {}).get("declared_identity") != identity:
        raise ValueError("conflicting candidate identity")
    _object(candidate["act_identity_claim"], {"declared_identity", "source_item", "source_asset_sha256s", "source_relation_ids"})
    claim = candidate["edition_claim"]
    _object(claim, {"captured_at", "claimed_edition_date", "claimed_edition_label", "snapshot_asset_sha256",
                    "source_asset_sha256s", "source_item", "source_relation_ids"})
    _object(candidate["temporal_evidence"], {"source_asset_sha256s", "source_relation_ids", "status", "valid_from", "valid_to"})
    if claim["snapshot_asset_sha256"] != asset["sha256"] or claim["source_item"] != asset["source_item"]:
        raise ValueError("candidate snapshot scope mismatch")
    item_id = hashlib.sha256(claim["source_item"].encode("utf-8")).hexdigest()
    if _read(_inside(root, f"items/{item_id}.json")).get("candidate_status") == "stale":
        raise ValueError("stale edition candidate cannot be wrapped; use diagnostic assets")
    evidence = candidate["source_evidence"]
    _object(evidence, {"assets", "items", "relations", "exceptions"})
    reconciliation = _read(_inside(root, f"reconciliations/{candidate['reconciliation_id']}.json"))
    if (
        reconciliation.get("reconciliation_id") != candidate["reconciliation_id"]
        or reconciliation.get("act_source_item") != candidate["act_identity_claim"]["source_item"]
        or sorted(reconciliation.get("item_source_ids", [])) != sorted(item["source_item"] for item in evidence["items"])
        or sorted(reconciliation.get("relation_ids", [])) != sorted(relation["relation_id"] for relation in evidence["relations"])
        or sorted(reconciliation.get("exception_ids", [])) != sorted(evidence["exceptions"])
    ):
        raise ValueError("candidate reconciliation scope mismatch")
    for public_item in evidence["items"]:
        _object(public_item, {"declared_act_identity", "item_kind", "label", "source_item", "source_system"}, optional={"source_url"})
        item_id = hashlib.sha256(_text(public_item["source_item"]).encode("utf-8")).hexdigest()
        persisted = _read(_inside(root, f"items/{item_id}.json"))
        if any(persisted.get(key) != value for key, value in public_item.items()):
            raise ValueError("candidate source item mismatch")
        if public_item["source_item"] in {candidate["act_identity_claim"]["source_item"], claim["source_item"]} and public_item["declared_act_identity"] != identity:
            raise ValueError("conflicting candidate source identity")
    for exception_id in evidence["exceptions"]:
        if _read(_inside(root, f"exceptions/{exception_id}.json")).get("exception_id") != exception_id:
            raise ValueError("candidate exception mismatch")
    known = {}
    for record in evidence["assets"]:
        checked, _ = _asset(root, record["sha256"])
        if checked != record:
            raise ValueError("candidate asset metadata mismatch")
        known[record["sha256"]] = checked
    for relation in evidence["relations"]:
        _object(relation, {"asserted_by", "from_source_item", "to_source_item", "relation_id", "relation_type", "review_state", "evidence_reference"})
        reference = relation["evidence_reference"]
        _object(reference, {"locator", "source_url", "source_asset_sha256"})
        if reference.get("source_asset_sha256") not in known:
            raise ValueError("candidate relation references unknown evidence")
        # The source claim's public URL may differ from the raw API URL.
        persisted = _read(_inside(root, f"relations/{relation['relation_id']}.json"))
        if any(persisted.get(key) != value for key, value in relation.items() if key != "evidence_reference"):
            raise ValueError("candidate relation mismatch")
        if any(persisted.get("evidence_reference", {}).get(key) != value for key, value in reference.items()):
            raise ValueError("candidate relation evidence mismatch")
    consolidates = [relation for relation in evidence["relations"] if relation["relation_type"] == "consolidates"
                    and relation["from_source_item"] == claim["source_item"]
                    and relation["to_source_item"] == candidate["act_identity_claim"]["source_item"]]
    if not consolidates or sorted(relation["relation_id"] for relation in consolidates) != sorted(claim["source_relation_ids"]):
        raise ValueError("candidate lacks its consolidated evidence path")
    relation_ids = {relation["relation_id"] for relation in evidence["relations"]}
    for group in (candidate["act_identity_claim"], claim, candidate["temporal_evidence"], *candidate["unresolved_items"]):
        if not set(_strings(group["source_asset_sha256s"])) <= known.keys() or not set(_strings(group["source_relation_ids"])) <= relation_ids:
            raise ValueError("candidate claim references unknown evidence")
    if candidate["review_status"] not in {"unreviewed", "reviewed", "rejected"}:
        raise ValueError("invalid candidate review status")
    decision = candidate["review_decision"]
    if candidate["review_status"] == "unreviewed":
        if decision is not None:
            raise ValueError("unreviewed candidate carries a review decision")
    elif (
        not isinstance(decision, dict) or decision.get("reviewer_role") != "Legal Reviewer"
        or decision.get("decision") != candidate["review_status"]
        or decision.get("reviewed_scope") != claim["source_item"]
        or decision.get("decision_id") != content_hash({key: value for key, value in decision.items() if key != "decision_id"})
    ):
        raise ValueError("invalid candidate review decision")
    if decision is not None:
        for field in ("reviewer_id", "rationale", "decided_at"):
            _text(decision.get(field))
        if datetime.fromisoformat(decision["decided_at"].replace("Z", "+00:00")).utcoffset() is None:
            raise ValueError("candidate decision timestamp needs a UTC offset")
        if not isinstance(decision.get("evidence_references"), list) or not decision["evidence_references"]:
            raise ValueError("candidate decision needs evidence")
        for reference in decision["evidence_references"]:
            if reference.get("source_asset_sha256") not in known or reference.get("source_relation_id") not in relation_ids:
                raise ValueError("candidate decision references unknown evidence")


def compile_input(input_path: Path, target_date: str, output_dir: Path) -> dict:
    manifest, raw, archive = load_input(Path(input_path), target_date)
    output_dir = Path(output_dir).resolve()
    for protected in ("raw", "assets", "items", "relations", "candidates", "approved"):
        if output_dir.is_relative_to((archive / protected).resolve()):
            raise ValueError("output directory overlaps protected source/approved state")
    extractions, trees = [], []
    blockers = {"legal_admission_not_requested", "temporal_coverage_unverified", *manifest["admission_blockers"]}
    if manifest["kind"] == "original_amendments":
        blockers.add("amendments_not_applied")
    for status in manifest["source_statuses"]:
        blockers.update(item["reason"] for item in status["unresolved_items"])
        blockers.update(value for key in ("candidate_status", "review_status") if (value := status[key]) in {"stale", "rejected"})
    if manifest["edition_candidate"]:
        blockers.update(item["reason"] for item in manifest["edition_candidate"]["unresolved_items"])
        if manifest["edition_candidate"]["review_status"] == "rejected":
            blockers.add("rejected")
    for asset in manifest["assets"]:
        if asset["metadata"]["media_type"].split(";", 1)[0] == "application/json":
            from .native_text import extract_native, native_tree

            extraction = extract_native(asset, raw[asset["sha256"]])
            extractions.append(extraction)
            trees.append(native_tree(asset, extraction))
            continue
        if asset["metadata"]["media_type"] != "text/plain; charset=utf-8":
            raise ValueError("unsupported extraction format; use UTF-8 fixture or native redtext JSON")
        text = raw[asset["sha256"]].decode("utf-8")
        extraction = {
            "schema_version": "text-extraction/1", "source_asset_sha256": asset["sha256"],
            "extractor_version": EXTRACTOR_VERSION, "config": {"encoding": "utf-8", "cleanup": "none"},
            "models": [], "pages": [{"page": None, "mode": "native_text", "confidence": None,
                "blocks": [{"text": text, "locator": "utf8:bytes:0:" + str(len(raw[asset["sha256"]])),
                            "bbox": None, "table_cells": [], "unresolved_regions": []}]}],
        }
        extraction["extraction_id"] = content_hash(extraction)
        extractions.append(extraction)
        trees.append(_tree(asset, text, extraction["extraction_id"]))
    if any(tree["unresolved_blocks"] for tree in trees):
        blockers.add("unresolved_structure")
    if any(tree["identity_decision"]["status"] == "unresolved" for tree in trees):
        blockers.add("identity_unresolved")
    content = {"trees": trees, "target_date": target_date, "kind": manifest["kind"]}
    draft = {
        "schema_version": "edition-draft/1", "input_hash": manifest["manifest_hash"],
        "validated_input_hash": content_hash(manifest), "extraction_ids": [item["extraction_id"] for item in extractions],
        "parser_version": "+".join(sorted({tree["parser_version"] for tree in trees})), "target_date": target_date, "scope": "diagnostic_snapshot",
        "content_hash": content_hash(content), "content": content, "blockers": sorted(blockers),
        "admission_status": manifest["admission_status"], "legal_admission": "not_requested",
    }
    draft["draft_id"] = content_hash(draft)
    draft_dir = output_dir / "drafts" / draft["draft_id"]
    files = {output_dir / "extractions" / f"{item['extraction_id']}.json": json_bytes(item) for item in extractions}
    files.update({draft_dir / "input.json": json_bytes(manifest), draft_dir / "manifest.json": json_bytes(draft),
                  draft_dir / "report.html": _report(manifest, draft).encode("utf-8")})
    # Validate every destination before writing; never repair a conflicting immutable artifact.
    for path, payload in files.items():
        resolved = path.resolve()
        if not resolved.is_relative_to(output_dir) or any(
            resolved.is_relative_to((archive / protected).resolve())
            for protected in ("raw", "assets", "items", "relations", "candidates", "approved")
        ):
            raise ValueError("derived artifact path overlaps protected state or escapes output")
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"immutable artifact conflict: {path}")
    result = "unchanged" if all(path.exists() for path in files) else "new"
    for path, payload in files.items():
        if not path.exists():
            _write_once(path, payload)
    return {"result": result, "manifest_hash": manifest["manifest_hash"], "draft_id": draft["draft_id"],
            "content_hash": draft["content_hash"], "draft": str(draft_dir / "manifest.json"),
            "report": str(draft_dir / "report.html"), "blockers": draft["blockers"]}


def _tree(asset: dict, text: str, extraction_id: str) -> dict:
    lines = text.splitlines(keepends=True)
    identity_matches = bool(lines and lines[0].strip() == asset["declared_identity"])
    identity = {"act_id": content_hash({"declared_identity": asset["declared_identity"]}),
                "declared_identity": asset["declared_identity"],
                "status": "claim_matches_header" if identity_matches else "unresolved"}
    nodes, unresolved, excluded = [], [], []
    offset = byte_offset = 0
    addresses = set()
    namespace = "act" if asset["role"] != "amendment" else "amendment/" + asset["sha256"]
    for index, line in enumerate(lines):
        size = len(line.encode("utf-8"))
        span = {"source_asset_sha256": asset["sha256"], "char_start": offset, "char_end": offset + len(line),
                "byte_start": byte_offset, "byte_end": byte_offset + size,
                "locator": f"utf8:bytes:{byte_offset}:{byte_offset + size}"}
        block = {"text": line, "source_span": span}
        article = re.fullmatch(r"Статья ([1-9][0-9]*)\. [^\r\n]+", line.rstrip("\r\n"))
        if not line.strip():
            excluded.append({**block, "reason": "whitespace"})
        elif index == 0 and identity_matches:
            nodes.append({**block, "kind": "identity_header", "address": namespace + "/title"})
        elif identity_matches and article and article[1] not in addresses:
            addresses.add(article[1])
            nodes.append({**block, "kind": "article", "address": namespace + "/article/" + article[1]})
        else:
            unresolved.append({**block, "kind": "unresolved_block", "reason": "unsupported_or_ambiguous_fixture_line"})
        offset += len(line)
        byte_offset += size
    accounting = {"total_chars": len(text), "total_bytes": len(text.encode("utf-8"))}
    for name, blocks in (("parsed", nodes), ("unresolved", unresolved), ("excluded", excluded)):
        accounting[name + "_chars"] = sum(len(block["text"]) for block in blocks)
        accounting[name + "_bytes"] = sum(len(block["text"].encode("utf-8")) for block in blocks)
    return {"schema_version": "legal-ast/1", "parser_version": PARSER_VERSION,
            "extraction_id": extraction_id, "source_asset_sha256": asset["sha256"], "role": asset["role"],
            "identity_decision": identity, "namespace": namespace, "nodes": nodes,
            "unresolved_blocks": unresolved, "excluded_blocks": excluded, "cleanup_mapping": [],
            "accounting": accounting}


def _report(manifest: dict, draft: dict) -> str:
    sections = []
    for tree in draft["content"]["trees"]:
        asset = next(asset for asset in manifest["assets"] if asset["sha256"] == tree["source_asset_sha256"])
        blocks = sorted([*tree["nodes"], *tree["unresolved_blocks"], *tree["excluded_blocks"]],
                        key=lambda block: block["source_span"]["char_start"])
        document_rows, excluded_rows = [], []
        excluded_ids = {block["block_id"] for block in tree["excluded_blocks"] if "block_id" in block}
        for block in blocks:
            row = ("<tr><td>" + escape(block.get("address", block.get("reason", ""))) + "</td><td>"
                   + escape(block["source_span"]["locator"]) + "</td><td><pre>" + escape(block["text"])
                   + "</pre>" + ("<details><summary>Original source text and HTML</summary><pre>"
                     + escape(block["original_text"]) + "</pre><pre>" + escape(block["original_html"])
                     + "</pre></details>" if "original_html" in block else "") + "</td></tr>")
            (excluded_rows if block.get("block_id") in excluded_ids else document_rows).append(row)
        exclusions = ("<details><summary>Excluded source tokens and reasons</summary><table>"
                      + "".join(excluded_rows) + "</table></details>") if excluded_rows else ""
        sections.append(f"<h2>{escape(tree['namespace'])}</h2><p>SHA-256: {asset['sha256']}</p>"
                        f"<p>Source: {escape(asset['source_url'])}; evidence: {escape(asset['evidence']['locator'])}</p>"
                        f"<pre>{escape(json.dumps(tree['accounting'], sort_keys=True, indent=2))}</pre>"
                        "<table><tr><th>Address / disposition</th><th>Raw locator</th><th>Text</th></tr>"
                        + "".join(document_rows) + "</table>" + exclusions)
    blockers = "".join("<li>" + escape(item) + "</li>" for item in draft["blockers"])
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><title>Legal RAG diagnostic draft</title>"
            "<style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px}"
            "table{width:100%;border-collapse:collapse}td,th{border:1px solid #bbb;padding:8px;text-align:left}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere}li{margin:6px 0}</style>"
            f"<h1>{escape(manifest['act_identity_claim']['declared_identity'])}</h1>"
            f"<p>Target: {draft['target_date']}; diagnostic snapshot; legal admission: not requested.</p>"
            f"<p>Input status: {escape(draft['admission_status'])}; kind: {manifest['kind']}.</p>"
            f"<p>Draft: {draft['draft_id']}; input: {draft['input_hash']}; content: {draft['content_hash']}</p>"
            f"<h2>Blockers</h2><ul>{blockers}</ul><h2>Source status and unresolved questions</h2>"
            f"<pre>{escape(json.dumps({'statuses': manifest['source_statuses'], 'questions': manifest['unresolved_questions']}, ensure_ascii=False, indent=2))}</pre>"
            f"<h2>Processing permission</h2><pre>{escape(json.dumps(manifest['processing_permission'], ensure_ascii=False, indent=2))}</pre>"
            + "".join(sections) + "</html>\n")


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
        # link creates the final name atomically without replacing an existing record.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
