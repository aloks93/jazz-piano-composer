"""Tests for the UI's display-free parts: translations, presets, palettes and preferences."""

import dataclasses
import json
import random
import re

import pytest

from jazz_composer.composer import CHORD_LENGTHS, FORMS, CompositionSettings, compose, format_composition, plan_sections
from jazz_composer.generators import STYLES
from jazz_composer.harmony import CADENCES
from jazz_composer.models import Chord
from jazz_composer.modulation import MOD_STRATEGIES
from jazz_composer.performance import FEELS
from jazz_composer.scales import SCALES
from jazz_composer.theory import pc
from jazz_composer.ui import preferences
from jazz_composer.ui.help_text import GUIDE
from jazz_composer.ui.i18n import HINTS, LANGS, UI, VALUES_ES, I18n
from jazz_composer.ui.presets import PRESETS
from jazz_composer.ui.palette import DARK, LIGHT


def test_every_engine_value_has_a_spanish_name():
    es = I18n("es")
    for value in [*STYLES, *FORMS, *CADENCES, *CHORD_LENGTHS, *MOD_STRATEGIES, *FEELS, *SCALES, *PRESETS]:
        assert value in VALUES_ES or value == es.v(value), value
    untranslated = [v for v in [*CADENCES, *CHORD_LENGTHS, *SCALES] if v not in VALUES_ES and v != "Plagal (IV-I)"]
    assert not untranslated
    assert es.v("Minor") == "Menor" and I18n("en").v("Minor") == "Minor"
    assert es.v("Dorian") == "dórica" and es.v("altered") == "alterada"


def test_ui_texts_and_hints_exist_in_both_languages():
    assert all(len(pair) == 2 and all(pair) for pair in UI.values())
    assert set(GUIDE) == set(LANGS)
    for lang in LANGS:
        i18n = I18n(lang)
        for group, items in HINTS:
            assert i18n.t(group)
            for key, en, es in items:
                assert i18n.t(key) and i18n.hint(key) == (es if lang == "es" else en)
    assert I18n("xx").lang == "en"
    assert I18n("en").t("status_generated", bars=8, seed=3) == "8 bars generated  ·  seed 3"


@pytest.mark.parametrize("minor", [False, True])
@pytest.mark.parametrize("style", STYLES)
def test_panel_translates_without_leaving_english_behind(style, minor):
    rng = random.Random(4)
    plan = plan_sections(4, "C", 10, rng, minor=minor)
    comp = compose(plan, CompositionSettings(style=style, density=9, minor=minor), rng)
    comp.replace_chord(0, Chord(0, "maj7", "(edited)", "T", key=0))
    english = "".join(line for line, _, _ in format_composition(comp))
    spanish = "".join(line for line, _, _ in format_composition(comp, I18n("es").v))
    assert "=== END ===" in english and "=== FIN ===" in spanish and "(editado)" in spanish
    assert len(spanish.splitlines()) == len(english.splitlines())
    for word in ("LEGEND", "Tonic", "Style", "Seed", "HOME KEY", "FINAL CADENCE", "Dorian", "Mixolydian",
                 "Lydian", "Ionian", "altered", "melodic minor", "edited", "pivot", "Dominant chain"):
        assert not re.search(rf"\b{word}\b", spanish), word


def test_presets_use_valid_engine_values():
    for name, p in PRESETS.items():
        assert p["style"] in STYLES and p["form"] in FORMS and p["cadence"] in CADENCES, name
        assert p["chord_len"] in CHORD_LENGTHS and p["feel"] in FEELS, name
        assert 1 <= p["density"] <= 10 and 0 <= p["mod_density"] <= 10 and 40 <= p["bpm"] <= 260, name
        pc(p["key"])


def test_light_and_dark_palettes_are_complete_and_readable():
    def luminance(color):
        r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    for palette in (LIGHT, DARK):
        for field in dataclasses.fields(palette):
            value = getattr(palette, field.name)
            colors = value.values() if isinstance(value, dict) else [value]
            assert all(re.fullmatch(r"#[0-9a-f]{6}", c) for c in colors), field.name
        assert abs(luminance(palette.text) - luminance(palette.card)) > 0.5
        for color in palette.func_colors.values():
            assert abs(luminance(color) - luminance(palette.field)) > 0.25
    assert luminance(DARK.bg) < 0.1 < 0.8 < luminance(LIGHT.bg)
    assert set(LIGHT.func_colors) == set(DARK.func_colors)


def test_preferences_roundtrip_and_fallbacks(tmp_path, monkeypatch):
    path = tmp_path / "prefs.json"
    monkeypatch.setattr(preferences, "PREFERENCES_PATH", path)
    assert preferences.load_preferences()["theme"] == "light"
    assert preferences.load_preferences()["lang"] in LANGS
    preferences.save_preferences({"lang": "es", "theme": "dark"})
    assert preferences.load_preferences() == {"lang": "es", "theme": "dark"}
    path.write_text(json.dumps({"lang": "fr", "theme": "neon"}), encoding="utf-8")
    assert preferences.load_preferences()["theme"] == "light"
    path.write_text("not json", encoding="utf-8")
    assert preferences.load_preferences()["lang"] in LANGS
