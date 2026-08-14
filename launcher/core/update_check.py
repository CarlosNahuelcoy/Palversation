"""
Lightweight update check: on startup, asks GitHub's Releases API for the
latest published release and compares it against CURRENT_VERSION. This
never downloads or replaces anything automatically -- a running .exe on
Windows can't safely overwrite itself anyway, and self-replacing updaters
need a separate helper process to do it safely. This just tells the
player a newer version exists and links straight to the Release page, so
they don't have to remember to check GitHub themselves.

The network call (fetch_latest_release) is blocking and meant to be run
in a background thread -- see app.py's _start_update_check -- so a slow
or failed connection never delays the GUI from opening.
"""

import json
import urllib.request

# Bump this by hand with every release you publish, so it matches the
# GitHub tag (e.g. CURRENT_VERSION = "1.1.0" for a "v1.1.0" tag). This is
# the ONLY place that needs updating for the check itself to work.
CURRENT_VERSION = "1.0.1"

RELEASES_API_URL = "https://api.github.com/repos/CarlosNahuelcoy/Palversation/releases/latest"
REQUEST_TIMEOUT_SECONDS = 5


def _parse_version(version_str: str):
    """Turns 'v1.2.10' or '1.2.10' into (1, 2, 10) for a numeric
    comparison. Falls back to (0,) for anything that doesn't parse the
    way we expect, so an unusual tag name never crashes the check -- it
    just won't register as newer."""
    cleaned = version_str.strip().lstrip("vV")
    parts = []
    for piece in cleaned.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def fetch_latest_release():
    """Blocking network call -- always run this in a background thread,
    never on the GUI thread. Returns a dict with 'version' and 'url' if
    a release was found, or None if the check failed for any reason at
    all (offline, GitHub unreachable, no releases published yet, rate
    limited, unexpected response shape, ...). Failing silently on
    purpose: this is a nice-to-have notice, never something that should
    interrupt someone from using the mod."""
    try:
        request = urllib.request.Request(
            RELEASES_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Palversation-Launcher",
            },
        )
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        tag_name = data.get("tag_name")
        html_url = data.get("html_url")
        if not tag_name or not html_url:
            return None
        return {"version": tag_name, "url": html_url}
    except Exception:
        return None
