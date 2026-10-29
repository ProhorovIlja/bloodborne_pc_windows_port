#!/usr/bin/env python3
"""V117: isolated 200-PLAYER, FIVE-PER-TEAM original Qt hosted sharding A/B.

Runs original YT1.3 server/loadtest/run_shards.py (real Redis, directory, shadNet,
bbload), not a synthetic mock server. One vs THREE actual Qt server processes
on localhost. Diagnostic only by default; any health claim is strict.
This cannot prove real WAN or P2P performance.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from run_capacity_curve import BUILD

SIZE = 5
POPULATION = 200
SHARD_COUNTS = (1, 3)
RUN_SECONDS = 30
RAMP_MS = 35
TIMEOUT = 120

def grade(item: dict, expected_shards: int) -> dict:
    if type(item) is not dict:
        return {"quality": "INVALID_ORIGINAL_REPORT"}
    if (item.get("players") != POPULATION or item.get("shards") != expected_shards):
        return {"quality": "WRONG_PLAYERS_OR_SHARDS"}
    rows = item.get("per_shard")
    if (not isinstance(rows, list) or len(rows) != expected_shards or
            any(not isinstance(row, dict) or type(row.get("shard")) is not str
                for row in rows)):
        return {"quality": "INVALID_PER_SHARD_EVIDENCE"}
    if {r["shard"] for r in rows} != {f"lt-{i}" for i in range(expected_shards)}:
        return {"quality": "INVALID_PER_SHARD_EVIDENCE"}
    for row in rows:
        cpu = row.get("link_thread_cpu_avg")
        if type(cpu) not in (float, int) or not math.isfinite(cpu) or cpu < 0:
            return {"quality": "INVALID_PER_SHARD_CPU"}
    for key in ("playing", "game_receivers", "complete_teams",
                "packets_sent", "packets_received",
                "packets_lost", "refused", "udp_buffer_drops"):
        value = item.get(key)
        if type(value) is not int or value < 0:
            return {"quality": "MISSING_REAL_GAME_COUNTERS", "field": key}
    for key in ("relay_ms_p99", "redirects", "redirect_ms_p99"):
        val = item.get(key)
        if type(val) not in (int, float) or not math.isfinite(val) or val < 0:
            return {"quality": "INVALID_TIMING_OR_REDIRECT", "field": key}
    playing, receivers = item["playing"], item["game_receivers"]
    sent, received = item["packets_sent"], item["packets_received"]
    if playing != POPULATION:
        quality = "NOT_ALL_PLAYING"
    elif receivers != POPULATION:
        quality = "GAME_RECEIVERS_MISSING"
    elif item["complete_teams"] != POPULATION // SIZE:
        quality = "FIVE_HUNTER_TEAMS_INCOMPLETE"
    elif item["refused"] or sent < POPULATION * 10:
        quality = "INSUFFICIENT_ACCEPTED_GAME_TRAFFIC"
    elif received > sent or received * 100 < sent * 99 or item["packets_lost"]:
        quality = "REAL_GAME_DELIVERY_DEGRADED"
    elif item["udp_buffer_drops"]:
        quality = "HOST_KERNEL_UDP_DROPS"
    elif item["relay_ms_p99"] > 50:
        quality = "RELAY_P99_OVER_50MS"
    elif max(row["link_thread_cpu_avg"] for row in rows) >= 75:
        quality = "SHARD_CPU_SATURATED"
    elif (expected_shards > 1 and
          (item["redirects"] < 1 or item["redirect_ms_p99"] > 2000)):
        quality = "CROSS_SHARD_REDIRECT_FAILED"
    else:
        quality = "FULL_GAMEPLAY_SYNTHETIC_ONLY"
    return {
        "quality": quality, "players": POPULATION, "shards": expected_shards,
        "playing": playing, "game_receivers": receivers,
        "complete_teams": item["complete_teams"], "packets_sent": sent,
        "packets_received": received, "packets_lost": item["packets_lost"],
        "relay_ms_p99": item["relay_ms_p99"],
        "redirects": item["redirects"], "redirect_ms_p99": item["redirect_ms_p99"],
        "udp_buffer_drops_host_wide": item["udp_buffer_drops"],
        "per_shard": [{
            "shard": r["shard"], "players_at_end": r.get("players_at_end"),
            "link_thread_cpu_avg": r["link_thread_cpu_avg"]
        } for r in rows],
    }

def command(args, shards: int, base_port: int) -> list[str]:
    if shards not in SHARD_COUNTS:
        raise ValueError("Must run one vs three independent original Qt shards")
    return [
        sys.executable, str(args.shard_script),
        "--shadnet", str(args.shadnet), "--bbload", str(args.bbload),
        "--players", str(POPULATION), "--team-size", str(SIZE),
        "--shards", str(shards), "--capacity", str(240 if shards == 1 else 80),
        "--seconds", str(RUN_SECONDS), "--ramp-ms", str(RAMP_MS),
        "--processes", "4", "--cross", "mixed", "--port", str(base_port),
        "--cfg", "CheckServerBuild=false",
        "--extra", f"--build '{BUILD}' --owner-fps 30 --follower-fps 8",
    ]

def execute(cmd: list[str], timeout_s: int) -> tuple[int, str]:
    if not 60 <= timeout_s <= TIMEOUT:
        raise ValueError("Unsafe shard test timeout")
    with tempfile.TemporaryDirectory(prefix="yt130-v117-5p-") as home:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True,
                                   start_new_session=True, env={**os.environ, "TMPDIR": home})
        try:
            stdout, _ = process.communicate(timeout=timeout_s)
            return process.returncode, stdout
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            return 124, ""

def run(args) -> int:
    for path in (args.shadnet, args.bbload, args.shard_script):
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing or linked real original server/generator source")
    if (args.shard_script.name != "run_shards.py" or
            not os.access(args.shadnet, os.X_OK) or
            not os.access(args.bbload, os.X_OK)):
        raise ValueError("Original source and real compiled Qt binaries are required")
    if not 60 <= args.timeout <= TIMEOUT:
        raise ValueError("Timeout outside finite guarded process-group cleanup")
    results = []
    for index, shards in enumerate(SHARD_COUNTS):
        rc, out = execute(command(args, shards, 39014 + index * 60), args.timeout)
        if rc == 124:
            result = {"quality": "ORIGINAL_SHARDS_TIMEOUT", "shards": shards}
        elif rc:
            result = {"quality": "ORIGINAL_SHARD_PROCESS_FAILED", "shards": shards,
                      "exit_code": rc}
        else:
            values = []
            for line in out.splitlines():
                if line.startswith("{"):
                    try:
                        values.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            result = (grade(values[0], shards) if len(values) == 1 else
                      {"quality": "MISSING_OR_DUPLICATE_GENERATOR_REPORT", "shards": shards})
        result["scope"] = "DISPOSABLE_LOOPBACK_REDIRECT_NOT_REAL_WAN_OR_DIRECT_P2P"
        result["team_size"] = SIZE
        results.append(result)
        print("YT130_V117_REAL_5P_SHARDS", shards, result["quality"],
              "PLAYING", result.get("playing", "?"), "GAME_RECEIVERS",
              result.get("game_receivers", "?"), "COMPLETE_FIVE_TEAMS",
              result.get("complete_teams", "?"), flush=True)
        if rc == 124:
            break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, sort_keys=True) + "\n")
    if len(results) == 2 and all(
            r["quality"] == "FULL_GAMEPLAY_SYNTHETIC_ONLY" for r in results):
        print("YT130_V117_BOTH_200_PLAYER_SHARD_RUNS_SYNTHETIC_HEALTH_PASS")
        return 0
    print("YT130_V117_DIAGNOSTIC_NOT_200_PLAYER_PRODUCTION_CAPACITY")
    return int(args.require_healthy)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for label in ("shadnet", "bbload", "shard-script", "output"):
        p.add_argument("--" + label, type=Path, required=True)
    p.add_argument("--timeout", type=int, default=TIMEOUT)
    p.add_argument("--require-healthy", action="store_true")
    raise SystemExit(run(p.parse_args()))
