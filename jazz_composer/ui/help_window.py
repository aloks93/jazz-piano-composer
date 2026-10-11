"""Help window: what each function does (one sentence each) and a quick guide."""

import tkinter as tk
from tkinter import ttk

from .help_text import GUIDE
from .i18n import HINTS, I18n
from .theme import Theme


def _text_tab(notebook: ttk.Notebook, theme: Theme):
    """A tab holding a scrollable Text; returns (frame, text)."""
    colors = theme.colors
    frame = ttk.Frame(notebook)
    text = tk.Text(frame, wrap="word", relief="flat", font="TkTextFont", background=colors.card,
                   foreground=colors.text, padx=theme.px(18), pady=theme.px(14), spacing1=2, spacing3=3)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)
    text.tag_configure("group", font=theme.title, foreground=colors.accent,
                       spacing1=theme.px(12), spacing3=theme.px(4))
    text.tag_configure("name", font=theme.bold)
    text.tag_configure("heading", font=theme.bold, spacing1=theme.px(8))
    return frame, text


def show_help(root: tk.Misc, i18n: I18n, theme: Theme) -> tk.Toplevel:
    win = tk.Toplevel(root, background=theme.colors.bg)
    win.title(i18n.t("help_title"))
    win.geometry(f"{theme.px(760)}x{theme.px(620)}")
    win.transient(root)

    notebook = ttk.Notebook(win)
    notebook.pack(fill="both", expand=True, padx=theme.px(10), pady=theme.px(10))

    frame, functions = _text_tab(notebook, theme)
    notebook.add(frame, text=i18n.t("tab_functions"))
    for group, items in HINTS:
        functions.insert("end", i18n.t(group).split("  ")[0] + "\n", "group")
        for key, _, _ in items:
            functions.insert("end", i18n.t(key).strip("✦▶■ …") + "  ", "name")
            functions.insert("end", "— " + i18n.hint(key) + "\n")
    functions.configure(state="disabled")

    frame, guide = _text_tab(notebook, theme)
    notebook.add(frame, text=i18n.t("tab_guide"))
    for line in GUIDE[i18n.lang].splitlines():
        guide.insert("end", line + "\n", "heading" if line.isupper() else "")
    guide.configure(state="disabled")
    return win
