"""Light and dark color palettes (no Tk dependency)."""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Palette:
    bg: str                 # window background
    card: str               # panels
    field: str              # inputs and the result panel
    border: str
    text: str
    muted: str
    header: str
    header_button: str
    header_button_hover: str
    header_muted: str
    accent: str
    accent_hover: str
    accent_soft: str        # selected table row
    button: str
    button_hover: str
    button_disabled: str
    text_disabled: str
    trough: str
    status: str
    now_playing: str
    tooltip: str
    tooltip_text: str
    func_colors: Dict[str, str]   # panel line colors by harmonic function


LIGHT = Palette(
    bg="#eef1f5", card="#ffffff", field="#fbfcfd", border="#d5dae1", text="#1f2933", muted="#6b7785",
    header="#18212f", header_button="#283548", header_button_hover="#374a63", header_muted="#9fb0c3",
    accent="#2563eb", accent_hover="#1d4ed8", accent_soft="#dbe7ff",
    button="#f5f6f8", button_hover="#e3e8ef", button_disabled="#eef0f3", text_disabled="#a3acb8",
    trough="#dde3ea", status="#dfe4ea", now_playing="#ffe9a8", tooltip="#18212f", tooltip_text="#ffffff",
    func_colors={"FUNC_T": "#1b7f2a", "FUNC_SD": "#1b4f9c", "FUNC_D": "#b3261e", "FUNC_BR": "#6a1b9c"},
)

DARK = Palette(
    bg="#12161d", card="#1b212b", field="#151a22", border="#2f3846", text="#e4e8ee", muted="#93a0b1",
    header="#0c0f14", header_button="#232b38", header_button_hover="#2f3a4b", header_muted="#8794a6",
    accent="#4f8cff", accent_hover="#6ea0ff", accent_soft="#263b63",
    button="#262e3b", button_hover="#313b4b", button_disabled="#1f252f", text_disabled="#5d6878",
    trough="#2a3340", status="#0f1319", now_playing="#5a4a12", tooltip="#e4e8ee", tooltip_text="#12161d",
    func_colors={"FUNC_T": "#6ed58a", "FUNC_SD": "#7db4ff", "FUNC_D": "#ff8a80", "FUNC_BR": "#cf9cf5"},
)

PALETTES = {"light": LIGHT, "dark": DARK}
