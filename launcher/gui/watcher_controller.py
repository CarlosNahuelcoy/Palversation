"""
Manages the background watcher thread from inside the GUI process, so the
whole app (settings + the actual Player2 connection) runs as a single
program -- this matters because it's what eventually gets packaged into
one .exe.
"""

import threading
import queue

from core.watcher import run_watch_loop
from core.launcher_runtime import build_provider, get_watch_folder, get_data_paths, ConfigError
from core.logger import add_sink


class WatcherController:
    def __init__(self, get_config):
        """get_config: a callable returning the current config dict
        (so this always reads the latest saved settings, not a snapshot)."""
        self._get_config = get_config
        self._thread = None
        self._stop_event = None
        self.log_queue = queue.Queue()
        self._sink_registered = False

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        """Returns None on success, or an error message string if the
        config isn't ready yet (missing API key, folders, etc)."""
        if self.is_running():
            return None

        config = self._get_config()
        try:
            provider = build_provider(config)
            watch_folder = get_watch_folder(config)
        except ConfigError as e:
            return str(e)

        history_path, prompts_path, names_path, pal_data_path, memory_path = get_data_paths(config)

        if not self._sink_registered:
            add_sink(self.log_queue.put)
            self._sink_registered = True

        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=run_watch_loop,
            kwargs=dict(
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
                stop_event=self._stop_event,
            ),
            daemon=True,  # never blocks the app from closing
        )
        self._thread.start()
        return None

    def stop(self):
        if self._stop_event:
            self._stop_event.set()

    def restart(self):
        """Stops and waits briefly for the old thread to actually exit
        before starting a new one, so both never poll the same folder at
        once (harmless if it happened, just untidy -- this avoids it)."""
        old_thread = self._thread
        self.stop()
        if old_thread is not None:
            old_thread.join(timeout=3.0)
        return self.start()
