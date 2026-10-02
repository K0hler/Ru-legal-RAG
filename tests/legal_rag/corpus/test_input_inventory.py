import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from legal_rag.corpus.compiler import json_bytes
from legal_rag.sources.pilot import PILOT_ACTS

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "docs/assets"))
from generate_m1_inventory import build_inventory, main, source_document  # noqa: E402


class InputInventoryTest(unittest.TestCase):
    def prepare(self, root):
        archive = root / "archive"
        systems = {"actual": "actual.pravo.gov.ru", "legislation": "pravo.gov.ru/legislation-russia",
                   "publication": "publication.pravo.gov.ru"}
        for act in PILOT_ACTS:
            for spec in act["items"]:
                source = systems[spec["connector"]] + ":" + spec["external_id"]
                payload = source.encode()
                digest = hashlib.sha256(payload).hexdigest()
                self.write(archive / "raw" / digest, payload)
                self.write(archive / "assets" / (digest + ".json"), json_bytes({
                    "sha256": digest, "archive_key": "raw/" + digest, "byte_length": len(payload),
                    "source_url": "https://example.invalid/" + spec["external_id"], "media_type": "text/plain",
                    "captured_at": "2026-10-02T00:00:00Z", "rights_status": "Project-authored test fixture",
                }))
                self.write(archive / "items" / (hashlib.sha256(source.encode()).hexdigest() + ".json"), json_bytes({
                    "source_item": source, "declared_act_identity": act["label"], "asset_sha256s": [digest],
                    "latest_successful_asset": digest, "source_url": "https://example.invalid/" + spec["external_id"],
                }))
        search = {"status": "incomplete", "checks": [{"method": "synthetic_known_id_check"}]}
        self.write(root / "search.json", json_bytes(search))
        return archive, search

    @staticmethod
    def write(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def test_ten_rows_preserve_temporal_permission_and_legal_blockers(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, search = self.prepare(Path(directory))
            inventory = build_inventory(archive, search)
            self.assertEqual(len({row["row_id"] for row in inventory["rows"]}), 10)
            for row in inventory["rows"]:
                self.assertEqual(row["status"], "blocked")
                self.assertIsNone(row["selected_date_basis"])
                self.assertEqual(row["processing_permission"]["status"], "pending")
                if row["act_id"] == "sanpin-2.1.3684-21":
                    self.assertEqual(row["route"], "original_amendments")
                    self.assertEqual(len(row["source_documents"]), 10)
                elif row["target_date"] == "2025-01-01":
                    self.assertEqual(row["route"], "unresolved")
                if row["act_id"] == "federal-law-59":
                    self.assertIn("case_law_sensitive_effect_unresolved", row["blockers"])
                if row["act_id"] == "government-decree-491":
                    self.assertEqual(row["m0_decision"]["status"], "rejected")
                    self.assertEqual(row["missing_source_items"], ["publication.pravo.gov.ru:0001202609260011"])
            for permission in inventory["permission_requests"].values():
                self.assertEqual(permission["decision"], "pending")
                self.assertIsNone(permission["authorized_at"])
                self.assertIsNone(permission["authorized_by"])

    def test_corrupt_or_mispointed_raw_evidence_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, _ = self.prepare(Path(directory))
            item_path = next((archive / "items").glob("*.json"))
            item = json.loads(item_path.read_bytes())
            digest = item["latest_successful_asset"]
            raw = archive / "raw" / digest
            saved = raw.read_bytes()
            raw.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "invalid source asset"):
                source_document(archive, item["source_item"], "original")
            raw.write_bytes(saved)
            metadata_path = archive / "assets" / (digest + ".json")
            metadata = json.loads(metadata_path.read_bytes())
            metadata["source_url"] = "https://example.invalid/wrong"
            metadata_path.write_bytes(json_bytes(metadata))
            with self.assertRaisesRegex(ValueError, "source URL mismatch"):
                source_document(archive, item["source_item"], "original")

    def test_replay_is_read_only_and_never_replaces_a_human_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive, _ = self.prepare(root)
            snapshot = {str(p): p.read_bytes() for p in archive.rglob("*") if p.is_file()}
            output = root / "output"
            args = ["--archive", str(archive), "--search-record", str(root / "search.json"),
                    "--output-dir", str(output)]
            self.assertEqual(main(args), 0)
            expected = {str(p): p.read_bytes() for p in output.rglob("*") if p.is_file()}
            self.assertEqual(main(args), 0)
            self.assertEqual(expected, {str(p): p.read_bytes() for p in output.rglob("*") if p.is_file()})
            self.assertEqual(snapshot, {str(p): p.read_bytes() for p in archive.rglob("*") if p.is_file()})
            permission = output / "permissions/federal-law-59.json"
            permission.write_bytes(b"human decision placeholder")
            with self.assertRaisesRegex(ValueError, "refusing to replace"):
                main(args)
            self.assertEqual(permission.read_bytes(), b"human decision placeholder")
            with self.assertRaisesRegex(ValueError, "separate from the source archive"):
                main([*args[:-1], str(archive / "raw")])

    def test_publication_card_and_pdf_have_distinct_evidence_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, _ = self.prepare(Path(directory))
            source = "publication.pravo.gov.ru:0001202102050027"
            item_path = archive / "items" / (hashlib.sha256(source.encode()).hexdigest() + ".json")
            item = json.loads(item_path.read_bytes())
            metadata_path = archive / "assets" / (item["latest_successful_asset"] + ".json")
            metadata = json.loads(metadata_path.read_bytes())
            payload = b'{"synthetic_publication_card":true}'
            digest = hashlib.sha256(payload).hexdigest()
            self.write(archive / "raw" / digest, payload)
            metadata.update({"sha256": digest, "archive_key": "raw/" + digest,
                             "byte_length": len(payload),
                             "source_url": "http://publication.pravo.gov.ru/api/Document?eoNumber=0001202102050027"})
            self.write(archive / "assets" / (digest + ".json"), json_bytes(metadata))
            item["asset_sha256s"].append(digest)
            item["declared_publication_asset"] = digest
            item["declared_publication"] = {
                "official_publication_url": "http://publication.pravo.gov.ru/document/0001202102050027"}
            self.write(item_path, json_bytes(item))
            document = source_document(archive, source, "original")
            self.assertEqual(document["supporting_assets"]["declared_publication"], digest)
            self.assertEqual(document["source_url"], item["declared_publication"]["official_publication_url"])


if __name__ == "__main__":
    unittest.main()
