#!/usr/bin/env python3
"""Cross-platform BLE bridge and local web dashboard for AEGIS badges."""

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import os
import sys
import time
import unicodedata
from collections import deque
from pathlib import Path

SERVICE_UUID = "6f8d0001-6a4b-4c52-9f2a-8f0f5d9b0001"
RX_UUID = "6f8d0002-6a4b-4c52-9f2a-8f0f5d9b0001"
TX_UUID = "6f8d0003-6a4b-4c52-9f2a-8f0f5d9b0001"
DEFAULT_ADMIN_KEY = "AEGIS_DEV_ONLY_CHANGE_ME"
ADMIN_KEY = os.environ.get("BADGE_ADMIN_KEY", DEFAULT_ADMIN_KEY)
BLE_COMMAND_MAX = 767
PROBLEM_LIMITS = {"title": 23, "prompt": 255, "answer": 79, "option": 23}
DASHBOARD_PATH = Path(__file__).with_name("dashboard") / "index.html"
FAVICON_PATH = DASHBOARD_PATH.with_name("favicon.svg")


def auth_tag(key, badge_id, challenge):
    message = f"{badge_id}:{challenge}".encode("ascii")
    return hmac.new(key.encode("utf-8"), message, hashlib.sha256).hexdigest()[:14].upper()


def normalize_problem(data):
    if not isinstance(data, dict):
        raise ValueError("problem must be a JSON object")
    problem_type = str(data.get("type", "")).lower()
    if problem_type not in {"choice", "flag"}:
        raise ValueError("type must be choice or flag")
    raw_options = data.get("options", [])
    if not isinstance(raw_options, list):
        raise ValueError("options must be an array")
    problem = {
        "type": problem_type,
        "title": unicodedata.normalize("NFC", str(data.get("title", "")).strip()),
        "prompt": unicodedata.normalize("NFC", str(data.get("prompt", "")).strip()),
        "answer": unicodedata.normalize("NFC", str(data.get("answer", "")).strip()),
        "options": [unicodedata.normalize("NFC", str(value).strip())
                    for value in raw_options],
    }
    problem["options"] = [value for value in problem["options"] if value]
    for key in ("title", "prompt", "answer"):
        value = problem[key]
        if not value or "\0" in value or len(value.encode("utf-8")) > PROBLEM_LIMITS[key]:
            raise ValueError(f"{key} must be 1-{PROBLEM_LIMITS[key]} UTF-8 bytes")
    if not problem["title"].isascii():
        raise ValueError("title must be ASCII for the OLED font")
    if len(problem["options"]) > 4:
        raise ValueError("options must contain at most 4 items")
    for option in problem["options"]:
        if "\0" in option or len(option.encode("utf-8")) > PROBLEM_LIMITS["option"]:
            raise ValueError("each option must be 1-23 UTF-8 bytes")
        if not option.isascii():
            raise ValueError("options must be ASCII for the OLED font")
    if problem_type == "choice":
        if len(problem["options"]) < 2:
            raise ValueError("choice problems require 2-4 options")
        if not problem["answer"].isdigit() or not 1 <= int(problem["answer"]) <= len(problem["options"]):
            raise ValueError("choice answer must be an option number")
    return problem


def encode_field(value):
    return base64.b64encode(value.encode("utf-8")).decode("ascii") or "-"


def problem_command(index, data):
    problem = normalize_problem(data)
    options = problem["options"] + [""] * (4 - len(problem["options"]))
    fields = [
        "problem set",
        str(index),
        "C" if problem["type"] == "choice" else "F",
        str(len(problem["options"])),
        *(encode_field(problem[key]) for key in ("title", "prompt", "answer")),
        *(encode_field(option) for option in options),
    ]
    command = "\t".join(fields)
    if len(command.encode("utf-8")) > BLE_COMMAND_MAX:
        raise ValueError("problem payload is too large")
    return command


def parse_problem_line(line):
    parts = line.split("\t")
    if len(parts) != 11 or parts[0] != "PROBLEM":
        raise ValueError("invalid problem field count")
    index = int(parts[1])
    option_count = int(parts[3])

    def decode(value):
        return "" if value == "-" else base64.b64decode(value, validate=True).decode("utf-8")

    problem = normalize_problem({
        "type": "choice" if parts[2] == "C" else "flag",
        "title": decode(parts[4]),
        "prompt": decode(parts[5]),
        "answer": decode(parts[6]),
        "options": [decode(value) for value in parts[7:11]][:option_count],
    })
    return index, problem


def command_chunks(command):
    payload = command.encode("utf-8")
    if not payload or len(payload) > BLE_COMMAND_MAX:
        raise ValueError(f"command must be 1-{BLE_COMMAND_MAX} UTF-8 bytes")
    payload += b"\n"
    return [payload[offset:offset + 20] for offset in range(0, len(payload), 20)]


def self_test():
    assert auth_tag("test-key", "AEGIS-112233445566", "89ABCDEF") == "22D55E4B05C38F"
    sample = {"type": "choice", "title": "Q", "prompt": "Pick", "answer": "2", "options": ["A", "B"]}
    command = problem_command(1, sample)
    assert command.startswith("problem set\t1\tC\t2\t")
    response = "PROBLEM\t" + "\t".join(command.split("\t")[1:])
    assert parse_problem_line(response) == (1, sample)
    flag = {"type": "flag", "title": "F", "prompt": "Submit", "answer": "Aegis{1}",
            "options": ["OLED view 1", "OLED view 2"]}
    flag_command = problem_command(2, flag)
    flag_response = "PROBLEM\t" + "\t".join(flag_command.split("\t")[1:])
    assert parse_problem_line(flag_response) == (2, flag)
    assert normalize_problem({**flag, "prompt": "한글"})["prompt"] == "한글"
    assert b"".join(command_chunks("Aegis{긴_FLAG_1234567890}")) == "Aegis{긴_FLAG_1234567890}\n".encode()
    try:
        normalize_problem({**sample, "answer": "3"})
    except ValueError:
        pass
    else:
        raise AssertionError("invalid choice answer accepted")
    try:
        normalize_problem({**sample, "title": "한글"})
    except ValueError:
        pass
    else:
        raise AssertionError("non-ASCII OLED title accepted")
    print("bridge protocol self-test: OK")


if __name__ == "__main__" and "--self-test" in sys.argv:
    self_test()
    raise SystemExit(0)

from aiohttp import web
from bleak import BleakClient, BleakScanner

sessions = {}


class BadgeSession:
    def __init__(self, device):
        self.device = device
        self.id = device.name or device.address
        self.client = None
        self.online = False
        self.authenticated = False
        self.status = {}
        self.last_seen = 0.0
        self.buffer = bytearray()
        self.lines = deque(maxlen=400)
        self.sequence = 0
        self.write_lock = asyncio.Lock()
        self.problem_waiters = {}
        self.task = None

    def log(self, text):
        self.sequence += 1
        self.lines.append({
            "seq": self.sequence,
            "at": time.strftime("%H:%M:%S"),
            "text": text,
        })

    def notification(self, _sender, data):
        self.buffer.extend(data)
        while b"\n" in self.buffer:
            raw, _, rest = self.buffer.partition(b"\n")
            self.buffer = bytearray(rest)
            self.handle_line(raw.decode("utf-8", "replace").strip())

    def handle_line(self, line):
        if not line:
            return
        self.last_seen = time.time()
        if line == "CLEAR":
            return
        if line.startswith("PROBLEM\t"):
            try:
                index, problem = parse_problem_line(line)
                waiter = self.problem_waiters.pop(index, None)
                if waiter and not waiter.done():
                    waiter.set_result(problem)
            except (UnicodeDecodeError, ValueError, binascii.Error) as error:
                self.log(f"ERR invalid problem data: {error}")
            return
        if line.startswith("STATUS "):
            try:
                self.status = json.loads(line[7:])
                self.id = self.status.get("id", self.id)
            except json.JSONDecodeError:
                self.log("ERR invalid status JSON")
            return

        self.log(line)
        if line.startswith("HELLO "):
            parts = line.split()
            if len(parts) == 3:
                self.id = parts[1]
                tag = auth_tag(ADMIN_KEY, parts[1], parts[2])
                asyncio.create_task(self.send_raw(f"a {tag}"))
        elif line == "AUTH OK":
            self.authenticated = True

    def disconnected(self, _client):
        self.online = False
        self.authenticated = False
        self.client = None
        self.log("[disconnected]")

    async def send_raw(self, command):
        if not self.client or not self.client.is_connected:
            raise RuntimeError("badge is offline")
        async with self.write_lock:
            for chunk in command_chunks(command):
                await self.client.write_gatt_char(
                    RX_UUID, chunk, response=True
                )

    async def request_problem(self, index, command):
        previous = self.problem_waiters.pop(index, None)
        if previous and not previous.done():
            previous.cancel()
        waiter = asyncio.get_running_loop().create_future()
        self.problem_waiters[index] = waiter
        try:
            await self.send_raw(command)
            return await asyncio.wait_for(waiter, timeout=5)
        finally:
            if self.problem_waiters.get(index) is waiter:
                self.problem_waiters.pop(index, None)

    async def run(self):
        while True:
            try:
                async with BleakClient(
                    self.device, disconnected_callback=self.disconnected
                ) as client:
                    self.client = client
                    self.online = True
                    self.authenticated = False
                    self.last_seen = time.time()
                    self.log("[connected]")
                    await client.start_notify(TX_UUID, self.notification)
                    await self.send_raw("hello")
                    while client.is_connected:
                        await asyncio.sleep(2)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.online = False
                self.authenticated = False
                self.client = None
                self.log(f"[connection error] {error}")
            await asyncio.sleep(2)


async def scan_loop():
    while True:
        try:
            found = await BleakScanner.discover(timeout=3, return_adv=True)
            for device, advertisement in found.values():
                name = device.name or advertisement.local_name or ""
                uuids = {value.lower() for value in advertisement.service_uuids}
                if not name.startswith("AEGIS-") and SERVICE_UUID not in uuids:
                    continue
                if device.address in sessions:
                    sessions[device.address].device = device
                    continue
                session = BadgeSession(device)
                sessions[device.address] = session
                session.task = asyncio.create_task(session.run())
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"BLE scan error: {error}", file=sys.stderr)
        await asyncio.sleep(2)


def badge_from_request(request, require_ready=False):
    badge_id = request.match_info["badge_id"]
    badge = next((item for item in sessions.values() if item.id == badge_id), None)
    if badge is None:
        raise web.HTTPNotFound(text="unknown badge")
    if require_ready and not (badge.online and badge.authenticated):
        raise web.HTTPConflict(text="badge is not ready")
    return badge


def problem_index(request):
    index = int(request.match_info["index"])
    if not 1 <= index <= 4:
        raise ValueError("only problems 1-4 are editable")
    return index


async def request_command(request):
    data = await request.json()
    if not isinstance(data, dict):
        raise ValueError("request body must be a JSON object")
    command = data.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("command must be a non-empty string")
    return command.strip()


async def bulk_result(operation, completed_key):
    badges = [badge for badge in sessions.values()
              if badge.online and badge.authenticated]
    if not badges:
        raise web.HTTPConflict(text="no authenticated badges are online")
    results = await asyncio.gather(
        *(operation(badge) for badge in badges), return_exceptions=True
    )
    failures = {
        badge.id: str(result)
        for badge, result in zip(badges, results)
        if isinstance(result, Exception)
    }
    return web.json_response({
        "ok": not failures,
        completed_key: len(badges) - len(failures),
        "total": len(badges),
        "failures": failures,
    })


async def dashboard_page(_request):
    response = web.FileResponse(DASHBOARD_PATH)
    response.headers["Cache-Control"] = "no-store"
    return response


async def favicon(_request):
    return web.FileResponse(FAVICON_PATH)


async def badges_api(_request):
    now = time.time()
    badges = []
    for badge in sorted(sessions.values(), key=lambda item: item.id):
        badges.append({
            "id": badge.id,
            "online": badge.online,
            "authenticated": badge.authenticated,
            "lastSeenSeconds": round(max(0, now - badge.last_seen), 1)
            if badge.last_seen else None,
            "status": badge.status,
        })
    return web.json_response(badges)


async def command_api(request):
    badge = badge_from_request(request, require_ready=True)
    try:
        command = await request_command(request)
        await badge.send_raw(command)
        badge.log(f"> {command}")
    except (KeyError, TypeError, UnicodeEncodeError, ValueError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error
    except RuntimeError as error:
        raise web.HTTPConflict(text=str(error)) from error
    return web.json_response({"ok": True})


async def bulk_command_api(request):
    try:
        command = await request_command(request)
        if command not in {"reset", "reboot"}:
            raise ValueError("bulk command must be reset or reboot")
    except (KeyError, TypeError, ValueError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error
    async def send(badge):
        await badge.send_raw(command)
        badge.log(f"> {command} [ALL ONLINE]")

    return await bulk_result(send, "succeeded")


async def console_api(request):
    badge = badge_from_request(request)
    try:
        after = int(request.query.get("after", "0"))
    except ValueError as error:
        raise web.HTTPBadRequest(text="after must be an integer") from error
    return web.json_response({
        "lines": [line for line in badge.lines if line["seq"] > after],
        "last": badge.sequence,
    })


async def problem_api(request):
    badge = badge_from_request(request, require_ready=True)
    try:
        index = problem_index(request)
        if request.method == "GET":
            command = f"problem get {index}"
        else:
            command = problem_command(index, await request.json())
        problem = await badge.request_problem(index, command)
    except (TypeError, KeyError, ValueError, UnicodeEncodeError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error
    except asyncio.TimeoutError as error:
        raise web.HTTPGatewayTimeout(text="badge did not return problem data") from error
    except RuntimeError as error:
        raise web.HTTPConflict(text=str(error)) from error
    return web.json_response(problem)


async def bulk_problem_api(request):
    try:
        index = problem_index(request)
        command = problem_command(index, await request.json())
    except (TypeError, KeyError, ValueError, UnicodeEncodeError) as error:
        raise web.HTTPBadRequest(text=str(error)) from error
    return await bulk_result(
        lambda badge: badge.request_problem(index, command),
        "updated",
    )


def create_app():
    app = web.Application()
    app.router.add_get("/", dashboard_page)
    app.router.add_get("/favicon.svg", favicon)
    app.router.add_get("/api/badges", badges_api)
    app.router.add_post("/api/badges/command", bulk_command_api)
    app.router.add_put("/api/badges/problems/{index}", bulk_problem_api)
    app.router.add_post("/api/badges/{badge_id}/command", command_api)
    app.router.add_get("/api/badges/{badge_id}/console", console_api)
    app.router.add_get("/api/badges/{badge_id}/problems/{index}", problem_api)
    app.router.add_put("/api/badges/{badge_id}/problems/{index}", problem_api)
    return app


async def main():
    if ADMIN_KEY == DEFAULT_ADMIN_KEY:
        print("WARNING: using development BLE admin key", file=sys.stderr)
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8080)
    await site.start()
    print("AEGIS dashboard: http://127.0.0.1:8080")
    scanner = asyncio.create_task(scan_loop())
    try:
        await asyncio.Event().wait()
    finally:
        tasks = [scanner, *(badge.task for badge in sessions.values()
                            if badge.task)]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
