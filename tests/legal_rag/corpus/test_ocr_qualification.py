"""Human transcription decisions bind a single page, never an entire corpus."""

import copy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "verify_m1_04", Path(__file__).resolve().parents[3] / "docs/assets/verify_m1_04.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class TranscriptionReviewTest(unittest.TestCase):
    def test_owner_exclusion_is_source_bound_and_preserves_other_blockers(self):
        documents = [{"source_sha256": "a" * 64, "identical": False,
                      "same_runtime": True, "same_settings": True, "runtime_verified": True,
                      "accounting": [{"pages": 75}], "uncertainties": [[], []],
                      "conditional_signs_page_75": [{"matches": 0, "total": 13}]}]
        scope = {"schema_version": "ocr-quality-scope/1", "decision": "accepted",
                 "reviewer": "product-owner", "recorded_at": "2026-10-16T18:00:00+00:00",
                 "fresh_inference_policy": "versioned",
                 "excluded_table_pages": [{"source_asset_sha256": "a" * 64, "physical_page": 75}]}
        self.assertEqual(verifier.qualification_blockers(documents, True, scope), [])
        for field in ("same_runtime", "same_settings", "runtime_verified"):
            with self.subTest(field=field):
                changed_documents = copy.deepcopy(documents)
                changed_documents[0][field] = False
                self.assertTrue(verifier.qualification_blockers(changed_documents, True, scope))
        self.assertEqual(verifier.qualification_blockers(documents, True, scope, "saved_replay"),
                         ["saved_extraction_replay_drift"])
        self.assertEqual(verifier.qualification_blockers(documents, True),
                         ["critical_ocr_errors_require_review", "fresh_ocr_output_drift"])
        changed = copy.deepcopy(scope)
        changed["excluded_table_pages"][0]["physical_page"] = 74
        self.assertEqual(verifier.qualification_blockers(documents, True, changed),
                         ["critical_ocr_errors_require_review"])
        changed["excluded_table_pages"][0]["source_asset_sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            verifier.qualification_blockers(documents, True, changed)
        self.assertEqual(verifier.qualification_blockers(documents, False, scope),
                         ["human_reviewed_transcription_missing"])
        documents[0]["uncertainties"][0].append("picture_ocr_incomplete_response")
        self.assertEqual(verifier.qualification_blockers(documents, True, scope), ["unresolved_picture_ocr"])

    def test_exact_page_binding_and_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pages").mkdir()
            (root / "pages/page_0001.png").write_bytes(b"authored page image")
            (root / "reference.txt").write_bytes("Текст\r\n".encode())
            reference = {"source": {"sha256": "a" * 64},
                         "pages": [{"page_number": 1, "text": "Текст\n"}]}
            review = {"schema_version": "ocr-transcription-review/1", "decision": "accepted",
                      "reviewer": "owner", "recorded_at": "2026-10-16T13:36:10+00:00",
                      "source_asset_sha256": "a" * 64, "physical_page": 1,
                      "reference_sha256": sha256("Текст\n".encode()).hexdigest(),
                      "reference_artifact_sha256": sha256((root / "reference.txt").read_bytes()).hexdigest(),
                      "image_sha256": sha256(b"authored page image").hexdigest(),
                      "actual_review_minutes": None}
            path = root / "human-review.json"
            metrics = [{"pages": [{"page": 1, "cer": 0.1, "wer": 0.2}]}] * 2

            def check(record):
                path.write_text(json.dumps(record), encoding="utf-8")
                return verifier.reviewed_sample(path, reference, [root, root], metrics)

            result = check(review)
            self.assertEqual(result["metrics"], [m["pages"][0] for m in metrics])
            self.assertIsNone(result["actual_review_minutes"])
            for field, value in (("decision", "pending"), ("source_asset_sha256", "b" * 64),
                                 ("physical_page", 2), ("reference_sha256", "b" * 64),
                                 ("reference_artifact_sha256", "b" * 64), ("image_sha256", "b" * 64),
                                 ("reviewer", ""), ("recorded_at", "2026-10-16T13:36:10")):
                with self.subTest(field=field):
                    invalid = copy.deepcopy(review)
                    invalid[field] = value
                    with self.assertRaises(ValueError):
                        check(invalid)
