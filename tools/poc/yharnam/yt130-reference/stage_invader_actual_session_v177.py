#!/usr/bin/env python3
"""V177: port source-reviewed YT #475 actual-room invader membership to pinned YT1.3.

Never equate an invader's server notice with admission to the local game room.
The upstream head has the core fix; V177 also invalidates 500ms lookup cache
on invader identity/room membership change, critical for repeated invasions.
Source+blob pinned. No compiled game, retail files, transport or saves included.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PR475 = "899e40da19d2253ebb1028cc529e49be2d90987a"
FILES = {
    "emulator/src/core/bloodborne_invasion.cpp": (
        "5c754b1958425df8fd44fd840d689418718bfed2",
        "23971ac89ed8f701844e6eb6b1fbc8323a0a9f02"),
    "emulator/src/core/bloodborne_invasion.h": (
        "67b83caf175a607c0d14c6b499df1a13b213f9f1",
        "1c29d2000c57f1f176a8b2c9e2a35a39007b03a3"),
    "emulator/src/core/bloodborne_server_world.cpp": (
        "9bce9a73fe1d9956774be5d2b7559f34a4c4edf7",
        "73151ad8fe358a1531e87e3635a3240e4ed753fe"),
    "emulator/tests/bloodborne/test_bloodborne_invasion.cpp": (
        "676a5972fb372159a6b42c594cb02cd5986ad99f",
        "d9f5137600d37f4c6490621ee1cedf771e9eb8ea"),
}
C, H, W, T = FILES
MARKER = "SHYT_V177_INVADER_ACTUAL_SESSION_NOT_SERVER_NOTICE"

def region(s: str, begin: str, end: str, what: str) -> str:
    if s.count(begin) != 1 or s.count(end) != 1 or s.index(begin) >= s.index(end):
        raise ValueError("V177 reviewed source anchor drift: " + what)
    return s[s.index(begin):s.index(end)]

def replace_once(s: str, old: str, new: str, what: str) -> str:
    if s.count(old) != 1 or new in s:
        raise ValueError("V177 pinned source conflict: " + what)
    return s.replace(old, new, 1)

def stage_sources(current: dict[str,str], original: dict[str,str],
                  upstream: dict[str,str]) -> dict[str,str]:
    if any(not current[k] or not original[k] or not upstream[k] for k in FILES):
        raise ValueError("V177 incomplete original/reviewed source")
    if any(MARKER in current[k] for k in FILES):
        raise ValueError("V177 already applied")
    # Patch the exact 1.3 baseline source, not a version with unrelated
    # v1.3.1 feature changes from #475 (which touches many other methods).
    donor_helper = region(upstream[C], "bool InvaderInSession(",
                          "\n\nInvasionJoin InvasionJoinOf(", "actual-room helper")
    if "std::ranges::any_of(session_names" not in donor_helper:
        raise ValueError("V177 reviewed helper no longer matches evidence")
    donor_decl = region(upstream[H], "// Whether the invader's game is among",
                         "\n\n// What the invader's JoinTeamSession", "declaration")
    donor_tests = region(upstream[T],
                         "// The server's \"joined\" comes",
                         "\n\n// The invader joins with", "source red-green C++ test")
    if "TheInvaderCountsOnlyOnceItIsInTheSession" not in donor_tests:
        raise ValueError("V177 upstream original test absent")
    donor_room = region(upstream[W],
                        "// The session's members for TeamJoin:",
                        "\n\nbool TickTeamJoin(bool ready)", "room membership")
    if ("now_ms - looked_ms >= 500" not in donor_room or
            "SessionMemberBoardName(member, online_ids)" not in donor_room):
        raise ValueError("V177 original head look-up behavior drift")
    # Improve upstream's 500ms static cache: if the invader changes before
    # the old time window expires (or the room returns to >2 members),
    # previously cached TRUE must NEVER be reused for a different invader.
    old_cache = """    if (invader.empty() || members != 2) {
        return members;
    }
    static s64 looked_ms = 0;
    static bool in_session = false;
    if (const s64 now_ms = SteadyMilliseconds(); now_ms - looked_ms >= 500) {
        looked_ms = now_ms;"""
    new_cache = """    static s64 looked_ms = 0;
    static bool in_session = false;
    static bool scanned = false;
    static std::string last_invader;
    if (invader.empty() || members != 2) {
        // No ghost invader must poison a later two-person co-op session.
        last_invader.clear();
        scanned = false;
        in_session = false;
        return members;
    }
    if (last_invader != invader) {
        last_invader = invader;
        scanned = false;
        in_session = false;
    }
    if (const s64 now_ms = SteadyMilliseconds();
            !scanned || now_ms - looked_ms >= 500) {
        scanned = true;
        looked_ms = now_ms;"""
    if donor_room.count(old_cache) != 1:
        raise ValueError("V177 upstream room cache anchor conflict")
    donor_room = donor_room.replace(old_cache, new_cache, 1)
    if "TeamSessionMembers(members, in_session)" not in donor_room:
        raise ValueError("V177 candidate discards original member semantics")

    out = dict(current)
    out[C] = replace_once(current[C], "\n\nInvasionJoin InvasionJoinOf(",
                          "\n\n"+donor_helper+"\n\nInvasionJoin InvasionJoinOf(",
                          "native C++ invaded member helper")
    out[H] = replace_once(current[H],
                          "\n\n// What the invader's JoinTeamSession",
                          "\n\n"+donor_decl+"\n\n// What the invader's JoinTeamSession",
                          "original native invader declaration")
    out[W] = replace_once(current[W], "\n\nbool TickTeamJoin(bool ready)",
                          "\n\n// "+MARKER+"\n"+donor_room+
                          "\n\nbool TickTeamJoin(bool ready)",
                          "room-bounded invader name scan")
    old_line = ".session_members = TeamSessionMembers(SessionMembers(), !InvaderInWorld().empty()),"
    out[W] = replace_once(out[W],old_line,
                          ".session_members = TeamJoinMembers(),",
                          "premature server-invader subtraction")
    out[T] = replace_once(current[T],
                          "\n\n// The invader joins with",
                          "\n\n"+donor_tests+"\n\n// The invader joins with",
                          "original official regression test")
    # Additional repeated-invasion five-seat contract, not in upstream:
    # the actual room's current members, not the server notice alone, win.
    extra = """
TEST(Invasion, FiveSeatAndRepeatedInvaderNotAlone) {
    using Names = std::vector<std::optional<std::string>>;
    const Names hosts = {"host", "guest2", "guest3", "guest4"};
    EXPECT_FALSE(InvaderInSession(hosts, "invader"));
    EXPECT_EQ(TeamSessionMembers(5, InvaderInSession(hosts, "invader")), 5u);
    const Names departed_invader = {"host"};
    EXPECT_FALSE(InvaderInSession(departed_invader, "old_invader"));
    EXPECT_EQ(TeamSessionMembers(2, InvaderInSession(departed_invader, "new_invader")), 2u);
    const Names in_room = {"new_invader"};
    EXPECT_TRUE(InvaderInSession(in_room, "new_invader"));
    EXPECT_EQ(TeamSessionMembers(2, InvaderInSession(in_room, "new_invader")), 1u);
}
"""
    out[T] = replace_once(out[T],
                          "\n\n// The invader joins with",
                          "\n"+extra+"\n// The invader joins with",
                          "V177 five-seat test insertion")
    if out[W].count("TeamJoinMembers()") != 2 or (
            "last_invader != invader" not in out[W]):
        raise ValueError("V177 candidate actual-room helper or invalidation incomplete")
    return out

def git(root, *args):
    return subprocess.check_output(["git","-C",str(root),*args], text=True).strip()

def run(pinned: Path, reviewed: Path):
    pinned,reviewed=pinned.resolve(strict=True),reviewed.resolve(strict=True)
    if pinned == reviewed or git(pinned,"rev-parse","HEAD")!=PIN or (
            git(reviewed,"rev-parse","HEAD")!=PR475):
        raise ValueError("V177 requires separate exact original+reviewed upstream checkouts")
    current, original, upstream = {}, {}, {}
    for path,(a,b) in FILES.items():
        if (git(pinned,"rev-parse","HEAD:"+path)!=a or
                git(reviewed,"rev-parse","HEAD:"+path)!=b):
            raise ValueError("V177 git blob mismatch at "+path)
        src,donor=pinned/path,reviewed/path
        if (not src.is_file() or src.is_symlink() or
                not donor.is_file() or donor.is_symlink()):
            raise ValueError("V177 nonregular game source path "+path)
        current[path]=src.read_text(encoding="utf-8")
        original[path]=subprocess.check_output(["git","-C",str(pinned),"show","HEAD:"+path]).decode()
        upstream[path]=donor.read_text(encoding="utf-8")
    after=stage_sources(current,original,upstream)
    for path,data in after.items():
        (pinned/path).write_text(data,encoding="utf-8")
    subprocess.run(["git","-C",str(pinned),"diff","--check"],check=True)
    print("SHYT_V177_ACTUAL_ROOM_INVADER_SOURCE_STAGED_NOT_FULL_GAMEPLAY_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pinned",type=Path,required=True)
    p.add_argument("--reviewed-pr475",type=Path,required=True)
    a=p.parse_args()
    run(a.pinned,a.reviewed_pr475)
