from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.__main__ import main  # noqa: E402
from legal_rag.sources.transport import RequestMeter  # noqa: E402


class PilotTest(unittest.TestCase):
    def test_request_meter_paces_adjacent_requests_and_counts_bytes(self):
        meter = RequestMeter(1.0)
        with (
            patch(
                "legal_rag.sources.transport.monotonic",
                side_effect=[10.0, 10.0, 10.25, 11.0],
            ),
            patch("legal_rag.sources.transport.sleep") as mocked_sleep,
        ):
            meter.before_request()
            meter.record_response(b"first")
            meter.before_request()
            meter.record_response(b"second")

        mocked_sleep.assert_called_once_with(0.75)
        self.assertEqual(
            meter.metrics,
            {"bytes_received": 11, "request_count": 2},
        )

    def test_cli_retries_and_reports_two_comparable_five_act_passes(self):
        successful_calls: dict[str, int] = {}
        failed_once = False

        def acquire(item, connectors, data_dir):
            nonlocal failed_once
            source_item = item["source_item"]
            result = "new" if successful_calls.get(source_item, 0) == 0 else "unchanged"
            errors = []
            exception_ids = []
            request_count = 2
            if not failed_once:
                failed_once = True
                result = "failed"
                request_count = 1
                errors = [
                    {
                        "message": "temporary source failure",
                        "reason": "network_error",
                        "retryable": True,
                        "source_url": "http://example.invalid/source",
                        "stage": "acquisition",
                    }
                ]
                exception_ids = [str(uuid.uuid4())]
            else:
                successful_calls[source_item] = successful_calls.get(source_item, 0) + 1

            run_id = str(uuid.uuid4())
            report_path = data_dir / "runs" / f"{run_id}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(
                    {
                        "errors": errors,
                        "exception_ids": exception_ids,
                        "metrics": {
                            "bytes_received": 100 if result != "failed" else 0,
                            "request_count": request_count,
                        },
                        "result": result,
                    }
                ),
                encoding="utf-8",
            )
            return {
                "report": str(report_path.resolve()),
                "result": result,
                "run_id": run_id,
                "source_item": source_item,
            }

        with tempfile.TemporaryDirectory() as temporary_directory:
            stdout = StringIO()
            with (
                patch("legal_rag.sources.pilot._acquire_item", side_effect=acquire),
                patch("legal_rag.sources.pilot.sleep"),
                redirect_stdout(stdout),
            ):
                exit_code = main(
                    [
                        "run-pilot",
                        "--data-dir",
                        temporary_directory,
                    ]
                )

            self.assertEqual(exit_code, 0)
            result = json.loads(stdout.getvalue())
            report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))

            self.assertEqual(result["result"], "completed")
            self.assertEqual(report["schema_version"], "m0-pilot-report/1")
            self.assertEqual(len(report["manifest"]), 5)
            self.assertEqual(
                sum(len(act["items"]) for act in report["manifest"]),
                14,
            )
            self.assertEqual(report["passes"][0]["counts"], {
                "changed": 0,
                "failed": 0,
                "new": 14,
                "unchanged": 0,
            })
            self.assertEqual(report["passes"][1]["counts"], {
                "changed": 0,
                "failed": 0,
                "new": 0,
                "unchanged": 14,
            })
            self.assertEqual(report["metrics"]["retry_count"], 1)
            self.assertEqual(report["metrics"]["failed_attempts"], 1)
            self.assertEqual(len(report["exceptions"]), 1)
            self.assertEqual(report["exceptions"][0]["pass"], 1)
            self.assertEqual(report["duplicate_source_items"], [])
            self.assertEqual(
                report["coverage_gaps"],
                {
                    "amendment_coverage_unresolved": [
                        "housing-code",
                        "government-decree-354",
                        "government-decree-491",
                        "federal-law-59",
                    ],
                    "missing_consolidated_editions": ["sanpin-2.1.3684-21"],
                    "temporal_evidence_unresolved": [
                        "housing-code",
                        "government-decree-354",
                        "government-decree-491",
                        "federal-law-59",
                        "sanpin-2.1.3684-21",
                    ],
                },
            )
            self.assertTrue(all(Path(item["report"]).is_file() for item in report["passes"]))


if __name__ == "__main__":
    unittest.main()
