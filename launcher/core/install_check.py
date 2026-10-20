"""
Automatic setup + diagnostics for the Palversation install. Finds the
game, checks UE4SS, installs/updates the bundled Lua mod and checks the
AI provider -- everything the player used to do by hand. Run at startup,
from the Setup tab, and before launching the game with Play.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from core.game_locator import find_palworld_dir, find_ue4ss, UE4SSInstall
from core.mod_installer import (
    install_or_update_mod, installed_mod_dir, read_mod_version, get_bundled_mod_dir, is_workshop_managed,
    MIN_COMPATIBLE_MOD_VERSION, _version_tuple,
)

UE4SS_DOWNLOAD_URL = "https://github.com/Okaetsu/RE-UE4SS/releases/tag/experimental-palworld"


class CheckStatus(Enum):
    OK = "ok"
    MISSING = "missing"
    UNKNOWN = "unknown"  # couldn't verify either way, not necessarily a problem


@dataclass
class CheckResult:
    status: CheckStatus
    message: str


@dataclass
class SetupReport:
    palworld_dir: Optional[Path] = None
    ue4ss: Optional[UE4SSInstall] = None
    mod_changed: bool = False
    checks: List[Tuple[str, CheckResult]] = field(default_factory=list)

    @property
    def game_ready(self) -> bool:
        """Palworld found, UE4SS present, mod installed."""
        return all(result.status == CheckStatus.OK for label, result in self.checks if label != "AI provider")

    def first_problem(self) -> Optional[Tuple[str, CheckResult]]:
        for label, result in self.checks:
            if result.status != CheckStatus.OK:
                return label, result
        return None


def _provider_check(config: dict) -> CheckResult:
    from providers.registry import get_provider_spec
    provider_id = config.get("provider", "player2")
    try:
        spec = get_provider_spec(provider_id)
    except ValueError:
        return CheckResult(CheckStatus.MISSING, f"Unknown provider '{provider_id}'. Pick one in the General tab.")
    key = config.get("api_keys", {}).get(provider_id, "")
    if spec.requires_api_key and (not key or key == "PUT_YOUR_API_KEY_HERE"):
        action = "enter your API key" if spec.key_is_pasted else "press Connect Account"
        return CheckResult(CheckStatus.MISSING, f"Not connected yet. Go to the General tab and {action}.")
    return CheckResult(CheckStatus.OK, f"{spec.display_name} is set up.")


def run_setup(config: dict, install: bool = True) -> SetupReport:
    """install=False only reports, without writing anything to the game folder."""
    report = SetupReport()

    report.palworld_dir = find_palworld_dir(config.get("palworld_dir", ""))
    if report.palworld_dir is None:
        report.checks.append(("Palworld", CheckResult(
            CheckStatus.MISSING,
            "Couldn't find Palworld automatically. Use \"Choose Palworld folder...\" "
            "and select the folder that contains Palworld.exe.",
        )))
    else:
        report.checks.append(("Palworld", CheckResult(CheckStatus.OK, f"Found at {report.palworld_dir}")))

    if report.palworld_dir is not None:
        report.ue4ss = find_ue4ss(report.palworld_dir)
    if report.ue4ss is None:
        status = CheckStatus.MISSING if report.palworld_dir else CheckStatus.UNKNOWN
        message = (
            "UE4SS (Palworld experimental build) isn't installed. It's what lets "
            "Palworld load Lua mods -- use \"Get UE4SS\", install it, then press Re-check."
            if report.palworld_dir else "Skipped until Palworld is found."
        )
        report.checks.append(("UE4SS", CheckResult(status, message)))
    else:
        report.checks.append(("UE4SS", CheckResult(CheckStatus.OK, f"Found at {report.ue4ss.root}")))

    if report.ue4ss is None:
        report.checks.append(("Palversation mod", CheckResult(CheckStatus.UNKNOWN, "Installed automatically once UE4SS is found.")))
    elif install:
        result = install_or_update_mod(report.ue4ss.mods_dir)
        report.mod_changed = result.changed
        report.checks.append(("Palversation mod", CheckResult(
            CheckStatus.OK if result.ok else CheckStatus.MISSING, result.message,
        )))
    else:
        installed = read_mod_version(installed_mod_dir(report.ue4ss.mods_dir))
        bundled_dir = get_bundled_mod_dir()
        bundled = read_mod_version(bundled_dir) if bundled_dir else None
        workshop_ok = is_workshop_managed(report.ue4ss.mods_dir) and _version_tuple(installed) >= _version_tuple(MIN_COMPATIBLE_MOD_VERSION)
        if installed and (installed == bundled or workshop_ok):
            report.checks.append(("Palversation mod", CheckResult(CheckStatus.OK, f"v{installed} installed.")))
        else:
            report.checks.append(("Palversation mod", CheckResult(CheckStatus.MISSING, "Not installed or outdated.")))

    report.checks.append(("AI provider", _provider_check(config)))
    return report
