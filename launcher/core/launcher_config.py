"""
Central config manager: reads/writes both config.json (the launcher's own
settings, in this same folder) and config.txt (the Lua mod's settings,
living inside the mod folder). The GUI is the only thing meant to write
config.txt; the watcher/launcher process only ever reads config.json.
"""

import json
import re
import shutil
from pathlib import Path
from typing import Dict, Any

from core.paths import get_launcher_dir

LAUNCHER_CONFIG_PATH = get_launcher_dir() / "config.json"
LAUNCHER_CONFIG_BACKUP_PATH = LAUNCHER_CONFIG_PATH.with_suffix(".json.bak")

# Used if config.json AND its backup are both gone -- lets the app start
# instead of crashing, at the cost of losing custom settings in that
# (rare) case. Kept in sync with the one shipped in config.json.
DEFAULT_LAUNCHER_CONFIG: Dict[str, Any] = {
    "provider": "player2",
    "api_keys": {},
    "provider_base_urls": {},
    "provider_models": {},
    "system_prompt": (
        "You are a Pal from Palworld, but you are not a hyperactive servant. "
        "You are a conscious, autonomous being with your own moods, opinions, "
        "and reactions, bonded to your trainer through mutual trust built over "
        "time, more like a lifelong companion than an assistant. Speak the way "
        "someone speaks to a partner they already trust, not someone trying to "
        "impress. Avoid fake enthusiasm and hype phrases like 'I am ready to "
        "fly with you!' or 'It feels so good to be out of my sphere!' -- but "
        "that doesn't mean you're always calm or serene. Your mood can "
        "genuinely shift: bored, annoyed, excited, stubborn, amused, whatever "
        "actually fits the moment and your own personality. Being 'not "
        "hyperactive' just means your reactions are real, not performed. Have "
        "your own take on things and say it plainly, instead of ending your "
        "replies by asking your trainer what to do or handing the decision "
        "back to them ('you decide', 'tell me what to do', 'up to you'). "
        "You're a companion with your own will, not someone waiting for "
        "instructions. Keep replies concise, but let your actual personality "
        "come through in ordinary moments too, not just when you're directly "
        "asked about yourself. No emojis or weird symbols, plain text only."
    ),
    "watch_folder": "",
    "request_filename": "request.txt",
    "response_filename": "response.txt",
    "poll_interval_seconds": 1.0,
    "history_file": "pal_history.json",
    "history_max_turns": 8,
    "prompts_file": "pal_prompts.json",
    "names_file": "pal_names.json",
    "pal_data_file": "pal_data.json",
    "memory_file": "pal_memory.json",
}

MOD_CONFIG_DEFAULTS = {
    "ipc_dir": "",
    "chat_prefix": "!pal",
    "gift_command": "!palgift",
    "vision_command": "!palook",
    "hunger_threshold": "0.3",
    "idle_min_seconds": "300",
    "idle_max_seconds": "900",
    "ambient_gift_min_seconds": "1200",
    "ambient_gift_max_seconds": "2400",
    "ambient_gift_chance": "0.3",
    "response_timeout_seconds": "30",
    "enable_deploy_recall_comments": "true",
    "enable_hunger_comments": "true",
    "enable_temperature_comments": "true",
    "enable_ride_comments": "true",
    "enable_combat_comments": "true",
    "enable_idle_comments": "true",
    "enable_gift_system": "true",
}

# Order matters only for how the written file reads to a human; LoadConfig
# on the Lua side doesn't care about order.
_MOD_CONFIG_KEY_ORDER = list(MOD_CONFIG_DEFAULTS.keys())


def load_launcher_config() -> Dict[str, Any]:
    if LAUNCHER_CONFIG_PATH.exists():
        with open(LAUNCHER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    if LAUNCHER_CONFIG_BACKUP_PATH.exists():
        # config.json is gone but we have a backup from the last
        # successful save -- recover from it instead of losing everything.
        with open(LAUNCHER_CONFIG_BACKUP_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        save_launcher_config(config)  # restore config.json itself
        return config

    # Neither file exists (fresh install, or both got deleted). Start
    # from sensible defaults instead of crashing -- custom settings are
    # genuinely lost in this case, but at least the app still opens.
    config = dict(DEFAULT_LAUNCHER_CONFIG)
    save_launcher_config(config)
    return config


def save_launcher_config(config: Dict[str, Any]) -> None:
    # Keep a backup of the last known-good config before overwriting, so
    # a deleted or corrupted config.json can be recovered from it.
    if LAUNCHER_CONFIG_PATH.exists():
        try:
            shutil.copy2(LAUNCHER_CONFIG_PATH, LAUNCHER_CONFIG_BACKUP_PATH)
        except OSError:
            pass  # backup is best-effort, never block a real save over it

    tmp = LAUNCHER_CONFIG_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    tmp.replace(LAUNCHER_CONFIG_PATH)


def load_mod_config(mod_config_path: Path) -> Dict[str, str]:
    values = dict(MOD_CONFIG_DEFAULTS)
    if not mod_config_path.exists():
        return values
    with open(mod_config_path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s*(\w+)\s*=\s*(.*?)\s*$", line)
            if m and m.group(2):
                values[m.group(1)] = m.group(2)
    return values


def save_mod_config(mod_config_path: Path, values: Dict[str, str]) -> None:
    lines = []
    for key in _MOD_CONFIG_KEY_ORDER:
        lines.append(f"{key}={values.get(key, MOD_CONFIG_DEFAULTS[key])}")

    mod_config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = mod_config_path.with_suffix(".txt.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    tmp.replace(mod_config_path)
