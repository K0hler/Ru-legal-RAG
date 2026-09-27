import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
FIXTURES = Path(__file__).with_name("fixtures")
FIXTURE = FIXTURES / "sample_act.txt"
FIXTURE_METADATA = FIXTURES / "sample_act.json"

sys.path.insert(0, str(SRC_ROOT))

from legal_rag.sources.acquisition import acquire_fixture  # noqa: E402


class FixtureAcquisitionTest(unittest.TestCase):
    def test_cli_records_new_then_unchanged_without_duplicate_raw_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)

            first = self._run_cli(data_dir)
            raw_path = next((data_dir / "raw").iterdir())
            first_raw_mtime = raw_path.stat().st_mtime_ns
            second = self._run_cli(data_dir)

            expected_hash = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
            fixture_metadata = json.loads(FIXTURE_METADATA.read_text(encoding="utf-8"))
            self.assertEqual(fixture_metadata["expected_sha256"], expected_hash)
            self.assertEqual(first["result"], "new")
            self.assertEqual(second["result"], "unchanged")
            self.assertEqual(first["source_item"], "fixture:sample-act")
            self.assertEqual(second["source_item"], "fixture:sample-act")
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertEqual(raw_path.read_bytes(), FIXTURE.read_bytes())
            self.assertEqual(raw_path.name, expected_hash)
            self.assertEqual(raw_path.stat().st_mtime_ns, first_raw_mtime)
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 1)
            self.assertEqual(len(list((data_dir / "assets").glob("*.json"))), 1)
            self.assertEqual(len(list((data_dir / "items").glob("*.json"))), 1)
            self.assertEqual(len(list((data_dir / "runs").glob("*.json"))), 2)

            asset = json.loads(
                (data_dir / "assets" / f"{expected_hash}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(asset["sha256"], expected_hash)
            self.assertEqual(asset["byte_length"], len(FIXTURE.read_bytes()))
            self.assertEqual(asset["captured_at"], fixture_metadata["captured_at"])
            self.assertEqual(asset["source_url"], fixture_metadata["source_url"])
            self.assertEqual(asset["archive_key"], f"raw/{expected_hash}")

            for output in (first, second):
                report_path = Path(output["report"])
                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(report["run_id"], output["run_id"])
                self.assertEqual(report["source"], "fixture")
                self.assertEqual(report["source_item"], "fixture:sample-act")
                self.assertEqual(report["result"], output["result"])
                self.assertEqual(report["adapter_version"], "fixture/1")
                self.assertEqual(report["errors"], [])
                self.assertTrue(report["started_at"].endswith("Z"))
                self.assertTrue(report["finished_at"].endswith("Z"))

    def test_interrupted_asset_metadata_write_is_not_visible(self):
        original_replace = os.replace

        def interrupt_asset_metadata(source, destination):
            if Path(destination).parent.name == "assets":
                raise OSError("simulated interruption")
            original_replace(source, destination)

        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory)
            with patch(
                "legal_rag.sources.acquisition.os.replace",
                side_effect=interrupt_asset_metadata,
            ):
                with self.assertRaisesRegex(OSError, "simulated interruption"):
                    acquire_fixture(FIXTURE, FIXTURE_METADATA, data_dir)

            self.assertEqual(list((data_dir / "assets").glob("*.json")), [])
            self.assertFalse((data_dir / "items").exists())
            self.assertFalse((data_dir / "runs").exists())
            self.assertEqual(list(data_dir.rglob("*.tmp")), [])

    def test_changed_fixture_is_deferred_without_changing_the_current_item(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "data"
            changed_fixture = Path(temporary_directory) / "changed.txt"
            changed_fixture.write_bytes(FIXTURE.read_bytes() + b"changed")
            first = acquire_fixture(FIXTURE, FIXTURE_METADATA, data_dir)

            with self.assertRaisesRegex(NotImplementedError, "M0-03"):
                acquire_fixture(changed_fixture, FIXTURE_METADATA, data_dir)

            item_path = next((data_dir / "items").glob("*.json"))
            item = json.loads(item_path.read_text(encoding="utf-8"))
            self.assertEqual(item["latest_successful_asset"], self._fixture_hash())
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 1)
            self.assertEqual(len(list((data_dir / "runs").iterdir())), 1)
            self.assertEqual(first["result"], "new")

    def _run_cli(self, data_dir: Path) -> dict[str, object]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            value
            for value in (str(SRC_ROOT), environment.get("PYTHONPATH"))
            if value
        )
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "legal_rag.sources",
                "acquire-fixture",
                "--fixture",
                str(FIXTURE),
                "--metadata",
                str(FIXTURE_METADATA),
                "--data-dir",
                str(data_dir),
            ],
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)

    def _fixture_hash(self) -> str:
        return hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
