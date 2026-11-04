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


def run_verifier(model, arguments=(), exit_code=0):
    directory, manifest, marker = model
    command = marker.parent / "command with spaces" / "fake inference.py"
    command.parent.mkdir()
    command.write_text("from pathlib import Path\nimport json,sys\n"
                       "Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]), encoding='utf-8')\n"
                       f"raise SystemExit({exit_code})\n", encoding="utf-8")
    return subprocess.run([sys.executable, str(VERIFY), str(directory), str(manifest), "--",
                           sys.executable, str(command), str(marker), *arguments], capture_output=True, text=True, timeout=30)


def test_matching_model_starts_the_command(model):
    result = run_verifier(model)
    assert result.returncode == 0, result.stderr
    assert model[2].exists()


@pytest.mark.parametrize("exit_code", [0, 7])
def test_command_preserves_arguments_and_exit_code(model, exit_code):
    arguments = ["two words", 'кавычка"текст', "", "C:\\folder with spaces\\"]
    result = run_verifier(model, arguments, exit_code)
    assert result.returncode == exit_code, result.stderr
    assert model[2].exists(), result.stderr
    assert json.loads(model[2].read_text(encoding="utf-8")) == arguments


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
