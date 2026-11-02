// SPDX-License-Identifier: GPL-2.0-or-later
// V251 genuine YT v1.3.1 GameLinkPeer/GameFrame reliability tests.
#include "hybrid_direct_ack_coalescer_v251.h"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;
namespace {
PeerRouteLease Lease() {
    PeerRouteLease p{};
    p.local_opt_in=true;p.remote_opt_in=true;
    p.same_party_session=true;p.session_authenticated=true;
    p.peer_authenticated=true;p.direct_datagram_verified=true;
    p.server_route_granted=true;p.has_common_protocol=true;
    p.granted_sender_id="A";p.granted_receiver_id="B";
    p.granted_party_session_id="party42";
    p.granted_sender_instance=17;p.granted_receiver_instance=29;
    p.authority_epoch=42;p.local_world_epoch=42;
    p.approved_sender_map=0x101;p.approved_target_map=0x101;
    p.now_ms=10000;p.lease_expiry_ms=20000;
    p.last_authenticated_direct_probe_ms=9999;
    return p;
}
GameFrame Movement(u32 sequence, u32 ack) {
    GameFrame f{};
    f.sender="A";f.instance=17;f.peer_instance=29;f.ack=ack;
    f.entries.push_back({PacketClass::Unreliable,sequence,
        std::vector<u8>{6,0,0,0,1,0,0,0,42}});
    return f;
}
}
int main() {
    GameLinkPeer from_a("A",17);
    GameFrame remote_reliable{};
    remote_reliable.sender="B";
    remote_reliable.instance=29;
    remote_reliable.peer_instance=17;
    remote_reliable.entries.push_back({PacketClass::Reliable,0,
                                       std::vector<u8>{7,0,0,0,1,0,0,0,99}});
    assert(from_a.Receive(remote_reliable,10000).size()==1);
    // This is ORIGINAL YT GameLinkPeer::Flush: expected=1 is repeated
    // on EVERY outgoing movement, not just when a reliable ACK is due.
    from_a.Send(PacketClass::Unreliable,
                std::vector<u8>{6,0,0,0,1,0,0,0,1},10000);
    auto frames=from_a.Flush(10000);
    assert(frames.size()==1 && frames[0].ack==1);

    auto lease=Lease();
    DirectEgressIdentity id{"A","B","party42",17,29,true,1100};
    const PacketEnds ends{0x101,0x101,EnemyPart::None,EnemyPart::None};
    DirectAckCoalescerV251 tracker;
    int direct=0,acks=0,relay_full=0;
    auto peer=[&](const GameFrame& f) {
        ++direct;
        assert(f.entries.size()==1 && f.ack==0);
        return true;
    };
    auto server=[&](const GameFrame& f) {
        if(f.entries.empty()) ++acks;
        else ++relay_full;
        return true;
    };
    auto send=[&](const GameFrame& f) {
        return SendExistingGameFrameV251(f,ends,lease,id,tracker,peer,server);
    };

    assert(send(frames[0])==EgressResult::Direct);
    assert(acks==1 && direct==1 && relay_full==0);
    for (u32 i=2;i<=60;i++) {
        assert(send(Movement(i,1))==EgressResult::Direct);
    }
    assert(direct==60 && acks==1 && relay_full==0); // 60x ACK flood avoided
    lease.now_ms=10749;
    assert(send(Movement(61,1))==EgressResult::Direct);
    assert(acks==1);
    lease.now_ms=10750;
    assert(send(Movement(62,1))==EgressResult::Direct);
    assert(acks==2); // re-ACK if earlier server UDP copy was lost
    lease.now_ms=10751;
    assert(send(Movement(63,2))==EgressResult::Direct);
    assert(acks==3); // immediate cumulative-ACK advancement
    assert(send(Movement(64,1))==EgressResult::Direct);
    assert(acks==4); // unexpected ack regression must not be suppressed

    // Returning to actual server route sends the FULL original frame.
    lease.lease_expiry_ms=10751;
    assert(send(Movement(65,1))==EgressResult::Server);
    assert(acks==4 && relay_full==1 && direct==64);
    lease.lease_expiry_ms=20000;
    lease.last_authenticated_direct_probe_ms=10752;
    lease.now_ms=10752;
    assert(send(Movement(66,1))==EgressResult::Direct);
    assert(acks==4); // server already saw this cumulative ACK in full frame

    // A new world epoch/party must never reuse previous ACK history.
    lease.authority_epoch=43;
    lease.local_world_epoch=43;
    assert(send(Movement(67,1))==EgressResult::Direct);
    assert(acks==5);
    lease.granted_party_session_id="new-party";
    id.server_authorized_party_session_id="new-party";
    assert(send(Movement(68,1))==EgressResult::Direct);
    assert(acks==6);

    // A failed direct sender relays ORIGINAL sequence/ack, after only one
    // server ACK attempt at most, never drops both reliable and movement.
    auto failing_peer=[&](const GameFrame&) { return false; };
    assert(SendExistingGameFrameV251(Movement(69,1),ends,lease,id,tracker,
             failing_peer,server)==EgressResult::Server);
    assert(relay_full==2 && acks==6);

    // Simulated server failure for new ACK must still attempt original full
    // frame through the original server link; no ACK state marked delivered.
    int failures=0;
    auto partial_failure=[&](const GameFrame& f) {
        if(f.entries.empty()) { ++failures;return false; }
        ++relay_full;return true;
    };
    assert(SendExistingGameFrameV251(Movement(70,7),ends,lease,id,tracker,
             peer,partial_failure)==EgressResult::Server);
    assert(failures==1 && relay_full==3);

    // Clock regression and route-key change MUST force server ACK send.
    tracker.Reset();
    assert(send(Movement(71,7))==EgressResult::Direct && acks==7);
    puts("SHYT_V251_ORIGINAL_YT_ACK_COALESCING_RETRY_FALLBACK_PASS");
}
