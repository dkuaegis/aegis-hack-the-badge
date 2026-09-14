"""Run with admin/.venv/bin/python admin/test_bridge.py; no hardware or live DB."""

import asyncio
import os
import queue
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from aiohttp.test_utils import TestClient, TestServer
from serial.tools.list_ports_common import ListPortInfo
from morse import CODES, LETTERS, MorseBridge, normalize_text, transmission


class Adapter:
    """Serial byte transport emulator, including partial lines and radio RX."""
    def __init__(self, device="TEST"):
        self.device = device
        self.input = queue.Queue()
        self.closed = False
        self.channel = 1
        self.commands = []
        self.no_ack = False

    def read(self, _size):
        if self.closed:
            raise OSError("USB disconnected")
        try:
            return self.input.get(timeout=0.02)
        except queue.Empty:
            return b""

    def write(self, data):
        if self.closed:
            raise OSError("USB disconnected")
        command = data.decode().strip()
        self.commands.append(command)
        if command.startswith("CHANNEL "):
            self.channel = int(command.split()[1])
        if self.device == "BADGE":
            response = b"ERR unknown command\n"
        elif command == "HELLO" or command.startswith("CHANNEL "):
            response = f"READY 3 {self.channel} 112233\n".encode()
        elif command.startswith("TX "):
            _, symbol, duration = command.split()
            response = f"RX AABBCC {symbol} {duration}\n".encode()
            if not self.no_ack:
                response += b"OK TX\n"
        else:
            response = b"ERR command\n"
        self.input.put(response[:4])
        self.input.put(response[4:])
        return len(data)

    def close(self):
        self.closed = True


async def wait_until(predicate):
    async def wait():
        while not predicate():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(wait(), 5)


async def test_morse():
    assert len(CODES) == len(LETTERS) == 36
    assert normalize_text(" cq  6 ") == "CQ 6"
    for invalid in ("", "?", "A\nB", "A" * 41, None):
        try:
            normalize_text(invalid)
            raise AssertionError("invalid text accepted")
        except ValueError:
            pass
    assert list(transmission("E T")) == [
        (".", 100, .4), ("/", 0, 0), (" ", 0, .4),
        ("-", 300, .6), ("/", 0, 0), (" ", 0, .4),
    ]
    # Multi-element letters and word gaps round-trip at the protocol's timing.
    decoder = MorseBridge()
    with patch("morse.time.monotonic", return_value=100.0) as clock:
        for symbol, duration, delay in transmission("CQ AEGIS 0123456789"):
            decoder.receive(f"RX ABCDEF {ord(symbol)} {duration}")
            clock.return_value += delay
        assert decoder.snapshot()["received"][0]["text"] == "CQ AEGIS 0123456789 "
    radio = MorseBridge("TEST", 6)
    adapters = []
    def connect(*_args, **_kwargs):
        adapter = Adapter()
        adapters.append(adapter)
        return adapter
    with patch("serial.Serial", side_effect=connect):
        task = asyncio.create_task(radio.run())
        try:
            await wait_until(lambda: radio.online)
            assert adapters[-1].channel == 6
            await radio.set_channel(13)
            assert radio.channel == adapters[-1].channel == 13
            send = asyncio.create_task(radio.send_text("E T"))
            await wait_until(lambda: radio.operation.locked())
            try:
                await radio.set_channel(1)
                raise AssertionError("channel changed while transmitting")
            except RuntimeError:
                pass
            await send
            assert radio.snapshot()["received"][0]["text"].strip() == "E T"
            await radio.set_channel(1)
            assert not radio.lines
            # Idle-gap decoding when the explicit boundary packet is lost.
            radio.receive("RX ABCDEF 45 300")
            radio.lines["ABCDEF"]["end"] -= 1
            assert radio.snapshot()["received"][0]["text"] == "T "
            for invalid in ("RX ABCDEF 32 100", "RX ABCDEF 46 0", "RX BAD 46 100"):
                try:
                    radio.receive(invalid)
                    raise AssertionError("invalid packet accepted")
                except ValueError:
                    pass
            # USB unplug and automatic reconnect restore the selected channel.
            adapters[-1].close()
            await wait_until(lambda: len(adapters) == 2 and radio.online)
            assert adapters[-1].channel == 1
            adapters[-1].no_ack = True
            try:
                await radio.send_text("E")
                raise AssertionError("missing radio ACK accepted")
            except RuntimeError:
                pass
            assert any("TX FAILED" in event["text"] for event in radio.events)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert not radio.online and adapters[-1].closed


async def test_morse_devices(bridge):
    radio = MorseBridge(channel=6)
    devices = []
    for name in ("TEST2", "BADGE", "TEST1"):
        device = ListPortInfo(name)
        device.description = "USB JTAG/serial debug unit"
        device.serial_number = f"SER-{name}"
        devices.append(device)
    adapters = []

    def connect(port, *_args, **_kwargs):
        assert all(adapter.closed for adapter in adapters), "previous device is still open"
        adapter = Adapter(port)
        adapters.append(adapter)
        return adapter

    with patch("serial.tools.list_ports.comports", return_value=devices), \
            patch("serial.Serial", side_effect=connect), patch.object(bridge, "morse", radio):
        task = asyncio.create_task(radio.run())
        try:
            async with TestClient(TestServer(bridge.create_app()),
                                  headers={"Host": "127.0.0.1:8080"}) as client:
                response = await client.get("/api/morse/ports")
                assert response.status == 200
                ports = await response.json()
                assert [item["port"] for item in ports] == ["BADGE", "TEST1", "TEST2"]
                assert ports[0]["serialNumber"] == "SER-BADGE"
                assert not adapters and not task.done() # Listing never probes/open devices.
                for invalid in ("UNKNOWN", "", 42, [], "/tmp/not-a-serial-device"):
                    response = await client.post("/api/morse", json={"port": invalid})
                    assert response.status == 400
                assert not adapters

                response = await client.post("/api/morse", json={"port": "TEST1"})
                assert response.status == 200
                await wait_until(lambda: radio.online)
                assert adapters[-1].device == "TEST1" and adapters[-1].channel == 6
                send = asyncio.create_task(radio.send_text("E"))
                await wait_until(lambda: radio.operation.locked())
                for port in (None, "TEST2"):
                    response = await client.post("/api/morse", json={"port": port})
                    assert response.status == 409
                assert radio.port == "TEST1" and not adapters[-1].closed
                await send

                response = await client.post("/api/morse", json={"port": "TEST2"})
                assert response.status == 200 and adapters[0].closed
                await wait_until(lambda: radio.online and adapters[-1].device == "TEST2")
                assert adapters[-1].channel == 6 and not radio.lines
                response = await client.post("/api/morse", json={"port": None})
                assert response.status == 200 and adapters[-1].closed
                await wait_until(lambda: radio.serial is None)
                await asyncio.sleep(2.1) # Manual disconnect also disables automatic reconnect.
                assert len(adapters) == 2 and radio.port is None and not task.done()

                response = await client.post("/api/morse", json={"port": "BADGE"})
                assert response.status == 200
                await wait_until(lambda: "Morse adapter check failed" in radio.error)
                assert not radio.online and adapters[-1].commands == ["HELLO"]
                response = await client.post("/api/morse", json={"text": "E"})
                assert response.status == 409
                response = await client.post("/api/morse", json={"port": None})
                assert response.status == 200
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert not radio.online and all(adapter.closed for adapter in adapters)


async def test_scores_and_api(bridge):
    bridge.init_score_db()
    for nickname in ("A", "0123456789", " A  B "):
        assert bridge.valid_nickname(nickname)
    for nickname in ("", "   ", "ABCDEFGHIJK", "A\tB", "a", "A\nB", None):
        assert not bridge.valid_nickname(nickname)
    one = bridge.BadgeSession(SimpleNamespace(name="AEGIS-000000000001"))
    two = bridge.BadgeSession(SimpleNamespace(name="AEGIS-000000000002"))
    commands = {one.id: [], two.id: []}
    for badge in (one, two):
        async def send(command, badge=badge):
            commands[badge.id].append(command)
        badge.send_raw = send
        badge.online = badge.authenticated = True
        bridge.sessions[badge.id] = badge
    await one.sync_scores()
    assert set(commands[one.id]) == {f"score sync {game} 0 ---" for game in bridge.SCORE_GAMES}
    for game in bridge.SCORE_GAMES:
        assert bridge.store_score(one.id, game, 50, "FIRST")
        commands[two.id].clear()
        await two.handle_score(f"SCORE {game} 40")
        assert not commands[two.id] # Must compare with the other badge's record.
        await two.handle_score(f"SCORE {game} 50")
        assert not commands[two.id]
        await two.handle_score(f"SCORE {game} 60")
        assert commands[two.id] == [f"score name {game} 60"]
        await two.handle_score(f"SCORE_SUBMIT {game} 60 A B")
        assert bridge.best_scores()[game]["score"] == 60
        for badge in (one, two):
            assert f"score sync {game} 60 A B" in commands[badge.id]
        assert not bridge.store_score(two.id, game, 59, "LOW")
        assert not bridge.store_score(two.id, game, 60, "TIE")
    assert len(bridge.score_rows()) == 6 # Personal DB rows remain intact.
    # BLE chunks and line endings must preserve even leading/repeated/trailing spaces.
    two.notification(None, b"SCORE_SUBMIT flappy 70  A ")
    two.notification(None, b" B \r\n")
    await wait_until(lambda: bridge.best_scores()["flappy"]["score"] == 70)
    assert bridge.best_scores()["flappy"]["nickname"] == " A  B "
    for badge in (one, two):
        assert "score sync flappy 70  A  B " in commands[badge.id]
    for nickname in ("   ", "A\tB", "ABCDEFGHIJK"):
        await two.handle_score(f"SCORE_SUBMIT flappy 80 {nickname}")
    assert bridge.best_scores()["flappy"]["score"] == 70
    two.authenticated = False
    await two.handle_score("SCORE_SUBMIT flappy 100 BAD")
    assert bridge.best_scores()["flappy"]["score"] == 70
    with bridge.score_db() as connection:
        connection.execute("DELETE FROM scores")
    commands[one.id].clear()
    await one.sync_scores()
    assert set(commands[one.id]) == {f"score sync {game} 0 ---" for game in bridge.SCORE_GAMES}
    async with TestClient(TestServer(bridge.create_app()),
                          headers={"Host": "127.0.0.1:8080"}) as client:
        response = await client.get("/morse")
        assert response.status == 200 and "MORSE LINK" in await response.text()
        response = await client.get("/api/morse")
        assert response.status == 200 and not (await response.json())["online"]
        response = await client.post("/api/morse", json={"channel": 14})
        assert response.status == 400
        response = await client.post("/api/morse", json={"text": "CQ"})
        assert response.status == 409
        response = await client.post("/api/morse", json={"text": "?"})
        assert response.status == 400
        response = await client.get("/api/leaderboard")
        assert response.status == 200


async def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ["AEGIS_SCORE_DB"] = str(Path(directory) / "scores.db")
        os.environ.pop("AEGIS_MORSE_PORT", None)
        import bridge
        await test_scores_and_api(bridge)
        await test_morse()
        await test_morse_devices(bridge)
    print("bridge score/API/Morse transport and device selection tests: OK")


if __name__ == "__main__":
    asyncio.run(main())
