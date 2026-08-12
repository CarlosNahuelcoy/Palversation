"""
Reading/writing the files we use to communicate with the Lua mod. This file
protocol is our own design (it doesn't come from any UE4SS or Palworld
documentation), so the Lua side has to be written to match this.

Protocol (plain text, 7 lines, not JSON, so Lua doesn't need to parse JSON
by hand):
  Line 1: active Pal's name
  Line 2: active Pal's element (or "None")
  Line 3: active Pal's stable key (CharacterID#InstanceId)
  Line 4: active Pal's passive skill IDs -- DISABLED, always empty (see
          main.lua's GetPalPassiveIds comment: a confirmed UE4SS
          use-after-free bug on TArray return values caused a real crash)
  Line 5: active Pal's friendship, "rank,point" (the game's real trust/bond
          value, confirmed via simple scalar getters -- not the same bug
          risk as line 4), or empty if unavailable
  Line 6: event type (chat, deploy, recall, hunger, cold, heat,
          ride_start, ride_end, combat, idle, gift_check)
  Line 7 onward: content (the player's message if event_type is "chat",
          empty or extra detail otherwise)

  - The Lua mod writes <watch_folder>/<request_filename> in that format.
  - This launcher detects it, processes it, and deletes it.
  - This launcher writes <watch_folder>/<response_filename> with the
    response text as plain text (no special formatting).
  - The Lua mod reads it, shows it in the chat, and deletes it.

Files are written atomically (write to a .tmp then rename) to avoid the
other side reading a half-written file.
"""

import os
from pathlib import Path
from typing import Optional, Tuple


def read_request(request_path: Path) -> Optional[str]:
    """Returns the raw text of the request (the 7 lines), or None if it
    doesn't exist or is empty.

    Uses 'utf-8-sig' instead of 'utf-8' because some tools (e.g.
    PowerShell's 'Out-File -Encoding utf8' on Windows) add a BOM at the
    start of the file; 'utf-8-sig' tolerates it, strict 'utf-8' does not."""
    if not request_path.exists():
        return None
    try:
        with open(request_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
        content = content.strip()
        return content if content else None
    except OSError as e:
        print(f"[Palversation Launcher] Could not read {request_path.name} yet: {e}")
        return None


def parse_request(raw_text: str) -> Tuple[str, str, str, str, str, str, str]:
    """Splits the raw text into (pal_name, pal_element, pal_key,
    pal_passives, pal_friendship, event_type, content). If a line is
    missing, returns an empty string for that part (event_type defaults
    to "chat")."""
    lines = raw_text.split("\n")
    pal_name = lines[0].strip() if len(lines) > 0 else ""
    pal_element = lines[1].strip() if len(lines) > 1 else ""
    pal_key = lines[2].strip() if len(lines) > 2 else ""
    pal_passives = lines[3].strip() if len(lines) > 3 else ""
    pal_friendship = lines[4].strip() if len(lines) > 4 else ""
    event_type = lines[5].strip() if len(lines) > 5 else "chat"
    content = "\n".join(lines[6:]).strip() if len(lines) > 6 else ""
    return pal_name, pal_element, pal_key, pal_passives, pal_friendship, event_type, content


def delete_request(request_path: Path) -> None:
    try:
        request_path.unlink(missing_ok=True)
    except OSError:
        pass


def write_response(response_path: Path, text: str) -> None:
    """Writes the response file atomically."""
    tmp_path = response_path.with_suffix(response_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp_path, response_path)
