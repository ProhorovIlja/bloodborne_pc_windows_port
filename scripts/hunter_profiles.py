# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only, defensive Bloodborne character-slot overview for the Hunter Hub.

Save layout research credit: Supermedo/bloodborne_pc launcher/bbport_character.py
(GPL-2.0-or-later), Noxde/Bloodborne-save-editor. This is an independently
bounded parser for preview ONLY, not a save converter, editor, or equipment
selection engine.

Only a validated decrypted userdata0000..0009 slot is displayed. The equipped
weapon, last lamp and last location are NOT reliably encoded by the fields
understood here. Do not silently infer them from the inventory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import struct
from typing import Iterable

SLOT = re.compile(r"^userdata000[0-9]$")
FACE_TO_NAME = 34496
NAME_SIZE = 34
# Byte offsets relative to the UTF-16 name, based on verified community work.
OFFSETS = {"vitality": -104, "endurance": -96, "strength": -80,
           "skill": -72, "bloodtinge": -64, "arcane": -56}
LEVEL = -24
ECHOES = -20
INSIGHT = -36
JOURNEY = 68830
DEATHS = 68544 + 360
PLAYED_MS = 8
# No need to parse large files or user-supplied backups outside ten exact slots.
MAX_FILE_BYTES = 8 * 1024 * 1024
MIN_FILE_BYTES = 0xF000 + JOURNEY + 1
MAX_PROFILES = 80
STATS = tuple(OFFSETS)


@dataclass(frozen=True)
class Hunter:
    slot: str
    name: str
    level: int
    vitality: int
    endurance: int
    strength: int
    skill: int
    bloodtinge: int
    arcane: int
    echoes: int
    insight: int
    playtime_seconds: int
    deaths: int
    journey: int
    source: str
    folder: str
    # Build label is inferred. Never mistake it for an in-game class.
    build_guess: str

    def public(self):
        return asdict(self)


def source_label(source: str) -> str:
    """Player-facing source; stored source identifiers remain unchanged."""
    if not isinstance(source, str):
        return "Unknown save source"
    if source.startswith("native:party"):
        return "Native PC · co-op save"
    if source.startswith("native:"):
        return "Native PC"
    if source.startswith("shadps4:") or source.startswith("shadps4-or-"):
        return "shadPS4 / legacy save"
    if source.startswith("native-or-shadps4:"):
        return "Portable PC / shadPS4"
    if source.startswith("manual:"):
        return "Chosen save folder"
    return "Other detected save source"


def inferred_build(stats: dict[str, int]) -> str:
    """Conservative, cosmetic heuristic; not a game-file field or a respec."""
    combat = {k: stats[k] for k in ("strength", "skill", "bloodtinge", "arcane")}
    first, second = sorted(combat, key=combat.get, reverse=True)[:2]
    if combat[first] < 20 or combat[first] - combat[second] < 12:
        return "Mixed / undecided"
    return {"strength": "Strength", "skill": "Skill",
            "bloodtinge": "Bloodtinge", "arcane": "Arcane"}[first] + " focus (estimated)"


def parse_slot(data: bytes, slot: str, *, source: str = "", folder: str = "") -> Hunter | None:
    """Parse validated data in memory. Return None for unknown/corrupt/encrypted formats."""
    if (not isinstance(data, bytes) or not SLOT.fullmatch(slot)
            or not MIN_FILE_BYTES <= len(data) <= MAX_FILE_BYTES):
        return None
    # A first-found FACE string can occur in unrelated bytes. Validate candidate,
    # require exactly one valid character or refuse an ambiguous file.
    result = None
    start, count = 0xF000, 0
    while start < len(data) and count < 16:
        face = data.find(b"FACE", start)
        if face < 0:
            break
        count += 1
        start = face + 4
        name_at = face - FACE_TO_NAME
        if (name_at < 0x80 or name_at + JOURNEY >= len(data)
                or name_at + DEATHS + 4 > len(data)):
            continue
        try:
            name = data[name_at:name_at + NAME_SIZE].decode("utf-16-le", "strict").split("\0")[0].strip()
            if not 1 <= len(name) <= 16 or any(ord(c) < 32 for c in name):
                continue
            def u32(offset: int) -> int:
                return struct.unpack_from("<I", data, name_at + offset)[0]
            stats = {key: u32(offset) for key, offset in OFFSETS.items()}
            level = u32(LEVEL)
            if not all(1 <= v <= 99 for v in stats.values()):
                continue
            if level != sum(stats.values()) - 50:
                continue
            # Do not guess off-by-one NG+ semantics in UI: expose a raw cycle marker.
            journey = data[name_at + JOURNEY]
            if journey > 8:
                continue
            echoes, insight = u32(ECHOES), u32(INSIGHT)
            # Even valid saves can contain extreme counters; cap at sensible bit ranges.
            if insight > 99:
                continue
            hunter = Hunter(
                slot=slot, name=name, level=level,
                echoes=echoes, insight=insight,
                playtime_seconds=struct.unpack_from("<I", data, PLAYED_MS)[0] // 1000,
                deaths=u32(DEATHS), journey=journey, source=source,
                folder=folder, build_guess=inferred_build(stats), **stats)
        except (UnicodeError, struct.error, ValueError, TypeError):
            continue
        if result is not None:
            return None
        result = hunter
    # More than 16 FACE candidates: potential adversarial/unknown format.
    return result if count < 16 else None


def read_slot(path: Path, *, source: str = "") -> Hunter | None:
    path = Path(path)
    if not SLOT.fullmatch(path.name):
        return None
    try:
        if path.is_symlink() or not path.is_file():
            return None
        before = path.stat()
        if not MIN_FILE_BYTES <= before.st_size <= MAX_FILE_BYTES:
            return None
        with path.open("rb") as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        after = path.stat()
        if len(data) != before.st_size or (before.st_size, before.st_mtime_ns) != (
                after.st_size, after.st_mtime_ns):
            return None  # Was saved during our read; retry on next open.
        return parse_slot(data, path.name, source=source, folder=str(path.parent))
    except (OSError, ValueError):
        return None


def read_group(folder: Path, *, source: str = "") -> list[Hunter]:
    folder = Path(folder)
    try:
        if not folder.is_dir() or folder.is_symlink():
            return []
        return [h for i in range(10)
                if (h := read_slot(folder / f"userdata{i:04d}", source=source)) is not None]
    except OSError:
        return []


def from_discovery(saves: Iterable[dict]) -> list[Hunter]:
    """Consume already bounded install_discovery.find_saves metadata. No scan of whole disk."""
    hunters, seen = [], set()
    for entry in saves:
        if len(hunters) >= MAX_PROFILES:
            break
        if not isinstance(entry, dict):
            continue
        folder = entry.get("folder")
        source = entry.get("source", "unknown")
        if not isinstance(folder, str) or not folder or not isinstance(source, str):
            continue
        try:
            key = str(Path(folder).resolve()).casefold()
            if key in seen:
                continue
            seen.add(key)
            hunters.extend(read_group(Path(folder), source=source[:80]))
        except (OSError, ValueError):
            continue
    return hunters[:MAX_PROFILES]
