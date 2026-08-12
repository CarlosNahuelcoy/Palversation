"""
Per-individual Pal custom personality text, keyed by the same stable
CharacterID#InstanceId key used for conversation history. Same fail-safe
JSON pattern as history_store.py.
"""

import json
from pathlib import Path
from typing import Dict


def load_prompts(prompts_path: Path) -> Dict[str, str]:
    if not prompts_path.exists():
        return {}
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_prompts(prompts_path: Path, prompts: Dict[str, str]) -> None:
    tmp_path = prompts_path.with_suffix(prompts_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)
    tmp_path.replace(prompts_path)


def get_prompt(prompts: Dict[str, str], pal_key: str) -> str:
    return prompts.get(pal_key, "")


def set_prompt(prompts: Dict[str, str], pal_key: str, text: str) -> None:
    text = (text or "").strip()
    if text:
        prompts[pal_key] = text
    elif pal_key in prompts:
        del prompts[pal_key]
