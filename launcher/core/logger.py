"""
Minimal logging shim used across core/. Always prints to stdout (keeps
`python main.py` console output working exactly as before), and also
forwards each line to any registered sink -- this is how the GUI's
Console panel gets live output from the background watcher thread
without the watcher needing to know the GUI exists.
"""

import threading

_lock = threading.Lock()
_sinks = []


def add_sink(fn) -> None:
    with _lock:
        if fn not in _sinks:
            _sinks.append(fn)


def remove_sink(fn) -> None:
    with _lock:
        if fn in _sinks:
            _sinks.remove(fn)


def log(message: str) -> None:
    print(message)
    with _lock:
        sinks = list(_sinks)
    for sink in sinks:
        try:
            sink(message)
        except Exception:
            pass  # a broken sink should never take down the watcher
