"""Core music theory: notes, scales, chord qualities and chord symbols."""

from typing import Callable, List, Optional, Sequence, Tuple

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
# Conventional key names (major / minor)
KEY_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
MINOR_KEY_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B']

MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]

# degree -> (quality, roman numeral, function)
DIATONIC_MAJOR = {
    1: ("maj7", "I",  "T"),
    2: ("m7",   "ii", "SD"),
    3: ("m7",   "iii", "T"),
    4: ("maj7", "IV", "SD"),
    5: ("7",    "V",  "D"),
    6: ("m7",   "vi", "T"),
    7: ("m7b5", "viiø", "D"),
}

# Natural minor with the V7 borrowed from harmonic minor
DIATONIC_MINOR = {
    1: ("m7",   "i",    "T"),
    2: ("m7b5", "iiø",  "SD"),
    3: ("maj7", "bIII", "T"),
    4: ("m7",   "iv",   "SD"),
    5: ("7",    "V",    "D"),
    6: ("maj7", "bVI",  "SD"),
    7: ("7",    "bVII", "SD"),
}

# (3rd, 7th) relative to the root
QUALITY_GUIDE_TONES = {
    "maj7": (4, 11),
    "m7":   (3, 10),
    "7":    (4, 10),
    "m7b5": (3, 10),
    "dim7": (3, 9),
    "sus7": (5, 10),
    "m6":   (3, 9),
    "mMaj7": (3, 11),
}

QUALITY_CHORD_TONES = {
    "maj7": [0, 4, 7, 11],
    "m7":   [0, 3, 7, 10],
    "7":    [0, 4, 7, 10],
    "m7b5": [0, 3, 6, 10],
    "dim7": [0, 3, 6, 9],
    "sus7": [0, 5, 7, 10],
    "m6":   [0, 3, 7, 9],
    "mMaj7": [0, 3, 7, 11],
}

TENSION_INTERVALS = {
    "6": 9,
    "9": 14,
    "b9": 13,
    "#9": 15,
    "11": 17,
    "#11": 18,
    "13": 21,
    "b13": 20,
}

_LETTERS = "CDEFGAB"
_NATURAL_PC = [0, 2, 4, 5, 7, 9, 11]
# semitones above the tonic -> letter steps (1, b2, 2, b3, 3, 4, #4, 5, b6, 6, b7, 7)
_DEGREE_LETTER_STEPS = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6]
_AWKWARD_SPELLINGS = {"E#", "B#", "Cb", "Fb"}


def pc(note: str) -> int:
    """Note name ('C', 'F#', 'Bb') -> pitch class 0..11."""
    letter, accidentals = note[0].upper(), note[1:]
    return (_NATURAL_PC[_LETTERS.index(letter)] + accidentals.count('#') - accidentals.count('b')) % 12


def name(p: int) -> str:
    return NOTE_NAMES[p % 12]


def key_name(key: int, minor: bool = False) -> str:
    return (MINOR_KEY_NAMES[key % 12] + "m") if minor else KEY_NAMES[key % 12]


def spell(p: int, key: Optional[int] = None, minor: bool = False) -> str:
    """Name a pitch class by its degree in the key (Bb in F, F# in G, Db as bII of C...).

    Without a key it uses sharps. When the theoretical spelling needs a double accidental
    or E#/B#/Cb/Fb, it falls back to the common enharmonic name.
    """
    if key is None:
        return name(p)
    tonic = (MINOR_KEY_NAMES if minor else KEY_NAMES)[key % 12]
    letter = (_LETTERS.index(tonic[0]) + _DEGREE_LETTER_STEPS[(p - key) % 12]) % 7
    accidental = (p - _NATURAL_PC[letter] + 6) % 12 - 6
    if abs(accidental) <= 1:
        spelled = _LETTERS[letter] + {-1: "b", 0: "", 1: "#"}[accidental]
        if spelled not in _AWKWARD_SPELLINGS:
            return spelled
    return KEY_NAMES[p % 12]


def scale_pcs(root: int, minor: bool = False) -> List[int]:
    return [(root + i) % 12 for i in (MINOR_SCALE if minor else MAJOR_SCALE)]


def degree_root(key_root: int, degree: int, minor: bool = False) -> int:
    return scale_pcs(key_root, minor)[degree - 1]


def diatonic_table(minor: bool = False) -> dict:
    return DIATONIC_MINOR if minor else DIATONIC_MAJOR


def chord_symbol(root_pc: int, quality: str, tensions: Optional[Sequence[str]] = None,
                 key: Optional[int] = None, minor: bool = False) -> str:
    s = f"{spell(root_pc, key, minor)}{quality}"
    if tensions:
        s += "(" + ",".join(tensions) + ")"
    return s


def parse_chord_symbol(sym: str) -> Tuple[int, str, List[str]]:
    """'G7(b9,#9)' -> (7, '7', ['b9', '#9']). Accepts flats ('Bbmaj7'). Raises ValueError if invalid."""
    s = sym.strip()
    if not s or s[0].upper() not in _LETTERS:
        raise ValueError(f"Invalid chord: {sym!r}")
    idx = 2 if len(s) > 1 and s[1] in "#b" else 1
    root = pc(s[:idx])
    q_end = s.find('(')
    if q_end == -1:
        q_end = len(s)
    quality = s[idx:q_end].strip()
    if quality not in QUALITY_CHORD_TONES:
        raise ValueError(f"Unknown quality: {quality!r}. Valid: {', '.join(QUALITY_CHORD_TONES)}")
    tensions: List[str] = []
    if '(' in s and ')' in s:
        inside = s[s.find('(') + 1:s.rfind(')')]
        tensions = [t.strip() for t in inside.split(',') if t.strip()]
    unknown = [t for t in tensions if t not in TENSION_INTERVALS]
    if unknown:
        raise ValueError(f"Unknown tension: {', '.join(unknown)}. Valid: {', '.join(TENSION_INTERVALS)}")
    return root, quality, tensions


def chord_pitch_classes(root_pc: int, quality: str, tensions: Sequence[str] = ()) -> List[int]:
    """Ordered pitch classes: root, 3rd/5th/7th, then tensions (no duplicates)."""
    intervals = list(QUALITY_CHORD_TONES.get(quality, [0, 4, 7]))
    intervals += [TENSION_INTERVALS[t] for t in tensions if t in TENSION_INTERVALS]
    return list(dict.fromkeys((root_pc + iv) % 12 for iv in intervals))


def quality_guide_tones(root_pc: int, quality: str) -> Tuple[int, int]:
    rel = QUALITY_GUIDE_TONES.get(quality, (4, 10))
    return ((root_pc + rel[0]) % 12, (root_pc + rel[1]) % 12)


def guide_motion(prev_gt: Tuple[int, int], next_gt: Tuple[int, int],
                 speller: Callable[[int], str] = name) -> str:
    """Describe how the 3rd and 7th move between two chords."""
    def step(a, b):
        up = (b - a) % 12
        down = (a - b) % 12
        return f"{speller(a)}→{speller(b)} ({'+' if up <= down else '-'}{min(up, down)})"
    return f"3rd: {step(prev_gt[0], next_gt[0])} | 7th: {step(prev_gt[1], next_gt[1])}"
