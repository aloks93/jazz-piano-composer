"""A piano keyboard drawn on a Canvas: shows the voicing being played."""

import tkinter as tk
from typing import Dict, Iterable

BLACK_PCS = {1, 3, 6, 8, 10}
WHITE_W, WHITE_H = 14, 52
BLACK_W, BLACK_H = 9, 32
ACTIVE_COLOR = "#f59e0b"


class PianoKeyboard(tk.Canvas):
    def __init__(self, parent, lo: int = 28, hi: int = 96, scale: float = 1.0, background: str = "#ffffff"):
        white_w, white_h = WHITE_W * scale, WHITE_H * scale
        black_w, black_h = BLACK_W * scale, BLACK_H * scale
        whites = [m for m in range(lo, hi + 1) if m % 12 not in BLACK_PCS]
        super().__init__(parent, width=int(len(whites) * white_w) + 1, height=int(white_h) + 1,
                         highlightthickness=0, background=background)
        self._keys: Dict[int, int] = {}      # MIDI note -> rectangle id
        self._base: Dict[int, str] = {}
        self._active: set = set()

        x_of = {m: i * white_w for i, m in enumerate(whites)}
        for m in whites:
            self._add(m, x_of[m], white_w, white_h, "#f8f9fb")
            if m % 12 == 0:  # label the Cs for orientation
                self.create_text(x_of[m] + white_w / 2, white_h - 8 * scale, text=f"C{m // 12 - 1}",
                                 font=("TkDefaultFont", 6), fill="#9aa5b1")
        for m in range(lo, hi + 1):
            if m % 12 in BLACK_PCS and m - 1 in x_of:
                self._add(m, x_of[m - 1] + white_w - black_w / 2, black_w, black_h, "#1f2933")

    def _add(self, midi: int, x: float, w: float, h: float, color: str):
        self._keys[midi] = self.create_rectangle(x, 0, x + w, h, fill=color, outline="#8792a0")
        self._base[midi] = color

    def show(self, notes: Iterable[int]):
        """Light up `notes` (MIDI numbers) and turn the rest off."""
        notes = {n for n in notes if n in self._keys}
        for midi in self._active - notes:
            self.itemconfigure(self._keys[midi], fill=self._base[midi])
        for midi in notes - self._active:
            self.itemconfigure(self._keys[midi], fill=ACTIVE_COLOR)
        self._active = notes
