"""Standard MIDI File export (SMF format 0), with no external dependencies."""

import struct

from .models import clamp
from .performance import Performance

TICKS_PER_BEAT = 480


def _var_len(value: int) -> bytes:
    """MIDI variable-length quantity (7 bits per byte, most significant first)."""
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def midi_bytes(perf: Performance, bpm: int) -> bytes:
    events = []  # (tick, order, bytes): note-offs go before note-ons on the same tick
    for note in perf.notes:
        on = round(note.start * TICKS_PER_BEAT)
        off = max(on + 1, round((note.start + note.dur) * TICKS_PER_BEAT))
        events.append((on, 1, bytes([0x90, note.midi, clamp(note.velocity, 1, 127)])))
        events.append((off, 0, bytes([0x80, note.midi, 0])))
    events.sort(key=lambda e: e[:2])

    tempo = round(60_000_000 / clamp(bpm, 30, 300))  # microseconds per quarter note
    track = bytearray()
    track += b"\x00\xff\x51\x03" + struct.pack(">I", tempo)[1:]
    track += b"\x00\xff\x58\x04\x04\x02\x18\x08"       # 4/4 time
    track += b"\x00\xc0\x00"                           # program 0: acoustic grand piano
    last = 0
    for tick, _, data in events:
        track += _var_len(tick - last) + data
        last = tick
    end = round(perf.total_beats * TICKS_PER_BEAT)
    track += _var_len(max(0, end - last)) + b"\xff\x2f\x00"

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, TICKS_PER_BEAT)
    return header + b"MTrk" + struct.pack(">I", len(track)) + bytes(track)


def write_midi(path: str, perf: Performance, bpm: int) -> None:
    with open(path, "wb") as f:
        f.write(midi_bytes(perf, bpm))
