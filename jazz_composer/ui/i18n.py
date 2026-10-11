"""Interface languages (English / Spanish).

The engine uses English strings as identifiers (styles, forms, scales...).
`I18n.v()` translates those for display only; `I18n.t()` translates the UI's own texts.
"""

LANGS = {"en": "English", "es": "Español"}

# Engine values -> Spanish
VALUES_ES = {
    # modes
    "Major": "Mayor", "Minor": "Menor",
    # styles and forms
    "Standard (functional)": "Standard (funcional)",
    "12-bar blues": "Blues de 12 compases",
    "Jazz blues (II-V)": "Jazz blues (II-V)",
    "Modal (Dorian/Mixolydian)": "Modal (dórico/mixolidio)",
    "Free": "Libre",
    "Through-composed": "Desarrollo continuo",
    # cadences
    "Authentic (V-I)": "Auténtica (V-I)",
    "Deceptive (V-vi)": "Engañosa (V-vi)",
    "Half (V)": "Suspensiva (V)",
    # chord length
    "1 bar": "1 compás",
    "2 beats (half bar)": "2 tiempos (medio compás)",
    "2 bars": "2 compases",
    "3 beats (3/4 bar)": "3 tiempos (3/4 de compás)",
    "Adaptive (by function)": "Adaptativa (según función)",
    # modulation bridges
    "Diatonic pivot": "Pivote diatónico",
    "Chromatic pivot": "Pivote cromático",
    "Direct": "Directa",
    "Tritone (SubV)": "Tritono (SubV)",
    "Dominant chain": "Cadena de dominantes",
    "Coltrane (major 3rd)": "Coltrane (3ª mayor)",
    # accompaniment
    "Block (sustained chord)": "Bloque (acorde sostenido)",
    "Swing + walking bass": "Swing + bajo caminante",
    # scales
    "Ionian": "jónica", "Lydian": "lidia", "Dorian": "dórica", "Phrygian": "frigia",
    "Aeolian": "eólica", "Locrian": "locria", "melodic minor": "menor melódica",
    "Mixolydian": "mixolidia", "Lydian dominant": "lidia dominante",
    "Mixolydian b9 b13": "mixolidia b9 b13", "altered": "alterada",
    "diminished (W-H)": "disminuida (T-ST)",
    # analysis labels
    "Pivot (diatonic)": "Pivote (diatónico)",
    "iv (borrowed pivot)": "iv (pivote prestado)",
    "V (prep new key)": "V (prepara la nueva tonalidad)",
    "SubV7 (tritone)": "SubV7 (tritono)",
    "V/V (chain)": "V/V (cadena)",
    "V (chain)": "V (cadena)",
    "V (half cadence)": "V (semicadencia)",
    "IV7 (Dorian vamp)": "IV7 (vamp dórico)",
    "i-7 (Dorian)": "i-7 (dórico)",
    "I7 (Mixolydian)": "I7 (mixolidio)",
    "(edited)": "(editado)",
    # educational panel
    "LEGEND": "LEYENDA",
    "T = Tonic (stability) | SD = Subdominant (preparation) | D = Dominant (tension)":
        "T = Tónica (estabilidad) | SD = Subdominante (preparación) | D = Dominante (tensión)",
    "Style": "Estilo", "Form": "Forma", "Final cadence": "Cadencia final", "Chord length": "Duración",
    "Seed": "Semilla", "HOME KEY": "TONALIDAD INICIAL", "FINAL CADENCE": "CADENCIA FINAL", "END": "FIN",
    # examples
    "Classic standard (AABA)": "Standard clásico (AABA)",
    "Minor ballad": "Balada en menor",
    "Twelve-bar blues": "Blues de 12 compases",
    "Minor jazz blues": "Jazz blues menor",
    "Bossa nova tune": "Tema de bossa nova",
    "Dorian modal": "Modal dórico",
    "For study (bare bones)": "Para estudiar (esqueleto)",
}

# Interface texts: key -> (English, Spanish)
UI = {
    "subtitle": ("Educational jazz progression generator", "Generador educativo de progresiones de jazz"),
    "explain_btn": ("?  Explain functions", "?  Explicar funciones"),
    "theme_dark": ("☾  Dark", "☾  Oscuro"),
    "theme_light": ("☀  Light", "☀  Claro"),
    "theme": ("Light / dark mode", "Modo claro / oscuro"),
    "card_start": ("1 · Key and form", "1 · Tonalidad y forma"),
    "card_color": ("2 · Harmonic color", "2 · Color armónico"),
    "card_perf": ("3 · Performance", "3 · Interpretación"),
    "card_sections": ("4 · Sections  (fine-tuning, optional)", "4 · Secciones  (ajuste fino, opcional)"),
    "card_panel": ("Result  ·  double-click a chord to reharmonize it",
                   "Resultado  ·  doble clic en un acorde para rearmonizarlo"),
    "preset": ("Start from an example", "Empezar con un ejemplo"),
    "preset_group": ("Quick start", "Inicio rápido"),
    "preset_placeholder": ("Pick an example…", "Elegí un ejemplo…"),
    "key": ("Key", "Tonalidad"),
    "style": ("Style", "Estilo"),
    "form": ("Form", "Forma"),
    "cadence": ("Final cadence", "Cadencia final"),
    "density": ("Harmonic density", "Densidad armónica"),
    "mod_density": ("Modulations", "Modulaciones"),
    "seed": ("Seed", "Semilla"),
    "seed_inline": ("empty = random", "vacía = al azar"),
    "pin_seed": ("Pin last", "Fijar última"),
    "feel": ("Accompaniment", "Acompañamiento"),
    "chord_len": ("Chord length", "Duración por acorde"),
    "bpm": ("Tempo (BPM)", "Tempo (BPM)"),
    "velocity": ("Dynamics", "Dinámica"),
    "n_sections": ("Count", "Cantidad"),
    "create": ("Create sections", "Crear secciones"),
    "col_bars": ("Bars", "Compases"),
    "col_key": ("Key", "Tonalidad"),
    "col_tension": ("Tension", "Tensión"),
    "col_mod": ("Modulates", "Modula"),
    "col_target": ("To", "Hacia"),
    "col_strategy": ("Bridge", "Puente"),
    "col_return": ("Returns", "Vuelve"),
    "yes": ("Yes", "Sí"),
    "no": ("No", "No"),
    "selected": ("Selected section:", "Sección seleccionada:"),
    "bars": ("Bars", "Compases"),
    "tension": ("Tension", "Tensión"),
    "modulate": ("Modulate to", "Modular a"),
    "strategy": ("via bridge", "con puente"),
    "return_": ("Return to the home key afterwards", "Volver a la tonalidad inicial al terminar"),
    "generate": ("✦  Generate", "✦  Generar"),
    "play": ("▶  Play", "▶  Reproducir"),
    "stop": ("■  Stop", "■  Detener"),
    "open": ("Open…", "Abrir…"),
    "save": ("Save…", "Guardar…"),
    "export": ("Export", "Exportar"),
    "export_txt": ("Panel as text (.txt)", "Panel como texto (.txt)"),
    "export_wav": ("Audio (.wav)", "Audio (.wav)"),
    "export_midi": ("MIDI (.mid)", "MIDI (.mid)"),
    "panel": ("Educational panel", "Panel educativo"),
    "keyboard": ("Keyboard", "Teclado"),
    "language": ("Language", "Idioma"),
    "status_ready": ("Pick an example or adjust the settings, then press Generate.",
                     "Elegí un ejemplo o ajustá los parámetros y pulsá Generar."),
    "status_generated": ("{bars} bars generated  ·  seed {seed}", "{bars} compases generados  ·  semilla {seed}"),
    "status_playing": ("Playing…", "Reproduciendo…"),
    "status_saved": ("Saved: {path}", "Guardado: {path}"),
    "status_loaded": ("Project opened: {path}", "Proyecto abierto: {path}"),
    "status_sections": ("{n} sections created. Select one to adjust it.",
                        "{n} secciones creadas. Seleccioná una para ajustarla."),
    "status_edited": ("Chord replaced with {chord}.", "Acorde reemplazado por {chord}."),
    "need_generate": ("Generate a progression first.", "Primero generá una progresión."),
    "reharm_title": ("Reharmonize", "Rearmonizar"),
    "reharm_prompt": ("New chord (e.g. Db7(#11), F#m7b5, Bbmaj7(9)):",
                      "Nuevo acorde (ej.: Db7(#11), F#m7b5, Bbmaj7(9)):"),
    "reharm_error": ("That chord is not valid.\nQualities: {qualities}\nTensions (in parentheses): {tensions}",
                     "Ese acorde no es válido.\nCualidades: {qualities}\nTensiones (entre paréntesis): {tensions}"),
    "open_error": ("Could not read the project:", "No se pudo leer el proyecto:"),
    "error": ("Error", "Error"),
    "help_title": ("Help", "Ayuda"),
    "tab_functions": ("Each function in brief", "Cada función en síntesis"),
    "tab_guide": ("Quick guide", "Guía rápida"),
    "group_actions": ("Actions", "Acciones"),
    "project_files": ("Jazz Composer project", "Proyecto Jazz Composer"),
    "text_files": ("Text", "Texto"),
    "density_1": ("Bare bones: sevenths, no extensions", "Esqueleto: séptimas sin extensiones"),
    "density_2": ("Diatonic jazz: 9, 11, 13", "Jazz diatónico: 9, 11, 13"),
    "density_3": ("Lydian dominants: 9, 13, #11", "Dominantes lidios: 9, 13, #11"),
    "density_4": ("Altered dominants: b9, #9, b13", "Dominantes alterados: b9, #9, b13"),
    "mod_0": ("No modulations", "Sin modulaciones"),
    "mod_1": ("A few, to neighbor keys", "Pocas, a tonos vecinos"),
    "mod_2": ("Frequent, with chromatic bridges", "Frecuentes, con puentes cromáticos"),
    "mod_3": ("Almost all, distant leaps", "Casi todas, saltos lejanos"),
}

# One-sentence explanation of each function: (group, [(key, English, Spanish), ...]).
# Used by the tooltips and by the "Explain functions" window.
HINTS = [
    ("preset_group", [
        ("preset", "Loads a ready-made combination (style, form, density, accompaniment, tempo) and generates right away. You can tweak everything afterwards.",
                   "Carga una combinación lista (estilo, forma, densidad, acompañamiento, tempo) y genera al instante. Después podés retocar todo."),
    ]),
    ("card_start", [
        ("key", "Home key and its mode. Minor uses iiø–V7alt–i and minor blues.",
                "Centro tonal de partida y su modo. En menor usa iiø–V7alt–i y blues menor."),
        ("style", "Kind of harmonic material in each section: functional, blues, modal or Coltrane cycle.",
                  "Tipo de material armónico de cada sección: funcional, blues, modal o ciclo de Coltrane."),
        ("form", "How sections are ordered and repeated (AABA, ABAC…). 12-bar blues and Rhythm Changes use their own fixed structure.",
                 "Cómo se ordenan y repiten las secciones (AABA, ABAC…). El blues de 12 compases y Rhythm Changes usan su propia estructura fija."),
        ("cadence", "The chords that close the piece: conclusive (V-I), surprise (V-vi), soft (IV-I) or open (V).",
                    "Los acordes que cierran la pieza: conclusiva (V-I), sorpresa (V-vi), suave (IV-I) o abierta (V)."),
    ]),
    ("card_color", [
        ("density", "How many tensions chords carry and how full the voicings sound. Low = simple; high = modern and altered.",
                    "Cuántas tensiones llevan los acordes y qué tan llenos suenan los voicings. Bajo = simple; alto = moderno y alterado."),
        ("mod_density", "How many sections change key and how far they go. Applied when you press Create sections.",
                        "Cuántas secciones cambian de tonalidad y cuán lejos van. Se aplica al pulsar Crear secciones."),
        ("seed", "Number that fixes randomness: the same seed repeats the same progression. Empty = different every time.",
                 "Número que fija el azar: la misma semilla repite la misma progresión. Vacía = distinta cada vez."),
        ("pin_seed", "Copies the seed of your last generation so you can repeat or share it.",
                     "Copia la semilla de lo último que generaste, para poder repetirlo o compartirlo."),
    ]),
    ("card_perf", [
        ("feel", "How chords are played: sustained, swing comping, swing with walking bass, or bossa nova.",
                 "Cómo se tocan los acordes: sostenidos, comping con swing, swing con bajo caminante o bossa nova."),
        ("chord_len", "How long each chord lasts. Adaptive shortens dominants to half a bar.",
                      "Cuánto dura cada acorde. Adaptativa acorta las dominantes a medio compás."),
        ("bpm", "Speed of playback and of exported files.",
                "Velocidad de reproducción y de los archivos exportados."),
        ("velocity", "Overall loudness and brightness. Dominants sound a bit louder and tonics softer.",
                     "Volumen y brillo general. Las dominantes suenan un poco más fuertes y las tónicas más suaves."),
    ]),
    ("card_sections", [
        ("create", "Creates that many sections and decides which ones modulate, based on the Modulations control. Replaces the current ones.",
                   "Crea esa cantidad de secciones y decide cuáles modulan, según el control Modulaciones. Reemplaza las actuales."),
        ("bars", "Number of bars in the selected section. Each section ends with a cadence on its tonic.",
                 "Cantidad de compases de la sección seleccionada. Cada sección termina con una cadencia en su tónica."),
        ("tension", "How loaded the section is within the density palette: 0 = almost no extensions, 3 = maximum.",
                    "Cuánto se carga la sección dentro de la paleta de densidad: 0 = casi sin extensiones, 3 = máximo."),
        ("modulate", "Makes the section start in another key, the one you pick next to it.",
                     "Hace que la sección empiece en otra tonalidad, la que elijas al lado."),
        ("strategy", "Bridge chords that prepare the new key: pivot, dominant chain, tritone, Coltrane or a direct change.",
                     "Acordes puente que preparan la nueva tonalidad: pivote, cadena de dominantes, tritono, Coltrane o cambio directo."),
        ("return_", "When this section ends, the next one goes back to the home key.",
                    "Al terminar esta sección, la siguiente vuelve a la tonalidad inicial."),
    ]),
    ("group_actions", [
        ("generate", "Composes a new progression with the current settings and explains it in the panel.",
                     "Compone una progresión nueva con los parámetros actuales y la explica en el panel."),
        ("play", "Plays the progression. The sounding chord is highlighted and the keyboard shows its notes.",
                 "Reproduce la progresión. Se resalta el acorde que suena y el teclado muestra sus notas."),
        ("stop", "Stops playback.", "Detiene la reproducción."),
        ("panel", "Each line shows bar, chord, degree, function, scale to improvise with, and 3rd/7th motion. Double-click a chord to change it by hand.",
                  "Cada línea muestra compás, acorde, grado, función, escala para improvisar y movimiento de 3ra y 7ma. Doble clic en un acorde para cambiarlo a mano."),
        ("keyboard", "Shows the voicing (the exact notes) of the chord being played.",
                     "Muestra el voicing (las notas exactas) del acorde que está sonando."),
        ("open", "Opens a saved project with its sections, settings and edited chords.",
                 "Abre un proyecto guardado, con sus secciones, ajustes y acordes editados."),
        ("save", "Saves everything to a .jazz.json file to continue later.",
                 "Guarda todo en un archivo .jazz.json para seguir después."),
        ("export", "Exports the panel as text, the audio as WAV, or the notes as MIDI to open in another program.",
                   "Exporta el panel como texto, el audio como WAV o las notas como MIDI para abrir en otro programa."),
        ("theme", "Switches between the light and the dark appearance.",
                  "Cambia entre la apariencia clara y la oscura."),
        ("language", "Switches the language of the whole interface and the panel.",
                     "Cambia el idioma de toda la interfaz y del panel."),
    ]),
]


class I18n:
    def __init__(self, lang: str = "en"):
        self.lang = lang if lang in LANGS else "en"
        self._hints = {key: (en, es) for _, items in HINTS for key, en, es in items}

    def _pick(self, pair) -> str:
        return pair[1] if self.lang == "es" else pair[0]

    def t(self, key: str, **fmt) -> str:
        """An interface text."""
        text = self._pick(UI[key])
        return text.format(**fmt) if fmt else text

    def v(self, value: str) -> str:
        """An engine value (style, scale, form...) as shown in this language."""
        return VALUES_ES.get(value, value) if self.lang == "es" else value

    def hint(self, key: str) -> str:
        return self._pick(self._hints[key]) if key in self._hints else ""
