"""
Finds the Palworld install and its UE4SS Mods folder on its own, so the
player never has to browse to a deeply nested folder by hand.

Palworld's Steam app ID is 1623730. Steam's own install path comes from
the registry, and every extra Steam library (other drives) is listed in
steamapps/libraryfolders.vdf. A manual override (config "palworld_dir",
set from the Setup tab's Browse button) always wins, which also covers
non-Steam installs.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

PALWORLD_APP_ID = "1623730"
PALWORLD_STEAM_URI = f"steam://rungameid/{PALWORLD_APP_ID}"

# Where UE4SS can live, relative to the Palworld root, in priority order:
# Palworld's own native mod loader layout first (what the Workshop /
# in-game mod manager uses), then the two classic manual installs into
# Pal/Binaries/Win64.
_UE4SS_CANDIDATES = (
    Path("Mods") / "NativeMods" / "UE4SS",
    Path("Pal") / "Binaries" / "Win64" / "ue4ss",
    Path("Pal") / "Binaries" / "Win64",
)


@dataclass
class UE4SSInstall:
    root: Path       # folder containing UE4SS.dll
    mods_dir: Path   # folder where Lua mods go (root/Mods)


def _steam_install_dirs() -> Iterator[Path]:
    try:
        import winreg
    except ImportError:
        return
    lookups = (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    )
    for hive, key_path, value_name in lookups:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
        except OSError:
            continue
        if value:
            yield Path(value)


def _steam_library_dirs() -> Iterator[Path]:
    seen = set()
    for steam_dir in _steam_install_dirs():
        candidates = [steam_dir]
        vdf = steam_dir / "steamapps" / "libraryfolders.vdf"
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
            # Entries look like:  "path"    "D:\\SteamLibrary"
            for raw in re.findall(r'"path"\s+"([^"]+)"', text):
                candidates.append(Path(raw.replace("\\\\", "\\")))
        except OSError:
            pass
        for lib in candidates:
            key = str(lib).lower()
            if key not in seen:
                seen.add(key)
                yield lib


def is_palworld_dir(folder: Path) -> bool:
    return (folder / "Palworld.exe").is_file() or (folder / "Pal" / "Binaries" / "Win64").is_dir()


def normalize_palworld_dir(selected: Path) -> Optional[Path]:
    """Accepts the Palworld folder itself or any folder inside it (e.g.
    the player browsed to Pal/Binaries/Win64 or the Mods folder) and
    returns the actual game root, or None if it isn't inside one."""
    for folder in (selected, *selected.parents):
        if is_palworld_dir(folder):
            return folder
    return None


def find_palworld_dir(override: str = "") -> Optional[Path]:
    if override and override.strip():
        found = normalize_palworld_dir(Path(override.strip()))
        if found:
            return found
    for lib in _steam_library_dirs():
        candidate = lib / "steamapps" / "common" / "Palworld"
        if is_palworld_dir(candidate):
            return candidate
    return None


def find_ue4ss(palworld_dir: Path) -> Optional[UE4SSInstall]:
    for relative in _UE4SS_CANDIDATES:
        root = palworld_dir / relative
        if (root / "UE4SS.dll").is_file():
            return UE4SSInstall(root=root, mods_dir=root / "Mods")
    return None
