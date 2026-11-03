import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from legal_rag.corpus import ocr_runtime as runtime  # noqa: E402
from legal_rag.corpus.compiler import json_bytes  # noqa: E402


@pytest.fixture
def own_runtime(tmp_path):
    project = tmp_path / "project with spaces"
    runtime_dir = project / "ocr/dotsmocr"
    files = {
        "compose.yaml": b"compose",
        "Dockerfile": b"dockerfile",
        "scripts/new_ocr_pdf.py": b"client",
        "scripts/verify_model.py": b"verifier",
        "config/new_ocr_models.json": b"model manifest",
        "config/dotsmocr_prompt.txt": b"prompt",
        "config/dotsmocr_picture_ocr.json": json_bytes({"enabled": True, "max_tokens": 512}),
    }
    for name, value in files.items():
        path = runtime_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    for name in ("input", "results", "model"):
        (project / "data/ocr/dotsmocr" / name).mkdir(parents=True)
    receipt = tmp_path / "receipt"
    receipt.mkdir()
    config = {"provider": "legal-rag-dotsmocr", "engine": "dotsmocr", "project_root": str(project),
              "workers": 4, "page_orientation": True, "rotation_retry": True, "loop_retry": True,
              "picture_ocr_failure_policy": "retain_unresolved"}
    return project, runtime_dir, receipt, config


def docker_double(runtime_dir, commands, *, image="sha256:fixture", config_hash="expected", baked=None,
                  change=None):
    data = runtime_dir.parents[1] / "data/ocr/dotsmocr"
    volumes = [{"type": "bind", "source": str(data / name), "target": "/data/" + name,
                "read_only": name != "results"}
               for name in ("model", "input", "results")]
    profile = {"command": ["vllm", "serve", "/data/model"], "environment": {"HF_HUB_OFFLINE": "1"},
               "volumes": volumes}
    def execute(command, **kwargs):
        commands.append(command)
        if command[1:3] == ["inspect", "--format"]:
            value = {"Id": "container", "State": {"Status": "running", "StartedAt": "start",
                                                   "Health": {"Status": "healthy"}},
                     "Image": image, "Config": {
                         "Entrypoint": ["python3", "/opt/dotsmocr/scripts/verify_model.py", "/data/model",
                                        "/opt/dotsmocr/config/new_ocr_models.json", "--"],
                         "Cmd": profile["command"], "Env": ["HF_HUB_OFFLINE=1"],
                         "Labels": {"com.docker.compose.config-hash": config_hash}},
                     "Mounts": [{"Type": "bind", "Source": v["source"], "Destination": v["target"],
                                 "RW": not v["read_only"]} for v in volumes]}
            if change == "command":
                value["Config"]["Cmd"] = ["other"]
            if change == "mount":
                value["Mounts"][0]["RW"] = True
            if change == "environment":
                value["Config"]["Env"] = ["HF_HUB_OFFLINE=0"]
            if change == "restart" and any("--output" in c for c in commands):
                value["State"]["StartedAt"] = "restarted"
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps(value))
        if command[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(command, 0, stdout="sha256:fixture\n")
        if "--hash" in command:
            return subprocess.CompletedProcess(command, 0, stdout="dotsmocr expected\n")
        if "--format" in command and "config" in command:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"services": {"dotsmocr": profile}}))
        if command[1:3] == ["exec", "legal-rag-dotsmocr"]:
            paths = ["scripts/verify_model.py", "config/new_ocr_models.json"]
            values = baked or {p: hashlib.sha256((runtime_dir / p).read_bytes()).hexdigest() for p in paths}
            return subprocess.CompletedProcess(command, 0, stdout="\n".join(
                f"{values[p]}  /opt/dotsmocr/{p}" for p in paths))
        return subprocess.CompletedProcess(command, 0, stdout="")
    return execute


def test_own_provider_snapshots_and_runs_only_its_container(own_runtime):
    project, runtime_dir, receipt, config = own_runtime
    commands = []
    with patch.object(runtime.subprocess, "run", side_effect=docker_double(runtime_dir, commands)):
        result = runtime.run_legal_rag_dotsmocr(config, b"%PDF fixture", "a" * 64, receipt)
    data = project / "data/ocr/dotsmocr"
    assert result == data / "results/legal-rag/receipt"
    assert (data / "input" / ("legal-rag-" + "a" * 64 + ".pdf")).read_bytes() == b"%PDF fixture"
    snapshot = next((data / "results/legal-rag-runtime").iterdir())
    assert (snapshot / "scripts/new_ocr_pdf.py").read_bytes() == b"client"
    picture = json.loads((snapshot / "config/dotsmocr_picture_ocr.json").read_bytes())
    assert picture["failure_policy"] == "retain_unresolved" and picture["recover_repetitions"]
    command = next(command for command in commands if "--output" in command)
    assert command[:4] == ["docker", "compose", "-f", str(runtime_dir / "compose.yaml")]
    assert command[command.index("--output") + 1] == "/data/results/legal-rag/receipt"
    assert all(flag in command for flag in ("--rotation-retry", "--loop-retry", "--page-orientation"))
    receipt_data = json.loads((receipt / "runtime.json").read_bytes())
    assert receipt_data["provider"] == "legal-rag-dotsmocr"
    assert receipt_data["image_id"] == "sha256:fixture"
    assert receipt_data["profile_id"] == snapshot.name


@pytest.mark.parametrize("failure", ["image", "compose", "manifest", "command", "mount", "environment"])
def test_own_provider_rejects_unverified_service_before_staging(own_runtime, failure):
    project, runtime_dir, receipt, config = own_runtime
    commands = []
    kwargs = {"image": "sha256:wrong"} if failure == "image" else (
        {"config_hash": "wrong"} if failure == "compose" else (
            {"baked": {"scripts/verify_model.py": "0" * 64, "config/new_ocr_models.json": "0" * 64}}
            if failure == "manifest" else {"change": failure}))
    with patch.object(runtime.subprocess, "run", side_effect=docker_double(runtime_dir, commands, **kwargs)):
        with pytest.raises(RuntimeError):
            runtime.run_legal_rag_dotsmocr(config, b"%PDF fixture", "a" * 64, receipt)
    assert not list((project / "data/ocr/dotsmocr/input").iterdir())
    assert not (receipt / "runtime.json").exists()


def test_own_provider_rejects_a_service_restarted_during_extraction(own_runtime):
    _, runtime_dir, receipt, config = own_runtime
    commands = []
    with patch.object(runtime.subprocess, "run", side_effect=docker_double(runtime_dir, commands, change="restart")):
        with pytest.raises(RuntimeError, match="changed during"):
            runtime.run_legal_rag_dotsmocr(config, b"%PDF fixture", "a" * 64, receipt)


def test_own_provider_rejects_changed_snapshot_after_execution(own_runtime):
    project, runtime_dir, receipt, config = own_runtime
    commands = []
    execute = docker_double(runtime_dir, commands)

    def alter(command, **kwargs):
        result = execute(command, **kwargs)
        if "--output" in command:
            snapshot = next((project / "data/ocr/dotsmocr/results/legal-rag-runtime").iterdir())
            (snapshot / "scripts/new_ocr_pdf.py").write_bytes(b"changed during OCR")
        return result

    with patch.object(runtime.subprocess, "run", side_effect=alter):
        with pytest.raises(RuntimeError, match="snapshot changed"):
            runtime.run_legal_rag_dotsmocr(config, b"%PDF fixture", "a" * 64, receipt)


@pytest.mark.parametrize("field,value", [("workers", True), ("loop_retry", 1), ("timeout_seconds", 0)])
def test_own_provider_rejects_invalid_settings_before_docker(own_runtime, field, value):
    _, _, receipt, config = own_runtime
    config[field] = value
    with patch.object(runtime.subprocess, "run", side_effect=AssertionError("unexpected Docker call")):
        with pytest.raises(ValueError):
            runtime.run_legal_rag_dotsmocr(config, b"%PDF fixture", "a" * 64, receipt)
