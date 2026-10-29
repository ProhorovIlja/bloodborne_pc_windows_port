#!/usr/bin/env python3
"""Source-verified, isolated FIVE-hunter synthetic load generator extension.

Extends original pinned bbload CLI to five, and ports upstream PR #444 multi-owner synthetic traffic.
Does not add server capacity, enable gameplay, or modify live binaries.
Original upstream 1.3 bbload would silently clamp requests for five to four.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

SOURCE = Path("server/loadtest/bbload.cpp")
PINNED_BLOB = "edfb6ea39b898cca2638d65826981cf9fc81c334"
OLD_HELP = '"team-size", "players a team (2-4)"'
NEW_HELP = '"team-size", "players a team (2-5)"'
OLD_CLAMP = 'std::clamp(parser.value("team-size").toInt(), 2, 4)'
NEW_CLAMP = 'std::clamp(parser.value("team-size").toInt(), 2, 5)'

# Source-reviewed port of original upstream PR #444 (lKaniel/bloodborne-server).
# The original generator models ONE enemy owner per team; since 1.3 a
# separated four-/five-hunter group may have several actual enemy owners.
# This affects load evidence ONLY, never game or server routing.
OWNER_EDITS = (
    ('  int follower_fps = 8; // a follower\\'s\\n',
     '  int follower_fps = 8; // a follower\\'s\\n'
     '  int owners = 1; // up to team_size seats own enemies; upstream #444\\n'),
    ('  bool Leader() const { return seat == 0; }\\n',
     '  bool Leader() const { return seat == 0; }\\n'
     '  bool Owner() const;\\n'),
    ('bool Game::Elsewhere() const {',
     'bool Game::Owner() const { return seat < load.settings.owners; }\\n\\n'
     'bool Game::Elsewhere() const {'),
    ('Leader() ? load.settings.owner_fps : load.settings.follower_fps',
     'Owner() ? load.settings.owner_fps : load.settings.follower_fps'),
    ('    if (Leader()) {\\n'
     '      // The enemy owner (rig 2026-10-15):',
     '    if (Owner()) {\\n'
     '      // The enemy owner (rig 2026-10-15):'),
    ('      {"follower-fps", "a follower\\'s frames a second per teammate", "n", "8"},',
     '      {"follower-fps", "a follower\\'s frames a second per teammate", "n", "8"},\\n'
     '      {"owners", "enemy-owner seats per team (1-team size)", "n", "1"},'),
    ('  settings.follower_fps = std::max(1, parser.value("follower-fps").toInt());',
     '  settings.follower_fps = std::max(1, parser.value("follower-fps").toInt());\\n'
     '  settings.owners = std::clamp(parser.value("owners").toInt(), 1, settings.team_size);'),
)


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\x00" + raw
    ).hexdigest()


def rewrite(text: str) -> str:
    for old in (OLD_HELP, OLD_CLAMP):
        if text.count(old) != 1:
            raise ValueError("Pinned five-player bbload source anchor drift")
    text = text.replace(OLD_HELP, NEW_HELP, 1).replace(
        OLD_CLAMP, NEW_CLAMP, 1
    )
    for old, new in OWNER_EDITS:
        if text.count(old) != 1:
            raise ValueError("Pinned upstream multi-owner bbload anchor drift")
        text = text.replace(old, new, 1)
    return text


def transform(raw: bytes) -> bytes:
    if blob_sha(raw) != PINNED_BLOB:
        raise ValueError("Not exact official pinned upstream bbload.cpp")
    return rewrite(raw.decode("utf-8")).encode("utf-8")


def stage(root: Path) -> None:
    source = root.resolve() / SOURCE
    if not source.is_file() or source.is_symlink():
        raise ValueError("No safe regular disposable bbload source")
    source.write_bytes(transform(source.read_bytes()))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_five_player_bbload.py DISPOSABLE_UPSTREAM")
    stage(Path(sys.argv[1]))
    print("SHYT_FIVE_HUNTER_BBLOAD_DIAGNOSTIC_ONLY_NO_SERVER_CAPACITY_CLAIM")
