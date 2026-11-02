#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic evidence only: no game launches, no fabricated real measurements."""
import copy
import json
from pathlib import Path
import tempfile

from compare_runtime_evidence_v235 import compare, read_report

HASH = "a" * 64


def report(runtime, improvement=False):
    scenario = dict(
        game_sha256=HASH, patches_sha256="b" * 64, mods_sha256="c" * 64,
        hardware_id="same-i7-and-rx-gpu", os_build="Windows 11 pinned",
        gpu_driver="pinned-driver", resolution="1920x1080",
        render_settings="preset-60fps", scene="HunterDream-5clients",
        team_members=5, network_topology="NAT restricted",
        server_host="same VPS test hardware",
        build_mode="release", warmup_seconds=30, sample_seconds=120,
        scripted_actions="same deterministic traversal"
    )
    runs = []
    for i in range(3):
        runs.append({
            "id": f"run-{i}",
            "metrics": dict(frame_p99_ms=26.0 if improvement else 30.0,
                            fps_1pct_low=45.0 if improvement else 40.0,
                            server_cpu_pct=35.0 if improvement else 54.0,
                            server_out_mbps=20.0 if improvement else 32.0,
                            join_p99_ms=220.0 if improvement else 230.0,
                            udp_loss_pct=0.0, p2p_direct_pct=80.0),
            "failures": dict(crashes=0, invisible_hunters=0,
                             join_failures=0, save_corruptions=0)
        })
    return dict(schema="SHYT_RUNTIME_V235", runtime=runtime,
                build_commit=("e" if improvement else "d") * 40,
                scenario=scenario, runs=runs)


def must_reject(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("invalid benchmark was accepted")


def main():
    base = report("yt-bbport")
    better = report("bbhost", improvement=True)
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        a, b = folder / "a.json", folder / "b.json"
        a.write_text(json.dumps(base), encoding="utf-8")
        b.write_text(json.dumps(better), encoding="utf-8")
        baseline = read_report(a)
        candidate = read_report(b)
        result = compare(baseline, candidate)
        assert result["candidate_passes_offline_gate"]
        assert not result["interoperability_or_migration_approved"]
        assert result["repetitions"] == [3, 3]

        changed = copy.deepcopy(better)
        changed["scenario"]["gpu_driver"] = "other-driver"
        must_reject(lambda: compare(base, changed))
        changed = copy.deepcopy(better)
        changed["scenario"]["team_members"] = 2
        must_reject(lambda: compare(base, changed))
        changed = copy.deepcopy(better)
        changed["runs"][1]["failures"]["invisible_hunters"] = 1
        assert not compare(base, changed)["candidate_passes_offline_gate"]
        changed = copy.deepcopy(better)
        changed["runs"][0]["metrics"]["p2p_direct_pct"] = 40
        changed["runs"][1]["metrics"]["p2p_direct_pct"] = 40
        assert not compare(base, changed)["candidate_passes_offline_gate"]
        changed = copy.deepcopy(better)
        for run in changed["runs"]:
            run["metrics"]["frame_p99_ms"] = 40.0
        assert not compare(base, changed)["candidate_passes_offline_gate"]

        changed = copy.deepcopy(better)
        changed["runs"].pop()
        b.write_text(json.dumps(changed), encoding="utf-8")
        must_reject(lambda: read_report(b))
        changed = copy.deepcopy(better)
        changed["runs"][1]["id"] = changed["runs"][0]["id"]
        b.write_text(json.dumps(changed), encoding="utf-8")
        must_reject(lambda: read_report(b))
        changed = copy.deepcopy(better)
        changed["runs"][0]["metrics"]["server_cpu_pct"] = float("nan")
        b.write_text(json.dumps(changed), encoding="utf-8")
        must_reject(lambda: read_report(b))
        changed = copy.deepcopy(better)
        changed["build_commit"] = "unpinned"
        b.write_text(json.dumps(changed), encoding="utf-8")
        must_reject(lambda: read_report(b))
        b.write_text(json.dumps(better) + "\n" + json.dumps(better))
        must_reject(lambda: read_report(b))
    print("SHYT_V235_COMPARABLE_RUNTIME_GATE_SYNTHETIC_PASS")


if __name__ == "__main__":
    main()
