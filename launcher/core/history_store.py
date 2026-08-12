"""
Simple JSON-based conversation history, keyed by the stable per-individual
Pal key (CharacterID + InstanceId, computed on the Lua side).

Each turn is timestamped (real wall-clock time, not in-game time -- much
simpler, no UE4SS involved, and it directly captures what actually
matters here: how long the player really left the Pal alone between
exchanges). turns_to_messages_with_time_gaps() uses that to inject a
natural-language time-gap note before a turn that came a while after the
previous one, so a conversation spread across a play session doesn't read
to the model like it all happened in one unbroken stretch.

Fail-safe: if the file is missing or corrupted, we start fresh instead of
crashing (same approach the reference mod uses for its own bond file).
"""

import json
import time
from pathlib import Path
from typing import Dict, List

Turn = Dict[str, object]  # {"role": "user"|"assistant", "content": "...", "ts": <float, optional>}


def load_history(history_path: Path) -> Dict[str, List[Turn]]:
    if not history_path.exists():
        return {}
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_history(history_path: Path, history: Dict[str, List[Turn]]) -> None:
    tmp_path = history_path.with_suffix(history_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    tmp_path.replace(history_path)


def get_turns(history: Dict[str, List[Turn]], pal_key: str) -> List[Turn]:
    return history.get(pal_key, [])


def append_turn(
    history: Dict[str, List[Turn]],
    pal_key: str,
    user_content: str,
    assistant_content: str,
    max_turns: int,
) -> List[Turn]:
    """Adds one exchange (user + assistant), both timestamped 'now', for
    this Pal, trimming old ones so we keep at most 'max_turns' exchanges
    (max_turns * 2 messages). Returns the turns that got dropped from the
    front (empty list if none), so the caller can fold them into a
    longer-term memory summary instead of losing them outright."""
    turns = history.setdefault(pal_key, [])
    now = time.time()
    turns.append({"role": "user", "content": user_content, "ts": now})
    turns.append({"role": "assistant", "content": assistant_content, "ts": now})

    max_messages = max_turns * 2
    dropped: List[Turn] = []
    if len(turns) > max_messages:
        cutoff = len(turns) - max_messages
        dropped = turns[:cutoff]
        del turns[:cutoff]
    return dropped


def _format_time_gap(seconds: float) -> str:
    """Natural-language English gap description (our prompts are all
    written in English even though the Pal must respond in Spanish, so
    this stays consistent with that). Returns "" for gaps too small to
    matter (a normal back-and-forth)."""
    if seconds < 90:
        return ""
    minutes = seconds / 60
    if minutes < 60:
        return "a few minutes"
    hours = minutes / 60
    if hours < 1.5:
        return "about an hour"
    if hours < 20:
        return f"about {int(round(hours))} hours"
    days = hours / 24
    if days < 1.5:
        return "about a day"
    if days < 7:
        return f"about {int(days)} days"
    weeks = days / 7
    return f"about {int(weeks)} week{'s' if weeks >= 2 else ''}"


def turns_to_messages_with_time_gaps(raw_turns: List[Turn]) -> List[Dict[str, str]]:
    """Converts stored turns (which may carry a 'ts' field) into clean
    {role, content} pairs ready to send to a provider, inserting a short
    time-gap note at the start of a user turn when a real gap preceded
    it. Turns without a 'ts' (older history saved before this feature
    existed) are passed through unchanged."""
    messages: List[Dict[str, str]] = []
    last_ts = None
    for turn in raw_turns:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        ts = turn.get("ts")
        if role == "user" and last_ts is not None and ts is not None:
            gap_text = _format_time_gap(ts - last_ts)
            if gap_text:
                content = f"[{gap_text} later] {content}"
        messages.append({"role": role, "content": content})
        if ts is not None:
            last_ts = ts
    return messages


def time_gap_prefix_for_now(raw_turns: List[Turn]) -> str:
    """Returns a "[gap later] " prefix (or "") for the CURRENT live
    message being processed right now, based on how long it's been since
    the last stored turn. This is the case that matters most in
    practice -- the player left the Pal alone for a while and just came
    back -- since the live message isn't in raw_turns yet when this
    runs, turns_to_messages_with_time_gaps() alone can't cover it."""
    if not raw_turns:
        return ""
    last_ts = raw_turns[-1].get("ts")
    if last_ts is None:
        return ""
    gap_text = _format_time_gap(time.time() - last_ts)
    return f"[{gap_text} later] " if gap_text else ""
