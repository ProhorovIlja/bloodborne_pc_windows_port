// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_direct_ingress.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
using namespace SeamlessHunt::Hybrid;

// Test-only deterministic tag; deliberately NOT a cryptographic MAC.
static std::array<std::uint8_t,16> FakeMac(std::span<const std::uint8_t> b) {
    std::array<std::uint8_t,16> m{};
    for (std::size_t i=0;i<b.size();++i)
        m[i % m.size()] = static_cast<std::uint8_t>(
            (std::uint32_t(m[i % m.size()])*17U + b[i] + 37U)&255U);
    return m;
}
static bool Check(std::span<const std::uint8_t> b,
                  std::span<const std::uint8_t> tag, void*) noexcept {
    const auto expected=FakeMac(b);
    return std::equal(expected.begin(),expected.end(),tag.begin(),tag.end());
}
static void U16(std::vector<std::uint8_t>& b,std::uint16_t n) {
    b.push_back(static_cast<std::uint8_t>(n));
    b.push_back(static_cast<std::uint8_t>(n>>8));
}
static void U32(std::vector<std::uint8_t>& b,std::uint32_t n) {
    for(unsigned i=0;i<32;i+=8)
        b.push_back(static_cast<std::uint8_t>(n>>i));
}
static void U64(std::vector<std::uint8_t>& b,std::uint64_t n) {
    for(unsigned i=0;i<64;i+=8)
        b.push_back(static_cast<std::uint8_t>(n>>i));
}
static PeerTicket Ticket() {
    PeerTicket t{};
    t.session_epoch=300;t.pair_binding=700;
    t.authenticated_sender=11;t.local_receiver=22;
    t.expires_at_ms=20000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static Grant SelectGrant() {
    Grant g{};
    g.session_epoch=300;g.peer_binding=700;g.valid_until_ms=20000;
    g.verified_server_authorization=g.local_consent=g.peer_consent=
        g.protocol_compatible=true;
    return g;
}
static ChannelAuthority World() {
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=a.peer_binding_verified=
        a.both_on_same_authorized_team=a.protocol_compatible=
        a.map_known=a.map_epoch_verified=a.both_on_same_map=
        a.enemy_stream_authorized=a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;
    return a;
}
static std::vector<std::uint8_t> Game(std::uint32_t channel) {
    std::vector<std::uint8_t> b{255,255,255,255,'S','H','A','D',0x40,1,1,'X'};
    U32(b,1);U32(b,1);U32(b,0);U16(b,1);
    b.push_back(channel>6?1:0);U32(b,11);U32(b,8);
    U32(b,channel);U32(b,0);
    return b;
}
static void Seal(std::vector<std::uint8_t>& b) {
    const auto n=b.size()-DirectReceiver::kTagBytes;
    const auto sig=FakeMac(std::span<const std::uint8_t>(b.data(),n));
    std::copy(sig.begin(),sig.end(),b.begin()+static_cast<std::ptrdiff_t>(n));
}
static std::vector<std::uint8_t> Wire(
    DirectKind kind,std::uint64_t seq,std::vector<std::uint8_t> game={}) {
    const auto t=Ticket();
    std::vector<std::uint8_t> b{'S','H','P','1',1,
        static_cast<std::uint8_t>(kind),0,0};
    U64(b,t.session_epoch);U64(b,t.pair_binding);
    U64(b,t.authenticated_sender);U64(b,t.local_receiver);U64(b,seq);
    U16(b,static_cast<std::uint16_t>(game.size()));U16(b,0);
    b.insert(b.end(),game.begin(),game.end());
    b.resize(b.size()+DirectReceiver::kTagBytes);
    Seal(b);
    return b;
}
static IngressStatus Receive(DirectIngress& rx,
                            const std::vector<std::uint8_t>& datagram,
                            const ChannelAuthority& auth,
                            std::int64_t now=120) {
    std::span<const std::uint8_t> out{};
    const auto status=rx.Receive(datagram,now,Check,nullptr,auth,out);
    assert((status==IngressStatus::AuthenticatedGame)==!out.empty());
    return status;
}
int main() {
    DirectIngress rx;
    auto t=Ticket();
    auto g=SelectGrant();
    auto a=World();
    assert(Receive(rx,Wire(DirectKind::Probe,1),a)==IngressStatus::Reject);
    g.peer_binding++;
    assert(!rx.Arm(t,g,"X",100));
    g=SelectGrant();g.valid_until_ms++;
    assert(!rx.Arm(t,g,"X",100));
    g=SelectGrant();
    assert(!rx.Arm(t,g,"",100));
    assert(rx.Arm(t,g,"X",100));
    assert(rx.CurrentPath(110)==Path::Relay);
    assert(Receive(rx,Wire(DirectKind::GameData,1,Game(0x06)),a)==IngressStatus::Reject);
    assert(Receive(rx,Wire(DirectKind::Heartbeat,2),a)==IngressStatus::Reject);
    assert(Receive(rx,Wire(DirectKind::Probe,3),a)==IngressStatus::AuthenticatedProbeOrHeartbeat);
    assert(Receive(rx,Wire(DirectKind::ProbeAck,4),a)==IngressStatus::AuthenticatedProbeOrHeartbeat);
    assert(rx.CurrentPath(120)==Path::Relay);
    assert(Receive(rx,Wire(DirectKind::Probe,5),a)==IngressStatus::AuthenticatedProbeOrHeartbeat);
    assert(rx.CurrentPath(120)==Path::Direct);
    assert(Receive(rx,Wire(DirectKind::GameData,6,Game(0x06)),a)==IngressStatus::AuthenticatedGame);
    assert(Receive(rx,Wire(DirectKind::GameData,6,Game(0x06)),a)==IngressStatus::Reject);
    assert(Receive(rx,Wire(DirectKind::GameData,7,Game(0x2F)),a)==IngressStatus::Reject);
    auto changed=World();changed.map_epoch_verified=false;
    assert(Receive(rx,Wire(DirectKind::GameData,8,Game(0x06)),changed)==IngressStatus::Reject);
    changed=World();changed.reliable_stream_handover_verified=false;
    assert(Receive(rx,Wire(DirectKind::GameData,9,Game(0x14)),changed)==IngressStatus::Reject);
    assert(Receive(rx,Wire(DirectKind::GameData,10,Game(0x06)),changed)==IngressStatus::AuthenticatedGame);
    auto forged=Wire(DirectKind::GameData,11,Game(0x06));
    forged[52]^=1;
    assert(Receive(rx,forged,a)==IngressStatus::Reject);
    assert(Receive(rx,Wire(DirectKind::GameData,11,Game(0x06)),a)==IngressStatus::AuthenticatedGame);
    assert(Receive(rx,Wire(DirectKind::Heartbeat,12),a,150)==IngressStatus::AuthenticatedProbeOrHeartbeat);
    assert(rx.CurrentPath(2149)==Path::Direct);
    assert(rx.CurrentPath(2151)==Path::Relay);
    assert(Receive(rx,Wire(DirectKind::GameData,13,Game(0x06)),a,2152)==IngressStatus::Reject);
    rx.Reset();
    assert(rx.CurrentPath(2153)==Path::Relay);
    assert(Receive(rx,Wire(DirectKind::Probe,14),a)==IngressStatus::Reject);
    return 0;
}
