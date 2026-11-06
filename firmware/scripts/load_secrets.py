"""Generate an ignored build header; private values never appear in compiler flags."""

import json
from pathlib import Path
import re
import sys

Import("env")

project = Path(env.subst("$PROJECT_DIR"))
sys.path.insert(0, str(project.parent / "admin"))
from private_config import load_private_config

settings = load_private_config()
key = settings.get("BADGE_ADMIN_KEY", "")
flag = settings.get("BADGE_FINAL_FLAG", "")
if len(key.encode("utf-8")) < 32 or key.startswith("AEGIS_DEV_ONLY"):
    raise SystemExit("Set a private BADGE_ADMIN_KEY of at least 32 UTF-8 bytes in .env or the environment")
if not re.fullmatch(r"MSGCTF\{[^{}\r\n]+\}", flag):
    raise SystemExit("Set BADGE_FINAL_FLAG in .env or the environment (MSGCTF{...})")

build = Path(env.subst("$BUILD_DIR"))
build.mkdir(parents=True, exist_ok=True)
header = build / "badge_secrets.h"
content = "#pragma once\n" + "".join(
    f"#define {name} {json.dumps(settings[name])}\n"
    for name in ("BADGE_ADMIN_KEY", "BADGE_FINAL_FLAG")
)
if not header.exists() or header.read_text(encoding="utf-8") != content:
    header.write_text(content, encoding="utf-8")
header.chmod(0o600)
env.Append(CPPPATH=[str(build)])
