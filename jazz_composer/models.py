"""Data structures shared by the engine, the audio layer and the UI."""

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import theory


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class Chord:
    """A chord with its analysis (roman numeral + function T/SD/D/Bridge).

    `key`/`minor` are the key it appears in: they decide how it is spelled (Bb vs A#).
    """
    root: int
    quality: str
    roman: str
    func: str
    tensions: Tuple[str, ...] = ()
    key: Optional[int] = None
    minor: bool = False

    def spell(self, p: int) -> str:
        return theory.spell(p, self.key, self.minor)

    @property
    def symbol(self) -> str:
        return theory.chord_symbol(self.root, self.quality, self.tensions, self.key, self.minor)

    @property
    def pitch_classes(self) -> List[int]:
        return theory.chord_pitch_classes(self.root, self.quality, self.tensions)

    @property
    def guides(self) -> Tuple[int, int]:
        """(3rd, 7th) as pitch classes."""
        return theory.quality_guide_tones(self.root, self.quality)


@dataclass
class Event:
    """A chord placed in time (bar) with its guide-tone motion."""
    chord: Chord
    bar: int = 0
    guides: str = ""


@dataclass
class Block:
    """One part of the form (A, B, S1...). `header` announces a modulation bridge."""
    events: List[Event]
    name: str = ""
    header: Optional[str] = None
    key_label: str = ""

    def copy(self) -> "Block":
        return Block([Event(e.chord) for e in self.events], self.name, self.header, self.key_label)


@dataclass
class Section:
    """Editable settings of one section (a row in the section editor)."""
    bars: int
    key_name: str
    tension: int
    do_modulate: bool
    target_key: str
    mod_strategy: str
    return_to_start: bool


@dataclass(frozen=True)
class PlayChord:
    """What the audio layer needs to play one chord."""
    chord: Chord
    velocity: int
    beats: float


@dataclass
class HarmonyContext:
    """Engine-wide parameters: harmonic density (1..10), mode and source of randomness."""
    density: int = 4
    rng: random.Random = field(default_factory=random.Random)
    minor: bool = False

    def __post_init__(self):
        self.density = clamp(int(self.density), 1, 10)
