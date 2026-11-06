#!/usr/bin/env python3
"""Build the Rev.3 firmware once and upload it to explicitly selected USB ports."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def find_platformio():
    executable = shutil.which("pio") or shutil.which("platformio")
    if executable:
        return executable
    core = Path(os.environ.get("PLATFORMIO_CORE_DIR", Path.home() / ".platformio"))
    executable = core / "penv" / (
        "Scripts/platformio.exe" if sys.platform == "win32" else "bin/platformio"
    )
    if executable.is_file():
        return str(executable)
    raise FileNotFoundError("PlatformIO를 찾지 못했습니다. PlatformIO IDE 터미널에서 실행하세요.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ports", nargs="*", help="배지 포트 목록 (COM5 COM6 등)")
    parser.add_argument("--list", action="store_true", help="연결된 포트만 표시")
    parser.add_argument("--dry-run", action="store_true", help="대상 확인만 수행; 빌드·업로드 생략")
    args = parser.parse_args(argv)
    if args.list and args.ports:
        parser.error("--list와 업로드 포트는 함께 지정할 수 없습니다.")

    pio = find_platformio()
    result = subprocess.run(
        [pio, "device", "list", "--json-output"],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    devices = json.loads(result.stdout)
    if not args.ports:
        for device in devices:
            print(f"{device['port']}  |  {device.get('description', '')}  |  {device.get('hwid', '')}")
        if not devices:
            print("연결된 Serial 포트가 없습니다.")
        print("배지 포트만 지정해 다시 실행하세요: python3 firmware/upload_all.py PORT1 PORT2")
        return 0

    # Exact names prevent PlatformIO wildcard matching or automatic port selection.
    available = {os.path.normcase(device["port"]): device["port"] for device in devices}
    ports = []
    for requested in args.ports:
        port = available.get(os.path.normcase(requested))
        if not port or any(char in port for char in "*?[]"):
            parser.error(f"연결된 정확한 포트를 지정하세요: {requested} (--list로 확인)")
        if port not in ports:
            ports.append(port)

    print(f"업로드 대상 {len(ports)}대: {', '.join(ports)}", flush=True)
    if args.dry_run:
        print("확인만 완료했습니다. 빌드·업로드하지 않았습니다.")
        return 0

    command = [pio, "run", "-d", str(ROOT), "-e", "esp32-s3-rev3"]
    print("배지 펌웨어를 한 번 빌드합니다.", flush=True)
    if subprocess.run(command).returncode:
        print("빌드 실패: 어떤 배지에도 업로드하지 않았습니다.", file=sys.stderr)
        return 1

    results = []
    # ponytail: sequential uploads; use independent esptool workers if batch time matters.
    for index, port in enumerate(ports, 1):
        print(f"\n[{index}/{len(ports)}] {port} 업로드", flush=True)
        try:
            code = subprocess.run(
                command + ["-t", "nobuild", "-t", "upload", "--upload-port", port]
            ).returncode
        except OSError as error:
            print(f"{port}: {error}", file=sys.stderr)
            code = 1
        results.append((port, code))

    print("\n업로드 결과", flush=True)
    for port, code in results:
        print(f"{'FAIL' if code else 'OK'}  {port}")
    failed = [port for port, code in results if code]
    print(f"성공 {len(results) - len(failed)}대 / 실패 {len(failed)}대")
    if failed:
        print("실패한 배지의 케이블·포트 점유·BOOT/EN을 확인하고 --list로 현재 포트를 확인하세요.")
        print("실패한 배지 포트만 지정해 다시 실행하면 됩니다.")
    return int(bool(failed))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"일괄 업로드 오류: {error}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n중단했습니다. 진행 중이던 배지는 재업로드가 필요할 수 있습니다.", file=sys.stderr)
        sys.exit(130)
