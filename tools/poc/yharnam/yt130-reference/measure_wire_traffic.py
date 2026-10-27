#!/usr/bin/env python3
"""Run pinned upstream synthetic players; inspect own server's wire-kinds only.

Read-only traffic attribution: fixed protocol kind counts without sensitive
addresses, names, secrets or packet bytes. CI-only disposable localhost tests.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

WIRE = re.compile(
    r"YT130_WIRE_TRAFFIC kind=(\d+) in_packets=(\d+) in_bytes=(\d+)"
    r" out_packets=(\d+) out_bytes=(\d+)"
)
FOLDER = re.compile(r"server folder:\s+(/tmp/shadnet-load-[a-zA-Z0-9_-]+)")
STAGES = (32, 64, 100, 200)
BUILD = "bb-build 1;version=dev;protocol=9;"


def aggregate(lines: list[str]) -> dict[str, dict[str, int]]:
    total: dict[str, dict[str, int]] = {}
    for line in lines:
        if not (found := WIRE.search(line)):
            continue
        kind, *values = found.groups()
        row = total.setdefault(kind, {
            "in_packets": 0, "in_bytes": 0,
            "out_packets": 0, "out_bytes": 0,
        })
        for key, number in zip(row, values):
            row[key] += int(number)
    return total


def extract_server_counters(stderr: str, output: Path) -> tuple[str, dict]:
    folders = FOLDER.findall(stderr)
    if len(folders) != 1:
        return "MISSING_SERVER_FOLDER", {}
    home = Path(folders[0])
    if home.is_symlink() or not home.is_dir() or home.parent != Path("/tmp"):
        return "UNSAFE_SERVER_FOLDER", {}
    lines = []
    try:
        with (home / "shadnet.log").open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if "YT130_WIRE_TRAFFIC kind=" in line:
                    lines.append(line)
        output.write_text("".join(lines), encoding="utf-8")
    finally:
        shutil.rmtree(home)
    return ("RECORDED" if lines else "NO_WIRE_COUNTERS"), aggregate(lines)


def run(args) -> int:
    for binary in (args.shadnet, args.bbload, args.load_script):
        if not binary.is_file():
            raise ValueError(f"Required real executable/script missing: {binary}")
    args.output.mkdir(parents=True, exist_ok=True)
    report = args.output / "wire-stages.jsonl"
    with report.open("w", encoding="utf-8") as out:
        for idx, players in enumerate(STAGES):
            processes = min(4, max(1, (players + 49) // 50))
            seconds = 15 if players <= 64 else 25
            cmd = [
                sys.executable, str(args.load_script),
                "--shadnet", str(args.shadnet),
                "--bbload", str(args.bbload),
                "--players", str(players),
                "--team-size", "2",
                "--processes", str(processes),
                "--seconds", str(seconds),
                "--ramp-ms", "100",
                "--port", str(33314 + 10 * idx),
                "--cfg", "CheckServerBuild=false",
                "--keep",
                "--extra", "--build '" + BUILD + "'",
            ]
            try:
                completed = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=100
                )
            except subprocess.TimeoutExpired:
                out.write(json.dumps({"players": players, "error": "TIMEOUT"}) + "\n")
                out.flush()
                continue
            stdout = [json.loads(line) for line in completed.stdout.splitlines()
                      if line.startswith("{")]
            evidence, kinds = extract_server_counters(
                completed.stderr, args.output / f"wire-{players}.log"
            )
            summary = stdout[0] if len(stdout) == 1 else {}
            item = {
                "stage_players": players,
                "run_returncode": completed.returncode,
                "evidence": evidence,
                "wire_kind_packets_and_bytes": kinds,
                "synthetic": {
                    k: summary.get(k) for k in (
                        "players", "playing", "packets_sent", "packets_received",
                        "relay_ms_p99", "main_thread_cpu_avg", "server_out_mbit"
                    )
                },
                "scope": "DISPOSABLE_SYNTHETIC_SERVER_ONLY; main link read/"
                         "Hub Apply and world Apply; not all direct sends, "
                         "not NIC accounting; reporting full 5-second windows",
            }
            out.write(json.dumps(item, sort_keys=True) + "\n")
            out.flush()
            print("YT130_WIRE_EVIDENCE players=" + str(players)
                  + " status=" + evidence
                  + " kinds=" + ",".join(sorted(kinds)), flush=True)
    print("YT130_WIRE_TRAFFIC_DIAGNOSTIC_ONLY_NOT_A_CAPACITY_PASS")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadnet", type=Path, required=True)
    parser.add_argument("--bbload", type=Path, required=True)
    parser.add_argument("--load-script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(parser.parse_args()))
