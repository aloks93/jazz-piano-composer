"""Modulations: choosing the target key, the strategy and the bridge chords."""

from typing import List, Tuple

from .harmony import make_chord
from .models import Chord, HarmonyContext, clamp
from .theory import degree_root, diatonic_table, key_name, scale_pcs

MOD_DIATONIC_PIVOT = "Diatonic pivot"
MOD_CHROMATIC_PIVOT = "Chromatic pivot"
MOD_DIRECT = "Direct"
MOD_TRITONE = "Tritone (SubV)"
MOD_DOMINANT_CHAIN = "Dominant chain"
MOD_COLTRANE = "Coltrane (major 3rd)"
MOD_STRATEGIES = [MOD_DIATONIC_PIVOT, MOD_CHROMATIC_PIVOT, MOD_DIRECT, MOD_TRITONE,
                  MOD_DOMINANT_CHAIN, MOD_COLTRANE]


def common_diatonic_pivots(key_a: int, key_b: int, minor: bool = False) -> List[Tuple[int, str]]:
    """Diatonic chords of `key_a` whose root also belongs to `key_b`."""
    common_tones = set(scale_pcs(key_a, minor)) & set(scale_pcs(key_b, minor))
    table = diatonic_table(minor)
    pivots = []
    for d in [2, 4, 6, 3, 1, 5]:  # order of preference
        r = degree_root(key_a, d, minor)
        if r in common_tones:
            pivots.append((r, table[d][0]))
    return list(dict.fromkeys(pivots))


def modulation_plan(ctx: HarmonyContext, current_key: int, target_key: int, strategy: str, tension: int) -> List[Chord]:
    """Bridge chords leading from `current_key` to `target_key` (empty = direct modulation)."""
    V_target = (target_key + 7) % 12

    def dom(root, roman, altered=False):
        return make_chord(ctx, root, "7", roman, "D", tension, altered=altered)

    if strategy == MOD_DIATONIC_PIVOT:
        pivots = common_diatonic_pivots(current_key, target_key, ctx.minor)
        if pivots:
            r, q = ctx.rng.choice(pivots)
            return [make_chord(ctx, r, q, "Pivot (diatonic)", "Bridge", -1)]
        strategy = MOD_CHROMATIC_PIVOT
    if strategy == MOD_CHROMATIC_PIVOT:
        return [
            make_chord(ctx, (current_key + 5) % 12, "m7", "iv (borrowed pivot)", "Bridge", max(1, tension - 1)),
            dom(V_target, "V (prep new key)", ctx.minor),
        ]
    if strategy == MOD_TRITONE:
        return [dom((V_target + 6) % 12, "SubV7 (tritone)")]
    if strategy == MOD_DOMINANT_CHAIN:
        return [dom((V_target + 7) % 12, "V/V (chain)"), dom(V_target, "V (chain)", ctx.minor)]
    if strategy == MOD_COLTRANE:
        mid = (current_key + 4) % 12
        return [dom((mid + 7) % 12, f"V → {key_name(mid)} (Coltrane)")]
    return []


def pick_modulation_target(ctx: HarmonyContext, start_key: int, cur_key: int, mod_density: int) -> int:
    """Target key: low density favors close keys; high density allows distant leaps."""
    md = clamp(int(mod_density), 0, 10)
    close_steps = (7, 5, 3, 10) if ctx.minor else (7, 5, 9, 2)   # v, iv, bIII, bVII / V, IV, vi, ii
    mid_steps = (8, 2, 6, 9) if ctx.minor else (10, 3, 6, 4)
    close = [(start_key + i) % 12 for i in close_steps]
    mid = [(start_key + i) % 12 for i in mid_steps]
    far = [(cur_key + 4) % 12, (cur_key + 8) % 12,          # major-third cycle
           (start_key + 1) % 12, (start_key + 11) % 12]     # semitones
    if md <= 2:
        pool = close
    elif md <= 6:
        pool = close + mid
    else:
        pool = close + mid + far
    pool = [p for p in pool if p != cur_key]
    return ctx.rng.choice(pool) if pool else cur_key


def pick_modulation_strategy(ctx: HarmonyContext, mod_density: int) -> str:
    """Bridge strategy, weighted by modulation density."""
    md = clamp(int(mod_density), 0, 10)
    if md == 0:
        return MOD_DIRECT
    low = [MOD_DIATONIC_PIVOT, MOD_DIRECT]
    mid = [MOD_CHROMATIC_PIVOT, MOD_DOMINANT_CHAIN, MOD_DIATONIC_PIVOT]
    high = [MOD_TRITONE, MOD_COLTRANE, MOD_DOMINANT_CHAIN, MOD_CHROMATIC_PIVOT]
    if md <= 3:
        pool = low + low + mid
    elif md <= 7:
        pool = low + mid + mid + high
    else:
        pool = mid + high + high
    return ctx.rng.choice(pool)
