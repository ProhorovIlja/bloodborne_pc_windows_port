#!/usr/bin/env python3
"""Offline, read-only Bloodborne 1.09 launcher patch conflict audit.

Reads user-supplied shadPS4/bbport XML. Never edits a game or saves; never
publishes payload bytes. Overlap means address-space overlap, not a verified
match to a particular decrypted executable. Do not auto-enable from XML flags.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import tempfile
from xml.etree import ElementTree as ET

MAX_XML_BYTES = 16 * 1024 * 1024

@dataclass(frozen=True)
class Write:
    source: str
    name: str
    address: int
    value: bytes

def load(path: Path, *, title_id: str, version: str, include_disabled: bool) -> tuple[list[Write], dict]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_XML_BYTES:
        raise ValueError("unsafe or missing patch XML file")
    source = path.read_bytes()
    if b"<!DOCTYPE" in source.upper() or b"<!ENTITY" in source.upper():
        raise ValueError("XML declarations/entities not allowed")
    root = ET.fromstring(source)
    if root.tag != "Patch":
        raise ValueError("expected Patch document")
    ids = [node.text for node in root.findall("./TitleID/ID")]
    if title_id not in ids:
        raise ValueError("patch XML does not list requested game TitleID")
    out: list[Write] = []
    selected = 0
    versions = set()
    entries = root.findall("Metadata")
    for mod in entries:
        name = mod.get("Name")
        if not name:
            raise ValueError("patch without Name")
        versions.add(mod.get("AppVer"))
        if mod.get("AppVer") != version:
            raise ValueError("patch XML contains a mismatched game version")
        if mod.get("AppElf") != "eboot.bin":
            raise ValueError("patch targets an unexpected original executable")
        if not include_disabled and mod.get("isEnabled") != "true":
            continue
        selected += 1
        for node in mod.findall("./PatchList/Line"):
            address = int(node.attrib["Address"], 16)
            kind = node.attrib["Type"]
            raw = node.attrib["Value"]
            if kind == "bytes":
                value = bytes.fromhex(raw.removeprefix("0x"))
            elif kind == "bytes32":
                if not 0 <= int(raw, 16) < 2**32:
                    raise ValueError("invalid bytes32 value")
                value = int(raw, 16).to_bytes(4, "little")
            elif kind == "bytes16":
                if not 0 <= int(raw, 16) < 2**16:
                    raise ValueError("invalid bytes16 value")
                value = int(raw, 16).to_bytes(2, "little")
            else:
                raise ValueError("unsupported patch operation: " + kind)
            if address < 0 or not value or address + len(value) > 2**64:
                raise ValueError("invalid patch address/length")
            out.append(Write(path.name, name, address, value))
    return out, {"source": path.name, "patches_total": len(entries),
                 "patches_selected": selected, "write_operations": len(out),
                 "versions": sorted(str(x) for x in versions)}

def audit(writes: list[Write]) -> dict:
    # Each byte has at most one owner here; if a third patch differs from an
    # earlier one, warn about both rather than silently choosing load order.
    owners: dict[int, list[tuple[str, str, int]]] = defaultdict(list)
    conflict_bytes: dict[tuple[str, str], set[int]] = defaultdict(set)
    shared_bytes: dict[tuple[str, str], set[int]] = defaultdict(set)
    for w in writes:
        key = (w.source, w.name)
        for offset, byte in enumerate(w.value):
            addr = w.address + offset
            for previous_source, previous_name, previous_byte in owners[addr]:
                previous = (previous_source, previous_name)
                if previous == key:
                    if previous_byte != byte:
                        raise ValueError("one patch contains contradictory writes to itself")
                    continue
                pair = tuple(sorted((previous_source + " :: " + previous_name,
                                     w.source + " :: " + w.name)))
                (conflict_bytes if previous_byte != byte else shared_bytes)[pair].add(addr)
            owners[addr].append((w.source, w.name, byte))
    return {
        "status": "BLOCKED" if conflict_bytes else "NO_BYTE_CONFLICTS_DETECTED",
        "writes": len(writes),
        "different_value_overlaps": [
            {"patches": list(pair), "byte_count": len(positions),
             "addresses": [f"0x{p:08X}" for p in sorted(positions)[:16]]}
            for pair, positions in sorted(conflict_bytes.items())
        ],
        "identical_value_overlaps": [
            {"patches": list(pair), "byte_count": len(positions)}
            for pair, positions in sorted(shared_bytes.items())
        ],
        "limitations": (
            "Exact patch offsets are NOT checked against original 1.09 ELF or "
            "other installed game script mods. No changes applied; no automatic "
            "selection. Different binary patches may have indirect conflicts."
        ),
    }

def selftest() -> None:
    template = '<Patch><TitleID><ID>CUSA03173</ID></TitleID>' + (
        '<Metadata Name="A" AppVer="01.09" AppElf="eboot.bin" isEnabled="true">'
        '<PatchList><Line Type="bytes" Address="0x10" Value="010203"/></PatchList></Metadata>'
        '<Metadata Name="B" AppVer="01.09" AppElf="eboot.bin" isEnabled="true">'
        '<PatchList><Line Type="bytes32" Address="0x11" Value="0x00000402"/></PatchList></Metadata>'
        '<Metadata Name="C" AppVer="01.09" AppElf="eboot.bin" isEnabled="false">'
        '<PatchList><Line Type="bytes" Address="0x11" Value="FF"/></PatchList></Metadata>'
    ) + '</Patch>'
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "example.xml"
        path.write_text(template)
        writes, summary = load(path, title_id="CUSA03173", version="01.09",
                               include_disabled=False)
        assert summary["patches_selected"] == 2
        result = audit(writes)
        assert result["status"] == "BLOCKED"
        assert result["different_value_overlaps"][0]["addresses"] == ["0x00000012"]
        assert result["identical_value_overlaps"][0]["byte_count"] == 1
        all_writes, _ = load(path, title_id="CUSA03173", version="01.09",
                             include_disabled=True)
        assert len(all_writes) == 3
        try:
            load(path, title_id="CUSA99999", version="01.09", include_disabled=False)
        except ValueError:
            pass
        else:
            raise AssertionError("wrong game identifier allowed")
    print("SHYT_PATCH_XML_OFFLINE_COLLISION_SELFTEST_PASS")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("xml", nargs="*", type=Path)
    parser.add_argument("--title-id", default="CUSA03173")
    parser.add_argument("--version", default="01.09")
    parser.add_argument("--include-disabled", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        selftest()
        return
    if not args.xml:
        parser.error("supply one or more private local XML patch files")
    writes: list[Write] = []
    source_meta = []
    try:
        for path in args.xml:
            one, meta = load(path, title_id=args.title_id,
                             version=args.version,
                             include_disabled=args.include_disabled)
            writes.extend(one)
            source_meta.append(meta)
        result = {"title_id": args.title_id, "version": args.version,
                  "selected_sources": source_meta, **audit(writes)}
    except (OSError, ValueError, ET.ParseError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.strict and result["status"] == "BLOCKED":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
