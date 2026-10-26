#!/usr/bin/env python3
"""Measure optimized shadNet capacity against real upstream bbload and quit at the first non-playing stage.
Each stage uses a fresh isolated localhost shadNet, synthetic database and independent loopback port.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

STAGES = (4, 16, 32, 64, 100, 200)
BUILD = "bb-build 1;version=dev;protocol=9;"

def settings(players: int) -> tuple[int, int, int]:
    if players not in STAGES:
        raise ValueError("Unreviewed synthetic client count")
    return (min(4, max(1, (players + 49)//50)), 15 if players <= 64 else 25, 100)

def quality(m: dict, players: int) -> str:
    if m.get("players") != players:
        return "GENERATOR_MISMATCH"
    if m.get("playing", 0) == 0 or m.get("packets_sent", 0) == 0:
        return "NO_GAMEPLAY"
    if m["playing"] != players:
        return "PARTIAL_GAMEPLAY"
    return "FULL_GAMEPLAY"

def run(args) -> int:
    for path in (args.shadnet,args.bbload,args.load_script):
        if not path.is_file():
            raise ValueError("Expected a real compiled executable/upstream script: " + str(path))
    with args.report.open("w", encoding="utf-8") as sink:
        for index,players in enumerate(STAGES):
            processes,seconds,ramp_ms=settings(players)
            cmd=[sys.executable,str(args.load_script),
                 "--shadnet",str(args.shadnet),"--bbload",str(args.bbload),
                 "--players",str(players),"--team-size","2",
                 "--processes",str(processes),"--seconds",str(seconds),
                 "--ramp-ms",str(ramp_ms),"--port",str(32314+10*index),
                 "--cfg","CheckServerBuild=false",
                 "--extra","--build '"+BUILD+"'"]
            try:
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=95)
            except subprocess.TimeoutExpired:
                sample={"stage_players":players,"quality":"TIMEOUT"}
                sink.write(json.dumps(sample)+"\n")
                sink.flush()
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
            if sample["quality"]!="FULL_GAMEPLAY":
                print("SHYT_YT130_CAPACITY_CEILING_REACHED_NOT_A_200_PLAYER_PASS")
                return 1
    print("SHYT_YT130_ACTUAL_200_SIMULATED_PLAYERS_COMPLETE_OPTIMIZED_BUILD")
    return 0

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--shadnet",type=Path,required=True)
    parser.add_argument("--bbload",type=Path,required=True)
    parser.add_argument("--load-script",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
