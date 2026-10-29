#!/usr/bin/env python3
"""Source-pinned five-hunter TeamLobby and native C++ test stage, CI ONLY.

Reuses source-reviewed patch_five_hunter_team.py from Seamless Hunt PR #17.
The ordinary YT1.3 source and game client cannot be claimed five-player
compatible until the unmodified C++/join and live 5-person gameplay pass.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
from patch_five_hunter_team import FILES, patch

PINNED = {
    "server/coop/team_lobby.h": "b97f3b650fbbd0b737accac9992a0bc1da7bd2b8",
    "server/coop/team_lobby.cpp": "7978d8d8062d8c18f1db79b02551c65fba2eb261",
    "server/tests/test_team_lobby.cpp": "c045e637ada5e548b003d34033c912fde54f1d34",
}

def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    if not root.is_dir() or set(PINNED) != set(FILES):
        raise ValueError("Incomplete five-hunter source registry")
    paths = {name: root / name for name in FILES}
    originals = {}
    for name, path in paths.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or linked native five-hunter source")
        raw = path.read_bytes()
        if blob_sha(raw) != PINNED[name]:
            raise ValueError("Unpinned original five-hunter source: " + name)
        originals[name] = raw.decode("utf-8")
    # Validate ALL anchors before writing ANY source to this disposable clone.
    changed = patch(originals)
    if set(changed) != set(FILES):
        raise ValueError("Incomplete native five-hunter source patch")
    for name in FILES:
        paths[name].write_text(changed[name], encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_five_hunter_server.py DISPOSABLE_YT_SOURCE")
    stage(Path(sys.argv[1]))
    print("SHYT_FIVE_HUNTER_QT_CPLUSPLUS_STAGE_ONLY_NO_PRODUCTION")
