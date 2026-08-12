"""
Resolves the launcher's base directory: the folder containing this
project's files when running from source (`python gui/app.py`), or the
folder containing the .exe when running as a PyInstaller-built
executable. Every module that needs "where does config.json / history /
etc live" should use get_launcher_dir() instead of `Path(__file__)`
directly -- once bundled into a single .exe, `__file__` no longer points
next to the real executable (it points inside PyInstaller's internal
bundle), which would silently read/write files in the wrong place and
lose everything between runs.
"""

import sys
from pathlib import Path
from typing import Optional


def get_launcher_dir() -> Path:
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-built executable. sys.executable is the
        # real .exe's own path on disk (true for both --onefile and
        # --onedir builds), so files end up next to the .exe, not inside
        # the temporary extraction folder or the bundled library archive.
        return Path(sys.executable).resolve().parent
    # Running from source.
    return Path(__file__).resolve().parent.parent


def get_bundled_dir() -> Optional[Path]:
    """Returns PyInstaller's temp extraction folder when running as a
    frozen build with data files bundled via --add-data (build_exe.bat
    does this for pal_data.json and assets/), or None when running from
    source or when nothing was bundled."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None
