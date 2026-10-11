"""Piano voicings: chord -> MIDI notes, picking the candidate with the smoothest voice leading."""

from typing import List, Optional

from .models import Chord

BASS_LO, BASS_HI = 36, 55      # C2..G3
UPPER_LO, UPPER_HI = 48, 96    # C3..C7


def nearest_midi_for_pc(pc: int, target: int, lo: int, hi: int) -> int:
    """MIDI note with pitch class `pc` as close as possible to `target`, within [lo, hi]."""
    in_range = [p for p in range(pc, 128, 12) if lo <= p <= hi]
    if in_range:
        return min(in_range, key=lambda p: abs(p - target))
    return max(lo, min(hi, pc + 12 * round((target - pc) / 12)))


def extended_pitch_classes(chord: Chord, density: int) -> List[int]:
    """The chord's pitch classes plus extra color by density, only where the symbol has none.

    Avoids clashes: no natural 9 over b9/#9, no 13 over b13, and #11 instead of 11 on
    chords with a major 3rd (the natural 11 is an avoid note).
    """
    pcs = chord.pitch_classes
    if chord.quality in ("dim7", "m7b5"):
        return pcs
    root = chord.root
    if chord.minor and chord.quality == "7" and chord.key is not None and (root - chord.key) % 12 == 7:
        return pcs  # V7 of a minor key: the natural 9 and 13 clash with the scale
    present = {(p - root) % 12 for p in pcs}
    major_third = 4 in present

    if density >= 6 and not present & {1, 2, 3 if major_third else 2}:
        pcs.append((root + 2) % 12)
    if density >= 8 and not present & {5, 6}:
        pcs.append((root + (6 if major_third else 5)) % 12)
    if density >= 9 and not present & {8, 9}:
        pcs.append((root + 9) % 12)
    return list(dict.fromkeys(pcs))


def _voice_lead_from_previous(prev_notes: List[int], root_pc: int, pcs: List[int]) -> List[int]:
    """Direct voice-leading candidate: each voice takes the octave nearest to the previous voice."""
    midi_root = nearest_midi_for_pc(root_pc, prev_notes[0], lo=36, hi=60)
    prev_upper = sorted(prev_notes[1:])

    voiced = [midi_root]
    for i, p in enumerate(q for q in pcs if q != root_pc):
        target = prev_upper[min(i, len(prev_upper) - 1)] if prev_upper else midi_root + 12 * (i + 1)
        note = nearest_midi_for_pc(p, target, UPPER_LO, UPPER_HI)
        # no crossings: each voice sits above the previous one
        while note <= voiced[-1]:
            note += 12
        while note > UPPER_HI:
            note -= 12
        if note <= voiced[-1]:
            note = voiced[-1] + 1
        voiced.append(note)
    return voiced


def _weighted_voice_distance(prev: List[int], cand: List[int]) -> float:
    """Distance between voicings: inner voices (guide tones) weigh more; bass leaps are penalized."""
    prev_s, cand_s = sorted(prev), sorted(cand)
    k = min(len(prev_s), len(cand_s))
    dist = 0.0
    for i, (p, c) in enumerate(zip(prev_s[-k:], cand_s[-k:])):
        x = (i + 0.5) / k
        weight = 1.0 + 0.55 * (1.0 - abs(0.5 - x) * 2.0)  # peaks in the middle
        dist += weight * abs(c - p)
    return dist + 0.75 * abs(cand[0] - prev[0])


def _place_upper(pcs: List[int], top_center: int) -> List[int]:
    """Stack pitch classes in ascending order, with the top voice near `top_center`."""
    notes: List[int] = []
    for i, p in enumerate(pcs):
        target = top_center - 12 * (len(pcs) - 1 - i)
        n = nearest_midi_for_pc(p, target, UPPER_LO, UPPER_HI)
        while notes and n <= notes[-1]:
            n += 12
        notes.append(n)
    return notes


def build_candidate_voicings(root_pc: int, pcs: List[int], density: int,
                             function_hint: Optional[str] = None, base_c3: int = 48) -> List[List[int]]:
    """Pianistic candidates: close, drop-2, rootless (SD/D at high density) and two-hand shell."""
    upper_pcs = [p for p in pcs if p != root_pc]
    keep = upper_pcs[:3]       # 3rd/5th/7th
    extra = upper_pcs[3:]      # tensions

    if density <= 3:
        keep, extra = keep[:2], []
    elif density <= 6:
        extra = extra[:1]
    else:
        extra = extra[:2]

    bass = base_c3 + root_pc
    while bass > BASS_HI:
        bass -= 12
    while bass < BASS_LO:
        bass += 12

    candidates: List[List[int]] = []

    # 1) Root + close upper structure
    compact = _place_upper(keep + extra, top_center=74)
    candidates.append([bass] + compact)

    # 2) Open (drop-2-ish): lower the third voice from the top by an octave
    if len(compact) >= 3:
        spread = compact[:]
        spread[-3] -= 12
        spread.sort()
        while spread[0] <= bass:
            spread[0] += 12
            spread.sort()
        candidates.append([bass] + spread)

    # 3) Rootless: the bass is implied
    if density >= 7 and function_hint in ("SD", "D") and len(keep) >= 2:
        rootless = _place_upper(keep[:2] + extra, top_center=76)
        support = nearest_midi_for_pc(keep[0], base_c3 + 12, lo=45, hi=60)
        while support >= rootless[0]:  # double the guide tone an octave below, never in unison
            support -= 12
        candidates.append([support] + rootless)

    # 4) Two-hand shell + color
    if len(keep) >= 2:
        lh_shell = nearest_midi_for_pc(keep[0], bass + 12, lo=45, hi=60)
        rh = _place_upper(keep[1:] + extra, top_center=78)
        while rh and lh_shell >= rh[0]:
            lh_shell -= 12
        if lh_shell > bass:
            candidates.append([bass, lh_shell] + rh)

    return [list(c) for c in dict.fromkeys(tuple(c) for c in candidates)]


def chord_to_midi_notes(chord: Chord, prev_notes: Optional[List[int]] = None, density: int = 4) -> List[int]:
    """MIDI notes for the chord. Given a previous chord, picks the voicing that moves the least."""
    pcs = extended_pitch_classes(chord, density)
    candidates = build_candidate_voicings(chord.root, pcs, density, function_hint=chord.func)
    if not prev_notes:
        return candidates[0]
    candidates.append(_voice_lead_from_previous(prev_notes, chord.root, pcs))
    return min(candidates, key=lambda c: _weighted_voice_distance(prev_notes, c))
