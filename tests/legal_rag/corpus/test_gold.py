from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from legal_rag.corpus.gold import QUERY_CLASSES, digest, freeze, main, validate  # noqa: E402


class GoldSetTest(unittest.TestCase):
    def test_review_split_evidence_and_immutable_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = b"Project-authored synthetic evidence."
            (root / "text.txt").write_bytes(content)
            sha = hashlib.sha256(content).hexdigest()
            acts = ["housing-code", "pp-354", "pp-491", "59-fz", "sanpin"]
            classes = sorted(QUERY_CLASSES)
            questions = []
            for i in range(40):
                questions.append({
                    "id": f"q{i}", "query": f"Synthetic question {i}",
                    "leakage_group": f"group{i}", "query_class": classes[i % 6],
                    "task_scope": "source_snapshot", "disputed": False,
                    "expected": {
                        "act": acts[i % 5], "address": f"item {i}",
                        "edition_claim": "synthetic edition", "expected_value": "Synthetic",
                        "outcome": "source_span", "spans": [{
                            "evidence_id": "e", "start": 0, "end": len(content),
                            "quote": content.decode(),
                        }],
                    },
                })
            questions[-1].update(task_scope="applicability", disputed=True)
            questions[-1]["expected"].update(
                outcome="no_answer", spans=[], reason="temporal_coverage_unknown", gap_evidence=["e"],
            )
            dataset = {
                "schema_version": "gold-question-set/1", "dataset_id": "synthetic",
                "label_author": "author", "storage_policy": "private project test data",
                "questions": questions, "evidence": {"e": {
                    "raw_path": "text.txt", "text_path": "text.txt", "method": "synthetic",
                    "source_url": "project-authored:test", "raw_sha256": sha,
                    "text_sha256": sha, "acts": acts,
                }},
            }
            split = {"dataset_id": "synthetic", "members": {
                "working": [q["id"] for q in questions[:20]],
                "closed": [q["id"] for q in questions[20:]],
            }}
            dataset_path, split_path, review_path = [root / f"{name}.json" for name in ("dataset", "split", "review")]

            def write(path, value):
                path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

            write(dataset_path, dataset)
            write(split_path, split)
            records = validate(dataset_path, split_path)
            self.assertEqual(records["summary"]["pending_count"], 40)
            with self.assertRaisesRegex(ValueError, "all labels reviewed"):
                freeze(records, root / "frozen.json")
            self.assertFalse((root / "frozen.json").exists())

            mutations = [
                lambda d: d["questions"].__setitem__(0, None),
                lambda d: d["questions"].append(d["questions"][0]),
                lambda d: d["questions"][0].update(query_class="unknown"),
                lambda d: d["questions"][20].update(leakage_group="group0"),
                lambda d: d["questions"][0]["expected"]["spans"][0].update(start=True),
                lambda d: d["questions"][0]["expected"]["spans"][0].update(quote="corrupt"),
                lambda d: d["questions"][-1]["expected"].update(gap_evidence=[]),
                lambda d: d["evidence"]["e"].update(raw_path="../outside.txt"),
                lambda d: d["evidence"]["e"].update(raw_path="missing.txt"),
                lambda d: d["evidence"]["e"].update(raw_sha256="0" * 64),
                lambda d: d["evidence"]["e"].update(text_sha256="0" * 64),
                lambda d: d["evidence"]["e"].update(acts=[]),
            ]
            for mutate in mutations:
                with self.subTest(mutation=mutate):
                    changed = deepcopy(dataset)
                    mutate(changed)
                    write(dataset_path, changed)
                    with self.assertRaises((ValueError, OSError)):
                        validate(dataset_path, split_path)
            write(dataset_path, dataset)
            invalid_split = deepcopy(split)
            invalid_split["members"]["closed"].append("q0")
            write(split_path, invalid_split)
            with self.assertRaisesRegex(ValueError, "exactly once"):
                validate(dataset_path, split_path)
            write(split_path, split)

            decision = {
                "reviewer_role": "Legal Reviewer", "reviewer_id": "first",
                "decided_at": "2026-09-30T10:00:00Z", "rationale": "Synthetic test approval",
                "decision": "reviewed", "question_ids": [q["id"] for q in questions],
            }
            review = {
                "dataset_sha256": digest(dataset), "split_sha256": digest(split),
                "storage_approved": True, "decisions": [decision],
            }
            write(review_path, review)
            records = validate(dataset_path, split_path, review_path)
            self.assertEqual(records["summary"]["pending_count"], 1)
            for field, value in (("reviewer_role", "Engineer"), ("decided_at", "2026-09-30"),
                                 ("question_ids", ["unknown"]), ("decision", "pending")):
                altered = deepcopy(review)
                altered["decisions"][0][field] = value
                write(review_path, altered)
                with self.assertRaises(ValueError):
                    validate(dataset_path, split_path, review_path)
            altered = deepcopy(review)
            altered["dataset_sha256"] = "0" * 64
            write(review_path, altered)
            with self.assertRaisesRegex(ValueError, "exact dataset"):
                validate(dataset_path, split_path, review_path)
            for reviewer in ("first", "author"):
                review["decisions"] = [decision, {**decision, "reviewer_id": reviewer, "question_ids": ["q39"]}]
                write(review_path, review)
                self.assertEqual(validate(dataset_path, split_path, review_path)["summary"]["pending_count"], 1)
            review["decisions"] = [decision, {**decision, "reviewer_id": "second", "question_ids": ["q39"]}]
            write(review_path, review)
            records = validate(dataset_path, split_path, review_path)
            for value in ("rejected", "disputed"):
                altered = deepcopy(review)
                altered["decisions"][0]["decision"] = value
                write(review_path, altered)
                self.assertEqual(validate(dataset_path, split_path, review_path)["summary"]["pending_count"], 40)
            altered = deepcopy(review)
            altered["storage_approved"] = False
            write(review_path, altered)
            with self.assertRaisesRegex(ValueError, "storage approval"):
                freeze(validate(dataset_path, split_path, review_path), root / "frozen.json")
            write(review_path, review)
            self.assertEqual(freeze(records, root / "frozen.json"), "new")
            before = (root / "frozen.json").read_bytes()
            self.assertEqual(freeze(records, root / "frozen.json"), "unchanged")
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(main([
                    "--dataset", str(dataset_path), "--split", str(split_path),
                    "--review", str(review_path), "--freeze",
                ]), 0)
            self.assertEqual(json.loads(output.getvalue())["result"], "unchanged")
            records["review"]["decisions"][0]["rationale"] = "Changed decision"
            with self.assertRaisesRegex(ValueError, "cannot be overwritten"):
                freeze(records, root / "frozen.json")
            self.assertEqual((root / "frozen.json").read_bytes(), before)
            (root / "text.txt").write_bytes(b"corrupt")
            with redirect_stdout(StringIO()) as output:
                self.assertEqual(main(["--dataset", str(dataset_path), "--split", str(split_path)]), 1)
            self.assertIn("hash mismatch", output.getvalue())


if __name__ == "__main__":
    unittest.main()
