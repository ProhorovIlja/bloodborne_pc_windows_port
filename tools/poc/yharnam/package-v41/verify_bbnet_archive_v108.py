#!/usr/bin/env python3
"""V108: prove genuine V97/V98/V99 game translation units are inside bbnet.

Called only after the original Windows Clang64 Ninja bbnet target succeeds.
Also rehash all seven patched source files to detect post-staging changes.
No retail game assets, account data, or gameplay networking is accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

PIN = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"
REQUIRED_UNITS = (
    "bloodborne_re.cpp",
    "bloodborne_party.cpp",
    "bloodborne_party_death.cpp",
    "bloodborne_flags_store.cpp",
)


def verify_manifest(manifest: Path, checkout: Path) -> None:
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("V108 source digest manifest missing or symlinked")
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or (
        doc.get("pinned_upstream") != PIN
        or doc.get("development_only") is not True
        or doc.get("native_gameplay_direct_udp_enabled") is not False
        or doc.get("native_game_translation_units_verified") is not True
    ):
        raise ValueError("V108 unexpected game source or unsafe manifest settings")
    hashes = doc.get("source_sha256")
    if not isinstance(hashes, dict) or len(hashes) != 7:
        raise ValueError("V108 expected exactly seven patched source hashes")
    for unit in REQUIRED_UNITS:
        if f"emulator/src/core/{unit}" not in hashes:
            raise ValueError("V108 missing patched translation unit digest: " + unit)
    for relative, expected in hashes.items():
        if (not isinstance(relative, str)
            or not re.fullmatch(r"emulator/src/core/[A-Za-z0-9_]+\.(?:cpp|h)", relative)
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)):
            raise ValueError("V108 malformed or unsafe source digest")
        source = checkout / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError("V108 patched source missing or symlinked: " + relative)
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("V108 patched source changed after V101 stage: " + relative)


def verify_archive(archive: Path, archiver: str = "llvm-ar") -> None:
    if not archive.is_file() or archive.is_symlink() or archive.stat().st_size == 0:
        raise ValueError("V108 real native bbnet archive missing or empty")
    listing = subprocess.check_output(
        [archiver, "t", str(archive)], text=True, timeout=60
    )
    members = [entry.replace("\\\\", "/").rsplit("/", 1)[-1].lower()
               for entry in listing.splitlines() if entry.strip()]
    for unit in REQUIRED_UNITS:
        expected = {unit.lower() + ".obj", unit.lower() + ".o"}
        count = sum(member in expected for member in members)
        if count != 1:
            raise ValueError(
                f"V108 game C++ object {unit} expected once, got {count}"
            )
    print("SHYT_V108_ACTUAL_PATCHED_NATIVE_GAME_OBJECTS_IN_BBNET_PASS")


def verify(archive: Path, manifest: Path, checkout: Path) -> None:
    verify_manifest(manifest, checkout)
    verify_archive(archive)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("checkout", type=Path)
    args = ap.parse_args()
    verify(args.archive, args.manifest, args.checkout)
