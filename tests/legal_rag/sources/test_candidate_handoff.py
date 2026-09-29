from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402


class CandidateHandoffTest(unittest.TestCase):
    def test_cli_writes_deterministic_allowlisted_candidate_with_review_gate(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            data_dir = root / "data"
            reconciliation_path, candidate_item_path, evidence = self._write_records(data_dir)

            first = self._run_cli(reconciliation_path, data_dir)
            candidate_path = Path(first["candidate"])
            first_bytes = candidate_path.read_bytes()
            second = self._run_cli(reconciliation_path, data_dir)

            self.assertEqual(first["result"], "new")
            self.assertEqual(second["result"], "unchanged")
            self.assertEqual(first["candidate_id"], second["candidate_id"])
            self.assertEqual(candidate_path.read_bytes(), first_bytes)

            candidate = json.loads(first_bytes)
            self.assertEqual(candidate["schema_version"], "edition-candidate/1")
            self.assertEqual(candidate["review_status"], "unreviewed")
            self.assertIsNone(candidate["review_decision"])
            self.assertEqual(
                candidate["act_identity_claim"]["declared_identity"],
                "Test Act",
            )
            self.assertEqual(
                candidate["edition_claim"]["claimed_edition_date"],
                "2026-09-01",
            )
            self.assertEqual(
                candidate["temporal_evidence"]["status"],
                "temporal_coverage_unknown",
            )
            self.assertEqual(len(candidate["unresolved_items"]), 2)
            self.assertEqual(
                {asset["sha256"] for asset in candidate["source_evidence"]["assets"]},
                set(evidence["asset_sha256s"]),
            )
            self.assertEqual(
                set(candidate["act_identity_claim"]["source_relation_ids"]),
                {evidence["consolidates_relation_id"]},
            )

            forbidden_fields = {
                "adapter_version",
                "baseid",
                "nd",
                "rdk",
                "source_asset_role",
                "transport_metadata",
            }
            self.assertTrue(forbidden_fields.isdisjoint(self._all_keys(candidate)))

            source_item = json.loads(candidate_item_path.read_text(encoding="utf-8"))
            source_item.update(
                {
                    "baseid": "should-not-leak",
                    "review_status": "reviewed",
                    "transport_metadata": {"endpoint": "/private"},
                }
            )
            candidate_item_path.write_text(
                json.dumps(source_item, ensure_ascii=False),
                encoding="utf-8",
            )
            ignored_fields = self._run_cli(reconciliation_path, data_dir)
            self.assertEqual(ignored_fields["candidate_id"], first["candidate_id"])

            invalid_decision_path = root / "invalid-review.json"
            invalid_decision_path.write_text(
                json.dumps({"decision": "reviewed"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "reviewer_role"):
                self._run_cli(reconciliation_path, data_dir, invalid_decision_path)

            review_decision_path = root / "review.json"
            review_decision_path.write_text(
                json.dumps(
                    {
                        "decided_at": "2026-09-29T08:00:00Z",
                        "decision": "reviewed",
                        "evidence_references": [
                            {
                                "source_asset_sha256": evidence["card_sha256"],
                                "source_relation_id": evidence["consolidates_relation_id"],
                            }
                        ],
                        "rationale": "Identity and snapshot evidence checked.",
                        "reviewed_scope": evidence["candidate_source_item"],
                        "reviewer_id": "reviewer-1",
                        "reviewer_role": "Legal Reviewer",
                    }
                ),
                encoding="utf-8",
            )
            reviewed = self._run_cli(
                reconciliation_path,
                data_dir,
                review_decision_path,
            )
            reviewed_candidate = json.loads(
                Path(reviewed["candidate"]).read_text(encoding="utf-8")
            )
            self.assertEqual(reviewed_candidate["review_status"], "reviewed")
            self.assertEqual(
                reviewed_candidate["review_decision"]["reviewer_id"],
                "reviewer-1",
            )

    def _run_cli(
        self,
        reconciliation_path: Path,
        data_dir: Path,
        review_decision_path: Path | None = None,
    ) -> dict[str, object]:
        arguments = [
            "build-candidate",
            "--reconciliation",
            str(reconciliation_path),
            "--data-dir",
            str(data_dir),
        ]
        if review_decision_path is not None:
            arguments.extend(["--review-decision", str(review_decision_path)])
        stdout = StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(main(arguments), 0)
        return json.loads(stdout.getvalue())

    def _write_records(self, data_dir: Path) -> tuple[Path, Path, dict[str, object]]:
        card_sha256 = self._write_asset(data_dir, b'{"edition":"2026-09-01"}')
        text_sha256 = self._write_asset(data_dir, b'{"text":"candidate"}')
        publication_sha256 = self._write_asset(data_dir, b"%PDF-test-publication")
        act_source_item = "declared-act:test"
        candidate_source_item = "ips.pravo.gov.ru:test-hash"
        publication_source_item = "publication.pravo.gov.ru:0000000000000000"

        items = [
            {
                "declared_act_identity": "Test Act",
                "external_id": "test",
                "item_kind": "act",
                "label": "Test Act",
                "source_item": act_source_item,
                "source_system": "declared-act",
            },
            {
                "adapter_version": "connector-private/1",
                "asset_sha256s": [text_sha256, card_sha256],
                "captured_at": "2026-09-29T07:00:00Z",
                "declared_act_identity": "Test Act",
                "declared_edition_label": "Edition 01.09.2026",
                "edition_claim": {
                    "claimed_edition_date": "2026-09-01",
                    "claimed_edition_label": "Edition 01.09.2026",
                    "source_asset_sha256": card_sha256,
                },
                "external_id": "test-hash",
                "item_kind": "edition_candidate",
                "label": "Test edition candidate",
                "latest_successful_asset": text_sha256,
                "rights_status": "Pilot use only",
                "source_item": candidate_source_item,
                "source_system": "ips.pravo.gov.ru",
                "source_url": "http://ips.pravo.gov.ru/search/test-hash",
                "supporting_assets": {"legislation_card": card_sha256},
                "temporal_coverage": {
                    "status": "temporal_coverage_unknown",
                    "valid_from": None,
                    "valid_to": None,
                },
                "unresolved_items": [
                    {
                        "diagnostic_message": "Effective dates were not verified.",
                        "reason": "temporal_coverage_unknown",
                        "source_asset_sha256": card_sha256,
                    }
                ],
            },
            {
                "asset_sha256s": [publication_sha256],
                "captured_at": "2026-09-29T07:00:00Z",
                "declared_act_identity": "Test Act",
                "external_id": "0000000000000000",
                "item_kind": "publication",
                "label": "Official publication",
                "latest_successful_asset": publication_sha256,
                "source_item": publication_source_item,
                "source_system": "publication.pravo.gov.ru",
                "source_url": "http://publication.pravo.gov.ru/document/0000000000000000",
            },
        ]
        item_paths = {}
        for item in items:
            item_path = data_dir / "items" / f"{self._stable_id(item['source_item'])}.json"
            self._write_json(item_path, item)
            item_paths[item["source_item"]] = item_path

        consolidates_relation_id = "relation-consolidates"
        relations = [
            {
                "asserted_by": "ips.pravo.gov.ru",
                "evidence_reference": {
                    "locator": "$.hash; $.nd; $.adoption",
                    "source_asset_role": "legislation_card",
                    "source_asset_sha256": card_sha256,
                    "source_url": "http://ips.pravo.gov.ru/search/test-hash",
                },
                "from_source_item": candidate_source_item,
                "relation_id": consolidates_relation_id,
                "relation_type": "consolidates",
                "review_state": "source_claim",
                "to_source_item": act_source_item,
            },
            {
                "asserted_by": "publication.pravo.gov.ru",
                "evidence_reference": {
                    "locator": "$.eoNumber",
                    "source_asset_sha256": publication_sha256,
                    "source_url": "http://publication.pravo.gov.ru/document/0000000000000000",
                },
                "from_source_item": publication_source_item,
                "relation_id": "relation-publishes",
                "relation_type": "publishes",
                "review_state": "source_claim",
                "to_source_item": act_source_item,
            },
        ]
        for relation in relations:
            self._write_json(
                data_dir / "relations" / f"{relation['relation_id']}.json",
                relation,
            )

        exception = {
            "diagnostic_message": "One amendment target is unresolved.",
            "exception_id": "exception-amendment",
            "reason": "missing_relation_target",
            "relation_type": "amends",
            "source_item": publication_source_item,
        }
        self._write_json(
            data_dir / "exceptions" / f"{exception['exception_id']}.json",
            exception,
        )
        reconciliation = {
            "act_source_item": act_source_item,
            "captured_at": "2026-09-29T07:00:00Z",
            "exception_ids": [exception["exception_id"]],
            "item_source_ids": [item["source_item"] for item in reversed(items)],
            "provenance": {"fixture": "candidate handoff"},
            "reconciliation_id": "reconciliation-test",
            "relation_ids": [relation["relation_id"] for relation in reversed(relations)],
        }
        reconciliation_path = data_dir / "reconciliations" / "reconciliation-test.json"
        self._write_json(reconciliation_path, reconciliation)
        return (
            reconciliation_path,
            item_paths[candidate_source_item],
            {
                "asset_sha256s": [card_sha256, publication_sha256, text_sha256],
                "candidate_source_item": candidate_source_item,
                "card_sha256": card_sha256,
                "consolidates_relation_id": consolidates_relation_id,
            },
        )

    def _write_asset(self, data_dir: Path, payload: bytes) -> str:
        sha256 = hashlib.sha256(payload).hexdigest()
        raw_path = data_dir / "raw" / sha256
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(payload)
        self._write_json(
            data_dir / "assets" / f"{sha256}.json",
            {
                "archive_key": f"raw/{sha256}",
                "byte_length": len(payload),
                "captured_at": "2026-09-29T07:00:00Z",
                "media_type": "application/json",
                "rights_status": "Pilot use only",
                "sha256": sha256,
                "source_url": "http://example.invalid/evidence",
                "transport_metadata": {"connector_private": True},
            },
        )
        return sha256

    @staticmethod
    def _write_json(path: Path, value: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _stable_id(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @classmethod
    def _all_keys(cls, value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {
                key
                for child in value.values()
                for key in cls._all_keys(child)
            }
        if isinstance(value, list):
            return {key for child in value for key in cls._all_keys(child)}
        return set()


if __name__ == "__main__":
    unittest.main()
