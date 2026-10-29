#!/usr/bin/env python3
"""Source-verified, isolated FIVE-hunter synthetic load generator extension.

Only changes bbload's help text and hardcoded CLI clamp 4 -> 5.
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


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\x00" + raw
    ).hexdigest()


def rewrite(text: str) -> str:
    for old in (OLD_HELP, OLD_CLAMP):
        if text.count(old) != 1:
            raise ValueError("Pinned five-player bbload source anchor drift")
    return text.replace(OLD_HELP, NEW_HELP, 1).replace(
        OLD_CLAMP, NEW_CLAMP, 1
    )


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
