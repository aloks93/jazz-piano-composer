"""Jazz Piano Composer.

An educational jazz progression generator with a built-in synthesizer.

Layers, from the inside out (each one only imports the ones above it):
  theory      -> notes, scales, chord symbols
  models      -> shared dataclasses
  harmony     -> tensions, cadences, secondary dominants
  modulation  -> bridges between keys
  generators  -> progressions per style (standard, blues, modal, Coltrane, rhythm changes)
  scales      -> chord-scale suggestions
  composer    -> assembles sections + form + final cadence (no UI)
  voicing     -> chord -> MIDI notes with voice leading
  performance -> progression -> timed notes (comping, walking bass, bossa)
  synth       -> timed notes -> PCM / WAV (numpy)
  midi        -> timed notes -> Standard MIDI File
  project     -> save / load projects as JSON
  audio       -> playback through pygame
  ui          -> Tkinter application
"""

__version__ = "1.0.0"
APP_NAME = "Jazz Piano Composer"
