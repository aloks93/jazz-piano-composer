"""Look and feel: fonts and ttk styles for the light and dark palettes."""

import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from .palette import PALETTES


def enable_dpi_awareness() -> None:
    """On Windows, keeps the window from looking blurry under display scaling."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def _pick_family(root: tk.Misc, candidates, fallback: str) -> str:
    available = set(tkfont.families(root))
    return next((f for f in candidates if f in available), fallback)


class Theme:
    """Applies the styles; exposes the active palette (`colors`), fonts and `px()` for scaled sizes."""

    def __init__(self, root: tk.Tk, mode: str = "light"):
        self.root = root
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96.0)

        default = tkfont.nametofont("TkDefaultFont")
        family = _pick_family(root, ("Segoe UI", "Helvetica Neue", "Noto Sans", "DejaVu Sans"), default.actual("family"))
        default.configure(family=family, size=10)
        tkfont.nametofont("TkTextFont").configure(family=family, size=10)
        mono_family = _pick_family(root, ("Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono"), "Courier")
        self.mono = tkfont.Font(root, family=mono_family, size=10)
        self.mono_bold = tkfont.Font(root, family=mono_family, size=10, weight="bold")
        self.small = tkfont.Font(root, family=family, size=9)
        self.bold = tkfont.Font(root, family=family, size=10, weight="bold")
        self.title = tkfont.Font(root, family=family, size=11, weight="bold")
        self.brand = tkfont.Font(root, family=family, size=15, weight="bold")

        ttk.Style(root).theme_use("clam")
        self.apply(mode)

    def px(self, n: float) -> int:
        return int(round(n * self.scale))

    def apply(self, mode: str) -> None:
        """Switch palette. Widgets created afterwards pick it up, so the UI is rebuilt on change."""
        self.mode = mode if mode in PALETTES else "light"
        self.colors = c = PALETTES[self.mode]
        px, root = self.px, self.root

        root.configure(background=c.bg)
        for option, value in (("background", c.field), ("foreground", c.text),
                              ("selectBackground", c.accent), ("selectForeground", "#ffffff")):
            root.option_add(f"*TCombobox*Listbox.{option}", value)
        root.option_add("*TCombobox*Listbox.font", tkfont.nametofont("TkDefaultFont"))

        s = ttk.Style(root)
        s.configure(".", background=c.bg, foreground=c.text, bordercolor=c.border, lightcolor=c.border,
                    darkcolor=c.border, focuscolor=c.accent, troughcolor=c.trough,
                    insertcolor=c.text, arrowcolor=c.text)
        s.configure("Card.TFrame", background=c.card)
        s.configure("Card.TLabel", background=c.card, foreground=c.text)
        s.configure("CardTitle.TLabel", background=c.card, foreground=c.text, font=self.title)
        s.configure("Muted.TLabel", background=c.card, foreground=c.muted, font=self.small)
        s.configure("Value.TLabel", background=c.card, foreground=c.accent, font=self.bold)
        s.configure("Now.TLabel", background=c.card, foreground=c.text, font=self.bold)
        s.configure("Status.TLabel", background=c.status, foreground=c.muted, padding=(px(12), px(5)))
        s.configure("Card.TCheckbutton", background=c.card, foreground=c.text, indicatorsize=px(14),
                    indicatormargin=px(4), indicatorbackground=c.field, indicatorforeground=c.text)
        s.map("Card.TCheckbutton", background=[("active", c.card)],
              indicatorbackground=[("selected", c.accent)], indicatorforeground=[("selected", "#ffffff")])

        for style in ("TButton", "TMenubutton"):
            s.configure(style, padding=(px(12), px(6)), background=c.button, foreground=c.text, relief="flat")
            s.map(style, background=[("disabled", c.button_disabled), ("active", c.button_hover)],
                  foreground=[("disabled", c.text_disabled)])
        s.configure("Accent.TButton", padding=(px(20), px(8)), background=c.accent, foreground="#ffffff",
                    font=self.bold, bordercolor=c.accent, lightcolor=c.accent, darkcolor=c.accent)
        s.map("Accent.TButton", background=[("disabled", c.button_disabled), ("active", c.accent_hover)],
              foreground=[("disabled", c.text_disabled)])
        s.configure("Header.TButton", padding=(px(12), px(6)), background=c.header_button, foreground="#ffffff",
                    bordercolor=c.header_button, lightcolor=c.header_button, darkcolor=c.header_button)
        s.map("Header.TButton", background=[("active", c.header_button_hover)])

        s.configure("TCombobox", padding=px(4), arrowsize=px(13), fieldbackground=c.field,
                    background=c.button, foreground=c.text)
        s.map("TCombobox",
              fieldbackground=[("disabled", c.button_disabled), ("readonly", c.field)],
              selectbackground=[("readonly", c.field)], selectforeground=[("readonly", c.text)],
              foreground=[("disabled", c.text_disabled)], background=[("active", c.button_hover)])
        s.configure("TEntry", padding=px(4), fieldbackground=c.field, foreground=c.text)
        s.configure("TSpinbox", padding=px(4), fieldbackground=c.field, foreground=c.text,
                    background=c.button, arrowsize=px(12))
        s.configure("TScrollbar", background=c.button, troughcolor=c.bg, arrowcolor=c.muted)
        s.map("TScrollbar", background=[("active", c.button_hover)])
        s.configure("Card.Horizontal.TScale", background=c.accent, bordercolor=c.border, lightcolor=c.accent,
                    darkcolor=c.accent, troughcolor=c.trough, gripcount=0, sliderlength=px(16))
        s.map("Card.Horizontal.TScale", background=[("active", c.accent_hover)])

        s.configure("Treeview", background=c.field, fieldbackground=c.field, foreground=c.text,
                    rowheight=px(25), borderwidth=0)
        s.configure("Treeview.Heading", background=c.button, foreground=c.muted, font=self.small,
                    relief="flat", padding=(px(4), px(4)))
        s.map("Treeview", background=[("selected", c.accent_soft)], foreground=[("selected", c.text)])
        s.map("Treeview.Heading", background=[("active", c.button_hover)])
        s.configure("TNotebook", background=c.bg)
        s.configure("TNotebook.Tab", padding=(px(14), px(6)), background=c.button, foreground=c.muted)
        s.map("TNotebook.Tab", background=[("selected", c.card)], foreground=[("selected", c.text)])
