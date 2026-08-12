"""
Shared logic to build an LLMProvider + resolve all the file paths from
the launcher's config.json. Used by both the CLI entry point (main.py,
kept working for debugging without the GUI) and the GUI's background
watcher thread, so the two never duplicate or drift from each other.
"""

from pathlib import Path
from typing import Tuple

from providers.base import LLMProvider
from providers.registry import get_provider_spec
from core.paths import get_launcher_dir

LAUNCHER_DIR = get_launcher_dir()


class ConfigError(Exception):
    """Raised when config.json isn't complete enough to start the watcher."""


def build_provider(config: dict) -> LLMProvider:
    provider_id = config.get("provider", "player2")
    try:
        spec = get_provider_spec(provider_id)
    except ValueError as e:
        raise ConfigError(str(e)) from e

    api_key = config.get("api_keys", {}).get(provider_id, "")
    if spec.requires_api_key and (not api_key or api_key == "PUT_YOUR_API_KEY_HERE"):
        raise ConfigError(f"No API key configured for provider '{provider_id}' (api_keys.{provider_id}).")

    base_url = config.get("provider_base_urls", {}).get(provider_id, spec.default_base_url)
    model_name = config.get("provider_models", {}).get(provider_id, spec.default_model)
    system_prompt = config.get("system_prompt", "")

    return spec.factory(api_key=api_key, base_url=base_url, system_prompt=system_prompt, model_name=model_name)


def get_watch_folder(config: dict) -> Path:
    watch_folder_str = config.get("watch_folder", "").strip()
    if not watch_folder_str or watch_folder_str == "PUT_THE_ABSOLUTE_PATH_TO_THE_ipc_FOLDER_HERE":
        # No IPC folder configured -- default to a folder right next to
        # the launcher itself instead of blocking startup on it. This is
        # created automatically (see core/watcher.py's mkdir call); most
        # players never need to point it anywhere else.
        return LAUNCHER_DIR / "ipc"
    return Path(watch_folder_str)


def default_watch_folder() -> Path:
    """The same default get_watch_folder() falls back to, exposed so the
    GUI can show it as a suggestion even before anything is saved."""
    return LAUNCHER_DIR / "ipc"


def get_data_paths(config: dict) -> Tuple[Path, Path, Path, Path, Path]:
    history_path = LAUNCHER_DIR / config.get("history_file", "pal_history.json")
    prompts_path = LAUNCHER_DIR / config.get("prompts_file", "pal_prompts.json")
    names_path = LAUNCHER_DIR / config.get("names_file", "pal_names.json")
    pal_data_path = LAUNCHER_DIR / config.get("pal_data_file", "pal_data.json")
    memory_path = LAUNCHER_DIR / config.get("memory_file", "pal_memory.json")
    return history_path, prompts_path, names_path, pal_data_path, memory_path
