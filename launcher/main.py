"""
CLI entry point for the Palversation launcher (no GUI). Mainly useful for
debugging without the graphical console. `python gui/app.py` is the
normal way to run everything (settings + the live connection) together.
"""

import sys

from core.launcher_config import load_launcher_config
from core.launcher_runtime import build_provider, get_watch_folder, get_data_paths, ConfigError
from core.watcher import run_watch_loop


def main():
    config = load_launcher_config()

    try:
        provider = build_provider(config)
        watch_folder = get_watch_folder(config)
    except ConfigError as e:
        print(f"[Palversation Launcher] {e}")
        sys.exit(1)

    history_path, prompts_path, names_path, pal_data_path, memory_path = get_data_paths(config)

    run_watch_loop(
        provider=provider,
        watch_folder=watch_folder,
        request_filename=config["request_filename"],
        response_filename=config["response_filename"],
        poll_interval_seconds=config["poll_interval_seconds"],
        history_path=history_path,
        history_max_turns=config.get("history_max_turns", 8),
        prompts_path=prompts_path,
        names_path=names_path,
        pal_data_path=pal_data_path,
        memory_path=memory_path,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Palversation Launcher] Stopped.")
