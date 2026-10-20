"""
Installs / updates the in-game Lua mod from the copy bundled with the
launcher, so the mod is never a separate download or a manual copy into
the right folder. Also enables it for UE4SS (enabled.txt, plus mods.txt /
mods.json when present), which used to be another manual step.

The bundled mod lives in mod/Palversation/ next to the source (or one
level up, in the GitHub repo layout), or inside the build (build_exe.bat
bundles it with --add-data).
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.paths import get_launcher_dir, get_bundled_dir

MOD_NAME = "Palversation"

# Files copied into <UE4SS Mods>/Palversation/, relative to the mod root.
_MOD_FILES = (
    Path("Scripts") / "main.lua",
    Path("info.json"),
    Path("enabled.txt"),
)

# Oldest mod that talks to this launcher: 0.14.0 moved the exchange files
# to the fixed %LOCALAPPDATA% data folder; older mods use their own ipc_dir.
MIN_COMPATIBLE_MOD_VERSION = "0.14.0"


def _version_tuple(version: str) -> tuple:
    return tuple(int(part) if part.isdigit() else 0 for part in (version or "0").split("."))


_VERSION_RE = re.compile(r'^\s*local\s+VERSION\s*=\s*"([^"]+)"', re.MULTILINE)


@dataclass
class InstallResult:
    ok: bool
    message: str
    changed: bool = False


def get_bundled_mod_dir() -> Optional[Path]:
    # launcher/mod/ or, in the GitHub repo layout, the repo-root mod/
    # folder next to launcher/.
    launcher_dir = get_launcher_dir()
    candidates = [launcher_dir / "mod" / MOD_NAME, launcher_dir.parent / "mod" / MOD_NAME]
    bundled = get_bundled_dir()
    if bundled:
        candidates.append(bundled / "mod" / MOD_NAME)
    for folder in candidates:
        if (folder / "Scripts" / "main.lua").is_file():
            return folder
    return None


def read_mod_version(mod_dir: Path) -> Optional[str]:
    try:
        text = (mod_dir / "Scripts" / "main.lua").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def installed_mod_dir(mods_dir: Path) -> Path:
    return mods_dir / MOD_NAME


def is_workshop_managed(mods_dir: Path) -> bool:
    """True when Palworld's own mod manager installed the mod from the
    Steam Workshop. It deploys into this same folder and tracks the files
    in Mods/ManagedMods/<PackageName>/InstallManifest.json; overwriting
    them would make the two fight over versions, so in that case the
    launcher leaves the folder alone and only reports."""
    # mods_dir is <Palworld>/Mods/NativeMods/UE4SS/Mods in that layout.
    palworld_mods = mods_dir.parent.parent.parent
    return (palworld_mods / "ManagedMods" / MOD_NAME / "InstallManifest.json").is_file()


def _enable_in_mods_txt(mods_txt: Path) -> None:
    if not mods_txt.is_file():
        return
    lines = mods_txt.read_text(encoding="utf-8", errors="replace").splitlines()
    pattern = re.compile(rf"^\s*{MOD_NAME}\s*:\s*\d+\s*$")
    for i, line in enumerate(lines):
        if pattern.match(line):
            if line.strip().endswith("1"):
                return
            lines[i] = f"{MOD_NAME} : 1"
            break
    else:
        # UE4SS wants its built-in Keybinds entry to stay last.
        insert_at = len(lines)
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("; built-in keybinds") or line.strip().startswith("Keybinds"):
                insert_at = i
                break
        lines.insert(insert_at, f"{MOD_NAME} : 1")
    mods_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _enable_in_mods_json(mods_json: Path) -> None:
    if not mods_json.is_file():
        return
    try:
        entries = json.loads(mods_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(entries, list):
        return
    for entry in entries:
        if isinstance(entry, dict) and entry.get("mod_name") == MOD_NAME:
            if entry.get("mod_enabled") is True:
                return
            entry["mod_enabled"] = True
            break
    else:
        new_entry = {"mod_name": MOD_NAME, "mod_enabled": True}
        keybinds_at = next(
            (i for i, e in enumerate(entries) if isinstance(e, dict) and e.get("mod_name") == "Keybinds"),
            len(entries),
        )
        entries.insert(keybinds_at, new_entry)
    mods_json.write_text(json.dumps(entries, indent=4) + "\n", encoding="utf-8")


def install_or_update_mod(mods_dir: Path) -> InstallResult:
    """Copies the bundled mod into mods_dir/Palversation when it's missing
    or differs from the bundled one, and makes sure UE4SS loads it.
    Safe to call on every launch: does nothing if already up to date."""
    source = get_bundled_mod_dir()
    if source is None:
        return InstallResult(False, "The launcher's bundled copy of the mod is missing. Re-download the launcher.")

    target = installed_mod_dir(mods_dir)
    bundled_version = read_mod_version(source) or "?"

    if is_workshop_managed(mods_dir):
        installed_version = read_mod_version(target)
        if installed_version is None:
            return InstallResult(
                False,
                "Palversation comes from the Steam Workshop but isn't deployed. Enable it "
                "in Palworld's in-game Mods menu, start the game once, then press Re-check.",
            )
        if _version_tuple(installed_version) < _version_tuple(MIN_COMPATIBLE_MOD_VERSION):
            return InstallResult(
                False,
                f"The Steam Workshop copy of the mod is v{installed_version}, too old for this "
                f"launcher (needs v{MIN_COMPATIBLE_MOD_VERSION}+). Let Steam update it: restart "
                "Steam, or unsubscribe and subscribe again, then press Re-check.",
            )
        if installed_version == bundled_version:
            return InstallResult(True, f"Mod v{installed_version} is installed through the Steam Workshop.")
        return InstallResult(
            True,
            f"Installed through the Steam Workshop (mod v{installed_version or '?'}), but this "
            f"launcher ships v{bundled_version}. They're compatible; update whichever is older "
            "if anything misbehaves.",
        )

    changed = False
    try:
        for relative in _MOD_FILES:
            src = source / relative
            dst = target / relative
            if not src.is_file():
                continue
            data = src.read_bytes()
            if dst.is_file() and dst.read_bytes() == data:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            changed = True
        _enable_in_mods_txt(mods_dir / "mods.txt")
        _enable_in_mods_json(mods_dir / "mods.json")
    except PermissionError:
        return InstallResult(
            False,
            f"Windows didn't allow writing to {target}. Run the launcher as "
            "administrator once so it can install the mod.",
        )
    except OSError as e:
        return InstallResult(False, f"Could not install the mod into {target}: {e}")

    if changed:
        return InstallResult(True, f"Mod v{bundled_version} installed into {target}. Restart Palworld if it's already open.", True)
    return InstallResult(True, f"Mod v{bundled_version} is installed and up to date.")
