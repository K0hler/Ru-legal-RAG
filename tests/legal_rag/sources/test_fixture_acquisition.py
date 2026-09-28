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

from legal_rag.sources.acquisition import acquire_fixture, acquire_publication  # noqa: E402
from legal_rag.sources.publication_pravo import (  # noqa: E402
    PublicationPravoConnector,
    PublicationPravoFailure,
)


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

    def test_fixture_media_type_is_detected_from_content(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            metadata = json.loads(FIXTURE_METADATA.read_text(encoding="utf-8"))
            metadata["media_type"] = "application/pdf"
            metadata_path = root / "metadata.json"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            acquire_fixture(FIXTURE, metadata_path, root / "data")

            asset_path = next((root / "data" / "assets").glob("*.json"))
            asset = json.loads(asset_path.read_text(encoding="utf-8"))
            self.assertEqual(asset["media_type"], "text/plain; charset=utf-8")

    def test_source_item_lifecycle_preserves_assets_and_reports_every_outcome(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            data_dir = Path(temporary_directory) / "data"
            changed_fixture = Path(temporary_directory) / "changed.txt"
            changed_fixture.write_bytes(FIXTURE.read_bytes() + b"changed")

            outputs = [
                acquire_fixture(FIXTURE, FIXTURE_METADATA, data_dir),
                acquire_fixture(FIXTURE, FIXTURE_METADATA, data_dir),
                acquire_fixture(changed_fixture, FIXTURE_METADATA, data_dir),
            ]
            connector = PublicationPravoConnector()
            connector.source_system = "fixture"
            connector.adapter_version = "fixture/1"
            with patch.object(
                connector,
                "fetch",
                side_effect=PublicationPravoFailure(
                    "timeout",
                    "source request timed out",
                    retryable=True,
                ),
            ):
                outputs.append(acquire_publication(connector, "sample-act", data_dir))

            self.assertEqual(
                [output["result"] for output in outputs],
                ["new", "unchanged", "changed", "failed"],
            )

            item_path = next((data_dir / "items").glob("*.json"))
            item = json.loads(item_path.read_text(encoding="utf-8"))
            changed_hash = hashlib.sha256(changed_fixture.read_bytes()).hexdigest()
            self.assertEqual(item["latest_successful_asset"], changed_hash)
            self.assertEqual(item["asset_sha256s"], [self._fixture_hash(), changed_hash])
            self.assertEqual(len(list((data_dir / "raw").iterdir())), 2)
            self.assertEqual(len(list((data_dir / "assets").iterdir())), 2)
            self.assertEqual(len(list((data_dir / "runs").iterdir())), 4)

            reports = [
                json.loads(Path(output["report"]).read_text(encoding="utf-8"))
                for output in outputs
            ]
            for outcome, report in zip(
                ("new", "unchanged", "changed", "failed"),
                reports,
                strict=True,
            ):
                self.assertEqual(
                    report["counts"],
                    {
                        status: int(status == outcome)
                        for status in ("new", "unchanged", "changed", "failed")
                    },
                )
                self.assertEqual(len(report["errors"]), int(outcome == "failed"))

            self.assertEqual(
                reports[2]["change"],
                {
                    "new_sha256": changed_hash,
                    "old_sha256": self._fixture_hash(),
                    "source_item": "fixture:sample-act",
                },
            )
            self.assertEqual(reports[3]["errors"][0]["reason"], "timeout")

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
