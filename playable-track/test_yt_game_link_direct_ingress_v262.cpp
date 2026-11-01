// SPDX-License-Identifier: GPL-2.0-or-later
// V262: source YT 1.3.1 GameFrame, replay window and SAME GameLinkPeer.
#include "yt_game_link_direct_ingress_v262.h"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;

static PeerRouteLease Lease() {
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
static GameFrame Movement(u32 seq,u8 pos) {
    GameFrame f{};
    f.sender="A";f.instance=17;f.peer_instance=29;
    f.entries.push_back({PacketClass::Unreliable,seq,
                         {6,0,0,0,1,0,0,0,pos}});
    return f;
}
int main() {
    LinkAuth::Key ab{},ba{};
    for(size_t i=0;i<ab.size();++i) {
        ab[i]=static_cast<u8>(i+1);
        ba[i]=static_cast<u8>(i+101);
    }
    PeerCryptoScopeV241 scope{"party42","A","B",17,29,42,0x101};
    PeerCryptoDatagramsV241 alice(scope,true,ab,ba);
    PeerCryptoDatagramsV241 bob(scope,false,ba,ab);
    GameLinkPeer original_receiver("B",29);
    VerifiedPeerIngressV262 incoming{};
    incoming.session=&bob;
    incoming.lease=Lease();
    incoming.identity={"A",17,29,1100,"B","party42"};
    incoming.endpoints={0x101,0x101,EnemyPart::None,EnemyPart::None};
    incoming.approved_endpoint={0x0100007f,31999};
    incoming.endpoint_proved_by_authenticated_handshake=true;
    const auto trusted=incoming.approved_endpoint;
    const auto stranger=std::pair<u32,u16>{0x0100007f,32000};

    auto first=alice.SealMovement(Movement(1,42));
    assert(first && first->size()<=1200);
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,stranger,*first).empty());
    assert(original_receiver.DroppedOld()==0);
    auto first_delivery=ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*first);
    assert(first_delivery.size()==1 &&
           first_delivery[0]==Movement(1,42).entries[0].packet);
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*first).empty()); // Noise replay

    auto second=alice.SealMovement(Movement(2,43));
    assert(second);
    incoming.lease.authority_epoch=43;
    incoming.lease.local_world_epoch=43;
    // A valid OLD world key may not be used with a NEW server-issued grant.
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*second).empty());
    incoming.lease.authority_epoch=42;
    incoming.lease.local_world_epoch=42;
    incoming.endpoint_proved_by_authenticated_handshake=false;
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*second).empty());
    incoming.endpoint_proved_by_authenticated_handshake=true;
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*second).size()==1);
    // Now server fallback must use the SAME GameLinkPeer, and not
    // resurrect a stale authenticated movement frame.
    const auto from_original_server=Movement(3,44);
    assert(original_receiver.Receive(from_original_server,10000).size()==1);
    auto late=alice.SealMovement(Movement(2,43));
    assert(late);
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*late).empty());
    assert(original_receiver.DroppedOld()==1);

    // World revocation, out-of-party routing, bad MAC and endpoint changes
    // must not reinitialize the existing original receiver stream.
    auto fourth=alice.SealMovement(Movement(4,45));
    assert(fourth);
    incoming.lease.lease_expiry_ms=incoming.lease.now_ms;
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*fourth).empty());
    incoming.lease.lease_expiry_ms=12000;
    incoming.identity.server_authorized_party_session_id="wrong";
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*fourth).empty());
    incoming.identity.server_authorized_party_session_id="party42";
    auto corrupt=*fourth;corrupt.back()^=0x20;
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,corrupt).empty());
    assert(ReceiveDirectYtFrameV262(
        original_receiver,incoming,trusted,*fourth).size()==1);
    puts("SHYT_V262_REAL_YT_AUTHENTICATED_SAME_RECEIVER_INGRESS_PASS");
}
