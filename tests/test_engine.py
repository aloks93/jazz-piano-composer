import random
import struct
import wave

import numpy as np
import pytest

from jazz_composer.composer import (
    CHORD_LENGTHS,
    FORMS,
    CompositionSettings,
    compose,
    format_composition,
    plan_sections,
)
from jazz_composer.generators import (
    STYLE_STANDARD,
    STYLES,
    generate_for_style,
    generate_rhythm_changes,
    generate_standard,
)
from jazz_composer.harmony import cadence_ii_v_i, pick_tensions
from jazz_composer.midi import midi_bytes
from jazz_composer.models import Chord, HarmonyContext
from jazz_composer.modulation import MOD_DIRECT, MOD_STRATEGIES, modulation_plan
from jazz_composer.performance import FEEL_SWING_BASS, FEELS, build_performance
from jazz_composer.project import load_project, save_project
from jazz_composer.scales import suggest_scale
from jazz_composer.synth import iter_performance_pcm, synth_note, write_wav
from jazz_composer.theory import chord_pitch_classes, key_name, parse_chord_symbol, pc, spell
from jazz_composer.voicing import chord_to_midi_notes, extended_pitch_classes


def _composition(seed=1, sections=3, **settings):
    rng = random.Random(seed)
    minor = settings.get("minor", False)
    plan = plan_sections(sections, settings.get("start_key", "C"), 6, rng, minor=minor)
    return compose(plan, CompositionSettings(**settings), rng)


# ------------------------ Theory ------------------------

def test_parse_chord_symbol():
    assert parse_chord_symbol("G7(b9,#9)") == (7, "7", ["b9", "#9"])
    assert parse_chord_symbol("Bbmaj7") == (10, "maj7", [])
    assert parse_chord_symbol("F#m7b5") == (6, "m7b5", [])
    assert pc("Eb") == 3 and pc("A#") == 10
    for bad in ("", "H7", "Cmaj13", "C7(b5)"):
        with pytest.raises(ValueError):
            parse_chord_symbol(bad)


def test_chord_pitch_classes():
    assert chord_pitch_classes(0, "maj7", ("9",)) == [0, 4, 7, 11, 2]
    assert chord_pitch_classes(7, "7", ("b9", "13")) == [7, 11, 2, 5, 8, 4]


def test_spelling_follows_key():
    assert spell(10) == "A#"                       # no key: sharps
    assert spell(10, key=pc("F")) == "Bb"
    assert spell(10, key=pc("C")) == "Bb"          # bVII
    assert spell(6, key=pc("C")) == "F#"           # #IV
    assert spell(1, key=pc("C")) == "Db"           # bII (subV)
    assert spell(6, key=pc("G")) == "F#"
    assert spell(3, key=pc("C"), minor=True) == "Eb"
    assert spell(2, key=pc("Db")) == "D"           # avoids Ebb
    assert key_name(1) == "Db" and key_name(1, minor=True) == "C#m"
    assert Chord(10, "maj7", "IV", "SD", key=pc("F")).symbol == "Bbmaj7"


def test_pick_tensions_palettes():
    assert pick_tensions(2, "D", 3) == ()
    assert pick_tensions(5, "D", 2) == ("9", "13")
    assert pick_tensions(8, "D", 3) == ("9", "13", "#11")
    assert pick_tensions(10, "D", 3) == ("b9", "#9", "b13")
    assert pick_tensions(8, "T", 3, "maj7") == ("9", "13", "#11")
    assert "11" not in pick_tensions(8, "SD", 3, "maj7")     # IVmaj7 takes #11, not 11
    assert pick_tensions(5, "D", 2, "7", altered=True) == ("b9",)
    assert pick_tensions(9, "SD", 3, "m7b5") == ("11",)


def test_suggest_scale():
    C = pc("C")
    assert suggest_scale(Chord(2, "m7", "ii", "SD", key=C))[0] == "D Dorian"
    assert suggest_scale(Chord(4, "m7", "iii", "T", key=C))[0] == "E Phrygian"
    assert suggest_scale(Chord(5, "maj7", "IV", "SD", key=C))[0] == "F Lydian"
    assert suggest_scale(Chord(7, "7", "V", "D", ("b9", "#9"), key=C)) == ("G altered", [7, 8, 10, 11, 1, 3, 5])
    assert suggest_scale(Chord(1, "7", "subV", "D", key=C))[0] == "Db Lydian dominant"
    assert suggest_scale(Chord(2, "m7b5", "iiø", "SD", key=C, minor=True))[0] == "D Locrian"


def test_plain_dominant_to_minor_chord_gets_b9_b13_scale():
    assert suggest_scale(Chord(7, "7", "V", "D", key=0, minor=True))[0] == "G Mixolydian b9 b13"
    assert suggest_scale(Chord(9, "7", "V/ii", "D", key=0))[0] == "A Mixolydian b9 b13"
    assert suggest_scale(Chord(7, "7", "V", "D", key=0))[0] == "G Mixolydian"


# ------------------------ Harmony and generators ------------------------

@pytest.mark.parametrize("minor", [False, True])
@pytest.mark.parametrize("style", STYLES)
@pytest.mark.parametrize("bars", [1, 2, 3, 4, 8, 13, 32])
def test_generators_one_chord_per_bar(style, bars, minor):
    for seed in range(15):
        ctx = HarmonyContext(density=8, rng=random.Random(seed), minor=minor)
        assert len(generate_for_style(ctx, style, 5, bars, 3)) == bars


@pytest.mark.parametrize("minor", [False, True])
@pytest.mark.parametrize("bars", [3, 4, 5, 8, 12, 16])
def test_standard_sections_open_on_the_tonic_and_close_with_a_cadence(bars, minor):
    key = pc("Eb")
    for seed in range(60):
        for density in (3, 6, 9):
            ctx = HarmonyContext(density=density, rng=random.Random(seed), minor=minor)
            chords = generate_standard(ctx, key, bars, 3)
            assert (chords[-1].root, chords[-1].func) == (key, "T"), [c.roman for c in chords]
            assert chords[-2].func == "D", [c.roman for c in chords]
            if bars > 3:
                assert (chords[0].root, chords[0].func) == (key, "T")
            # no chord is repeated back to back
            assert all(a.root != b.root or a.quality != b.quality for a, b in zip(chords, chords[1:]))


def test_standard_sections_are_varied():
    openings = set()
    for seed in range(200):
        ctx = HarmonyContext(density=5, rng=random.Random(seed))
        openings.add(" ".join(c.roman for c in generate_standard(ctx, 0, 8, 2)[:4]))
    assert len(openings) >= 8


def test_minor_cadence_is_half_diminished_altered_minor():
    ctx = HarmonyContext(density=5, rng=random.Random(0), minor=True)
    ii, V, i = cadence_ii_v_i(ctx, pc("C"), 2)
    assert (ii.root, ii.quality) == (pc("D"), "m7b5")
    assert (V.root, V.quality) == (pc("G"), "7") and "b9" in V.tensions and "9" not in V.tensions
    assert (i.root, i.quality) == (pc("C"), "m7")


def test_rhythm_changes_symbols():
    chords = generate_rhythm_changes(pc("Bb"), 3)
    assert len(chords) == 32
    assert chords[1].symbol == "G7(b9,#9)"


@pytest.mark.parametrize("minor", [False, True])
@pytest.mark.parametrize("strategy", MOD_STRATEGIES)
def test_modulation_plan(strategy, minor):
    ctx = HarmonyContext(density=6, rng=random.Random(1), minor=minor)
    plan = modulation_plan(ctx, 0, 7, strategy, 2)
    assert (plan == []) if strategy == MOD_DIRECT else all(isinstance(c, Chord) for c in plan) and plan


# ------------------------ Composition ------------------------

@pytest.mark.parametrize("minor", [False, True])
@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("style", STYLES)
def test_compose_all_forms(form, style, minor):
    comp = _composition(7, sections=4, start_key="F", style=style, form=form, density=9, minor=minor)
    events = [e for b in comp.blocks for e in b.events]
    assert [e.bar for e in events] == list(range(1, len(events) + 1))
    assert all(b.name and b.key_label for b in comp.blocks)
    assert len(comp.playback) == len(events) + len(comp.tail)
    lines = list(format_composition(comp))
    assert [i for _, _, i in lines if i is not None] == list(range(len(comp.chords)))
    assert lines[-1][0] == "=== END ===\n"
    assert all(c.key is not None for c in comp.chords)


def test_seed_makes_composition_reproducible():
    plan = plan_sections(3, "C", 0)
    first = compose(plan, CompositionSettings(density=7, seed=42))
    again = compose(plan, CompositionSettings(density=7, seed=42))
    other = compose(plan, CompositionSettings(density=7))
    assert [c.symbol for c in first.chords] == [c.symbol for c in again.chords]
    assert first.settings.seed == 42 and other.settings.seed is not None


def test_flat_keys_use_flat_names():
    comp = _composition(3, start_key="Eb", density=8, sections=1)
    assert comp.blocks[0].key_label == "Eb"
    roots = {c.symbol[:2] for c in comp.chords}
    assert "Eb" in roots and not roots & {"D#", "A#", "G#"}


def test_replace_chord_updates_guides():
    comp = _composition(5)
    before = comp.blocks[0].events[1].guides
    comp.replace_chord(0, Chord(1, "7", "(edited)", "D", ("#11",), key=0))
    assert comp.chords[0].symbol == "Db7(#11)"
    assert comp.blocks[0].events[1].guides != before
    last = len(comp.chords) - 1
    comp.replace_chord(last, Chord(0, "m6", "(edited)", "T", key=0))
    assert comp.tail[-1].quality == "m6"


def test_project_roundtrip(tmp_path):
    comp = _composition(9, start_key="Ab", minor=True, density=8, form="AABA", sections=4)
    comp.replace_chord(2, Chord(3, "dim7", "(edited)", "D", key=pc("Ab"), minor=True))
    plan = plan_sections(4, "Ab", 5, random.Random(9), minor=True)
    path = tmp_path / "p.jazz.json"
    save_project(str(path), comp.settings, plan, comp, {"bpm": 96})
    settings, sections, loaded, extra = load_project(str(path))
    assert settings == comp.settings and sections == plan and extra == {"bpm": 96}
    assert loaded.chords == comp.chords
    assert [b.name for b in loaded.blocks] == [b.name for b in comp.blocks]
    assert [e.guides for b in loaded.blocks for e in b.events] == [e.guides for b in comp.blocks for e in b.events]


# ------------------------ Voicings ------------------------

@pytest.mark.parametrize("minor", [False, True])
def test_voicings_are_playable(minor):
    for density in (1, 5, 8, 10):
        comp = _composition(density, sections=4, start_key="Eb", density=density, minor=minor)
        prev = None
        for chord in comp.chords:
            notes = chord_to_midi_notes(chord, prev, density)
            assert len(notes) >= 3
            assert notes == sorted(notes) and len(set(notes)) == len(notes)
            assert 36 <= notes[0] and notes[-1] <= 108
            prev = notes


def test_density_color_avoids_clashes():
    altered = Chord(7, "7", "V", "D", ("b9", "#9", "b13"))
    rel = {(p - 7) % 12 for p in extended_pitch_classes(altered, 10)}
    assert 2 not in rel and 9 not in rel      # no natural 9 or 13 over altered tensions
    major = Chord(0, "maj7", "I", "T")
    rel = {p % 12 for p in extended_pitch_classes(major, 10)}
    assert 5 not in rel and 6 in rel          # #11 instead of the natural 11
    minor_V = Chord(7, "7", "V", "D", key=0, minor=True)
    assert extended_pitch_classes(minor_V, 10) == minor_V.pitch_classes


# ------------------------ Performance, audio and MIDI ------------------------

@pytest.mark.parametrize("chord_len", list(CHORD_LENGTHS))
@pytest.mark.parametrize("feel", FEELS)
def test_performance_stays_in_bounds(feel, chord_len):
    comp = _composition(4, density=8, chord_len=chord_len)
    perf = build_performance(comp.playback, 8, feel, bpm=140, seed=3)
    assert perf.total_beats == sum(p.beats for p in comp.playback)
    assert len(perf.voicings) == len(perf.spans) == len(comp.playback)
    assert perf.notes == sorted(perf.notes, key=lambda n: n.start)
    for n in perf.notes:
        assert n.start >= 0 and n.dur > 0 and n.start + n.dur <= perf.total_beats + 1e-9
        assert 21 <= n.midi <= 108 and 1 <= n.velocity <= 127
    assert perf.chord_at(0) == 0 and perf.chord_at(perf.total_beats) is None
    assert perf.chord_at(perf.total_beats - 0.01) == len(comp.playback) - 1
    assert perf.notes == build_performance(comp.playback, 8, feel, bpm=140, seed=3).notes


def test_walking_bass_plays_every_beat_and_lands_on_roots():
    comp = _composition(2, density=6)
    perf = build_performance(comp.playback, 6, FEEL_SWING_BASS, seed=1)
    for (start, _), item in zip(perf.spans, comp.playback):
        on_beat = [n for n in perf.notes if abs(n.start - start) < 0.05 and n.midi <= 55]
        assert any(n.midi % 12 == item.chord.root for n in on_beat)
    bass = [n for n in perf.notes if n.midi <= 55 and n.dur == pytest.approx(0.95)]
    assert len(bass) >= perf.total_beats - 1


def test_synth_note_ends_in_silence():
    wave_ = synth_note(60, 0.5, 44100, 100)
    assert len(wave_) == 22050 and wave_.dtype == np.float32
    assert wave_[-1] == 0.0 and np.abs(wave_).max() < 1.0


def test_pcm_stream_matches_total_length_for_any_chunk_size():
    comp = _composition(6, sections=1, density=6)
    perf = build_performance(comp.playback[:4], 6, FEEL_SWING_BASS, bpm=200)
    small = b"".join(iter_performance_pcm(perf, 200, chunk_seconds=0.1))
    big = b"".join(iter_performance_pcm(perf, 200, chunk_seconds=3.0))
    assert small == big
    assert len(small) == 2 * int(perf.total_beats * 0.3 * 44100)
    assert max(abs(s) for s in struct.unpack(f"<{len(small) // 2}h", small)) > 1000


def test_write_wav(tmp_path):
    comp = _composition(3, sections=1)
    perf = build_performance(comp.playback[:3], 4, bpm=240)
    path = tmp_path / "out.wav"
    write_wav(str(path), perf, bpm=240)
    with wave.open(str(path)) as wf:
        assert wf.getframerate() == 44100 and wf.getnchannels() == 1
        assert wf.getnframes() == 3 * 44100


def test_midi_file_structure():
    comp = _composition(3, sections=1)
    perf = build_performance(comp.playback[:2], 4, FEEL_SWING_BASS, bpm=120)
    data = midi_bytes(perf, 120)
    assert data[:4] == b"MThd" and struct.unpack(">IHHH", data[4:14]) == (6, 0, 1, 480)
    assert data[14:18] == b"MTrk" and struct.unpack(">I", data[18:22])[0] == len(data) - 22
    assert data.endswith(b"\xff\x2f\x00")
    assert data.count(b"\xff\x51\x03" + struct.pack(">I", 500000)[1:]) == 1   # 120 bpm
