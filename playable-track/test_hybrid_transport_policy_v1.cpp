// SPDX-License-Identifier: GPL-2.0-or-later
// Compile against exact real Yharnam Together public coop/packet_routes.h.
#include "hybrid_transport_policy_v1.h"
#include <cassert>
#include <cstdio>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;

constexpr PacketEnds same_map{0x101,0x101,EnemyPart::None,EnemyPart::None};
constexpr PacketEnds apart{0x101,0x102,EnemyPart::None,EnemyPart::None};
constexpr PacketEnds unknown{0,0,EnemyPart::None,EnemyPart::None};

constexpr PeerRouteLease fully_granted() {
    PeerRouteLease lease{};
    lease.local_opt_in = true;
    lease.remote_opt_in = true;
    lease.same_party_session = true;
    lease.session_authenticated = true;
    lease.peer_authenticated = true;
    lease.direct_datagram_verified = true;
    lease.server_route_granted = true;
    lease.has_common_protocol = true;
    lease.granted_sender_id = "hunter-A";
    lease.granted_receiver_id = "hunter-B";
    lease.authority_epoch = 1777;
    lease.local_world_epoch = 1777;
    lease.approved_sender_map = 0x101;
    lease.approved_target_map = 0x101;
    lease.now_ms = 10000;
    lease.lease_expiry_ms = 12000;
    lease.last_authenticated_direct_probe_ms = 9900;
    return lease;
}

static_assert(ChooseNativePacketCarrier(0x06,same_map,{}) == Carrier::Server);
static_assert(ChooseNativePacketCarrier(0x06,same_map,fully_granted()) == Carrier::DirectPeer);
static_assert(ChooseNativePacketCarrier(0x06,apart,fully_granted()) == Carrier::Drop);
static_assert(ChooseNativePacketCarrier(0x06,unknown,fully_granted()) == Carrier::Server);
// Original server semantics always win over the new P2P experiment.
static_assert(ChooseNativePacketCarrier(0x2C,same_map,fully_granted()) == Carrier::Drop);
static_assert(ChooseNativePacketCarrier(0x2F,same_map,fully_granted()) == Carrier::Drop);
static_assert(ChooseNativePacketCarrier(0x27,same_map,fully_granted()) == Carrier::Drop);
static_assert(ChooseNativePacketCarrier(0x07,same_map,fully_granted()) == Carrier::Server);
static_assert(ChooseNativePacketCarrier(0x04,same_map,fully_granted()) == Carrier::Server);
static_assert(ChooseNativePacketCarrier(0x05,same_map,fully_granted()) == Carrier::Server);
static_assert(ChooseNativePacketCarrier(0x14,same_map,fully_granted()) == Carrier::Server);
static_assert(ChooseNativePacketCarrier(0x44,same_map,fully_granted()) == Carrier::Drop);

int main() {
    const auto route=[](u32 ch,const PacketEnds &p,const PeerRouteLease &l) {
        return ChooseNativePacketCarrier(ch,p,l);
    };
    auto l=fully_granted();
    assert(route(0x06,same_map,l)==Carrier::DirectPeer);
    l.local_opt_in=false; assert(route(0x06,same_map,l)==Carrier::Server);l.local_opt_in=true;
    l.remote_opt_in=false; assert(route(0x06,same_map,l)==Carrier::Server);l.remote_opt_in=true;
    l.same_party_session=false; assert(route(0x06,same_map,l)==Carrier::Server);l.same_party_session=true;
    l.session_authenticated=false;assert(route(0x06,same_map,l)==Carrier::Server);l.session_authenticated=true;
    l.peer_authenticated=false;assert(route(0x06,same_map,l)==Carrier::Server);l.peer_authenticated=true;
    l.direct_datagram_verified=false;assert(route(0x06,same_map,l)==Carrier::Server);l.direct_datagram_verified=true;
    l.server_route_granted=false;assert(route(0x06,same_map,l)==Carrier::Server);l.server_route_granted=true;
    l.has_common_protocol=false;assert(route(0x06,same_map,l)==Carrier::Server);l.has_common_protocol=true;
    l.granted_sender_id={};assert(route(0x06,same_map,l)==Carrier::Server);l.granted_sender_id="hunter-A";
    l.granted_receiver_id={};assert(route(0x06,same_map,l)==Carrier::Server);l.granted_receiver_id="hunter-B";
    l.sender_or_receiver_hostile=true;assert(route(0x06,same_map,l)==Carrier::Server);l.sender_or_receiver_hostile=false;
    l.local_world_epoch++;assert(route(0x06,same_map,l)==Carrier::Server);l.local_world_epoch--;
    l.approved_sender_map=0x102;assert(route(0x06,same_map,l)==Carrier::Server);l.approved_sender_map=0x101;
    l.approved_target_map=0x102;assert(route(0x06,same_map,l)==Carrier::Server);l.approved_target_map=0x101;
    l.lease_expiry_ms=10000;assert(route(0x06,same_map,l)==Carrier::Server);l.lease_expiry_ms=12000;
    l.last_authenticated_direct_probe_ms=7499; assert(route(0x06,same_map,l)==Carrier::Server);
    l.last_authenticated_direct_probe_ms=10001;assert(route(0x06,same_map,l)==Carrier::Server);
    l.last_authenticated_direct_probe_ms=7500;assert(route(0x06,same_map,l)==Carrier::DirectPeer);
    l.last_authenticated_direct_probe_ms=9900;
    // All direct cases remain within 0x06 and the same map, regardless of
    // upstream hostile/enemy-only special native channel rules.
    for (u32 ch=0;ch<=0x44;++ch) {
        const auto decision=route(ch,same_map,l);
        if (decision==Carrier::DirectPeer) assert(ch==0x06);
        if (NativeChannelPolicy(ch)==ChannelPolicy::Ours ||
            NativeChannelPolicy(ch)==ChannelPolicy::Drop)
            assert(decision==Carrier::Drop);
    }
    std::puts("SHYT_PLAYABLE_HYBRID_V1_UPSTREAM_NATIVE_ROUTING_POLICY_PASS");
    std::puts("This is policy-only; no live client, server or 5-player support was changed.");
    return 0;
}
