"""Additive "piano-like" synthesizer (numpy) and rendering of performances to PCM / WAV.

Not a sampler: each note is a sum of sine partials.
Velocity controls loudness and brightness (more partials, slower roll-off).
"""

import wave
from functools import lru_cache
from typing import Iterator

import numpy as np

from .models import clamp
from .performance import Performance

SAMPLE_RATE = 44100
DETUNE_RATIO = 2.0 ** (2.5 / 1200.0)  # subtle chorus: 2.5 cents
NOTE_GAIN = 0.45                       # ~1/sqrt(5): a typical chord does not clip
VELOCITY_STEP = 4                      # velocity is quantized so cached notes get reused


def midi_to_freq(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def beat_seconds(bpm: int) -> float:
    return 60.0 / clamp(bpm, 30, 300)


def adsr_envelope(n: int, sr: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
    """ADSR envelope of `n` samples (times in seconds). Always ends at 0."""
    a, d = int(sr * attack), int(sr * decay)
    r = min(int(sr * release), n)
    env = np.interp(np.arange(n), [0, a, a + d], [0.0, 1.0, sustain])
    if r > 0:
        env[n - r:] *= np.linspace(1.0, 0.0, r)
    return env


@lru_cache(maxsize=160)
def _note_wave(midi: int, n: int, sr: int, velocity: int) -> np.ndarray:
    v = velocity / 127.0
    max_harm = int(7 + 18 * v)        # 7..25 partials
    rolloff = 1.75 - 0.95 * v         # lower = brighter
    hi_damp = 1.2 + 2.0 * v           # high partials die out faster

    f = midi_to_freq(midi)
    t = np.arange(n) / sr
    ph1 = 2.0 * np.pi * f * t
    ph2 = ph1 * DETUNE_RATIO
    damp_step = np.exp(-t * hi_damp / max_harm)
    damp = np.ones(n)
    wave_ = np.zeros(n)
    # partials below Nyquist (avoids aliasing on high notes)
    for h in range(1, min(max_harm, int(sr / 2 / (f * DETUNE_RATIO))) + 1):
        damp *= damp_step
        wave_ += damp * (np.sin(ph1 * h) / h ** rolloff + 0.55 * np.sin(ph2 * h) / h ** (rolloff + 0.18))

    # "Hammer noise": a very short burst of noise on the attack
    hammer_len = min(n, int(sr * 0.012))
    noise = np.random.default_rng(1337 + midi * 31 + velocity).uniform(-1.0, 1.0, hammer_len)
    wave_[:hammer_len] += noise * (0.005 + 0.010 * v) * np.linspace(1.0, 0.0, hammer_len, endpoint=False)

    wave_ *= (0.17 + 0.20 * v) * NOTE_GAIN * adsr_envelope(
        n, sr,
        attack=0.008 + 0.006 * (1.0 - v),
        decay=0.09,
        sustain=0.62,
        release=min(0.28, n / sr * 0.38),
    )
    out = wave_.astype(np.float32)
    out.setflags(write=False)
    return out


def synth_note(midi: int, duration: float, sr: int = SAMPLE_RATE, velocity: int = 100) -> np.ndarray:
    """Waveform (float32, unclipped) of a MIDI note lasting `duration` seconds."""
    velocity = clamp(round(velocity / VELOCITY_STEP) * VELOCITY_STEP, 1, 127)
    return _note_wave(int(midi), max(1, int(sr * duration)), sr, velocity)


def iter_performance_pcm(perf: Performance, bpm: int, sr: int = SAMPLE_RATE,
                         chunk_seconds: float = 0.5) -> Iterator[bytes]:
    """Mix the performance and yield it as chunks of 16-bit mono PCM.

    Each note is synthesized only when it starts, so the first chunk comes out right away.
    """
    beat = beat_seconds(bpm)
    total_n = int(perf.total_beats * beat * sr)
    chunk_n = max(1, int(chunk_seconds * sr))
    pending = np.zeros(0, dtype=np.float32)   # the mix from `pos` onwards
    pos = 0
    i = 0
    while pos < total_n:
        end = min(pos + chunk_n, total_n)
        while i < len(perf.notes):
            note = perf.notes[i]
            start = int(note.start * beat * sr)
            if start >= end:
                break
            wave_ = synth_note(note.midi, note.dur * beat, sr, note.velocity)[:total_n - start]
            offset = start - pos
            if offset + len(wave_) > len(pending):
                pending = np.concatenate([pending, np.zeros(offset + len(wave_) - len(pending), dtype=np.float32)])
            pending[offset:offset + len(wave_)] += wave_
            i += 1
        if len(pending) < end - pos:
            pending = np.concatenate([pending, np.zeros(end - pos - len(pending), dtype=np.float32)])
        out, pending = pending[:end - pos], pending[end - pos:]
        pos = end
        yield (np.tanh(out * 1.35) * 32767).astype(np.int16).tobytes()  # soft clip


def write_wav(path: str, perf: Performance, bpm: int, sr: int = SAMPLE_RATE) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for pcm in iter_performance_pcm(perf, bpm, sr, chunk_seconds=2.0):
            wf.writeframes(pcm)
