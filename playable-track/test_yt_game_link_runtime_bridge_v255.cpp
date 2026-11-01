// SPDX-License-Identifier: GPL-2.0-or-later
// V255 original GameLink source-hook integration semantics.
#include "yt_game_link_runtime_bridge_v255.h"
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
    auto direct_send=[&](std::string_view member, std::span<const u8> bytes) {
        assert(member=="hunter-B");
        const auto frame=receiver.OpenMovement(bytes);
        assert(frame);
        assert(frame->ack==0);
        const auto delivered=original_receiver.Receive(*frame,20000);
        assert(delivered.size()==1);
        ++direct;
        return true;
    };
    pending.frame=Movement(2,11);
    assert(DispatchYtFrameV255(pending,&active,original_send,direct_send)
           ==EgressResult::Direct);
    assert(direct==1 && original_relay==2);
    // Piggybacked *same* reliable ACK no longer sends an ACK-only
    // server datagram every movement frame. It refreshes periodically.
    pending.frame=Movement(3,11);
    assert(DispatchYtFrameV255(pending,&active,original_send,direct_send)
           ==EgressResult::Direct);
    assert(direct==2 && original_relay==2);
    active.lease.now_ms+=DirectAckCoalescerV251::AckRefreshMs;
    active.lease.last_authenticated_direct_probe_ms=active.lease.now_ms;
    pending.frame=Movement(4,11);
    assert(DispatchYtFrameV255(pending,&active,original_send,direct_send)
           ==EgressResult::Direct);
    assert(direct==3 && original_relay==3);

    // Failure of direct peer socket must relay ORIGINAL GameFrame, same
    // source sequence, no player reordering or new GameLinkPeer.
    pending.frame=Movement(5,11);
    auto failed_peer=[&](std::string_view,std::span<const u8>) { return false; };
    assert(DispatchYtFrameV255(pending,&active,original_send,failed_peer)
           ==EgressResult::Server);
    assert(original_relay==4 && direct==3);
    // Initial YT peer_instance=0 never drops; always sends to server.
    pending.frame=Movement(6);
    pending.frame.peer_instance=0;
    assert(DispatchYtFrameV255(pending,&active,original_send,failed_peer)
           ==EgressResult::Server);
    assert(original_relay==5);
    // Wrong peer id or stale lease returns unchanged server route.
    pending.member="not-granted";
    pending.frame=Movement(7);
    assert(DispatchYtFrameV255(pending,&active,original_send,illegal_direct)
           ==EgressResult::Server);
    assert(original_relay==6 && unexpected_server==0);
    puts("SHYT_V255_ORIGINAL_YT_GAME_LINK_SOURCE_SEAM_PASS");
}
