#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V324: pin a bounded same-socket STUN discovery seam into original YT.

Apply AFTER the V265/V318 authenticated physical source overlay in
a disposable upstream checkout. This discovers an UNTRUSTED advisory
reflexive IPv4 address; it never authorizes a gameplay sender/packet.
No STUN server specified => strict default off. It is NOT ICE/NAT
hole-punching, STUN discovery alone cannot prove mutual reachability.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="5d2305ee611ef1e03be39ff925f0da75c9a70393"
ORIGINAL_BLOB="087aef46868b55320f139b3f7c4f46e5fc545347"
REL="emulator/src/core/libraries/network/p2p_sockets.cpp"
HEADER="emulator/src/core/shyt_hybrid/yt_reflexive_stun_v321.h"

def once(s:str,a:str,b:str)->str:
    if s.count(a)!=1:
        raise ValueError("original pinned physical source seam changed")
    return s.replace(a,b,1)

def modified(s:str)->str:
    s=once(s,
        '#include "core/shyt_hybrid/yt_client_authority_pin_v318.h"',
        '#include "core/shyt_hybrid/yt_client_authority_pin_v318.h"\n'
        '#include "core/shyt_hybrid/yt_reflexive_stun_v321.h"')
    s=once(s,
        "    std::mutex verified_direct_mutex;",
        """    std::mutex verified_direct_mutex;
    // V324: STUN is ONLY address discovery; it cannot grant the
    // SHDP physical gate, identity, Noise keys or sender consent.
    std::mutex reflexive_mutex;
    BloodborneCoop::SHYTHybrid::ReflexiveStunV321::Binding reflexive_probe;
    std::optional<BloodborneCoop::SHYTHybrid::ReflexiveStunV321::Endpoint>
        reflexive_mapped;
    s64 last_reflexive_start_ms = -30000;
    s64 reflexive_mapped_ms = -1;""")
    methods="""    // V324: the *original physical host_socket* does the STUN request,
    // so the resulting NAT mapping is from the same UDP port the game's
    // other traffic uses. It is untrusted advisory candidate metadata.
    // No implicit server selection, no P2P grant, no gameplay send.
    bool BeginReflexiveDiscovery(u32 ip_nbo, u16 port_nbo) {
        namespace Stun=BloodborneCoop::SHYTHybrid::ReflexiveStunV321;
        if(!LinkWelcomed() || !IsReady() || !ip_nbo || !port_nbo)
            return false;
        const auto server=LinkServer();
        if(ip_nbo==server.addr_nbo && port_nbo==server.port_nbo)
            return false;
        std::array<u8,12> txid{};
        if(!Stun::FreshTransactionIdV323(txid))
            return false;
        const s64 now=P2PNowMs();
        std::lock_guard lock(reflexive_mutex);
        // At most one 20-byte request every 15 seconds, no background
        // STUN flood/retry loop; existing authoritative relay unaffected.
        if(now<0 || now<last_reflexive_start_ms ||
           now-last_reflexive_start_ms<15000)
            return false;
        reflexive_probe.Revoke();
        reflexive_mapped.reset();
        const Stun::Endpoint target{ip_nbo,port_nbo};
        const auto request=reflexive_probe.Start(target,txid,now);
        if(!request)return false;
        last_reflexive_start_ms=now;
        sockaddr_in dest{};
        dest.sin_family=AF_INET;
        dest.sin_addr.s_addr=ip_nbo;
        dest.sin_port=port_nbo;
        if(!Transmit(dest,std::vector<u8>(request->begin(),request->end()))) {
            reflexive_probe.Revoke();
            return false;
        }
        return true;
    }

    bool TakeReflexiveDiscovery(u32* ip_nbo,u16* port_nbo) {
        if(!ip_nbo || !port_nbo || !LinkWelcomed() || !IsReady())
            return false;
        std::lock_guard lock(reflexive_mutex);
        // V326: NAT mappings may change. Never report a stale address.
        const s64 now=P2PNowMs();
        if(!reflexive_mapped || reflexive_mapped_ms<0 ||
           now<reflexive_mapped_ms ||
           now-reflexive_mapped_ms>10000) {
            reflexive_mapped.reset();
            return false;
        }
        *ip_nbo=reflexive_mapped->address_nbo;
        *port_nbo=reflexive_mapped->port_nbo;
        reflexive_mapped.reset();
        reflexive_mapped_ms=-1;
        return true;
    }

    void RevokeReflexiveDiscovery() {
        std::lock_guard lock(reflexive_mutex);
        reflexive_probe.Revoke();
        reflexive_mapped.reset();
        last_reflexive_start_ms=-30000;
        reflexive_mapped_ms=-1;
    }

"""
    s=once(s,
        "    int SendVerifiedMovement(const void* data,u32 len,u32 ip,u16 port) {",
        methods+"    int SendVerifiedMovement(const void* data,u32 len,u32 ip,u16 port) {")
    s=once(s,
        "        verified_direct_queue.clear();\n    }\n\n",
        "        verified_direct_queue.clear();\n"
        "        // STUN-derived information must not survive a link revoke.\n"
        "        RevokeReflexiveDiscovery();\n    }\n\n")
    demux="""            // V324: only the exact source and transaction ID of our
            // outstanding STUN request can yield an untrusted candidate.
            // Ordinary shadNet/SHDP frames are NEVER treated as STUN.
            if(datagram.size()>=8 && datagram[0]==1 && datagram[1]==1 &&
               std::equal(
                  BloodborneCoop::SHYTHybrid::ReflexiveStunV321::Binding::Cookie.begin(),
                  BloodborneCoop::SHYTHybrid::ReflexiveStunV321::Binding::Cookie.end(),
                  datagram.begin()+4)) {
                std::lock_guard lock(reflexive_mutex);
                namespace Stun=BloodborneCoop::SHYTHybrid::ReflexiveStunV321;
                const Stun::Endpoint from_stun{
                    from.sin_addr.s_addr,from.sin_port};
                if(auto address=reflexive_probe.Take(
                       from_stun,datagram,P2PNowMs())) {
                    reflexive_mapped=address;
                    reflexive_mapped_ms=P2PNowMs();
                    continue;
                }
            }
"""
    s=once(s,
        "            if (const auto server = LinkServer();",
        demux+"            if (const auto server = LinkServer();")
    api="""// V324: advisory reflexive address only, NOT authorization to send
// to any peer. The original secure SHDP socket remains grant-gated.
bool P2PBeginReflexiveDiscovery(u32 ip_nbo,u16 port_nbo) {
    return P2PTransport::Instance().BeginReflexiveDiscovery(ip_nbo,port_nbo);
}
bool P2PTakeReflexiveDiscovery(u32* ip_nbo,u16* port_nbo) {
    return P2PTransport::Instance().TakeReflexiveDiscovery(ip_nbo,port_nbo);
}

"""
    s=once(s,
        "bool P2PInstallVerifiedMovementEndpoint(",
        api+"bool P2PInstallVerifiedMovementEndpoint(")
    return s

def git(root:Path,*args:str)->str:
    a=subprocess.run(["git","-C",str(root),*args],capture_output=True,
                     text=True,timeout=12)
    if a.returncode:raise ValueError("not pinned original YT")
    return a.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    args=p.parse_args()
    root=args.upstream_checkout.resolve(strict=True)
    dst=root/REL
    if (git(root,"rev-parse","HEAD")!=PIN or
        git(root,"rev-parse","HEAD:"+REL)!=ORIGINAL_BLOB or
        not dst.is_file() or dst.is_symlink()):
        raise ValueError("original game UDP socket SHA drift")
    original=dst.read_text(encoding="utf-8")
    if ("Hybrid::MatchesLauncherAuthorityV318(" not in original or
        "V277: check + enqueue MUST be atomic" not in original):
        raise ValueError("missing authenticated V265/V318 source overlay")
    converted=modified(original)
    if args.mode=="apply":
        destination=root/HEADER
        home=Path(__file__).resolve().parent/"yt_reflexive_stun_v321.h"
        if (destination.exists() or destination.is_symlink() or
            destination.parent.is_symlink() or not destination.parent.is_dir() or
            not home.is_file() or home.is_symlink()):
            raise ValueError("already applied or missing private source overlay")
        destination.write_bytes(home.read_bytes())
        dst.write_text(converted,encoding="utf-8")
        print("SHYT_V324_ORIGINAL_GAME_SAME_SOCKET_STUN_ADVISORY_APPLIED_DEFAULT_OFF")
    else:
        print("SHYT_V324_ORIGINAL_GAME_STUN_ANCHORS_PASS")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise SystemExit("V324 refused physical STUN overlay: "+
                         type(exc).__name__) from None
