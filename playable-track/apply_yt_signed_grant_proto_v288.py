#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V288: exact upstream YT v1.3.1 authenticated Coop-stream P2P schema.

This modifies ONLY original server/coop/coop.proto in a disposable
pinned source checkout. Both real YT client/server protobuf builds
must use the same patched schema. Merely adding a protobuf definition
does not issue a signed grant or enable Direct P2P.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="5d2305ee611ef1e03be39ff925f0da75c9a70393"
BLOB="f0055dce7cb09ff8bd382cff883b588abcf1b4a8"
RELATIVE="server/coop/coop.proto"
ANCHOR="        DuelState duel_state = 50;\n    }\n}\n"
NEW_FIELDS="""        // V288 additive, disabled until server-side feature negotiation.
        DirectPeerRequest direct_peer_request = 51;
        DirectPeerGrant direct_peer_grant = 52;
"""
MESSAGES="""
// V288: game -> its already-authenticated shadNet reliable Coop stream.
// The game may REQUEST a peer. It cannot self-authorize an endpoint,
// party/instance/world epoch, public IP or other players' membership.
// The server must derive those facts from its live authoritative state.
// Requests without an enabled server issuer are ignored or refused.
message DirectPeerRequest {
    string recipient = 1;
    bytes noise_static_public_key = 2; // exactly 32 authenticated bytes
    bytes request_nonce = 3;            // exactly 16 fresh CSPRNG bytes
}

// shadNet -> game over the same authenticated Coop stream (never peer UDP).
// The EdDSA verifier key MUST come from this already pinned server link
// or from independently pinned launcher settings, never from peer UDP.
// The 512-byte maximum grant includes the 64-byte EdDSA signature.
// This schema is not a substitute for V279/V280/V285 signature checks.
message DirectPeerGrant {
    bytes signed_grant = 1;
    bytes authority_public_key = 2; // exactly 32 bytes, server-bound
}
"""

def patch(source:str)->str:
    if source.count(ANCHOR)!=1:
        raise ValueError("original Coop oneof layout changed")
    if "message DirectPeerGrant {" in source or "direct_peer_request = 51" in source:
        raise ValueError("already extended or unknown schema")
    # Insert messages before Envelope so code generators see exact typed
    # fields. No existing numbers are modified or reused.
    intro="message Envelope {\n"
    if source.count(intro)!=1: raise ValueError("missing original Envelope")
    source=source.replace(intro,MESSAGES+"\n"+intro,1)
    return source.replace(ANCHOR,
        "        DuelState duel_state = 50;\n"+NEW_FIELDS+"    }\n}\n",1)

def git(root:Path,*args:str)->str:
    result=subprocess.run(["git","-C",str(root),*args],
                          capture_output=True,text=True,timeout=12)
    if result.returncode:
        raise ValueError("not the pinned upstream source checkout")
    return result.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    args=p.parse_args()
    root=args.upstream_checkout.resolve(strict=True)
    target=root/RELATIVE
    if (not target.is_file() or target.is_symlink() or
        git(root,"rev-parse","HEAD")!=PIN or
        git(root,"hash-object",RELATIVE)!=BLOB):
        raise ValueError("not the original pinned shadNet proto schema")
    output=patch(target.read_text(encoding="utf-8"))
    if args.mode=="apply":
        target.write_text(output,encoding="utf-8")
        print("SHYT_V288_PINNED_COOP_PROTO_EXTENSION_APPLIED_DEFAULT_OFF")
    else:
        print("SHYT_V288_PINNED_COOP_PROTO_ANCHORS_PASS")

if __name__=="__main__":
    try: main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as err:
        raise SystemExit("V288 refused unsafe YT schema patch: "+
                         type(err).__name__) from None
