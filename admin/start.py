#!/usr/bin/env python3
"""Create the local venv, install changed requirements, and run the bridge."""

import argparse
import hashlib
import os
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


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    key = parser.add_mutually_exclusive_group()
    key.add_argument("--allow-dev-key", action="store_true")
    key.add_argument("--admin-key")
    return parser.parse_args(argv)


def main():
    options = parse_args(sys.argv[1:])
    python = prepare()
    bridge = str(ROOT / "bridge.py")
    environment = os.environ.copy()
    if options.admin_key:
        if len(options.admin_key.encode("utf-8")) < 32:
            raise SystemExit("--admin-key must be at least 32 UTF-8 bytes")
        environment["BADGE_ADMIN_KEY"] = options.admin_key
    subprocess.check_call([python, bridge, "--self-test"], env=environment)
    if options.check:
        print("[setup] ready")
        return
    bridge_args = ["--allow-dev-key"] if options.allow_dev_key else []
    os.execve(python, [python, bridge, *bridge_args], environment)


if __name__ == "__main__":
    main()
