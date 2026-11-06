#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V432 offline, original YT 1.4.0 signed-in OnlineID layout source gate.

Uses only source files pinned by Git blob ID. Never reads, copies or
uploads decrypted EBOOT, network packet contents or player account data.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

ORIGINAL = (
    ("emulator/src/core/bloodborne_patches.cpp",
     "5e698a5bcd714f41ab40782a0838d63055d84d62",
     ("std::string OnlineIdOfMember(u64 member_id) {",
      "const u64 identity = member_id >= 0x10000 ? ReadValue<u64>(member_id, 0) : 0;",
      "identity + 0x36, 17, MemoryProt::CpuRead",
      "NpOnlineIdAt({reinterpret_cast<const u8*>(identity + 0x36), 17})")),
    ("emulator/src/core/bloodborne_party.cpp",
     "54637fea5b6f15d8410f68b1f8ba70d2344127dd",
     ("std::optional<std::string> NpOnlineIdAt(std::span<const u8> bytes)",
      "bytes.first(std::min<std::size_t>(bytes.size(), 17))",
      "if (byte == 0)",
      "return id.size() >= 3 ? std::optional{id} : std::nullopt;",
      "if (!std::isalnum(byte) && byte != '-' && byte != '_')")),
    ("server/src/bloodborne_world.cpp",
     "071a9fe301ebbdb6fa81f73ddf11943fd31ec0e9",
     ("std::string AuthenticatedMember(const QByteArray& online_id)",
      "return online_id.toHex().toStdString();")),
)
def verify_source(root:Path, filename:str, expected:str, tokens:tuple[str,...]) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("pinned original YT source checkout missing")
    obj=subprocess.check_output(
        ["git","-C",str(root),"rev-parse",f"HEAD:{filename}"],
        text=True,timeout=10).strip()
    if obj!=expected:
        raise ValueError("original YT Git blob drift: "+filename)
    path=root/filename
    if not path.is_file() or path.is_symlink() or path.stat().st_size>900000:
        raise ValueError("source file size or path rejected")
    source=path.read_text(encoding="utf-8")
    if any(token not in source for token in tokens):
        raise ValueError("original game member extraction ABI changed")
def main(yt:Path, header:Path, session:Path)->None:
    for args in ORIGINAL:
        verify_source(yt,*args)
    if header.is_symlink() or not header.is_file() or header.stat().st_size>15000:
        raise ValueError("V432 source header invalid")
    if session.is_symlink() or not session.is_file() or session.stat().st_size>100000:
        raise ValueError("V432 server adapter invalid")
    head=header.read_text(encoding="utf-8")
    adapter=session.read_text(encoding="utf-8")
    must=(
        "SHYT_V432_SCE_NP_ID_BYTES=17",
        "SHYT_V432_MEMBER_PTR_BYTES=8",
        "SHYT_V432_ID_OFFSET=0x36",
        "SHYT_V432_MIN_ONLINE_ID=3",
        "SHYT_V432_MAX_ONLINE_ID=16",
        "SHYT_V432_TRAFFIC_ALLOWED=0",
        "strcmp(loaded_sha,SHYT_V427_EXPECTED_EBOOT_SHA256)!=0",
        "read(game_member_addr,ptr,sizeof(ptr))!=0",
        "read(identity+SHYT_V432_ID_OFFSET,id,sizeof(id))!=0",
        "out->canonical_member_hex[2u*i]=lower_hex[id[i]>>4u]",
    )
    if any(token not in head for token in must):
        raise ValueError("V432 bounded source-backed guest identity gate drift")
    if ('shyt_yt_v432_resolve(' not in adapter or
        'shyt_yt_server_peer_evidence_v431(' not in adapter or
        'out->can_route_game=0u;' not in adapter or
        'out->can_arm_game_queue=0u;' not in adapter):
        raise ValueError("V432 game->authenticated roster adapter missing/unsafe")
    for forbidden in ("api->write(","api->patch(","api->hook(",
                      "api->hook2(","sendto(","recvfrom("):
        if forbidden in head:
            raise ValueError("V432 helper must never mutate guest or send network data")
    print("SHYT_V432_YT_140_NP_ID_AND_SIGNED_IN_SERVER_HEX_SOURCE_CONTRACT_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--yt",type=Path,required=True)
    p.add_argument("--header",type=Path,required=True)
    p.add_argument("--session",type=Path,required=True)
    args=p.parse_args()
    try:
        main(args.yt,args.header,args.session)
    except (ValueError,OSError,UnicodeError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as err:
        raise SystemExit("SHYT_V432_GUEST_MEMBER_SOURCE_CONTRACT_REFUSED: "+
                         type(err).__name__) from None
