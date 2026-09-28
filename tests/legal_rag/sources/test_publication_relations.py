import base64
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
FIXTURE = Path(__file__).with_name("fixtures") / "pp354_publication_relations.json"
REPLAY = Path(__file__).with_name("fixtures") / "publication_pravo_0001202511280030.json"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402
from legal_rag.sources.acquisition import acquire_publication  # noqa: E402
from legal_rag.sources.publication_pravo import PublicationPravoConnector  # noqa: E402
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


class PublicationRelationsTest(unittest.TestCase):
    def test_cli_persists_relation_chain_exceptions_and_idempotent_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            self._acquire_publication(data_dir)
            outputs = []
            exit_codes = []
            snapshots = []

            for _ in range(2):
                stdout = StringIO()
                with redirect_stdout(stdout):
                    exit_codes.append(
                        main(
                            [
                                "reconcile-relations",
                                "--claims",
                                str(FIXTURE),
                                "--data-dir",
                                str(data_dir),
                            ]
                        )
                    )
                outputs.append(json.loads(stdout.getvalue()))
                snapshots.append(
                    {
                        str(path.relative_to(data_dir)): path.read_bytes()
                        for path in data_dir.rglob("*")
                        if path.is_file()
                    }
                )

            self.assertEqual(exit_codes, [0, 0])
            self.assertEqual([output["result"] for output in outputs], ["new", "unchanged"])
            self.assertEqual(snapshots[0], snapshots[1])

            items = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (data_dir / "items").glob("*.json")
            ]
            self.assertEqual(
                {item["source_item"] for item in items},
                {
                    "declared-act:government-decree:2011-05-06:354",
                    "official-print:sobranie-zakonodatelstva-rf:2011:22:3168",
                    "declared-act:government-decree:2025-11-25:1871",
                    "publication.pravo.gov.ru:0001202511280030",
                },
            )
            self.assertEqual(
                {item["source_item"]: item["item_kind"] for item in items},
                {
                    "declared-act:government-decree:2011-05-06:354": "act",
                    "official-print:sobranie-zakonodatelstva-rf:2011:22:3168": "publication",
                    "declared-act:government-decree:2025-11-25:1871": "amendment",
                    "publication.pravo.gov.ru:0001202511280030": "publication",
                },
            )

            relations = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in (data_dir / "relations").glob("*.json")
            ]
            self.assertEqual(
                {
                    (
                        relation["from_source_item"],
                        relation["relation_type"],
                        relation["to_source_item"],
                    )
                    for relation in relations
                },
                {
                    (
                        "official-print:sobranie-zakonodatelstva-rf:2011:22:3168",
                        "publishes",
                        "declared-act:government-decree:2011-05-06:354",
                    ),
                    (
                        "publication.pravo.gov.ru:0001202511280030",
                        "publishes",
                        "declared-act:government-decree:2025-11-25:1871",
                    ),
                    (
                        "declared-act:government-decree:2025-11-25:1871",
                        "amends",
                        "declared-act:government-decree:2011-05-06:354",
                    ),
                },
            )
            self.assertTrue(
                all(
                    relation["review_state"] == "source_claim"
                    and relation["asserted_by"]
                    and relation["evidence_reference"]["source_url"].startswith("http://")
                    for relation in relations
                )
            )
            self.assertEqual(
                {
                    relation["evidence_reference"]["locator"]
                    for relation in relations
                },
                {
                    "citation: Собрание законодательства Российской Федерации, 2011, № 22, ст. 3168",
                    "$.eoNumber; $.complexName",
                    "$.name",
                },
            )
            acquired_relations = [
                relation
                for relation in relations
                if relation["asserted_by"] == "publication.pravo.gov.ru"
            ]
            self.assertTrue(
                all(
                    (data_dir / "raw" / relation["evidence_reference"]["source_asset_sha256"]).is_file()
                    for relation in acquired_relations
                )
            )
            self.assertFalse((data_dir / "relation-items").exists())

            exceptions = list((data_dir / "exceptions").glob("*.json"))
            self.assertEqual(len(exceptions), 1)
            exception = json.loads(exceptions[0].read_text(encoding="utf-8"))
            self.assertEqual(exception["reason"], "missing_relation_target")
            self.assertEqual(exception["relation_type"], "attachment")
            self.assertEqual(exception["candidate_source_items"], [])

            report = Path(outputs[0]["report"]).read_text(encoding="utf-8")
            self.assertIn("Постановление Правительства Российской Федерации от 06.05.2011 № 354", report)
            self.assertIn("`publishes`", report)
            self.assertIn("`amends`", report)
            self.assertIn("Unresolved gaps", report)
            self.assertIn("missing_relation_target", report)

    def test_ambiguous_target_becomes_exception_without_relation(self):
        claims = {
            "act_source_item": "act:a",
            "captured_at": "2026-09-28T03:19:57Z",
            "items": [
                {
                    "external_id": "a",
                    "item_kind": "act",
                    "label": "Act A",
                    "source_item": "act:a",
                    "source_system": "act",
                },
                {
                    "external_id": "b",
                    "item_kind": "act",
                    "label": "Act B",
                    "source_item": "act:b",
                    "source_system": "act",
                },
                {
                    "external_id": "c",
                    "item_kind": "amendment",
                    "label": "Ambiguous amendment",
                    "source_item": "amendment:c",
                    "source_system": "amendment",
                },
            ],
            "provenance": {},
            "relation_claims": [
                {
                    "asserted_by": "test-source",
                    "evidence_reference": {
                        "locator": "ambiguous title",
                        "source_url": "https://example.invalid/claim",
                    },
                    "from_source_item": "amendment:c",
                    "relation_type": "amends",
                    "to_candidates": ["act:a", "act:b"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            claims_path = Path(temporary_directory) / "claims.json"
            claims_path.write_text(json.dumps(claims), encoding="utf-8")
            result = reconcile_publication_relations(
                claims_path,
                Path(temporary_directory) / "data",
            )

            self.assertEqual(result["relation_count"], 0)
            self.assertEqual(result["exception_count"], 1)
            exception_path = next(
                (Path(temporary_directory) / "data" / "exceptions").glob("*.json")
            )
            exception = json.loads(exception_path.read_text(encoding="utf-8"))
            self.assertEqual(exception["reason"], "ambiguous_relation_target")
            self.assertEqual(exception["candidate_source_items"], ["act:a", "act:b"])
            self.assertFalse((Path(temporary_directory) / "data" / "relations").exists())

    def test_missing_acquired_source_item_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "data"
            with self.assertRaisesRegex(ValueError, "acquired source item not found"):
                reconcile_publication_relations(FIXTURE, data_dir)

            self.assertFalse(data_dir.exists())

    def test_invalid_evidence_is_rejected_before_any_output(self):
        original = json.loads(FIXTURE.read_text(encoding="utf-8"))
        mutations = (
            lambda claim: claim.update(asserted_by=""),
            lambda claim: claim.update(evidence_reference={}),
        )

        for mutate in mutations:
            with self.subTest(mutation=mutate):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    data_dir = root / "data"
                    self._acquire_publication(data_dir)
                    before = {
                        str(path.relative_to(data_dir)): path.read_bytes()
                        for path in data_dir.rglob("*")
                        if path.is_file()
                    }
                    claims = json.loads(json.dumps(original))
                    mutate(claims["relation_claims"][0])
                    claims_path = root / "claims.json"
                    claims_path.write_text(json.dumps(claims), encoding="utf-8")

                    with self.assertRaises(ValueError):
                        reconcile_publication_relations(claims_path, data_dir)

                    after = {
                        str(path.relative_to(data_dir)): path.read_bytes()
                        for path in data_dir.rglob("*")
                        if path.is_file()
                    }
                    self.assertEqual(after, before)

    def test_acquired_relation_evidence_asset_is_verified_before_output(self):
        for corruption in ("missing_raw", "mismatched_pointer", "corrupt_raw"):
            with self.subTest(corruption=corruption):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    data_dir = Path(temporary_directory) / "data"
                    self._acquire_publication(data_dir)
                    item_path = next((data_dir / "items").glob("*.json"))
                    item = json.loads(item_path.read_text(encoding="utf-8"))
                    evidence_sha256 = item["declared_publication_asset"]
                    raw_path = data_dir / "raw" / evidence_sha256

                    if corruption == "missing_raw":
                        raw_path.unlink()
                    elif corruption == "mismatched_pointer":
                        for claim in item["relation_claims"]:
                            claim["evidence_reference"]["source_asset_sha256"] = "0" * 64
                        item_path.write_text(json.dumps(item), encoding="utf-8")
                    else:
                        raw_path.write_bytes(b"corrupt")

                    before = {
                        str(path.relative_to(data_dir)): path.read_bytes()
                        for path in data_dir.rglob("*")
                        if path.is_file()
                    }
                    with self.assertRaisesRegex(ValueError, "evidence asset"):
                        reconcile_publication_relations(FIXTURE, data_dir)
                    after = {
                        str(path.relative_to(data_dir)): path.read_bytes()
                        for path in data_dir.rglob("*")
                        if path.is_file()
                    }
                    self.assertEqual(after, before)

    def _acquire_publication(self, data_dir: Path) -> None:
        replay = json.loads(REPLAY.read_text(encoding="utf-8"))
        card_url = replay["provenance"]["card_url"]
        asset_url = replay["provenance"]["asset_url"]
        responses = [
            ReplayResponse(
                json.dumps(replay["card"], ensure_ascii=False).encode("utf-8"),
                card_url,
                replay["card_headers"],
            ),
            ReplayResponse(
                base64.b64decode(replay["asset"]["body_base64"]),
                asset_url,
                replay["asset"]["headers"],
            ),
        ]
        with patch(
            "legal_rag.sources.publication_pravo.urlopen",
            side_effect=responses,
        ):
            result = acquire_publication(
                PublicationPravoConnector(timeout=1),
                replay["card"]["eoNumber"],
                data_dir,
            )
        self.assertEqual(result["result"], "new")


if __name__ == "__main__":
    unittest.main()
