// SPDX-License-Identifier: GPL-2.0-or-later
// V243: one original GameLinkPeer receive path for real YT authenticated
// datagrams AND server-relayed fallback. No actual socket or retail assets.
#include "hybrid_peer_crypto_v241.h"
#include <cassert>
#include <cstdio>
#include <optional>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;

static PeerRouteLease grant() {
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
    p.now_ms=10000;p.lease_expiry_ms=12000;
    p.last_authenticated_direct_probe_ms=9999;
    return p;
}
static GameFrame movement(u32 sequence,u8 value,u32 ack=0) {
    GameFrame f{};
    f.sender="A";f.instance=17;f.peer_instance=29;f.ack=ack;
    f.entries.push_back({PacketClass::Unreliable,sequence,
                         std::vector<u8>{6,0,0,0,1,0,0,0,value}});
    return f;
}
int main() {
    LinkAuth::Key ab{},ba{};
    for(size_t i=0;i<ab.size();++i) {
        ab[i]=static_cast<u8>(i+1);
        ba[i]=static_cast<u8>(i+91);
    }
    PeerCryptoScopeV241 scope{"party42","A","B",17,29,42,0x101};
    PeerCryptoDatagramsV241 secure_a(scope,true,ab,ba);
    PeerCryptoDatagramsV241 secure_b(scope,false,ba,ab);
    GameLinkPeer actual_receiver("B",29);
    DirectEgressIdentity from_a{"A","B","party42",17,29,true,1100};
    DirectIngressIdentity for_b{"A",17,29,1100,"B","party42"};
    const PacketEnds ends{0x101,0x101,EnemyPart::None,EnemyPart::None};
    auto lease=grant();
    int direct_sent=0,relay_sent=0,ack_relay=0;
    std::optional<std::vector<u8>> captured;
    auto secure_send=[&](const GameFrame& outbound) {
        ++direct_sent;
        captured=secure_a.SealMovement(outbound);
        if(!captured) return false;
        const auto frame=secure_b.OpenMovement(*captured);
        assert(frame && AcceptAuthenticatedDirectMovement(*frame,ends,lease,for_b));
        const auto delivered=actual_receiver.Receive(*frame,lease.now_ms);
        assert(delivered.size()==1);
        assert(delivered[0]==outbound.entries[0].packet);
        return true;
    };
    auto relay=[&](const GameFrame& f) {
        ++relay_sent;
        if(f.entries.empty()) {
            ++ack_relay;
            return true;
        }
        const auto got=actual_receiver.Receive(f,lease.now_ms);
        assert(got.size()==1);
        return true;
    };
    // Direct encrypted -> decoded -> original ingress -> original
    // GameLinkPeer::Receive; subsequent replay rejected by LinkAuth.
    auto first=movement(1,42);
    assert(SendExistingGameFrameV240(first,ends,lease,from_a,secure_send,relay)
           ==EgressResult::Direct);
    assert(direct_sent==1 && relay_sent==0 && captured);
    assert(!secure_b.OpenMovement(*captured));
    // A mixed ACK+movement sends the ACK over server and the real movement
    // encrypted peer-to-peer (the wire payload has ack=0).
    auto second=movement(2,43,123);
    assert(SendExistingGameFrameV240(second,ends,lease,from_a,secure_send,relay)
           ==EgressResult::Direct);
    assert(direct_sent==2 && relay_sent==1 && ack_relay==1);

    // A failed direct sender uses the EXACT original frame and sequence
    // over the original relay. No second GameLinkPeer instance is created.
    auto broken=[&](const GameFrame& f) {
        ++direct_sent;
        return secure_a.SealMovement(f).has_value() && false;
    };
    auto third=movement(3,44);
    assert(SendExistingGameFrameV240(third,ends,lease,from_a,broken,relay)
           ==EgressResult::Server);
    assert(direct_sent==3 && relay_sent==2);
    // The old direct frame, even if authenticated, can no longer roll back
    // the original receiver's newest unreliable channel state.
    auto old=secure_a.SealMovement(movement(2,43));
    assert(old);
    auto old_decoded=secure_b.OpenMovement(*old);
    assert(old_decoded);
    assert(actual_receiver.Receive(*old_decoded,lease.now_ms).empty());

    // Lease revoked: only original server path, no encryption attempt.
    lease.lease_expiry_ms=lease.now_ms;
    auto fourth=movement(4,45);
    assert(SendExistingGameFrameV240(fourth,ends,lease,from_a,secure_send,relay)
           ==EgressResult::Server);
    assert(direct_sent==3 && relay_sent==3);
    puts("SHYT_V243_ENCRYPTED_YT_EGRESS_INGRESS_SHARED_RELAY_PASS");
}
