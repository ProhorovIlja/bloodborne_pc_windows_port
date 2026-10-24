# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only Bloodborne carried-weapon inventory and optional in-game item names.

The inventory structure and IDs were cross-checked against GPL-2.0-or-later
Supermedo/bloodborne_pc launcher/bbport_character.py, which credits Noxde's
Bloodborne Save Editor research. Never alter savedata or redistribute game text.

IMPORTANT: inventory membership != equipped right/left slots. This deliberately
does NOT present owned weapons as equipped, and names are optional because
not every game dump has the same translated message archives.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import struct
import zlib

INVENTORY_OFFSET = 468
INVENTORY_ENTRIES = 1984
ENTRY_SIZE = 16
TRICK_WEAPONS = (
    2000000, 4000000, 5000000, 5100000, 7000000, 7100000, 8000000,
    8100000, 9000000, 10000000, 10100000, 11000000, 12000000, 13000000,
    22000000, 23000000, 24000000, 25000000, 26000000, 27000000,
    28000000, 29000000, 30000000, 31000000, 32000000, 34000000, 38000000,
)
LEFT_HAND_WEAPONS = (
    6000000, 6100000, 14000000, 14100000, 14200000, 15000000,
    18000000, 18100000, 19000000, 19100000, 20000000, 20100000,
    33000000, 35000000, 36000000,
)
WEAPON_KINDS = TRICK_WEAPONS + LEFT_HAND_WEAPONS
WEAPON_KIND_ORDER = {value: index for index, value in enumerate(WEAPON_KINDS)}
VALID_VARIANTS = (0, 1, 2, 8)
VARIANT_NAMES = {0: "", 1: "Uncanny", 2: "Lost", 8: "Variant"}
MSG_FOLDERS = {
    "0": "jpnjp", "1": "engus", "2": "frafr", "3": "spaes",
    "4": "deude", "5": "itait", "8": "rusru", "17": "porbr",
}
MAX_MSG_FILE_BYTES = 24 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 64 * 1024 * 1024
MAX_TEXT_LENGTH = 180
MAX_FMG_GROUPS = 2048
MAX_FMG_WORDS = 120000


def owned_weapon_ids(data: bytes, name_at: int) -> tuple[int, ...]:
    """Best upgrade per weapon/variant, sorted right-hand then left-hand.

    Rejects incomplete inventories; skips armor/items and invalid IDs.
    Does not determine whether the weapon is actually equipped.
    """
    start = name_at + INVENTORY_OFFSET
    end = start + INVENTORY_ENTRIES * ENTRY_SIZE
    if start < 0 or end > len(data):
        return ()
    best: dict[int, int] = {}
    for at in range(start, end, ENTRY_SIZE):
        if (data[at + 7], data[at + 11]) == (0xB0, 0x40) or data[at + 11] == 0x10:
            continue
        ident = struct.unpack_from("<I", data, at + 8)[0]
        kind = (ident // 100000) * 100000
        variant = (ident % 100000) // 10000
        level = (ident % 10000) // 100
        if (kind not in WEAPON_KIND_ORDER or variant not in VALID_VARIANTS
                or level > 10 or ident % 100 != 0):
            continue
        key = kind + variant * 10000
        if key not in best or level > ((best[key] % 10000) // 100):
            best[key] = ident
    return tuple(sorted(best.values(), key=lambda i: (
        WEAPON_KIND_ORDER[(i // 100000) * 100000], i % 100000 // 10000)))


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError("Binary archive offset outside file")
    return struct.unpack_from("<I", data, offset)[0]


def _u64(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 8 > len(data):
        raise ValueError("Binary archive offset outside file")
    return struct.unpack_from("<Q", data, offset)[0]


def decompress_game_text(blob: bytes) -> bytes:
    """Bounded DFLT-DCX decoder, output max 64 MiB; no unbounded zlib.decompress."""
    if len(blob) < 0x4D or blob[:4] != b"DCX\0" or blob[0x28:0x2C] != b"DFLT":
        raise ValueError("Unsupported DCX format")
    dec = zlib.decompressobj()
    out = dec.decompress(blob[0x4C:], MAX_DECOMPRESSED_BYTES + 1)
    if len(out) > MAX_DECOMPRESSED_BYTES or not dec.eof:
        raise ValueError("DCX exceeds bounds or is truncated")
    return out


def item_archive_member(data: bytes, file_id: int = 11) -> bytes:
    """One BND4 member; validate all offsets before slicing."""
    if len(data) < 0x40 or data[:4] != b"BND4" or _u64(data, 0x20) != 0x24:
        raise ValueError("Unsupported BND4 format")
    count = _u32(data, 0x0C)
    if count > 512 or 0x40 + count * 0x24 > len(data):
        raise ValueError("BND4 index out of bounds")
    for index in range(count):
        at = 0x40 + index * 0x24
        size = _u64(data, at + 8)
        start = _u32(data, at + 0x18)
        mid = _u32(data, at + 0x1C)
        if start > len(data) or size > len(data) - start:
            raise ValueError("BND4 member outside archive")
        if mid == file_id:
            return data[start:start + size]
    raise ValueError("No weapon names in message archive")


def fmg_weapon_names(data: bytes) -> dict[int, str]:
    """Parse bounded v2 FMG string tables (game-provided localized names)."""
    if len(data) < 0x28:
        raise ValueError("FMG too small")
    groups, offsets = _u32(data, 0x0C), _u64(data, 0x18)
    if groups > MAX_FMG_GROUPS or 0x28 + groups * 16 > len(data):
        raise ValueError("FMG group table out of bounds")
    if offsets > len(data):
        raise ValueError("FMG offsets out of bounds")
    names: dict[int, str] = {}
    total = 0
    for g in range(groups):
        at = 0x28 + 16 * g
        index, first, last = struct.unpack_from("<iii", data, at)
        if index < 0 or first < 0 or last < first:
            raise ValueError("Invalid FMG group")
        count = last - first + 1
        total += count
        if total > MAX_FMG_WORDS or (index + count) * 8 > len(data) - offsets:
            raise ValueError("FMG string index out of bounds")
        for j in range(count):
            pos = struct.unpack_from("<q", data, offsets + 8 * (index + j))[0]
            if pos <= 0:
                continue
            if pos + 2 > len(data):
                raise ValueError("FMG string offset out of bounds")
            max_end = min(len(data), pos + MAX_TEXT_LENGTH * 2 + 2)
            end = pos
            while end + 2 <= max_end and data[end:end + 2] != b"\0\0":
                end += 2
            if end + 2 > max_end or data[end:end + 2] != b"\0\0":
                continue  # Unknown/malformed string; never hang.
            name = data[pos:end].decode("utf-16-le", errors="strict").strip()
            if name and all(ord(ch) >= 32 or ch == "\t" for ch in name):
                names[first + j] = name
    return names


@lru_cache(maxsize=4)
def game_weapon_names(game_dir: str, language: str = "1") -> dict[int, str]:
    """Look up weapon labels from user's *own* game dump; never downloads it."""
    base = Path(game_dir) / "dvdroot_ps4" / "msg"
    localized = MSG_FOLDERS.get(str(language), "engus")
    for code in dict.fromkeys((localized, "engus")):
        archive = base / code / "item.msgbnd.dcx"
        try:
            if archive.is_symlink() or not archive.is_file():
                continue
            if not 0 < archive.stat().st_size <= MAX_MSG_FILE_BYTES:
                continue
            data = decompress_game_text(archive.read_bytes())
            names = fmg_weapon_names(item_archive_member(data))
            if names:
                return names
        except (OSError, ValueError, UnicodeError, struct.error, zlib.error):
            continue
    return {}


def weapon_description(ident: int, names: dict[int, str] | None = None) -> str:
    """Names only when supported by the user's game files. Never say 'equipped'."""
    kind = ident // 100000 * 100000
    if kind not in WEAPON_KIND_ORDER:
        return "Unknown weapon"
    variant = ident % 100000 // 10000
    level = ident % 10000 // 100
    title = None
    if names:
        title = names.get(ident) or names.get(ident - ident % 10000)
    if not title:
        title = f"Weapon ID {kind}"
    # Actual translation may already contain variant/upgrade wording for exact ID.
    if names and ident in names:
        description = title
    else:
        prefix = (VARIANT_NAMES.get(variant) or "")
        description = f"{prefix} {title}".strip()
        if level:
            description += f" +{level}"
    hand = "Right-hand" if kind in TRICK_WEAPONS else "Left-hand"
    return f"{description} · {hand}"
