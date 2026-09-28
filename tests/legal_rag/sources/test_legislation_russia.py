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
FIXTURE = Path(__file__).with_name("fixtures") / "legislation_russia_pp354.json"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402
from legal_rag.sources import legislation_russia  # noqa: E402
from legal_rag.sources.acquisition import acquire_legislation  # noqa: E402
from legal_rag.sources.legislation_russia import LegislationRussiaConnector  # noqa: E402
from legal_rag.sources.relations import reconcile_publication_relations  # noqa: E402


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


class LegislationRussiaTest(unittest.TestCase):
    def test_cli_archives_and_reconciles_pp354_without_inventing_edition_coverage(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        body = fixture["body"].encode("windows-1251")
        self.assertEqual(hashlib.sha256(body).hexdigest(), fixture["expected_sha256"])
        responses = [
            ReplayResponse(
                body, fixture["provenance"]["source_url"], fixture["headers"]
            ),
            ReplayResponse(
                body, fixture["provenance"]["source_url"], fixture["headers"]
            ),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_dir = root / "data"
            results = []
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                side_effect=responses,
            ):
                for _ in range(2):
                    stdout = StringIO()
                    with redirect_stdout(stdout):
                        exit_code = main(
                            [
                                "acquire-legislation",
                                "--document-id",
                                fixture["document_id"],
                                "--data-dir",
                                str(data_dir),
                            ]
                        )
                    self.assertEqual(exit_code, 0)
                    results.append(json.loads(stdout.getvalue()))

            self.assertEqual(
                [result["result"] for result in results], ["new", "unchanged"]
            )
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 1)
            self.assertEqual(
                (data_dir / "raw" / fixture["expected_sha256"]).read_bytes(),
                body,
            )

            item = json.loads(
                next((data_dir / "items").glob("*.json")).read_text("utf-8")
            )
            candidate_source_item = (
                "pravo.gov.ru/legislation-russia:" + fixture["document_id"]
            )
            act_source_item = "declared-act:government-decree:2011-05-06:354"
            self.assertEqual(item["source_item"], candidate_source_item)
            self.assertEqual(item["item_kind"], "edition_candidate")
            self.assertIsNone(item["declared_edition_label"])
            self.assertEqual(
                item["edition_claim"],
                {
                    "claimed_edition_date": None,
                    "claimed_edition_label": None,
                    "source_asset_sha256": fixture["expected_sha256"],
                },
            )
            self.assertEqual(
                item["temporal_coverage"],
                {
                    "status": "temporal_coverage_unknown",
                    "valid_from": None,
                    "valid_to": None,
                },
            )
            self.assertEqual(
                {unresolved["reason"] for unresolved in item["unresolved_items"]},
                {"edition_metadata_absent", "temporal_coverage_unknown"},
            )
            self.assertEqual(
                item["supporting_assets"],
                {"legislation_document": fixture["expected_sha256"]},
            )
            self.assertEqual(
                item["relation_claims"][0]["evidence_reference"],
                {
                    "locator": "document title; government decree heading",
                    "source_asset_role": "legislation_document",
                    "source_asset_sha256": fixture["expected_sha256"],
                    "source_url": fixture["provenance"]["source_url"],
                },
            )
            self.assertEqual(
                item["relation_claims"][0]["to_candidates"], [act_source_item]
            )

            claims_path = root / "claims.json"
            claims_path.write_text(
                json.dumps(
                    {
                        "acquired_source_items": [candidate_source_item],
                        "act_source_item": act_source_item,
                        "captured_at": fixture["provenance"]["observed_at"],
                        "items": [],
                        "provenance": fixture["provenance"],
                        "relation_claims": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            reconciliation = reconcile_publication_relations(claims_path, data_dir)

            self.assertEqual(reconciliation["relation_count"], 1)
            relation = json.loads(
                next((data_dir / "relations").glob("*.json")).read_text("utf-8")
            )
            self.assertEqual(relation["from_source_item"], candidate_source_item)
            self.assertEqual(relation["relation_type"], "consolidates")
            self.assertEqual(relation["to_source_item"], act_source_item)

    def test_timeout_after_success_preserves_the_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        body = fixture["body"].encode("windows-1251")
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                side_effect=[
                    ReplayResponse(
                        body,
                        fixture["provenance"]["source_url"],
                        fixture["headers"],
                    ),
                    TimeoutError("timed out"),
                ],
            ):
                first = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_id"],
                    data_dir,
                )
                item_path = next((data_dir / "items").glob("*.json"))
                successful_item = item_path.read_bytes()
                failed = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_id"],
                    data_dir,
                )

            self.assertEqual(first["result"], "new")
            self.assertEqual(failed["result"], "failed")
            self.assertEqual(item_path.read_bytes(), successful_item)
            report = json.loads(Path(failed["report"]).read_text("utf-8"))
            self.assertEqual(report["errors"][0]["reason"], "timeout")
            self.assertTrue(report["errors"][0]["retryable"])

    def test_document_markers_inside_script_do_not_pass_source_validation(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        title = (
            "О предоставлении коммунальных услуг собственникам и пользователям помещений "
            "в многоквартирных домах и жилых домов"
        )
        body = (
            f"<html><head><title>{title}</title></head><body><script>"
            "ПРАВИТЕЛЬСТВО РОССИЙСКОЙ ФЕДЕРАЦИИ ПОСТАНОВЛЕНИЕ "
            f"от 6 мая 2011 г. № 354 {title}</script></body></html>"
        ).encode("windows-1251")

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                return_value=ReplayResponse(
                    body,
                    fixture["provenance"]["source_url"],
                    {**fixture["headers"], "Content-Length": str(len(body))},
                ),
            ):
                result = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_id"],
                    data_dir,
                )

            report = json.loads(Path(result["report"]).read_text("utf-8"))
            self.assertEqual(result["result"], "failed")
            self.assertEqual(report["errors"][0]["reason"], "invalid_document")
            self.assertFalse((data_dir / "raw").exists())

    def test_incomplete_response_does_not_create_a_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        body = fixture["body"].encode("windows-1251")
        headers = {
            **fixture["headers"],
            "Content-Length": str(len(body) + 1),
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                return_value=ReplayResponse(
                    body,
                    fixture["provenance"]["source_url"],
                    headers,
                ),
            ):
                result = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_id"],
                    data_dir,
                )

            report = json.loads(Path(result["report"]).read_text("utf-8"))
            self.assertEqual(result["result"], "failed")
            self.assertEqual(report["errors"][0]["reason"], "incomplete_response")
            self.assertFalse((data_dir / "raw").exists())

    def test_input_and_transport_failures_are_classified_without_successful_assets(
        self,
    ):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        source_url = fixture["provenance"]["source_url"]
        redirect_url = "https://pravo.gov.ru/proxy/ips/?doc_itself=&nd=102147807"

        def redirecting_response(request, timeout):
            return legislation_russia._SameOriginRedirectHandler().redirect_request(
                request,
                None,
                302,
                "Found",
                {"Location": redirect_url},
                redirect_url,
            )

        cases = (
            ("unsupported", "not-a-document", [], "unsupported_document", False),
            (
                "network",
                fixture["document_id"],
                URLError("connection refused"),
                "network_error",
                True,
            ),
            (
                "not_found",
                fixture["document_id"],
                HTTPError(source_url, 404, "Not Found", None, None),
                "http_error",
                False,
            ),
            (
                "unavailable",
                fixture["document_id"],
                HTTPError(source_url, 503, "Unavailable", None, None),
                "http_error",
                True,
            ),
            (
                "redirect",
                fixture["document_id"],
                redirecting_response,
                "blocked_redirect",
                False,
            ),
        )

        for case, document_id, side_effect, reason, retryable in cases:
            with (
                self.subTest(case=case),
                tempfile.TemporaryDirectory() as temporary_directory,
            ):
                data_dir = Path(temporary_directory)
                with patch(
                    "legal_rag.sources.legislation_russia.urlopen",
                    side_effect=side_effect,
                ) as mocked_urlopen:
                    result = acquire_legislation(
                        LegislationRussiaConnector(timeout=0.01),
                        document_id,
                        data_dir,
                    )

                report = json.loads(Path(result["report"]).read_text("utf-8"))
                self.assertEqual(result["result"], "failed")
                self.assertEqual(report["errors"][0]["reason"], reason)
                self.assertEqual(report["errors"][0]["retryable"], retryable)
                self.assertFalse((data_dir / "raw").exists())
                self.assertFalse((data_dir / "items").exists())
                if case == "unsupported":
                    mocked_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
