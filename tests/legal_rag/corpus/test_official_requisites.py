"""Bound official-card metadata, independently of OCR requisites recognition."""
import hashlib
import json
from pathlib import Path

import pytest

from legal_rag.corpus.compiler import compile_input, json_bytes, manifest_digest
from legal_rag.corpus import ocr_runtime


EO = "0001202403170001"
CLAIM = "Распоряжение Правительства Российской Федерации от 17.03.2024 № 1165-р"
CARD_URL = f"http://publication.pravo.gov.ru/api/Document?eoNumber={EO}"
PDF_URL = f"http://publication.pravo.gov.ru/File/Pdf?eoNumber={EO}"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def put_card(context, **changes):
    card = dict(context["card"], **changes)
    raw = json_bytes(card)
    digest = hashlib.sha256(raw).hexdigest()
    root = context["root"]
    (root / "raw" / digest).write_bytes(raw)
    metadata = {"sha256": digest, "archive_key": f"raw/{digest}", "byte_length": len(raw),
                "captured_at": "2024-03-17T12:00:00Z", "media_type": "application/json",
                "rights_status": "Authored fixture", "source_url": CARD_URL, "role": "declared_publication"}
    write(root / "assets" / f"{digest}.json", metadata)
    pdf_path = root / "assets" / f"{context['pdf_sha']}.json"
    pdf = json.loads(pdf_path.read_bytes())
    pdf["source_url"] = PDF_URL
    pdf["transport_metadata"] = {"request_url": PDF_URL, "response_url": PDF_URL,
        "card_request": {"sha256": digest, "request_url": CARD_URL, "response_url": CARD_URL}}
    write(pdf_path, pdf)
    item = json.loads(context["item_path"].read_bytes())
    item["declared_publication_asset"] = digest
    item["asset_sha256s"] = sorted(set(item["asset_sha256s"]) | {digest})
    write(context["item_path"], item)
    return digest


@pytest.fixture
def prepared(tmp_path):
    from test_ocr_runtime import OcrRuntimeTest
    path, mapping, output, pdf_sha = OcrRuntimeTest().prepare(tmp_path)
    root = path.parent
    manifest = json.loads(path.read_bytes())
    reference, = manifest["assets"]
    old_item_id = hashlib.sha256(reference["source_item"].encode()).hexdigest()
    item = json.loads((root / "items" / f"{old_item_id}.json").read_bytes())
    source_item = f"publication.pravo.gov.ru:{EO}"
    item.update(source_item=source_item, source_system="publication.pravo.gov.ru", external_id=EO,
                declared_act_identity=CLAIM, latest_successful_asset=pdf_sha)
    item_path = root / "items" / (hashlib.sha256(source_item.encode()).hexdigest() + ".json")
    write(item_path, item)
    reference.update(source_item=source_item, source_url=PDF_URL, declared_identity=CLAIM)
    reference["evidence"]["source_url"] = PDF_URL
    manifest["act_identity_claim"]["declared_identity"] = CLAIM
    permission_path = root / manifest["processing_permission"]["path"]
    permission = json.loads(permission_path.read_bytes())
    permission["act_identity"] = CLAIM
    write(permission_path, permission)
    manifest["processing_permission"]["sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest()
    manifest["manifest_hash"] = manifest_digest(manifest)
    write(path, manifest)
    context = {"input": path, "root": root, "output": output, "pdf_sha": pdf_sha, "item_path": item_path,
        "card": {"eoNumber": EO, "complexName": CLAIM, "name": None, "documentDate": "2024-03-17T00:00:00",
                 "number": "1165-р", "documentType": {"name": "Распоряжение"},
                 "signatoryAuthorities": [{"name": "Правительство Российской Федерации"}]}}
    context["card_sha"] = put_card(context)
    saved = ocr_runtime.extract_input(path, output, results_path=mapping)
    context["index"] = Path(saved["index"])
    return context


def compile_card(context, folder="compiled"):
    return compile_input(context["input"], "2025-01-01", context["output"] / folder,
                         extraction_index=context["index"])


@pytest.mark.parametrize("title", [None, "", "absent"])
def test_official_card_supplies_requisites_when_ocr_identity_is_unresolved(prepared, title):
    changes = {"name": title}
    if title == "absent":
        del prepared["card"]["name"]
        changes = {}
    digest = put_card(prepared, **changes)
    before = {p: p.read_bytes() for p in prepared["root"].rglob("*") if p.is_file()}
    result = compile_card(prepared)
    draft = json.loads(Path(result["draft"]).read_bytes())
    record = draft["official_requisites"][prepared["pdf_sha"]]
    assert record["status"] == "official_card"
    assert record["values"] == {"document_date": "2024-03-17", "document_number": "1165-р",
                                "document_type": "Распоряжение",
                                "signatory_authorities": ["Правительство Российской Федерации"]}
    assert record["card_asset_sha256"] == digest
    assert record["ocr_comparison"] == "not_required"
    assert draft["content"]["trees"][0]["identity_decision"]["status"] == "unresolved"
    assert "identity_unresolved" not in result["blockers"]
    assert "official_requisites_unavailable" not in result["blockers"]
    assert "ocr_review_required" in result["blockers"]
    assert draft["legal_admission"] == "not_requested"
    assert "1165-р" in Path(result["report"]).read_text(encoding="utf-8")
    assert compile_card(prepared)["result"] == "unchanged"
    assert compile_card(prepared, "separate")["draft_id"] == result["draft_id"]
    assert {p: p.read_bytes() for p in prepared["root"].rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("changes, missing", [({"number": None}, "document_number"),
    ({"documentDate": ""}, "document_date"), ({"documentType": {}}, "document_type"),
    ({"signatoryAuthorities": []}, "signatory_authorities")])
def test_empty_required_card_field_remains_explicit(prepared, changes, missing):
    put_card(prepared, **changes)
    result = compile_card(prepared)
    draft = json.loads(Path(result["draft"]).read_bytes())
    record = draft["official_requisites"][prepared["pdf_sha"]]
    assert record["status"] == "official_card_incomplete"
    assert missing in record["missing_fields"]
    assert "official_requisites_unavailable" in result["blockers"]
    assert "identity_unresolved" not in result["blockers"]


@pytest.mark.parametrize("damage", ["raw", "card_id", "item_id", "card_url", "card_role",
                                    "membership", "pdf_response", "card_request"])
def test_misbound_card_or_pdf_is_rejected_before_writing(prepared, damage):
    digest = prepared["card_sha"]
    root = prepared["root"]
    if damage == "raw":
        (root / "raw" / digest).write_bytes(b'{}')
    elif damage == "card_id":
        put_card(prepared, eoNumber="0001202403179999")
    elif damage in {"membership", "item_id"}:
        item = json.loads(prepared["item_path"].read_bytes())
        if damage == "membership":
            item["asset_sha256s"].remove(digest)
        else:
            item["external_id"] = "0001202403179999"
        write(prepared["item_path"], item)
    elif damage in {"card_url", "card_role"}:
        path = root / "assets" / f"{digest}.json"
        metadata = json.loads(path.read_bytes())
        if damage == "card_url":
            metadata["source_url"] = "http://publication.pravo.gov.ru/api/Document?eoNumber=0001202403179999"
        else:
            metadata["role"] = "unrelated_json"
        write(path, metadata)
    else:
        path = root / "assets" / f"{prepared['pdf_sha']}.json"
        metadata = json.loads(path.read_bytes())
        if damage == "pdf_response":
            metadata["transport_metadata"]["response_url"] = PDF_URL + "9999"
        else:
            metadata["transport_metadata"]["card_request"]["request_url"] = CARD_URL + "9999"
        write(path, metadata)
    with pytest.raises(ValueError):
        compile_card(prepared)
    assert not (prepared["output"] / "compiled").exists()


def test_missing_card_capture_keeps_structure_with_explicit_unavailable_status(prepared):
    path = prepared["root"] / "assets" / f"{prepared['pdf_sha']}.json"
    metadata = json.loads(path.read_bytes())
    del metadata["transport_metadata"]["card_request"]
    write(path, metadata)
    result = compile_card(prepared)
    draft = json.loads(Path(result["draft"]).read_bytes())
    record = draft["official_requisites"][prepared["pdf_sha"]]
    assert record["status"] == "unavailable"
    assert record["reason"] == "card_pdf_binding_missing"
    assert "official_requisites_unavailable" in result["blockers"]
    assert "identity_unresolved" not in result["blockers"]
    assert draft["content"]["trees"][0]["nodes"]


def test_selected_pdf_uses_its_capture_instead_of_latest_card_pointer(prepared):
    old_pdf_metadata = (prepared["root"] / "assets" / f"{prepared['pdf_sha']}.json").read_bytes()
    put_card(prepared, number="9999-р")
    (prepared["root"] / "assets" / f"{prepared['pdf_sha']}.json").write_bytes(old_pdf_metadata)
    result = compile_card(prepared)
    record = json.loads(Path(result["draft"]).read_bytes())["official_requisites"][prepared["pdf_sha"]]
    assert record["card_asset_sha256"] == prepared["card_sha"]
    assert record["values"]["document_number"] == "1165-р"
