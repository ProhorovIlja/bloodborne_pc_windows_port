#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V233 offline fail-closed server performance regression gate.

Input is official YT v1.3.1 server/loadtest/run_load.py one-line JSON.
Must be same machine, simulated players, team size, network profile,
build configuration and warmup before comparing. This tool never
executes commands, reads private game logs or contacts the server.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

MAX_INPUT = 128 * 1024
FIELDS = (
    "players", "playing", "refused", "packets_sent", "packets_received",
    "packets_lost", "server_out_mbit", "server_in_mbit",
    "relay_ms_p99", "welcome_ms_p99", "server_cpu_avg",
    "main_thread_cpu_avg", "udp_buffer_drops", "server_rss_mb_max"
)


def read_one(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT:
        raise ValueError("missing or oversized benchmark result")
    content = path.read_text(encoding="utf-8").strip().splitlines()
    # Accept only ONE bounded report; never pull/parse complete server logs.
    if len(content) != 1:
        raise ValueError("expected a single official run_load.py JSON summary")
    obj = json.loads(content[0])
    if not isinstance(obj, dict):
        raise ValueError("benchmark result must be an object")
    for key in FIELDS:
        v = obj.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f"missing or invalid official metric: {key}")
    for key in ("players", "playing", "refused", "packets_sent", "packets_received",
                "packets_lost", "udp_buffer_drops"):
        if not isinstance(obj[key], int):
            raise ValueError(f"player/packet metric must be an integer: {key}")
    if obj["playing"] > obj["players"] or obj["packets_received"] > obj["packets_sent"]:
        raise ValueError("inconsistent played games or packet counts")
    return obj


def compare(baseline: dict, candidate: dict, *, main_cpu_slack: float = 5.0,
            relay_p99_slack: float = 10.0,
            outbound_mbit_slack: float = 0.0,
            rss_slack_mb: float = 50.0) -> dict:
    if any(x < 0 or not math.isfinite(x) for x in
           (main_cpu_slack, relay_p99_slack, outbound_mbit_slack, rss_slack_mb)):
        raise ValueError("invalid regression budget")
    if baseline["players"] != candidate["players"] or baseline["players"] < 1:
        raise ValueError("benchmark loads differ; no comparison permitted")
    gates = {
        "playing_population_not_reduced":
            candidate["playing"] >= baseline["playing"],
        "refused_connections_not_increased":
            candidate["refused"] <= baseline["refused"],
        "no_new_udp_receive_buffer_drops":
            candidate["udp_buffer_drops"] <= baseline["udp_buffer_drops"],
        "main_relay_thread_cpu_within_budget":
            candidate["main_thread_cpu_avg"] <= baseline["main_thread_cpu_avg"] + main_cpu_slack,
        "p99_relay_latency_within_budget":
            candidate["relay_ms_p99"] <= baseline["relay_ms_p99"] + relay_p99_slack,
        "outbound_bandwidth_within_budget":
            candidate["server_out_mbit"] <= baseline["server_out_mbit"] + outbound_mbit_slack,
        "server_rss_within_budget":
            candidate["server_rss_mb_max"] <= baseline["server_rss_mb_max"] + rss_slack_mb,
    }
    def delta(k: str) -> float:
        return round(candidate[k] - baseline[k], 4)
    return {
        "format": "SHYT_V233_OFFLINE_SERVER_CAPACITY_REGRESSION",
        "same_simulated_player_count": baseline["players"],
        "all_gates_pass": all(gates.values()),
        "gates": gates,
        "delta": {k: delta(k) for k in (
            "main_thread_cpu_avg", "server_cpu_avg",
            "server_out_mbit", "server_in_mbit", "relay_ms_p99",
            "welcome_ms_p99", "server_rss_mb_max")},
        "this_is_simulated_shadnet_load_only": True,
        "real_direct_p2p_verified": False,
        "live_fornex_touched": False,
        "test_matching_hardware_profiles_and_repeatability_unproven": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--max-main-cpu-regression-points", type=float, default=5.0)
    ap.add_argument("--max-relay-p99-regression-ms", type=float, default=10.0)
    ap.add_argument("--max-outbound-regression-mbit", type=float, default=0.0)
    ap.add_argument("--max-rss-regression-mb", type=float, default=50.0)
    args = ap.parse_args()
    try:
        report = compare(
            read_one(args.baseline), read_one(args.candidate),
            main_cpu_slack=args.max_main_cpu_regression_points,
            relay_p99_slack=args.max_relay_p99_regression_ms,
            outbound_mbit_slack=args.max_outbound_regression_mbit,
            rss_slack_mb=args.max_rss_regression_mb
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        ap.error(str(exc))
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["all_gates_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
