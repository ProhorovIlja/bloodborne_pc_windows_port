#!/usr/bin/env python3
"""Compile and EXECUTE only exact patched original YT1.3 C++ invader/session code.

Mocks only independent host-provided session observation API; never modifies
real game or fakes the actual C++ algorithms under test.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

MARKER="SHYT_V177_INVADER_ACTUAL_SESSION_NOT_SERVER_NOTICE"

def exact_region(s, start, end, desc):
    if s.count(start)!=1 or s.count(end)!=1 or s.index(start)>=s.index(end):
        raise ValueError("V177 actual original C++ source drift: "+desc)
    return s[s.index(start):s.index(end)]

def harness(original: Path) -> str:
    core=original/"emulator/src/core"
    inv=(core/"bloodborne_invasion.cpp").read_text(encoding="utf-8")
    world=(core/"bloodborne_server_world.cpp").read_text(encoding="utf-8")
    if MARKER not in world:
        raise ValueError("Missing V177 modified original YT1.3 game code")
    member=exact_region(inv,"size_t TeamSessionMembers(",
                        "\n\nInvasionJoin InvasionJoinOf(","original policy helper+reviewed source")
    actual=exact_region(world,"size_t TeamJoinMembers()",
                        "\n\nbool TickTeamJoin(bool ready)", "actual original game room hook")
    if ("bool InvaderInSession(" not in member or
            "std::ranges::any_of" not in member or
            "last_invader != invader" not in actual or
            "SessionMemberBoardName(member, online_ids)" not in actual):
        raise ValueError("V177 exact game C++ room-membership algorithm missing")
    return r"""
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <optional>
#include <ranges>
#include <span>
#include <string>
#include <string_view>
#include <vector>
using u64=std::uint64_t;
using s64=std::int64_t;
static size_t simulated_room_members=0;
static std::string announced_invader;
static std::vector<std::optional<std::string>> simulated_board_names;
static s64 now_ms=0;
size_t SessionMembers(){return simulated_room_members;}
std::string InvaderInWorld(){return announced_invader;}
s64 SteadyMilliseconds(){return now_ms;}
std::string OnlineIdOfBoardMember(const std::string &v){return v;}
std::vector<u64> OtherSessionMembers() {
    std::vector<u64> result;
    for (size_t i=0;i<simulated_board_names.size();++i)result.push_back(i);
    return result;
}
std::optional<std::string> SessionMemberBoardName(
        u64 member,const std::vector<std::string>&) {
    return simulated_board_names.at(member);
}
""" + member + "\n" + actual + r"""
int main(){
    // Three/five hunters, no server notice: preserve every genuine member.
    simulated_room_members=5; now_ms=1;
    announced_invader="hostileA"; simulated_board_names={"host","guest2","guest3","guest4"};
    assert(TeamJoinMembers()==5);
    // Host+guest room; announcement is early, invader not present.
    simulated_room_members=2; now_ms=2;
    simulated_board_names={"host"};
    assert(TeamJoinMembers()==2);
    // Invader becomes an actual member; only then subtract.
    now_ms=502; simulated_board_names={"hostileA"};
    assert(TeamJoinMembers()==1);
    // New server-announced invader arrives within OLD 500ms cached tick:
    // falsely retaining A's cached in_session=true would kick the guest.
    now_ms=503; announced_invader="hostileB"; simulated_board_names={"host"};
    assert(TeamJoinMembers()==2);
    now_ms=1003; simulated_board_names={"hostileB"};
    assert(TeamJoinMembers()==1);
    // Leaving larger co-op rooms and re-entering 2-player resets cache.
    simulated_room_members=4; now_ms=1004;
    assert(TeamJoinMembers()==4);
    simulated_room_members=2; now_ms=1005; simulated_board_names={"host"};
    assert(TeamJoinMembers()==2);
    announced_invader.clear(); now_ms=1006;
    assert(TeamJoinMembers()==2);
    announced_invader="hostileC"; now_ms=1007;
    assert(TeamJoinMembers()==2);
    // Unknown board name must not be interpreted as the invader.
    now_ms=1507; simulated_board_names={std::nullopt};
    assert(TeamJoinMembers()==2);
    return 0;
}
"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pinned",type=Path,required=True)
    p.add_argument("--compiler",default="g++")
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    target=a.out
    target.parent.mkdir(parents=True,exist_ok=True)
    target.with_suffix(".cpp").write_text(harness(a.pinned),encoding="utf-8")
    subprocess.run([a.compiler,"-std=c++20","-O2","-Wall","-Wextra",
                    "-Werror","-pedantic",str(target.with_suffix(".cpp")),
                    "-o",str(target)],check=True)
    subprocess.run([str(target.resolve())],check=True)
    print("SHYT_V177_ORIGINAL_NATIVE_INVADER_CXX_REPEATED_IDENTITY_AND_5_SEAT_PASS")
if __name__=="__main__":main()
