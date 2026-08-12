"""
Persistent mapping from a Pal's stable key to the last known display name
seen for it (nickname if set, otherwise the raw species ID) -- purely so
the GUI can show a friendly label in the Pals list instead of the raw
CharacterID#InstanceId key. Not used for anything the LLM sees; the
prompt already reads the name fresh from Lua on every single event.
"""

import json
from pathlib import Path
from typing import Dict


def load_names(names_path: Path) -> Dict[str, str]:
    if not names_path.exists():
        return {}
    try:
        with open(names_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_names(names_path: Path, names: Dict[str, str]) -> None:
    tmp_path = names_path.with_suffix(names_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=2)
    tmp_path.replace(names_path)


def get_name(names: Dict[str, str], pal_key: str, fallback: str) -> str:
    return names.get(pal_key, fallback)


def set_name(names: Dict[str, str], pal_key: str, name: str) -> None:
    if name:
        names[pal_key] = name
