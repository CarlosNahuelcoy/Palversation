"""
Player2 account connection. Tries the local Player2 desktop app first
(instant, no browser needed), and falls back to the OAuth Device Code
flow (opens the browser for a one-time approval) if the app isn't
running. This is Player2's own confirmed working mechanism for
third-party apps, adapted from a real reference integration -- not
invented.

IMPORTANT: PLAYER2_CLIENT_ID below is a placeholder. Register your own
app on the Player2 Developer Dashboard to get a real Game Client ID
before distributing this. Reusing someone else's ID would misattribute
every connection made through this app to theirs instead of yours.
"""

import threading
import time
import webbrowser
from typing import Callable, Optional

import requests

PLAYER2_BASE_URL = "https://api.player2.game/v1"
PLAYER2_LOCAL_URL = "http://localhost:4315"

PLAYER2_CLIENT_ID = "019fcd6c-41b2-7a18-ad57-3aa38f0b843e"  # from the Player2 Developer Dashboard

_DEVICE_CODE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
_POLL_TIMEOUT_SECONDS = 300


def connect_player2_account(
    on_key: Callable[[str], None],
    on_status: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> None:
    """Starts the connection in a background thread (never blocks the
    caller). Calls on_key(p2_key) once connected, on_status(message) for
    progress updates along the way, on_error(message) if it fails."""

    def _status(msg: str):
        if on_status:
            on_status(msg)

    def _error(msg: str):
        if on_error:
            on_error(msg)

    def run():
        if PLAYER2_CLIENT_ID == "PUT_YOUR_PLAYER2_CLIENT_ID_HERE":
            _error("PLAYER2_CLIENT_ID is still a placeholder. Register an app on the Player2 Developer Dashboard first.")
            return

        # Path 1: local Player2 app (instant, no browser).
        _status("Checking for the Player2 app...")
        try:
            response = requests.post(
                f"{PLAYER2_LOCAL_URL}/v1/login/web/{PLAYER2_CLIENT_ID}",
                timeout=3,
            )
            if response.ok:
                data = response.json()
                if data.get("p2Key"):
                    on_key(data["p2Key"])
                    return
        except Exception:
            pass  # local app not running, fall through to the browser flow

        # Path 2: OAuth Device Code flow.
        _status("Opening your browser to approve access...")
        try:
            response = requests.post(
                f"{PLAYER2_BASE_URL}/login/device/new",
                json={"client_id": PLAYER2_CLIENT_ID},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            _error(f"Could not start Player2 login: {e}")
            return

        verification_uri = data.get("verificationUriComplete") or data.get("verificationUri")
        device_code = data.get("deviceCode")
        interval = data.get("interval", 5)

        if not device_code:
            _error("Player2 login did not return a device code.")
            return

        if verification_uri:
            webbrowser.open(verification_uri)

        _status("Waiting for you to approve in the browser...")
        deadline = time.time() + _POLL_TIMEOUT_SECONDS
        while time.time() < deadline:
            time.sleep(interval)
            try:
                response = requests.post(
                    f"{PLAYER2_BASE_URL}/login/device/token",
                    json={
                        "client_id": PLAYER2_CLIENT_ID,
                        "device_code": device_code,
                        "grant_type": _DEVICE_CODE_GRANT_TYPE,
                    },
                    timeout=10,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("p2Key"):
                        on_key(data["p2Key"])
                        return
            except requests.RequestException:
                pass  # transient network hiccup, keep polling until the deadline

        _error("Player2 login timed out. Try again.")

    run()


def start_connect(on_key, on_status=None, on_error=None) -> None:
    threading.Thread(target=connect_player2_account, args=(on_key, on_status, on_error), daemon=True).start()
