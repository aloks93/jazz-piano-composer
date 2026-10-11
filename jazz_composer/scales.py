"""Suggested scale for improvising over each chord (chord-scale relationship)."""

from typing import List, Tuple

from .models import Chord

SCALES = {
    "Ionian":            [0, 2, 4, 5, 7, 9, 11],
    "Lydian":            [0, 2, 4, 6, 7, 9, 11],
    "Dorian":            [0, 2, 3, 5, 7, 9, 10],
    "Phrygian":          [0, 1, 3, 5, 7, 8, 10],
    "Aeolian":           [0, 2, 3, 5, 7, 8, 10],
    "Locrian":           [0, 1, 3, 5, 6, 8, 10],
    "melodic minor":     [0, 2, 3, 5, 7, 9, 11],
    "Mixolydian":        [0, 2, 4, 5, 7, 9, 10],
    "Lydian dominant":   [0, 2, 4, 6, 7, 9, 10],
    "Mixolydian b9 b13": [0, 1, 4, 5, 7, 8, 10],
    "altered":           [0, 1, 3, 4, 6, 8, 10],
    "diminished (W-H)":  [0, 2, 3, 5, 6, 8, 9, 11],
}

# Secondary dominants that resolve to a minor chord
_DOMINANTS_TO_MINOR = ("V/ii", "V/iii", "V/vi", "V/iv")


def _scale_name(chord: Chord) -> str:
    tensions = set(chord.tensions)
    degree = None if chord.key is None else (chord.root - chord.key) % 12
    q = chord.quality

    if q == "maj7":
        if "#11" in tensions:
            return "Lydian"
        home = 3 if chord.minor else 0  # the key's I (or the relative major, in minor)
        return "Ionian" if degree in (None, home) else "Lydian"
    if q == "m7":
        if chord.minor:
            return "Aeolian" if degree == 0 and "13" not in tensions else "Dorian"
        return {4: "Phrygian", 9: "Aeolian"}.get(degree, "Dorian")
    if q in ("m6", "mMaj7"):
        return "melodic minor"
    if q == "m7b5":
        return "Locrian"
    if q == "dim7":
        return "diminished (W-H)"
    if q in ("7", "sus7"):
        if "#9" in tensions or {"b9", "b13"} <= tensions:
            return "altered"
        if tensions & {"b9", "b13"}:
            return "Mixolydian b9 b13"
        if "#11" in tensions or chord.roman.lower().startswith(("subv", "bvii", "bii", "bvi")):
            return "Lydian dominant"
        # a dominant resolving to a minor chord: b9/b13 even when the symbol shows no tensions
        if (chord.minor and degree == 7) or chord.roman in _DOMINANTS_TO_MINOR:
            return "Mixolydian b9 b13"
        return "Mixolydian"
    return "Ionian"


def scale_parts(chord: Chord) -> Tuple[str, str, List[int]]:
    """(root, scale name, pitch classes), e.g. ('G', 'altered', [7, 8, 10, 11, 1, 3, 5])."""
    scale = _scale_name(chord)
    return chord.spell(chord.root), scale, [(chord.root + i) % 12 for i in SCALES[scale]]


def suggest_scale(chord: Chord) -> Tuple[str, List[int]]:
    """(label, pitch classes), e.g. ('G altered', [7, 8, 10, 11, 1, 3, 5])."""
    root, scale, pcs = scale_parts(chord)
    return f"{root} {scale}", pcs


def scale_note_names(chord: Chord) -> str:
    return " ".join(chord.spell(p) for p in suggest_scale(chord)[1])
