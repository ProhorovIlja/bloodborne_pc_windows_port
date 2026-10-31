#!/usr/bin/env python3
"""V194: compile/run the ORIGINAL YT1.3.1 C++ guest-sign selector in isolation.

Original upstream function is extracted only from a source-pinned *public*
GitHub checkout. Surrounding C++ is synthetic in-memory protobuf-like data.
This proves the 5th guest's sign computation, NOT in-game remote actor slots.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess

PIN="5d2305ee611ef1e03be39ff925f0da75c9a70393"
SOURCE="emulator/src/core/bloodborne_team.cpp"
SOURCE_SHA="a3cc741f93aecac916ddc89e484a17d8609d43a2"
START="u32 TeamGuestSign("
END="\n\nstd::vector<std::pair<std::string, std::string>> TeamLoadMembers("
MARK="SHYT_V194_ORIGINAL_YT131_GUEST_SIGN_CLIENT_CPP_PASS"

def blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def extract(text:str)->str:
    if text.count(START)!=1 or text.count(END)!=1:
        raise ValueError("V194 original guest sign function anchor drift")
    first=text.index(START)
    last=text.index(END,first)
    fn=text[first:last]
    if fn.count("constexpr u32 FirstGuestSign = 7;")!=1 or (
        fn.count("return FirstGuestSign - guest;")!=1
    ) or fn.count("return m.sign();")!=2:
        raise ValueError("V194 original C++ sign/host carry-over algorithm changed")
    return fn

HEADER = r"""
#include <cassert>
#include <algorithm>
#include <cstdint>
#include <ranges>
#include <string>
#include <vector>
using u32=std::uint32_t;
namespace bbcoop {
struct TeamMember {
    std::string id;
    u32 slot=0;
    const std::string& member() const { return id; }
    u32 sign() const { return slot; }
};
struct Team {
    std::string leader_id;
    std::vector<TeamMember> entries;
    const std::string& leader() const { return leader_id; }
    const std::vector<TeamMember>& members() const { return entries; }
};
struct LobbyState {
    bool has=false;
    Team current;
    bool has_team() const { return has; }
    const Team& team() const { return current; }
};
}
namespace Core::Bloodborne {
"""
FOOTER = r"""
} // namespace Core::Bloodborne
int main() {
    using namespace Core::Bloodborne;
    bbcoop::LobbyState none;
    assert(TeamGuestSign(none, "a", "host")==7);

    bbcoop::LobbyState lobby;
    lobby.has=true;
    lobby.current.leader_id="host";
    lobby.current.entries={{"host",0},{"a",0},{"b",0},{"c",0},{"d",0}};
    // No server-assigned sign yet: fourth remote participant must be 4.
    assert(TeamGuestSign(lobby,"a","host")==7);
    assert(TeamGuestSign(lobby,"b","host")==6);
    assert(TeamGuestSign(lobby,"c","host")==5);
    assert(TeamGuestSign(lobby,"d","host")==4);

    lobby.current.entries={{"host",0},{"a",7},{"b",6},{"c",5},{"d",4}};
    assert(TeamGuestSign(lobby,"d","host")==4);
    assert(TeamGuestSign(lobby,"b","host")==6);
    // A host may have been a guest before leader handover, preserve its slot
    // when the client receives session host=former guest.
    assert(TeamGuestSign(lobby,"missing","b")==6);
    // Old gameplay and server were both four; no sixth remote participant
    // is authorized just because the fallback arithmetic could compute 3.
    return 0;
}
"""

def harness(text:str)->str:
    return HEADER+extract(text)+"\n"+FOOTER

def run(root:Path,out:Path,compiler:str)->None:
    root=root.resolve(strict=True)
    git=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                text=True,stderr=subprocess.DEVNULL).strip()
    if git!=PIN:
        raise ValueError("V194 client proof requires exact YT 1.3.1")
    source=root/SOURCE
    if not source.is_file() or source.is_symlink():
        raise ValueError("V194 client original C++ file missing")
    original=source.read_bytes()
    if blob(original)!=SOURCE_SHA:
        raise ValueError("V194 client original C++ blob SHA changed")
    if out.exists():
        raise ValueError("V194 client test target must be a fresh path")
    out.parent.mkdir(parents=True,exist_ok=True)
    src=out.with_suffix(".cpp")
    if src.exists():
        raise ValueError("V194 client test source target must be fresh")
    src.write_text(harness(original.decode("utf-8")),encoding="utf-8")
    subprocess.run([compiler,"-std=c++20","-O2","-Wall","-Wextra",
                    "-Werror","-pedantic",str(src),"-o",str(out)],check=True)
    subprocess.run([str(out.resolve(strict=True))],check=True)
    print(MARK)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--checkout",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--compiler",default="g++")
    a=p.parse_args()
    run(a.checkout,a.out,a.compiler)
