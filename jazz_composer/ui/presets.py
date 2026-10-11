"""Ready-made examples: parameter combinations to get started with one click."""

from ..generators import STYLE_BLUES, STYLE_COLTRANE, STYLE_JAZZ_BLUES, STYLE_MODAL, STYLE_STANDARD
from ..harmony import CADENCE_AUTHENTIC, CADENCE_HALF, CADENCE_PLAGAL
from ..performance import FEEL_BLOCK, FEEL_BOSSA, FEEL_SWING, FEEL_SWING_BASS

_DEFAULTS = dict(key="C", minor=False, style=STYLE_STANDARD, form="Free", cadence=CADENCE_AUTHENTIC,
                 chord_len="1 bar", density=5, mod_density=3, feel=FEEL_SWING_BASS, bpm=120,
                 velocity=100, sections=3)

_PRESETS = {
    "Classic standard (AABA)": dict(key="F", form="AABA", density=5, mod_density=4, bpm=140, sections=4),
    "Minor ballad": dict(key="C", minor=True, density=7, mod_density=2, feel=FEEL_BLOCK, bpm=66,
                         velocity=84, cadence=CADENCE_PLAGAL),
    "Twelve-bar blues": dict(key="F", style=STYLE_BLUES, form="12-bar blues", density=4, mod_density=0,
                             bpm=116, sections=1),
    "Minor jazz blues": dict(key="C", minor=True, style=STYLE_JAZZ_BLUES, form="12-bar blues", density=6,
                             mod_density=0, bpm=132, sections=1),
    "Bebop · Rhythm Changes": dict(key="Bb", form="Rhythm Changes", density=8, mod_density=0, bpm=200,
                                   chord_len="2 beats (half bar)", sections=1),
    "Bossa nova tune": dict(key="D", form="AB", density=6, mod_density=3, feel=FEEL_BOSSA, bpm=132, sections=2),
    "Dorian modal": dict(key="D", minor=True, style=STYLE_MODAL, density=6, mod_density=0, feel=FEEL_SWING,
                         bpm=126, chord_len="2 bars", sections=2, cadence=CADENCE_HALF),
    "Giant Steps (Coltrane)": dict(key="B", style=STYLE_COLTRANE, density=4, mod_density=0, bpm=220,
                                   chord_len="2 beats (half bar)", sections=2),
    "For study (bare bones)": dict(key="C", density=2, mod_density=0, feel=FEEL_BLOCK, bpm=84, sections=2),
}

PRESETS = {name: {**_DEFAULTS, **values} for name, values in _PRESETS.items()}
