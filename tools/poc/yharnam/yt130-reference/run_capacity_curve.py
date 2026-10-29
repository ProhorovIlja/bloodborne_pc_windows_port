#!/usr/bin/env python3
"""Measure optimized shadNet capacity against real upstream bbload and quit at the first non-playing stage.
Each stage uses a fresh isolated localhost shadNet, synthetic database and independent loopback port.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import signal
from pathlib import Path
import subprocess
import sys

STAGES = (4, 16, 32, 64, 100, 200)
DIAGNOSTIC_STAGES = (32, 64, 100, 200)
BUILD = "bb-build 1;version=dev;protocol=9;"

def settings(players: int) -> tuple[int, int, int]:
    if players not in STAGES:
        raise ValueError("Unreviewed synthetic client count")
    return (min(4, max(1, (players + 49)//50)), 15 if players <= 64 else 25, 100)

def quality(m: dict, players: int) -> str:
    # Upstream bbload reports aggregate counters, not per-peer delivery proofs.
    keys = ("players", "playing", "packets_sent", "packets_received", "packets_lost")
    # Qt serializes these counters as JSON numbers: whole values may be 3 or 3.0.
    # A received packet can also have more than one recipient, so do not
    # assume that aggregate receive counts never exceed send counts.
    def valid_counter(v):
        return ((type(v) is int and v >= 0) or
                (type(v) is float and v >= 0 and v != float("inf") and
                 v == v and v.is_integer()))
    if any(not valid_counter(m.get(key)) for key in keys):
        return "INVALID_METRICS"
    if m["players"] != players:
        return "GENERATOR_MISMATCH"
    if m["playing"] > players:
        return "INVALID_METRICS"
    if m["playing"] == 0 or m["packets_sent"] == 0 or m["packets_received"] == 0:
        return "NO_GAMEPLAY"
    if m["playing"] != players:
        return "PARTIAL_GAMEPLAY"
    # A handful of packets cannot substantiate an all-player gameplay claim.
    # This is a minimum evidence gate, not proof of per-client packet delivery.
    if m["packets_sent"] < players or m["packets_received"] < players:
        return "INSUFFICIENT_DELIVERY_EVIDENCE"
    # A connected client and some packets are not a healthy session.
    # These are explicit conservative *localhost synthetic* acceptance budgets,
    # not claims of Internet or 2-PC gameplay quality. Never use host-global
    # UDP drop counters to judge this server alone.
    for key in ("relay_ms_p99", "main_thread_cpu_avg"):
        metric = m.get(key)
        if type(metric) not in (int, float) or not math.isfinite(metric) or metric < 0:
            return "INVALID_METRICS"
    if m["packets_received"] / m["packets_sent"] < 0.99:
        return "DELIVERY_DEGRADED"
    # Native bbload counts sequence holes separately for each recipient.
    # Fanout can make aggregate packets_received > packets_sent, masking
    # loss in the simple sent/received ratio. Reject >1% observed holes.
    # This still does NOT prove per-client delivery or real WAN gameplay.
    if m["packets_lost"] / (m["packets_received"] + m["packets_lost"]) > 0.01:
        return "SEQUENCE_GAPS_DEGRADED"
    if m["relay_ms_p99"] > 50.0:
        return "RELAY_LATENCY_DEGRADED"
    if m["main_thread_cpu_avg"] >= 75.0:
        return "MAIN_THREAD_SATURATED"
    return "FULL_GAMEPLAY"

def isolated_load(cmd: list[str], timeout: int = 95) -> subprocess.CompletedProcess | None:
    """Terminate all spawned synthetic peers and server on timeout/interrupt.

    Upstream run_load.py starts shadnet + several bbload descendants.
    subprocess.run(timeout=...) kills only its immediate Python child, which
    can leave old servers listening on localhost and corrupt later measurements.
    This test executes on the isolated Ubuntu GitHub runner, not Windows/Fornex.
    """
    if not 20 <= timeout <= 120:
        raise ValueError("Invalid bounded load stage timeout")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as ex:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # child group already exited
        proc.communicate()
        if isinstance(ex, KeyboardInterrupt):
            raise
        return None


def run(args) -> int:
    for path in (args.shadnet,args.bbload,args.load_script):
        if not path.is_file():
            raise ValueError("Expected a real compiled executable/upstream script: " + str(path))
    with args.report.open("w", encoding="utf-8") as sink:
        stages = DIAGNOSTIC_STAGES if args.profile == "reduced" else STAGES
        for index,players in enumerate(stages):
            processes,seconds,ramp_ms=settings(players)
            cmd=[sys.executable,str(args.load_script),
                 "--shadnet",str(args.shadnet),"--bbload",str(args.bbload),
                 "--players",str(players),"--team-size","2",
                 "--processes",str(processes),"--seconds",str(seconds),
                 "--ramp-ms",str(ramp_ms),"--port",str(32314+10*index),
                 "--cfg","CheckServerBuild=false",
                 "--extra","--build '"+BUILD+"'" +
                 (" --owner-fps 10 --follower-fps 3" if args.profile == "reduced" else "")]
            result=isolated_load(cmd, timeout=95)
            if result is None:
                sample={"stage_players":players,"quality":"TIMEOUT",
                        "cleanup":"LOCAL_PROCESS_GROUP_KILLED",
                        "no_gameplay_claim":True}
                sink.write(json.dumps(sample,sort_keys=True)+"\n")
                sink.flush()
                print("SHYT_YT130_LOAD_TIMEOUT_CLEANED_WHOLE_PROCESS_GROUP",
                      "players="+str(players),flush=True)
                return 1
            summaries=[]
            for line in result.stdout.splitlines():
                if line.lstrip().startswith("{"):
                    try:
                        data=json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(data,dict) and "players" in data:
                        summaries.append(data)
            if len(summaries)!=1 or result.returncode:
                sample={"stage_players":players,"quality":"GENERATOR_FAILED",
                        "returncode":result.returncode,"summaries":len(summaries)}
            else:
                sample=summaries[0]
                sample.update(stage_players=players,quality=quality(sample,players),
                              udp_drops_scope="host-global kernel counter; not just shadNet")
            sink.write(json.dumps(sample,sort_keys=True)+"\n")
            sink.flush()
            print("SHYT_YT130_OPTIMIZED_REAL_CAPACITY_STAGE",
                  "players="+str(players),"playing="+str(sample.get("playing","?")),
                  "main_cpu="+str(sample.get("main_thread_cpu_avg","?")),
                  "quality="+sample["quality"],flush=True)
            if sample["quality"]!="FULL_GAMEPLAY" and not args.diagnostic:
                print("SHYT_YT130_HEALTH_CEILING_REACHED_NOT_A_200_PLAYER_PASS")
                return 1
    if args.diagnostic:
        print("SHYT_YT130_DIAGNOSTIC_ONLY_NO_HEALTH_OR_CAPACITY_PASS_CLAIM")
        return 0
    print("SHYT_YT130_ACTUAL_200_SIMULATED_PLAYERS_COMPLETE_OPTIMIZED_BUILD")
    return 0

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--shadnet",type=Path,required=True)
    parser.add_argument("--bbload",type=Path,required=True)
    parser.add_argument("--load-script",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--profile",choices=("baseline","reduced"),default="baseline")
    parser.add_argument("--diagnostic",action="store_true",
                        help="record all stages without publishing a passing capacity claim")
    raise SystemExit(run(parser.parse_args()))
