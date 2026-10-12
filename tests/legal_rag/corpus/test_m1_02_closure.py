import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from legal_rag.corpus.compiler import content_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "docs/assets"))
from validate_m1_02_closure import ACTS, DATES, validate  # noqa: E402


class ClosureTest(unittest.TestCase):
    def prepare(self, root):
        source = root / "source.txt"
        source.write_text("Project-authored source fixture", encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        review = root / "review.json"
        review.write_text(json.dumps({"schema": "m1-02-focused-human-review/2",
            "question": "59-ks19p-after-80", "role": "Legal Reviewer", "decision": "confirmed",
            "targets": sorted(DATES), "edition_admission": False, "packet_hash": "fixture"}), encoding="utf-8")
        permission = root / "permission.json"
        permission.write_text(json.dumps({"schema_version": "processing-permission/1",
            "decision": "allowed", "scope": "diagnostic", "act_identity": "Fixture act",
            "source_asset_sha256s": [digest]}), encoding="utf-8")
        permission_reference = {"path": "permission.json", "sha256": hashlib.sha256(permission.read_bytes()).hexdigest()}
        result = {"schema": "m1-02-route-closure/1", "edition_admission": False,
                  "review_packet_hash": "fixture", "human_decision_path": "review.json",
                  "evidence_files": [{"path": "source.txt", "sha256": digest},
                      permission_reference,
                      {"path": "review.json", "sha256": hashlib.sha256(review.read_bytes()).hexdigest()}],
                  "rows": [{"act_id": act, "target_date": date,
                      "act_identity": "Fixture act",
                      "route": "original_amendments" if act == "sanpin-2.1.3684-21" else
                          "historical_official_candidate" if date == "2025-01-01" else "official_consolidated",
                      "source_sha256s": [digest], "blockers": ["fixture_unreviewed"],
                      "processing_permission": permission_reference,
                      "next_slice": ["M1-13"], "edition_admission": False}
                      for act in sorted(ACTS) for date in sorted(DATES)]}
        self.save(root, result)
        return result

    @staticmethod
    def save(root, result):
        result.pop("content_hash", None)
        result["content_hash"] = content_hash(result)
        (root / "closure.json").write_text(json.dumps(result), encoding="utf-8")

    def test_read_only_replay_and_corrupt_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepare(root)
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            first = validate(root / "closure.json", root)
            self.assertEqual(first, validate(root / "closure.json", root))
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            (root / "source.txt").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "evidence hash mismatch"):
                validate(root / "closure.json", root)

    def test_duplicate_row_admission_and_later_historical_text_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.prepare(root)
            result["rows"][0] = result["rows"][1]
            self.save(root, result)
            with self.assertRaisesRegex(ValueError, "ten distinct"):
                validate(root / "closure.json", root)
            result = self.prepare(root)
            result["edition_admission"] = True
            self.save(root, result)
            with self.assertRaisesRegex(ValueError, "without edition admission"):
                validate(root / "closure.json", root)
            result = self.prepare(root)
            next(row for row in result["rows"] if row["act_id"] == "federal-law-59"
                 and row["target_date"] == "2025-01-01")["route"] = "official_consolidated"
            self.save(root, result)
            with self.assertRaisesRegex(ValueError, "historical input"):
                validate(root / "closure.json", root)

    def test_path_escape_and_wrong_human_scope_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.prepare(root)
            result["evidence_files"][0]["path"] = "../source.txt"
            self.save(root, result)
            with self.assertRaisesRegex(ValueError, "escapes"):
                validate(root / "closure.json", root)
            result = self.prepare(root)
            review = json.loads((root / "review.json").read_text("utf-8"))
            review["role"] = "Engineer"
            (root / "review.json").write_text(json.dumps(review), encoding="utf-8")
            next(entry for entry in result["evidence_files"] if entry["path"] == "review.json")["sha256"] = hashlib.sha256((root / "review.json").read_bytes()).hexdigest()
            self.save(root, result)
            with self.assertRaisesRegex(ValueError, "human decision scope"):
                validate(root / "closure.json", root)

    def test_permission_cannot_authorize_unlisted_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.prepare(root)
            permission = json.loads((root / "permission.json").read_text("utf-8"))
            permission["source_asset_sha256s"] = ["0" * 64]
            (root / "permission.json").write_text(json.dumps(permission), encoding="utf-8")
            digest = hashlib.sha256((root / "permission.json").read_bytes()).hexdigest()
            for entry in result["evidence_files"]:
                if entry["path"] == "permission.json":
                    entry["sha256"] = digest
            for row in result["rows"]:
                row["processing_permission"]["sha256"] = digest
            self.save(root, result)
            with self.assertRaisesRegex(ValueError, "permission scope mismatch"):
                validate(root / "closure.json", root)


if __name__ == "__main__":
    unittest.main()
