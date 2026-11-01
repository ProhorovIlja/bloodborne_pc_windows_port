#!/usr/bin/env python3
"""Source-pinned, offline candidate fix for YT's cross-member join presence test.

Only writes to an explicitly requested CLEAN upstream source checkout.
No game image/save/launcher/production server is modified. Not shipping!
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PIN = "5d2305ee611ef1e03be39ff925f0da75c9a70393"
REL = Path("emulator/src/core/bloodborne_boards.cpp")
OLD = '''    const bool here = view.Fresh() && !view.member.empty() &&
                      SomeoneElseStands(view.board.members, view.member, PlayingMap());
    const s64 now = SteadyMilliseconds();
'''
NEW = '''    // A second, unrelated teammate standing on this map must not cause
    // a WAITING third member to receive a CreateCharacterStep.
    // Use the existing memoized identity resolver, not a fresh per-tick
    // scan of every identity's memory.
    std::vector<std::string> online_ids;
    if (view.Fresh()) {
        for (const MemberVitals& member : view.board.members) {
            const std::string id = OnlineIdOfBoardMember(member.member);
            if (!id.empty()) {
                online_ids.push_back(id);
            }
        }
    }
    const u32 here_map = PlayingMap();
    const s64 now = SteadyMilliseconds();
'''
OLD_TICK = '''        switch (waiting->second.Tick(now, here, parts ? ReadValue<u8>(parts, 0) : 0)) {
'''
NEW_TICK = '''        const std::optional<std::string> target =
            view.Fresh() && !online_ids.empty()
                ? SessionMemberBoardName(member_id, online_ids)
                : std::nullopt;
        const bool target_here =
            target && !view.member.empty() && *target != view.member &&
            here_map != 0 &&
            std::ranges::any_of(view.board.members, [&](const MemberVitals& member) {
                return member.member == *target && member.map == here_map &&
                       member.vital == Vital::Up;
            });
        switch (waiting->second.Tick(now, target_here,
                                     parts ? ReadValue<u8>(parts, 0) : 0)) {
'''


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   text=True).strip()


def check(root: Path, *, apply: bool) -> None:
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("wrong YT source commit; explicitly re-review upstream changes")
    if git(root, "status", "--porcelain"):
        raise ValueError("upstream checkout contains uncommitted work")
    path = root / REL
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 512_000:
        raise ValueError("unexpected upstream source file")
    source = path.read_text(encoding="utf-8")
    if source.count(OLD) != 1 or source.count(OLD_TICK) != 1:
        raise ValueError("upstream original join guards changed; manual review required")
    changed = source.replace(OLD, NEW).replace(OLD_TICK, NEW_TICK)
    if changed.count("target_here") != 2:
        raise ValueError("unexpected patched source")
    if apply:
        path.write_text(changed, encoding="utf-8")
        print("SHYT_JOIN_TARGET_SOURCE_CANDIDATE_APPLIED_NOT_PLAYTESTED")
    else:
        print("SHYT_JOIN_TARGET_SOURCE_CANDIDATE_MATCH_PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--apply", action="store_true",
                        help="modifies only the pinned clean upstream source file")
    args = parser.parse_args()
    try:
        check(args.checkout, apply=args.apply)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
