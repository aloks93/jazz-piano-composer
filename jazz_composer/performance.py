"""Performance: progression -> timed notes (comping, walking bass, bossa, humanization).

Everything is measured in beats (quarter notes); audio and MIDI convert with the BPM.
"""

import random
from bisect import bisect_right
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .models import PlayChord, clamp
from .voicing import chord_to_midi_notes, nearest_midi_for_pc

FEEL_BLOCK = "Block (sustained chord)"
FEEL_SWING = "Swing (comping)"
FEEL_SWING_BASS = "Swing + walking bass"
FEEL_BOSSA = "Bossa nova"
FEELS = [FEEL_BLOCK, FEEL_SWING, FEEL_SWING_BASS, FEEL_BOSSA]

BASS_LO, BASS_HI = 31, 55   # G1..G3
SWING_OFFBEAT = 2.0 / 3.0   # the "and" eighth note falls on the last third of the beat

# Comping patterns per 4-beat bar: (onset, duration, anticipates the next chord)
SWING_PATTERNS = [
    [(0.0, 1.0, False), (1.5, 1.5, False)],             # Charleston
    [(0.0, 0.5, False), (2.5, 1.0, False)],
    [(1.5, 1.0, False), (3.5, 1.5, True)],
    [(0.0, 3.0, False)],
    [(1.0, 0.5, False), (2.5, 1.0, False)],
    [(0.0, 1.5, False), (3.5, 1.5, True)],
]
BOSSA_PATTERNS = [
    [(0.0, 0.5, False), (1.5, 1.0, False), (3.0, 0.5, False)],
    [(1.0, 0.5, False), (2.5, 1.0, False)],
]
# Bossa bass: (onset, duration, plays the fifth)
BOSSA_BASS = [(0.0, 1.5, False), (1.5, 0.5, False), (2.0, 1.5, True), (3.5, 0.5, True)]


@dataclass(frozen=True)
class Note:
    start: float     # in beats
    dur: float       # in beats
    midi: int
    velocity: int


@dataclass
class Performance:
    notes: List[Note]
    spans: List[Tuple[float, float]]   # (start, end) of each chord, in beats
    voicings: List[List[int]]
    total_beats: float

    def chord_at(self, beat: float) -> Optional[int]:
        """Index of the chord sounding at `beat` (None once it is over)."""
        if not self.spans or not 0 <= beat < self.total_beats:
            return None
        return bisect_right([start for start, _ in self.spans], beat) - 1


def _swing(position: float) -> float:
    whole, frac = divmod(position, 1.0)
    return whole + (SWING_OFFBEAT if abs(frac - 0.5) < 1e-9 else frac)


def _comping_hits(rng: random.Random, beats: float, patterns, alternate: bool,
                  has_next: bool, anticipated: bool) -> List[Tuple[float, float, bool]]:
    """Comping hits for one chord: (onset, duration, plays the next chord)."""
    hits = []
    bar = 0
    while bar * 4 < beats:
        pattern = patterns[bar % len(patterns)] if alternate else rng.choice(patterns)
        for onset, dur, anticipates in pattern:
            start = bar * 4 + onset
            if start >= beats:
                continue
            if anticipates:
                if has_next and abs(start - (beats - 0.5)) < 1e-9:
                    hits.append((start, dur, True))
                continue
            if anticipated and start < 1.0:
                continue  # the chord already came in half a beat early
            hits.append((start, min(dur, beats - start), False))
        bar += 1
    if not hits and not anticipated:
        hits.append((0.0, min(beats, 2.0), False))
    return hits


def _walking_bass(rng: random.Random, item: PlayChord, next_root: Optional[int], prev: int) -> List[int]:
    """One note per beat: root, chord tones and a chromatic approach to the next root."""
    chord = item.chord
    tones = [p for p in chord.pitch_classes[1:4]] or [chord.root]
    steps = max(1, int(item.beats))
    line: List[int] = []
    for k in range(steps):
        if k % 4 == 0:
            note = nearest_midi_for_pc(chord.root, prev, BASS_LO, BASS_HI)
        elif k == steps - 1 and next_root is not None:
            target = nearest_midi_for_pc(next_root, prev, BASS_LO, BASS_HI)
            note = clamp(target + rng.choice((-1, 1)), BASS_LO, BASS_HI)
        else:
            options = [nearest_midi_for_pc(p, prev, BASS_LO, BASS_HI) for p in tones]
            note = rng.choice([n for n in options if n != prev] or options)
        line.append(note)
        prev = note
    return line


def build_performance(playback: Sequence[PlayChord], density: int, feel: str = FEEL_BLOCK,
                      bpm: int = 120, seed: int = 0) -> Performance:
    """Turn the progression into notes. Deterministic: playback and export sound the same."""
    rng = random.Random(seed)
    beat_seconds = 60.0 / clamp(bpm, 30, 300)

    def ms(milliseconds: float) -> float:
        return milliseconds / 1000.0 / beat_seconds

    voicings: List[List[int]] = []
    spans: List[Tuple[float, float]] = []
    prev_voicing = None
    t = 0.0
    for item in playback:
        prev_voicing = chord_to_midi_notes(item.chord, prev_voicing, density)
        voicings.append(prev_voicing)
        spans.append((t, t + item.beats))
        t += item.beats
    total = t

    notes: List[Note] = []

    def add(start: float, dur: float, midi: int, velocity: int):
        start = max(0.0, start)
        dur = min(dur, total - start)
        if dur > 0:
            notes.append(Note(start, dur, midi, clamp(velocity, 1, 127)))

    def strike(start: float, dur: float, voicing: Sequence[int], velocity: int, strum_ms: float):
        """A chord with a slightly rolled attack and uneven dynamics (less 'MIDI')."""
        for midi in voicing:
            add(start + ms(rng.uniform(0.0, strum_ms)), dur, midi, velocity + rng.randint(-4, 4))

    swing = feel in (FEEL_SWING, FEEL_SWING_BASS)
    with_bass = feel in (FEEL_SWING_BASS, FEEL_BOSSA)
    prev_bass = 40
    anticipated = False

    for i, item in enumerate(playback):
        start, _ = spans[i]
        has_next = i + 1 < len(playback)

        if feel not in (FEEL_SWING, FEEL_SWING_BASS, FEEL_BOSSA):
            strike(start, item.beats, voicings[i], item.velocity, strum_ms=14.0)
            continue

        def upper(voicing):  # with a bass line, the piano does not double the low note
            return voicing[1:] if with_bass and len(voicing) >= 4 else voicing

        patterns = SWING_PATTERNS if swing else BOSSA_PATTERNS
        hits = _comping_hits(rng, item.beats, patterns, alternate=not swing,
                             has_next=has_next, anticipated=anticipated)
        anticipated = False
        for onset, dur, anticipates in hits:
            position = _swing(onset) if swing else onset
            voicing = voicings[i + 1] if anticipates else voicings[i]
            accent = 5 if onset % 1.0 else 0   # offbeats push
            strike(start + position + ms(rng.uniform(-6.0, 6.0)), dur, upper(voicing),
                   item.velocity - 8 + accent, strum_ms=6.0)
            anticipated = anticipated or anticipates

        if feel == FEEL_SWING_BASS:
            next_root = playback[i + 1].chord.root if has_next else None
            for k, midi in enumerate(_walking_bass(rng, item, next_root, prev_bass)):
                add(start + k + ms(rng.uniform(-5.0, 5.0)), 0.95, midi,
                    item.velocity - 2 + (4 if k % 2 == 0 else 0) + rng.randint(-4, 4))
                prev_bass = midi
        elif feel == FEEL_BOSSA:
            chord = item.chord
            fifth_pc = (chord.root + (6 if chord.quality in ("m7b5", "dim7") else 7)) % 12
            root = nearest_midi_for_pc(chord.root, prev_bass, BASS_LO, BASS_HI)
            fifth = nearest_midi_for_pc(fifth_pc, root, BASS_LO, BASS_HI)
            prev_bass = root
            bar = 0
            while bar * 4 < item.beats:
                for onset, dur, use_fifth in BOSSA_BASS:
                    if bar * 4 + onset < item.beats:
                        add(start + bar * 4 + onset + ms(rng.uniform(-4.0, 4.0)), dur,
                            fifth if use_fifth else root, item.velocity - 6 + rng.randint(-3, 3))
                bar += 1

    notes.sort(key=lambda n: n.start)
    return Performance(notes, spans, voicings, total)
