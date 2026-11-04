#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V13: source-locked BBHost HLE P2P route counters, off by default.

Run AFTER the exact v0.2.24/v0.2.25 STUN CSPRNG V2 patch on a disposable checkout.
No game files, wire protocol changes, IP logging, payload interception,
server updates or gameplay hooks.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess

PIN="b0098e04b889e2e70b4af84be1ce809d7af3ff95"
PIN_V025="7dbe6f60f33fff45ea1bcbf6c6e61a6b35466e13"
ALLOWED_RELEASE_HEADS=(PIN,PIN_V025)  # explicit source pins only
ORIGINAL_NET_BLOB="476fd20eb8acf1acbb5ca45cbb4e03af6b6da4a2"
REL="src/hle/net.cpp"
NAME="shyt_route_telemetry_v13.h"
INCLUDE='#include "net/stun.h"\n'
SEND='    if (sock.p2p && relay_target(to->addr, to->port, token, &stun_sa)) {\n'
POST='    if (n < 0) return sock_errno() == EAGAIN ? net_again() : net_fail();\n    if (sock.queue) {\n'

def replace_once(source:str,from_:str,to:str)->str:
    if source.count(from_)!=1:
        raise ValueError("original BBHost P2P source anchor changed")
    return source.replace(from_,to,1)

def patched(source:str)->str:
    if 'if (req_len == 0) return false;' not in source:
        raise ValueError("BBHost V2 protected STUN source patch missing")
    source=replace_once(source,INCLUDE,INCLUDE+'#include "hle/'+NAME+'"\n')
    source=replace_once(source,SEND,
        '    const bool shyt_relay_framed_v13 = sock.p2p &&\n'
        '        relay_target(to->addr, to->port, token, &stun_sa);\n'
        '    if (shyt_relay_framed_v13) {\n')
    source=replace_once(source,POST,
        '    if (n < 0) return sock_errno() == EAGAIN ? net_again() : net_fail();\n'
        '    if (sock.p2p) {\n'
        '        shyt_route_account_success_v13(shyt_relay_framed_v13,\n'
        '            static_cast<std::uint64_t>(n) +\n'
        '                (shyt_relay_framed_v13 ? kRelayHeader : 0u));\n'
        '    }\n'
        '    if (sock.queue) {\n')
    return source

def git(root:Path,*args:str)->str:
    r=subprocess.run(["git","-C",str(root),*args],capture_output=True,text=True,timeout=15)
    if r.returncode:raise ValueError("source-pinned BBHost repository unavailable")
    return r.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    a=p.parse_args()
    root=a.upstream_checkout.resolve(strict=True)
    net=root/REL
    header=root/"src/hle"/NAME
    source=Path(__file__).with_name(NAME)
    if (git(root,"rev-parse","HEAD") not in ALLOWED_RELEASE_HEADS or
        git(root,"rev-parse","HEAD:"+REL)!=ORIGINAL_NET_BLOB or
        not net.is_file() or net.is_symlink() or
        not source.is_file() or source.is_symlink() or
        header.exists() or header.is_symlink()):
        raise ValueError("BBHost source or telemetry header pin rejected")
    target=patched(net.read_text(encoding="utf-8"))
    if a.mode=="apply":
        shutil.copyfile(source,header)
        net.write_text(target,encoding="utf-8")
    print("SHYT_BBHOST_V13_ROUTE_AUDIT_SOURCE_"+("APPLIED" if a.mode=="apply" else "PINNED"))

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as err:
        raise SystemExit("SHYT_BBHOST_V13_PINNED_ROUTE_AUDIT_REFUSED: "+
                         type(err).__name__) from None
