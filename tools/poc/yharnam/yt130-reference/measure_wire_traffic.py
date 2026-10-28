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
COOP = re.compile(
    r"YT130_COOP_RELIABILITY frames=(\d+) body_bytes=(\d+)"
    r" reliable_entries=(\d+) fresh_entries=(\d+) resent_entries=(\d+)"
    r" ack_only_frames=(\d+) pending_chunks=(\d+) pending_bytes=(\d+)"
    r" blocked_members=(\d+) active_members=(\d+)"
)
ORIGIN = re.compile(r"YT130_COOP_ORIGIN kind=(\d+) sends=(\d+)")
EVENTLOOP = re.compile(
    r"YT130_EVENTLOOP read_batches=(\d+)"
    r"(?: udp_queue_max=(\d+) udp_queue_pressure=(\d+))?"
    r" read_datagrams=(\d+) read_busy_us=(\d+) max_read_batch_us=(\d+)"
    r" max_read_batch_datagrams=(\d+) world_ticks=(\d+)"
    r" world_busy_us=(\d+) max_world_busy_us=(\d+)"
    r" max_world_gap_us=(\d+) late_world_ticks=(\d+)"
)
FOLDER = re.compile(r"server folder:\s+(/tmp/shadnet-load-[a-zA-Z0-9_-]+)")
STAGES = (32, 64, 100, 200)
BUILD = "bb-build 1;version=dev;protocol=9;"
# Names are source-pinned to official server/coop/coop.proto Envelope.oneof body.
# Never read message contents or display private player identifiers.
ENVELOPE_NAMES = {
    1: "Hello",
    2: "Welcome",
    3: "Lifecycle",
    4: "KillProposal",
    5: "Entries",
    6: "SnapshotRequest",
    7: "Snapshot",
    8: "ShownReport",
    9: "FlagProposal",
    10: "MapStateReport",
    11: "ReturnPointReport",
    12: "HpProposal",
    13: "MemberMap",
    14: "MapBoard",
    15: "Rest",
    16: "RestBoard",
    17: "Trophies",
    18: "Echoes",
    19: "Vitals",
    20: "VitalsBoard",
    21: "Portrait",
    22: "EnemyOwners",
    23: "LobbyHello",
    24: "TeamRequest",
    25: "LobbyState",
    26: "TeamStart",
    27: "TradeOffer",
    28: "TradeStatus",
    29: "TradeAsk",
    30: "TradeAnswer",
    31: "TradeCancel",
    32: "TradeClosed",
    33: "TradeGrant",
    34: "TradeGranted",
    35: "TeamWorld",
    36: "TeamSession",
    37: "LoadProgress",
    39: "EnemyHit",
    40: "ResumeAt",
    41: "Ping",
    42: "AltarRecord",
    43: "InvadeRequest",
    44: "InvasionNotice",
    45: "InvasionStart",
    46: "InvaderJoined",
    47: "InvasionEnd",
    48: "TeamTravel",
    49: "DuelRequest",
    50: "DuelState",
}



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


def aggregate_eventloop(lines: list[str]) -> dict:
    """5s bucket timing: summed busy time, max single callback and timer gap.

    No packet bodies, player identities, credentials or user IPs.
    """
    fields = (
        "read_batches", "udp_queue_max", "udp_queue_pressure",
        "read_datagrams", "read_busy_us", "max_read_batch_us",
        "max_read_batch_datagrams", "world_ticks", "world_busy_us",
        "max_world_busy_us", "max_world_gap_us", "late_world_ticks",
    )
    maximums = {
        "max_read_batch_us", "max_read_batch_datagrams", "udp_queue_max",
        "max_world_busy_us", "max_world_gap_us",
    }
    totals = dict.fromkeys(fields, 0)
    windows = 0
    queue_windows = 0
    for line in lines:
        if m := EVENTLOOP.search(line):
            windows += 1
            groups = m.groups()
            if groups[1] is not None and groups[2] is not None:
                queue_windows += 1
            for name, value in zip(fields, groups):
                # Original observations have no FIFO metrics. Keep missing
                # evidence distinct from a measured queue size of zero.
                if value is None:
                    continue
                number = int(value)
                totals[name] = max(totals[name], number) if name in maximums else totals[name] + number
    return {"observed_windows": windows, "queue_evidence_windows": queue_windows,
            "metrics": totals}


def aggregate_coop(lines: list[str]) -> dict:
    """Plaintext reliable frame diagnostics: per-window snapshot max for queues."""
    fields = ("frames", "body_bytes", "reliable_entries", "fresh_entries",
              "resent_entries", "ack_only_frames", "pending_chunks",
              "pending_bytes", "blocked_members", "active_members")
    totals = {k: 0 for k in fields}
    origins: dict[str, int] = {}
    intervals = 0
    for line in lines:
        if m := COOP.search(line):
            intervals += 1
            for key, value in zip(fields, m.groups()):
                if key.startswith("pending_") or key in ("blocked_members", "active_members"):
                    totals[key] = max(totals[key], int(value))
                else:
                    totals[key] += int(value)
        if m := ORIGIN.search(line):
            key, count = m.groups()
            origins[key] = origins.get(key, 0) + int(count)
    return {"intervals": intervals, "metrics": totals,
            "envelope_body_case_sends": origins,
            "eventloop": aggregate_eventloop(lines),
            "envelope_type_sends": {
                ENVELOPE_NAMES.get(int(kind), "Unknown_" + kind): count
                for kind, count in origins.items()
            }}


def extract_server_counters(stderr: str, output: Path) -> tuple[str, dict, dict]:
    folders = FOLDER.findall(stderr)
    if len(folders) != 1:
        return "MISSING_SERVER_FOLDER", {}, {}
    home = Path(folders[0])
    if home.is_symlink() or not home.is_dir() or home.parent != Path("/tmp"):
        return "UNSAFE_SERVER_FOLDER", {}, {}
    lines = []
    try:
        with (home / "shadnet.log").open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if any(tag in line for tag in ("YT130_WIRE_TRAFFIC kind=",
                                           "YT130_COOP_RELIABILITY frames=",
                                           "YT130_COOP_ORIGIN kind=",
                                           "YT130_EVENTLOOP read_batches=")):
                    lines.append(line)
        output.write_text("".join(lines), encoding="utf-8")
    finally:
        shutil.rmtree(home)
    return ("RECORDED" if lines else "NO_WIRE_COUNTERS"), aggregate(lines), aggregate_coop(lines)


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
            evidence, kinds, reliability = extract_server_counters(
                completed.stderr, args.output / f"wire-{players}.log"
            )
            summary = stdout[0] if len(stdout) == 1 else {}
            item = {
                "stage_players": players,
                "run_returncode": completed.returncode,
                "evidence": evidence,
                "wire_kind_packets_and_bytes": kinds,
                "coop_reliability": reliability,
                "synthetic": {
                    k: summary.get(k) for k in (
                        "players", "playing", "packets_sent", "packets_received",
                        "relay_ms_p99", "main_thread_cpu_avg", "server_out_mbit"
                    )
                },
                "scope": "DISPOSABLE_SYNTHETIC_SERVER_ONLY; main link read/"
                         "Hub Apply and world Apply; not all direct sends, "
                         "not NIC accounting; reporting full 5-second windows;"
                         " Coop metrics count raw reliable stream chunks and ACK-only"
                         " frames; not end-user gameplay packet delivery",
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
