"""Progression generators, one per style. Each returns one chord per bar."""

from typing import List, Optional

from .harmony import (
    cadence_ii_v_i,
    diatonic_chord,
    dominant_chord,
    make_chord,
    secondary_dominant_to_degree,
    tonic_chord,
    turnaround,
)
from .models import Chord, HarmonyContext, clamp
from .theory import degree_root, diatonic_table

STYLE_STANDARD = "Standard (functional)"
STYLE_BLUES = "12-bar blues"
STYLE_JAZZ_BLUES = "Jazz blues (II-V)"
STYLE_MODAL = "Modal (Dorian/Mixolydian)"
STYLE_COLTRANE = "Coltrane changes"
STYLES = [STYLE_STANDARD, STYLE_BLUES, STYLE_JAZZ_BLUES, STYLE_MODAL, STYLE_COLTRANE]


def _fit(pattern: List[Chord], bars: int) -> List[Chord]:
    """Repeat or truncate a pattern to the requested length."""
    reps = (bars + len(pattern) - 1) // len(pattern)
    return (pattern * reps)[:bars]


def _next_diatonic(ctx: HarmonyContext, key_root: int, prev: Chord, tension: int,
                   avoid_root: Optional[int] = None) -> Chord:
    """A diatonic chord that follows `prev` in the functional flow T -> SD -> D -> T."""
    rng = ctx.rng
    by_function = {"T": [], "SD": [], "D": []}
    for degree, (_, _, func) in diatonic_table(ctx.minor).items():
        if degree != 7 or ctx.minor:  # viiø is left out in major; bVII7 is a usable SD in minor
            by_function[func].append(degree)

    roll = rng.random()
    if prev.func == "D":
        func = "T"
    elif prev.func == "SD":
        func = "D" if roll < 0.5 else ("SD" if roll < 0.8 else "T")
    else:
        func = "SD" if roll < 0.7 else "T"

    def fresh(degrees):
        chords = [diatonic_chord(ctx, key_root, d, tension) for d in degrees]
        return [c for c in chords if c.root not in (prev.root, avoid_root)]

    # if that function has nothing new to offer, any other diatonic chord will do
    candidates = fresh(by_function[func]) or fresh(d for degrees in by_function.values() for d in degrees)
    return rng.choice(candidates)


def generate_standard(ctx: HarmonyContext, key_root: int, bars: int, tension: int) -> List[Chord]:
    """Functional harmony phrased like a tune.

    The section opens on the tonic, moves away through diatonic motion and secondary
    dominants, and closes with a ii-V-I that lands on the tonic in the last bar.
    """
    rng = ctx.rng
    soft = max(0, tension - 1)
    tonic = tonic_chord(ctx, key_root, soft)
    if bars <= 0:
        return []
    if bars == 1:
        return [tonic]
    if bars == 2:
        return [dominant_chord(ctx, key_root, tension), tonic]

    closing = cadence_ii_v_i(ctx, key_root, tension)
    room = bars - len(closing)
    secondary_targets = [4, 6, 3] if ctx.minor else [2, 4, 6]

    def diatonic(degree: int) -> Chord:
        return diatonic_chord(ctx, key_root, degree, soft)

    # Opening: establish the key
    chords: List[Chord] = []
    opening = rng.random()
    if room >= 4 and opening < 0.45:
        chords += turnaround(ctx, key_root, soft)
    elif room >= 4 and opening < 0.70:
        chords += [tonic, diatonic(4), diatonic(3), diatonic(6)]
    elif room >= 2:
        chords += [tonic, diatonic(rng.choice([4, 6]))]
    elif room == 1:
        chords.append(tonic)

    # Middle: move away from the tonic before the cadence brings it back
    while len(chords) < room:
        left = room - len(chords)
        # whatever lands right before the cadence must not repeat its first chord
        avoid = closing[0].root if left <= 2 else None
        targets = []
        for d in secondary_targets:
            target_root = degree_root(key_root, d, ctx.minor)
            repeats_previous = chords[-1].quality == "7" and chords[-1].root == (target_root + 7) % 12
            if target_root != avoid and not repeats_previous:
                targets.append(d)
        if left >= 2 and targets and rng.random() < 0.55:
            chords += secondary_dominant_to_degree(ctx, key_root, rng.choice(targets), tension)
        else:
            chords.append(_next_diatonic(ctx, key_root, chords[-1], soft, avoid if left == 1 else None))

    return chords + closing


def _major_blues(ctx: HarmonyContext, key_root: int, tension: int, jazz: bool) -> List[Chord]:
    ii = (key_root + 2) % 12
    IV = (key_root + 5) % 12
    soft = max(1, tension - 1)

    def plain(root, roman, func):
        return make_chord(ctx, root, "7", roman, func, -1)

    def dom(root, roman, level, altered=False):
        return make_chord(ctx, root, "7", roman, "D", level, altered=altered)

    I7, IV7 = plain(key_root, "I7", "T"), plain(IV, "IV7", "SD")
    V7, turn = dominant_chord(ctx, key_root, tension, "V7"), dominant_chord(ctx, key_root, soft, "V7 (turn)")

    if jazz:
        ii7 = make_chord(ctx, ii, "m7", "ii7", "SD", soft)
        return [
            I7, plain(IV, "IV7 (quick)", "SD"), I7, dom((ii + 7) % 12, "V/ii", tension, altered=True),
            ii7, V7, IV7, dom((IV + 7) % 12, "V/IV", soft),
            ii7, V7, I7, turn,
        ]
    return [
        I7, IV7, I7, I7,
        IV7, IV7, I7, I7,
        V7, IV7, I7, turn,
    ]


def _minor_blues(ctx: HarmonyContext, key_root: int, tension: int, jazz: bool) -> List[Chord]:
    soft = max(1, tension - 1)
    i7 = make_chord(ctx, key_root, "m7", "i7", "T", soft)
    iv7 = make_chord(ctx, (key_root + 5) % 12, "m7", "iv7", "SD", soft)
    bVI7 = make_chord(ctx, (key_root + 8) % 12, "7", "bVI7", "SD", tension)
    V7, turn = dominant_chord(ctx, key_root, tension, "V7"), dominant_chord(ctx, key_root, soft, "V7 (turn)")

    if jazz:
        ii = make_chord(ctx, (key_root + 2) % 12, "m7b5", "iiø", "SD", tension)
        V_of_iv = make_chord(ctx, key_root, "7", "V/iv", "D", tension, altered=True)
        return [
            i7, ii, i7, V_of_iv,
            iv7, iv7, i7, i7,
            ii, V7, i7, turn,
        ]
    return [
        i7, i7, i7, i7,
        iv7, iv7, i7, i7,
        bVI7, V7, i7, turn,
    ]


def generate_blues(ctx: HarmonyContext, key_root: int, bars: int, tension: int, variant: str = STYLE_BLUES) -> List[Chord]:
    """12-bar blues (classic, or jazz blues with ii-Vs; major or minor), repeated or truncated."""
    builder = _minor_blues if ctx.minor else _major_blues
    return _fit(builder(ctx, key_root, tension, jazz=variant == STYLE_JAZZ_BLUES), bars)


def generate_modal(ctx: HarmonyContext, key_root: int, bars: int, tension: int) -> List[Chord]:
    """Modal vamps: Dorian (always, in minor mode) or Mixolydian. The tonal center stays put."""
    rng = ctx.rng
    dorian = ctx.minor or rng.random() < 0.55
    IV = (key_root + 5) % 12
    chords: List[Chord] = []

    for i in range(bars):
        beat = i % 4
        if dorian:
            if beat in (1, 3) and rng.random() < 0.75:
                spec = (IV, "7", "IV7 (Dorian vamp)", "SD")
            else:
                spec = (key_root, "m7", "i-7 (Dorian)", "T")
        else:
            r = rng.random()
            if beat == 2 and r < 0.6:
                spec = ((key_root + 10) % 12, "maj7", "bVIImaj7 (Mixo color)", "T")
            elif beat in (1, 3) and r < 0.75:
                spec = (IV, "7", "IV7 (Mixo)", "SD")
            else:
                spec = (key_root, "7", "I7 (Mixolydian)", "T")
        chords.append(make_chord(ctx, *spec, tension))

    return chords


def generate_coltrane(ctx: HarmonyContext, key_root: int, bars: int, tension: int) -> List[Chord]:
    """Major-third cycle (Giant Steps style): three tonal centers joined by their V7s.

    I | V7/bVI | bVI | V7/III | III | V7 | (back to I). The centers are always major.
    """
    soft = max(0, tension - 1)

    def center(interval, roman):
        return make_chord(ctx, (key_root + interval) % 12, "maj7", roman, "T", soft)

    def dom_to(interval, roman):
        return make_chord(ctx, (key_root + interval + 7) % 12, "7", roman, "D", tension)

    cycle = [
        center(0, "I"), dom_to(8, "V/bVI"),
        center(8, "bVI"), dom_to(4, "V/III"),
        center(4, "III"), dom_to(0, "V"),
    ]
    return _fit(cycle, bars)


def generate_rhythm_changes(key_root: int, tension: int) -> List[Chord]:
    """Simplified Rhythm Changes (AABA, 32 bars, always major).

    A: I | VI7 | II7 | V7 (x2)        B: III7 | VI7 | II7 | V7 (x2)
    """
    level = clamp(tension, 0, 3)
    tens_dom = [(), ("9",), ("13",), ("b9", "#9")][level]
    tens_ton = [(), ("6",), ("9",), ("9",)][level]

    def dom(interval, roman):
        return Chord((key_root + interval) % 12, "7", roman, "D", tens_dom)

    tonic = Chord(key_root, "maj7", "I", "T", tens_ton)
    cycle = [dom(9, "VI7"), dom(2, "II7"), dom(7, "V7")]
    A = ([tonic] + cycle) * 2
    B = ([dom(4, "III7")] + cycle) * 2
    return A + A + B + A


def generate_for_style(ctx: HarmonyContext, style: str, key_root: int, bars: int, tension: int) -> List[Chord]:
    if style in (STYLE_BLUES, STYLE_JAZZ_BLUES):
        return generate_blues(ctx, key_root, bars, tension, style)
    if style == STYLE_MODAL:
        return generate_modal(ctx, key_root, bars, tension)
    if style == STYLE_COLTRANE:
        return generate_coltrane(ctx, key_root, bars, tension)
    return generate_standard(ctx, key_root, bars, tension)
