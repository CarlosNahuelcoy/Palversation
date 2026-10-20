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

import os
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


def get_data_dir() -> Path:
    """The fixed folder shared with the in-game Lua mod:
    %LOCALAPPDATA%/Palversation. Both sides derive it on their own (the
    mod via os.getenv("LOCALAPPDATA")), so no path ever has to be
    configured. Holds the mod's config.txt, the request/response exchange
    files and pal_species_names.txt. Created on demand."""
    base = os.environ.get("LOCALAPPDATA")
    data_dir = Path(base) / "Palversation" if base else get_launcher_dir() / "ipc"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# Per-player files that used to live next to the exe (pre-1.1). Moving
# them to the data folder means extracting a new version somewhere else,
# or deleting the old folder, never loses a Pal's memories or settings.
USER_DATA_FILES = (
    "config.json",
    "config.json.bak",
    "pal_history.json",
    "pal_prompts.json",
    "pal_names.json",
    "pal_memory.json",
)


def import_user_data(from_dir: Path, overwrite: bool = False) -> list:
    """Copies the player's files from an old launcher folder into the
    data folder. Never deletes the originals. Returns the names copied."""
    import shutil
    data_dir = get_data_dir()
    copied = []
    for name in USER_DATA_FILES:
        src = from_dir / name
        dst = data_dir / name
        if not src.is_file() or (dst.exists() and not overwrite):
            continue
        shutil.copy2(src, dst)
        copied.append(name)
    return copied


def migrate_user_data() -> list:
    """One-time automatic move for players who extracted the new version
    over the old one: only copies files that don't exist in the data
    folder yet, so it's a no-op on every launch after the first."""
    launcher_dir = get_launcher_dir()
    if launcher_dir == get_data_dir():
        return []
    return import_user_data(launcher_dir, overwrite=False)
