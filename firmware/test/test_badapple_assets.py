import importlib.util
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "encode_badapple_music", ROOT / "tools" / "encode_badapple_music.py")
encoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encoder)


def track(events):
    body = b"".join(events) + b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + body


def records(binary, part):
    counts = struct.unpack_from("<3I", binary, 8)
    offsets = struct.unpack_from("<3I", binary, 20)
    return [struct.unpack_from("<IB", binary, offsets[part] + i * 5)
            for i in range(counts[part])]


def test_encoder():
    tracks = [track([b"\x00\xff\x51\x03\x07\xa1\x20"])]
    for index in range(1, 14):
        if index == 3:
            events = [b"\x00\x92\x28\x60", b"\x87\x40\x82\x28\x00"]
        elif index == 5:
            events = [b"\x00\x94\x4b\x60", b"\x87\x40\x84\x4b\x00"]
        elif index == 6:
            events = [b"\x83\x60\x96\x46\x60", b"\x83\x60\x86\x46\x00"]
        elif index == 8:
            events = [b"\x83\x60\x92\x3c\x60", b"\x83\x60\x82\x3c\x00"]
        else:
            events = []
        tracks.append(track(events))
    midi = b"MThd" + struct.pack(">IHHH", 6, 1, 14, 960) + b"".join(tracks)
    binary, counts = encoder.encode(midi)
    assert binary[:4] == b"BAM1"
    assert counts == [3, 3, 2]
    assert records(binary, 0) == [(0, 40), (250, 70), (500, 0)]
    assert records(binary, 1) == [(0, 0), (250, 66), (500, 0)]
    assert records(binary, 2) == [(0, 40), (500, 0)]
    assert encoder.harmony_note(75, 6) == 71
    assert encoder.harmony_note(79, 9) == 76

    drum_tracks = [track([]) for _ in range(14)]
    drum_tracks[1] = track([b"\x00\x99\x23\x60", b"\x83\x60\x89\x23\x00",
                            b"\x00\x99\x23\x60", b"\x83\x60\x89\x23\x00"])
    drum_tracks[6] = track([b"\x87\x40\x96\x46\x60", b"\x83\x60\x86\x46\x00"])
    drum_midi = b"MThd" + struct.pack(">IHHH", 6, 1, 14, 960) + b"".join(drum_tracks)
    binary, _ = encoder.encode(drum_midi)
    assert records(binary, 0) == [(0, 35), (45, 0), (250, 35), (295, 0),
                                  (500, 70), (750, 0)]


def test_local_assets():
    video = ROOT / "badapple_data" / "video.rle"
    music = ROOT / "badapple_data" / "music.bin"
    if not video.exists() and not music.exists():
        return
    assert video.exists() and music.exists()
    data = video.read_bytes()
    pos = decoded = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        if byte in (0x55, 0xaa):
            assert pos < len(data)
            count = data[pos]
            pos += 1
            if count & 0x80:
                assert pos < len(data)
                count = (count & 127) | (data[pos] << 7)
                pos += 1
            decoded += count or 1
        else:
            decoded += 1
    assert decoded == 6573 * 1024
    tune = music.read_bytes()
    assert tune[:4] == b"BAM1"
    assert struct.unpack_from("<I", tune, 4)[0] == 219100
    for part in range(3):
        line = records(tune, part)
        assert line and all(at <= 219100 and note <= 127 for at, note in line)
        assert line == sorted(line)
        if part == 0:
            assert max(line[i + 1][0] - at for i, (at, note) in
                       enumerate(line[:-1]) if at < 13913 and note) <= 45
            intro = [note for at, note in line if 13913 <= at < 27826]
            assert intro and max(intro) <= 44
        if part == 1:
            assert (27826, 71) in line
    lead = records(tune, 0)
    harmony = records(tune, 1)
    lead_note = harmony_note = 0
    for at in sorted({time for time, _ in lead + harmony}):
        lead_note = next((note for time, note in reversed(lead) if time <= at), 0)
        harmony_note = next((note for time, note in reversed(harmony) if time <= at), 0)
        if lead_note and harmony_note:
            assert (lead_note - harmony_note) % 12 != 0


if __name__ == "__main__":
    test_encoder()
    test_local_assets()
    print("Bad Apple assets and MIDI encoder: OK")
