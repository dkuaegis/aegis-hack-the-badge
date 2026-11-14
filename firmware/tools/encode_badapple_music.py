"""Convert the Bad Apple MIDI arrangement to three monophonic badge parts."""

import argparse
import bisect
import struct
from pathlib import Path

VIDEO_FRAMES = 6573
VIDEO_FPS = 30
# Track numbers in rkk-2s/bad-apple's Alstroemeria Records arrangement.
# The chromatic sweep on track 5 is a sound effect; it masks the intro on a buzzer.
# Track 8 doubles the bass by two octaves, so it is not a distinct harmony.
# Melody falls back to intro bass/drums before the lead enters at 28 seconds.
PARTS = ((6, 9, 3), (6, 9), (3, 10, 11, 7))


def harmony_note(note, track):
    # Follow the D-sharp minor lead, then the G-major outro, a third below.
    scale = {1, 3, 5, 6, 8, 10, 11} if track == 6 else {0, 2, 4, 6, 7, 9, 11}
    below = [candidate for candidate in range(note - 1, note - 12, -1)
             if candidate % 12 in scale]
    return below[1]


def vlq(data, pos):
    value = 0
    for _ in range(4):
        if pos >= len(data):
            raise ValueError("truncated MIDI variable-length value")
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 127)
        if byte < 128:
            return value, pos
    raise ValueError("MIDI variable-length value too long")


def parse_midi(data):
    if data[:4] != b"MThd" or len(data) < 14:
        raise ValueError("not a MIDI file")
    header_size = int.from_bytes(data[4:8], "big")
    fmt, tracks, division = struct.unpack_from(">HHH", data, 8)
    if fmt != 1 or division & 0x8000 or division == 0:
        raise ValueError("expected type-1 MIDI with ticks per quarter note")
    pos = 8 + header_size
    notes, tempos = [], [(0, 500000)]
    for track in range(tracks):
        if data[pos:pos + 4] != b"MTrk" or pos + 8 > len(data):
            raise ValueError("missing MIDI track")
        size = int.from_bytes(data[pos + 4:pos + 8], "big")
        chunk = data[pos + 8:pos + 8 + size]
        if len(chunk) != size:
            raise ValueError("truncated MIDI track")
        pos += 8 + size
        at = cursor = running = 0
        while cursor < size:
            delta, cursor = vlq(chunk, cursor)
            at += delta
            status = chunk[cursor]
            if status & 0x80:
                cursor += 1
                if status < 0xF0:
                    running = status
            elif running:
                status = running
            else:
                raise ValueError("MIDI running status without a prior event")
            if status == 0xFF:
                kind = chunk[cursor]
                cursor += 1
                length, cursor = vlq(chunk, cursor)
                payload = chunk[cursor:cursor + length]
                if len(payload) != length:
                    raise ValueError("truncated MIDI meta event")
                cursor += length
                if kind == 0x51 and length == 3:
                    tempos.append((at, int.from_bytes(payload, "big")))
            elif status in (0xF0, 0xF7):
                length, cursor = vlq(chunk, cursor)
                cursor += length
            else:
                kind = status & 0xF0
                length = 1 if kind in (0xC0, 0xD0) else 2
                if cursor + length > size:
                    raise ValueError("truncated MIDI channel event")
                note = chunk[cursor]
                velocity = chunk[cursor + 1] if length == 2 else 0
                cursor += length
                if kind in (0x80, 0x90):
                    notes.append((at, track, note, kind == 0x90 and velocity > 0))
    tempos.sort(key=lambda item: item[0])
    starts, elapsed, rates = [], [], []
    for tick, rate in tempos:
        if starts and tick == starts[-1]:
            rates[-1] = rate
        else:
            us = 0 if not starts else elapsed[-1] + (tick - starts[-1]) * rates[-1] // division
            starts.append(tick)
            elapsed.append(us)
            rates.append(rate)

    def millis(tick):
        index = bisect.bisect_right(starts, tick) - 1
        return (elapsed[index] + (tick - starts[index]) * rates[index] // division + 500) // 1000

    return [(millis(t), t, track, note, on) for t, track, note, on in notes]


def encode(data):
    events = sorted(parse_midi(data))
    if not any(track == 6 and on for _, _, track, _, on in events):
        raise ValueError("Bad Apple melody track missing")
    intro_end = min(at for at, _, track, _, on in events
                    if on and track in PARTS[0])
    active = {}
    parts = [[], [], []]
    index = 0
    while index < len(events):
        at = events[index][0]
        while index < len(events) and events[index][0] == at:
            _, _, track, note, on = events[index]
            key = (track, note)
            active[key] = max(0, active.get(key, 0) + (1 if on else -1))
            index += 1
        for part, priority in enumerate(PARTS):
            pitch = 0
            for track in priority:
                sounding = [note for (source, note), count in active.items()
                            if source == track and count]
                if sounding:
                    pitch = min(sounding) if part == 2 else max(sounding)
                    if part == 1:
                        pitch = harmony_note(pitch, track)
                    break
            if not parts[part] or parts[part][-1][1] != pitch:
                parts[part].append((at, pitch))
    # The MIDI kick lasts until the next kick; a buzzer needs short hits, not a held note.
    drum_hits = sorted({at for at, _, track, _, on in events
                        if track == 1 and on and at < intro_end})
    parts[0] = ([(at, 35) for at in drum_hits] +
                [(min(at + 45, intro_end), 0) for at in drum_hits] +
                [(at, note) for at, note in parts[0] if at >= intro_end])
    parts[0].sort()
    header_size = 32
    offsets = []
    offset = header_size
    for part in parts:
        offsets.append(offset)
        offset += len(part) * 5
    result = bytearray(struct.pack("<4sI3I3I", b"BAM1", VIDEO_FRAMES * 1000 // VIDEO_FPS,
                                   *(len(part) for part in parts), *offsets))
    for part in parts:
        for at, note in part:
            result.extend(struct.pack("<IB", at, note))
    assert len(result) == offset
    return bytes(result), [len(part) for part in parts]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    binary, counts = encode(args.source.read_bytes())
    args.output.write_bytes(binary)
    print(f"{len(binary)} bytes; notes per part: {counts}")


if __name__ == "__main__":
    main()
