#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-pinned BBHost v0.2.24 V19 true inbound direct/relay UDP auditing.

Apply only after V2 CSPRNG and V13 outbound route-accounting patches to
a disposable authentic BBHost checkout. No game code/data, network payload
inspection or wire changes. No server deploy and no original IP logging.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="b0098e04b889e2e70b4af84be1ce809d7af3ff95"
NET_BLOB="476fd20eb8acf1acbb5ca45cbb4e03af6b6da4a2"
NET="src/hle/net.cpp"
HEADER="src/hle/shyt_route_telemetry_v13.h"

READER=(
    '        ssize_type n = sock_recvfrom(port->fd, buf, sizeof(buf), true, &sa, &sl);\n'
    '        if (n < 0) continue;\n'
    '        if (n >= 4 && buf[0] == kRelayMagic && buf[1] == kRelayToClient && from_relay_server(sa)) {\n'
)
READER_NEW=(
    '        ssize_type n = sock_recvfrom(port->fd, buf, sizeof(buf), true, &sa, &sl);\n'
    '        if (n < 0) continue;\n'
    '        const std::uint64_t shyt_rx_wire_v19 = static_cast<std::uint64_t>(n);\n'
    '        const bool shyt_rx_relay_v19 =\n'
    '            n >= 4 && buf[0] == kRelayMagic && buf[1] == kRelayToClient && from_relay_server(sa);\n'
    '        if (shyt_rx_relay_v19) {\n'
)
ENQUEUE=(
    '            if (q->q.size() > q->hiwater) q->hiwater = q->q.size();\n'
    '#if !defined(_WIN32)\n'
    '            const std::uint64_t one = 1;\n'
    '            if (q->qfd >= 0) (void)!::write(q->qfd, &one, sizeof(one));\n'
    '#endif\n'
    '        }\n'
    '        q->cv.notify_all();\n'
)
ENQUEUE_NEW=ENQUEUE.replace(
    '        q->cv.notify_all();\n',
    '        // Count only datagrams with a real P2P header delivered to a\n'
    '        // game queue. Drop STUN/hole punching/non-game/no-header bytes\n'
    '        // from the relay-vs-direct resource accounting.\n'
    '        if (hdr) shyt_route_account_received_v19(shyt_rx_relay_v19, shyt_rx_wire_v19);\n'
    '        q->cv.notify_all();\n'
)

def replace_one(s:str,old:str,new:str)->str:
    if s.count(old)!=1:
        raise ValueError("authentic BBHost P2P receive source anchor drift")
    return s.replace(old,new,1)

def patched(source:str)->str:
    if ('shyt_route_account_success_v13(shyt_relay_framed_v13,' not in source or
            '#include "hle/shyt_route_telemetry_v13.h"' not in source or
            'if (req_len == 0) return false;' not in source):
        raise ValueError("V2 STUN + V13 outbound instrumentation required")
    if 'shyt_route_account_received_v19' in source:
        raise ValueError("V19 route RX instrumentation already installed")
    return replace_one(replace_one(source,READER,READER_NEW),ENQUEUE,ENQUEUE_NEW)

def git(root:Path,*args:str)->str:
    r=subprocess.run(["git","-C",str(root),*args],capture_output=True,text=True,timeout=15)
    if r.returncode:
        raise ValueError("pinned upstream source verification failed")
    return r.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    args=p.parse_args()
    root=args.upstream_checkout.resolve(strict=True)
    path=root/NET
    header=root/HEADER
    if (git(root,"rev-parse","HEAD")!=PIN or
            git(root,"rev-parse","HEAD:"+NET)!=NET_BLOB or
            not path.is_file() or path.is_symlink() or
            not header.is_file() or header.is_symlink() or
            "shyt_route_account_received_v19" not in header.read_text(encoding="utf-8")):
        raise ValueError("V19 authentic modified BBHost HLE source pin refused")
    source=patched(path.read_text(encoding="utf-8"))
    if args.mode=="apply":
        path.write_text(source,encoding="utf-8")
    print("SHYT_BBHOST_V19_DIRECT_RELAY_INCOMING_GAME_UDP_"+
          ("APPLIED" if args.mode=="apply" else "SOURCE_PINNED"))

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:
        raise SystemExit("SHYT_V19_SOURCE_PINNED_RX_AUDIT_REFUSED: "+type(error).__name__) from None
