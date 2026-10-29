#!/usr/bin/env python3
"""V117: use REAL original hosted Redis/Qt shard generator with five hunters.

Only disposable original YT1.3 checkout; never change production directory.
Source-pinned run_shards.py, real modified bbload generator counts every client
which received a decoded game frame. Stop if the official generator drifts.
"""
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = "server/loadtest/run_shards.py"
BLOB = "9a8e6a1dd866f9ef996ed544e3b781953e154230"
MARKER = "SHYT-V117-TRUE-FIVE-HUNTER-SHARD-GAME-RECEIVERS"
IMPORT_OLD = "import shutil\nimport socket"
IMPORT_NEW = "import shutil\nimport shlex\nimport socket"
SPLIT_OLD = "args.extra.split(),"
SPLIT_NEW = "shlex.split(args.extra),"
COUNTERS_OLD = """            "packets_lost": sum(r["packets_lost"] for r in results),
            "packets_received": sum(r["packets_received"] for r in results),"""
COUNTERS_NEW = """            # SHYT-V117-TRUE-FIVE-HUNTER-SHARD-GAME-RECEIVERS:
            # Every REAL original bbload child must return this metric.
            # No client may be called PLAYING/healthy without game receipt.
            "game_receivers": sum(r["game_receivers"] for r in results),
            "packets_sent": sum(r["packets_sent"] for r in results),
            "packets_lost": sum(r["packets_lost"] for r in results),
            "packets_received": sum(r["packets_received"] for r in results),"""

def replace_one(source: str, original: str, updated: str, label: str) -> str:
    count = source.count(original)
    if count != 1:
        raise ValueError(f"V117 original shard generator drift {label}: {count}")
    return source.replace(original, updated, 1)

def patch_source(source: str) -> str:
    if MARKER in source:
        raise ValueError("V117 cannot stage twice")
    source = replace_one(source, IMPORT_OLD, IMPORT_NEW, "shlex import")
    source = replace_one(source, SPLIT_OLD, SPLIT_NEW, "quoted original fingerprint")
    return replace_one(source, COUNTERS_OLD, COUNTERS_NEW, "original per-child game counters")

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    path = root / PATH
    if (git(root, "rev-parse", "HEAD") != PIN or
            git(root, "rev-parse", "HEAD:" + PATH) != BLOB or
            not path.is_file() or path.is_symlink() or
            git(root, "diff", "--", PATH)):
        raise ValueError("V117 requires pristine original 1.3 shard generator")
    candidate = patch_source(path.read_text(encoding="utf-8"))
    path.write_text(candidate, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V117_ORIGINAL_SHARDS_GAME_RECIPIENTS_PATCHED_NOT_A_LOAD_PASS")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_shard_generator_v117.py DISPOSABLE_13_CLONE")
    stage(Path(sys.argv[1]))
