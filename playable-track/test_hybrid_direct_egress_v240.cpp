// SPDX-License-Identifier: GPL-2.0-or-later
// V240: tests against authentic pinned YT 1.3.1 GameLinkPeer/GameFrame types.
#include "hybrid_direct_egress_v240.h"
#include <cassert>
#include <cstdio>
#include <vector>

using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;

static constexpr PacketEnds endpoints{0x101,0x101,EnemyPart::None,EnemyPart::None};

static PeerRouteLease authorized() {
    PeerRouteLease l{};
    l.local_opt_in = true; l.remote_opt_in = true;
    l.same_party_session = true; l.session_authenticated = true;
    l.peer_authenticated = true; l.direct_datagram_verified = true;
    l.server_route_granted = true; l.has_common_protocol = true;
    l.granted_sender_id = "hunter-A"; l.granted_receiver_id = "hunter-B";
    l.granted_party_session_id = "party-42";
    l.granted_sender_instance = 17; l.granted_receiver_instance = 29;
    l.authority_epoch = 42; l.local_world_epoch = 42;
    l.approved_sender_map = 0x101; l.approved_target_map = 0x101;
    l.now_ms = 10000; l.lease_expiry_ms = 12000;
    l.last_authenticated_direct_probe_ms = 9990;
    return l;
}
static std::vector<u8> native(u32 channel, u8 value) {
    return {static_cast<u8>(channel),0,0,0, 1,0,0,0, value};
}
static GameFrame game(u32 seq, u32 channel=6) {
    GameFrame frame{};
    frame.sender = "hunter-A";
    frame.instance = 17; frame.peer_instance = 29;
    frame.entries.push_back({PacketClass::Unreliable,seq,native(channel,42)});
    return frame;
}
static DirectEgressIdentity sender() {
    return {"hunter-A","hunter-B","party-42",17,29,true,1100};
}
int main() {
    auto lease=authorized();
    auto id=sender();
    GameFrame frame=game(1);
    GameLinkPeer receiver("hunter-B",29);
    int direct_calls=0, server_calls=0;
    auto direct=[&](const GameFrame& sent) {
        ++direct_calls;
        assert(sent.ack==0);
        auto delivered=receiver.Receive(sent,lease.now_ms);
        assert(delivered.size()==1 && delivered[0]==native(6,42));
        return true;
    };
    auto server=[&](const GameFrame&) { ++server_calls; return true; };
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,server)==
           EgressResult::Direct);
    assert(direct_calls==1 && server_calls==0);
    assert(receiver.Receive(frame,lease.now_ms).empty()); // fallback/dedup identity

    // V253: original YT emits peer_instance=0 while the new peer is
    // unknown/reconnecting. The real YT server must see this frame to
    // complete initial session establishment; direct must NOT consume it.
    auto startup=game(77); startup.peer_instance=0;
    const int before_startup_server=server_calls;
    const int before_startup_direct=direct_calls;
    assert(SendExistingGameFrameV240(startup,endpoints,lease,id,direct,server)
           ==EgressResult::Server);
    assert(server_calls==before_startup_server+1 &&
           direct_calls==before_startup_direct);
    // Invalid zero SOURCE instance still fails closed rather than
    // forging an anonymous game connection.
    startup.instance=0;
    assert(SendExistingGameFrameV240(startup,endpoints,lease,id,direct,server)
           ==EgressResult::Failed);
    assert(server_calls==before_startup_server+1);

    // ACKs stay on the original server link, movement uses the direct one.
    frame=game(2); frame.ack=11;
    int ack_only=0;
    auto relay_ack=[&](const GameFrame& sent) {
        ++server_calls;
        assert(sent.ack==11);
        assert(sent.entries.empty());
        ++ack_only;
        return true;
    };
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,relay_ack)==
           EgressResult::Direct);
    assert(ack_only==1 && direct_calls==2);

    // Secure datagram unavailable: exact same sequence and ACK use server.
    frame=game(3); frame.ack=0;
    id.secure_peer_datagram_sender_installed=false;
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,server)==
           EgressResult::Server);
    assert(server_calls==3 && direct_calls==2);
    id.secure_peer_datagram_sender_installed=true;
    auto broken=[&](const GameFrame&) { ++direct_calls; return false; };
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,broken,server)==
           EgressResult::Server);
    assert(server_calls==4 && direct_calls==3);

    // Expiration, wrong party, wrong sender, reliable packets, mixed entries,
    // wrong native packet size all refuse the direct carrier.
    lease.lease_expiry_ms=lease.now_ms;
    assert(SendExistingGameFrameV240(game(4),endpoints,lease,id,direct,server)==
           EgressResult::Server);
    lease=authorized();
    id.server_authorized_party_session_id="other-party";
    assert(SendExistingGameFrameV240(game(5),endpoints,lease,id,direct,server)==
           EgressResult::Server);
    id=sender();
    frame=game(6); frame.sender="hunter-C";
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,server)==
           EgressResult::Server);
    frame=game(7); frame.entries[0].packet_class=PacketClass::Reliable;
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,server)==
           EgressResult::Server);
    frame=game(8); frame.entries.push_back({PacketClass::Unreliable,9,native(6,43)});
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,server)==
           EgressResult::Server);
    frame=game(10); frame.entries[0].packet[4]=20;
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,server)==
           EgressResult::Server);
    frame=game(11,5);
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,server)==
           EgressResult::Server);
    assert(direct_calls==3);

    // ACK-only relay failure cannot silently drop the ACK to shift traffic.
    frame=game(12); frame.ack=50;
    int server_attempts=0;
    auto offline=[&](const GameFrame&) { ++server_attempts; return false; };
    assert(SendExistingGameFrameV240(frame,endpoints,lease,id,direct,offline)==
           EgressResult::Failed);
    assert(server_attempts==2 && direct_calls==3);
    puts("SHYT_V240_YT_REAL_GAMEFRAME_EGRESS_SYNTHETIC_PASS");
}
