// SPDX-License-Identifier: GPL-2.0-or-later
// V247: actual Linux kernel UDP sockets, original YT 1.3.1 Noise/AEAD,
// and original GameLinkPeer delivery. LOCAL LOOPBACK ONLY, NO REAL NAT.
#include "hybrid_peer_noise_v244.h"
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <span>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;
using namespace BloodborneCoop::SHYTHybrid::PeerNoiseV244;
namespace {
struct Udp {
    int fd = -1;
    sockaddr_in address{};
    Udp() {
        fd = ::socket(AF_INET, SOCK_DGRAM, 0);
        assert(fd >= 0);
        address.sin_family=AF_INET;
        address.sin_port=0;
        address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        assert(::bind(fd,reinterpret_cast<sockaddr*>(&address),sizeof(address))==0);
        socklen_t len=sizeof(address);
        assert(::getsockname(fd,reinterpret_cast<sockaddr*>(&address),&len)==0);
        timeval timeout{2,0};
        assert(::setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))==0);
    }
    Udp(const Udp&)=delete;
    Udp& operator=(const Udp&)=delete;
    ~Udp(){ if(fd>=0) ::close(fd); }
    void Send(const sockaddr_in& target, std::span<const u8> bytes) const {
        assert(!bytes.empty() && bytes.size()<=1200);
        assert(::sendto(fd,bytes.data(),bytes.size(),0,
              reinterpret_cast<const sockaddr*>(&target),sizeof(target))==
              static_cast<ssize_t>(bytes.size()));
    }
    std::vector<u8> Take() const {
        std::array<u8,1201> b{};
        sockaddr_in from{};
        socklen_t len=sizeof(from);
        ssize_t count=::recvfrom(fd,b.data(),b.size(),0,
                          reinterpret_cast<sockaddr*>(&from),&len);
        assert(count>0 && count<=1200);
        assert(from.sin_addr.s_addr==htonl(INADDR_LOOPBACK));
        return {b.begin(),b.begin()+count};
    }
};
Key Secret(u8 start) {
    Key s{};
    for(size_t i=0;i<s.size();++i) s[i]=static_cast<u8>(start+i);
    return s;
}
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
    p.now_ms=10000;p.lease_expiry_ms=12000;
    p.last_authenticated_direct_probe_ms=9990;
    return p;
}
GameFrame Movement(u32 sequence,u8 value,u32 ack=0) {
    GameFrame f{};
    f.sender="A";f.instance=17;f.peer_instance=29;f.ack=ack;
    f.entries.push_back({PacketClass::Unreliable,sequence,
                         std::vector<u8>{6,0,0,0,1,0,0,0,value}});
    return f;
}
}
int main() {
    Udp hunter_a, hunter_b, server_relay_fixture;
    const PeerCryptoScopeV241 scope{"party42","A","B",17,29,42,0x101};
    const Key server_pinned_b=Secret(19);
    Initiator initiator(scope,LinkAuth::Noise::PublicOf(server_pinned_b));
    Responder responder(scope,server_pinned_b);
    auto hello=initiator.Start(Secret(44));
    assert(hello);
    hunter_a.Send(hunter_b.address,*hello);
    const auto received_hello=hunter_b.Take();
    const auto answer=responder.Answer(received_hello,Secret(101));
    assert(answer);
    hunter_b.Send(hunter_a.address,answer->answer);
    const auto arrived_answer=hunter_a.Take();
    const auto keys=initiator.Finish(arrived_answer);
    assert(keys && *keys==answer->keys);
    PeerCryptoDatagramsV241 cipher_a(scope,true,keys->first,keys->second);
    PeerCryptoDatagramsV241 cipher_b(scope,false,answer->keys.second,answer->keys.first);

    GameLinkPeer receiver("B",29);
    DirectIngressIdentity incoming{"A",17,29,1100,"B","party42"};
    DirectEgressIdentity outgoing{"A","B","party42",17,29,true,1100};
    PeerRouteLease lease=Lease();
    const PacketEnds ends{0x101,0x101,EnemyPart::None,EnemyPart::None};
    unsigned direct=0,through_server=0;
    auto send_direct=[&](const GameFrame& frame) -> bool {
        const auto sealed=cipher_a.SealMovement(frame);
        if(!sealed) return false;
        hunter_a.Send(hunter_b.address,*sealed);
        auto wire=hunter_b.Take();
        const auto clear=cipher_b.OpenMovement(wire);
        assert(clear && AcceptAuthenticatedDirectMovement(*clear,ends,lease,incoming));
        auto delivered=receiver.Receive(*clear,lease.now_ms);
        assert(delivered.size()==1 && delivered[0]==frame.entries[0].packet);
        ++direct;
        // Attempt to process exact same authenticated datagram twice.
        assert(!cipher_b.OpenMovement(wire));
        return true;
    };
    // Test-only stand-in for shadNet relay: real UDP sockets and original
    // GameFrame serialization, NOT real shadNet authentication/world rules.
    auto server_send=[&](const GameFrame& frame) -> bool {
        auto serialized=EncodeGameFrame(frame);
        hunter_a.Send(server_relay_fixture.address,serialized);
        auto received=server_relay_fixture.Take();
        auto decoded=DecodeGameFrame(received);
        assert(decoded && *decoded==frame);
        server_relay_fixture.Send(hunter_b.address,received);
        auto delivered_wire=hunter_b.Take();
        auto forwarded=DecodeGameFrame(delivered_wire);
        assert(forwarded && *forwarded==frame);
        auto delivered=receiver.Receive(*forwarded,lease.now_ms);
        if(frame.entries.empty()) assert(delivered.empty());
        else assert(delivered.size()==1 && delivered[0]==frame.entries[0].packet);
        ++through_server;
        return true;
    };
    assert(SendExistingGameFrameV240(Movement(1,42),ends,lease,outgoing,
              send_direct,server_send)==EgressResult::Direct);
    assert(direct==1 && through_server==0);
    // A reliable ACK on a movement frame MUST still traverse server relay.
    assert(SendExistingGameFrameV240(Movement(2,43,99),ends,lease,outgoing,
              send_direct,server_send)==EgressResult::Direct);
    assert(direct==2 && through_server==1);
    // After losing P2P eligibility, relay uses same original GameLinkPeer.
    lease.lease_expiry_ms=lease.now_ms;
    assert(SendExistingGameFrameV240(Movement(3,44),ends,lease,outgoing,
              send_direct,server_send)==EgressResult::Server);
    assert(direct==2 && through_server==2);
    // Out-of-order direct frame can be authenticated but not re-delivered.
    auto late=cipher_a.SealMovement(Movement(2,43));
    assert(late);
    hunter_a.Send(hunter_b.address,*late);
    auto opened=cipher_b.OpenMovement(hunter_b.Take());
    assert(opened && receiver.Receive(*opened,lease.now_ms).empty());
    std::puts("SHYT_V247_REAL_LOCAL_UDP_NOISE_GAMEFRAME_FALLBACK_PASS");
}
