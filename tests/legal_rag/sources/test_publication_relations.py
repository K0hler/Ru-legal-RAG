from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
FIXTURE = Path(__file__).with_name("fixtures") / "pp354_publication_relations.json"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402
from legal_rag.sources.acquisition import acquire_fixture  # noqa: E402
from legal_rag.sources.relations import reconcile_publication_relations  # noqa: E402


class PublicationRelationsTest(unittest.TestCase):
    def test_cli_persists_relation_chain_exceptions_and_idempotent_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
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
                for path in (data_dir / "relation-items").glob("*.json")
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

    def test_relation_discovery_and_acquisition_do_not_share_item_records(self):
        metadata = {
            "adapter_version": "fixture/1",
            "captured_at": "2026-09-28T03:19:57Z",
            "declared_act_identity": "Постановление Правительства РФ № 1871",
            "declared_edition_label": "as published",
            "external_id": "0001202511280030",
            "media_type": "application/pdf",
            "rights_status": "Official publication replay fixture",
            "source_system": "publication.pravo.gov.ru",
            "source_url": "http://publication.pravo.gov.ru/document/0001202511280030",
        }

        for acquisition_first in (False, True):
            with self.subTest(acquisition_first=acquisition_first):
                with tempfile.TemporaryDirectory() as temporary_directory:
                    root = Path(temporary_directory)
                    data_dir = root / "data"
                    asset_path = root / "publication.pdf"
                    metadata_path = root / "metadata.json"
                    asset_path.write_bytes(b"%PDF-1.4\nfixture\n")
                    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

                    if acquisition_first:
                        acquisition = acquire_fixture(asset_path, metadata_path, data_dir)
                    reconciliation = reconcile_publication_relations(FIXTURE, data_dir)
                    if not acquisition_first:
                        acquisition = acquire_fixture(asset_path, metadata_path, data_dir)

                    self.assertEqual(acquisition["result"], "new")
                    self.assertEqual(reconciliation["relation_count"], 3)
                    acquired_item = json.loads(
                        next((data_dir / "items").glob("*.json")).read_text(encoding="utf-8")
                    )
                    self.assertIn("latest_successful_asset", acquired_item)
                    self.assertEqual(
                        len(list((data_dir / "relation-items").glob("*.json"))),
                        4,
                    )

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
                    claims = json.loads(json.dumps(original))
                    mutate(claims["relation_claims"][0])
                    claims_path = root / "claims.json"
                    claims_path.write_text(json.dumps(claims), encoding="utf-8")
                    data_dir = root / "data"

                    with self.assertRaises(ValueError):
                        reconcile_publication_relations(claims_path, data_dir)

                    self.assertFalse(data_dir.exists())


if __name__ == "__main__":
    unittest.main()
