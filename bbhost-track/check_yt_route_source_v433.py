#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Original YT v1.4.0 server routing oracle, source-identity CI gate.

Compile the actual source in V433 tests, not a handcrafted fixture.
No game binaries, user identity, UDP server or production path required.
"""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path

FILES={
    "server/coop/packet_routes.h":"f732c87cd0a030751f5ed23dfa225e98bb8ffc5c",
    "server/coop/game_link.h":"5029581251bfe5decf562c19a10bdd079150cdad",
    "server/coop/coop_types.h":"457f7c7126868d81052fb492dea772ffbf6a18b1",
}
def check(yt:Path,header:Path,test:Path)->None:
    for path,blob in FILES.items():
        actual=subprocess.check_output(
            ["git","-C",str(yt),"rev-parse",f"HEAD:{path}"],
            text=True,timeout=10).strip()
        if actual!=blob:
            raise ValueError("original YT route/reliability source drift")
        source=yt/path
        if source.is_symlink() or not source.is_file() or source.stat().st_size>85000:
            raise ValueError("original YT file missing or oversized")
    for path in [header,test]:
        if path.is_symlink() or not path.is_file() or path.stat().st_size>30000:
            raise ValueError("local checked source file missing or oversized")
    h=header.read_text(encoding="utf-8")
    t=test.read_text(encoding="utf-8")
    required_h=[
        "DroppedNativeChannel=68u",
        "return Assessment{policy,!policy && reliable,false,false};",
        "static bool CoOpPolicy(",
        "static bool HostilePolicy(",
        "if(e.sender_map && e.target_map && e.sender_map!=e.target_map)",
        "return !from_visitor && same_map &&",
        "case 0x27u:case 0x39u:",
    ]
    if any(x not in h for x in required_h):
        raise ValueError("V433 candidate route gating unexpectedly changed")
    required_t=[
        '#include "coop/packet_routes.h"',
        "BloodborneCoop::RoutesNativePacket(",
        "BloodborneCoop::RoutesHostilePacket(",
        "BloodborneCoop::RouteGameFrame(",
        "BloodborneCoop::EncodeGameFrame(",
        "BloodborneCoop::DecodeGameFrame(",
    ]
    if any(x not in t for x in required_t):
        raise ValueError("V433 actual YT routing oracle tests missing")
    if "api->hook2(" in h or "sendto(" in h or "api->write(" in h:
        raise ValueError("V433 readonly route policy must not send data")
    print("SHYT_V433_YT_140_AUTHENTIC_COOP_INVASION_ROUTING_ORACLE_SOURCE_PASS")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--yt",type=Path,required=True)
    parser.add_argument("--header",type=Path,required=True)
    parser.add_argument("--test",type=Path,required=True)
    args=parser.parse_args()
    try:
        check(args.yt,args.header,args.test)
    except (ValueError,OSError,UnicodeError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        raise SystemExit("SHYT_V433_SOURCE_ROUTE_POLICY_REFUSED: "+
                         type(exc).__name__) from None
