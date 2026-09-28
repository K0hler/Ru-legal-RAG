from contextlib import redirect_stderr, redirect_stdout
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
    def test_acquisition_archives_card_and_selected_edition_without_inventing_coverage(
        self,
    ):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw_responses = {
            name: json.dumps(
                fixture[name],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            for name in ("card", "documenttext")
        }
        self.assertEqual(
            {
                name: hashlib.sha256(body).hexdigest()
                for name, body in raw_responses.items()
            },
            fixture["expected_sha256"],
        )
        document_hash = fixture["document_hash"]
        api_base = "http://ips.pravo.gov.ru/api/ips/legislation"
        urls = (
            f"{api_base}/document_card.json?hash={document_hash}",
            (f"{api_base}/documenttext?nd=1000000000102147807&rdk=60&bpa=c000000000"),
        )
        responses = [
            ReplayResponse(raw_responses[name], url, fixture["headers"])
            for _ in range(2)
            for name, url in zip(("card", "documenttext"), urls)
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
                    results.append(
                        acquire_legislation(
                            LegislationRussiaConnector(timeout=0.01),
                            document_hash,
                            data_dir,
                        )
                    )

            self.assertEqual(
                [result["result"] for result in results], ["new", "unchanged"]
            )
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 2)
            for name, body in raw_responses.items():
                sha256 = fixture["expected_sha256"][name]
                self.assertEqual((data_dir / "raw" / sha256).read_bytes(), body)

            item = json.loads(
                next((data_dir / "items").glob("*.json")).read_text("utf-8")
            )
            candidate_source_item = "pravo.gov.ru/legislation-russia:" + document_hash
            act_source_item = "declared-act:government-decree:2011-05-06:354"
            self.assertEqual(item["source_item"], candidate_source_item)
            self.assertEqual(item["item_kind"], "edition_candidate")
            edition_label = (
                "на 27.07.2026, (№ 931 от 24.07.2026), актуальная, "
                "есть изменения, не вступившие в силу"
            )
            self.assertEqual(item["declared_edition_label"], edition_label)
            self.assertEqual(
                item["edition_claim"],
                {
                    "claimed_edition_date": "2026-07-27",
                    "claimed_edition_label": edition_label,
                    "source_asset_sha256": fixture["expected_sha256"]["card"],
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
                {"temporal_coverage_unknown"},
            )
            self.assertEqual(
                item["supporting_assets"],
                {
                    "legislation_card": fixture["expected_sha256"]["card"],
                    "legislation_text": fixture["expected_sha256"]["documenttext"],
                },
            )
            self.assertEqual(
                item["latest_successful_asset"],
                fixture["expected_sha256"]["documenttext"],
            )
            self.assertEqual(
                item["relation_claims"][0]["evidence_reference"],
                {
                    "locator": "$.hash; $.nd; $.adoption",
                    "source_asset_role": "legislation_card",
                    "source_asset_sha256": fixture["expected_sha256"]["card"],
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

    def test_card_identity_mismatch_does_not_create_a_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        card = {**fixture["card"], "hash": "0" * 64}
        body = json.dumps(card, ensure_ascii=False, separators=(",", ":")).encode()

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                return_value=ReplayResponse(
                    body,
                    fixture["provenance"]["source_url"],
                    fixture["headers"],
                ),
            ):
                result = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_hash"],
                    data_dir,
                )

            report = json.loads(Path(result["report"]).read_text("utf-8"))
            self.assertEqual(result["result"], "failed")
            self.assertEqual(report["errors"][0]["reason"], "invalid_card")
            self.assertFalse((data_dir / "raw").exists())

    def test_documenttext_edition_mismatch_does_not_create_a_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        card_body = json.dumps(
            fixture["card"], ensure_ascii=False, separators=(",", ":")
        ).encode()
        documenttext = {**fixture["documenttext"], "rdk": 59}
        text_body = json.dumps(
            documenttext, ensure_ascii=False, separators=(",", ":")
        ).encode()

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                side_effect=[
                    ReplayResponse(
                        card_body,
                        fixture["provenance"]["source_url"],
                        fixture["headers"],
                    ),
                    ReplayResponse(
                        text_body,
                        fixture["provenance"]["source_url"],
                        fixture["headers"],
                    ),
                ],
            ):
                result = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_hash"],
                    data_dir,
                )

            report = json.loads(Path(result["report"]).read_text("utf-8"))
            self.assertEqual(result["result"], "failed")
            self.assertEqual(report["errors"][0]["reason"], "invalid_text")
            self.assertFalse((data_dir / "raw").exists())

    def test_cli_accepts_the_public_document_hash(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        bodies = [
            json.dumps(
                fixture[name], ensure_ascii=False, separators=(",", ":")
            ).encode()
            for name in ("card", "documenttext")
        ]
        responses = [
            ReplayResponse(
                body,
                fixture["provenance"]["source_url"],
                fixture["headers"],
            )
            for body in bodies
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            stdout = StringIO()
            stderr = StringIO()
            with (
                patch(
                    "legal_rag.sources.legislation_russia.urlopen",
                    side_effect=responses,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                try:
                    exit_code = main(
                        [
                            "acquire-legislation",
                            "--document-hash",
                            fixture["document_hash"],
                            "--data-dir",
                            temporary_directory,
                        ]
                    )
                except SystemExit as error:
                    exit_code = error.code

            self.assertEqual(exit_code, 0, stderr.getvalue())
            self.assertEqual(json.loads(stdout.getvalue())["result"], "new")

    def test_timeout_after_success_preserves_the_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        bodies = [
            json.dumps(
                fixture[name], ensure_ascii=False, separators=(",", ":")
            ).encode()
            for name in ("card", "documenttext")
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                side_effect=[
                    ReplayResponse(
                        bodies[0],
                        fixture["provenance"]["source_url"],
                        fixture["headers"],
                    ),
                    ReplayResponse(
                        bodies[1],
                        fixture["provenance"]["source_url"],
                        fixture["headers"],
                    ),
                    TimeoutError("timed out"),
                ],
            ):
                first = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_hash"],
                    data_dir,
                )
                self.assertEqual(first["result"], "new")
                item_path = next((data_dir / "items").glob("*.json"))
                successful_item = item_path.read_bytes()
                failed = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_hash"],
                    data_dir,
                )

            self.assertEqual(failed["result"], "failed")
            self.assertEqual(item_path.read_bytes(), successful_item)
            report = json.loads(Path(failed["report"]).read_text("utf-8"))
            self.assertEqual(report["errors"][0]["reason"], "timeout")
            self.assertTrue(report["errors"][0]["retryable"])

    def test_card_without_the_selected_edition_does_not_create_a_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        card = {**fixture["card"], "actualrdk": 61}
        body = json.dumps(card, ensure_ascii=False, separators=(",", ":")).encode()

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.legislation_russia.urlopen",
                return_value=ReplayResponse(
                    body,
                    fixture["provenance"]["source_url"],
                    fixture["headers"],
                ),
            ):
                result = acquire_legislation(
                    LegislationRussiaConnector(timeout=0.01),
                    fixture["document_hash"],
                    data_dir,
                )

            report = json.loads(Path(result["report"]).read_text("utf-8"))
            self.assertEqual(result["result"], "failed")
            self.assertEqual(report["errors"][0]["reason"], "invalid_card")
            self.assertFalse((data_dir / "raw").exists())

    def test_incomplete_response_does_not_create_a_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        body = json.dumps(
            fixture["card"], ensure_ascii=False, separators=(",", ":")
        ).encode()
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
                    fixture["document_hash"],
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
        document_hash = fixture["document_hash"]
        source_url = (
            "http://ips.pravo.gov.ru/api/ips/legislation/document_card.json?hash="
            + document_hash
        )
        redirect_url = source_url.replace("http://", "https://")

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
            ("invalid", "not-a-document", [], "invalid_external_id", False),
            ("unsupported", "0" * 64, [], "unsupported_document", False),
            (
                "network",
                document_hash,
                URLError("connection refused"),
                "network_error",
                True,
            ),
            (
                "not_found",
                document_hash,
                HTTPError(source_url, 404, "Not Found", None, None),
                "http_error",
                False,
            ),
            (
                "unavailable",
                document_hash,
                HTTPError(source_url, 503, "Unavailable", None, None),
                "http_error",
                True,
            ),
            (
                "redirect",
                document_hash,
                redirecting_response,
                "blocked_redirect",
                False,
            ),
        )

        for case, requested_hash, side_effect, reason, retryable in cases:
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
                        requested_hash,
                        data_dir,
                    )

                report = json.loads(Path(result["report"]).read_text("utf-8"))
                self.assertEqual(result["result"], "failed")
                self.assertEqual(report["errors"][0]["reason"], reason)
                self.assertEqual(report["errors"][0]["retryable"], retryable)
                self.assertFalse((data_dir / "raw").exists())
                self.assertFalse((data_dir / "items").exists())
                if case in {"invalid", "unsupported"}:
                    mocked_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
