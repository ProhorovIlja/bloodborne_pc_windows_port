#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V313 source-locked original YT LinkServer operator signer overlay.

Apply ONLY after V288 and V292 in disposable original YT v1.3.1
checkout. It does not enable P2P by default, deploy to Fornex, or
publish any private seed. A seed path must be explicitly configured
by the Linux operator, and clients must pin the distinct EdDSA key.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="5d2305ee611ef1e03be39ff925f0da75c9a70393"
REL="server/src/link_server.cpp"
BLOB="1878a08eae4fce402c0106a8813d061fb23a5b80"

def once(data:str,old:str,new:str)->str:
    if data.count(old)!=1:
        raise ValueError("unpinned original LinkServer source drift")
    return data.replace(old,new,1)

def patch(original:str)->str:
    modified=once(
        original,
        '#include "link_server.h"',
        '#include "link_server.h"\n'
        '#include "shyt_hybrid/yt_operator_peer_signer_v313.h"')
    return once(
        modified,
        '    m_world.RequireAuthenticatedIdentity();',
        '    m_world.RequireAuthenticatedIdentity();\n'
        '    // V313: explicit Linux seed file only. No operator seed means\n'
        '    // zero server-issued peer grants and full server relay only.\n'
        '    (void)BloodborneCoop::SHYTHybrid::OperatorPeerSignerV313::\n'
        '        InstallFromEnvironment(m_world);')

def git(root:Path,*args:str)->str:
    response=subprocess.run(
        ["git","-C",str(root),*args],
        capture_output=True,text=True,timeout=12)
    if response.returncode:
        raise ValueError("untrusted original YT checkout")
    return response.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    args=p.parse_args()
    root=args.upstream_checkout.resolve(strict=True)
    candidate=root/REL
    if (git(root,"rev-parse","HEAD")!=PIN or
            not candidate.is_file() or candidate.is_symlink() or
            git(root,"hash-object",REL)!=BLOB):
        raise ValueError("unpinned original LinkServer source")
    changed=patch(candidate.read_text(encoding="utf-8"))
    directory=root/"server/src/shyt_hybrid"
    header=directory/"yt_operator_peer_signer_v313.h"
    prerequisite=directory/"yt_server_direct_signer_v310.h"
    if args.mode=="apply":
        if (directory.is_symlink() or not directory.is_dir() or
                header.exists() or header.is_symlink() or
                not prerequisite.is_file() or prerequisite.is_symlink()):
            raise ValueError("V292 source overlay missing or target already modified")
        source=Path(__file__).resolve().parent/"yt_operator_peer_signer_v313.h"
        if not source.is_file() or source.is_symlink():
            raise ValueError("missing operator seed-file source")
        header.write_bytes(source.read_bytes())
        candidate.write_text(changed,encoding="utf-8")
        print("SHYT_V313_ORIGINAL_LINKSERVER_OPT_IN_SIGNER_APPLIED_DEFAULT_OFF")
    else:
        print("SHYT_V313_ORIGINAL_LINKSERVER_SIGNER_ANCHORS_PASS")

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise SystemExit("V313 refused unsafe LinkServer overlay: "+
                         type(exc).__name__) from None
