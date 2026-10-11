"""User preferences (language, light/dark theme) kept in a small JSON file in the home directory."""

import json
import locale
from pathlib import Path
from typing import Dict

PREFERENCES_PATH = Path.home() / ".jazz_composer.json"


def _system_language() -> str:
    """'es' on Spanish systems, 'en' everywhere else."""
    try:
        name = (locale.getlocale()[0] or "").lower()
    except (ValueError, TypeError):
        name = ""
    return "es" if name.startswith(("es", "spanish")) else "en"


def load_preferences() -> Dict[str, str]:
    try:
        saved = json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    return {
        "lang": saved.get("lang") if saved.get("lang") in ("en", "es") else _system_language(),
        "theme": saved.get("theme") if saved.get("theme") in ("light", "dark") else "light",
    }


def save_preferences(preferences: Dict[str, str]) -> None:
    try:
        PREFERENCES_PATH.write_text(json.dumps(preferences), encoding="utf-8")
    except OSError:
        pass  # preferences are optional: without write access the app just carries on
