#!/usr/bin/env python3
"""Fail-closed check of native Windows Seamless Hunt CI candidates.

Source-check and packaging check only, NOT proof of co-op protocol,
real gameplay or a safe public release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

ROOT = "bbport-windows/"
REQUIRED = {
    "BLauncher.exe", "Bloodborne.exe", "bin/bb-probe.exe",
    "bin/bb-gpu-capabilities.exe", "run.py", "README.md", "LICENSE",
}
FATAL_EXACT = {
    "eboot.bin", "shadnet.db", "shadnet.cfg", "coop.json",
    "id_rsa", "id_ed25519", ".env",
}
FATAL_DIRS = {"dvdroot_ps4", "sce_module", "sce_sys", "user", "game", "secrets"}
FATAL_EXTS = {".pkg", ".sav", ".pem", ".pfx", ".p12", ".key"}
MAX_ENTRIES = 18000
MAX_UNCOMPRESSED = 3 * 1024**3
MAX_FILE = 1024**3
MAX_COMPRESSED = 2 * 1024**3


class UnsafeBundle(ValueError):
    pass


def check(archive: Path, *, sha_path: Path | None = None) -> dict:
    if not archive.is_file() or archive.stat().st_size > MAX_COMPRESSED:
        raise UnsafeBundle("missing or oversized Windows candidate archive")
    h = hashlib.sha256()
    with archive.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if sha_path is not None:
        lines = sha_path.read_text(encoding="ascii").splitlines()
        expected = digest + "  " + archive.name
        if lines != [expected]:
            raise UnsafeBundle("archive SHA-256 checksum mismatch")
    found: set[str] = set()
    total = 0
    with zipfile.ZipFile(archive, "r") as z:
        infos = z.infolist()
        if not infos or len(infos) > MAX_ENTRIES:
            raise UnsafeBundle("invalid candidate ZIP item count")
        for info in infos:
            # On Windows zipfile normalizes backslashes in .filename.
            # .orig_filename preserves the untrusted ZIP entry spelling.
            raw = info.orig_filename
            if not raw or "\\" in raw or "\x00" in raw or raw.startswith("/") or ":" in raw:
                raise UnsafeBundle("invalid or ambiguous ZIP filename")
            name = raw.rstrip("/")
            parts = name.split("/")
            if any(p in {"", ".", ".."} for p in parts) or parts[0] != ROOT[:-1]:
                raise UnsafeBundle("ZIP member escapes expected package root")
            if any(part.lower() in FATAL_DIRS for part in parts[1:-1]):
                raise UnsafeBundle("retail/private data directory found in package")
            leaf = parts[-1].lower()
            if leaf in FATAL_EXACT or any(leaf.endswith(ext) for ext in FATAL_EXTS):
                raise UnsafeBundle("retail/private file found in package")
            if name in found:
                raise UnsafeBundle("duplicate ZIP member")
            found.add(name)
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
                raise UnsafeBundle("ZIP symlinks are not supported")
            if info.file_size > MAX_FILE:
                raise UnsafeBundle("oversized ZIP member")
            total += info.file_size
            if total > MAX_UNCOMPRESSED:
                raise UnsafeBundle("archive too large when unpacked")
        missing = sorted(ROOT + req for req in REQUIRED if ROOT + req not in found)
        if missing:
            raise UnsafeBundle("missing required native runtime or launcher: " + ", ".join(missing))
        for binary in ("BLauncher.exe", "Bloodborne.exe", "bin/bb-probe.exe"):
            if z.getinfo(ROOT + binary).file_size < 1024:
                raise UnsafeBundle("empty or placeholder executable")
        damaged = z.testzip()
        if damaged is not None:
            raise UnsafeBundle("corrupt ZIP member")
    return {"sha256": digest, "entries": len(found),
            "uncompressed_bytes": total, "release_ready": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", type=Path)
    args = parser.parse_args()
    try:
        result = check(args.archive, sha_path=args.sha256)
    except (UnsafeBundle, OSError, zipfile.BadZipFile, UnicodeError) as e:
        parser.exit(2, "WINDOWS_CANDIDATE_REJECTED: " + str(e) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("WINDOWS_CANDIDATE_STRUCTURE_PASS (not game or co-op tested)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
