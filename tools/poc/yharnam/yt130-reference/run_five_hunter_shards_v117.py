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
OWNER_CASES = (1, 3, 5)  # 5-player team; per-actor enemy ownership in YT 1.3
CROSS_MODES = ("mixed", "code", "invite")  # same original hosted bbload join policies
RUN_SECONDS = 30
RAMP_MS = 35
TIMEOUT = 120
LOAD_PROCESSES = (4, 8, 16)  # original Qt bbload process isolation A/B, same population

def minimum_original_source_entries(owner_seats: int, seconds: int) -> int:
    """Conservative >=80% offer floor for the pinned original real Qt bbload.

    Game::SendGamePackets emits two 0x31 entries per owner frame,
    one 0x06 entry per follower frame, to each of the other four seats.
    Owner=30fps, follower=8fps from command(); extra owner 0x04/0x05/0x06
    frames are deliberately NOT included, so this is a lower bound.
    A generator unable to sustain even this traffic cannot prove server
    capacity at 200 active hunters, regardless of 99% packet delivery.
    """
    if owner_seats not in OWNER_CASES or type(seconds) is not int or seconds < 0:
        raise ValueError("Invalid source-verified five-seat load rate inputs")
    teams=POPULATION//SIZE
    per_team_per_second=(2*30*owner_seats+8*(SIZE-owner_seats))*(SIZE-1)
    return per_team_per_second*teams*seconds*80//100


def grade(item: dict, expected_shards: int, expected_workers: int = 4,
          require_directed: bool = False, owner_seats: int = 1) -> dict:
    if require_directed and owner_seats not in OWNER_CASES:
        raise ValueError("Required original owner count must be 1, 3 or 5")
    if expected_workers not in LOAD_PROCESSES:
        raise ValueError("Only four, eight or sixteen original Qt workers")
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
    # V155: real original Qt LinkServer traffic by source wire kind 3.
    # These are 5-second samples of the entire run, NOT exact steady-state
    # client delivery counts and not proof of successful remote receipt.
    wire_fields = ("game_wire_in_packets", "game_wire_out_packets",
                   "game_wire_in_bytes", "game_wire_out_bytes",
                   "game_wire_sample_windows")
    for key in wire_fields:
        value = item.get(key)
        if type(value) is not int or value < 0:
            return {"quality": "MISSING_REAL_QT_WIRE_COUNTERS", "field": key}
        if any(type(row.get(key)) is not int or row[key] < 0 for row in rows):
            return {"quality": "INVALID_QT_SHARD_WIRE_COUNTERS", "field": key}
        if value != sum(row[key] for row in rows):
            return {"quality": "QT_WIRE_COUNTER_TOTAL_MISMATCH", "field": key}
    # V156 server's own refusal reasons from observed LobbyState.notice.
    # Reply counters can include repeat attempts: not distinct players.
    notice_fields = ("team_name_absent", "team_name_ambiguous",
                     "team_lookup_throttled", "team_other_notice",
                     "team_total_notices")
    for field in notice_fields:
        if type(item.get(field)) is not int or item[field] < 0:
            return {"quality": "MISSING_REAL_LOBBY_REFUSAL_COUNTS", "field": field}
    if (item["team_name_absent"] + item["team_name_ambiguous"] +
        item["team_lookup_throttled"] + item["team_other_notice"] !=
        item["team_total_notices"]):
        return {"quality": "INCONSISTENT_REAL_LOBBY_REFUSAL_COUNTS"}
    # V158/159: original Qt receive and game-data decoding observations.
    # Never silently omit source counters from the durable diagnostic JSON.
    recv_fields = ("udp_read_failed", "udp_read_short",
                   "game_data_datagrams_received", "game_data_decode_failed",
                   "game_frame_decode_failed", "game_frame_bad_header",
                   "game_frame_short_entries", "game_frame_decoded")
    detail_fields = ("team_no_invite", "team_no_code", "team_full",
                     "team_already_joined", "team_create_first",
                     "team_world_unavailable", "team_unknown_other")
    for field in recv_fields + detail_fields:
        if type(item.get(field)) is not int or item[field] < 0:
            return {"quality": "MISSING_OR_INVALID_QT_CLIENT_RECEIVE_OR_JOIN_DETAILS",
                    "field": field}
    if (item["game_data_decode_failed"] + item["game_frame_decode_failed"] +
            item["game_frame_bad_header"] + item["game_frame_decoded"] !=
            item["game_data_datagrams_received"]):
        return {"quality": "QT_CLIENT_GAME_DATA_FRAME_COUNTER_MISMATCH"}
    if sum(item[field] for field in detail_fields) != item["team_other_notice"]:
        return {"quality": "ORIGINAL_LOBBY_OTHER_NOTICE_DETAIL_MISMATCH"}
    # V161: independent common send-time cohort. The source-only V155/159
    # workflows still run without it. If any cohort field is supplied, all
    # must be source-consistent or reject, never silently discard a bad score.
    cohort_fields = ("cohort_quality", "cohort_start_us", "cohort_end_us",
                     "cohort_seconds", "cohort_packets_sent",
                     "cohort_packets_received", "cohort_scope")
    has_cohort = any(key in item for key in cohort_fields)
    if has_cohort:
        if any(key not in item for key in cohort_fields):
            return {"quality": "MISSING_OR_PARTIAL_GLOBAL_COHORT_EVIDENCE"}
        if (item["cohort_quality"] not in (
                "NO_GLOBAL_200_PLAYER_FIVE_SEAT_COHORT",
                "INVALID_GLOBAL_COHORT_BUCKETS",
                "INSUFFICIENT_OR_INVALID_GLOBAL_GAME_COHORT",
                "GLOBAL_GAME_COHORT_DELIVERY_DEGRADED",
                "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY") or
                type(item["cohort_scope"]) is not str or
                "NOT a production QoS pass" not in item["cohort_scope"] or
                any(type(item[key]) is not int or item[key] < 0
                    for key in cohort_fields[1:6])):
            return {"quality": "INVALID_GLOBAL_COHORT_EVIDENCE"}
        if (item["cohort_end_us"] < item["cohort_start_us"] or
            item["cohort_end_us"] - item["cohort_start_us"] !=
                item["cohort_seconds"] * 1_000_000 or
            (item["cohort_quality"] == "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY"
             and (item["cohort_seconds"] < 5 or
                  item["cohort_packets_sent"] < 10000 or
                  item["cohort_packets_received"] > item["cohort_packets_sent"] or
                  item["cohort_packets_received"] * 100 <
                     item["cohort_packets_sent"] * 99))):
            return {"quality": "INVALID_GLOBAL_COHORT_EVIDENCE"}
    # V169: directed sender->recipient synthetic telemetry must be complete
    # when requested by the original 200-player CI. A 99% global average
    # alone may conceal a nearly dead low-volume directed route.
    directed_fields = ("directed_quality", "directed_packets_sent",
                       "directed_packets_received", "directed_routes",
                       "directed_scope")
    has_directed = any(key in item for key in directed_fields)
    if require_directed and not has_directed:
        return {"quality": "MISSING_REQUIRED_DIRECTED_GAME_EVIDENCE"}
    if has_directed:
        if not has_cohort or any(key not in item for key in directed_fields):
            return {"quality": "MISSING_OR_PARTIAL_DIRECTED_GAME_EVIDENCE"}
        status = item["directed_quality"]
        if (status not in ("NO_VERIFIED_DIRECTED_GAME_COHORT",
                           "INVALID_DIRECTED_GAME_COHORT",
                           "DIRECTED_GAME_COHORT_DELIVERY_DEGRADED",
                           "DIRECTED_GAME_COHORT_OFFER_UNDERDRIVEN",
                           "DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY") or
                type(item["directed_scope"]) is not str or
                "NOT a production QoS pass" not in item["directed_scope"] or
                any(type(item[k]) is not int or item[k] < 0
                    for k in directed_fields[1:4])):
            return {"quality": "INVALID_DIRECTED_GAME_EVIDENCE"}
        reliable = status in ("DIRECTED_GAME_COHORT_DELIVERY_DEGRADED",
                              "DIRECTED_GAME_COHORT_OFFER_UNDERDRIVEN",
                              "DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY")
        if reliable and (
                item["cohort_quality"] not in (
                    "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY",
                    "GLOBAL_GAME_COHORT_DELIVERY_DEGRADED") or
                item["directed_packets_sent"] != item["cohort_packets_sent"] or
                item["directed_packets_received"] != item["cohort_packets_received"] or
                item["directed_routes"] != POPULATION*(SIZE-1) or
                item["directed_packets_received"] > item["directed_packets_sent"]):
            return {"quality": "INVALID_DIRECTED_GAME_EVIDENCE"}
        if status == "DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY" and (
                item["cohort_quality"] != "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY" or
                item["directed_packets_received"] * 100 <
                    item["directed_packets_sent"] * 99):
            return {"quality": "INVALID_DIRECTED_GAME_EVIDENCE"}
        if not reliable and any(item[k] for k in directed_fields[1:4]):
            return {"quality": "INVALID_DIRECTED_GAME_EVIDENCE"}
    for row in rows:
        cpu = row.get("link_thread_cpu_avg")
        if type(cpu) not in (float, int) or not math.isfinite(cpu) or cpu < 0:
            return {"quality": "INVALID_PER_SHARD_CPU"}
    for key in ("playing", "game_receivers", "complete_teams",
                "linking", "lobby", "awaiting_welcome",
                "udp_write_failed", "udp_write_short",
                "steady_workers", "steady_packets_sent", "steady_packets_received",
                "packets_sent", "packets_received",
                "packets_lost", "refused", "udp_buffer_drops"):
        value = item.get(key)
        if type(value) is not int or value < 0:
            return {"quality": "MISSING_REAL_GAME_COUNTERS", "field": key}
    for key in ("relay_ms_p99", "redirects", "redirect_ms_p99",
                "steady_window_ms_min"):
        val = item.get(key)
        if type(val) not in (int, float) or not math.isfinite(val) or val < 0:
            return {"quality": "INVALID_TIMING_OR_REDIRECT", "field": key}
    playing, receivers = item["playing"], item["game_receivers"]
    if (item["linking"] + item["lobby"] + item["awaiting_welcome"] +
            playing != POPULATION):
        return {"quality": "INVALID_ORIGINAL_GAME_LIFECYCLE_SUM"}
    sent, received = item["packets_sent"], item["packets_received"]
    steady_sent = item["steady_packets_sent"]
    steady_received = item["steady_packets_received"]
    if require_directed and (
            item["cohort_packets_sent"] > sent or
            item["cohort_packets_received"] > received or
            item["cohort_packets_sent"] > steady_sent or
            item["cohort_packets_received"] > steady_received):
        # The shared sender-clock interval is a subset of the original
        # real Qt worker's full-run AND post-Playing steady counters.
        # Never accept a fabricated 800-route healthy cohort larger than
        # the traffic actually generated/decoded by the entire worker run.
        return {"quality": "DIRECTED_COHORT_EXCEEDS_ORIGINAL_QT_TOTALS"}
    if item["steady_workers"] != expected_workers or item["steady_window_ms_min"] < 5000:
        steady_quality = "NO_FIVE_HUNTER_STEADY_WINDOW"
    elif steady_sent < 10000 or steady_received > steady_sent:
        steady_quality = "INSUFFICIENT_OR_INVALID_STEADY_TRAFFIC"
    elif steady_received * 100 < steady_sent * 99:
        steady_quality = "STEADY_DELIVERY_DEGRADED"
    else:
        steady_quality = "STEADY_DELIVERY_PASS_SYNTHETIC_ONLY"
    if item["udp_write_failed"] or item["udp_write_short"]:
        quality = "GENERATOR_UDP_SOCKET_WRITE_FAILED"
    elif item["udp_read_failed"] or item["udp_read_short"]:
        quality = "GENERATOR_UDP_SOCKET_READ_FAILED"
    elif (item["game_data_decode_failed"] or item["game_frame_decode_failed"] or
          item["game_frame_bad_header"] or item["game_frame_short_entries"]):
        quality = "GENERATOR_GAME_DATA_DECODE_REJECTED"
    elif playing != POPULATION:
        quality = "NOT_ALL_PLAYING"
    elif receivers != POPULATION:
        quality = "GAME_RECEIVERS_MISSING"
    elif item["complete_teams"] != POPULATION // SIZE:
        quality = "FIVE_HUNTER_TEAMS_INCOMPLETE"
    elif item["refused"] or sent < POPULATION * 10:
        quality = "INSUFFICIENT_ACCEPTED_GAME_TRAFFIC"
    elif received > sent or received * 100 < sent * 99 or item["packets_lost"]:
        quality = "REAL_GAME_DELIVERY_DEGRADED"
    elif steady_quality != "STEADY_DELIVERY_PASS_SYNTHETIC_ONLY":
        quality = steady_quality
    elif item["udp_buffer_drops"]:
        quality = "HOST_KERNEL_UDP_DROPS"
    elif item["relay_ms_p99"] > 50:
        quality = "RELAY_P99_OVER_50MS"
    elif max(row["link_thread_cpu_avg"] for row in rows) >= 75:
        quality = "SHARD_CPU_SATURATED"
    elif (expected_shards > 1 and
          (item["redirects"] < 1 or item["redirect_ms_p99"] > 2000)):
        quality = "CROSS_SHARD_REDIRECT_FAILED"
    elif any(r["game_wire_sample_windows"] == 0 for r in rows):
        quality = "QT_GAME_DATA_WIRE_SAMPLES_MISSING"
    elif has_directed and item["directed_quality"] == "DIRECTED_GAME_COHORT_OFFER_UNDERDRIVEN":
        quality = "DIRECTED_GAME_COHORT_OFFER_UNDERDRIVEN"
    elif has_directed and item["directed_quality"] != "DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY":
        quality = "DIRECTED_GAME_COHORT_UNHEALTHY"
    elif require_directed and item["cohort_packets_sent"] < minimum_original_source_entries(
            owner_seats, item["cohort_seconds"]):
        quality = "INSUFFICIENT_QT_ORIGINAL_GAME_OFFERED_RATE"
    else:
        quality = "FULL_GAMEPLAY_SYNTHETIC_ONLY"
    return {
        "quality": quality, "players": POPULATION, "shards": expected_shards,
        **({key: item[key] for key in cohort_fields} if has_cohort else {}),
        **({key: item[key] for key in directed_fields} if has_directed else {}),
        **({"cohort_min_offered_entries": minimum_original_source_entries(
            owner_seats, item["cohort_seconds"])} if require_directed else {}),
        "playing": playing, "game_receivers": receivers,
        "linking": item["linking"], "lobby": item["lobby"],
        "awaiting_welcome": item["awaiting_welcome"],
        "udp_write_failed": item["udp_write_failed"],
        "udp_write_short": item["udp_write_short"],
        "game_wire_in_packets": item["game_wire_in_packets"],
        "game_wire_out_packets": item["game_wire_out_packets"],
        "game_wire_in_bytes": item["game_wire_in_bytes"],
        "game_wire_out_bytes": item["game_wire_out_bytes"],
        "game_wire_sample_windows": item["game_wire_sample_windows"],
        "team_name_absent": item["team_name_absent"],
        "team_name_ambiguous": item["team_name_ambiguous"],
        "team_lookup_throttled": item["team_lookup_throttled"],
        "team_other_notice": item["team_other_notice"],
        "team_total_notices": item["team_total_notices"],
        "udp_read_failed": item["udp_read_failed"],
        "udp_read_short": item["udp_read_short"],
        "game_data_datagrams_received": item["game_data_datagrams_received"],
        "game_data_decode_failed": item["game_data_decode_failed"],
        "game_frame_decode_failed": item["game_frame_decode_failed"],
        "game_frame_bad_header": item["game_frame_bad_header"],
        "game_frame_short_entries": item["game_frame_short_entries"],
        "game_frame_decoded": item["game_frame_decoded"],
        "team_no_invite": item["team_no_invite"],
        "team_no_code": item["team_no_code"],
        "team_full": item["team_full"],
        "team_already_joined": item["team_already_joined"],
        "team_create_first": item["team_create_first"],
        "team_world_unavailable": item["team_world_unavailable"],
        "team_unknown_other": item["team_unknown_other"],
        "notice_scope": "Refusal responses observed, not unique players",
        "wire_scope": "Qt LinkServer 5s samples over whole run; not steady client delivery",
        "complete_teams": item["complete_teams"], "packets_sent": sent,
        "steady_quality": steady_quality,
        "steady_workers": item["steady_workers"],
        "steady_window_ms_min": item["steady_window_ms_min"],
        "steady_packets_sent": steady_sent,
        "steady_packets_received": steady_received,
        "steady_delivered_pct": round(100.0 * steady_received / max(1, steady_sent), 2),
        "packets_received": received, "packets_lost": item["packets_lost"],
        "relay_ms_p99": item["relay_ms_p99"],
        "redirects": item["redirects"], "redirect_ms_p99": item["redirect_ms_p99"],
        "udp_buffer_drops_host_wide": item["udp_buffer_drops"],
        "per_shard": [{
            "shard": r["shard"], "players_at_end": r.get("players_at_end"),
            "link_thread_cpu_avg": r["link_thread_cpu_avg"],
            "game_wire_in_packets": r["game_wire_in_packets"],
            "game_wire_out_packets": r["game_wire_out_packets"],
            "game_wire_in_bytes": r["game_wire_in_bytes"],
            "game_wire_out_bytes": r["game_wire_out_bytes"],
            "game_wire_sample_windows": r["game_wire_sample_windows"]
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
        "--processes", str(getattr(args, "load_processes", 4)), "--cross", getattr(args, "cross", "mixed"), "--port", str(base_port),
        "--cfg", "CheckServerBuild=false",
        "--extra", f"--build '{BUILD}' --owner-fps 30 --follower-fps 8 --owners {args.owners}",
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
    if getattr(args, "load_processes", 4) not in LOAD_PROCESSES:
        raise ValueError("Only 4, 8 or 16 original Qt load-generator processes")
    if args.owners not in OWNER_CASES:
        raise ValueError("Only source-tested 1/3/5-owner five-player cases allowed")
    results = []
    if getattr(args, "cross", "mixed") not in CROSS_MODES:
        raise ValueError("Only original hosted code/invite/mixed join policies")
    if getattr(args, "one_only", False) and getattr(args, "three_only", False):
        raise ValueError("one-only and three-only are mutually exclusive")
    cases = ((1,) if getattr(args, "one_only", False) else
             (3,) if getattr(args, "three_only", False) else SHARD_COUNTS)
    for index, shards in enumerate(cases):
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
            result = (grade(values[0], shards, getattr(args, "load_processes", 4),
                            getattr(args, "require_directed", False),
                            args.owners) if len(values) == 1 else
                      {"quality": "MISSING_OR_DUPLICATE_GENERATOR_REPORT", "shards": shards})
        result["scope"] = "DISPOSABLE_LOOPBACK_REDIRECT_NOT_REAL_WAN_OR_DIRECT_P2P"
        result["team_size"] = SIZE
        result["load_processes"] = getattr(args, "load_processes", 4)
        result["enemy_owner_seats"] = args.owners
        result["cross_join_mode"] = getattr(args, "cross", "mixed")
        results.append(result)
        print("YT130_V117_REAL_5P_SHARDS", shards, result["quality"],
              "PLAYING", result.get("playing", "?"), "GAME_RECEIVERS",
              result.get("game_receivers", "?"), "COMPLETE_FIVE_TEAMS",
              result.get("complete_teams", "?"), "STEADY",
              result.get("steady_quality", "?"), "STEADY_PCT",
              result.get("steady_delivered_pct", "?"), "LINKING",
              result.get("linking", "?"), "LOBBY",
              result.get("lobby", "?"), "AWAIT_WELCOME",
              result.get("awaiting_welcome", "?"), "UDP_WRITE_FAILED",
              result.get("udp_write_failed", "?"), "UDP_WRITE_SHORT",
              result.get("udp_write_short", "?"), flush=True)
        if rc == 124:
            break
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, sort_keys=True) + "\n")
    if len(results) == len(cases) and all(
            r["quality"] == "FULL_GAMEPLAY_SYNTHETIC_ONLY" for r in results):
        print("YT130_V157_REQUESTED_200_PLAYER_SHARD_CASES_SYNTHETIC_HEALTH_PASS")
        return 0
    print("YT130_V117_DIAGNOSTIC_NOT_200_PLAYER_PRODUCTION_CAPACITY")
    return int(args.require_healthy)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for label in ("shadnet", "bbload", "shard-script", "output"):
        p.add_argument("--" + label, type=Path, required=True)
    p.add_argument("--timeout", type=int, default=TIMEOUT)
    p.add_argument("--one-only", action="store_true",
                   help="diagnostic only: run the single-shard case, 200 players")
    p.add_argument("--three-only", action="store_true",
                   help="diagnostic only: compare cross-shard join modes without 1-shard baseline")
    p.add_argument("--cross", choices=CROSS_MODES, default="mixed")
    p.add_argument("--load-processes", type=int, choices=LOAD_PROCESSES, default=4,
                   help="4/8/16 real Qt bbload child processes, keep 200 hunters fixed")
    p.add_argument("--owners", type=int, choices=OWNER_CASES, default=5,
                   help="how many of the five players independently own enemies (worst case 5)")
    p.add_argument("--require-directed", action="store_true",
                   help="fail closed without source-authenticated directed 5-seat flow QoS")
    p.add_argument("--require-healthy", action="store_true")
    raise SystemExit(run(p.parse_args()))
