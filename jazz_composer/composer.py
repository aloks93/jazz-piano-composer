"""Full composition: sections -> blocks -> form -> final cadence. No UI dependencies."""

import random
from dataclasses import dataclass, field, replace
from typing import Callable, Iterator, List, Optional, Tuple

from .generators import (
    STYLE_BLUES,
    STYLE_JAZZ_BLUES,
    STYLE_STANDARD,
    generate_blues,
    generate_for_style,
    generate_rhythm_changes,
)
from .harmony import CADENCES, cadence_tail
from .models import Block, Chord, Event, HarmonyContext, PlayChord, Section, clamp
from .modulation import (
    MOD_DIRECT,
    MOD_STRATEGIES,
    modulation_plan,
    pick_modulation_strategy,
    pick_modulation_target,
)
from .scales import scale_parts
from .theory import KEY_NAMES, guide_motion, key_name, pc

FORM_FREE = "Free"
FORM_BLUES = "12-bar blues"
FORM_RHYTHM_CHANGES = "Rhythm Changes"
FORMS = [FORM_FREE, "AABA", "ABAC", "AB", "Through-composed", FORM_BLUES, FORM_RHYTHM_CHANGES]

LENGTH_ONE_BAR = "1 bar"
# UI label -> beats per chord (None = adaptive, by function)
CHORD_LENGTHS = {
    LENGTH_ONE_BAR: 4,
    "2 beats (half bar)": 2,
    "2 bars": 8,
    "3 beats (3/4 bar)": 3,
    "Adaptive (by function)": None,
}

VELOCITY_ACCENT = {"D": 10, "SD": 2, "T": -8}


@dataclass
class CompositionSettings:
    start_key: str = "C"
    style: str = STYLE_STANDARD
    form: str = FORM_FREE
    cadence: str = CADENCES[0]
    chord_len: str = LENGTH_ONE_BAR
    density: int = 4
    base_velocity: int = 100
    minor: bool = False
    seed: Optional[int] = None  # None = random; compose() records the one it used


@dataclass
class Composition:
    settings: CompositionSettings
    blocks: List[Block]
    tail: List[Chord] = field(default_factory=list)

    def __post_init__(self):
        self.annotate()

    @property
    def chords(self) -> List[Chord]:
        return [e.chord for b in self.blocks for e in b.events] + self.tail

    @property
    def playback(self) -> List[PlayChord]:
        base = self.settings.base_velocity
        return [
            PlayChord(c, clamp(base + VELOCITY_ACCENT.get(c.func, 0), 1, 127),
                      beats_for(self.settings.chord_len, c.func))
            for c in self.chords
        ]

    def annotate(self) -> None:
        """Number the bars and compute guide-tone motion (3rd/7th) between chords."""
        bar = 1
        prev = None
        for block in self.blocks:
            for e in block.events:
                e.bar = bar
                bar += 1
                e.guides = guide_motion(prev.guides, e.chord.guides, e.chord.spell) if prev else ""
                prev = e.chord

    def replace_chord(self, index: int, chord: Chord) -> None:
        """Manual reharmonization: swap chord `index` (in the order of `chords`)."""
        events = [e for b in self.blocks for e in b.events]
        if index < len(events):
            events[index].chord = chord
        else:
            self.tail[index - len(events)] = chord
        self.annotate()


def beats_for(chord_len: str, func: str) -> float:
    beats = CHORD_LENGTHS.get(chord_len, 4)
    if beats is None:  # adaptive: dominants resolve faster
        return 2 if func == "D" else 4
    return beats


def _in_key(chords: List[Chord], key: int, minor: bool) -> List[Chord]:
    return [replace(c, key=key, minor=minor) for c in chords]


# ------------------------ Section plan ------------------------

def plan_sections(n: int, start_key: str, mod_density: int, rng: Optional[random.Random] = None,
                  minor: bool = False) -> List[Section]:
    """Initial sections. `mod_density` (0..10) controls how many modulate and how far."""
    ctx = HarmonyContext(rng=rng or random.Random(), minor=minor)
    mod_density = clamp(int(mod_density), 0, 10)
    start_pc = pc(start_key)
    cur = start_key
    sections: List[Section] = []

    for idx in range(1, n + 1):
        do_mod = idx != 1 and ctx.rng.random() < mod_density / 10.0
        # With 2 sections, keep at least one stable unless the density is high
        if n <= 2 and idx == n:
            do_mod = do_mod and mod_density >= 5

        if do_mod:
            target = KEY_NAMES[pick_modulation_target(ctx, start_pc, pc(cur), mod_density)]
            strategy = pick_modulation_strategy(ctx, mod_density)
        else:
            target, strategy = cur, MOD_DIRECT

        return_to_start = idx == 3
        sections.append(Section(
            bars=8, key_name=cur, tension=min(idx, 3),
            do_modulate=do_mod, target_key=target, mod_strategy=strategy,
            return_to_start=return_to_start,
        ))
        if do_mod:
            cur = target
        if return_to_start:
            cur = start_key
    return sections


def recompute_keys(sections: List[Section], start_key: str) -> None:
    """Propagate each section's entry key through modulations and returns."""
    cur = start_key
    for sec in sections:
        sec.key_name = cur
        if sec.do_modulate:
            cur = sec.target_key
        if sec.return_to_start:
            cur = start_key


# ------------------------ Composition ------------------------

def _section_blocks(ctx: HarmonyContext, sections: List[Section], style: str, start_pc: int) -> List[Block]:
    blocks: List[Block] = []
    current_key = start_pc
    for sec in sections:
        chords: List[Chord] = []
        header = None
        if sec.do_modulate:
            target = pc(sec.target_key)
            bridge = modulation_plan(ctx, current_key, target, sec.mod_strategy, sec.tension)
            if bridge:
                header = f"[Bridge: {sec.mod_strategy} → {key_name(target, ctx.minor)}]"
                chords += bridge
            current_key = target
        chords += generate_for_style(ctx, style, current_key, sec.bars, sec.tension)
        blocks.append(Block([Event(c) for c in _in_key(chords, current_key, ctx.minor)],
                            header=header, key_label=key_name(current_key, ctx.minor)))
        if sec.return_to_start:
            current_key = start_pc
    return blocks


def _apply_form(ctx: HarmonyContext, form: str, style: str, blocks: List[Block],
                sections: List[Section], start_pc: int) -> List[Block]:
    """Order/repeat the blocks according to the form and name them."""
    def arrange(letters: str, extra: List[Block]) -> List[Block]:
        by_letter = dict(zip("ABC", blocks))
        out = []
        for letter in letters:
            b = by_letter[letter].copy()
            b.name = letter
            out.append(b)
        return out + extra

    first_tension = sections[0].tension if sections else 2

    if form == "AABA" and len(blocks) >= 4:
        out = arrange("AABA", blocks[3:])
    elif form == "AABA" and len(blocks) >= 2:
        out = arrange("ABA", [])
    elif form == "ABAC" and len(blocks) >= 3:
        out = arrange("ABAC", blocks[3:])
    elif form == "AB" and len(blocks) >= 2:
        out = arrange("AB", [])
    elif form == FORM_BLUES:
        variant = STYLE_JAZZ_BLUES if style == STYLE_JAZZ_BLUES else STYLE_BLUES
        chords = _in_key(generate_blues(ctx, start_pc, 12, first_tension, variant), start_pc, ctx.minor)
        out = [Block([Event(c) for c in chords], name="BLUES", key_label=key_name(start_pc, ctx.minor))]
    elif form == FORM_RHYTHM_CHANGES:
        chords = _in_key(generate_rhythm_changes(start_pc, first_tension), start_pc, False)
        out = [Block([Event(c) for c in chords[i:i + 8]], name=part, key_label=key_name(start_pc))
               for i, part in zip(range(0, 32, 8), "AABA")]
    else:
        out = blocks

    for i, b in enumerate(out, start=1):
        if not b.name:
            b.name = f"S{i}"
    return out


def compose(sections: List[Section], settings: CompositionSettings,
            rng: Optional[random.Random] = None) -> Composition:
    """Generate the full composition. The same seed (`settings.seed` or `rng`) gives the same result."""
    if rng is None:
        seed = settings.seed if settings.seed is not None else random.randrange(1_000_000)
        settings = replace(settings, seed=seed)
        rng = random.Random(seed)
    ctx = HarmonyContext(density=settings.density, rng=rng, minor=settings.minor)
    start_pc = pc(settings.start_key)

    blocks = _section_blocks(ctx, sections, settings.style, start_pc)
    blocks = _apply_form(ctx, settings.form, settings.style, blocks, sections, start_pc)

    last_tension = sections[-1].tension if sections else 2
    tail = _in_key(cadence_tail(ctx, start_pc, settings.cadence, max(0, last_tension)), start_pc, ctx.minor)
    return Composition(settings, blocks, tail)


# ------------------------ Presentation ------------------------

FUNC_TAGS = {"T": "FUNC_T", "SD": "FUNC_SD", "D": "FUNC_D"}
LEGEND = "T = Tonic (stability) | SD = Subdominant (preparation) | D = Dominant (tension)"


def format_composition(comp: Composition,
                       tr: Callable[[str], str] = lambda text: text) -> Iterator[Tuple[str, str, Optional[int]]]:
    """Lines of the educational panel: (text, style tag, chord index or None).

    `tr` translates labels and names (the UI uses it to show the panel in another language).
    """
    s = comp.settings

    def scale(c: Chord) -> str:
        root, scale_name, _ = scale_parts(c)
        return f"{root} {tr(scale_name)}"

    def bridge(header: str) -> str:
        for strategy in MOD_STRATEGIES:
            header = header.replace(strategy, tr(strategy))
        return header

    yield f"=== {tr('LEGEND')} ===\n", "HDR", None
    yield tr(LEGEND) + "\n\n", "MONO", None
    yield (f"{tr('Style')}: {tr(s.style)} | {tr('Form')}: {tr(s.form)} | "
           f"{tr('Final cadence')}: {tr(s.cadence)} | {tr('Chord length')}: {tr(s.chord_len)}\n"), "MONO", None
    if s.seed is not None:
        yield f"{tr('Seed')}: {s.seed}\n", "MONO", None
    yield f"\n=== {tr('HOME KEY')}: {key_name(pc(s.start_key), s.minor)} ===\n\n", "MONO", None

    index = 0
    for block in comp.blocks:
        yield f"--- {block.name}{f' ({block.key_label})' if block.key_label else ''} ---\n", "HDR", None
        if block.header:
            yield bridge(block.header) + "\n", "FUNC_BR", None
        for e in block.events:
            c = e.chord
            yield (f"Bar {e.bar:02d}: {c.symbol:<17} | {tr(c.roman):<22} | Func: {c.func:<6} | "
                   f"{scale(c):<24} | {e.guides}\n",
                   FUNC_TAGS.get(c.func, "FUNC_BR"), index)
            index += 1
        yield "\n", "MONO", None

    if comp.tail:
        yield f"--- {tr('FINAL CADENCE')} ---\n", "HDR", None
        for c in comp.tail:
            yield (f"        {c.symbol:<17} | {tr(c.roman):<22} | Func: {c.func:<6} | {scale(c)}\n",
                   FUNC_TAGS.get(c.func, "FUNC_BR"), index)
            index += 1
    yield f"=== {tr('END')} ===\n", "HDR", None
