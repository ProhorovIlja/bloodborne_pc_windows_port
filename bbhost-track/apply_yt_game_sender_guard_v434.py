#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Create an opt-in, reproducible 1.4.0 original YT server patch candidate.

Never touches the user's production Fornex, a live checkout or game data.
Produces an isolated Qt server source overlay, NOT a deployed service.
The original server's decoded SHAD GameFrame.sender is untrusted text,
whereas sender.online_id comes from the server-authenticated Link.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess

ORIGINAL_CPP="dd6d0fe7de39facde2f8c7ab448642834b747cc9"
ORIGINAL_FRAME="5029581251bfe5decf562c19a10bdd079150cdad"
INCLUDE='#include "coop/packet_routes.h"'
# The released Hub bypasses game-frame inspection entirely when the
# packet-routes callback has not been installed. V435 closes only the
# native GameFrame path; unrelated SHLK and SHAD control data unchanged.
ORIGINAL_ROUTE_GATE='''    if (!packet_routes || frame.size() < GameFrameAt || frame.mid(4, 4) != "SHAD" ||
        static_cast<quint8>(frame[8]) != BloodborneCoop::GamePacketsType) {
        return frame;
    }'''
V435_ROUTE_GATE='''    // V435: never forward an uninspected native GameFrame when
    // route policy is absent. Other kinds of server messages unchanged.
    if (frame.size() < GameFrameAt || frame.mid(4, 4) != "SHAD" ||
        static_cast<quint8>(frame[8]) != BloodborneCoop::GamePacketsType) {
        return frame;
    }
    if (!packet_routes) {
        return std::nullopt;
    }'''
ADMISSION='''    if (!game_frame) {
        return std::nullopt;
    }
    const size_t refused = BloodborneCoop::RouteGameFrame('''
GUARD='''    // V434: GameFrame.sender is client-controlled and controls the
    // receiver's GameLinkPeer key; source link.online_id was signed in
    // on this authenticated (original YT Noise-NK) Hub connection.
    // Reject wrong sender / malformed native frame BEFORE routing or
    // forwarding. Never infer P2P or owner/map authorization from it.
    if (!game_frame ||
        SeamlessHunt::YtGameSenderBindingV434::Inspect(
            *game_frame,
            std::string_view(sender.online_id.constData(),
                             static_cast<std::size_t>(sender.online_id.size())))
           != SeamlessHunt::YtGameSenderBindingV434::Status::Accepted) {
        return std::nullopt;
    }
    const size_t refused = BloodborneCoop::RouteGameFrame('''

def blob(yt:Path,path:str)->str:
    return subprocess.check_output(["git","-C",str(yt),"rev-parse",
                                    "HEAD:"+path],timeout=10,text=True).strip()
def patch(yt:Path,header:Path,out:Path)->None:
    if not yt.is_dir() or yt.is_symlink() or not header.is_file() or header.is_symlink():
        raise ValueError("missing pinned YT repo or guard header")
    if blob(yt,"server/src/server_link.cpp")!=ORIGINAL_CPP or \
       blob(yt,"server/coop/game_link.h")!=ORIGINAL_FRAME:
        raise ValueError("original server link/Gamelink source drift")
    src=yt/"server/src/server_link.cpp"
    if src.is_symlink() or src.stat().st_size>100000 or header.stat().st_size>15000:
        raise ValueError("oversized/missing original or candidate source")
    s=src.read_text(encoding="utf-8")
    if (s.count(INCLUDE)!=1 or s.count(ADMISSION)!=1 or
        s.count(ORIGINAL_ROUTE_GATE)!=1):
        raise ValueError("cannot identify unique original YT route boundaries")
    if "YtGameSenderBindingV434" not in header.read_text(encoding="utf-8"):
        raise ValueError("missing authenticated sender check implementation")
    replaced=(s.replace(INCLUDE,INCLUDE+'\n#include "coop/shyt_yt_game_sender_binding_v434.h"')
               .replace(ORIGINAL_ROUTE_GATE,V435_ROUTE_GATE)
               .replace(ADMISSION,GUARD))
    if (replaced.count("YtGameSenderBindingV434::Inspect(")!=1 or
        replaced.count("sender.online_id.constData()")!=1 or
        replaced.count("if (!packet_routes) {")!=1):
        raise ValueError("not a unique authenticated link ID guard")
    if out.is_symlink() or (out.exists() and not out.is_dir()):
        raise ValueError("output path cannot be a file or symlink")
    source_dest=out/"server/src/server_link.cpp"
    header_dest=out/"server/coop/shyt_yt_game_sender_binding_v434.h"
    source_dest.parent.mkdir(parents=True,exist_ok=True)
    header_dest.parent.mkdir(parents=True,exist_ok=True)
    if source_dest.exists() or header_dest.exists():
        raise ValueError("refuse overwrite of candidate files")
    source_dest.write_text(replaced,encoding="utf-8")
    shutil.copyfile(header,header_dest)
    # Explicitly keep candidate source outside the original checkout.
    assert src.read_text(encoding="utf-8")==s
    print("SHYT_V435_PINNED_ORIGINAL_YT_SERVER_GAME_SENDER_AND_ABSENT_ROUTE_GUARD_CANDIDATE_PASS")
    print("Source overlay only, not a compiled Qt server or production install.")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--yt",type=Path,required=True)
    ap.add_argument("--header",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    try:patch(args.yt,args.header,args.out)
    except (OSError,ValueError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        raise SystemExit("SHYT_V434_SERVER_SOURCE_PATCH_REFUSED: "+
                         type(exc).__name__) from None
