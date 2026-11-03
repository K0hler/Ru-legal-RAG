import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


VERIFY = Path(__file__).resolve().parents[3] / "ocr/dotsmocr/scripts/verify_model.py"


@pytest.fixture
def model(tmp_path):
    directory = tmp_path / "model"
    directory.mkdir()
    files = {"config.json": b'{"model_type":"dots_ocr"}', "model.safetensors": b"authored weights"}
    for name, payload in files.items():
        (directory / name).write_bytes(payload)
    hashes = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"dotsmocr": {"sha256": hashes}}), encoding="utf-8")
    return directory, manifest, tmp_path / "inference-started"


def run_verifier(model):
    directory, manifest, marker = model
    command = marker.parent / "fake_inference.py"
    command.write_text("from pathlib import Path\nimport sys\nPath(sys.argv[1]).touch()\n", encoding="utf-8")
    return subprocess.run([sys.executable, str(VERIFY), str(directory), str(manifest), "--",
                           sys.executable, str(command), str(marker)], capture_output=True, text=True, timeout=30)


def test_matching_model_starts_the_command(model):
    result = run_verifier(model)
    assert result.returncode == 0, result.stderr
    assert model[2].exists()


@pytest.mark.parametrize("damage", ["corrupt", "missing", "extra"])
def test_invalid_model_is_rejected_before_start(model, damage):
    directory, _, marker = model
    weight = directory / "model.safetensors"
    if damage == "corrupt":
        weight.write_bytes(b"altered weights")
    elif damage == "missing":
        weight.unlink()
    else:
        (directory / "unlisted.py").write_bytes(b"unverified code")
    result = run_verifier(model)
    assert result.returncode != 0
    assert "model integrity check failed" in result.stderr.lower()
    assert not marker.exists()


def test_manifest_cannot_name_files_outside_model(model, tmp_path):
    _, manifest, marker = model
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    manifest.write_text(json.dumps({"dotsmocr": {"sha256": {"../outside": hashlib.sha256(b"outside").hexdigest()}}}),
                        encoding="utf-8")
    result = run_verifier(model)
    assert result.returncode != 0
    assert "model integrity check failed" in result.stderr.lower()
    assert not marker.exists()
