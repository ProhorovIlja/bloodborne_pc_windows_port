#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V235 bounded, offline BBHost-vs-YT benchmark evidence gate.

Independent test operators supply ONE small JSON summary per runtime.
This does not execute games, contact Fornex, or certify benchmark honesty.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

MAX_BYTES = 128 * 1024
MIN_RUNS = 3
MAX_RUNS = 20
SCENARIO_FIELDS = (
    "game_sha256", "patches_sha256", "mods_sha256", "hardware_id",
    "os_build", "gpu_driver", "resolution", "render_settings",
    "scene", "team_members", "network_topology", "server_host",
    "build_mode", "warmup_seconds", "sample_seconds", "scripted_actions"
)
METRICS = (
    "frame_p99_ms", "fps_1pct_low", "server_cpu_pct",
    "server_out_mbps", "join_p99_ms", "udp_loss_pct", "p2p_direct_pct"
)
FAILURES = ("crashes", "invisible_hunters", "join_failures", "save_corruptions")


def read_report(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or not (0 < path.stat().st_size <= MAX_BYTES):
        raise ValueError("invalid or oversized benchmark summary")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "SHYT_RUNTIME_V235":
        raise ValueError("unsupported benchmark format")
    if data.get("runtime") not in ("bbhost", "yt-bbport", "lantern"):
        raise ValueError("unknown runtime identity")
    sha = data.get("build_commit")
    if not isinstance(sha, str) or not (7 <= len(sha) <= 40) or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("unpinned build")
    scenario = data.get("scenario")
    if not isinstance(scenario, dict) or set(scenario) != set(SCENARIO_FIELDS):
        raise ValueError("incomplete or extra scenario fields")
    for name, value in scenario.items():
        if name in ("team_members", "warmup_seconds", "sample_seconds"):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"invalid scenario quantity {name}")
        elif not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError(f"invalid scenario identity {name}")
    if scenario["team_members"] not in (2, 5):
        raise ValueError("only identical two- or five-client sessions can be compared")
    for name in ("game_sha256", "patches_sha256", "mods_sha256"):
        value = scenario[name]
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"bad content identity {name}")
    runs = data.get("runs")
    if not isinstance(runs, list) or not (MIN_RUNS <= len(runs) <= MAX_RUNS):
        raise ValueError("need 3-20 independent runs")
    seen = set()
    for run in runs:
        if not isinstance(run, dict) or set(run) != {"id", "metrics", "failures"}:
            raise ValueError("invalid run layout")
        rid = run["id"]
        if not isinstance(rid, str) or not rid or len(rid) > 64 or rid in seen:
            raise ValueError("missing or duplicate run identity")
        seen.add(rid)
        metrics, failures = run["metrics"], run["failures"]
        if not isinstance(metrics, dict) or set(metrics) != set(METRICS):
            raise ValueError("missing/extra metrics")
        if not isinstance(failures, dict) or set(failures) != set(FAILURES):
            raise ValueError("missing/extra safety counters")
        for key, val in metrics.items():
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0:
                raise ValueError(f"invalid metric {key}")
            if key.endswith("_pct") and val > 100:
                raise ValueError(f"invalid percentage {key}")
        for key, val in failures.items():
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                raise ValueError(f"invalid failure counter {key}")
    return data


def summarize(data: dict) -> dict:
    return {key: statistics.median(run["metrics"][key] for run in data["runs"])
            for key in METRICS}


def _within(candidate: float, baseline: float, factor: float) -> bool:
    return candidate <= baseline * factor + 1e-9


def compare(baseline: dict, candidate: dict) -> dict:
    if baseline["runtime"] == candidate["runtime"]:
        raise ValueError("two distinct runtime implementations required")
    if baseline["scenario"] != candidate["scenario"]:
        raise ValueError("different hardware/game/mod/network/scenario: comparison invalid")
    b, c = summarize(baseline), summarize(candidate)
    gates = {
        "frame_p99_no_regression": _within(c["frame_p99_ms"], b["frame_p99_ms"], 1.05),
        "fps_1pct_low_no_regression": c["fps_1pct_low"] + 1e-9 >= b["fps_1pct_low"] * 0.95,
        "server_cpu_no_regression": _within(c["server_cpu_pct"], b["server_cpu_pct"], 1.05),
        "server_out_no_regression": _within(c["server_out_mbps"], b["server_out_mbps"], 1.05),
        "join_p99_no_regression": _within(c["join_p99_ms"], b["join_p99_ms"], 1.05),
        "loss_no_regression": _within(c["udp_loss_pct"], b["udp_loss_pct"], 1.05),
        "direct_p2p_not_worse": c["p2p_direct_pct"] + 5 >= b["p2p_direct_pct"],
        "no_candidate_safety_failures": all(
            sum(run["failures"][name] for run in candidate["runs"]) == 0 for name in FAILURES
        ),
    }
    material_gain = any(
        c[key] <= 0.95 * b[key] and b[key] > 0
        for key in ("frame_p99_ms", "server_cpu_pct", "server_out_mbps")
    ) or (b["fps_1pct_low"] > 0 and c["fps_1pct_low"] >= 1.05 * b["fps_1pct_low"])
    return {
        "schema": "SHYT_RUNTIME_V235_COMPARISON",
        "reference_runtime": baseline["runtime"],
        "candidate_runtime": candidate["runtime"],
        "scenario_identical": True,
        "repetitions": [len(baseline["runs"]), len(candidate["runs"])],
        "reference_medians": b,
        "candidate_medians": c,
        "gates": gates,
        "material_gain_at_least_5pct": material_gain,
        "candidate_passes_offline_gate": all(gates.values()) and material_gain,
        "real_hardware_measurement_verified_by_tool": False,
        "interoperability_or_migration_approved": False,
        "production_fornex_tested": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        report = compare(read_report(args.baseline), read_report(args.candidate))
        serialized = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.output:
            if args.output.is_symlink() or not args.output.parent.is_dir():
                raise ValueError("unsafe output path")
            args.output.write_text(serialized, encoding="utf-8")
        else:
            print(serialized)
        return 0 if report["candidate_passes_offline_gate"] else 3
    except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"V235_BENCHMARK_INCOMPARABLE: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
