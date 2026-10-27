#!/usr/bin/env python3
"""Bounded offline native YT1.3.0 scaling measurement, NOT a release.

Run original source-pinned run_load.py and actual compiled shadnet/bbload.
Profiles test 250/500/1000 (256/512/1024 for four-player teams),
optionally 2000/2048. No external IP, credentials or production writes.
The 30/8 fps default is original upstream bbload active-owner/follower rate.
Results are diagnostic, not P2P or real two-PC gameplay evidence.
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
import time

from run_capacity_curve import BUILD, quality

MATRIX = {2: (250, 500, 1000, 2000), 4: (256, 512, 1024, 2048)}
FPS = {"active": (30, 8), "reduced": (10, 3), "presence": (1, 1)}
MAX_TIMEOUT = 160


def stages(team_size: int, peak: int) -> tuple[int, ...]:
    allowed = MATRIX[team_size]
    if peak not in allowed:
        raise ValueError("Unreviewed scale or wrong team-size")
    return allowed[:allowed.index(peak) + 1]


def processes(players: int) -> int:
    """Bound generator processes, not server threads."""
    return min(24, max(2, math.ceil(players / 100)))


def make_command(args, players: int, index: int) -> list[str]:
    owner, follower = FPS[args.profile]
    return [
        sys.executable, str(args.load_script),
        "--shadnet", str(args.shadnet),
        "--bbload", str(args.bbload),
        "--players", str(players),
        "--team-size", str(args.team_size),
        "--processes", str(processes(players)),
        "--seconds", "22",
        "--ramp-ms", "20",
        "--port", str(36314 + index * 10),
        "--cfg", "CheckServerBuild=false",
        "--extra", f"--build '{BUILD}' --owner-fps {owner} --follower-fps {follower}",
    ]


def measure(cmd: list[str], timeout: int) -> tuple[int, str, str]:
    """Kill whole local process group on timeout; don't strand server/bbload."""
    if not 20 <= timeout <= MAX_TIMEOUT:
        raise ValueError("Unsafe time limit")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
        return int(proc.returncode), out, err
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return 124, "", "LOCAL_GENERATOR_TIMEOUT_PROCESS_GROUP_KILLED"


def inspect(stdout: str, rc: int, expected: int) -> dict:
    rows = []
    for line in stdout.splitlines():
        if not line.lstrip().startswith("{"):
            continue
        try:
            x = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(x) is dict and "players" in x:
            rows.append(x)
    if rc == 124:
        return {"quality": "TIMEOUT", "observed": False}
    if rc != 0 or len(rows) != 1:
        return {"quality": "GENERATOR_FAILED", "observed": False}
    m = rows[0]
    if m.get("players") != expected:
        return {"quality": "GENERATOR_MISMATCH", "observed": False}
    return {
        "quality": quality(m, expected),
        "observed": True,
        "metrics": {name: m.get(name) for name in (
            "players", "playing", "refused", "packets_sent",
            "packets_received", "delivered_pct", "relay_ms_p50",
            "relay_ms_p99", "ping_ms_p99",
            "main_thread_cpu_avg", "main_thread_cpu_max",
            "server_cpu_avg", "server_cpu_max",
            "server_in_mbit", "server_out_mbit", "server_rss_mb_max",
            "server_threads", "udp_buffer_drops")},
    }


def run(args) -> int:
    if args.team_size not in MATRIX or args.profile not in FPS:
        raise ValueError("Unsupported team shape or FPS profile")
    if args.timeout < 20 or args.timeout > MAX_TIMEOUT:
        raise ValueError("Unsafe timeout")
    if any(not p.is_file() or p.is_symlink() for p in
           (args.shadnet, args.bbload, args.load_script)):
        raise ValueError("Missing or linked original compiled server / generator")
    if args.load_script.name != "run_load.py":
        raise ValueError("Only original source-pinned upstream generator accepted")
    selected = stages(args.team_size, args.peak)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    all_green = True
    with args.output.open("w", encoding="utf-8") as out:
        for i, players in enumerate(selected):
            cmd = make_command(args, players, i)
            started = time.monotonic()
            rc, stdout, _ = measure(cmd, args.timeout)
            report = inspect(stdout, rc, players)
            row = {
                "stage_players": players,
                "team_size": args.team_size,
                "profile": args.profile,
                "owner_fps": FPS[args.profile][0],
                "follower_fps": FPS[args.profile][1],
                "generator_processes": processes(players),
                "elapsed_s": round(time.monotonic() - started, 2),
                "scope": "ISOLATED_127.0.0.1_SYNTHETIC_YT130_ONLY",
                "proof": "LOOPBACK_GAMEPLAY_NOT_REAL_WORLD_1000_PLAYER_SLA",
                **report,
            }
            out.write(json.dumps(row, sort_keys=True) + "\n")
            out.flush()
            print("YT130_SCALE_PLAYERS", players, "PROFILE", args.profile,
                  "QUALITY", row["quality"], "PLAYING",
                  row.get("metrics", {}).get("playing", "unknown"), flush=True)
            if row["quality"] != "FULL_GAMEPLAY":
                all_green = False
            if rc == 124:
                # A hung 500-user test must not immediately launch 1000 more.
                print("YT130_SCALE_SAFETY_STOP_AFTER_TIMEOUT", flush=True)
                break
    print("YT130_1000_PLUS_DIAGNOSTIC_ONLY_NO_DEPLOY_NO_CAPACITY_CLAIM")
    return 1 if args.require_healthy and not all_green else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--shadnet", type=Path, required=True)
    p.add_argument("--bbload", type=Path, required=True)
    p.add_argument("--load-script", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--team-size", type=int, choices=(2, 4), default=2)
    p.add_argument("--profile", choices=tuple(FPS), default="active")
    p.add_argument("--peak", type=int,
                   choices=(250, 256, 500, 512, 1000, 1024, 2000, 2048), default=1000)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--require-healthy", action="store_true")
    raise SystemExit(run(p.parse_args()))
