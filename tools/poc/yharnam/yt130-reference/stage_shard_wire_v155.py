#!/usr/bin/env python3
"""V155: preserve anonymous original Qt Data-kind wire counters in shard report.

Run AFTER V117 source-locked run_shards stage, only in disposable YT1.3 load
checkout. Original instrumented LinkServer already prints every 5 seconds:
 YT130_WIRE_TRAFFIC kind=3 in_packets=... in_bytes=... out_packets=... out_bytes=...
Original run_shards.py deletes its temporary server logs on exit. Summarize
them just before deletion. No IPs, session tokens, usernames or payloads are
recorded. Do not equate all-window counters to steady client sends/receives.
"""
from __future__ import annotations
import re
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = Path("server/loadtest/run_shards.py")
V117 = "SHYT-V117-TRUE-FIVE-HUNTER-SHARD-GAME-RECEIVERS"
MARK = "SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE"
READER_ANCHOR = """        per_shard = []
        for i in range(args.shards):
            steady = samples[i][len(samples[i]) // 3:] or samples[i]
"""
READER_PATCH = """        # SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE: only bounded
        # counters of the real LinkServer wire kind 3 (game Data) sampled
        # every 5s. No identifiers, payload, or IP addresses retained.
        wire_pattern = re.compile(
            r'YT130_WIRE_TRAFFIC kind=3 in_packets=(\\d+) in_bytes=(\\d+) '
            r'out_packets=(\\d+) out_bytes=(\\d+)(?!\\d)')
        def data_wire(shard_index):
            packets_in = packets_out = bytes_in = bytes_out = windows = 0
            path = os.path.join(root, f"shard{shard_index}", "shadnet.log")
            with open(path, encoding="utf-8", errors="replace") as source_log:
                for line in source_log:
                    match = wire_pattern.search(line)
                    if match:
                        inc, ib, out, ob = map(int, match.groups())
                        packets_in += inc
                        bytes_in += ib
                        packets_out += out
                        bytes_out += ob
                        windows += 1
            return (packets_in, packets_out, bytes_in, bytes_out, windows)

        per_shard = []
        for i in range(args.shards):
            wire_in, wire_out, wire_bytes_in, wire_bytes_out, wire_windows = data_wire(i)
            steady = samples[i][len(samples[i]) // 3:] or samples[i]
"""
ROW_ANCHOR = """                "players_at_end": row.get("players"),
                "link_thread_cpu_avg": round(sum(s["main"] for s in steady) / max(1, len(steady)), 1),"""
ROW_PATCH = """                "players_at_end": row.get("players"),
                "game_wire_in_packets": wire_in,
                "game_wire_out_packets": wire_out,
                "game_wire_in_bytes": wire_bytes_in,
                "game_wire_out_bytes": wire_bytes_out,
                "game_wire_sample_windows": wire_windows,
                "link_thread_cpu_avg": round(sum(s["main"] for s in steady) / max(1, len(steady)), 1),"""
SUMMARY_ANCHOR = """            "per_shard": per_shard,
        }))"""
SUMMARY_PATCH = """            "per_shard": per_shard,
            "game_wire_in_packets": sum(r["game_wire_in_packets"] for r in per_shard),
            "game_wire_out_packets": sum(r["game_wire_out_packets"] for r in per_shard),
            "game_wire_in_bytes": sum(r["game_wire_in_bytes"] for r in per_shard),
            "game_wire_out_bytes": sum(r["game_wire_out_bytes"] for r in per_shard),
            "game_wire_sample_windows": sum(r["game_wire_sample_windows"] for r in per_shard),
            "wire_counter_scope": "Qt LinkServer 5s sampled entire run, partial tail excluded",
        }))"""
IMPORT_ANCHOR = "import shlex\nimport socket"
IMPORT_PATCH = "import shlex\nimport re\nimport socket"

def patch_source(source: str) -> str:
    if V117 not in source:
        raise ValueError("V155 requires prior exact original V117 instrumentation")
    if MARK in source:
        raise ValueError("V155 cannot stage twice")
    for before, after, label in (
            (IMPORT_ANCHOR, IMPORT_PATCH, "regular expression import"),
            (READER_ANCHOR, READER_PATCH, "source Qt per-shard logs before cleanup"),
            (ROW_ANCHOR, ROW_PATCH, "source Qt shard CPU row"),
            (SUMMARY_ANCHOR, SUMMARY_PATCH, "source original JSON report")):
        if source.count(before) != 1 or after in source:
            raise ValueError("V155 original source drift: " + label)
        source = source.replace(before, after, 1)
    return source

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   text=True, stderr=subprocess.DEVNULL).strip()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    src = root / PATH
    if (git(root, "rev-parse", "HEAD") != PIN or
            not src.is_file() or src.is_symlink() or
            V117 not in src.read_text(encoding="utf-8")):
        raise ValueError("V155 requires pinned original YT1.3 and already staged V117")
    original = src.read_text(encoding="utf-8")
    patched = patch_source(original)
    src.write_text(patched, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("SHYT_V155_ORIGINAL_QT_DATA_WIRE_AGGREGATION_STAGED_DIAG_ONLY")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_shard_wire_v155.py DISPOSABLE_ORIGINAL_YT130_CHECKOUT")
    stage(Path(sys.argv[1]))
