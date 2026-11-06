"""USB CDC adapter for the badge's ESP-NOW Morse v4 protocol."""

import asyncio
import time
from collections import deque

CODES = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", (
    ".-", "-...", "-.-.", "-..", ".", "..-.", "--.", "....", "..", ".---",
    "-.-", ".-..", "--", "-.", "---", ".--.", "--.-", ".-.", "...", "-",
    "..-", "...-", ".--", "-..-", "-.--", "--..", "-----", ".----", "..---",
    "...--", "....-", ".....", "-....", "--...", "---..", "----.",
)))
LETTERS = {code: letter for letter, code in CODES.items()}


def badge_label(sender, number):
    if type(number) is not int or not (0 <= number <= 999 or number == 65535):
        raise ValueError("invalid badge number")
    return "ADMIN" if number == 65535 else f"BADGE #{number:02d}" if number else sender


def serial_ports():
    from serial.tools import list_ports
    return [{"port": port.device, "description": port.description or "Serial device",
             "serialNumber": port.serial_number or ""}
            for port in sorted(list_ports.comports())]


def normalize_text(value):
    if not isinstance(value, str):
        raise ValueError("text must be A-Z, 0-9 and spaces (1-40 characters)")
    value = value.strip().upper()
    if not 1 <= len(value) <= 40 or any(c not in CODES and c != " " for c in value):
        raise ValueError("text must be A-Z, 0-9 and spaces (1-40 characters)")
    return " ".join(value.split())


def transmission(text):
    for word_index, word in enumerate(text.split()):
        if word_index:
            yield " ", 0, 0.4  # 300ms letter gap + 400ms = 700ms word gap
        for letter in word:
            code = CODES[letter]
            for index, symbol in enumerate(code):
                duration = 100 if symbol == "." else 300
                gap = 300 if index == len(code) - 1 else 100
                yield symbol, duration, (duration + gap) / 1000
            yield "/", 0, 0
    yield " ", 0, 0.4


class MorseBridge:
    def __init__(self, port=None, channel=1):
        if type(channel) is not int or not 1 <= channel <= 13:
            raise ValueError("channel must be 1-13")
        self.port = port
        self.channel = channel
        self.online = False
        self.error = "" if port else "Select a Morse adapter device to connect"
        self.serial = None
        self.reply = None
        self.operation = asyncio.Lock()
        self.port_changed = asyncio.Event()
        self.lines = {}
        self.events = deque(maxlen=100)
        self.sequence = 0

    def log(self, text):
        self.sequence += 1
        self.events.append({"seq": self.sequence, "text": text})

    def finish_letter(self, state):
        if state["symbols"]:
            state["text"] = (state["text"] + LETTERS.get(state["symbols"], "?"))[-80:]
            state["symbols"] = ""

    def receive(self, line):
        parts = line.split()
        if len(parts) != 5 or parts[0] != "RX" or len(parts[1]) != 6 or any(
                c not in "0123456789ABCDEF" for c in parts[1]):
            raise ValueError("invalid RX sender")
        sender = parts[1]
        number = int(parts[4])
        label = badge_label(sender, number)
        symbol, duration = int(parts[2]), int(parts[3])
        if not ((symbol in (46, 45) and 30 <= duration <= 2000) or
                (symbol in (47, 32) and duration == 0)):
            raise ValueError("invalid RX element")
        self.expire()
        if sender not in self.lines:
            if len(self.lines) >= 32:
                del self.lines[next(iter(self.lines))]
            self.lines[sender] = {"text": "", "symbols": "", "end": 0.0}
        state = self.lines[sender]
        state["displayName"] = label
        if symbol in (46, 45):
            state["symbols"] = (state["symbols"] + chr(symbol))[-7:]
            state["end"] = time.monotonic() + duration / 1000
        else:
            self.finish_letter(state)
            if symbol == 32 and state["text"] and not state["text"].endswith(" "):
                state["text"] = (state["text"] + " ")[-80:]

    def expire(self):
        now = time.monotonic()
        for state in self.lines.values():
            if now - state["end"] >= 0.3:
                self.finish_letter(state)
            if now - state["end"] >= 0.7 and state["text"] and not state["text"].endswith(" "):
                state["text"] = (state["text"] + " ")[-80:]

    def snapshot(self):
        self.expire()
        return {"online": self.online, "port": self.port, "channel": self.channel,
                "displayName": "ADMIN",
                "busy": self.operation.locked(), "error": self.error,
                "received": [{"sender": sender, "displayName": state["displayName"],
                              "text": state["text"],
                              "symbols": state["symbols"]}
                             for sender, state in self.lines.items()],
                "events": list(self.events)}

    async def read_loop(self, connection):
        buffer = bytearray()
        dropping = False
        try:
            while True:
                data = await asyncio.to_thread(connection.read, 256)
                for byte in data:
                    if byte == 10:
                        line = buffer.decode("ascii", "replace").strip()
                        buffer.clear()
                        if not dropping:
                            if line.startswith("RX "):
                                try:
                                    self.receive(line)
                                except ValueError as error:
                                    self.log(str(error))
                            elif line.startswith(("READY ", "OK ", "ERR ")):
                                if self.reply and not self.reply.done():
                                    self.reply.set_result(line)
                        dropping = False
                    elif not dropping:
                        buffer.append(byte)
                        if len(buffer) > 128:
                            buffer.clear()
                            dropping = True
        except Exception as error:
            self.online = False
            self.error = str(error)
            if self.reply and not self.reply.done():
                self.reply.set_exception(RuntimeError(self.error))
            raise

    async def request(self, command, expected):
        if self.serial is None:
            raise RuntimeError("Morse adapter is offline")
        self.reply = asyncio.get_running_loop().create_future()
        try:
            await asyncio.to_thread(self.serial.write, (command + "\n").encode("ascii"))
            response = await asyncio.wait_for(self.reply, 3)
            if response != expected and not (expected == "READY 4 " and response.startswith(expected)):
                raise RuntimeError(response)
            return response
        except Exception as error:
            self.online = False
            self.error = str(error) or "Morse adapter timed out"
            if command == "HELLO":
                self.error = f"Morse adapter check failed: {self.error}. Check the device and adapter firmware."
            # Discard this serial session so a late reply cannot ACK a new request.
            if self.serial:
                self.serial.close()
            raise RuntimeError(self.error) from error
        finally:
            self.reply = None

    async def set_port(self, port):
        if port is not None:
            if not isinstance(port, str) or not port:
                raise ValueError("port must be a device name or null to disconnect")
            if port not in {item["port"] for item in await asyncio.to_thread(serial_ports)}:
                raise ValueError("device is no longer available; refresh the device list")
        if self.operation.locked():
            raise RuntimeError("Morse adapter is busy; wait for the current operation to finish")
        async with self.operation:
            self.port = port
            self.online = False
            self.error = "Connecting to selected device" if port else "Select a Morse adapter device to connect"
            self.lines.clear()
            self.port_changed.set()
            if self.serial:
                self.serial.close()
            self.log(f"DEVICE {port}" if port else "DEVICE DISCONNECTED")

    async def set_channel(self, channel):
        if type(channel) is not int or not 1 <= channel <= 13:
            raise ValueError("channel must be 1-13")
        if not self.online or self.operation.locked():
            raise RuntimeError("Morse adapter is offline or busy")
        async with self.operation:
            response = await self.request(f"CHANNEL {channel}", "READY 4 ")
            if response.split()[2] != str(channel):
                raise RuntimeError("adapter channel mismatch")
            self.channel = channel
            self.lines.clear()
            self.log(f"CHANNEL {channel}")

    async def send_text(self, value):
        text = normalize_text(value)
        if not self.online or self.operation.locked():
            raise RuntimeError("Morse adapter is offline or busy")
        async with self.operation:
            self.log(f"TX CH{self.channel}: {text}")
            try:
                for symbol, duration, delay in transmission(text):
                    started = time.monotonic()
                    await self.request(f"TX {ord(symbol)} {duration}", "OK TX")
                    await asyncio.sleep(max(0, delay - (time.monotonic() - started)))
            except Exception:
                self.log("TX FAILED (message may be partially sent)")
                raise
            self.log("TX COMPLETE (radio sent; receiver delivery is not acknowledged)")

    async def run(self):
        import serial
        while True:
            if not self.port:
                self.error = "Select a Morse adapter device to connect"
                await self.port_changed.wait()
                self.port_changed.clear()
                continue
            self.port_changed.clear()
            port = self.port
            connection = None
            reader = None
            try:
                connection = serial.Serial(port, 115200, timeout=0.05, write_timeout=0.5)
                self.serial = connection
                reader = asyncio.create_task(self.read_loop(connection))
                async with self.operation:
                    await self.request("HELLO", "READY 4 ")
                    response = await self.request(f"CHANNEL {self.channel}", "READY 4 ")
                    if response.split()[2] != str(self.channel):
                        raise RuntimeError("adapter channel mismatch")
                    self.lines.clear()
                    self.online = True
                    self.error = ""
                    self.log(f"CONNECTED {port} CH{self.channel}")
                await reader
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if port == self.port:
                    self.error = str(error)
                    self.log(f"DISCONNECTED {port}: {error}")
            finally:
                self.online = False
                self.serial = None
                if connection:
                    connection.close()
                if reader:
                    reader.cancel()
                    await asyncio.gather(reader, return_exceptions=True)
            if not self.port_changed.is_set():
                try:
                    await asyncio.wait_for(self.port_changed.wait(), 2)
                except asyncio.TimeoutError:
                    pass
