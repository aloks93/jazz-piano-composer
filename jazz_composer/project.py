"""Save / load projects as JSON: sections, settings and the composition (manual edits included)."""

import json
from dataclasses import asdict, fields
from typing import Any, Dict, List, Optional

from .composer import Composition, CompositionSettings
from .models import Block, Chord, Event, Section

PROJECT_VERSION = 1


def _known(cls, data: Dict[str, Any]) -> Dict[str, Any]:
    """Drop keys the dataclass does not know (projects from another version)."""
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in names}


def _chord_from(data: Dict[str, Any]) -> Chord:
    data = _known(Chord, data)
    data["tensions"] = tuple(data.get("tensions", ()))
    return Chord(**data)


def composition_to_dict(comp: Composition) -> Dict[str, Any]:
    return {
        "blocks": [
            {"name": b.name, "header": b.header, "key_label": b.key_label,
             "chords": [asdict(e.chord) for e in b.events]}
            for b in comp.blocks
        ],
        "tail": [asdict(c) for c in comp.tail],
    }


def composition_from_dict(data: Dict[str, Any], settings: CompositionSettings) -> Composition:
    blocks = [
        Block([Event(_chord_from(c)) for c in b["chords"]], b.get("name", ""), b.get("header"), b.get("key_label", ""))
        for b in data["blocks"]
    ]
    return Composition(settings, blocks, [_chord_from(c) for c in data.get("tail", [])])


def save_project(path: str, settings: CompositionSettings, sections: List[Section],
                 composition: Optional[Composition] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    """`extra`: UI state that is not part of the engine (bpm, accompaniment...)."""
    data = {
        "version": PROJECT_VERSION,
        "settings": asdict(composition.settings if composition else settings),
        "sections": [asdict(s) for s in sections],
        "composition": composition_to_dict(composition) if composition else None,
        "extra": extra or {},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project(path: str):
    """Return (settings, sections, composition or None, extra)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    settings = CompositionSettings(**_known(CompositionSettings, data["settings"]))
    sections = [Section(**_known(Section, s)) for s in data["sections"]]
    composition = composition_from_dict(data["composition"], settings) if data.get("composition") else None
    return settings, sections, composition, data.get("extra", {})
