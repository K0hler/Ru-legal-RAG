"""Verify every pinned model file before starting the container command."""

import hashlib
import json
import os
from pathlib import Path
import re
import sys


def verify_model(directory: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hashes = manifest["dotsmocr"]["sha256"]
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("missing file hashes")
    for name, digest in hashes.items():
        if (not isinstance(name, str) or not name or Path(name).name != name or "\\" in name
                or name in {".", ".."} or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise ValueError("invalid model manifest entry")
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("model directory is missing or a symlink")
    entries = list(directory.iterdir())
    if any(item.is_symlink() or not item.is_file() for item in entries):
        raise ValueError("model contains an unverified entry")
    if {item.name for item in entries} != set(hashes):
        raise ValueError("model files differ from the manifest")
    for name, expected in hashes.items():
        with (directory / name).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != expected:
            raise ValueError(f"model hash mismatch: {name}")


if __name__ == "__main__":
    if len(sys.argv) < 5 or sys.argv[3] != "--":
        raise SystemExit("usage: verify_model.py MODEL MANIFEST -- COMMAND [ARG ...]")
    try:
        verify_model(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(f"model integrity check failed: {error}") from error
    os.execvp(sys.argv[4], sys.argv[4:])
