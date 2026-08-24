"""
Best-effort diagnostics for the three-piece Palversation install (UE4SS +
mod folder + launcher). Nothing here is a hard requirement to start the
watcher -- these are advisory checks, run at startup and on demand from a
"Verify installation" button, so the player gets an actionable message
instead of a silent "!pal did nothing".
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class CheckStatus(Enum):
    OK = "ok"
    MISSING = "missing"
    UNKNOWN = "unknown"  # couldn't verify either way, not necessarily a problem


@dataclass
class CheckResult:
    status: CheckStatus
    message: str


# The exact folder chain UE4SS expects a Lua mod to live in, read from
# innermost to outermost parent: mod_folder itself sits directly inside
# .../Mods/NativeMods/UE4SS/Mods/<mod_folder_name>.
EXPECTED_LOCATION_TAIL = ("Mods", "UE4SS", "NativeMods", "Mods")


def check_mod_location(resolved_folder: Path) -> CheckResult:
    """
    Checks that the (already-resolved, main.lua-containing) mod folder is
    actually installed inside Palworld's UE4SS Mods folder, not just
    sitting somewhere else with the right files in it -- e.g. still in a
    Downloads folder, extracted to the Desktop, or dropped directly into
    Palworld/Mods instead of Palworld/Mods/NativeMods/UE4SS/Mods. This is
    the other common source of "!pal does nothing": the launcher points
    at a real main.lua, but UE4SS itself never loads it because it's not
    where UE4SS actually looks.
    """
    parents = list(resolved_folder.parents)
    actual_tail = tuple(p.name for p in parents[:4])

    if actual_tail == EXPECTED_LOCATION_TAIL:
        return CheckResult(
            CheckStatus.OK,
            "This folder is correctly installed inside Palworld's UE4SS "
            "Mods folder.",
        )

    return CheckResult(
        CheckStatus.MISSING,
        f"{resolved_folder} has a main.lua, but doesn't look like it's "
        "inside Palworld's UE4SS Mods folder. It should be at "
        ".../Palworld/Mods/NativeMods/UE4SS/Mods/Palversation -- if this "
        "is a leftover copy (e.g. still in Downloads, or on the Desktop), "
        "move or reinstall it into that folder, then point the launcher "
        "there instead.",
    )


def find_mod_lua_folder(selected_folder: Path) -> Optional[Path]:
    """
    Given whatever folder the player picked in the Folders tab, return the
    folder that should actually be used (the one directly containing
    Scripts/main.lua), auto-correcting the single most common setup
    mistake: pointing at the Scripts subfolder itself instead of its
    parent.

    Returns None if neither the given folder nor its parent look like a
    valid Palversation install (no main.lua found either way) -- in that
    case the caller should not silently guess further, just surface the
    problem.
    """
    if not selected_folder or not selected_folder.is_dir():
        return None

    # Correct case: the folder itself has Scripts/main.lua inside.
    if (selected_folder / "Scripts" / "main.lua").is_file():
        return selected_folder

    # Common mistake: the folder IS Scripts, main.lua is right here, and
    # what we actually want is its parent.
    if selected_folder.name == "Scripts" and (selected_folder / "main.lua").is_file():
        return selected_folder.parent

    return None


def check_mod_folder(selected_folder: Optional[Path]) -> tuple[CheckResult, Optional[Path]]:
    """
    Returns the check result AND the corrected folder to actually use (or
    None if nothing usable was found). Callers that persist the mod
    folder setting should save the corrected path back, so this doesn't
    have to run the correction every single time.
    """
    if not selected_folder or not str(selected_folder).strip():
        return CheckResult(
            CheckStatus.MISSING,
            "No mod folder is set yet. Go to the Folders tab and point it "
            "at your Palversation install.",
        ), None

    resolved = find_mod_lua_folder(selected_folder)
    if resolved is None:
        return CheckResult(
            CheckStatus.MISSING,
            f"main.lua wasn't found in {selected_folder} or its Scripts "
            "subfolder. Make sure this points at the Palversation mod folder.",
        ), None

    if resolved != selected_folder:
        return CheckResult(
            CheckStatus.OK,
            f"Auto-corrected: you had pointed at the Scripts folder, now "
            f"using {resolved} instead.",
        ), resolved

    return CheckResult(CheckStatus.OK, "Mod folder looks correct."), resolved


def run_full_check(selected_mod_folder: Optional[Path]) -> list[tuple[str, CheckResult]]:
    """
    Runs every static check in order and returns labeled results, ready to
    show in a summary dialog. Doesn't touch the provider or the watcher --
    that's a separate, heavier check (see the end-to-end conversation
    test).
    """
    results: list[tuple[str, CheckResult]] = []

    mod_result, corrected_folder = check_mod_folder(selected_mod_folder)
    results.append(("Mod folder", mod_result))

    if corrected_folder is not None:
        results.append(("Mod location", check_mod_location(corrected_folder)))
    else:
        results.append((
            "Mod location",
            CheckResult(CheckStatus.UNKNOWN, "Skipped, fix the mod folder first."),
        ))

    return results