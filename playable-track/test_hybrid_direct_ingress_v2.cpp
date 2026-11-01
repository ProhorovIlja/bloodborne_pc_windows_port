// SPDX-License-Identifier: GPL-2.0-or-later
// REAL original Yharnam Together GameLinkPeer / GameFrame tests.
// Direct and server packets share ONE receiver GameLinkPeer sequence state.
#include "hybrid_direct_ingress_v2.h"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;

static constexpr PacketEnds map{0x101,0x101,EnemyPart::None,EnemyPart::None};

static PeerRouteLease lease() {
    PeerRouteLease l{};
    l.local_opt_in=true;l.remote_opt_in=true;
    l.same_party_session=true;l.session_authenticated=true;
    l.peer_authenticated=true;l.direct_datagram_verified=true;
    l.server_route_granted=true;l.has_common_protocol=true;
    l.authority_epoch=42;l.local_world_epoch=42;
    l.approved_sender_map=0x101;l.approved_target_map=0x101;
    l.now_ms=10000;l.lease_expiry_ms=12000;
    l.last_authenticated_direct_probe_ms=9990;
    return l;
}
static std::vector<u8> movement(u8 value) {
    // Real native NetSync packet: channel u32=0x06, size u32, payload.
    return {6,0,0,0, 1,0,0,0, value};
}
static GameFrame make_frame(u32 seq,u8 value) {
    GameFrame f{};
    f.sender="hunter-A";f.instance=17;f.peer_instance=29;
    f.entries.push_back({PacketClass::Unreliable,seq,movement(value)});
    return f;
}
int main() {
    auto l=lease();
    DirectIngressIdentity id{"hunter-A",17,29,1100};
    GameLinkPeer receiver("hunter-B",29);
    const auto ingest=[&](const GameFrame& f,bool direct) {
        if (direct && !AcceptAuthenticatedDirectMovement(f,map,l,id))
            return std::vector<std::vector<u8>>{};
        // This must be the SAME receiver regardless of UDP carrier:
        // deduplication is owned by the original YT GameLinkPeer.
        return receiver.Receive(f,l.now_ms);
    };
    // Direct movement is accepted only with a valid authority lease.
    assert(AcceptAuthenticatedDirectMovement(make_frame(1,42),map,l,id));
    auto first=ingest(make_frame(1,42),true);
    assert(first.size()==1 && first[0]==movement(42));
    // Identical frame arriving via server relay must NOT be applied again.
    assert(ingest(make_frame(1,42),false).empty());
    assert(receiver.DroppedOld()==1);
    // A newer relay movement works after direct route is lost.
    l.lease_expiry_ms=10000;
    assert(ChooseNativePacketCarrier(0x06,map,l)==Carrier::Server);
    assert(ingest(make_frame(2,43),true).empty());
    auto second=ingest(make_frame(2,43),false);
    assert(second.size()==1 && second[0]==movement(43));
    // Delayed previously valid direct transport frame cannot resurrect
    // old movement; the original stream detects the duplicate.
    l.lease_expiry_ms=12000;
    assert(ingest(make_frame(1,42),true).empty());
    assert(receiver.DroppedOld()==2);
    // Reordered packet 4 beats late packet 3 on SAME stream.
    assert(ingest(make_frame(4,45),true).size()==1);
    assert(ingest(make_frame(3,44),false).empty());
    assert(receiver.DroppedOld()==3);

    auto bad=make_frame(5,46);
    bad.sender="different";assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.instance=16;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.peer_instance=28;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.peer_instance=0;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.entries.clear();
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.entries[0].packet_class=PacketClass::Reliable;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.entries[0].packet[0]=0x07;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.entries[0].packet[4]=2;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.entries[0].packet.resize(7);
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.entries[0].packet.resize(1101);
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);bad.entries.push_back({PacketClass::Reliable,0,movement(1)});
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    bad=make_frame(5,46);
    auto no_id=id;no_id.server_authorized_remote_id={};
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,no_id));
    no_id=id;no_id.local_instance=0;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,no_id));
    no_id=id;no_id.server_authorized_remote_instance=0;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,no_id));
    auto other_map=map;other_map.target_map=0x102;
    assert(!AcceptAuthenticatedDirectMovement(bad,other_map,l,id));
    l.authority_epoch++;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));
    l=lease();
    l.last_authenticated_direct_probe_ms=0;
    assert(!AcceptAuthenticatedDirectMovement(bad,map,l,id));

    // A native reliable message still uses the server and original
    // reliable order/retransmit semantics, NEVER a P2P game route.
    l=lease();
    GameFrame reliable{};
    reliable.sender="hunter-A";reliable.instance=17;reliable.peer_instance=29;
    reliable.entries.push_back({PacketClass::Reliable,0,{7,0,0,0,1,0,0,0,0x99}});
    assert(!AcceptAuthenticatedDirectMovement(reliable,map,l,id));
    auto rel=ingest(reliable,false);
    assert(rel.size()==1);
    assert(ingest(reliable,false).empty());

    std::puts("SHYT_PLAYABLE_V131_REAL_GAMELINK_CROSS_CARRIER_DEDUP_FAILOVER_PASS");
    std::puts("Prototype ingress only: no live authenticated UDP or YT client patch.");
    return 0;
}
