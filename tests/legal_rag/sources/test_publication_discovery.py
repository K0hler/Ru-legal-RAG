import base64
from contextlib import redirect_stdout
import hashlib
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
    def test_feed_discovers_amendment_invalidates_candidate_and_replays_idempotently(self):
        replay = json.loads(FIXTURE.read_text(encoding="utf-8"))
        responses = self._responses(replay) * 2
        ocr_by_hash = {
            hashlib.sha256(base64.b64decode(document["asset_body_base64"])).hexdigest(): document[
                "ocr_pages"
            ]
            for document in replay["documents"]
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            candidate_path = self._write_pp491_candidate(data_dir)
            outputs = []
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=responses,
            ) as urlopen, patch(
                "legal_rag.sources.discovery._extract_pdf_pages",
                side_effect=lambda path: ocr_by_hash[path.name],
            ):
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
