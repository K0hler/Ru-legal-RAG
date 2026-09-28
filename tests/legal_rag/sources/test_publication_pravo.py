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
from urllib.error import HTTPError, URLError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
REPLAY_PATH = Path(__file__).with_name("fixtures") / "publication_pravo_0001202511280030.json"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402
from legal_rag.sources.acquisition import acquire_publication  # noqa: E402
from legal_rag.sources.publication_pravo import PublicationPravoConnector  # noqa: E402


class ReplayResponse:
    def __init__(self, body: bytes, url: str, headers: dict[str, str]):
        self._body = body
        self._url = url
        self.headers = headers
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._body


class PublicationPravoTest(unittest.TestCase):
    def setUp(self):
        self.replay = json.loads(REPLAY_PATH.read_text(encoding="utf-8"))
        self.eo_number = self.replay["card"]["eoNumber"]

    def test_cli_replays_document_card_and_original_asset_without_network(self):
        card_url = self.replay["provenance"]["card_url"]
        asset_url = self.replay["provenance"]["asset_url"]
        card_bytes = json.dumps(self.replay["card"], ensure_ascii=False).encode("utf-8")
        asset_bytes = base64.b64decode(self.replay["asset"]["body_base64"])
        responses = [
            ReplayResponse(
                card_bytes,
                card_url,
                self.replay["card_headers"],
            ),
            ReplayResponse(asset_bytes, asset_url, self.replay["asset"]["headers"]),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            output = StringIO()
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=responses,
            ) as urlopen, redirect_stdout(output):
                exit_code = main(
                    [
                        "acquire-publication",
                        "--eo-number",
                        self.eo_number,
                        "--data-dir",
                        temporary_directory,
                        "--timeout",
                        "2.5",
                    ]
                )

            result = json.loads(output.getvalue())
            data_dir = Path(temporary_directory)
            item = json.loads(next((data_dir / "items").glob("*.json")).read_text("utf-8"))
            assets = [
                json.loads(path.read_text("utf-8"))
                for path in (data_dir / "assets").glob("*.json")
            ]
            self.assertEqual(
                {asset["media_type"] for asset in assets},
                {"application/json", "application/pdf"},
            )
            pdf_asset = next(asset for asset in assets if asset["media_type"] == "application/pdf")
            card_asset = next(asset for asset in assets if asset["media_type"] == "application/json")
            requested_urls = [call.args[0].full_url for call in urlopen.call_args_list]

            self.assertEqual(exit_code, 0)
            self.assertEqual(result["result"], "new")
            self.assertEqual(
                result["source_item"],
                f"publication.pravo.gov.ru:{self.eo_number}",
            )
            self.assertEqual(requested_urls, [card_url, asset_url])
            self.assertTrue(all(url.startswith("http://") for url in requested_urls))
            self.assertEqual([call.kwargs["timeout"] for call in urlopen.call_args_list], [2.5, 2.5])
            self.assertEqual(
                item["declared_publication"]["electronic_publication_number"],
                self.eo_number,
            )
            self.assertEqual(item["declared_publication"]["document_number"], "1871")
            self.assertEqual(item["declared_publication"]["publication_date"], "2025-11-28T00:00:00")
            self.assertNotIn("valid_from", item)
            self.assertEqual(pdf_asset["sha256"], self.replay["asset"]["expected_sha256"])
            self.assertEqual(pdf_asset["source_url"], asset_url)
            self.assertEqual(pdf_asset["transport_metadata"]["http_status"], 200)
            self.assertEqual(
                pdf_asset["transport_metadata"]["headers"]["content-type"],
                "application/octet-stream",
            )
            card_hash = hashlib.sha256(card_bytes).hexdigest()
            self.assertEqual(card_asset["sha256"], card_hash)
            self.assertEqual(card_asset["source_url"], card_url)
            self.assertEqual((data_dir / "raw" / card_hash).read_bytes(), card_bytes)
            self.assertEqual(item["declared_publication_asset"], card_hash)
            self.assertIn("discovered_source_items", item)
            self.assertIn("relation_claims", item)
            self.assertEqual(
                item["relation_claims"],
                [
                    {
                        "asserted_by": "publication.pravo.gov.ru",
                        "evidence_reference": {
                            "locator": "$.eoNumber; $.complexName",
                            "source_asset_sha256": card_hash,
                            "source_url": card_url,
                        },
                        "from_source_item": f"publication.pravo.gov.ru:{self.eo_number}",
                        "relation_type": "publishes",
                        "to_candidates": [
                            "declared-act:government-decree:2025-11-25:1871"
                        ],
                    },
                    {
                        "asserted_by": "publication.pravo.gov.ru",
                        "evidence_reference": {
                            "locator": "$.name",
                            "source_asset_sha256": card_hash,
                            "source_url": card_url,
                        },
                        "from_source_item": "declared-act:government-decree:2025-11-25:1871",
                        "relation_type": "amends",
                        "to_candidates": [
                            "declared-act:government-decree:2011-05-06:354"
                        ],
                    },
                ],
            )

    def test_timeout_creates_diagnostic_failed_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=TimeoutError("timed out"),
            ):
                result = acquire_publication(
                    PublicationPravoConnector(timeout=0.01),
                    self.eo_number,
                    Path(temporary_directory),
                )

            self._assert_failed_run(result, Path(temporary_directory), "timeout", True)

    def test_invalid_external_id_creates_nonretryable_failed_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = acquire_publication(
                PublicationPravoConnector(timeout=1),
                "not-an-eo-number",
                Path(temporary_directory),
            )

            self._assert_failed_run(
                result,
                Path(temporary_directory),
                "invalid_external_id",
                False,
            )

    def test_not_found_creates_nonretryable_failed_run(self):
        card_url = self.replay["provenance"]["card_url"]
        error = HTTPError(card_url, 404, "Not Found", None, None)
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=error,
            ):
                result = acquire_publication(
                    PublicationPravoConnector(timeout=1),
                    self.eo_number,
                    Path(temporary_directory),
                )

            self._assert_failed_run(result, Path(temporary_directory), "http_error", False)
            self.assertTrue(error.closed)

    def test_network_error_creates_retryable_failed_run(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=URLError("connection refused"),
            ):
                result = acquire_publication(
                    PublicationPravoConnector(timeout=1),
                    self.eo_number,
                    Path(temporary_directory),
                )

            self._assert_failed_run(
                result,
                Path(temporary_directory),
                "network_error",
                True,
            )

    def test_unparsed_amendment_target_remains_an_unresolved_source_claim(self):
        replay = json.loads(json.dumps(self.replay))
        replay["card"]["name"] = "О внесении изменений в отдельные акты Правительства Российской Федерации"
        replay["card"]["complexName"] = replay["card"]["name"]
        card_url = replay["provenance"]["card_url"]
        responses = [
            ReplayResponse(
                json.dumps(replay["card"], ensure_ascii=False).encode("utf-8"),
                card_url,
                replay["card_headers"],
            ),
            ReplayResponse(
                base64.b64decode(replay["asset"]["body_base64"]),
                replay["provenance"]["asset_url"],
                replay["asset"]["headers"],
            ),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=responses,
            ):
                result = acquire_publication(
                    PublicationPravoConnector(timeout=1),
                    self.eo_number,
                    data_dir,
                )

            item = json.loads(next((data_dir / "items").glob("*.json")).read_text("utf-8"))
            self.assertEqual(result["result"], "new")
            self.assertEqual(item["discovered_source_items"][0]["item_kind"], "amendment")
            self.assertEqual(len(item["relation_claims"]), 2)
            self.assertEqual(
                item["relation_claims"][1],
                {
                    "asserted_by": "publication.pravo.gov.ru",
                    "diagnostic_message": "The publication card declares amendments but does not identify one supported target.",
                    "evidence_reference": {
                        "locator": "$.name",
                        "source_asset_sha256": item["declared_publication_asset"],
                        "source_url": card_url,
                    },
                    "from_source_item": "declared-act:government-decree:2025-11-25:1871",
                    "relation_type": "amends",
                    "to_candidates": [],
                },
            )

    def test_http_error_creates_diagnostic_failed_run(self):
        card_url = self.replay["provenance"]["card_url"]
        error = HTTPError(card_url, 503, "Service Unavailable", None, None)
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=error,
            ):
                result = acquire_publication(
                    PublicationPravoConnector(timeout=1),
                    self.eo_number,
                    Path(temporary_directory),
                )

            self._assert_failed_run(result, Path(temporary_directory), "http_error", True)
            report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
            self.assertEqual(report["errors"][0]["http_status"], 503)
            self.assertIn("source_url", report["errors"][0])
            self.assertEqual(report["errors"][0]["source_url"], card_url)
            self.assertTrue(error.closed)

    def test_invalid_card_creates_failed_run_without_asset(self):
        card_url = self.replay["provenance"]["card_url"]
        response = ReplayResponse(b"not json", card_url, self.replay["card_headers"])
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                return_value=response,
            ):
                result = acquire_publication(
                    PublicationPravoConnector(timeout=1),
                    self.eo_number,
                    Path(temporary_directory),
                )

            self._assert_failed_run(result, Path(temporary_directory), "invalid_card", False)

    def test_invalid_card_field_type_creates_failed_run_without_asset(self):
        replay = json.loads(json.dumps(self.replay))
        replay["card"]["name"] = 123
        responses = [
            ReplayResponse(
                json.dumps(replay["card"], ensure_ascii=False).encode("utf-8"),
                replay["provenance"]["card_url"],
                replay["card_headers"],
            ),
            ReplayResponse(
                base64.b64decode(replay["asset"]["body_base64"]),
                replay["provenance"]["asset_url"],
                replay["asset"]["headers"],
            ),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=responses,
            ):
                try:
                    result = acquire_publication(
                        PublicationPravoConnector(timeout=1),
                        self.eo_number,
                        Path(temporary_directory),
                    )
                except AttributeError as error:
                    self.fail(f"invalid card field escaped source validation: {error}")

            self._assert_failed_run(result, Path(temporary_directory), "invalid_card", False)

    def test_non_pdf_asset_creates_failed_run_without_asset(self):
        card_url = self.replay["provenance"]["card_url"]
        asset_url = self.replay["provenance"]["asset_url"]
        responses = [
            ReplayResponse(
                json.dumps(self.replay["card"], ensure_ascii=False).encode("utf-8"),
                card_url,
                self.replay["card_headers"],
            ),
            ReplayResponse(b"<html>error</html>", asset_url, {"Content-Type": "text/html"}),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch(
                "legal_rag.sources.publication_pravo.urlopen",
                side_effect=responses,
            ):
                result = acquire_publication(
                    PublicationPravoConnector(timeout=1),
                    self.eo_number,
                    Path(temporary_directory),
                )

            self._assert_failed_run(result, Path(temporary_directory), "invalid_asset", False)

    def _assert_failed_run(
        self,
        result: dict[str, str],
        data_dir: Path,
        reason: str,
        retryable: bool,
    ) -> None:
        report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
        self.assertEqual(result["result"], "failed")
        self.assertEqual(report["counts"]["failed"], 1)
        self.assertEqual(report["errors"][0]["stage"], "acquisition")
        self.assertEqual(report["errors"][0]["reason"], reason)
        self.assertEqual(report["errors"][0]["retryable"], retryable)
        self.assertIn("source_url", report["errors"][0])
        exception_paths = list((data_dir / "exceptions").glob("*.json"))
        self.assertEqual(len(exception_paths), 1)
        exception = json.loads(exception_paths[0].read_text(encoding="utf-8"))
        self.assertEqual(report["exception_ids"], [exception["exception_id"]])
        self.assertEqual(exception["reason"], reason)
        self.assertEqual(exception["retryable"], retryable)
        self.assertEqual(exception["source_url"], report["errors"][0]["source_url"])
        self.assertFalse((data_dir / "raw").exists())
        self.assertFalse((data_dir / "items").exists())


if __name__ == "__main__":
    unittest.main()
