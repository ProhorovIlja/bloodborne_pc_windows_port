#!/usr/bin/env python3
"""Yharnam Together 1.3.1/CLS offline *privacy-preserving* join log triage.

Reads local text logs from each PC/instance. Never changes saves or games.
Only outputs aggregate, anonymized task IDs and event counts; no player names,
network addresses, message bodies, or raw log line content. This is evidence
triage, NOT proof that an in-game character was visibly rendered.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from collections import defaultdict
from pathlib import Path

MAX_LOG_BYTES = 32 * 1024 * 1024
REQUEST = re.compile(
    r"Bloodborne party trip: asked a member still joining for its data "
    r"\(request (\d+), task (0x[0-9a-fA-F]+) step=(-?\d+) "
    r"flags=(0x[0-9a-fA-F]+) slot=(none|-?\d+)\)"
)
CREATE = re.compile(
    r"Bloodborne party trip: a member that was still joining sent its data; "
    r"creating its character \(task (0x[0-9a-fA-F]+) step=(-?\d+) "
    r"flags=(0x[0-9a-fA-F]+) slot=(-?\d+)\)"
)
REBUILD = re.compile(
    r"Bloodborne party trip: rebuilt the join task of a member "
    r"kind=(-?\d+) task=(0x[0-9a-fA-F]+) slot known=(true|false|0|1) "
    r"flags=(0x[0-9a-fA-F]+)"
)
TASK_SNAPSHOT = re.compile(
    r"\[kind=(-?\d+) slot=(\d+) flags=(0x[0-9a-fA-F]+) "
    r"step=(-?\d+) identity=(0x[0-9a-fA-F]+)\]"
)
SENSITIVE_OUTPUT_NOTICE = (
    "Only anonymized event summaries. Local log files are not uploaded. "
    "Requests or task-step changes do NOT confirm actor existence. "
    "Silence, missing lines or non-Debug builds are not proof of health."
)

def read_log(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("log must be an existing regular file, not a link")
    if path.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("log too large for bounded offline triage (32 MiB)")
    return path.read_text(encoding="utf-8", errors="replace").splitlines()

def audit_lines(lines: list[str]) -> dict:
    events = defaultdict(int)
    identities: dict[str, str] = {}
    task_data: dict[str, dict] = {}
    last_snapshots: list[dict] = []
    # Raw IDs never appear outside this function.
    def alias(task: str) -> str:
        if task not in identities:
            identities[task] = f"task_{len(identities)+1}"
        return identities[task]

    for index, line in enumerate(lines, 1):
        if "Bloodborne join tasks:" in line:
            events["join_task_snapshots"] += 1
            snapshots = TASK_SNAPSHOT.findall(line)
            # Keep bounded and intentionally OMIT raw identity. The identity
            # is only used for grouping inside the process if needed later.
            last_snapshots = [
                {"kind": int(kind), "slot": int(slot),
                 "flags_hex": flags.lower(), "step": int(step)}
                for kind, slot, flags, step, _identity in snapshots[:8]
            ]
        m = REQUEST.search(line)
        if m:
            seq, task, step, flags, slot = m.groups()
            state = task_data.setdefault(alias(task), {
                "requests": 0, "created": False,
                "rebuild_events": 0, "last_line": 0,
            })
            state["requests"] += 1
            state["last_request_number"] = int(seq)
            state["last_step_before_request"] = int(step)
            state["last_slot_before_request"] = None if slot == "none" else int(slot)
            state["last_line"] = index
            events["member_data_requests"] += 1
            continue
        m = CREATE.search(line)
        if m:
            task, step, flags, slot = m.groups()
            state = task_data.setdefault(alias(task), {
                "requests": 0, "created": False,
                "rebuild_events": 0, "last_line": 0,
            })
            state["created"] = True
            state["last_step_before_create"] = int(step)
            state["last_line"] = index
            events["member_data_create_intent"] += 1
            continue
        m = REBUILD.search(line)
        if m:
            kind, task, known, flags = m.groups()
            state = task_data.setdefault(alias(task), {
                "requests": 0, "created": False,
                "rebuild_events": 0, "last_line": 0,
            })
            state["rebuild_events"] += 1
            state["kind"] = int(kind)
            state["last_line"] = index
            events["remote_task_rebuilds"] += 1
        if "a member with no join task yet is left to the" in line:
            events["no_join_task_left_to_game"] += 1
        if "Bloodborne party UI: guest role" in line and "named as role" in line:
            events["role_name_fix_applied"] += 1
        if "?ActionEventInfo?" in line:
            events["placeholder_text_mentioned_in_log"] += 1
    # We refuse to label as a bug if a task got a create intent in its log,
    # but even that intent does not prove a visible remote actor.
    stalled = sorted(key for key, state in task_data.items()
                     if state["requests"] >= 2 and not state["created"])
    incomplete = sorted(key for key, state in task_data.items()
                        if state["requests"] > 0 and not state["created"])
    if stalled:
        status = "INVESTIGATE_REPEATED_MEMBER_DATA_REQUESTS"
    elif events["join_task_snapshots"] or any(
        events[k] for k in ("member_data_requests", "remote_task_rebuilds")
    ):
        status = "JOIN_LOGS_PRESENT_RUNTIME_VISIBILITY_UNVERIFIED"
    else:
        status = "INSUFFICIENT_JOIN_DIAGNOSTICS"
    return {
        "status": status,
        "lines_processed": len(lines),
        "events": dict(sorted(events.items())),
        "anonymized_tasks": dict(sorted(task_data.items())),
        "last_join_snapshot": last_snapshots,
        "repeated_request_no_create_tasks": stalled,
        "request_no_create_tasks": incomplete,
        "notice": SENSITIVE_OUTPUT_NOTICE,
    }

def self_test() -> None:
    early = (
        "[12:00] Bloodborne party trip: rebuilt the join task of a member "
        "kind=1 task=0xABC slot known=true flags=0x04 (it was still joining)\n"
        "[12:01] Bloodborne join tasks: [kind=1 slot=0 flags=0x04 "
        "step=3 identity=0x123]\n"
        "[12:02] Bloodborne party trip: asked a member still joining for "
        "its data (request 1, task 0xABC step=3 flags=0x4 slot=0)\n"
        "[12:08] Bloodborne party trip: asked a member still joining for "
        "its data (request 2, task 0xABC step=3 flags=0x4 slot=0)\n"
    )
    stalled = audit_lines(early.splitlines())
    assert stalled["status"] == "INVESTIGATE_REPEATED_MEMBER_DATA_REQUESTS"
    assert stalled["repeated_request_no_create_tasks"] == ["task_1"]
    assert stalled["last_join_snapshot"][0]["step"] == 3
    assert "0xABC" not in json.dumps(stalled)
    assert "0x123" not in json.dumps(stalled)
    after = early + (
        "[12:09] Bloodborne party trip: a member that was still joining "
        "sent its data; creating its character (task 0xABC step=3 flags=0x4 slot=0)\n"
    )
    resolved = audit_lines(after.splitlines())
    assert resolved["status"] == "JOIN_LOGS_PRESENT_RUNTIME_VISIBILITY_UNVERIFIED"
    assert resolved["request_no_create_tasks"] == []
    assert resolved["events"]["member_data_create_intent"] == 1
    assert audit_lines(["totally unrelated line"])["status"] == "INSUFFICIENT_JOIN_DIAGNOSTICS"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "private.txt"
        path.write_text(after)
        assert read_log(path) == after.splitlines()
    print("YT_JOIN_LOG_TRIAGE_SELFTEST_PASS")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="*", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="exit 2 if repeated requests lack any create intent")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.logs:
        parser.error("pass one or more local Yharnam Together Debug log files")
    reports = []
    try:
        for i, path in enumerate(args.logs):
            report = audit_lines(read_log(path))
            report["client"] = f"client_{i+1}"
            reports.append(report)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"clients": reports}, indent=2, ensure_ascii=False))
    if args.strict and any(
        r["status"] == "INVESTIGATE_REPEATED_MEMBER_DATA_REQUESTS"
        for r in reports
    ):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
