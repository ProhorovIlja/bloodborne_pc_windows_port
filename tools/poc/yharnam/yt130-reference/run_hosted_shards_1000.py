#!/usr/bin/env python3
"""Measure REAL original YT1.3 Hosted/Redis shards, never a production deployment.

Official server/loadtest/run_shards.py runs actual shadNet, Redis, directory and
bbload on LOCALHOST. Each stage records its own result, no raw private data.
1 vs 3 processes are independently tested with identical original 30/8 fps
owner/follower game packets. 2000+ is an explicitly opt-in test profile.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
TEAM_SIZES = {2: (250, 500, 1000, 2000), 4: (256, 512, 1024, 2048)}
FPS = {"active": (30, 8), "reduced": (10, 3)}
SHARD_COUNTS = (1, 3)
MAX_SECONDS = 60
MAX_TIMEOUT = 240


def stages(team_size: int, peak: int) -> tuple[int, ...]:
    allowed = TEAM_SIZES.get(team_size, ())
    if peak not in allowed:
        raise ValueError("Stage not approved for exact team size")
    return allowed[:allowed.index(peak) + 1]


def build_command(args, shards: int, players: int, index: int) -> list[str]:
    if shards not in SHARD_COUNTS:
        raise ValueError("Unapproved shard count")
    if players % args.team_size:
        raise ValueError("Every simulated player must be in a team")
    fps_owner, fps_follower = FPS[args.profile]
    return [
        sys.executable, str(args.load_script),
        "--shadnet", str(args.shadnet),
        "--bbload", str(args.bbload),
        "--players", str(players),
        "--team-size", str(args.team_size),
        "--shards", str(shards),
        "--capacity", "800",
        "--cross", "mixed",
        "--seconds", str(args.seconds),
        "--ramp-ms", str(args.ramp_ms),
        "--processes", str(min(20, max(2, (players + 149) // 150))),
        "--port", str(38314 + index * 20),
        "--extra", (f"--owner-fps {fps_owner} "
                    f"--follower-fps {fps_follower}"),
    ]


def execute(command: list[str], timeout_s: int) -> tuple[int, str]:
    """Kill all original local Redis/shard/generator descendants on timeout."""
    if not 20 <= timeout_s <= MAX_TIMEOUT:
        raise ValueError("Unsafe timeout")
    with tempfile.TemporaryDirectory(prefix="yt-hosted-shard-qa-") as root:
        env = dict(os.environ)
        env["TMPDIR"] = root
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True, env=env)
        try:
            out, _ = proc.communicate(timeout=timeout_s)
            return int(proc.returncode), out
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            return 124, ""


def report(stdout: str, code: int, expected: int, shard_count: int) -> dict:
    if code == 124:
        return {"quality": "TIMEOUT", "measured": False}
    if code:
        return {"quality": "ORIGINAL_GENERATOR_FAILED", "measured": False}
    values = []
    for line in stdout.splitlines():
        if not line.startswith("{"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(item) is dict and "players" in item:
            values.append(item)
    if len(values) != 1:
        return {"quality": "MISSING_OR_DUPLICATE_JSON", "measured": False}
    item = values[0]
    if item.get("players") != expected or item.get("shards") != shard_count:
        return {"quality": "WRONG_POPULATION_OR_SHARDS", "measured": False}
    got_shards = item.get("per_shard", [])
    if (not isinstance(got_shards, list) or len(got_shards) != shard_count or
        any(type(shard) is not dict for shard in got_shards) or
        len({shard.get("shard") for shard in got_shards}) != shard_count):
        return {"quality": "NO_PER_SHARD_EVIDENCE", "measured": False}
    got = item.get("packets_received", 0)
    lost = item.get("packets_lost", 0)
    playing = item.get("playing", 0)
    p99 = item.get("relay_ms_p99", 1e9)
    if not all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in
               (got, lost, playing, p99)):
        return {"quality": "INVALID_COUNTERS", "measured": False}
    redirect_count = item.get("redirects")
    redirect_p99 = item.get("redirect_ms_p99")
    if shard_count > 1 and (type(redirect_count) not in (int, float) or
                            not math.isfinite(redirect_count) or redirect_count < 0 or
                            type(redirect_p99) not in (int, float) or
                            not math.isfinite(redirect_p99) or redirect_p99 < 0):
        return {"quality": "INVALID_CROSS_SHARD_COUNTERS", "measured": False}
    if any(type(shard.get("link_thread_cpu_avg")) not in (int, float) or
           not math.isfinite(shard["link_thread_cpu_avg"]) or
           shard["link_thread_cpu_avg"] < 0 for shard in got_shards):
        return {"quality": "INVALID_PER_SHARD_CPU", "measured": False}
    quality = "FULL_GAMEPLAY"
    if playing != expected:
        quality = "PARTIAL_PLAYING"
    elif got < expected * 10:
        quality = "INSUFFICIENT_GAME_FRAMES"
    elif got / max(1, got + lost) < 0.99:
        quality = "GAME_PACKET_LOSS"
    elif p99 > 50:
        quality = "RELAY_P99_OVER_50MS"
    elif any(shard["link_thread_cpu_avg"] >= 75 for shard in got_shards):
        quality = "SHARD_MAIN_CPU_SATURATED"
    elif shard_count > 1 and redirect_count == 0:
        # Without a genuine redirect, a 3-shard test could have stayed local.
        quality = "CROSS_SHARD_NOT_EXERCISED"
    elif shard_count > 1 and redirect_p99 > 2000:
        quality = "CROSS_SHARD_JOIN_TOO_SLOW"
    return {
        "quality": quality, "measured": True,
        "players": item["players"], "playing": playing,
        "refused": item.get("refused"), "redirects": item.get("redirects"),
        "redirect_ms_p99": redirect_p99,
        "relay_ms_p99": p99, "packets_received": got,
        "packets_lost": lost, "udp_buffer_drops_host_wide": item.get("udp_buffer_drops"),
        "cpu_load_host_wide": item.get("load_avg"), "cores_host": item.get("cores"),
        "per_shard": [{
            key: shard.get(key) for key in (
                "shard", "players_at_end", "link_thread_cpu_avg",
                "link_thread_cpu_max", "process_cpu_avg", "rss_mb_max")
        } for shard in got_shards],
    }


def run(args) -> int:
    if args.profile not in FPS or args.team_size not in TEAM_SIZES:
        raise ValueError("Unsupported FPS profile or team size")
    if not 1 <= args.ramp_ms <= 1000 or not 10 <= args.seconds <= MAX_SECONDS:
        raise ValueError("Outside approved ramp or runtime")
    if not 20 <= args.timeout <= MAX_TIMEOUT:
        raise ValueError("Invalid timeout")
    if any(not p.is_file() or p.is_symlink()
           for p in (args.shadnet, args.bbload, args.load_script)):
        raise ValueError("Missing binary or symlink path is not allowed")
    if args.load_script.name != "run_shards.py":
        raise ValueError("Only pinned official original shard generator may run")
    for p in (args.shadnet, args.bbload):
        if not os.access(p, os.X_OK):
            raise ValueError("Expected compiled real shadNet and bbload")
    selected = stages(args.team_size, args.peak)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    idx = 0
    good = True
    with args.output.open("w", encoding="utf-8") as output:
        for players in selected:
            for shards in SHARD_COUNTS:
                command = build_command(args, shards, players, idx)
                idx += 1
                start = time.monotonic()
                code, stdout = execute(command, args.timeout)
                result = report(stdout, code, players, shards)
                row = {
                    "scale": players, "shards": shards,
                    "team_size": args.team_size,
                    "fps_profile": args.profile, "seconds": args.seconds,
                    "ramp_ms": args.ramp_ms,
                    "elapsed_s": round(time.monotonic() - start, 2),
                    "testing_scope": "ISOLATED_HOSTED_LOOPBACK_NOT_REAL_USERS",
                    "limit": "NO_REAL_TWO_PC_WAN_NAT_P2P_OR_PRODUCTION_CAPACITY_PROOF",
                    **result,
                }
                output.write(json.dumps(row, sort_keys=True) + "\n")
                output.flush()
                print("YT130_HOSTED_SHARDS", players, "SHARDS", shards, "QUALITY",
                      result["quality"], "PLAYING", result.get("playing", "?"),
                      flush=True)
                good &= result["quality"] == "FULL_GAMEPLAY"
                if code == 124:
                    # A stopped shard can cause orphan load: never ramp further.
                    print("YT130_HOSTED_TIMEOUT_ABORT_LOCAL_STRESS", flush=True)
                    return 1 if args.require_healthy else 0
    print("YT130_HOSTED_SCALE_COMPLETE_DIAGNOSTIC_ONLY_NO_LIVE_DEPLOY")
    return int(args.require_healthy and not good)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadnet", type=Path, required=True)
    parser.add_argument("--bbload", type=Path, required=True)
    parser.add_argument("--load-script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--team-size", type=int, choices=(2, 4), default=2)
    parser.add_argument("--profile", choices=tuple(FPS), default="active")
    parser.add_argument("--peak", type=int, default=1000)
    parser.add_argument("--seconds", type=int, default=24)
    parser.add_argument("--ramp-ms", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=130)
    parser.add_argument("--require-healthy", action="store_true")
    raise SystemExit(run(parser.parse_args()))
