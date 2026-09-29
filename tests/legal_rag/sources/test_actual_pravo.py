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
FIXTURE = Path(__file__).with_name("fixtures") / "actual_pravo_59_fz.json"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402
from legal_rag.sources import actual_pravo  # noqa: E402
from legal_rag.sources.acquisition import acquire_actual  # noqa: E402
from legal_rag.sources.actual_pravo import ActualPravoConnector  # noqa: E402
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


class ActualPravoTest(unittest.TestCase):
    def test_housing_code_uses_the_approved_code_identity(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document_hash = (
            "8b4a1920bd1b392ecc9684dc74ddebb02da5af465df06bc4a7ff8c2baf3915ce"
        )
        card = json.loads(json.dumps(fixture["card"]))
        card.update(
            {
                "adoptions": [
                    {
                        "organ": "",
                        "onumber": "188-ФЗ",
                        "odate": "29.12.2004",
                        "region": "Российской Федерации",
                        "type": "Кодекс",
                    }
                ],
                "dochash": document_hash,
                "docid": 80781,
                "docname": "Жилищный кодекс Российской Федерации",
                "docpassing": "Кодекс Российской Федерации от 29.12.2004 № 188-ФЗ",
            }
        )
        redactions = json.loads(json.dumps(fixture["redactions"]))
        redactions.update({"dochash": document_hash, "docid": 80781})
        bodies = [
            json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
            for value in (card, redactions, fixture["redtext"])
        ]
        responses = [
            ReplayResponse(body, "http://actual.pravo.gov.ru/test", fixture["headers"])
            for body in bodies
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.actual_pravo.urlopen",
                side_effect=responses,
            ):
                result = acquire_actual(
                    ActualPravoConnector(timeout=0.01),
                    document_hash,
                    data_dir,
                )

            item = json.loads(next((data_dir / "items").glob("*.json")).read_text("utf-8"))
            self.assertEqual(result["result"], "new")
            self.assertEqual(
                item["relation_claims"][0]["to_candidates"],
                ["declared-act:code:2004-12-29:188-ФЗ"],
            )

    def test_cli_preserves_candidate_evidence_and_links_it_to_publication_chain(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document_hash = fixture["document_hash"]
        raw_responses = {
            name: json.dumps(
                fixture[name],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            for name in ("card", "redactions", "redtext")
        }
        self.assertEqual(
            {name: hashlib.sha256(body).hexdigest() for name, body in raw_responses.items()},
            fixture["expected_sha256"],
        )
        api_base = "http://actual.pravo.gov.ru:8000/api/ebpi"
        urls = (
            f"{api_base}/card/?bpa=ebpi&t=card",
            f"{api_base}/redactions/?bpa=ebpi&t=redactions",
            f"{api_base}/redtext?bpa=ebpi&t=466661&ttl=0",
        )
        responses = [
            ReplayResponse(raw_responses[name], url, fixture["headers"])
            for _ in range(2)
            for name, url in zip(("card", "redactions", "redtext"), urls)
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_dir = root / "data"
            results = []
            with patch(
                "legal_rag.sources.actual_pravo.urlopen",
                side_effect=responses,
            ):
                for _ in range(2):
                    stdout = StringIO()
                    with redirect_stdout(stdout):
                        exit_code = main(
                            [
                                "acquire-actual",
                                "--document-hash",
                                document_hash,
                                "--data-dir",
                                str(data_dir),
                            ]
                        )
                    self.assertEqual(exit_code, 0)
                    results.append(json.loads(stdout.getvalue()))

            self.assertEqual([result["result"] for result in results], ["new", "unchanged"])
            report = json.loads(Path(results[0]["report"]).read_text(encoding="utf-8"))
            self.assertEqual(
                report["metrics"],
                {
                    "bytes_received": sum(map(len, raw_responses.values())),
                    "request_count": 3,
                },
            )
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 3)
            for name, body in raw_responses.items():
                sha256 = fixture["expected_sha256"][name]
                self.assertEqual((data_dir / "raw" / sha256).read_bytes(), body)

            item_path = next((data_dir / "items").glob("*.json"))
            item = json.loads(item_path.read_text(encoding="utf-8"))
            actual_source_item = f"actual.pravo.gov.ru:{document_hash}"
            act_source_item = "declared-act:federal-law:2006-05-02:59-ФЗ"
            self.assertEqual(item["source_item"], actual_source_item)
            self.assertEqual(item["item_kind"], "edition_candidate")
            self.assertEqual(item["declared_edition_label"], "с 30.03.2025, актуальная")
            self.assertEqual(
                item["supporting_assets"],
                {
                    "actual_card": fixture["expected_sha256"]["card"],
                    "declared_editions": fixture["expected_sha256"]["redactions"],
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
                item["unresolved_items"][0]["reason"],
                "temporal_coverage_unknown",
            )
            self.assertEqual(item["latest_successful_asset"], fixture["expected_sha256"]["redtext"])
            self.assertNotIn("api/ebpi", item["source_url"])
            self.assertEqual(item["relation_claims"][0]["to_candidates"], [act_source_item])
            self.assertEqual(
                item["relation_claims"][0]["evidence_reference"]["source_asset_sha256"],
                fixture["expected_sha256"]["card"],
            )

            claims = {
                "acquired_source_items": [actual_source_item],
                "act_source_item": act_source_item,
                "captured_at": fixture["provenance"]["observed_at"],
                "items": [
                    {
                        "declared_act_identity": item["declared_act_identity"],
                        "external_id": "sobranie-zakonodatelstva-rf:2006:19:2060",
                        "item_kind": "publication",
                        "label": "Собрание законодательства Российской Федерации, 2006, № 19, ст. 2060",
                        "source_item": "official-print:sobranie-zakonodatelstva-rf:2006:19:2060",
                        "source_system": "official-print",
                        "source_url": "http://pravo.gov.ru/",
                    }
                ],
                "provenance": fixture["provenance"],
                "relation_claims": [
                    {
                        "asserted_by": "actual.pravo.gov.ru",
                        "evidence_reference": {
                            "locator": "$.card.publications[0]",
                            "source_url": item["source_url"],
                        },
                        "from_source_item": "official-print:sobranie-zakonodatelstva-rf:2006:19:2060",
                        "relation_type": "publishes",
                        "to_candidates": [act_source_item],
                    }
                ],
            }
            claims_path = root / "claims.json"
            claims_path.write_text(json.dumps(claims, ensure_ascii=False), encoding="utf-8")
            reconciliation = reconcile_publication_relations(claims_path, data_dir)

            self.assertEqual(reconciliation["relation_count"], 2)
            self.assertEqual(reconciliation["exception_count"], 0)
            relations = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (data_dir / "relations").glob("*.json")
            ]
            self.assertEqual(
                {
                    (relation["from_source_item"], relation["relation_type"], relation["to_source_item"])
                    for relation in relations
                },
                {
                    (
                        "official-print:sobranie-zakonodatelstva-rf:2006:19:2060",
                        "publishes",
                        act_source_item,
                    ),
                    (actual_source_item, "consolidates", act_source_item),
                },
            )

    def test_reconciliation_rejects_actual_relation_evidence_with_wrong_asset_role(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document_hash = fixture["document_hash"]
        raw_responses = [
            json.dumps(
                fixture[name],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            for name in ("card", "redactions", "redtext")
        ]
        responses = [
            ReplayResponse(body, f"http://actual.pravo.gov.ru/{index}", fixture["headers"])
            for index, body in enumerate(raw_responses)
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_dir = root / "data"
            with patch(
                "legal_rag.sources.actual_pravo.urlopen",
                side_effect=responses,
            ), redirect_stdout(StringIO()):
                main(
                    [
                        "acquire-actual",
                        "--document-hash",
                        document_hash,
                        "--data-dir",
                        str(data_dir),
                    ]
                )

            item_path = next((data_dir / "items").glob("*.json"))
            item = json.loads(item_path.read_text(encoding="utf-8"))
            item["relation_claims"][0]["evidence_reference"][
                "source_asset_sha256"
            ] = item["latest_successful_asset"]
            item_path.write_text(json.dumps(item), encoding="utf-8")
            claims = {
                "acquired_source_items": [item["source_item"]],
                "act_source_item": "declared-act:federal-law:2006-05-02:59-ФЗ",
                "captured_at": fixture["provenance"]["observed_at"],
                "items": [],
                "provenance": fixture["provenance"],
                "relation_claims": [],
            }
            claims_path = root / "claims.json"
            claims_path.write_text(json.dumps(claims), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "evidence asset role mismatch"):
                reconcile_publication_relations(claims_path, data_dir)

            self.assertFalse((data_dir / "relations").exists())
            self.assertFalse((data_dir / "reconciliations").exists())
            self.assertFalse((data_dir / "reports").exists())

    def test_supporting_asset_change_then_failure_preserves_latest_candidate(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document_hash = fixture["document_hash"]
        changed_redactions = json.loads(json.dumps(fixture["redactions"]))
        changed_redactions["serverdate"] = "2026-09-29T00:00:00"

        def encode(value):
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")

        first_bodies = [encode(fixture[name]) for name in ("card", "redactions", "redtext")]
        second_bodies = [
            first_bodies[0],
            encode(changed_redactions),
            first_bodies[2],
        ]
        responses = [
            ReplayResponse(body, f"http://actual.pravo.gov.ru/{index}", fixture["headers"])
            for index, body in enumerate([*first_bodies, *second_bodies])
        ]
        responses.append(TimeoutError("timed out"))

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            results = []
            with patch(
                "legal_rag.sources.actual_pravo.urlopen",
                side_effect=responses,
            ):
                for _ in range(3):
                    results.append(
                        acquire_actual(
                            ActualPravoConnector(timeout=0.01),
                            document_hash,
                            data_dir,
                        )
                    )
                    if len(results) == 2:
                        item_path = next((data_dir / "items").glob("*.json"))
                        item_after_change = item_path.read_bytes()

            self.assertEqual(
                [result["result"] for result in results],
                ["new", "changed", "failed"],
            )
            changed_report = json.loads(Path(results[1]["report"]).read_text("utf-8"))
            old_sha256 = hashlib.sha256(first_bodies[1]).hexdigest()
            new_sha256 = hashlib.sha256(second_bodies[1]).hexdigest()
            self.assertEqual(
                changed_report["change"]["changed_assets"]["declared_editions"],
                {"new_sha256": new_sha256, "old_sha256": old_sha256},
            )
            item = json.loads(item_after_change)
            self.assertEqual(item["latest_successful_asset"], hashlib.sha256(first_bodies[2]).hexdigest())
            self.assertEqual(item["supporting_assets"]["declared_editions"], new_sha256)
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 4)

            failed_report = json.loads(Path(results[2]["report"]).read_text("utf-8"))
            self.assertEqual(failed_report["errors"][0]["reason"], "timeout")
            self.assertTrue(failed_report["errors"][0]["retryable"])
            self.assertIn("/card/?", failed_report["errors"][0]["source_url"])
            exception = json.loads(
                (data_dir / "exceptions" / f"{failed_report['exception_ids'][0]}.json").read_text(
                    "utf-8"
                )
            )
            self.assertEqual(exception["reason"], "timeout")
            self.assertEqual(next((data_dir / "items").glob("*.json")).read_bytes(), item_after_change)

    def test_invalid_actual_inputs_and_transport_fail_without_successful_assets(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        document_hash = fixture["document_hash"]

        def encode(value):
            return json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")

        card_response = ReplayResponse(
            encode(fixture["card"]),
            fixture["provenance"]["source_url"],
            fixture["headers"],
        )
        no_current = json.loads(json.dumps(fixture["redactions"]))
        no_current["redactions"][0]["actual"] = False
        redirect_url = "https://actual.pravo.gov.ru/api/ebpi/card/"

        def redirecting_response(request, timeout):
            return actual_pravo._HttpOnlyRedirectHandler().redirect_request(
                request,
                None,
                302,
                "Found",
                {"Location": redirect_url},
                redirect_url,
            )

        cases = (
            ("invalid_id", "not-a-hash", [], "invalid_external_id", False),
            (
                "unsupported_document",
                "0" * 64,
                [],
                "unsupported_document",
                False,
            ),
            (
                "invalid_json",
                document_hash,
                [ReplayResponse(b"not json", "http://actual.pravo.gov.ru/card", fixture["headers"])],
                "invalid_card",
                False,
            ),
            (
                "invalid_card",
                document_hash,
                [
                    ReplayResponse(
                        encode({**fixture["card"], "docid": True}),
                        "http://actual.pravo.gov.ru/card",
                        fixture["headers"],
                    )
                ],
                "invalid_card",
                False,
            ),
            (
                "no_current_edition",
                document_hash,
                [
                    card_response,
                    ReplayResponse(
                        encode(no_current),
                        "http://actual.pravo.gov.ru/redactions",
                        fixture["headers"],
                    ),
                ],
                "invalid_redactions",
                False,
            ),
            ("timeout", document_hash, TimeoutError("timed out"), "timeout", True),
            (
                "network",
                document_hash,
                URLError("connection refused"),
                "network_error",
                True,
            ),
            (
                "http",
                document_hash,
                HTTPError("http://actual.pravo.gov.ru/card", 503, "Unavailable", None, None),
                "http_error",
                True,
            ),
            ("redirect", document_hash, redirecting_response, "blocked_redirect", False),
        )

        for case, external_id, side_effect, reason, retryable in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary_directory:
                data_dir = Path(temporary_directory)
                with patch(
                    "legal_rag.sources.actual_pravo.urlopen",
                    side_effect=side_effect,
                ) as mocked_urlopen:
                    result = acquire_actual(
                        ActualPravoConnector(timeout=0.01),
                        external_id,
                        data_dir,
                    )

                report = json.loads(Path(result["report"]).read_text("utf-8"))
                self.assertEqual(result["result"], "failed")
                self.assertEqual(report["errors"][0]["reason"], reason)
                self.assertEqual(report["errors"][0]["retryable"], retryable)
                self.assertIn("source_url", report["errors"][0])
                self.assertEqual(len(list((data_dir / "exceptions").glob("*.json"))), 1)
                self.assertFalse((data_dir / "items").exists())
                self.assertFalse((data_dir / "raw").exists())
                if case in {"invalid_id", "unsupported_document"}:
                    mocked_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
