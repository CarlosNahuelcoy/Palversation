"""
Static reference data about each Pal species (real display name, flavor
description, genus category, elements, size, etc.), compiled by the user
from a public data source -- not pulled live from the game via UE4SS, so
none of the native-call/use-after-free risks apply here. Keyed by the raw
CharacterID, the same internal species ID the Lua mod already sends us
(as the first part of the stable pal_key, "CharacterID#InstanceGuid").
"""

import json
from pathlib import Path
from typing import Dict, Optional

from core.paths import get_bundled_dir


def resolve_pal_data_path(configured_path: Path) -> Path:
    """Prefers a real pal_data.json sitting next to the exe/launcher --
    lets anyone override or update the curated species data without
    rebuilding -- falling back to the copy bundled inside the exe itself
    (via build_exe.bat's --add-data) if present, so the app ships with
    real species names and lore out of the box, with nothing extra to
    download or set up the first time someone runs it."""
    if configured_path.exists():
        return configured_path
    bundled_dir = get_bundled_dir()
    if bundled_dir:
        bundled_path = bundled_dir / configured_path.name
        if bundled_path.exists():
            return bundled_path
    return configured_path  # doesn't exist either way; load_pal_data() handles that gracefully


def load_pal_data(data_path: Path) -> Dict[str, dict]:
    if not data_path.exists():
        return {}
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def get_species_info(pal_data: Dict[str, dict], character_id: str) -> Optional[dict]:
    return pal_data.get(character_id)


def get_display_name(pal_data: Dict[str, dict], character_id: str) -> str:
    info = pal_data.get(character_id)
    if info and info.get("name"):
        return info["name"]
    return character_id


def build_species_hint(info: dict) -> str:
    """Builds a short, factual system-prompt addition from a species'
    static data. Always applied when we have data for the species,
    regardless of per-pal custom prompt or generated personality --
    this is factual grounding, not a personality choice."""
    if not info:
        return ""
    parts = []

    real_name = info.get("name")
    desc = info.get("description")
    if desc:
        clean_desc = " ".join(desc.split())  # collapse the \r\n line breaks in the source data
        parts.append(f'Official lore about your species: "{clean_desc}"')

    genus = info.get("genus_category")
    if genus:
        parts.append(f"Body type: {genus}.")

    size = info.get("size")
    if size:
        parts.append(f"Size class: {size}.")

    traits = []
    if info.get("nocturnal"):
        traits.append("nocturnal")
    if info.get("predator"):
        traits.append("a predator by nature")
    if info.get("is_boss"):
        traits.append("considered a boss-tier Pal")
    if traits:
        parts.append("You are " + " and ".join(traits) + ".")

    partner_title = info.get("partner_skill_title")
    if partner_title:
        partner_desc = info.get("partner_skill_description") or ""
        parts.append(f"Your partner skill is '{partner_title}'" + (f": {partner_desc}" if partner_desc else "") + ".")

    if not parts:
        return ""
    return " " + " ".join(parts)


def export_species_names_lookup(pal_data: Dict[str, dict], out_path: Path) -> None:
    """Writes a simple 'CharacterID=DisplayName' text file (same format
    the Lua side's config.txt uses) so the mod can show the real species
    name in the game chat too, without needing to parse JSON in Lua."""
    lines = []
    for character_id, info in pal_data.items():
        name = info.get("name") if isinstance(info, dict) else None
        if name:
            lines.append(f"{character_id}={name}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    tmp_path.replace(out_path)
