import base64
from contextlib import redirect_stdout
import hashlib
from html import escape
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
FIXTURE = Path(__file__).with_name("fixtures") / "publication_discovery_2026_09_26.json"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402
from legal_rag.sources.acquisition import _persist_success  # noqa: E402
from legal_rag.sources.relations import _stable_id  # noqa: E402
from legal_rag.corpus.pdf_extraction import normalize_dotsmocr  # noqa: E402


class ReplayResponse:
    def __init__(self, body: bytes, url: str, content_type: str):
        self._body = body
        self._url = url
        self.headers = {"Content-Type": content_type}
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._body


class PublicationDiscoveryTest(unittest.TestCase):
    def setUp(self):
        sleeper = patch("legal_rag.sources.transport.sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def test_feed_discovers_amendment_invalidates_candidate_and_replays_idempotently(self):
        replay = json.loads(FIXTURE.read_text(encoding="utf-8"))
        responses = self._responses(replay) * 2
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            candidate_path = self._write_pp491_candidate(data_dir)
            index_path = self._write_extractions(replay, data_dir / "shared")
            outputs = []
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=responses,
            ) as urlopen:
                for _ in range(2):
                    stdout = StringIO()
                    with redirect_stdout(stdout):
                        self.assertEqual(
                            main(
                                [
                                    "discover-publications",
                                    "--date",
                                    "2026-09-26",
                                    "--data-dir",
                                    str(data_dir),
                                    "--extraction-index",
                                    str(index_path),
                                    "--timeout",
                                    "2.5",
                                ]
                            ),
                            0,
                        )
                    outputs.append(json.loads(stdout.getvalue()))

            self.assertEqual([output["result"] for output in outputs], ["new", "unchanged"])
            self.assertEqual(outputs[0]["report"], outputs[1]["report"])
            self.assertEqual(outputs[0]["publication_event_count"], 2)
            self.assertEqual(outputs[0]["resolved_relation_count"], 1)
            self.assertEqual(outputs[0]["unresolved_target_count"], 1)
            self.assertEqual(len(list((data_dir / "publication_events").glob("*.json"))), 2)
            self.assertEqual(len(list((data_dir / "relations").glob("*.json"))), 2)
            self.assertEqual(len(list((data_dir / "exceptions").glob("*.json"))), 1)
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 5)

            requested_urls = [call.args[0].full_url for call in urlopen.call_args_list]
            self.assertEqual(requested_urls[0], replay["provenance"]["feed_url"])
            self.assertNotIn("--eo-number", requested_urls[0])
            self.assertEqual(requested_urls[5], replay["provenance"]["feed_url"])

            relations = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (data_dir / "relations").glob("*.json")
            ]
            amendment = next(relation for relation in relations if relation["relation_type"] == "amends")
            self.assertEqual(
                amendment["from_source_item"],
                "declared-act:government-decree:2026-09-26:1242",
            )
            self.assertEqual(
                amendment["to_source_item"],
                "declared-act:government-decree:2006-08-13:491",
            )
            self.assertEqual(amendment["review_state"], "source_claim")
            self.assertIn("PDF page 3", amendment["evidence_reference"]["locator"])
            self.assertIn("/pages/2/blocks", amendment["evidence_reference"]["locator"])
            extraction_id = amendment["evidence_reference"]["extraction_id"]
            extraction = json.loads((data_dir / "extractions" / f"{extraction_id}.json").read_text("utf-8"))
            self.assertEqual(extraction["schema_version"], "text-extraction/1")
            self.assertEqual(extraction_id, _stable_id({key: value for key, value in extraction.items() if key != "extraction_id"}))
            evidence_sha256 = amendment["evidence_reference"]["source_asset_sha256"]
            self.assertEqual(
                (data_dir / "raw" / evidence_sha256).read_bytes(),
                base64.b64decode(replay["documents"][0]["asset_body_base64"]),
            )

            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            self.assertEqual(candidate["candidate_status"], "stale")
            self.assertEqual(len(candidate["candidate_invalidations"]), 1)
            self.assertEqual(
                candidate["candidate_invalidations"][0]["source_relation_id"],
                amendment["relation_id"],
            )
            self.assertIn(
                "newer_amendment_detected",
                {item["reason"] for item in candidate["unresolved_items"]},
            )

            resync = _persist_success(
                {
                    "adapter_version": candidate["adapter_version"],
                    "captured_at": "2026-09-29T15:00:00Z",
                    "declared_act_identity": candidate["declared_act_identity"],
                    "declared_edition_label": candidate["declared_edition_label"],
                    "declared_publication": None,
                    "edition_claim": candidate["edition_claim"],
                    "external_id": candidate["external_id"],
                    "item_kind": "edition_candidate",
                    "label": candidate["label"],
                    "media_type": "application/json",
                    "raw_bytes": b'{"resynced":true}',
                    "request_cursor": candidate["external_id"],
                    "rights_status": candidate["rights_status"],
                    "source_system": candidate["source_system"],
                    "source_url": candidate["source_url"],
                    "temporal_coverage": candidate["temporal_coverage"],
                    "transport_metadata": {"fixture": "candidate-resync"},
                    "unresolved_items": [],
                },
                data_dir,
                "2026-09-29T15:00:00Z",
                {"bytes_received": 17, "request_count": 0},
            )
            self.assertEqual(resync["result"], "changed")
            resynced_candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            self.assertEqual(resynced_candidate["candidate_status"], "stale")
            self.assertEqual(len(resynced_candidate["candidate_invalidations"]), 1)
            self.assertIn(
                "newer_amendment_detected",
                {item["reason"] for item in resynced_candidate["unresolved_items"]},
            )

            exception = json.loads(next((data_dir / "exceptions").glob("*.json")).read_text("utf-8"))
            self.assertEqual(exception["reason"], "unresolved_amendment_target")
            self.assertEqual(exception["stage"], "publication_discovery")

    def test_missing_extraction_can_be_supplied_before_replaying_the_same_feed(self):
        replay = json.loads(FIXTURE.read_text("utf-8"))
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            candidate_path = self._write_pp491_candidate(data_dir)
            with patch("legal_rag.sources.publication_pravo.urlopen", side_effect=self._responses(replay) * 2):
                first = self._discover(data_dir)
                self.assertEqual(first["result"], "failed")
                self.assertEqual(first["resolved_relation_count"], 0)
                self.assertNotIn("candidate_status", json.loads(candidate_path.read_text("utf-8")))
                exceptions = [json.loads(path.read_text("utf-8")) for path in (data_dir / "exceptions").glob("*.json")]
                self.assertTrue(all("--extraction-index" in entry["diagnostic_message"] for entry in exceptions))
                index_path = self._write_extractions(replay, data_dir / "shared")
                second = self._discover(data_dir, index_path)
            self.assertEqual(second["resolved_relation_count"], 1)
            self.assertEqual(json.loads(candidate_path.read_text("utf-8"))["candidate_status"], "stale")

    def test_projected_table_text_retains_its_source_span(self):
        replay = json.loads(FIXTURE.read_text("utf-8"))
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._write_pp491_candidate(data_dir)
            index_path = self._write_extractions(replay, data_dir / "shared", table=True)
            with patch("legal_rag.sources.publication_pravo.urlopen", side_effect=self._responses(replay)):
                result = self._discover(data_dir, index_path)
            self.assertEqual(result["resolved_relation_count"], 1)

    def test_invalid_shared_extractions_cannot_create_relations(self):
        replay = json.loads(FIXTURE.read_text("utf-8"))
        for mutation in ("missing_index", "index_hash", "index_shape", "extraction_hash", "wrong_pdf", "missing_page", "duplicate_page", "missing_locator", "invalid_locator", "missing_offsets", "missing_region", "wrong_offsets", "wrong_span_text", "wrong_span_pdf", "wrong_span_page", "ambiguous_target"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary_directory:
                data_dir = Path(temporary_directory)
                candidate_path = self._write_pp491_candidate(data_dir)
                candidate_before = candidate_path.read_bytes()
                index_path = self._write_extractions(replay, data_dir / "shared")
                index = json.loads(index_path.read_text("utf-8"))
                reference = next(iter(index["extractions"].values()))
                extraction_path = index_path.parent / reference["path"]
                extraction = json.loads(extraction_path.read_text("utf-8"))
                if mutation == "missing_index":
                    index_path.unlink()
                elif mutation == "index_hash":
                    index["input_hash"] = "0" * 64
                    index_path.write_text(json.dumps(index), encoding="utf-8")
                elif mutation == "index_shape":
                    index["extractions"] = []
                    index.pop("index_id")
                    index["index_id"] = _stable_id(index)
                    index_path.write_text(json.dumps(index), encoding="utf-8")
                elif mutation == "extraction_hash":
                    extraction["blocks"][0]["text"] += " altered"
                    extraction_path.write_text(json.dumps(extraction), encoding="utf-8")
                else:
                    if mutation == "wrong_pdf":
                        extraction["source_asset_sha256"] = "0" * 64
                    elif mutation == "missing_page":
                        extraction["pages"].pop()
                    elif mutation == "duplicate_page":
                        extraction["pages"][-1]["page"] = 1
                    elif mutation == "missing_locator":
                        del extraction["pages"][2]["blocks"][0]["source_span"]["locator"]
                    elif mutation == "invalid_locator":
                        extraction["pages"][2]["blocks"][0]["source_span"]["locator"] = "ocr:/pages/0/layout/0/text:chars:0:1"
                    elif mutation in {"missing_offsets", "missing_region", "wrong_offsets", "wrong_span_text"}:
                        block = extraction["pages"][2]["blocks"][0]
                        span = block["source_span"]
                        if mutation == "missing_offsets":
                            del span["ocr_char_start"], span["ocr_char_end"]
                        elif mutation == "missing_region":
                            span["json_pointer"] = "/pages/2/layout/99999/text"
                        elif mutation == "wrong_offsets":
                            span.update(ocr_char_start=0, ocr_char_end=1)
                        else:
                            block["text"] = "1. Изменённый текст"
                        span["locator"] = f"ocr:{span['json_pointer']}:chars:{span.get('ocr_char_start')}:{span.get('ocr_char_end')}"
                    elif mutation == "wrong_span_pdf":
                        extraction["pages"][2]["blocks"][0]["source_span"]["source_asset_sha256"] = "0" * 64
                    elif mutation == "wrong_span_page":
                        extraction["pages"][2]["blocks"][0]["source_span"]["page"] = 1
                    elif mutation == "ambiguous_target":
                        text = "постановлением Правительства Российской Федерации от 13 августа 2006 г. № 4910 или № 491"
                        extraction["pages"][2]["blocks"][0]["text"] = text
                    extraction.pop("extraction_id")
                    extraction["extraction_id"] = _stable_id(extraction)
                    reference.update(path=extraction["extraction_id"] + ".json", extraction_id=extraction["extraction_id"])
                    (index_path.parent / reference["path"]).write_text(json.dumps(extraction), encoding="utf-8")
                    index.pop("index_id")
                    index["index_id"] = _stable_id(index)
                    index_path.write_text(json.dumps(index), encoding="utf-8")
                with patch("legal_rag.sources.publication_pravo.urlopen", side_effect=self._responses(replay)):
                    result = self._discover(data_dir, index_path)
                self.assertEqual(result["resolved_relation_count"], 0)
                self.assertEqual(candidate_path.read_bytes(), candidate_before)
                self.assertFalse((data_dir / "relations").exists())
                self.assertGreater(result["unresolved_target_count"], 0)

    def _discover(self, data_dir, index_path=None):
        arguments = ["discover-publications", "--date", "2026-09-26", "--data-dir", str(data_dir)]
        if index_path is not None:
            arguments.extend(["--extraction-index", str(index_path)])
        stdout = StringIO()
        with redirect_stdout(stdout), patch("legal_rag.sources.transport.sleep"):
            main(arguments)
        return json.loads(stdout.getvalue())

    @staticmethod
    def _write_extractions(replay, directory, table=False):
        directory.mkdir()
        entries = {}
        for document in replay["documents"]:
            digest = hashlib.sha256(base64.b64decode(document["asset_body_base64"])).hexdigest()
            pages = document["ocr_pages"]
            layouts = [[{"category": "Text", "bbox": [0, 0, 100, 100], "text": text}] for text in pages]
            if table:
                layouts = [[{**layout[0], "category": "Table", "text": "<table><tr><td>" + escape(layout[0]["text"]) + "</td></tr></table>"}] for layout in layouts]
            native = {"pages": [{"page_number": i + 1, "image_size": [100, 100], "layout": layout,
                      "native": {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(layout)}}]}}
                     for i, layout in enumerate(layouts)]}
            run = {"engine": "dotsmocr", "source_sha256": digest, "status": "complete", "source_pages": len(pages),
                   "requested_pages": list(range(1, len(pages) + 1)), "completed_pages": list(range(1, len(pages) + 1)),
                   "model": {"repo": "dots-studio/dots.mocr", "revision": "b" * 40,
                             "weights_sha256": {"model.safetensors": "c" * 64}}, "config": {}}
            extraction = normalize_dotsmocr(native, run, digest)
            name = extraction["extraction_id"] + ".json"
            (directory / name).write_text(json.dumps(extraction, ensure_ascii=False), encoding="utf-8")
            entries[digest] = {"path": name, "extraction_id": extraction["extraction_id"], "native_evidence_id": "d" * 64}
        index = {"schema_version": "extraction-index/1", "input_hash": "e" * 64, "permission_hash": "f" * 64, "extractions": entries}
        index["index_id"] = _stable_id(index)
        path = directory / "index.json"
        path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        return path

    @staticmethod
    def _responses(replay: dict[str, object]) -> list[ReplayResponse]:
        responses = [
            ReplayResponse(
                json.dumps(replay["feed"], ensure_ascii=False).encode("utf-8"),
                replay["provenance"]["feed_url"],
                "application/json; charset=utf-8",
            )
        ]
        for document in replay["documents"]:
            eo_number = document["card"]["eoNumber"]
            responses.extend(
                [
                    ReplayResponse(
                        json.dumps(document["card"], ensure_ascii=False).encode("utf-8"),
                        f"http://publication.pravo.gov.ru/api/Document?eoNumber={eo_number}",
                        "application/json; charset=utf-8",
                    ),
                    ReplayResponse(
                        base64.b64decode(document["asset_body_base64"]),
                        f"http://publication.pravo.gov.ru/File/Pdf?eoNumber={eo_number}",
                        "application/octet-stream",
                    ),
                ]
            )
        return responses

    @staticmethod
    def _write_pp491_candidate(data_dir: Path) -> Path:
        target = "declared-act:government-decree:2006-08-13:491"
        candidate = {
            "adapter_version": "legislation-russia/3",
            "asset_sha256s": [],
            "captured_at": "2026-09-29T07:58:36Z",
            "declared_act_identity": "Постановление Правительства Российской Федерации от 13.08.2006 № 491",
            "declared_edition_label": "на 01.09.2025",
            "discovered_source_items": [
                {
                    "declared_act_identity": "Постановление Правительства Российской Федерации от 13.08.2006 № 491",
                    "external_id": "government-decree:2006-08-13:491",
                    "item_kind": "act",
                    "label": "Постановление Правительства Российской Федерации от 13.08.2006 № 491",
                    "source_item": target,
                    "source_system": "declared-act",
                    "source_url": "http://ips.pravo.gov.ru/search/test-pp491",
                }
            ],
            "edition_claim": {
                "claimed_edition_date": "2025-09-01",
                "claimed_edition_label": "на 01.09.2025",
                "source_asset_sha256": "candidate-card-sha256",
            },
            "external_id": "test-pp491",
            "item_kind": "edition_candidate",
            "label": "ПП РФ № 491 candidate",
            "latest_successful_asset": "candidate-text-sha256",
            "relation_claims": [
                {
                    "asserted_by": "pravo.gov.ru/legislation-russia",
                    "evidence_reference": {
                        "locator": "$.hash; $.nd; $.adoption",
                        "source_asset_sha256": "candidate-card-sha256",
                        "source_url": "http://ips.pravo.gov.ru/search/test-pp491",
                    },
                    "from_source_item": "pravo.gov.ru/legislation-russia:test-pp491",
                    "relation_type": "consolidates",
                    "to_candidates": [target],
                }
            ],
            "rights_status": "Official legal act",
            "source_item": "pravo.gov.ru/legislation-russia:test-pp491",
            "source_system": "pravo.gov.ru/legislation-russia",
            "source_url": "http://ips.pravo.gov.ru/search/test-pp491",
            "temporal_coverage": {
                "status": "temporal_coverage_unknown",
                "valid_from": None,
                "valid_to": None,
            },
            "unresolved_items": [],
        }
        item_id = hashlib.sha256(candidate["source_item"].encode("utf-8")).hexdigest()
        path = data_dir / "items" / f"{item_id}.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
        return path


if __name__ == "__main__":
    unittest.main()
