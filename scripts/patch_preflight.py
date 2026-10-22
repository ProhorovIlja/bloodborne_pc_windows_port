"""Offline Bloodborne 1.09 XML patch collision preflight.

Detects different bytes targeting the same eboot address across selected
patches. This is an advisory check, not a patcher or proof of game stability.
Does NOT write/execute any patch, touch saves or transmit user files.

Usage:
  python scripts/patch_preflight.py patches/Bloodborne.xml --defaults
  python scripts/patch_preflight.py mods/MyPatches.xml --enable "Foo" --enable "Bar"
  python scripts/patch_preflight.py Bloodborne.xml DollRebirth.xml --defaults --json

Only compare the same address space: shadPS4 cheat JSON memory offsets are NOT
assumed equivalent to PS4 eboot file XML addresses.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

MAX_XML_BYTES = 16 * 1024 * 1024
MAX_PATCH_LINES = 60_000
MAX_WRITE_BYTES = 4096
SUPPORTED = frozenset(("bytes", "bytes16", "bytes32", "float32", "utf16"))


@dataclass(frozen=True)
class PatchWrite:
    name: str
    source: str
    address: int
    data: bytes


def decode_patch(typ: str, value: str) -> bytes:
    typ = str(typ or "").lower()
    if typ == "bytes":
        text = value.strip().removeprefix("0x").removeprefix("0X")
        if not text or not all(ch in "0123456789abcdefABCDEF" for ch in text):
            raise ValueError("invalid byte string")
        if len(text) % 2:
            text = "0" + text
        data = bytes.fromhex(text)
    elif typ in ("bytes16", "bytes32"):
        length = 2 if typ == "bytes16" else 4
        data = int(value, 0).to_bytes(length, byteorder="little", signed=False)
    elif typ == "float32":
        data = struct.pack("<f", float(value))
    elif typ == "utf16":
        data = str(value).encode("utf-16le")
    else:
        raise ValueError("unsupported patch write type")
    if not data or len(data) > MAX_WRITE_BYTES:
        raise ValueError("patch write size outside supported range")
    return data


def xml_writes(path: Path, enabled_names: set[str] | None = None,
               defaults: bool = False) -> tuple[list[PatchWrite], list[str]]:
    """Return selected bytes and warnings. Files are read, NEVER modified.

    If enabled_names is None, --defaults selects isEnabled=true.
    Otherwise only explicit names are selected; file defaults are ignored.
    """
    path = Path(path)
    if path.stat().st_size > MAX_XML_BYTES:
        raise ValueError("XML patch file is too large")
    root = ET.parse(path).getroot()
    if root.tag != "Patch":
        raise ValueError("expected a Bloodborne patch XML document")
    writes = []
    warnings = []
    total_lines = 0
    for meta in root.findall("Metadata"):
        name = (meta.get("Name") or "").strip()
        if not name:
            warnings.append("unnamed patch skipped")
            continue
        selected = (name in enabled_names) if enabled_names is not None else (
            defaults and meta.get("isEnabled", "").lower() == "true")
        if not selected:
            continue
        appver = (meta.get("AppVer") or "").strip()
        if appver and appver != "01.09":
            warnings.append(f"{name}: game version {appver} is not 01.09")
            continue
        for line in meta.findall("./PatchList/Line"):
            total_lines += 1
            if total_lines > MAX_PATCH_LINES:
                raise ValueError("too many patch lines")
            typ = line.get("Type")
            try:
                if typ not in SUPPORTED:
                    warnings.append(f"{name}: skipped unsupported type {typ!r}")
                    continue
                address = int(line.get("Address", ""), 0)
                if address < 0 or address > (1 << 63):
                    raise ValueError("invalid address")
                data = decode_patch(typ, line.get("Value", ""))
            except (TypeError, ValueError, OverflowError, struct.error) as exc:
                warnings.append(f"{name}: malformed {typ} patch line ({type(exc).__name__})")
                continue
            writes.append(PatchWrite(name, path.name, address, data))
    return writes, warnings


def find_conflicts(writes: list[PatchWrite]) -> list[dict]:
    """Report value-changing overlaps between DIFFERENT named patch sets.

    Uses a per-byte write map and merges consecutive conflicting addresses
    for a stable, human-readable report.
    """
    slots: dict[int, dict[str, int]] = defaultdict(dict)
    for write in writes:
        for index, value in enumerate(write.data):
            slots[write.address + index][f"{write.source}::{write.name}"] = value

    clashes: dict[tuple[str, str], list[int]] = defaultdict(list)
    for addr, participants in sorted(slots.items()):
        if len(participants) < 2 or len(set(participants.values())) == 1:
            continue
        distinct = sorted(participants)
        for i, a in enumerate(distinct):
            for b in distinct[i + 1:]:
                if participants[a] != participants[b]:
                    clashes[(a, b)].append(addr)
    summary = []
    for (left, right), addrs in sorted(clashes.items()):
        ranges = []
        start = last = addrs[0]
        for a in addrs[1:]:
            if a == last + 1:
                last = a
            else:
                ranges.append([f"0x{start:X}", f"0x{last:X}"])
                start = last = a
        ranges.append([f"0x{start:X}", f"0x{last:X}"])
        summary.append({"left": left, "right": right,
                        "different_bytes": len(addrs), "ranges": ranges})
    return summary


def audit(paths: list[Path], *, enabled_names: set[str] | None = None,
          defaults: bool = False) -> dict:
    all_writes = []
    warnings = []
    sources = []
    for path in paths:
        writes, messages = xml_writes(path, enabled_names=enabled_names, defaults=defaults)
        all_writes.extend(writes)
        warnings.extend(messages)
        sources.append(Path(path).name)
    conflicts = find_conflicts(all_writes)
    return {"sources": sources, "selected_write_lines": len(all_writes),
            "patch_sets": sorted({w.name for w in all_writes}),
            "conflicts": conflicts, "warnings": warnings,
            "safe_to_apply": not conflicts and not warnings}


def format_report(report: dict) -> str:
    lines = [
        f"Selected patch sets: {len(report['patch_sets'])}; "
        f"write lines: {report['selected_write_lines']}",
        f"Conflicting pairs: {len(report['conflicts'])}",
    ]
    for conflict in report["conflicts"]:
        ranges = ", ".join((a if a == b else f"{a}..{b}")
                           for a, b in conflict["ranges"][:8])
        lines.append(f"  {conflict['left']} vs {conflict['right']}: "
                     f"{conflict['different_bytes']} conflicting bytes at {ranges}")
    for warning in report["warnings"][:20]:
        lines.append(f"WARNING: {warning}")
    if not report["conflicts"] and not report["warnings"]:
        lines.append("No conflicting bytes found among selected writes. "
                     "This does NOT validate online gameplay, FPS or memory safety.")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("xml", nargs="+", type=Path)
    choice = ap.add_mutually_exclusive_group(required=True)
    choice.add_argument("--defaults", action="store_true",
                        help="scan XML patches marked isEnabled=true")
    choice.add_argument("--enable", action="append", metavar="PATCH_NAME",
                        help="scan exactly named patch sets (repeat for multiple)")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    args = ap.parse_args(argv)
    try:
        result = audit(args.xml, enabled_names=set(args.enable) if args.enable else None,
                       defaults=args.defaults)
    except (OSError, ET.ParseError, ValueError) as exc:
        ap.error(str(exc))
    print(json.dumps(result, indent=2) if args.json else format_report(result))
    return 2 if result["conflicts"] or result["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
