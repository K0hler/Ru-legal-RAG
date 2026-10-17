"""Build retained-input OCR controls without importing or reading a parser.

This is an independent source audit, not a production parser or legal gold set.
Literal scope/ownership checks were authored from retained OCR and selected page
images. A separate, deliberately small prefix scanner inventories all blocks;
its unreviewed assignments must not be called exhaustive semantic review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data/m1/pilot_runs/m1-04-seal-recovery-20261016-v1/fresh"
INDEX = INPUT / "extractions/index-da25b7bc11033c9b5a5e65eb002e21cdd8c0db97621822a93901ac6377ccd9b0.json"
OUTPUT = ROOT / "data/m1/experiments/m1-04a-20261017-v1/controls"
APPROVED = "act/approved_text/1"
ANNEX = "act/annex/unnumbered-1"
SUPERSCRIPTS = "⁰¹²³⁴⁵⁶⁷⁸⁹"

# Exact-input control fixtures are intentionally asset-bound, unlike production rules.
SPECS = {
    "09d1df31": {"pages": 2, "blocks": 30, "number": "37", "body": 25, "signature": [29]},
    "14e725ed": {"pages": 2, "blocks": 39, "number": "13", "body": 14, "signature": [38], "noise": [(19, 37)], "quotes": [(17, 17, "act/item/1", None)]},
    "17ef26d6": {"pages": 3, "blocks": 30, "number": "6", "body": 9, "signature": [13], "annex": (15, 28), "operative": [29]},
    "2bc8a80b": {"pages": 4, "blocks": 61, "number": "2", "body": 9, "signature": [21], "noise": [(12, 20)], "annex": (25, 42), "operative": [9], "quotes": [(51, 53, ANNEX + "/item/1/subitem/б", None), (58, 58, ANNEX + "/item/2/subitem/а", None), (60, 60, ANNEX + "/item/2/subitem/б", "4")]},
    "4cdf224a": {"pages": 3, "blocks": 35, "number": "25", "body": 9, "signature": [24], "noise": [(12, 23)], "annex": (26, 32), "operative": [9, 33], "quotes": [(34, 34, ANNEX + "/operative/1", None)]},
    "5a6c0fc0": {"pages": 3, "blocks": 32, "number": "16", "body": 10, "signature": [11], "noise": [(12, 12)], "annex": (15, 29), "operative": [10, 30], "quotes": [(31, 31, ANNEX + "/operative/1", "35(1)")]},
    "66210869": {"pages": 75, "blocks": 963, "number": "3", "body": 9, "signature": [46, 47]},
    "a0ee4eb3": {"pages": 4, "blocks": 37, "number": "21", "body": 10, "signature": [12], "annex": (14, 23), "quotes": [(25, 25, ANNEX + "/item/1", "2"), (27, 27, ANNEX + "/item/2", None)]},
    "d1368055": {"pages": 4, "blocks": 45, "number": "10", "body": 9, "signature": [13], "annex": (18, 37), "quotes": [(43, 43, ANNEX + "/item/3", "4(1)")]},
    "d6b6b0e1": {"pages": 3, "blocks": 24, "number": "11", "body": 15, "signature": [23]},
}
SECTIONS = [
    (56, "I", 1, 2), (59, "II", 3, 65), (211, "III", 66, 74),
    (243, "IV", 75, 90), (287, "V", 91, 106), (331, "VI", 107, 116),
    (370, "VII", 117, 123), (390, "VIII", 124, 147), (455, "IX", 148, 156),
    (483, "X", 157, 266), (766, "XI", 267, 271), (775, "XII", 272, 288),
    (812, "XIII", 289, 299),
]
ANNEX_STARTS = [(848, 1), (856, 2), (873, 3), (878, 4), (900, 5), (923, 6), (930, 7), (937, 8), (951, 9)]
TABLES = [
    ([852, 854], 1, None, "1"), ([876], 3, None, "1"),
    ([884], 4, 2, "1"), ([887, 889], 4, 3, "2"), ([892], 4, 4, "3"),
    ([926, 928], 6, None, "1"), ([933, 935], 7, None, "1"),
    ([943], 8, None, "form-1"), ([946], 8, None, "form-2"), ([949], 8, None, "form-3"),
    ([954], 9, None, "1"), ([957, 959], 9, None, "2"),
]
# Only these pages were actually opened with view_image during authoring.
IMAGE_REVIEW = {
    "66210869": {1: "approving act and registration; numbered item starts", 2: "item 1 continuation; items 2-4 and decimal subitems", 6: "approved text, sections I/II, items and notes", 8: "notes 8-12 and item 11", 9: "note 12 continuation separated by footnote rule", 33: "Roman X despite Cyrillic OCR lookalike; note 48", 57: "lettered children of item 291(2)", 59: "annex 1 table and merged cells", 60: "annex 1 table continuation", 64: "annex 4 table 1 and beginning of table 2", 65: "table 2 continuation; table 3; superscript loss in OCR cells", 72: "annex 8 three journal forms and blank rows", 74: "annex 9 indicator table, 9 columns", 75: "table continuation and three legend lines; quality exclusion only"},
    "09d1df31": {2: "item 1 continuation, item 2 and round seal"},
    "14e725ed": {2: "replacement quote under item 1; item 2 and seal junk"},
    "17ef26d6": {3: "unnumbered annex and unnumbered change instruction"},
    "2bc8a80b": {4: "continued lettered changes; quoted paragraph and quoted footnote 4"},
    "4cdf224a": {3: "unnumbered annex, instruction and replacement quote"},
    "5a6c0fc0": {3: "approved unnumbered annex, quoted item 35(1)"},
    "a0ee4eb3": {3: "annex items 1-3; quoted foreign item 2 and notes 1-3"},
    "d1368055": {4: "annex item 3 continuation, quoted foreign item 4(1), next own item 4"},
    "d6b6b0e1": {3: "item 3 continuation, own item 4, signature and seal"},
}


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_new(path: Path, value: object) -> str:
    raw = canonical(value)
    if path.exists() and path.read_bytes() != raw:
        raise ValueError(f"Refusing to overwrite changed retained controls: {path}")
    path.write_bytes(raw)
    return digest(raw)


def original_table_map() -> dict:
    tables = {}
    for ids, annex, item, table in TABLES:
        parent = f"{APPROVED}/annex/{annex}"
        if item is not None:
            parent += f"/item/{item}"
        address = f"{parent}/table/{table}"
        for block_id in ids:
            tables[block_id] = (address, parent, ids[0])
    return tables


def scan_source(extraction: dict, prefix: str, spec: dict) -> list[dict]:
    """Independent prefix inventory with literal, asset-bound scope boundaries."""
    regions = {r["region_id"]: r for p in extraction["pages"] for r in p["regions"]}
    section_map = {b: n for b, n, _, _ in SECTIONS} if prefix == "66210869" else {}
    annex_map = dict(ANNEX_STARTS) if prefix == "66210869" else {}
    tables = original_table_map() if prefix == "66210869" else {}
    scope = owner = "act"
    item = numeric_subitem = None
    operative_counts = Counter()
    result = []
    for block in extraction["blocks"]:
        bid, text = block["block_id"], block["text"]
        page = block["source_span"]["page"]
        category = regions[block["source_region_id"]]["category"]
        row = {"block_id": bid, "source_block_id": block["source_block_id"], "source_region_id": block["source_region_id"], "page": page, "locator": block["locator"], "source_span": block["source_span"], "text_sha256": digest(text.encode("utf-8")), "text": text, "kind": "paragraph", "number": None, "address": None, "expected_parent": None, "expected_owner": owner, "basis": "independent_source_scanner_unreviewed", "status": "inferred"}
        if category == "Page-header" and text.isdigit() and int(text) == page:
            row.update(kind="page_number", expected_owner="act", status="non_provision")
        elif any(a <= bid <= z for a, z in spec.get("noise", [])):
            row.update(kind="seal_text", expected_owner="act", status="non_provision", basis="literal_source_scope")
        elif bid in spec.get("signature", []):
            row.update(kind="signature", expected_owner="act", status="non_provision")
        elif prefix == "66210869" and bid == 49:
            scope = owner = APPROVED
            item = numeric_subitem = None
            row.update(kind="approved_text", address=scope, expected_parent="act", expected_owner=scope, basis="literal_source_scope")
        elif bid in section_map:
            scope = owner = f"{APPROVED}/section/{section_map[bid]}"
            item = numeric_subitem = None
            row.update(kind="section", number=section_map[bid], address=scope, expected_parent=APPROVED, expected_owner=scope, basis="literal_source_scope")
        elif bid in annex_map:
            scope = owner = f"{APPROVED}/annex/{annex_map[bid]}"
            item = numeric_subitem = None
            row.update(kind="annex", number=str(annex_map[bid]), address=scope, expected_parent=APPROVED, expected_owner=scope, basis="literal_source_scope")
        elif spec.get("annex", (None,))[0] == bid:
            scope = owner = ANNEX
            item = numeric_subitem = None
            row.update(kind="annex", address=scope, expected_parent="act", expected_owner=scope, basis="literal_source_scope", printed_number=None)
        elif (prefix == "66210869" and 49 < bid < 56) or ("annex" in spec and spec["annex"][0] < bid <= spec["annex"][1]):
            row.update(kind="scope_heading", expected_owner=scope, basis="literal_source_scope")
        elif block["note"]:
            row.update(kind="note", expected_owner=None, status="unresolved")
        elif bid in tables:
            address, parent, start = tables[bid]
            row.update(kind="table", address=address, expected_parent=parent, expected_owner=parent, table_start_block_id=start, basis="literal_source_scope")
        elif block["table_cells"]:
            row.update(kind="registration_metadata", expected_owner="act", status="non_provision")
        elif bid < spec["body"]:
            row.update(kind="act_metadata", expected_owner="act", status="non_provision")
        else:
            quote = next((q for q in spec.get("quotes", []) if q[0] <= bid <= q[1]), None)
            decimal = re.match(r"^(\d+(?:\.\d+)*)\.\s", text)
            numeric = re.match(r"^(\d+)\)\s", text)
            letter = re.match(r"^([а-я])\)\s", text)
            if quote:
                first, _, parent, number = quote
                row.update(kind="quoted_payload", number=number, address=f"{parent}/quote/{first}", expected_parent=parent, expected_owner=parent, basis="literal_source_quote_scope", quoted_foreign_number=number)
            elif bid in spec.get("operative", []):
                operative_counts[scope] += 1
                owner = f"{scope}/operative/{operative_counts[scope]}"
                row.update(kind="operative_paragraph", address=owner, expected_parent=scope, expected_owner=owner, basis="literal_source_scope")
            elif decimal:
                number = decimal[1]
                if "." in number:
                    parent_number = number.rsplit(".", 1)[0]
                    parent = f"{scope}/item/{parent_number}"
                    address = f"{parent}/subitem/{number}"
                    owner = address
                else:
                    parent = scope
                    item = owner = f"{scope}/item/{number}"
                    numeric_subitem = None
                    address = owner
                row.update(kind="subitem" if "." in number else "item", number=number, address=address, expected_parent=parent, expected_owner=owner)
            elif numeric or letter:
                number = (numeric or letter)[1]
                parent = item if numeric else (numeric_subitem or item)
                if parent is None:
                    row.update(kind="unresolved_number", number=number, expected_owner=None, status="unresolved")
                else:
                    owner = f"{parent}/subitem/{number}"
                    if numeric:
                        numeric_subitem = owner
                    row.update(kind="subitem", number=number, address=owner, expected_parent=parent, expected_owner=owner)
            else:
                row["expected_owner"] = owner
        result.append(row)
    # Match exact superscript tokens, rather than assigning every footer to the last item.
    for row in result:
        if row["kind"] != "note":
            continue
        match = re.match(f"^([{SUPERSCRIPTS}]+)\\s", row["text"])
        if not match:
            row["unresolved_reason"] = "note_marker_not_readable"
            continue
        token = match[1]
        number = token.translate(str.maketrans(SUPERSCRIPTS, "0123456789"))
        ref = re.compile(f"(?<![{SUPERSCRIPTS}]){token}(?![{SUPERSCRIPTS}])")
        candidates = [r for r in result if r["block_id"] < row["block_id"] and row["page"] - 2 <= r["page"] <= row["page"] and r["kind"] in {"item", "subitem", "paragraph", "operative_paragraph"} and ref.search(r["text"])]
        owners = {r["expected_owner"] for r in candidates}
        row.update(number=number, reference_block_ids=[r["block_id"] for r in candidates])
        if len(owners) == 1 and None not in owners:
            parent = next(iter(owners))
            row.update(address=f"{parent}/note/{number}", expected_parent=parent, expected_owner=parent, status="inferred")
        else:
            row["unresolved_reason"] = "nonunique_or_absent_literal_note_reference"
    if prefix == "66210869":
        note = result[92]
        assert note["number"] == "12"
        result[105].update(kind="note_continuation", number="12", address=note["address"], expected_parent=note["expected_parent"], expected_owner=note["address"], basis="literal_image_review", status="literal_control", continuation_of_block_id=92)
        for bid in (960, 961, 962):
            result[bid].update(kind="table_legend", expected_owner=f"{APPROVED}/annex/9/table/2", basis="literal_image_review")
    return result


def literal_checks(prefix: str) -> list[tuple]:
    checks = {
        "09d1df31": [(25, "item", "1", "act", "1. В пункте 5"), (27, "paragraph", None, "act/item/1", "норм СанПиН"), (28, "item", "2", "act", "2. Настоящее")],
        "14e725ed": [(14, "item", "1", "act", "1. Второе предложение"), (16, "paragraph", None, "act/item/1", "и питьевому"), (17, "quoted_payload", None, "act/item/1", "«Размещение над гаражами"), (18, "item", "2", "act", "2. Настоящее"), (19, "seal_text", None, "act", "ФЕДЕРАЦИЯ")],
        "17ef26d6": [(9, "item", "1", "act", "1. Внести"), (11, "paragraph", None, "act/item/1", "эксплуатации"), (15, "annex", None, "act", "Приложение"), (29, "operative_paragraph", None, ANNEX, "В пункте 35(1)")],
        "2bc8a80b": [(9, "operative_paragraph", None, "act", "внести изменения"), (11, "paragraph", None, "act/operative/1", "и сельских"), (25, "annex", None, "act", "Приложение"), (43, "item", "1", ANNEX, "1. В санитарных"), (44, "subitem", "а", ANNEX + "/item/1", "а) в пункте 282"), (49, "subitem", "б", ANNEX + "/item/1", "б) абзац второй"), (51, "quoted_payload", None, ANNEX + "/item/1/subitem/б", "«В случае"), (55, "subitem", "в", ANNEX + "/item/1", "в) пункт 286"), (56, "item", "2", ANNEX, "2. В санитарных"), (60, "quoted_payload", "4", ANNEX + "/item/2/subitem/б", "«⁴ Пункты 272")],
        "4cdf224a": [(9, "operative_paragraph", None, "act", "Внести изменение"), (11, "paragraph", None, "act/operative/1", "санитарно-противоэпидемических"), (26, "annex", None, "act", "Приложение"), (33, "operative_paragraph", None, ANNEX, "Пункт 34 дополнить"), (34, "quoted_payload", None, ANNEX + "/operative/1", "«В районах Крайнего")],
        "5a6c0fc0": [(10, "operative_paragraph", None, "act", "Внести изменение"), (15, "annex", None, "act", "Приложение"), (30, "operative_paragraph", None, ANNEX, "Дополнить пунктом 35(1)"), (31, "quoted_payload", "35(1)", ANNEX + "/operative/1", "«35(1). До 1 марта")],
        "a0ee4eb3": [(10, "item", "1", "act", "1. Внести"), (14, "annex", None, "act", "Приложение"), (24, "item", "1", ANNEX, "1. Постановление"), (25, "quoted_payload", "2", ANNEX + "/item/1", "«2. Настоящее"), (26, "item", "2", ANNEX, "2. Постановление"), (28, "item", "3", ANNEX, "3. В пункте 3"), (33, "item", "4", ANNEX, "4. В пункте 4"), (34, "item", "5", ANNEX, "5. Пункт 5")],
        "d1368055": [(9, "item", "1", "act", "1. Внести"), (11, "paragraph", None, "act/item/1", "классификация"), (18, "annex", None, "act", "Приложение"), (40, "item", "3", ANNEX, "3. Постановление"), (42, "paragraph", None, ANNEX + "/item/3", "жилым помещениям"), (43, "quoted_payload", "4(1)", ANNEX + "/item/3", "«4(1). Признать"), (44, "item", "4", ANNEX, "4. В пункте 5")],
        "d6b6b0e1": [(15, "item", "1", "act", "1. В пункте 3"), (17, "paragraph", None, "act/item/1", "Российской Федерации"), (19, "item", "3", "act", "3. В пункте 5"), (21, "paragraph", None, "act/item/3", "29.01.2021"), (22, "item", "4", "act", "4. Настоящее")],
    }
    if prefix != "66210869":
        return checks[prefix]
    checks = [(9, "item", "1", "act", "1. Утвердить"), (11, "paragraph", None, "act/item/1", "водоснабжению"), (15, "subitem", "4.1", "act/item/4", "4.1. Постановление"), (21, "paragraph", None, "act/item/4/subitem/4.5", "СанПиН 2.1.7.1287"), (49, "approved_text", None, "act", "УТВЕРЖДЕНЫ"), (57, "item", "1", APPROVED + "/section/I", "1. Настоящие"), (60, "item", "3", APPROVED + "/section/II", "3. На территориях"), (65, "paragraph", None, APPROVED + "/section/II/item/3", "с автоматическими"), (61, "note", "1", APPROVED + "/section/II/item/3", "¹ Статья"), (92, "note", "12", APPROVED + "/section/II/item/11", "¹² Приказ"), (105, "note_continuation", "12", APPROVED + "/section/II/item/11", "(зарегистрирован Минюстом России 24.04.2017"), (122, "paragraph", None, APPROVED + "/section/II/item/27", "1 раза в сутки"), (146, "paragraph", None, APPROVED + "/section/II/item/42", "к организации"), (623, "subitem", "е", APPROVED + "/section/X/item/200", "е) при любом"), (669, "paragraph", None, APPROVED + "/section/X/item/211/subitem/а", "осуществляющих работы"), (781, "subitem", "1", APPROVED + "/section/XII/item/273", "1) во дворах"), (826, "subitem", "а", APPROVED + "/section/XIII/item/291/subitem/2", "а) квадратный корень"), (827, "subitem", "б", APPROVED + "/section/XIII/item/291/subitem/2", "б) сумма"), (859, "item", "1", APPROVED + "/annex/2", "1. Выбор показателей"), (869, "item", "8", APPROVED + "/annex/2", "8. В перечень"), (960, "table_legend", None, APPROVED + "/annex/9/table/2", 'Знак "+"'), (962, "table_legend", None, APPROVED + "/annex/9/table/2", 'знак "+/-"')]
    checks += [(bid, "section", number, APPROVED, "##" if bid != 211 else "###") for bid, number, _, _ in SECTIONS]
    checks += [(bid, "annex", str(number), APPROVED, f"Приложение № {number}") for bid, number in ANNEX_STARTS]
    for ids, annex, item, _ in TABLES:
        parent = f"{APPROVED}/annex/{annex}" + (f"/item/{item}" if item else "")
        checks += [(bid, "table", None, parent, None) for bid in ids]
    return checks


def build(index_path: Path, output: Path) -> dict:
    index_bytes = index_path.read_bytes()
    index = json.loads(index_bytes)
    assert len(index["extractions"]) == 10
    output.mkdir(parents=True, exist_ok=True)
    documents = []
    for asset, record in sorted(index["extractions"].items()):
        prefix = asset[:8]
        spec = SPECS[prefix]
        path = index_path.parent / record["path"]
        raw = path.read_bytes()
        extraction = json.loads(raw)
        assert extraction["source_asset_sha256"] == asset
        assert extraction["extraction_id"] == record["extraction_id"]
        assert len(extraction["pages"]) == spec["pages"]
        assert len(extraction["blocks"]) == spec["blocks"]
        assert extraction["blocks"] == [b for p in extraction["pages"] for b in p["blocks"]]
        rows = scan_source(extraction, prefix, spec)
        checks = []
        for bid, kind, number, parent_or_owner, literal in literal_checks(prefix):
            row = rows[bid]
            assert row["kind"] == kind, (prefix, bid, row)
            assert row["number"] == number, (prefix, bid, row)
            parent = row["expected_parent"] if row["address"] else row["expected_owner"]
            assert parent == parent_or_owner, (prefix, bid, parent, parent_or_owner)
            assert literal is None or row["text"].startswith(literal), (prefix, bid, literal)
            checks.append({"block_id": bid, "kind": kind, "number": number, "expected_parent_or_owner": parent_or_owner, "address": row["address"], "literal_prefix": literal, "text_sha256": row["text_sha256"], "locator": row["locator"], "page": row["page"], "source_span": row["source_span"], "image_inspected": row["page"] in IMAGE_REVIEW[prefix]})
            row["status"] = "literal_control"
        assert len({r["block_id"] for r in rows}) == len(rows)
        images = []
        for page, scope in sorted(IMAGE_REVIEW[prefix].items()):
            image_path = INPUT / "ocr-evidence" / record["native_evidence_id"] / "pages" / f"page_{page:04d}.png"
            images.append({"page": page, "path": image_path.relative_to(ROOT).as_posix(), "sha256": digest(image_path.read_bytes()), "review_scope": scope, "reviewer_type": "codex_agent_visual_inspection", "human_review": False})
        table_inventory = [{"block_id": b["block_id"], "source_region_id": b["source_region_id"], "source_span": b["source_span"], "cells": b["table_cells"], "cells_sha256": digest(canonical(b["table_cells"])), "expected_owner": rows[b["block_id"]]["expected_owner"], "topology_status": "retained_ocr_topology_not_exhaustive_image_cell_validation"} for b in extraction["blocks"] if b["table_cells"]]
        region_inventory = []
        for page in extraction["pages"]:
            for region in page["regions"]:
                members = [r for r in rows if r["source_region_id"] == region["region_id"]]
                region_inventory.append({"page": page["page"], "region_id": region["region_id"], "category": region["category"], "json_pointer": region["json_pointer"], "bbox": region["bbox"], "block_ids": [r["block_id"] for r in members], "owner_candidates": sorted({r["expected_owner"] for r in members if r["expected_owner"]}), "unresolved_physical_region": not bool(members), "disposition": "retain_in_physical_tree_even_if_no_text"})
        unresolved = [{"block_id": r["block_id"], "reason": r.get("unresolved_reason"), "page": r["page"], "locator": r["locator"]} for r in rows if r["status"] == "unresolved"]
        document = {"schema_version": "ocr-source-controls/1", "source_asset_sha256": asset, "extraction_id": extraction["extraction_id"], "extraction_sha256": digest(raw), "extraction_path": path.relative_to(ROOT).as_posix(), "native_evidence_id": record["native_evidence_id"], "expected_act_number": spec["number"], "pages": spec["pages"], "blocks": spec["blocks"], "literal_controls": checks, "block_dispositions": rows, "tables": table_inventory, "physical_regions": region_inventory, "image_review": images, "unresolved": unresolved, "confidence": {"literal_controls": "independently_authored_source_relationships", "other_dispositions": "source_only_prefix_scanner_inference_requires_semantic_review", "full_normalized_input_read": True, "full_image_semantic_review": False, "human_review": False, "legal_admission": False}}
        filename = f"{asset}.json"
        sha = write_new(output / filename, document)
        documents.append({"source_asset_sha256": asset, "extraction_id": extraction["extraction_id"], "extraction_sha256": digest(raw), "path": filename, "controls_sha256": sha, "pages": spec["pages"], "blocks": spec["blocks"], "literal_controls": len(checks), "reviewed_images": len(images), "table_regions": len(table_inventory), "physical_regions": len(region_inventory), "unresolved_blocks": len(unresolved), "kind_counts": dict(sorted(Counter(r["kind"] for r in rows).items()))})
    manifest = {"schema_version": "ocr-source-controls-index/1", "index_id": index["index_id"], "index_sha256": digest(index_bytes), "generator_sha256": digest(Path(__file__).read_bytes()), "documents": documents, "independence": {"candidate_code_read": False, "candidate_outputs_read": False, "dedoc_outputs_read": False, "closed_gold_read": False, "reserved_cohort_read": False, "network_or_new_ocr": False, "method": "literal source/image relationship assertions plus separate stdlib prefix scanner"}, "review_limits": {"human_review": False, "full_image_semantic_review": False, "all_input_pages_block_accounted": True, "all_blocks_semantically_qualified": False, "quality_exclusions": ["round-seal transcription accuracy only; regions and text retained", "original SanPiN physical-page-75 table quality only; ownership, cells, text and locators retained"], "remaining_unknowns": ["Unreviewed scanner dispositions are not independently established gold.", "Retained table cell topology is not an exhaustive source-image topology/semantics check.", "OCR superscript attachments in annex 4 table 2 are flattened (for example 501); no silent repair.", "Empty Picture regions retain physical evidence but their semantic content is not transcribed by these controls."]}, "totals": {key: sum(d[key] for d in documents) for key in ("pages", "blocks", "literal_controls", "reviewed_images", "table_regions", "physical_regions", "unresolved_blocks")}}
    write_new(output / "index.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    manifest = build(INDEX, args.output)
    print(json.dumps(manifest["totals"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
