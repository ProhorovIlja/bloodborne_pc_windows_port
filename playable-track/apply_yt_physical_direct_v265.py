#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Source-locked YT 1.3.1 physical SHDP transport integration.
Only edits a disposable owner-owned SOURCE checkout, never Fornex.
No live peer endpoints are installed: default remains server-only.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

UPSTREAM = "5d2305ee611ef1e03be39ff925f0da75c9a70393"
PATHS = {
    "emulator/src/core/libraries/network/p2p_sockets.cpp":
        "087aef46868b55320f139b3f7c4f46e5fc545347",
    "emulator/src/core/libraries/network/sockets.h":
        "5e4636ee0b4c67a849f8d45c6bf50e590f27c87e",
}
INCLUDE = '#include "core/libraries/network/server_link.h"'
INCLUDE_NEW = '#include "core/shyt_hybrid/hybrid_direct_physical_gate_v264.h"'
PRIVATE_QUEUE = "    std::deque<QueuedPacket> game_packets_queue;"
DIRECT_MEMBERS = """    // V265: independent authenticated movement packets, never SHAD.
    std::mutex shyt_direct_mutex;
    BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264 shyt_direct_gate;
    std::deque<QueuedPacket> shyt_direct_queue;
"""
PUBLIC_METHOD = """    // V265: called only by TRUSTED authenticated server-grant + Noise
    // lifecycle code, never from UDP or UI opt-in flags. Empty by default.
    bool ShytDirectAuthorizePeer(u32 ip, u16 port, s64 expires_ms) {
        std::lock_guard lock(shyt_direct_mutex);
        return shyt_direct_gate.InstallAuthenticatedEndpoint(
            {ip,port,expires_ms},P2PNowMs());
    }
    void ShytDirectRevokeAll() {
        std::lock_guard lock(shyt_direct_mutex);
        shyt_direct_gate.RevokeAll();
        std::lock_guard queue_lock(internal_mutex);
        shyt_direct_queue.clear();
    }
    int ShytDirectSend(const void* data,u32 len,u32 ip,u16 port) {
        if (!IsReady() || !data || !ip || !port ||
            len>BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::MaxWire)
            return -1;
        const auto packet=std::span<const u8>(static_cast<const u8*>(data),len);
        {
            std::lock_guard lock(shyt_direct_mutex);
            if (!shyt_direct_gate.Allows({ip,port,0},P2PNowMs(),packet))
                return -1;
        }
        sockaddr_in destination{};
        destination.sin_family=AF_INET;
        destination.sin_addr.s_addr=ip;
        destination.sin_port=port;
        // Existing physical host_socket, no virtual port, no shadNet relay.
        return Transmit(destination,{packet.begin(),packet.end()}) ?
               static_cast<int>(len) : -1;
    }
    int ShytDirectReceive(void* data,u32 len,u32* from_ip,u16* from_port) {
        if (!data || len < BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::MaxWire)
            return -1;
        std::lock_guard lock(internal_mutex);
        if (shyt_direct_queue.empty()) return -1;
        QueuedPacket packet=std::move(shyt_direct_queue.front());
        shyt_direct_queue.pop_front();
        std::memcpy(data,packet.payload.data(),packet.payload.size());
        if(from_ip) *from_ip=packet.source_addr;
        if(from_port) *from_port=packet.source_port;
        return static_cast<int>(packet.payload.size());
    }

"""
PHYSICAL_RECEIVE = """            // V265: SHDP is not SHAD! Only the separate authenticated
            // movement format may bypass original server-only policy.
            // Source IP/port and lease are pre-filtered here; V262 must
            // check AEAD/replay and the live party/world grant afterwards.
            if(datagram.size()>=8 &&
               datagram[0]==0xff && datagram[1]==0xff &&
               datagram[2]==0xff && datagram[3]==0xff &&
               std::memcmp(datagram.data()+4,"SHDP",4)==0) {
                bool allowed=false;
                {
                    std::lock_guard lock(shyt_direct_mutex);
                    allowed=shyt_direct_gate.Allows(
                        {from.sin_addr.s_addr,from.sin_port,0},
                        P2PNowMs(),datagram);
                }
                if(allowed) {
                    QueuedPacket packet{};
                    packet.source_addr=from.sin_addr.s_addr;
                    packet.source_port=from.sin_port;
                    packet.payload.assign(datagram.begin(),datagram.end());
                    std::lock_guard lock(internal_mutex);
                    if(shyt_direct_queue.size()>=
                       BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::MaxQueued)
                        shyt_direct_queue.pop_front(); // favor fresh movement
                    shyt_direct_queue.push_back(std::move(packet));
                }
                continue; // never send SHDP through original SHAD path
            }
"""
FREE_FUNCTIONS = """
// V265: deliberately no caller to authorize peers in the source overlay.
// Only server-validated party grants and a live Noise session may do that.
bool ShytDirectPeerAuthorizeV265(u32 ip,u16 port,s64 expires_ms) {
    return P2PTransport::Instance().ShytDirectAuthorizePeer(ip,port,expires_ms);
}
void ShytDirectPeerRevokeAllV265() {
    P2PTransport::Instance().ShytDirectRevokeAll();
}
int ShytDirectPeerSendV265(const void* bytes,u32 len,u32 ip,u16 port) {
    return P2PTransport::Instance().ShytDirectSend(bytes,len,ip,port);
}
int ShytDirectPeerReceiveV265(void* bytes,u32 len,u32* ip,u16* port) {
    return P2PTransport::Instance().ShytDirectReceive(bytes,len,ip,port);
}
"""
DECLARATIONS = """// SHDP movement only: authenticated and server-authorized direct UDP
// sent on the SAME physical socket, never used for ordinary SHAD frames.
// Source overlay has no authorization caller; closed until integrated.
bool ShytDirectPeerAuthorizeV265(u32 ip,u16 port,s64 expires_ms);
void ShytDirectPeerRevokeAllV265();
int ShytDirectPeerSendV265(const void* bytes,u32 len,u32 ip,u16 port);
int ShytDirectPeerReceiveV265(void* bytes,u32 len,u32* ip,u16* port);
"""


def replace_once(text: str, needle: str, repl: str) -> str:
    if text.count(needle)!=1:
        raise ValueError("pinned source anchor mismatch")
    return text.replace(needle,repl,1)


def rev(root: Path,*args: str) -> str:
    r=subprocess.run(["git","-C",str(root),*args],capture_output=True,
                     text=True,timeout=10)
    if r.returncode: raise ValueError("not a pinned Git source checkout")
    return r.stdout.strip()


def prepare(root: Path) -> tuple[dict[Path,str],Path]:
    if root.is_symlink() or not root.is_dir() or rev(root,"rev-parse","HEAD")!=UPSTREAM:
        raise ValueError("wrong original YT 1.3.1 source")
    originals={}
    for relative,sha in PATHS.items():
        path=root/relative
        if path.is_symlink() or not path.is_file() or rev(root,"hash-object",relative)!=sha:
            raise ValueError("upstream physical source changed")
        originals[path]=path.read_text(encoding="utf-8")
    source=next(p for p in originals if p.name=="p2p_sockets.cpp")
    header=next(p for p in originals if p.name=="sockets.h")
    c=originals[source]
    c=replace_once(c,INCLUDE,INCLUDE+"\n"+INCLUDE_NEW)
    c=replace_once(c,"enum class InternalChannel {",
        "enum class InternalChannel {\n    ShytDirectMovement,")
    c=replace_once(c,"    int SendInternal(const void* data,",
        PUBLIC_METHOD+"    int SendInternal(const void* data,")
    c=replace_once(c,"        case InternalChannel::Signaling:\n",
        "        case InternalChannel::ShytDirectMovement:\n"
        "            return shyt_direct_queue;\n"
        "        case InternalChannel::Signaling:\n")
    c=replace_once(c,
        "            if (const auto server = LinkServer();\n"
        "                server.addr_nbo == from.sin_addr.s_addr",
        PHYSICAL_RECEIVE+
        "            if (const auto server = LinkServer();\n"
        "                server.addr_nbo == from.sin_addr.s_addr")
    c=replace_once(c,PRIVATE_QUEUE,PRIVATE_QUEUE+"\n"+DIRECT_MEMBERS)
    c=replace_once(c,"int P2PCoopSendTo(const void* data,",
        FREE_FUNCTIONS+"\nint P2PCoopSendTo(const void* data,")
    h=replace_once(originals[header],
        "int P2PCoopSendTo(const void* data,",
        DECLARATIONS+"\nint P2PCoopSendTo(const void* data,")
    target=root/"emulator/src/core/shyt_hybrid/hybrid_direct_physical_gate_v264.h"
    return {source:c,header:h},target


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    opt=p.parse_args()
    root=opt.upstream_checkout.resolve(strict=True)
    patches,target=prepare(root)
    src=Path(__file__).resolve().parent/"hybrid_direct_physical_gate_v264.h"
    if src.is_symlink() or not src.is_file():
        raise ValueError("no trusted peer transport header")
    if opt.mode=="apply":
        if target.exists() or target.is_symlink():
            raise ValueError("refusing existing direct transport header")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(src.read_bytes())
        for path,new_text in patches.items():
            path.write_text(new_text,encoding="utf-8")
    print("SHYT_V265_PINNED_YT_PHYSICAL_SHDP_SOURCE_"+opt.mode.upper()+
          "_PASS_DEFAULT_SERVER_ONLY")


if __name__=="__main__":
    try: main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as err:
        raise SystemExit("V265 fail-closed: "+type(err).__name__) from None
