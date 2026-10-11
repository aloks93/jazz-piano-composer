"""Functional harmony building blocks: tensions, cadences, turnarounds, secondary dominants."""

from typing import List, Tuple

from .models import Chord, HarmonyContext
from .theory import degree_root, diatonic_table

CADENCE_AUTHENTIC = "Authentic (V-I)"
CADENCE_DECEPTIVE = "Deceptive (V-vi)"
CADENCE_PLAGAL = "Plagal (IV-I)"
CADENCE_HALF = "Half (V)"
CADENCES = [CADENCE_AUTHENTIC, CADENCE_DECEPTIVE, CADENCE_PLAGAL, CADENCE_HALF]


def pick_tensions(density: int, function: str, tension_level: int, quality: str = "",
                  altered: bool = False) -> Tuple[str, ...]:
    """Chord tensions by density (the palette) and section tension (how loaded it gets).

    Density:
      1-3  : no extensions
      4-6  : basic color (9, sometimes 11/13)
      7-8  : rich diatonic color; Lydian-dominant style dominants (9, 13, #11)
      9-10 : altered dominants (b9, #9, b13)

    `altered`: a dominant resolving to a minor chord -> always b9/b13 (harmonic minor).
    """
    tl = max(0, min(3, int(tension_level)))
    if density <= 3 or tl <= 0:
        return ()
    if quality == "m7b5":  # the natural 9 clashes; the 11 is the safe color
        return ("11",) if tl >= 2 else ()

    if altered and function == "D":
        if density <= 6:
            out = ["b9"] + (["b13"] if tl >= 3 else [])
        else:
            out = ["b9"] + (["#9"] if tl >= 3 else []) + (["b13"] if tl >= 2 else [])
    elif density <= 6:
        if function == "T":
            out = ["9"] + (["13"] if tl >= 3 else [])
        elif function == "SD":
            out = ["9"] + (["11"] if tl >= 2 else []) + (["13"] if tl >= 3 else [])
        else:
            out = ["9"] + (["13"] if tl >= 2 else [])
    elif density <= 8:
        if function == "T":
            out = ["9"] + (["13"] if tl >= 2 else [])
            if tl >= 3 and "maj" in quality:
                out.append("#11")
        elif function == "SD":
            out = ["9", "11"] + (["13"] if tl >= 2 else [])
        else:  # Lydian dominant: no b9/#9
            out = ["9"] + (["13"] if tl >= 2 else []) + (["#11"] if tl >= 3 else [])
    else:
        if function == "T":
            out = ["9", "13"]
            if tl >= 2 and "maj" in quality:
                out.append("#11")
        elif function == "SD":
            out = ["9", "11", "13"]
        else:  # altered: no 11/#11
            out = ["b9"] + (["#9"] if tl >= 2 else []) + (["b13"] if tl >= 3 else [])

    if "maj" in quality:   # the natural 11 is an avoid note over a major 3rd
        out = ["#11" if t == "11" else t for t in out]
    if quality == "m6":    # the 13 is already the chord's 6th
        out = [t for t in out if t != "13"]
    return tuple(dict.fromkeys(out))


def make_chord(ctx: HarmonyContext, root: int, quality: str, roman: str, func: str, tension: int,
               altered: bool = False) -> Chord:
    """A chord with the tensions its function calls for. `tension` < 0 => no tensions."""
    tension_func = func if func in ("T", "SD", "D") else "SD"
    tens = pick_tensions(ctx.density, tension_func, tension, quality, altered) if tension >= 0 else ()
    return Chord(root, quality, roman, func, tens)


def diatonic_chord(ctx: HarmonyContext, key_root: int, degree: int, tension: int) -> Chord:
    quality, roman, func = diatonic_table(ctx.minor)[degree]
    # Tonic and subdominant chords carry one level less than the dominant
    level = tension if func == "D" else max(0, tension - 1)
    return make_chord(ctx, degree_root(key_root, degree, ctx.minor), quality, roman, func, level,
                      altered=ctx.minor and degree == 5)


def tonic_chord(ctx: HarmonyContext, key_root: int, tension: int) -> Chord:
    """The chord of rest: Imaj7, or im7 / im6 (melodic minor, at high density) in minor."""
    if ctx.minor:
        return make_chord(ctx, key_root, "m6" if ctx.density >= 7 else "m7", "i", "T", tension)
    return make_chord(ctx, key_root, "maj7", "I", "T", tension)


def dominant_chord(ctx: HarmonyContext, key_root: int, tension: int, roman: str = "V") -> Chord:
    return make_chord(ctx, (key_root + 7) % 12, "7", roman, "D", tension, altered=ctx.minor)


def cadence_ii_v_i(ctx: HarmonyContext, key_root: int, tension: int) -> List[Chord]:
    """ii-V-I (iiø-V7alt-i in minor) with idiomatic variations of the same length:

    - Backdoor (major only): ivm7 -> bVII7 -> Imaj7 (modal interchange).
    - Tritone substitution of the V7 (bII7).
    """
    soft = max(0, tension - 1)
    tonic = tonic_chord(ctx, key_root, soft)

    if not ctx.minor and tension >= 2 and ctx.density >= 7 and ctx.rng.random() < 0.16:
        return [
            make_chord(ctx, (key_root + 5) % 12, "m7", "ivm7", "SD", soft),
            make_chord(ctx, (key_root + 10) % 12, "7", "bVII7", "D", tension),
            tonic,
        ]

    ii = diatonic_chord(ctx, key_root, 2, tension)
    if tension >= 2 and ctx.density >= 8 and ctx.rng.random() < 0.26:
        dominant = make_chord(ctx, (key_root + 1) % 12, "7", "subV", "D", tension)
    else:
        dominant = dominant_chord(ctx, key_root, tension)
    return [ii, dominant, tonic]


def turnaround(ctx: HarmonyContext, key_root: int, tension: int) -> List[Chord]:
    """I-vi-ii-V in major; i-bVI-iiø-V in minor."""
    soft = max(0, tension - 1)
    return [
        tonic_chord(ctx, key_root, soft),
        diatonic_chord(ctx, key_root, 6, tension),
        diatonic_chord(ctx, key_root, 2, tension + 1),  # +1 offsets the SD's one-level reduction
        dominant_chord(ctx, key_root, tension),
    ]


def secondary_dominant_to_degree(ctx: HarmonyContext, key_root: int, target_degree: int, tension: int) -> List[Chord]:
    """V7/x -> x. When x is minor the dominant is altered (b9/b13)."""
    quality, base_roman, _ = diatonic_table(ctx.minor)[target_degree]
    target_root = degree_root(key_root, target_degree, ctx.minor)
    return [
        make_chord(ctx, (target_root + 7) % 12, "7", f"V/{base_roman}", "D", tension,
                   altered=quality.startswith("m7")),
        diatonic_chord(ctx, key_root, target_degree, max(0, tension - 1)),
    ]


def cadence_tail(ctx: HarmonyContext, key_root: int, cadence: str, tension: int) -> List[Chord]:
    """A short final cadence (1-2 chords) that reinforces the ending."""
    soft = max(0, tension - 1)
    tonic = tonic_chord(ctx, key_root, soft)

    if cadence == CADENCE_DECEPTIVE:  # V-vi (V-bVI in minor)
        return [dominant_chord(ctx, key_root, max(1, tension - 1)), diatonic_chord(ctx, key_root, 6, tension)]
    if cadence == CADENCE_PLAGAL:
        return [diatonic_chord(ctx, key_root, 4, tension), tonic]
    if cadence == CADENCE_HALF:
        return [dominant_chord(ctx, key_root, tension, "V (half cadence)")]
    return [dominant_chord(ctx, key_root, tension), tonic]
