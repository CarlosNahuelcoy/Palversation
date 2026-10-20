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
from core.paths import get_launcher_dir, get_data_dir

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

    return spec.factory(
        api_key=api_key, base_url=base_url, system_prompt=system_prompt, model_name=model_name,
        timeout_seconds=provider_timeout_seconds(),
    )


def provider_timeout_seconds() -> float:
    """How long the launcher waits for the AI, derived from the in-game
    mod's "Response timeout" (Events tab) so raising it there -- e.g. for a
    slow local model -- actually lets slow replies through. A few seconds
    are kept as margin so the launcher answers before the mod gives up."""
    from core.launcher_config import load_mod_config, get_mod_config_path
    try:
        mod_timeout = float(load_mod_config(get_mod_config_path()).get("response_timeout_seconds", 30))
    except (OSError, ValueError):
        mod_timeout = 30.0
    return max(10.0, mod_timeout - 3.0)


def get_watch_folder(config: dict) -> Path:
    # Always the fixed data folder the Lua mod also derives on its own
    # (see core/paths.get_data_dir). Older configs' "watch_folder" is
    # ignored on purpose: a mismatch between the two sides was the main
    # cause of "!pal does nothing".
    return get_data_dir()


def get_data_paths(config: dict) -> Tuple[Path, Path, Path, Path, Path]:
    # Player data lives in the shared data folder; pal_data.json is static
    # reference data shipped with the launcher, so it stays next to it.
    data_dir = get_data_dir()
    history_path = data_dir / config.get("history_file", "pal_history.json")
    prompts_path = data_dir / config.get("prompts_file", "pal_prompts.json")
    names_path = data_dir / config.get("names_file", "pal_names.json")
    pal_data_path = LAUNCHER_DIR / config.get("pal_data_file", "pal_data.json")
    memory_path = data_dir / config.get("memory_file", "pal_memory.json")
    return history_path, prompts_path, names_path, pal_data_path, memory_path
