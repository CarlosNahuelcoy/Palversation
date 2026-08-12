"""
Captures the currently active (foreground) window as a base64-encoded
PNG, for use with vision-capable LLM providers (confirmed working with
Player2's /chat/completions image_url content blocks, same format other
OpenAI-compatible providers use).

Uses mss (screen-region capture from the desktop compositor's actual
output) rather than the Windows PrintWindow API, because PrintWindow
usually returns a black/blank image for hardware-accelerated games:
DirectX/OpenGL/Vulkan render via the GPU, not the window's GDI surface
that PrintWindow reads. mss instead captures whatever the desktop is
really displaying, which is always correct -- the tradeoff is it would
capture whatever overlaps the window at that instant, but in practice
that's a non-issue here: capture only happens right after the player
typed a command into the game's own chat, which requires the game
window to already be focused and on top.
"""

import base64

try:
    import mss
    import mss.tools
    import win32gui
    _AVAILABLE = True
    _IMPORT_ERROR = None
except ImportError as e:
    _AVAILABLE = False
    _IMPORT_ERROR = str(e)


def is_available() -> bool:
    return _AVAILABLE


def capture_foreground_window_base64():
    """Returns (base64_png_string, window_title). Raises RuntimeError if
    the required libraries aren't installed or the capture fails for any
    reason -- callers should treat this as a soft failure, not crash the
    whole response pipeline over it."""
    if not _AVAILABLE:
        raise RuntimeError(
            f"mss and pywin32 are required for screenshots (pip install mss pywin32): {_IMPORT_ERROR}"
        )

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        raise RuntimeError("Could not find the foreground window.")
    title = win32gui.GetWindowText(hwnd)

    client_rect = win32gui.GetClientRect(hwnd)
    client_width = client_rect[2] - client_rect[0]
    client_height = client_rect[3] - client_rect[1]
    if client_width <= 0 or client_height <= 0:
        raise RuntimeError("Foreground window has no visible client area (minimized?).")

    screen_left, screen_top = win32gui.ClientToScreen(hwnd, (0, 0))

    bbox = {
        "left": screen_left,
        "top": screen_top,
        "width": client_width,
        "height": client_height,
    }

    with mss.mss() as sct:
        shot = sct.grab(bbox)
        png_bytes = mss.tools.to_png(shot.rgb, shot.size)

    b64 = base64.b64encode(png_bytes).decode("ascii")
    return b64, title
