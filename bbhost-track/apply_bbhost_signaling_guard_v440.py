#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sandbox-only hardening candidate for authentic BBHost PR217 signaling.

V440 rejects signals not addressed to the receiving local OnlineID, malformed
padding, unknown kinds and invalid packet shapes BEFORE PR217 mutates
Transport. It does NOT authenticate the claimed sender, endpoint, room or
gameplay authority; the original unkeyed UDP control still needs a server-
bound identity/capability and a separate safety review before promotion.
Never applies to production 0.2.24 or to any unstated PR217 commit.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess

PR217="271f68ef8811b873c7e0cc31f98a92f8deb7e999"
SOURCE_BLOB="4668783f279c9e6c65e48b3c31c956c29056bf61"
NET_P2P_BLOB="ed846bfc67919a7d492c98b9b5d866e56b35916b"
HEADER='#include "hle/net_p2p.h"'
ENTRY='''void hle_np_signaling_control(const std::uint8_t* data, std::size_t len, std::uint32_t addr, std::uint16_t port) {
    if (len < kPacketLen) return;'''
PATCH='''void hle_np_signaling_control(const std::uint8_t* data, std::size_t len, std::uint32_t addr, std::uint16_t port) {
    // V440 is a wire/recipient gate, NOT proof of sender identity or
    // authorization to establish/direct or relay a game connection.
    if (!data || SeamlessHunt::BbhostSignalTargetV440::Inspect(
                     {data,len},net::online_id()) !=
                     SeamlessHunt::BbhostSignalTargetV440::Reason::Accepted)
        return;'''

def git(root:Path,*args:str)->str:
    return subprocess.check_output(
        ["git","-C",str(root),*args],text=True,timeout=10).strip()

def main(host:Path,header:Path,mode:str)->None:
    if host.is_symlink() or not host.is_dir():
        raise ValueError("PR217 candidate checkout unavailable")
    if git(host,"rev-parse","HEAD")!=PR217:
        raise ValueError("wrong BBHost PR217 source commit")
    for path,blob in (
        ("src/hle/np_signaling.cpp",SOURCE_BLOB),
        ("src/hle/net_p2p.h",NET_P2P_BLOB)):
        item=host/path
        if item.is_symlink() or not item.is_file() or item.stat().st_size>90000 or \
           git(host,"rev-parse","HEAD:"+path)!=blob or \
           git(host,"hash-object",path)!=blob:
            raise ValueError("unverified PR217 original signaling source")
    if header.is_symlink() or not header.is_file() or header.stat().st_size>14000:
        raise ValueError("missing V440 bounded signal guard")
    content=header.read_text(encoding="utf-8")
    for token in ("WireLen=46u","MagicLen=4u","ToAt=22u",
                  "NotPeerProof","if(to!=local)return Reason::WrongRecipient;"):
        if token not in content:
            raise ValueError("V440 original signaling wire/recipient guard drift")
    source_path=host/"src/hle/np_signaling.cpp"
    original=source_path.read_text(encoding="utf-8")
    if original.count(HEADER)!=1 or original.count(ENTRY)!=1 or \
       original.count("std::memcpy(pkt + kToAt, t.online_id.data()")!=1:
        raise ValueError("PR217 signaling send/receive boundary changed")
    if mode=="check":
        print("SHYT_V440_PR217_SIGNAL_DESTINATION_SOURCE_ONLY_CANDIDATE_PINNED")
        return
    local_dest=host/"src/hle/shyt_bbhost_signal_target_v440.h"
    if local_dest.exists() or local_dest.is_symlink():
        raise ValueError("refuse overwriting existing signaling code")
    source_path.write_text(
        original.replace(HEADER,HEADER+
           '\n#include "hle/shyt_bbhost_signal_target_v440.h"').replace(
           ENTRY,PATCH),encoding="utf-8")
    shutil.copyfile(header,local_dest)
    assert original!=source_path.read_text(encoding="utf-8")
    print("SHYT_V440_PR217_SIGNAL_TARGET_FAIL_CLOSED_SANDBOX_SOURCE_PATCH_APPLIED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--guard",type=Path,required=True)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    a=p.parse_args()
    try:main(a.upstream_checkout,a.guard,a.mode)
    except (ValueError,OSError,UnicodeError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as e:
        raise SystemExit("SHYT_V440_SIGNAL_SOURCE_GUARD_REFUSED: "+
                         type(e).__name__) from None
