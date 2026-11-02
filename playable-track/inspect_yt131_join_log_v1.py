#!/usr/bin/env python3
"""Safe offline triage of real YT 1.3.1 member-data join logs.

Runs on the owner's PC; never sends a log or game/saved data to GitHub.
Only prints bounded counters, never actual raw lines, names, addresses or IPs.
A missing CREATE line is a clue, not proof a hunter was invisible.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

MAX_LOG_SIZE = 64 * 1024 * 1024
MAX_LINES = 500_000
MAX_TASKS = 10_000

REQUEST = re.compile(
    r"asked a member still joining for its data \(request (\d+), "
    r"task (0x[0-9a-fA-F]+) step=(-?\d+) flags=0x[0-9a-fA-F]+ slot=(none|\d+)\)"
)
CREATED = re.compile(
    r"a member that was still joining sent its data; creating its character "
    r"\(task (0x[0-9a-fA-F]+) step=(-?\d+) flags=0x[0-9a-fA-F]+ slot=(-?\d+)\)"
)
WAITING = re.compile(r"a remote player kind=\d+ still joining at step -?\d+")
JOIN_TASKS = re.compile(r"Bloodborne join tasks:")
NO_JOIN_TASK = "a member with no join task yet is left to the game's own join"
RECREATE = "re-creating remote player kind="


def inspect_lines(lines: object) -> dict:
    # Internal pointer is retained only as an in-memory matching key.
    # Never return or print pointer values.
    pending: dict[str, int] = {}
    requested = created = creates_without_request = 0
    missing_slot = waiting = no_task = recreate = 0
    duplicate_requests = task_snapshots = 0
    line_count = 0
    truncated = False
    for line in lines:
        line_count += 1
        if line_count > MAX_LINES or len(line) > 16384:
            truncated = True
            break
        match = REQUEST.search(line)
        if match:
            requested += 1
            task = match.group(2)
            if task in pending:
                duplicate_requests += 1
            if len(pending) >= MAX_TASKS and task not in pending:
                truncated = True
                break
            pending[task] = int(match.group(1))
            if match.group(4) == "none":
                missing_slot += 1
            continue
        match = CREATED.search(line)
        if match:
            created += 1
            if pending.pop(match.group(1), None) is None:
                creates_without_request += 1
            continue
        if WAITING.search(line):
            waiting += 1
        if JOIN_TASKS.search(line):
            task_snapshots += 1
        if NO_JOIN_TASK in line:
            no_task += 1
        if RECREATE in line:
            recreate += 1
    return {
        "status": "INCOMPLETE_INPUT" if truncated else
                  ("NEEDS_JOIN_REVIEW" if pending or missing_slot else
                   "NO_UNRESOLVED_REQUEST_IN_CAPTURE"),
        "lines_scanned": min(line_count, MAX_LINES),
        "member_data_requests": requested,
        "member_data_create_events": created,
        "outstanding_task_requests_at_log_end": len(pending),
        "repeated_requests": duplicate_requests,
        "requests_without_remote_slot": missing_slot,
        "create_events_without_prior_request_in_capture": creates_without_request,
        "waiting_remote_task_events": waiting,
        "missing_join_task_events": no_task,
        "recreate_remote_player_events": recreate,
        "join_task_change_snapshots": task_snapshots,
        "captured_entire_input": not truncated,
        "interpretation": (
            "This is diagnostic correlation only. Game actor visibility, "
            "session membership, world/map identity and actual network delivery "
            "cannot be inferred from these log messages alone. An outstanding "
            "request can simply mean the log ended before completion."
        ),
    }


def selftest() -> None:
    req = ("[Debug] Bloodborne party trip: asked a member still joining "
           "for its data (request 1, task 0xabc step=3 flags=0x4 slot=1)")
    done = ("[Debug] Bloodborne party trip: a member that was still joining "
            "sent its data; creating its character "
            "(task 0xabc step=3 flags=0x5 slot=1)")
    ok = inspect_lines([req, done])
    assert ok["member_data_requests"] == 1
    assert ok["member_data_create_events"] == 1
    assert ok["outstanding_task_requests_at_log_end"] == 0
    assert ok["status"] == "NO_UNRESOLVED_REQUEST_IN_CAPTURE"
    open_task = inspect_lines([req, req.replace("request 1", "request 2")])
    assert open_task["status"] == "NEEDS_JOIN_REVIEW"
    assert open_task["repeated_requests"] == 1
    assert open_task["outstanding_task_requests_at_log_end"] == 1
    missing = inspect_lines([req.replace("slot=1", "slot=none"), done])
    assert missing["requests_without_remote_slot"] == 1
    assert missing["status"] == "NEEDS_JOIN_REVIEW"
    assert inspect_lines([done])["create_events_without_prior_request_in_capture"] == 1
    assert inspect_lines(["a" * 16385])["status"] == "INCOMPLETE_INPUT"
    # Log metadata must not leak task pointers or names.
    assert "0xabc" not in json.dumps(ok)
    print("SHYT_YT131_JOIN_TRACE_OFFLINE_PRIVACY_SELFTEST_PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", nargs="?", type=Path, help="local trimmed YT debug log")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        selftest()
        return
    if args.log is None:
        parser.error("give a local log or use --self-test")
    if args.log.is_symlink() or not args.log.is_file():
        parser.error("log missing or symbolic link")
    if args.log.stat().st_size > MAX_LOG_SIZE:
        parser.error("file exceeds 64 MiB limit; trim a local log first")
    with args.log.open("r", encoding="utf-8", errors="replace") as handle:
        report = inspect_lines(handle)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
