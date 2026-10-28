#!/usr/bin/env python3
"""Validate actual upstream loadtest JSON: no invented or greenwashed metrics."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
KEYS = ("players","playing","refused","packets_sent","packets_received",
        "packets_lost","udp_buffer_drops","server_cpu_avg","main_thread_cpu_avg",
        "server_rss_mb_max","relay_ms_p50","relay_ms_p99",
        "server_in_mbit","server_out_mbit")

def load(path: Path, expected_players: int, require_full_gameplay: bool = False) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Invalid bbload JSON-lines evidence")
    results = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("{"):
            x = json.loads(line)
            if isinstance(x, dict) and "players" in x:
                results.append(x)
    if len(results) != 1:
        raise ValueError("Expected exactly one real loadtest summary")
    r = results[0]
    for key in KEYS:
        x = r.get(key)
        if isinstance(x, bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or x < 0:
            raise ValueError("Missing/invalid numeric real benchmark metric: "+key)
    if r["players"] != expected_players:
        raise ValueError("Generator did not simulate the requested player count")
    # Upstream 'refused' counts EACH failed HELLO retry, not distinct players.
    # It may legitimately exceed attempted users and is diagnostic, not a
    # measure of unique refused people. Keep that raw counter unchanged.
    if r["playing"] > r["players"]:
        raise ValueError("Impossible number of playing users")
    if r["playing"] == 0:
        raise ValueError("No synthetic player reached the PLAYING state; do not publish performance results")
    if r["packets_sent"] == 0 or r["packets_lost"] > r["packets_sent"]:
        raise ValueError("No valid actual game traffic")
    if require_full_gameplay:
        # A synthetic client can report PLAYING after entering a team and
        # still lose nearly all subsequent game traffic: real PR45 delivered
        # only 264/2091 (12.63%) while 4/4 reported PLAYING.
        if (r["playing"] != expected_players or
            r["packets_sent"] < expected_players * 20 or
            r["packets_received"] * 100 < r["packets_sent"] * 99 or
            r["packets_lost"] != 0 or r["udp_buffer_drops"] != 0 or
            r["relay_ms_p99"] > 50):
            raise ValueError("4-peer smoke has incomplete game packet delivery, "
                             "missing players, Linux UDP drops or relay p99 >50ms")
    return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("report",type=Path)
    p.add_argument("--expected-players",type=int,default=200)
    p.add_argument("--require-full-gameplay",action="store_true")
    a=p.parse_args()
    r=load(a.report,a.expected_players,a.require_full_gameplay)
    print("SHYT_YT130_REAL_SYNTHETIC_LOAD200_RESULTS")
    for k in KEYS:
        print(f"{k}={r[k]}")
    print("MEASURES_SIMULATED_LOOPBACK_SERVER_RELAY_NOT_LIVE_USERS_OR_DIRECT_P2P")

if __name__=="__main__":
    main()
