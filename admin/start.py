#!/usr/bin/env python3
"""Create the local venv, install changed requirements, and run the bridge."""

import hashlib
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
MARKER = VENV / ".requirements.sha256"


def venv_python():
    return VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def requirement_hash():
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def prepare():
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required.")
    python_path = venv_python()
    if not python_path.exists():
        print("[setup] creating admin/.venv")
        venv.EnvBuilder(with_pip=True).create(str(VENV))
    python = str(python_path)

    digest = requirement_hash()
    imports_ok = subprocess.run(
        [python, "-c", "import aiohttp, bleak"], capture_output=True
    ).returncode == 0
    if (not imports_ok or not MARKER.exists()
            or MARKER.read_text(encoding="utf-8").strip() != digest):
        print("[setup] installing Python packages")
        subprocess.check_call([
            python, "-m", "pip", "install", "--disable-pip-version-check",
            "-r", REQUIREMENTS,
        ])
        MARKER.write_text(digest, encoding="utf-8")
    return python


def main():
    python = prepare()
    bridge = str(ROOT / "bridge.py")
    subprocess.check_call([python, bridge, "--self-test"])
    if "--check" in sys.argv[1:]:
        print("[setup] ready")
        return
    raise SystemExit(subprocess.call([python, bridge]))


if __name__ == "__main__":
    main()
