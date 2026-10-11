"""Reusable widgets: card, translated dropdown, captioned slider and tooltip."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Sequence

from .palette import Palette


class Tooltip:
    """A short hint shown when the pointer rests on a control."""

    DELAY_MS = 450

    def __init__(self, root: tk.Misc, wraplength: int):
        self._root = root
        self._wrap = wraplength
        self._window: Optional[tk.Toplevel] = None
        self._pending = None
        self.background, self.foreground = "#18212f", "#ffffff"

    def attach(self, widget: tk.Misc, text: str) -> None:
        if not text:
            return
        widget.bind("<Enter>", lambda e: self._schedule(widget, text), add="+")
        widget.bind("<Leave>", lambda e: self.hide(), add="+")
        widget.bind("<ButtonPress>", lambda e: self.hide(), add="+")

    def _schedule(self, widget, text):
        self.hide()
        self._pending = self._root.after(self.DELAY_MS, lambda: self._show(widget, text))

    def _show(self, widget, text):
        self._pending = None
        if not widget.winfo_exists():
            return
        self._window = win = tk.Toplevel(self._root)
        win.wm_overrideredirect(True)
        win.attributes("-topmost", True)
        tk.Label(win, text=text, justify="left", wraplength=self._wrap, background=self.background,
                 foreground=self.foreground, padx=10, pady=7).pack()
        win.update_idletasks()
        x = widget.winfo_rootx()
        y = widget.winfo_rooty() + widget.winfo_height() + 6
        x = max(0, min(x, win.winfo_screenwidth() - win.winfo_reqwidth() - 8))
        if y + win.winfo_reqheight() > win.winfo_screenheight() - 40:
            y = widget.winfo_rooty() - win.winfo_reqheight() - 6
        win.wm_geometry(f"+{x}+{y}")

    def hide(self):
        if self._pending is not None:
            self._root.after_cancel(self._pending)
            self._pending = None
        if self._window is not None:
            self._window.destroy()
            self._window = None


class Card(tk.Frame):
    """A bordered panel with a title. Content goes in `.body`; title-row extras in `.header`."""

    def __init__(self, parent, title: str, pad: int, colors: Palette):
        super().__init__(parent, background=colors.card, highlightthickness=1,
                         highlightbackground=colors.border, highlightcolor=colors.border)
        self.header = ttk.Frame(self, style="Card.TFrame")
        self.header.pack(fill="x", padx=pad, pady=(pad * 2 // 3, 0))
        ttk.Label(self.header, text=title, style="CardTitle.TLabel").pack(side="left")
        self.body = ttk.Frame(self, style="Card.TFrame")
        self.body.pack(fill="both", expand=True, padx=pad, pady=(pad // 2, pad))


class _VarBound:
    """Follows a Tk variable for as long as the widget exists (variables outlive UI rebuilds)."""

    def _follow(self, var: tk.Variable, callback: Callable[[], None]):
        token = var.trace_add("write", lambda *_: self.winfo_exists() and callback())
        self.bind("<Destroy>", lambda e: e.widget is self and var.trace_remove("write", token), add="+")


class Choice(ttk.Combobox, _VarBound):
    """A dropdown that shows translated values but stores the internal value in `var`."""

    def __init__(self, parent, var: tk.StringVar, values: Sequence[str],
                 tr: Callable[[str], str] = lambda v: v, placeholder: str = "",
                 on_pick: Optional[Callable[[str], None]] = None, **kw):
        super().__init__(parent, state="readonly", values=[tr(v) for v in values], **kw)
        self._var, self._values, self._placeholder, self._on_pick = var, list(values), placeholder, on_pick
        self.bind("<<ComboboxSelected>>", self._picked)
        self._follow(var, self._sync)
        self._sync()

    def _picked(self, _event):
        value = self._values[self.current()]
        self._var.set(value)
        self.selection_clear()
        if self._on_pick:
            self._on_pick(value)

    def _sync(self):
        value = self._var.get()
        if value in self._values:
            self.current(self._values.index(value))
        else:
            self.set(self._placeholder)


class LabeledSlider(ttk.Frame, _VarBound):
    """An integer slider that shows its value and, optionally, a caption interpreting it."""

    def __init__(self, parent, label: str, var: tk.IntVar, lo: int, hi: int,
                 caption: Optional[Callable[[int], str]] = None):
        super().__init__(parent, style="Card.TFrame")
        self._var, self._lo, self._hi, self._caption_fn = var, lo, hi, caption
        self.columnconfigure(0, weight=1)
        self.label = ttk.Label(self, text=label, style="Muted.TLabel")
        self.label.grid(row=0, column=0, sticky="w")
        self._value = ttk.Label(self, style="Value.TLabel")
        self._value.grid(row=0, column=1, sticky="e")
        self._pos = tk.DoubleVar(self)
        self.scale = ttk.Scale(self, from_=lo, to=hi, variable=self._pos, command=self._moved,
                               style="Card.Horizontal.TScale")
        self.scale.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        self._caption = None
        if caption:
            self._caption = ttk.Label(self, style="Muted.TLabel")
            self._caption.grid(row=2, column=0, columnspan=2, sticky="w")
        self._follow(var, self._sync)
        self._sync()

    def _moved(self, position: str):
        value = int(round(float(position)))
        if value != self._read():
            self._var.set(value)

    def _read(self) -> int:
        try:
            return max(self._lo, min(self._hi, int(self._var.get())))
        except (tk.TclError, ValueError):
            return self._lo

    def _sync(self):
        value = self._read()
        self._pos.set(value)
        self._value.configure(text=str(value))
        if self._caption is not None:
            self._caption.configure(text=self._caption_fn(value))
