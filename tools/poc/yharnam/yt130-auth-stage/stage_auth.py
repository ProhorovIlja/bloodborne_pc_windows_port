#!/usr/bin/env python3
"""Safely stage pinned YT1.3 auth overrides into a disposable test checkout."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
SOURCE_BLOBS = {
    "server/src/database.h": "01f729832f96291d7b8e93401a27a07d4741efc4",
    "server/src/database.cpp": "9e9d52eadb69810a5c5bcf8389deae07cc831381",
    "server/src/link_server.h": "4530df9be35e161cd4e4fd56fe1f1696bb8b407b",
    "server/src/link_server.cpp": "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8",
    "server/tests/test_accounts.cpp": "f22ab39b1e1c973573ca1ccf8e6dee06b0283d06"
}

def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def main(override_root: Path, clean_checkout: Path) -> None:
    override_root, clean_checkout = override_root.resolve(), clean_checkout.resolve()
    if clean_checkout == override_root or clean_checkout in override_root.parents or override_root in clean_checkout.parents:
        raise ValueError("Override files and checkout must be separate locations")
    head = subprocess.check_output(["git", "-C", str(clean_checkout), "rev-parse", "HEAD"],
                                   text=True, timeout=20).strip()
    if head != PIN:
        raise ValueError("Not the pinned original Yharnam Together checkout")
    status = subprocess.check_output(["git", "-C", str(clean_checkout), "status", "--porcelain"],
                                     text=True, timeout=20)
    if status.strip():
        raise ValueError("Refusing to modify non-clean checkout")
    prepared = []
    for rel, expected in SOURCE_BLOBS.items():
        source = clean_checkout / rel
        override = override_root / rel
        if (not source.is_file() or source.is_symlink() or
            not override.is_file() or override.is_symlink() or
            blob(source.read_bytes()) != expected):
            raise ValueError("Pinned source mismatch or unsafe override: " + rel)
        candidate = override.read_bytes()
        if b"SHYT-AUTH-2026" not in candidate or not candidate:
            raise ValueError("Unverified staged fix file: " + rel)
        prepared.append((source, candidate))
    for source, candidate in prepared:
        source.write_bytes(candidate)
    print("SHYT_YT130_AUTH_OVERRIDES_STAGED_FOR_ISOLATED_QT_BUILD_ONLY")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: stage_auth.py OVERRIDES_ROOT DISPOSABLE_PINNED_CHECKOUT")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
