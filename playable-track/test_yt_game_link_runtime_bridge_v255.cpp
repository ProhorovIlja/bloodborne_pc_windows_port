// SPDX-License-Identifier: GPL-2.0-or-later
// V255 original GameLink source-hook integration semantics.
#include "yt_game_link_runtime_bridge_v255.h"
#include "yt_game_link_direct_ingress_v262.h"
#include <cassert>
#include <cstdio>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;
static PeerRouteLease Grant() {
    PeerRouteLease x{};
    x.local_opt_in=true;x.remote_opt_in=true;x.same_party_session=true;
    x.session_authenticated=true;x.peer_authenticated=true;
    x.direct_datagram_verified=true;x.server_route_granted=true;
    x.has_common_protocol=true;x.granted_sender_id="hunter-A";
    x.granted_receiver_id="hunter-B";x.granted_party_session_id="party-17";
    x.granted_sender_instance=7;x.granted_receiver_instance=8;
    x.authority_epoch=42;x.local_world_epoch=42;
    x.approved_sender_map=0x101;x.approved_target_map=0x101;
    x.now_ms=20000;x.lease_expiry_ms=30000;
    x.last_authenticated_direct_probe_ms=19999;
    return x;
}
static GameFrame Movement(u32 seq,u32 ack=0) {
    GameFrame f{};
    f.sender="hunter-A";f.instance=7;f.peer_instance=8;f.ack=ack;
    f.entries.push_back({PacketClass::Unreliable,seq,
                         {6,0,0,0,1,0,0,0,42}});
    return f;
}
int main() {
    PendingYtFrameV255 pending{"hunter-B",{0x0100007f,41234},Movement(1)};
    int original_relay=0, direct=0, unexpected_server=0;
    GameLinkPeer original_receiver("hunter-B",8);
    auto original_send=[&](const std::pair<u32,u16>& addr,
                           std::span<const u8> wire) {
        assert(addr==pending.existing_server_link_address);
        assert(wire.size()>=5 && wire[0]=='S' && wire[1]=='H' &&
               wire[2]=='A' && wire[3]=='D' && wire[4]==GamePacketsType);
        const auto decoded=DecodeGameFrame(wire.subspan(5));
        assert(decoded);
        ++original_relay;
        if(decoded->entries.empty()) {
            assert(decoded->ack!=0);
        } else {
            const auto delivered=original_receiver.Receive(*decoded,20000);
            assert(delivered.size()==1);
        }
        return true;
    };
    // With no verified server-authorized route installed, unchanged
    // SHAD packet MUST travel via the original shadNet endpoint.
    auto illegal_direct=[&](std::string_view, std::span<const u8>) {
        ++unexpected_server;
        return true;
    };
    assert(DispatchYtFrameV255(pending,nullptr,original_send,illegal_direct)
           ==EgressResult::Server);
    assert(original_relay==1 && unexpected_server==0);

    LinkAuth::Key ab{},ba{};
    for(size_t i=0;i<ab.size();++i) {
        ab[i]=static_cast<u8>(1+i);
        ba[i]=static_cast<u8>(101+i);
    }
    PeerCryptoScopeV241 scope{"party-17","hunter-A","hunter-B",7,8,42,0x101};
    PeerCryptoDatagramsV241 sender(scope,true,ab,ba);
    PeerCryptoDatagramsV241 receiver(scope,false,ba,ab);
    DirectAckCoalescerV251 tracker;
    VerifiedPeerRouteV255 active{};
    active.lease=Grant();
    active.identity={"hunter-A","hunter-B","party-17",7,8,true,1100};
    active.endpoints={0x101,0x101,EnemyPart::None,EnemyPart::None};
    active.peer_crypto=&sender;
    active.ack_tracker=&tracker;
    // V258: a configured key/lease does not prove the remote game has
    // installed the matching direct receiver. Stay on server until then.
    pending.frame=Movement(2);
    const int before_ingress_relay=original_relay;
    assert(DispatchYtFrameV255(pending,&active,original_send,illegal_direct)
           ==EgressResult::Server);
    assert(original_relay==before_ingress_relay+1 && unexpected_server==0);
    active.same_peer_ingress_installed=true;
    // V263: the *same* original GameLinkPeer is now fed by either the
    // genuine server packet or the matching authenticated peer receiver,
    // with live server-issued party/world/endpoint constraints enforced.
    VerifiedPeerIngressV262 inbound{};
    inbound.session=&receiver;
    inbound.lease=active.lease;
    inbound.identity={"hunter-A",7,8,1100,"hunter-B","party-17"};
    inbound.endpoints=active.endpoints;
    inbound.approved_endpoint={0x0100007f,31234};
    inbound.endpoint_proved_by_authenticated_handshake=true;
    auto direct_send=[&](std::string_view member, std::span<const u8> bytes) {
        assert(member=="hunter-B");
        inbound.lease=active.lease;
        // V286: our real physical sender now supplies SHDP-framed
        // ciphertext. The original YT receiver sees ONLY unwrapped AEAD.
        assert(ShdpWireV286::OpenEnvelope(bytes));
        const auto delivered=ReceivePhysicalDirectYtFrameV286(
            original_receiver,inbound,inbound.approved_endpoint,bytes);
        assert(delivered.size()==1);
        ++direct;
        return true;
    };
    pending.frame=Movement(3,11);
    assert(DispatchYtFrameV255(pending,&active,original_send,direct_send)
           ==EgressResult::Direct);
    assert(direct==1 && original_relay==3);
    // Piggybacked *same* ACK no longer sends a server datagram each frame.
    pending.frame=Movement(4,11);
    assert(DispatchYtFrameV255(pending,&active,original_send,direct_send)
           ==EgressResult::Direct);
    assert(direct==2 && original_relay==3);
    active.lease.now_ms+=DirectAckCoalescerV251::AckRefreshMs;
    active.lease.last_authenticated_direct_probe_ms=active.lease.now_ms;
    pending.frame=Movement(5,11);
    assert(DispatchYtFrameV255(pending,&active,original_send,direct_send)
           ==EgressResult::Direct);
    assert(direct==3 && original_relay==4); // periodic lost-ACK recovery

    // Failure of secure peer socket relays ORIGINAL frame, same sequence.
    pending.frame=Movement(6,11);
    auto failed_peer=[&](std::string_view,std::span<const u8>) { return false; };
    assert(DispatchYtFrameV255(pending,&active,original_send,failed_peer)
           ==EgressResult::Server);
    assert(original_relay==5 && direct==3);

    // V258: a grant for a NEW world epoch must never re-use old Noise
    // keys even if the server-provided direct-enabled flags are still set.
    active.lease.authority_epoch=43;
    active.lease.local_world_epoch=43;
    pending.frame=Movement(7);
    assert(DispatchYtFrameV255(pending,&active,original_send,illegal_direct)
           ==EgressResult::Server);
    assert(original_relay==6 && unexpected_server==0);
    active.lease.authority_epoch=42;
    active.lease.local_world_epoch=42;

    // Original YT peer_instance=0 is valid at join/reconnect.
    pending.frame=Movement(8);
    pending.frame.peer_instance=0;
    assert(DispatchYtFrameV255(pending,&active,original_send,failed_peer)
           ==EgressResult::Server);
    assert(original_relay==7);

    // Wrong peer id returns the unmodified original server route.
    pending.member="not-granted";
    pending.frame=Movement(9);
    assert(DispatchYtFrameV255(pending,&active,original_send,illegal_direct)
           ==EgressResult::Server);
    assert(original_relay==8 && unexpected_server==0);
    puts("SHYT_V255_ORIGINAL_YT_GAME_LINK_SOURCE_SEAM_PASS");
}
