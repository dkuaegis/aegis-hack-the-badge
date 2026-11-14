"""Check batch selection, build failure and per-port failure without touching USB."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import upload_all

DEVICES = [{"port": port, "description": "USB test device",
            "hwid": "USB VID:PID=303A:1001" if port != "COM8" else "USB VID:PID=1234:5678"}
           for port in ("COM5", "COM6", "COM7", "COM8")]


def run_batch(args, build_code=0, upload_codes=None, buildfs_code=0, answer="y"):
    calls = []
    output = io.StringIO()

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == "device":
            return subprocess.CompletedProcess(command, 0, json.dumps(DEVICES))
        if "--upload-port" in command:
            port = command[command.index("--upload-port") + 1]
            target = "uploadfs" if "uploadfs" in command else "upload"
            code = (upload_codes or {}).get((port, target),
                                           (upload_codes or {}).get(port, 0))
            if isinstance(code, Exception):
                raise code
        elif "buildfs" in command:
            code = buildfs_code
        else:
            code = build_code
        return subprocess.CompletedProcess(command, code)

    with patch.object(upload_all, "find_platformio", return_value="pio"), \
            patch.object(upload_all.subprocess, "run", side_effect=run), \
            patch("builtins.input", return_value=answer), \
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

for args in (["COM5", "COM99"], ["COM*"], [""], ["--list", "COM5"],
             ["--all", "COM5"], ["--all", "--list"]):
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

code, calls, output = run_batch(["--firmware", "default", "--all", "--dry-run"])
assert code == 0 and len(calls) == 1
assert "COM5, COM6, COM7" in output and "COM8" not in output
code, calls, output = run_batch(["--all"], answer="n")
assert code == 0 and len(calls) == 1 and "취소" in output
code, calls, output = run_batch(["--all"])
assert code == 0 and len(calls) == 5
assert [call[-1] for call in calls[2:]] == ["COM5", "COM6", "COM7"]

with TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "data").mkdir()
    (root / "data/doom1.wad").write_bytes(b"wad")
    (root / "badapple_data").mkdir()
    (root / "badapple_data/video.rle").write_bytes(b"video")
    (root / "badapple_data/music.bin").write_bytes(b"music")
    with patch.object(upload_all, "ROOT", root):
        for firmware in ("doom", "badapple"):
            code, calls, output = run_batch(["--firmware", firmware, "COM5", "COM6"])
            assert code == 0 and len(calls) == 7
            assert calls[2][-2:] == ["-t", "buildfs"]
            assert all(call[-2] == "--upload-port" for call in calls[3:])
            assert [call[-1] for call in calls[3:]] == ["COM5", "COM5", "COM6", "COM6"]
            assert ["uploadfs" in call for call in calls[3:]] == [False, True, False, True]
            assert all(call[call.index("-e") + 1] == upload_all.FIRMWARE[firmware]
                       for call in calls[1:])
        code, calls, output = run_batch(["--firmware", "doom", "COM5"], buildfs_code=1)
        assert code == 1 and len(calls) == 3 and "어떤 배지에도" in output
        code, calls, output = run_batch(["--firmware", "doom", "COM5", "COM6"],
                                        upload_codes={("COM5", "uploadfs"): 1})
        assert code == 1 and len(calls) == 7 and "FAIL  COM5" in output and "OK  COM6" in output
        code, calls, output = run_batch(["--firmware", "doom", "COM5", "COM6"],
                                        upload_codes={("COM5", "upload"): 1})
        assert code == 1 and len(calls) == 6
        assert not any("uploadfs" in call and call[-1] == "COM5" for call in calls)
        (root / "data/doom1.wad").write_bytes(b"")
        code, calls, output = run_batch(["--firmware", "doom", "COM5"])
        assert code == 1 and len(calls) == 1 and "필수 데이터" in output
print("batch upload selection, build-once and failure handling checks: OK")
