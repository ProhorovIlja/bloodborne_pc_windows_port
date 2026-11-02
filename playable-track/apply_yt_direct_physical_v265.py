#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V265: pinned YT 1.3.1 real physical UDP socket source overlay.

Run AFTER V256 in a disposable cloned source checkout. Source-locked:
refuses unknown upstream commit / modified p2p_sockets.cpp. The new
SHDP path uses the EXISTING physical socket and a distinct 128-item
queue. It is DENIED unless a genuine already-authorized V262 inbound
peer session/lease explicitly installs an endpoint. Does not change
server-only SHAD ingress or global peer default.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PINNED_SHA="5d2305ee611ef1e03be39ff925f0da75c9a70393"
PINNED_BLOB="087aef46868b55320f139b3f7c4f46e5fc545347"
RELATIVE="emulator/src/core/libraries/network/p2p_sockets.cpp"
HEADER="core/shyt_hybrid/yt_direct_physical_api_v264.h"
SOURCE_HEADER='#include "sockets.h"'

def replace_once(source:str,needle:str,change:str)->str:
    if source.count(needle)!=1:
        raise ValueError("YT upstream source mismatch; no physical UDP patch")
    return source.replace(needle,change,1)

def patch(source:str)->str:
    src=replace_once(source,SOURCE_HEADER,
        SOURCE_HEADER+'\n#include "core/shyt_hybrid/yt_direct_physical_api_v264.h"\n'
        '#include "core/shyt_hybrid/hybrid_direct_physical_gate_v264.h"')
    src=replace_once(src,
        "    GamePackets,\n    // Our messages with the server itself",
        "    GamePackets,\n    VerifiedDirectMovement, // SHDP only, NEVER SHAD\n"
        "    // Our messages with the server itself")
    src=replace_once(src,
        "        case InternalChannel::GamePackets:\n"
        "            return game_packets_queue;",
        "        case InternalChannel::GamePackets:\n"
        "            return game_packets_queue;\n"
        "        case InternalChannel::VerifiedDirectMovement:\n"
        "            return verified_direct_queue;")
    src=replace_once(src,
        "        // Nobody may read the co-op queue (no party): keep only the newest frames.",
        "        // V265: bounded distinct encrypted peer-only SHDP queue.\n"
        "        if (channel == InternalChannel::VerifiedDirectMovement &&\n"
        "            queue.size() >= BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::MaxQueued)\n"
        "            queue.pop_front();\n"
        "        // Nobody may read the co-op queue (no party): keep only the newest frames.")
    src=replace_once(src,
        "    std::deque<QueuedPacket> game_packets_queue;",
        "    std::deque<QueuedPacket> game_packets_queue;\n"
        "    std::deque<QueuedPacket> verified_direct_queue;\n"
        "    std::mutex verified_direct_mutex;\n"
        "    BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264 verified_direct_gate;")

    public_methods="""    // V265: ONLY a server-authenticated, key-pinned, epoch-valid V262
    // game receiver can approve an endpoint. This socket method never
    // interprets a remote UDP address as identity or proof of admission.
    bool InstallVerifiedMovementEndpoint(
        const BloodborneCoop::SHYTHybrid::VerifiedPeerIngressV262& proof) {
        namespace Hybrid = BloodborneCoop::SHYTHybrid;
        if (!LinkWelcomed() || !proof.session ||
            !proof.endpoint_proved_by_authenticated_handshake ||
            !proof.session->MatchesIncomingGrantV262(
                proof.lease, proof.identity, proof.endpoints) ||
            Hybrid::ChooseNativePacketCarrier(
                0x06, proof.endpoints, proof.lease) != Hybrid::Carrier::DirectPeer)
            return false;
        const auto [address,port]=proof.approved_endpoint;
        const auto server=LinkServer();
        if (!address || !port ||
            (address==server.addr_nbo && port==server.port_nbo))
            return false;
        std::lock_guard guard(verified_direct_mutex);
        return verified_direct_gate.InstallAuthenticatedEndpoint(
            {address,port,proof.lease.lease_expiry_ms},proof.lease.now_ms);
    }

    // This is a separate authenticated wire route, not SendInternal's
    // shadNet SHAD port. Never send plaintext or unknown peer datagrams.
    int SendVerifiedMovement(const void* data,u32 len,u32 ip,u16 port) {
        if (!data || !ip || !port || !LinkWelcomed() || !IsReady() ||
            len < BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::WireHeader.size()+32+24+1 ||
            len > BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::MaxWire)
            return -1;
        const auto bytes=std::span<const u8>{static_cast<const u8*>(data),len};
        const auto now=P2PNowMs();
        std::lock_guard guard(verified_direct_mutex);
        if (!verified_direct_gate.Allows({ip,port,0},now,bytes))
            return -1;
        sockaddr_in peer{};
        peer.sin_family=AF_INET;
        peer.sin_addr.s_addr=ip;
        peer.sin_port=port;
        std::vector<u8> datagram(bytes.begin(),bytes.end());
        return Transmit(peer,std::move(datagram))?static_cast<int>(len):-1;
    }

    int ReadVerifiedMovement(void* out,u32 max,u32* ip,u16* port) {
        // V276: previously admitted peer ciphertext must not outlive
        // the ORIGINAL server-authenticated link's welcome state.
        // The live V262 world/party lease is rechecked again by game ingress.
        if (!LinkWelcomed() || !IsReady())
            return -1;
        // Never let generic ReceiveInternal truncate an authenticated
        // SHDP ciphertext. GameLink needs the ENTIRE AEAD frame or none.
        if (!out || max < BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::MaxWire)
            return -1;
        return ReceiveInternal(InternalChannel::VerifiedDirectMovement,
                               out,max,ip,port);
    }

    void RevokeVerifiedMovementEndpoints() {
        std::lock_guard guard(verified_direct_mutex);
        verified_direct_gate.RevokeAll();
        std::lock_guard queue_guard(internal_mutex);
        verified_direct_queue.clear();
    }

"""
    src=replace_once(src,
        "    int SendInternal(const void* data, u32 len, u32 dest_addr_nbo, u16 dest_port_nbo) {",
        public_methods+
        "    int SendInternal(const void* data, u32 len, u32 dest_addr_nbo, u16 dest_port_nbo) {")

    # V266: a reconnect/new server MUST revoke all physical peer
    # permissions before the server link's auth state is reset.
    src=replace_once(src,
        "        const auto key = LinkAuth::KeyFromHex(server_key);",
        "        RevokeVerifiedMovementEndpoints(); // V266: server key/epoch changed\n"
        "        const auto key = LinkAuth::KeyFromHex(server_key);")
    # A stopped game transport cannot retain old authenticated endpoints.
    src=replace_once(src,
        "        std::lock_guard lock(start_mutex);\n"
        "        if (!running.exchange(false, std::memory_order_acq_rel)) {",
        "        std::lock_guard lock(start_mutex);\n"
        "        RevokeVerifiedMovementEndpoints(); // V266: shutdown revoke\n"
        "        if (!running.exchange(false, std::memory_order_acq_rel)) {")

    # V276: the game may replace its build without changing its server
    # address/key. This re-hello invalidates prior peer pair grants too.
    src=replace_once(src,
        "    void SetLinkBuild(std::string build) {\\n"
        "        std::lock_guard lock(link_mutex);\\n"
        "        if (Link::SaysHelloAgainForBuild(link_build, build)) {\\n"
        "            link_welcomed = false;\\n"
        "            link_hello_ms.reset();\\n"
        "        }\\n"
        "        link_build = std::move(build);\\n"
        "    }",
        "    void SetLinkBuild(std::string build) {\\n"
        "        bool reset_peer_grant = false;\\n"
        "        {\\n"
        "            std::lock_guard lock(link_mutex);\\n"
        "            if (Link::SaysHelloAgainForBuild(link_build, build)) {\\n"
        "                link_welcomed = false;\\n"
        "                link_hello_ms.reset();\\n"
        "                reset_peer_grant = true;\\n"
        "            }\\n"
        "            link_build = std::move(build);\\n"
        "        }\\n"
        "        if (reset_peer_grant)\\n"
        "            RevokeVerifiedMovementEndpoints(); // V276: build reauth\\n"
        "    }")

    gate="""            // V265: a separately typed, encrypted SHDP packet from a
            // verified peer endpoint. Never place it into original shadNet
            // signaling, GamePackets or direct guest socket queues.
            if (BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::LooksLikePeerWire(datagram)) {
                // V272: consume SHDP family even if malformed/unknown version.
                // Peer traffic must NEVER fall through to the old SHAD path.
                if (!BloodborneCoop::SHYTHybrid::DirectPhysicalGateV264::CorrectWire(datagram))
                    continue;
                const auto now=P2PNowMs();
                bool permitted=false;
                {
                    std::lock_guard guard(verified_direct_mutex);
                    permitted=verified_direct_gate.Allows(
                        {from.sin_addr.s_addr,from.sin_port,0},now,datagram);
                }
                if (permitted && LinkWelcomed()) {
                    PushInternal(InternalChannel::VerifiedDirectMovement,
                                 from.sin_addr.s_addr,from.sin_port,
                                 datagram.data(),datagram.size());
                }
                continue; // never fall through to normal shadNet SHAD
            }
"""
    src=replace_once(src,
        "            if (!Link::TakesDatagramFrom(LinkServer(), from.sin_addr.s_addr, from.sin_port)) {",
        gate+"            if (!Link::TakesDatagramFrom(LinkServer(), from.sin_addr.s_addr, from.sin_port)) {")

    exports="""// V265: these operations share the ORIGINAL OS UDP socket but not
// original YT server-only SHAD wire path. Without a real verified V262
// pair grant, Send/Receive remain disabled and do not bypass shadNet.
bool P2PInstallVerifiedMovementEndpoint(
    const BloodborneCoop::SHYTHybrid::VerifiedPeerIngressV262& proof) {
    return P2PTransport::Instance().InstallVerifiedMovementEndpoint(proof);
}
int P2PVerifiedMovementSendTo(const void* data,u32 len,u32 ip,u16 port) {
    return P2PTransport::Instance().SendVerifiedMovement(data,len,ip,port);
}
int P2PVerifiedMovementRecvFrom(void* buf,u32 len,u32* ip,u16* port) {
    return P2PTransport::Instance().ReadVerifiedMovement(buf,len,ip,port);
}
void P2PRevokeVerifiedMovementEndpoints() {
    P2PTransport::Instance().RevokeVerifiedMovementEndpoints();
}

"""
    src=replace_once(src,
        "int P2PGamePacketsRecvFrom(void* buf, u32 len, u32* from_addr, u16* from_port) {",
        exports+
        "int P2PGamePacketsRecvFrom(void* buf, u32 len, u32* from_addr, u16* from_port) {")
    return src

def repo_hash(root:Path,*args:str)->str:
    proc=subprocess.run(["git","-C",str(root),*args],
         capture_output=True,text=True,timeout=12,check=False)
    if proc.returncode: raise ValueError("not a pinned YT git checkout")
    return proc.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    args=p.parse_args()
    root=args.upstream_checkout.resolve(strict=True)
    path=root/RELATIVE
    if repo_hash(root,"rev-parse","HEAD")!=PINNED_SHA or not path.is_file() or path.is_symlink():
        raise ValueError("unpinned or linked YT source")
    if repo_hash(root,"hash-object",RELATIVE)!=PINNED_BLOB:
        raise ValueError("p2p_sockets.cpp upstream drift")
    original=path.read_text(encoding="utf-8")
    converted=patch(original)
    if args.mode=="check":
        print("SHYT_V265_ORIGINAL_P2P_SOCKETS_PINNED_ANCHORS_PASS")
        return
    header_dir=root/"emulator/src/core/shyt_hybrid"
    if not header_dir.is_dir() or header_dir.is_symlink():
        raise ValueError("run verified V256 source overlay first")
    base=Path(__file__).resolve().parent
    for name in ("hybrid_direct_physical_gate_v264.h","yt_direct_physical_api_v264.h"):
        src=base/name
        if src.is_symlink() or not src.is_file():
            raise ValueError("missing required physical gate header")
        dst=header_dir/name
        if dst.exists() or dst.is_symlink():
            raise ValueError("refusing overwrite of existing physical gate header")
    for name in ("hybrid_direct_physical_gate_v264.h","yt_direct_physical_api_v264.h"):
        (header_dir/name).write_bytes((base/name).read_bytes())
    path.write_text(converted,encoding="utf-8")
    print("SHYT_V265_PINNED_PHYSICAL_UDP_SOURCE_APPLIED_DEFAULT_OFF")

if __name__=="__main__":
    try: main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        raise SystemExit("V265 refused unsafe physical source patch: "+type(exc).__name__) from None
