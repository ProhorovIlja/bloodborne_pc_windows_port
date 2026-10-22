"""A pinned Hunter is UI metadata, *never* the game's selected save.

Only a bounded folder and userdata0000..0009 name are saved in the launcher's
local settings. Reopen the slot read-only to refresh the visible preview. A
stale, moved, encrypted or damaged save has no remembered stat fallback.
"""
from pathlib import Path

try:
    from . import hunter_profiles
except ImportError:
    import hunter_profiles

MAX_FOLDER_LENGTH = 2048


def validate_pin(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    folder, slot, source = value.get("folder"), value.get("slot"), value.get("source")
    if (not isinstance(folder, str) or not folder or len(folder) > MAX_FOLDER_LENGTH
            or "\0" in folder or not isinstance(slot, str)
            or not hunter_profiles.SLOT.fullmatch(slot)
            or not isinstance(source, str) or len(source) > 80):
        return None
    return {"folder": folder, "slot": slot, "source": source}


def pin_from_hunter(hunter: hunter_profiles.Hunter) -> dict:
    pin = validate_pin({"folder": hunter.folder, "slot": hunter.slot,
                        "source": hunter.source})
    if pin is None:
        raise ValueError("Invalid Hunter slot or source")
    return pin


def preview(pin) -> hunter_profiles.Hunter | None:
    checked = validate_pin(pin)
    if checked is None:
        return None
    folder = Path(checked["folder"])
    try:
        if folder.is_symlink() or not folder.is_dir():
            return None
        return hunter_profiles.read_slot(
            folder / checked["slot"], source=checked["source"])
    except (OSError, ValueError):
        return None


def label(hunter: hunter_profiles.Hunter | None) -> str:
    if hunter is None:
        return "Preview unavailable · open Hunters / Saves to choose again"
    return (f"{hunter.name} · level {hunter.level} · {hunter.build_guess} "
            "· pinned preview ONLY, not the active game slot")
