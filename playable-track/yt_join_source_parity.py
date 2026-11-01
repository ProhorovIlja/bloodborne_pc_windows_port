#!/usr/bin/env python3
"""Offline Yharnam Together 1.3.1 vs CLS merge *source* regression gate.

Compare actual checked-out sources, never game binaries. It finds absent
functional guards and tests, not runtime defects. Reads no secrets or saves.
Standard library only. No outbound traffic. Private source stays on the PC.
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_SIZE = 8 * 1024 * 1024
SOURCE_FILES = {
    "party": "emulator/src/core/bloodborne_party.cpp",
    "rules": "emulator/src/core/bloodborne_party_rules.cpp",
    "join": "emulator/src/core/bloodborne_join.cpp",
    "boards": "emulator/src/core/bloodborne_boards.cpp",
    "ui_test": "emulator/tests/bloodborne/test_bloodborne_ui_polish.cpp",
    "member_test": "emulator/tests/bloodborne/test_bloodborne_member_data.cpp",
    "multi_test": "emulator/tests/bloodborne/test_bloodborne_three_players.cpp",
}
# These are API / test symbols, not bundled game bytes.
CHECKS: tuple[tuple[str, str, str, str], ...] = (
    ("role_name_fix", "party", r"\bNameUnnamedGuestRole\s*\(", "blocking"),
    ("role_name_called", "rules", r"\bNameUnnamedGuestRole\s*\(\s*roles\s*\)", "blocking"),
    ("ui_polish_tick", "rules", r"\bPolishMultiplayerUi\s*\(", "blocking"),
    ("role_name_regression", "ui_test",
     r"\bNamesTheGuestRoleTheGameLeftUnnamed\b", "blocking"),
    ("remote_join_task_rebuild", "join", r"\bRebuildJoinTask\s*\(", "blocking"),
    ("saved_remote_tasks", "join", r"\bsaved_join_tasks\b", "blocking"),
    ("member_data_wait_map", "join", r"\bjoins_waiting_for_data\b", "blocking"),
    ("member_data_completion", "boards", r"\bFinishWaitingJoins\s*\(", "blocking"),
    ("member_data_request", "boards", r"\bSendMemberDataRequest\s*\(", "blocking"),
    ("wait_for_request_before_create", "member_test",
     r"\bDataSeenBeforeTheRequestIsNotTrusted\b", "blocking"),
    ("joining_during_trip_test", "multi_test",
     r"\bAGuestStillJoiningAtATripIsRebuiltAsAFreshJoin\b", "blocking"),
    ("member_data_retries", "member_test",
     r"\bAnUnansweredRequestIsRepeated\b", "blocking"),
)
BROAD_PRESENCE = re.compile(
    r"\bSomeoneElseStands\s*\(\s*view\.board\.members\s*,\s*"
    r"view\.member\s*,\s*PlayingMap\s*\(\s*\)\s*\)"
)

@dataclass(frozen=True)
class SourceStatus:
    key: str
    found: bool
    severity: str
    reason: str

def analyze(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("source root must be a real local directory")
    texts: dict[str, str | None] = {}
    for key, subpath in SOURCE_FILES.items():
        path = root / subpath
        # No implicit external reads through symlinks anywhere in the tree.
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent):
            raise ValueError("symlink in source path: " + subpath)
        if not path.is_file():
            texts[key] = None
            continue
        if path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError("oversized source: " + subpath)
        texts[key] = path.read_text(encoding="utf-8", errors="replace")
    checks = []
    for name, file_key, pattern, severity in CHECKS:
        content = texts[file_key]
        found = content is not None and re.search(pattern, content) is not None
        checks.append(SourceStatus(name, bool(found), severity,
                                   "present" if found else (
                                       "source file absent" if content is None
                                       else "required symbol/test absent")))
    boards = texts["boards"] or ""
    broad_presence = BROAD_PRESENCE.search(boards) is not None
    return {
        "status": ("BLOCKED_SOURCE_PARITY" if any(
            not item.found and item.severity == "blocking" for item in checks)
            else "SOURCE_GATES_PRESENT_RUNTIME_UNVERIFIED"),
        "files_checked": len(SOURCE_FILES),
        "checks": [
            {"id": x.key, "passed": x.found, "severity": x.severity,
             "reason": x.reason} for x in checks
        ],
        "review_flags": ([
            {"id": "multi_guest_presence_is_teamwide_not_member_specific",
             "severity": "review",
             "explanation": (
                 "FinishWaitingJoins reads SomeoneElseStands for ANY other standing "
                 "player on the local map before processing each waiting member. "
                 "In a split-map 3-5-person group, that test may be true for a "
                 "different guest than the one awaiting data. Review against real "
                 "game traces, member identity binding and upstream five-player "
                 "PRs before modifying the handshake. This is not a proven bug."
             )}
        ] if broad_presence else []),
        "limits": (
            "Static source-presence check, not build/rig proof. Does not verify "
            "function reachability, runtime hook setup, correctness of merge, "
            "or whether actors visibly render. Source contents stay private."
        ),
    }

def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for sub in SOURCE_FILES.values():
            path = root / sub
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("// minimal synthetic fixture\n", encoding="utf-8")
        assert analyze(root)["status"] == "BLOCKED_SOURCE_PARITY"
        for name, file_key, pattern, _ in CHECKS:
            content = (root / SOURCE_FILES[file_key]).read_text()
            # Generate innocuous strings containing the known public symbols.
            symbol = {
                "role_name_called": "NameUnnamedGuestRole(roles)",
            }.get(name, pattern.strip(r"\b").split(r"\s*")[0])
            if name == "role_name_fix":
                symbol = "NameUnnamedGuestRole("
            elif name == "ui_polish_tick":
                symbol = "PolishMultiplayerUi("
            elif name == "remote_join_task_rebuild":
                symbol = "RebuildJoinTask("
            elif name == "member_data_completion":
                symbol = "FinishWaitingJoins("
            elif name == "member_data_request":
                symbol = "SendMemberDataRequest("
            (root / SOURCE_FILES[file_key]).write_text(
                content + " " + symbol + " \n", encoding="utf-8")
        healthy = analyze(root)
        assert healthy["status"] == "SOURCE_GATES_PRESENT_RUNTIME_UNVERIFIED", healthy
        board = root / SOURCE_FILES["boards"]
        board.write_text(board.read_text() +
                         " SomeoneElseStands(view.board.members, view.member, PlayingMap());\n")
        assert len(analyze(root)["review_flags"]) == 1
        rule = root / SOURCE_FILES["rules"]
        rule.write_text(rule.read_text().replace("NameUnnamedGuestRole(roles)", ""))
        assert analyze(root)["status"] == "BLOCKED_SOURCE_PARITY"
    print("YT_JOIN_SOURCE_PARITY_SELFTEST_PASS")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", type=Path,
                        help="directory with emulator/src/core and emulator/tests")
    parser.add_argument("--strict", action="store_true",
                        help="exit code 2 if a required source symbol/test is missing")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.source is None:
        parser.error("pass path to LOCAL checked-out Yharnam Together source")
    try:
        result = analyze(args.source)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.strict and result["status"] == "BLOCKED_SOURCE_PARITY":
        raise SystemExit(2)

if __name__ == "__main__":
    main()
