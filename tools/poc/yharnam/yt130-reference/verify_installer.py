#!/usr/bin/env python3
"""Verify the exact official Yharnam Together 1.3.0 installer offline.

Run after obtaining the setup directly from upstream GitHub Release.
This script NEVER executes or modifies the installer, user saves or accounts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MANIFEST = Path(__file__).with_name("release.json")


def check(path: Path, expected_bytes: int, expected_hash: str) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Expected a regular, non-symlink installer file")
    if path.stat().st_size != expected_bytes:
        raise ValueError("Official v1.3.0 installer size mismatch")
    dig = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            dig.update(chunk)
    actual = dig.hexdigest()
    if actual != expected_hash:
        raise ValueError("Official v1.3.0 installer SHA-256 mismatch")
    return actual


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("installer", nargs="?", type=Path)
    args = p.parse_args()
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.installer is None:
        print(json.dumps(m, indent=2, ensure_ascii=False))
        return
    verified_hash = check(args.installer, m["installer_bytes"], m["installer_sha256"])
    print("SHYT_OFFICIAL_YT130_INSTALLER_BYTES_AND_SHA256_MATCH", verified_hash)


if __name__ == "__main__":
    main()
