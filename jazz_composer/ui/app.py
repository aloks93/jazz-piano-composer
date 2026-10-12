"""Tkinter interface: collects settings, calls the engine and shows the result.

Tk variables always hold the engine's internal (English) values; widgets display them
translated. That is why switching language or theme just rebuilds the widgets: no state is lost.
"""

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Dict, List, Optional

from .. import APP_NAME, project
from ..audio import AudioPlayer
from ..composer import (
    CHORD_LENGTHS,
    FORMS,
    Composition,
    CompositionSettings,
    compose,
    format_composition,
    plan_sections,
    recompute_keys,
)
from ..generators import STYLES
from ..harmony import CADENCES
from ..midi import write_midi
from ..models import Chord, Section, clamp
from ..modulation import MOD_STRATEGIES
from ..performance import FEELS, Performance, build_performance
from ..scales import scale_note_names, scale_parts
from ..synth import beat_seconds, iter_performance_pcm, write_wav
from ..theory import (
    KEY_NAMES,
    QUALITY_CHORD_TONES,
    TENSION_INTERVALS,
    key_name,
    parse_chord_symbol,
    pc,
)
from . import help_window
from .i18n import LANGS, I18n
from .keyboard import PianoKeyboard
from .preferences import load_preferences, save_preferences
from .presets import PRESETS
from .theme import Theme, enable_dpi_awareness
from .widgets import Card, Choice, LabeledSlider, Tooltip

MODE_MAJOR, MODE_MINOR = "Major", "Minor"
MODES = [MODE_MAJOR, MODE_MINOR]


def _int(var: tk.Variable, default: int, lo: int, hi: int) -> int:
    """Read an integer from a widget, tolerating empty or invalid fields."""
    try:
        return clamp(int(var.get()), lo, hi)
    except (tk.TclError, ValueError):
        return default


class App:
    def __init__(self, root: tk.Tk, lang: Optional[str] = None, theme: Optional[str] = None):
        self.root = root
        self.preferences = load_preferences()
        self.i18n = I18n(lang or self.preferences["lang"])
        self.theme = Theme(root, theme or self.preferences["theme"])
        self.tooltip = Tooltip(root, wraplength=self.theme.px(340))

        self.sections: List[Section] = []
        self.composition: Optional[Composition] = None
        self._selected = 0                           # section shown in the editor
        self._loading = False                        # True while values are loaded into the editor
        self._chord_lines: Dict[int, int] = {}       # chord index -> panel line
        self._performance: Optional[Performance] = None
        self._now_playing: Optional[int] = None
        self._player_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._audio = AudioPlayer()

        self._create_variables()
        self._build_ui()
        self.reset_sections(announce=False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------ State ------------------------

    def _create_variables(self):
        r = self.root
        self.preset_var = tk.StringVar(r, "")
        self.start_key = tk.StringVar(r, "C")
        self.mode_var = tk.StringVar(r, MODE_MAJOR)
        self.style_var = tk.StringVar(r, STYLES[0])
        self.form_var = tk.StringVar(r, FORMS[0])
        self.cadence_var = tk.StringVar(r, CADENCES[0])
        self.chord_len_var = tk.StringVar(r, next(iter(CHORD_LENGTHS)))
        self.feel_var = tk.StringVar(r, FEELS[0])
        self.density_var = tk.IntVar(r, 4)
        self.mod_density_var = tk.IntVar(r, 3)
        self.seed_var = tk.StringVar(r, "")
        self.bpm = tk.IntVar(r, 120)
        self.vel = tk.IntVar(r, 100)
        self.n_sections = tk.IntVar(r, 3)
        self.status_var = tk.StringVar(r, "")
        # editor of the selected section: every change applies immediately
        self.bars_var = tk.IntVar(r, 8)
        self.tension_var = tk.IntVar(r, 2)
        self.mod_var = tk.BooleanVar(r, False)
        self.target_key = tk.StringVar(r, "G")
        self.strategy = tk.StringVar(r, MOD_STRATEGIES[0])
        self.return_var = tk.BooleanVar(r, False)
        for var in (self.bars_var, self.tension_var, self.mod_var, self.target_key, self.strategy, self.return_var):
            var.trace_add("write", lambda *_: self._apply_editor())
        self.start_key.trace_add("write", lambda *_: self._keys_changed())
        self.mode_var.trace_add("write", lambda *_: self.refresh_tree())

    def _density(self) -> int:
        return _int(self.density_var, 4, 1, 10)

    def _bpm(self) -> int:
        return _int(self.bpm, 120, 30, 300)

    def _minor(self) -> bool:
        return self.mode_var.get() == MODE_MINOR

    def _seed(self) -> Optional[int]:
        try:
            return int(self.seed_var.get())
        except ValueError:
            return None

    def _settings(self) -> CompositionSettings:
        return CompositionSettings(
            start_key=self.start_key.get(),
            style=self.style_var.get(),
            form=self.form_var.get(),
            cadence=self.cadence_var.get(),
            chord_len=self.chord_len_var.get(),
            density=self._density(),
            base_velocity=_int(self.vel, 100, 1, 127),
            minor=self._minor(),
            seed=self._seed(),
        )

    def _apply_settings(self, s: CompositionSettings):
        """Push settings (from a loaded project) into the controls."""
        self.start_key.set(key_name(pc(s.start_key)))
        self.mode_var.set(MODE_MINOR if s.minor else MODE_MAJOR)
        self.style_var.set(s.style)
        self.form_var.set(s.form)
        self.cadence_var.set(s.cadence)
        self.chord_len_var.set(s.chord_len)
        self.density_var.set(s.density)
        self.vel.set(s.base_velocity)

    def _status(self, key: str, **fmt):
        self.status_var.set(self.i18n.t(key, **fmt))

    # ------------------------ Construction ------------------------

    def _build_ui(self):
        self.tooltip.hide()
        for child in self.root.winfo_children():
            child.destroy()
        colors = self.theme.colors
        self.tooltip.background, self.tooltip.foreground = colors.tooltip, colors.tooltip_text
        self.root.title(f"{APP_NAME} — {self.i18n.t('subtitle')}")
        px = self.theme.px
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        body = ttk.Frame(self.root, padding=(px(12), px(12), px(12), 0))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(body)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, px(12)))
        self._build_start_card(sidebar).pack(fill="x")
        self._build_color_card(sidebar).pack(fill="x", pady=px(10))
        self._build_performance_card(sidebar).pack(fill="x")

        main = ttk.Frame(body)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        self._build_sections_card(main).grid(row=0, column=0, sticky="ew")
        self._build_panel_card(main).grid(row=1, column=0, sticky="nsew", pady=(px(10), 0))

        self._build_transport()
        ttk.Label(self.root, textvariable=self.status_var, style="Status.TLabel", anchor="w")\
            .grid(row=3, column=0, sticky="ew")

        self.refresh_tree(rebuild=True)
        self._load_editor()
        self._render()
        self._update_buttons()
        if not self.status_var.get():
            self._status("status_ready")

    def _card(self, parent, title_key: str) -> Card:
        return Card(parent, self.i18n.t(title_key), self.theme.px(14), self.theme.colors)

    def _hint(self, key: str, *widgets):
        for widget in widgets:
            self.tooltip.attach(widget, self.i18n.hint(key))

    def _field(self, parent, key: str, row: int, column: int, columnspan: int = 1) -> ttk.Frame:
        """A cell with its label on top; the control is packed inside the returned frame."""
        px = self.theme.px
        cell = ttk.Frame(parent, style="Card.TFrame")
        cell.grid(row=row, column=column, columnspan=columnspan, sticky="ew",
                  padx=(0 if column == 0 else px(10), 0), pady=(0 if row == 0 else px(9), 0))
        label = ttk.Label(cell, text=self.i18n.t(key), style="Muted.TLabel")
        label.pack(anchor="w")
        self._hint(key, label)
        return cell

    def _choice(self, parent, key: str, var, values, row, column, columnspan=1, **kw) -> Choice:
        cell = self._field(parent, key, row, column, columnspan)
        choice = Choice(cell, var, values, self.i18n.v, **kw)
        choice.pack(fill="x", pady=(2, 0))
        self._hint(key, choice)
        return choice

    def _build_header(self):
        px, t, colors = self.theme.px, self.i18n.t, self.theme.colors
        header = tk.Frame(self.root, background=colors.header)
        header.grid(row=0, column=0, sticky="ew")

        def caption(text):
            return tk.Label(header, text=text, background=colors.header, foreground=colors.header_muted)

        tk.Label(header, text=f"♪  {APP_NAME}", font=self.theme.brand, background=colors.header,
                 foreground="#ffffff").pack(side="left", padx=(px(16), px(12)), pady=px(10))
        preset_label = caption(t("preset"))
        preset_label.pack(side="left", padx=(px(18), px(8)))
        preset = Choice(header, self.preset_var, list(PRESETS), self.i18n.v, width=28,
                        placeholder=t("preset_placeholder"), on_pick=self.apply_preset)
        preset.pack(side="left")
        self._hint("preset", preset_label, preset)

        language = ttk.Combobox(header, state="readonly", values=list(LANGS.values()), width=9)
        language.set(LANGS[self.i18n.lang])
        language.bind("<<ComboboxSelected>>",
                      lambda e: self.set_language(list(LANGS)[language.current()]))
        language.pack(side="right", padx=(px(6), px(16)))
        caption(t("language")).pack(side="right")
        self._hint("language", language)

        toggle = ttk.Button(header, style="Header.TButton", command=self.toggle_theme,
                            text=t("theme_dark" if self.theme.mode == "light" else "theme_light"))
        toggle.pack(side="right", padx=(0, px(16)))
        self._hint("theme", toggle)
        ttk.Button(header, text=t("explain_btn"), style="Header.TButton", command=self.show_help)\
            .pack(side="right", padx=px(8))

    def _build_start_card(self, parent) -> Card:
        card = self._card(parent, "card_start")
        body = card.body
        body.columnconfigure((0, 1), weight=1, uniform="half")

        cell = self._field(body, "key", 0, 0)
        row = ttk.Frame(cell, style="Card.TFrame")
        row.pack(fill="x", pady=(2, 0))
        key = Choice(row, self.start_key, KEY_NAMES, width=4)
        key.pack(side="left")
        mode = Choice(row, self.mode_var, MODES, self.i18n.v, width=7)
        mode.pack(side="left", fill="x", expand=True, padx=(self.theme.px(6), 0))
        self._hint("key", key, mode)

        self._choice(body, "cadence", self.cadence_var, CADENCES, 0, 1, width=16)
        self._choice(body, "style", self.style_var, STYLES, 1, 0, width=22)
        self._choice(body, "form", self.form_var, FORMS, 1, 1, width=16)
        return card

    def _build_color_card(self, parent) -> Card:
        px, t = self.theme.px, self.i18n.t
        card = self._card(parent, "card_color")

        def density_caption(v):
            return t("density_1" if v <= 3 else "density_2" if v <= 6 else "density_3" if v <= 8 else "density_4")

        def mod_caption(v):
            return t("mod_0" if v == 0 else "mod_1" if v <= 3 else "mod_2" if v <= 7 else "mod_3")

        density = LabeledSlider(card.body, t("density"), self.density_var, 1, 10, density_caption)
        density.pack(fill="x")
        self._hint("density", density.label, density.scale)
        modulation = LabeledSlider(card.body, t("mod_density"), self.mod_density_var, 0, 10, mod_caption)
        modulation.pack(fill="x", pady=(px(9), 0))
        self._hint("mod_density", modulation.label, modulation.scale)

        seed_label = ttk.Label(card.body, text=t("seed"), style="Muted.TLabel")
        seed_label.pack(anchor="w", pady=(px(9), 0))
        row = ttk.Frame(card.body, style="Card.TFrame")
        row.pack(fill="x", pady=(2, 0))
        seed = ttk.Entry(row, textvariable=self.seed_var, width=10)
        seed.pack(side="left")
        pin = ttk.Button(row, text=t("pin_seed"), command=self.pin_seed)
        pin.pack(side="left", padx=px(6))
        ttk.Label(row, text=t("seed_inline"), style="Muted.TLabel").pack(side="left")
        self._hint("seed", seed_label, seed)
        self._hint("pin_seed", pin)
        return card

    def _build_performance_card(self, parent) -> Card:
        px, t = self.theme.px, self.i18n.t
        card = self._card(parent, "card_perf")
        body = card.body
        body.columnconfigure((0, 1), weight=1, uniform="half")
        self._choice(body, "feel", self.feel_var, FEELS, 0, 0, width=22)
        self._choice(body, "chord_len", self.chord_len_var, list(CHORD_LENGTHS), 0, 1, width=16)

        tempo = LabeledSlider(body, t("bpm"), self.bpm, 40, 260)
        tempo.grid(row=1, column=0, sticky="ew", pady=(px(9), 0))
        self._hint("bpm", tempo.label, tempo.scale)
        dynamics = LabeledSlider(body, t("velocity"), self.vel, 1, 127)
        dynamics.grid(row=1, column=1, sticky="ew", padx=(px(10), 0), pady=(px(9), 0))
        self._hint("velocity", dynamics.label, dynamics.scale)
        return card

    def _build_sections_card(self, parent) -> Card:
        px, t, v = self.theme.px, self.i18n.t, self.i18n.v
        card = self._card(parent, "card_sections")

        create = ttk.Button(card.header, text=t("create"), command=self.reset_sections)
        create.pack(side="right")
        count = ttk.Spinbox(card.header, from_=1, to=12, textvariable=self.n_sections, width=3)
        count.pack(side="right", padx=px(6))
        ttk.Label(card.header, text=t("n_sections"), style="Muted.TLabel").pack(side="right")
        self._hint("create", create, count)

        cols = [("bars", "col_bars", 70), ("key", "col_key", 80), ("tension", "col_tension", 70),
                ("mod", "col_mod", 80), ("target", "col_target", 70), ("strategy", "col_strategy", 190),
                ("return", "col_return", 70)]
        table = ttk.Frame(card.body, style="Card.TFrame")
        table.pack(fill="x")
        self.tree = ttk.Treeview(table, columns=[c for c, _, _ in cols], show="headings",
                                 height=3, selectmode="browse")
        tree_scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y")
        for column, key, width in cols:
            self.tree.heading(column, text=t(key))
            self.tree.column(column, width=px(width), anchor="center")
        self.tree.pack(side="left", fill="x", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_section)

        editor = ttk.Frame(card.body, style="Card.TFrame")
        editor.pack(fill="x", pady=(px(10), 0))

        def label(key):
            widget = ttk.Label(editor, text=t(key), style="Card.TLabel")
            widget.pack(side="left", padx=(px(12), px(4)))
            return widget

        ttk.Label(editor, text=t("selected"), style="Muted.TLabel").pack(side="left")
        bars_label = label("bars")
        bars = ttk.Spinbox(editor, from_=1, to=64, textvariable=self.bars_var, width=4)
        bars.pack(side="left")
        self._hint("bars", bars_label, bars)
        tension_label = label("tension")
        tension = ttk.Spinbox(editor, from_=0, to=3, textvariable=self.tension_var, width=3)
        tension.pack(side="left")
        self._hint("tension", tension_label, tension)

        modulate = ttk.Checkbutton(editor, text=t("modulate"), variable=self.mod_var, style="Card.TCheckbutton")
        modulate.pack(side="left", padx=(px(16), px(4)))
        self._target_choice = Choice(editor, self.target_key, KEY_NAMES, width=4)
        self._target_choice.pack(side="left")
        self._hint("modulate", modulate, self._target_choice)
        strategy_label = label("strategy")
        self._strategy_choice = Choice(editor, self.strategy, MOD_STRATEGIES, v, width=20)
        self._strategy_choice.pack(side="left")
        self._hint("strategy", strategy_label, self._strategy_choice)

        back = ttk.Checkbutton(card.body, text=t("return_"), variable=self.return_var, style="Card.TCheckbutton")
        back.pack(anchor="w", pady=(px(6), 0))
        self._hint("return_", back)
        return card

    def _build_panel_card(self, parent) -> Card:
        px, colors = self.theme.px, self.theme.colors
        card = self._card(parent, "card_panel")
        body = card.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.text = tk.Text(body, height=7, width=100, wrap="none", font=self.theme.mono, relief="flat",
                            background=colors.field, foreground=colors.text, padx=px(8), pady=px(6),
                            highlightthickness=1, highlightbackground=colors.border,
                            highlightcolor=colors.border, insertbackground=colors.field,
                            selectbackground=colors.accent, selectforeground="#ffffff", cursor="arrow")
        ysb = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        xsb = ttk.Scrollbar(body, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        self.text.bind("<Double-Button-1>", self._on_double_click)
        self.text.bind("<Key>", self._read_only_key)
        for tag, color in colors.func_colors.items():
            self.text.tag_configure(tag, foreground=color)
        self.text.tag_configure("HDR", font=self.theme.mono_bold)
        self.text.tag_configure("MONO", foreground=colors.muted)
        self.text.tag_configure("NOW", background=colors.now_playing)
        self._hint("panel", card.header)

        self.now_label = ttk.Label(body, text="", style="Now.TLabel")
        self.now_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(px(8), px(4)))
        self.keyboard = PianoKeyboard(body, scale=self.theme.scale, background=colors.card)
        self.keyboard.grid(row=3, column=0, columnspan=2, sticky="w")
        self._hint("keyboard", self.keyboard)
        return card

    @staticmethod
    def _read_only_key(event):
        """The panel is not edited by typing, but its text can be selected and copied."""
        if event.state & 0x4 and event.keysym.lower() in ("c", "a"):
            return None
        return "break"

    def _build_transport(self):
        px, t, colors = self.theme.px, self.i18n.t, self.theme.colors
        bar = ttk.Frame(self.root, padding=(px(12), px(10)))
        bar.grid(row=2, column=0, sticky="ew")

        generate = ttk.Button(bar, text=t("generate"), style="Accent.TButton", command=self.generate)
        generate.pack(side="left")
        self.play_btn = ttk.Button(bar, text=t("play"), command=self.play)
        self.play_btn.pack(side="left", padx=(px(10), 0))
        self.stop_btn = ttk.Button(bar, text=t("stop"), command=self.stop)
        self.stop_btn.pack(side="left", padx=(px(6), 0))

        self.export_btn = ttk.Menubutton(bar, text=t("export"))
        menu = tk.Menu(self.export_btn, tearoff=0, background=colors.card, foreground=colors.text,
                       activebackground=colors.accent, activeforeground="#ffffff")
        menu.add_command(label=t("export_txt"), command=self.export_panel_txt)
        menu.add_command(label=t("export_wav"), command=self.export_wav)
        menu.add_command(label=t("export_midi"), command=self.export_midi)
        self.export_btn["menu"] = menu
        self.export_btn.pack(side="right")
        save = ttk.Button(bar, text=t("save"), command=self.save_project)
        save.pack(side="right", padx=px(6))
        open_ = ttk.Button(bar, text=t("open"), command=self.open_project)
        open_.pack(side="right")

        for key, widget in (("generate", generate), ("play", self.play_btn), ("stop", self.stop_btn),
                            ("export", self.export_btn), ("save", save), ("open", open_)):
            self._hint(key, widget)

    def _update_buttons(self, playing: bool = False):
        has_music = self.composition is not None
        self.play_btn.config(state="normal" if has_music and not playing else "disabled")
        self.export_btn.config(state="normal" if has_music else "disabled")
        self.stop_btn.config(state="normal" if playing else "disabled")

    def _rebuild(self):
        """Recreate every widget with the current language and theme; the state lives in variables."""
        self.stop()
        self.preferences = {"lang": self.i18n.lang, "theme": self.theme.mode}
        save_preferences(self.preferences)
        self.status_var.set("")
        self._build_ui()

    def set_language(self, lang: str):
        if lang != self.i18n.lang and lang in LANGS:
            self.i18n.lang = lang
            self._rebuild()

    def toggle_theme(self):
        self.theme.apply("dark" if self.theme.mode == "light" else "light")
        self._rebuild()

    def show_help(self):
        return help_window.show_help(self.root, self.i18n, self.theme)

    # ------------------------ Sections ------------------------

    def reset_sections(self, announce: bool = True):
        self.stop()
        self.sections = plan_sections(
            _int(self.n_sections, 3, 1, 12),
            self.start_key.get(),
            _int(self.mod_density_var, 3, 0, 10),
            minor=self._minor(),
        )
        self._selected = 0
        self.refresh_tree(rebuild=True)
        self._load_editor()
        if announce:
            self._status("status_sections", n=len(self.sections))

    def _keys_changed(self):
        recompute_keys(self.sections, self.start_key.get())
        self.refresh_tree()

    def _row_values(self, s: Section):
        t, minor = self.i18n.t, self._minor()
        return (
            s.bars, key_name(pc(s.key_name), minor), s.tension,
            t("yes") if s.do_modulate else t("no"),
            key_name(pc(s.target_key), minor) if s.do_modulate else "–",
            self.i18n.v(s.mod_strategy) if s.do_modulate else "–",
            t("yes") if s.return_to_start else t("no"),
        )

    def refresh_tree(self, rebuild: bool = False):
        tree = getattr(self, "tree", None)
        if tree is None or not tree.winfo_exists():
            return
        rows = tree.get_children()
        if rebuild or len(rows) != len(self.sections):
            tree.delete(*rows)
            for idx, s in enumerate(self.sections):
                tree.insert("", "end", iid=str(idx), values=self._row_values(s))
            if self.sections:
                tree.selection_set(str(min(self._selected, len(self.sections) - 1)))
        else:
            for idx, s in enumerate(self.sections):
                tree.item(str(idx), values=self._row_values(s))

    def _on_select_section(self, _event=None):
        sel = self.tree.selection()
        if sel and int(sel[0]) != self._selected:
            self._selected = int(sel[0])
            self._load_editor()

    def _load_editor(self):
        """Load the selected section into the editor controls."""
        if not self.sections:
            return
        self._selected = min(self._selected, len(self.sections) - 1)
        s = self.sections[self._selected]
        self._loading = True
        try:
            self.bars_var.set(s.bars)
            self.tension_var.set(s.tension)
            self.mod_var.set(s.do_modulate)
            self.target_key.set(key_name(pc(s.target_key)))
            self.strategy.set(s.mod_strategy)
            self.return_var.set(s.return_to_start)
        finally:
            self._loading = False
        self._sync_editor_state()

    def _sync_editor_state(self):
        """Modulation controls are only enabled when the section modulates."""
        state = "readonly" if self.mod_var.get() else "disabled"
        for widget in (getattr(self, "_target_choice", None), getattr(self, "_strategy_choice", None)):
            if widget is not None and widget.winfo_exists():
                widget.configure(state=state)

    def _apply_editor(self):
        """Apply the editor controls to the selected section."""
        if self._loading or not self.sections:
            return
        s = self.sections[self._selected]
        s.bars = _int(self.bars_var, s.bars, 1, 64)
        s.tension = _int(self.tension_var, s.tension, 0, 3)
        s.do_modulate = bool(self.mod_var.get())
        s.target_key = self.target_key.get()
        s.mod_strategy = self.strategy.get()
        s.return_to_start = bool(self.return_var.get())
        recompute_keys(self.sections, self.start_key.get())
        self._sync_editor_state()
        self.refresh_tree()

    # ------------------------ Generate / edit ------------------------

    def apply_preset(self, name: str):
        """Load a complete example and generate it."""
        p = PRESETS[name]
        self.preset_var.set(name)
        self.start_key.set(p["key"])
        self.mode_var.set(MODE_MINOR if p["minor"] else MODE_MAJOR)
        self.style_var.set(p["style"])
        self.form_var.set(p["form"])
        self.cadence_var.set(p["cadence"])
        self.chord_len_var.set(p["chord_len"])
        self.density_var.set(p["density"])
        self.mod_density_var.set(p["mod_density"])
        self.feel_var.set(p["feel"])
        self.bpm.set(p["bpm"])
        self.vel.set(p["velocity"])
        self.n_sections.set(p["sections"])
        self.seed_var.set("")
        self.reset_sections(announce=False)
        self.generate()

    def generate(self):
        self.stop()
        recompute_keys(self.sections, self.start_key.get())
        self.refresh_tree()
        self.composition = compose(self.sections, self._settings())
        self._render()
        self._update_buttons()
        bars = sum(len(b.events) for b in self.composition.blocks)
        self._status("status_generated", bars=bars, seed=self.composition.settings.seed)

    def _render(self):
        """Write the composition into the panel and remember which line each chord landed on."""
        self.text.delete("1.0", tk.END)
        self._chord_lines = {}
        self._now_playing = None
        self.now_label.config(text="")
        self.keyboard.show(())
        if self.composition is None:
            return
        for line, tag, chord_index in format_composition(self.composition, self.i18n.v):
            if chord_index is not None:
                self._chord_lines[chord_index] = int(self.text.index("end-1c").split(".")[0])
            self.text.insert(tk.END, line, tag)

    def clear(self):
        self.stop()
        self.composition = None
        self._render()
        self._update_buttons()

    def pin_seed(self):
        """Copy the seed of the last generation into the field, to repeat it."""
        if self.composition is not None and self.composition.settings.seed is not None:
            self.seed_var.set(str(self.composition.settings.seed))

    def _on_double_click(self, event):
        """Reharmonize: replace by hand the chord on the clicked line."""
        line = int(self.text.index(f"@{event.x},{event.y}").split(".")[0])
        index = next((i for i, ln in self._chord_lines.items() if ln == line), None)
        if index is None or self.composition is None:
            return "break"
        old = self.composition.chords[index]
        answer = simpledialog.askstring(self.i18n.t("reharm_title"), self.i18n.t("reharm_prompt"),
                                        initialvalue=old.symbol, parent=self.root)
        if not answer:
            return "break"
        try:
            root, quality, tensions = parse_chord_symbol(answer)
        except ValueError:
            messagebox.showerror(self.i18n.t("reharm_title"), self.i18n.t(
                "reharm_error", qualities=", ".join(QUALITY_CHORD_TONES), tensions=", ".join(TENSION_INTERVALS)))
            return "break"
        self.stop()
        func = "D" if quality == "7" else ("T" if old.func == "D" else old.func)
        new = Chord(root, quality, "(edited)", func, tuple(tensions), old.key, old.minor)
        self.composition.replace_chord(index, new)
        self._render()
        self.text.see(f"{line}.0")
        self._status("status_edited", chord=new.symbol)
        return "break"

    # ------------------------ Projects / export ------------------------

    def _project_filetypes(self):
        return [(self.i18n.t("project_files"), "*.jazz.json"), ("JSON", "*.json")]

    def save_project(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".jazz.json", filetypes=self._project_filetypes(),
            initialfile="progression.jazz.json", title=self.i18n.t("save").rstrip("…"))
        if not path:
            return
        extra = {"bpm": self._bpm(), "feel": self.feel_var.get(),
                 "mod_density": _int(self.mod_density_var, 3, 0, 10), "seed_field": self.seed_var.get()}
        try:
            project.save_project(path, self._settings(), self.sections, self.composition, extra)
        except OSError as error:
            messagebox.showerror(self.i18n.t("error"), str(error))
            return
        self._status("status_saved", path=path)

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=self._project_filetypes(),
                                          title=self.i18n.t("open").rstrip("…"))
        if not path:
            return
        try:
            settings, sections, composition, extra = project.load_project(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror(self.i18n.t("error"), f"{self.i18n.t('open_error')}\n{error}")
            return
        self.stop()
        self.sections = sections
        self._selected = 0
        self._apply_settings(settings)
        self.n_sections.set(len(sections))
        self.bpm.set(extra.get("bpm", 120))
        self.feel_var.set(extra.get("feel") if extra.get("feel") in FEELS else FEELS[0])
        self.mod_density_var.set(extra.get("mod_density", 3))
        self.seed_var.set(extra.get("seed_field", ""))
        self.preset_var.set("")
        self.composition = composition
        self.refresh_tree(rebuild=True)
        self._load_editor()
        self._render()
        self._update_buttons()
        self._status("status_loaded", path=path)

    def export_panel_txt(self):
        """Export the educational panel to .txt, keeping the alignment."""
        content = self.text.get("1.0", tk.END)
        if not content.strip():
            messagebox.showinfo(self.i18n.t("export_txt"), self.i18n.t("need_generate"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt", filetypes=[(self.i18n.t("text_files"), "*.txt")],
            initialfile="jazz_progression.txt", title=self.i18n.t("export_txt"))
        if not path:
            return
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content.replace("→", "->").rstrip() + "\n")
            f.write(f"\n---\n{APP_NAME}\n")
        self._status("status_saved", path=path)

    def _build_performance(self) -> Performance:
        return build_performance(self.composition.playback, self._density(), self.feel_var.get(),
                                 self._bpm(), seed=self.composition.settings.seed or 0)

    def _export(self, title_key: str, extension: str, writer):
        title = self.i18n.t(title_key)
        if self.composition is None:
            messagebox.showinfo(title, self.i18n.t("need_generate"))
            return
        path = filedialog.asksaveasfilename(
            defaultextension=extension, filetypes=[(title, f"*{extension}")],
            initialfile=f"jazz_progression{extension}", title=title)
        if not path:
            return
        self.root.config(cursor="watch")
        self.root.update_idletasks()
        try:
            writer(path, self._build_performance(), self._bpm())
        except Exception as error:
            messagebox.showerror(title, str(error))
            return
        finally:
            self.root.config(cursor="")
        self._status("status_saved", path=path)

    def export_wav(self):
        self._export("export_wav", ".wav", write_wav)

    def export_midi(self):
        self._export("export_midi", ".mid", write_midi)

    # ------------------------ Playback ------------------------

    def play(self):
        if self.composition is None:
            messagebox.showinfo(self.i18n.t("play"), self.i18n.t("need_generate"))
            return
        if self._player_thread and self._player_thread.is_alive() and not self._stop_flag.is_set():
            return

        # Read the widgets here: Tkinter is not safe to call from other threads
        bpm = self._bpm()
        self._performance = perf = self._build_performance()
        self._beat = beat_seconds(bpm)
        self._stop_flag = stop_flag = threading.Event()
        self._update_buttons(playing=True)
        self._status("status_playing")

        def runner():
            try:
                self._audio.play_pcm(iter_performance_pcm(perf, bpm), stop_flag)
            except Exception as error:
                msg = str(error)
                self.root.after(0, lambda: messagebox.showerror("Audio", msg))
            finally:
                self.root.after(0, lambda: stop_flag is self._stop_flag and self._playback_ended())

        self._player_thread = threading.Thread(target=runner, daemon=True)
        self._player_thread.start()
        self._tick(stop_flag)

    def _tick(self, stop_flag: threading.Event):
        """Follow playback: highlight the sounding chord and show it on the keyboard."""
        if stop_flag is not self._stop_flag or stop_flag.is_set():
            return
        position = self._audio.position()
        if position is not None and self._performance is not None:
            self._show_now(self._performance.chord_at(position / self._beat))
        self.root.after(40, self._tick, stop_flag)

    def _show_now(self, index: Optional[int]):
        if index == self._now_playing:
            return
        self._now_playing = index
        self.text.tag_remove("NOW", "1.0", tk.END)
        if index is None or self.composition is None or self._performance is None:
            self.now_label.config(text="")
            self.keyboard.show(())
            return
        chord = self.composition.chords[index]
        line = self._chord_lines.get(index)
        if line is not None:
            self.text.tag_add("NOW", f"{line}.0", f"{line}.end")
            self.text.see(f"{line}.0")
        root, scale, _ = scale_parts(chord)
        self.now_label.config(
            text=f"▶ {chord.symbol}   ·   {self.i18n.v(chord.roman)}   ·   "
                 f"{root} {self.i18n.v(scale)}:  {scale_note_names(chord)}")
        self.keyboard.show(self._performance.voicings[index])

    def _playback_ended(self):
        self._stop_flag.set()
        self._show_now(None)
        self._update_buttons()
        if self.status_var.get() == self.i18n.t("status_playing"):
            self._status("status_ready")

    def stop(self):
        self._stop_flag.set()
        self._audio.stop_all()
        if hasattr(self, "play_btn"):
            self._playback_ended()

    def on_close(self):
        self.stop()
        self.tooltip.hide()
        self.root.destroy()


def self_test() -> int:
    """Check that a packaged build is complete: engine, synthesis, MIDI, pygame and the UI all load.

    Run with `--self-test`; the exit code is 0 on success, and on failure the traceback is
    written to the file named by JAZZ_SELF_TEST_LOG. Setting JAZZ_SELF_TEST_AUDIO=1 also
    plays a short clip, which needs an audio device.
    """
    import os
    import traceback
    try:
        import pygame.mixer  # noqa: F401  (must be bundled)
        from ..midi import midi_bytes

        root = tk.Tk()
        app = App(root)
        app.apply_preset(next(iter(PRESETS)))
        root.update()
        perf = build_performance(app.composition.playback[:2], app._density(), FEELS[2], 240)
        chunks = list(iter_performance_pcm(perf, 240))
        assert any(chunks) and midi_bytes(perf, 240).startswith(b"MThd")
        if os.environ.get("JAZZ_SELF_TEST_AUDIO") == "1":
            app._audio.play_pcm(iter(chunks), threading.Event())
        app.on_close()
        return 0
    except Exception:
        # windowed builds have no console, so the reason goes to a log file
        log = os.environ.get("JAZZ_SELF_TEST_LOG", "jazz_composer_self_test.log")
        with open(log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        return 1


def main():
    import sys
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    enable_dpi_awareness()
    root = tk.Tk()
    App(root)
    root.update_idletasks()
    width, height = root.winfo_reqwidth(), root.winfo_reqheight()
    root.minsize(width, height)
    # a little taller than the minimum so the result panel can breathe
    height = min(height + int(height * 0.18), root.winfo_screenheight() - 100)
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2 - 30)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.mainloop()
