#!/usr/bin/env python3
"""Yharnam Together v1.3.1: verify OFFICIAL release before external install.

This standalone, read-only verifier is a source prototype, NOT integrated
with the shipped YT launcher/updater. It hashes existing official assets
offline; it never downloads, executes, unpacks, or edits the user's
game files. Hashes and sizes are from official 2026-10-31 GitHub release:
https://github.com/lKaniel/bloodborne-server/releases/tag/v1.3.1
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys

OFFICIAL={
    "YharnamTogether-v1.3.1-setup.exe": (
        127500183,
        "21f9fb0fbb1d48b96ed614dc9cfbc7bc88e55c407015db82a30da72cc317e76a"),
    "YharnamTogether-v1.3.1-portable.zip": (
        198394703,
        "f87883bdcb729325fdbcc6d8292f56304eed60c4039cd34192141c9ba4a13db1"),
}
CHUNK=1024*1024

def check(path:Path, manifest:dict|None=None)->bool:
    # The supplied manifest is for unit testing only. CLI always uses the
    # fixed official publisher's manifest above; no arbitrary override.
    expected=(OFFICIAL if manifest is None else manifest).get(path.name)
    if expected is None or path.is_symlink() or not path.is_file():
        return False
    size, digest=expected
    if path.stat().st_size!=size:
        return False
    hasher=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(CHUNK),b""):
            hasher.update(block)
    # It is possible for a file to change while hashing it.
    # Recheck size; do not accept a changed or partial download.
    return path.stat().st_size==size and hasher.hexdigest()==digest

def main()->int:
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("asset",type=Path,help="An existing official v1.3.1 setup.exe or portable.zip")
    args=p.parse_args()
    if not check(args.asset):
        print("YT_V131_RELEASE_INTEGRITY_FAILED: do not run or install",file=sys.stderr)
        return 2
    print("YT_V131_OFFICIAL_RELEASE_SHA256_AND_SIZE_PASS")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
