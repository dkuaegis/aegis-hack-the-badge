"""Check batch selection, build failure and per-port failure without touching USB."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import upload_all

DEVICES = [{"port": port, "description": "USB test device"}
           for port in ("COM5", "COM6", "COM7", "COM8")]


def run_batch(args, build_code=0, upload_codes=None):
    calls = []
    output = io.StringIO()

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == "device":
            return subprocess.CompletedProcess(command, 0, json.dumps(DEVICES))
        if "--upload-port" in command:
            port = command[command.index("--upload-port") + 1]
            code = (upload_codes or {}).get(port, 0)
            if isinstance(code, Exception):
                raise code
        else:
            code = build_code
        return subprocess.CompletedProcess(command, code)

    with patch.object(upload_all, "find_platformio", return_value="pio"), \
            patch.object(upload_all.subprocess, "run", side_effect=run), \
            redirect_stdout(output), redirect_stderr(output):
        try:
            code = upload_all.main(args)
        except SystemExit as error:
            code = error.code
    return code, calls, output.getvalue()


code, calls, output = run_batch(["COM5", "COM6", "COM5", "COM7"], upload_codes={"COM6": 2})
assert code == 1
assert len(calls) == 5  # Discovery, one build, three distinct uploads.
assert "--upload-port" not in calls[1] and "-t" not in calls[1]
assert [call[-1] for call in calls[2:]] == ["COM5", "COM6", "COM7"]
assert all(call[-6:-1] == ["-t", "nobuild", "-t", "upload", "--upload-port"]
           for call in calls[2:])
assert all(call[call.index("-e") + 1] == "esp32-s3-rev3" for call in calls[1:])
assert all(call[call.index("-d") + 1] == str(upload_all.ROOT) for call in calls[1:])
assert "OK  COM5" in output and "FAIL  COM6" in output and "OK  COM7" in output
assert "성공 2대 / 실패 1대" in output

code, calls, output = run_batch(["COM5", "COM6"], build_code=1)
assert code == 1 and len(calls) == 2  # Never flash stale firmware after a failed build.
assert not any("--upload-port" in call for call in calls)

for args in (["COM5", "COM99"], ["COM*"], [""], ["--list", "COM5"]):
    code, calls, output = run_batch(args)
    assert code == 2 and len(calls) <= 1  # Validate the entire selection before building.

for args in ([], ["--list"], ["--dry-run", "COM5", "COM6"]):
    code, calls, output = run_batch(args)
    assert code == 0 and len(calls) == 1  # Discovery/preview never builds or opens USB.

code, calls, output = run_batch(["COM5", "COM7"])
assert code == 0 and len(calls) == 4 and "성공 2대 / 실패 0대" in output
assert "COM6" not in output and "COM8" not in output  # Unselected devices are untouched.

code, calls, output = run_batch(["COM5", "COM7"], upload_codes={"COM5": OSError("disconnected")})
assert code == 1 and len(calls) == 4 and "OK  COM7" in output
print("batch upload selection, build-once and failure handling checks: OK")
