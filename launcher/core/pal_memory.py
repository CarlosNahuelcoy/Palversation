"""
Long-term memory summaries per Pal, layered on top of the raw recent
history. When a Pal's conversation grows past its rolling window
(history_max_turns), the exchanges about to be dropped are folded into a
running summary instead of being silently forgotten -- this is what lets
a long relationship with a Pal stay coherent beyond just the last few
exchanges, without keeping the entire raw transcript forever (which would
grow the prompt, and the cost, without bound).

Same fail-safe JSON pattern as history_store.py / pal_prompts.py.
"""

import json
from pathlib import Path
from typing import Dict, List


def load_memories(memory_path: Path) -> Dict[str, str]:
    if not memory_path.exists():
        return {}
    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_memories(memory_path: Path, memories: Dict[str, str]) -> None:
    tmp_path = memory_path.with_suffix(memory_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)
    tmp_path.replace(memory_path)


def get_memory(memories: Dict[str, str], pal_key: str) -> str:
    return memories.get(pal_key, "")


def set_memory(memories: Dict[str, str], pal_key: str, summary: str) -> None:
    summary = (summary or "").strip()
    if summary:
        memories[pal_key] = summary
    elif pal_key in memories:
        del memories[pal_key]


def build_memory_hint(summary: str) -> str:
    """Always applied when available (like the friendship/species hints)
    -- this is remembered continuity, not a personality choice, so it
    doesn't depend on whether a custom per-pal prompt is set."""
    if not summary:
        return ""
    return f" Background you remember from earlier times together: {summary}"


def build_summarization_message(existing_summary: str, turns_to_summarize: List[Dict[str, str]]) -> str:
    """Builds the instruction+transcript sent to the LLM to (re)generate
    the running summary, folding in older turns that are about to be
    dropped from the raw rolling history."""
    lines = []
    for turn in turns_to_summarize:
        speaker = "Trainer" if turn.get("role") == "user" else "You"
        lines.append(f"{speaker}: {turn.get('content', '')}")
    transcript = "\n".join(lines)

    prefix = ""
    if existing_summary:
        prefix = f'Here is what you currently remember about your history together: "{existing_summary}"\n\n'

    return (
        f"{prefix}Here are some older exchanges that are about to fall out of "
        f"your immediate memory:\n\n{transcript}\n\n"
        "Update your running memory of your trainer and your history together "
        "in 2-4 short sentences, written in first person. Keep anything from "
        "your existing memory that's still relevant, and fold in anything "
        "notable from these older exchanges (events, things your trainer told "
        "you, promises, feelings). Don't just list events -- write it the way "
        "you'd actually remember them, as an impression, not a transcript. "
        "This replaces your current memory entirely, so don't lose anything "
        "important."
    )
