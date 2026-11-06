"""Read private badge settings without shell expansion or third-party packages."""

import json
import os
from pathlib import Path
import re

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
PRIVATE_NAMES = ("BADGE_ADMIN_KEY", "BADGE_FINAL_FLAG")


def load_private_config(path=ENV_PATH, environ=None):
    values = {}
    if path.is_file():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            key, value = key.strip(), value.strip()
            try:
                if not separator or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
                    raise ValueError
                if value.startswith('"'):
                    value = json.loads(value)
                elif value.startswith("'"):
                    if len(value) < 2 or not value.endswith("'"):
                        raise ValueError
                    value = value[1:-1]
                if not isinstance(value, str) or any(c in value for c in "\x00\r\n"):
                    raise ValueError
            except (ValueError, TypeError):
                raise ValueError(f"{path.name}:{number}: invalid KEY=VALUE setting") from None
            values[key] = value
    environment = os.environ if environ is None else environ
    values.update({key: environment[key] for key in PRIVATE_NAMES if key in environment})
    return values
