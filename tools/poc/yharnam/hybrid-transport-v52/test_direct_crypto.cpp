// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_direct_crypto.hpp"
#include "sh_direct_ingress.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>
using namespace SeamlessHunt::Hybrid;

static std::array<std::uint8_t,32> Key(std::uint8_t start=0) {
    std::array<std::uint8_t,32> k{};
    for (unsigned i=0;i<32;++i)k[i]=static_cast<std::uint8_t>(i+start);
    return k;
}
static PeerTicket Ticket() {
    PeerTicket t{};
    t.session_epoch=300;t.pair_binding=700;
    t.authenticated_sender=11;t.local_receiver=22;
    t.expires_at_ms=20000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static Grant GrantFor(const PeerTicket& t) {
    Grant g{};
    g.session_epoch=t.session_epoch;
    g.peer_binding=t.pair_binding;
    g.valid_until_ms=t.expires_at_ms;
    g.verified_server_authorization=g.local_consent=g.peer_consent=
        g.protocol_compatible=true;
    return g;
}
static ChannelAuthority AuthorizedWorld() {
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=a.peer_binding_verified=
        a.both_on_same_authorized_team=a.protocol_compatible=
        a.map_known=a.map_epoch_verified=a.both_on_same_map=
        a.enemy_stream_authorized=a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;
    return a;
}
static void U32(std::vector<std::uint8_t>& b,std::uint32_t v) {
    for(unsigned i=0;i<32;i+=8)b.push_back(static_cast<std::uint8_t>(v>>i));
}
static void U16(std::vector<std::uint8_t>& b,std::uint16_t v) {
    b.push_back(static_cast<std::uint8_t>(v));
    b.push_back(static_cast<std::uint8_t>(v>>8));
}
static std::vector<std::uint8_t> NativeGame(std::uint32_t ch) {
    std::vector<std::uint8_t> b{255,255,255,255,'S','H','A','D',0x40,1,1,'X'};
    U32(b,1);U32(b,1);U32(b,0);U16(b,1);
    b.push_back(ch>6?1:0);U32(b,11);U32(b,8);U32(b,ch);U32(b,0);
    return b;
}
int main() {
    // Independently generated Python hashlib HMAC-SHA256 reference vector,
    // full digest for key 00..1f and ASCII "Seamless Hunt P2P test":
    // 5852fea1bbcfe8f4f9bd9fbda71dbd8057969b8abfe692e74b546aa026648593
    const std::array<std::uint8_t,16> expected{
        0x58,0x52,0xfe,0xa1,0xbb,0xcf,0xe8,0xf4,
        0xf9,0xbd,0x9f,0xbd,0xa7,0x1d,0xbd,0x80};
    DirectionMac mac, other;
    const auto key=Key();
    const auto otherkey=Key(1);
    const std::array<std::uint8_t,32> zero{};
    assert(!mac.InstallKey(zero));
    assert(!mac.InstallKey({}));
    assert(mac.InstallKey(key));
    assert(other.InstallKey(otherkey));
    constexpr std::string_view message="Seamless Hunt P2P test";
    const auto data=std::span<const std::uint8_t>(
        reinterpret_cast<const std::uint8_t*>(message.data()),message.size());
    std::array<std::uint8_t,16> tag{};
    assert(mac.Tag(data,tag));
    assert(tag==expected);
    assert(mac.Verify(data,expected));
    assert(!other.Verify(data,expected));
    auto broken=expected;
    broken[15]^=1;
    assert(!mac.Verify(data,broken));
    assert(!mac.Verify({},expected));

    const auto t=Ticket();
    DirectEncoder enc;
    DirectReceiver rx;
    std::vector<std::uint8_t> datagram;
    assert(!enc.Encode(DirectKind::Probe,{},100,datagram));
    assert(enc.Arm(t,mac,100));
    assert(rx.Arm(t,100));
    assert(enc.Encode(DirectKind::Probe,{},101,datagram));
    assert(datagram.size()==68);
    DirectFrame parsed{};
    assert(!rx.Receive(datagram,102,DirectionMac::VerifyCallback,&other,parsed));
    assert(rx.Receive(datagram,102,DirectionMac::VerifyCallback,&mac,parsed));
    assert(parsed.sequence==1 && parsed.kind==DirectKind::Probe);
    assert(!rx.Receive(datagram,102,DirectionMac::VerifyCallback,&mac,parsed));
    assert(enc.Encode(DirectKind::GameData,NativeGame(0x06),103,datagram));
    auto forged=datagram; forged[DirectReceiver::kHeaderBytes]^=1;
    assert(!rx.Receive(forged,104,DirectionMac::VerifyCallback,&mac,parsed));
    assert(rx.Receive(datagram,104,DirectionMac::VerifyCallback,&mac,parsed));
    assert(parsed.sequence==2 && parsed.kind==DirectKind::GameData);
    assert(EligibleNativeWireFrame(parsed.payload,"X",AuthorizedWorld()).direct_eligible);
    assert(!EligibleNativeWireFrame(parsed.payload,"Y",AuthorizedWorld()).direct_eligible);
    std::vector<std::uint8_t> discarded;
    assert(!enc.Encode(DirectKind::GameData,{},105,discarded));
    assert(!enc.Encode(DirectKind::Probe,std::array<std::uint8_t,1>{1},105,discarded));
    assert(!enc.Encode(DirectKind::GameData,
        std::vector<std::uint8_t>(DirectReceiver::kMaxPayloadBytes+1,1),
        105,discarded));
    assert(discarded.empty());
    assert(enc.Encode(DirectKind::Heartbeat,{},106,datagram));
    assert(rx.Receive(datagram,106,DirectionMac::VerifyCallback,&mac,parsed));
    mac.Clear();
    assert(!mac.ready());
    assert(!enc.Encode(DirectKind::Heartbeat,{},107,discarded));
    assert(!rx.Receive(datagram,107,DirectionMac::VerifyCallback,&mac,parsed));
    assert(mac.InstallKey(key));
    assert(!enc.Encode(DirectKind::Heartbeat,{},20001,discarded));
    assert(!rx.Receive(datagram,20001,DirectionMac::VerifyCallback,&mac,parsed));
    assert(!rx.armed());
    // A complete game ingress must use *real* MAC callback before decoding.
    DirectIngress ingress;
    assert(ingress.Arm(t,GrantFor(t),"X",100));
    assert(enc.Arm(t,mac,100));
    std::span<const std::uint8_t> game{};
    for (int i=0;i<3;i++) {
        assert(enc.Encode(DirectKind::Probe,{},110+i,datagram));
        assert(ingress.Receive(datagram,110+i,DirectionMac::VerifyCallback,
               &mac,AuthorizedWorld(),game)==IngressStatus::AuthenticatedProbeOrHeartbeat);
    }
    assert(ingress.CurrentPath(120)==Path::Direct);
    assert(enc.Encode(DirectKind::GameData,NativeGame(0x06),120,datagram));
    assert(ingress.Receive(datagram,120,DirectionMac::VerifyCallback,
           &mac,AuthorizedWorld(),game)==IngressStatus::AuthenticatedGame);
    assert(!game.empty());
    assert(enc.Encode(DirectKind::GameData,NativeGame(0x2F),125,datagram));
    assert(ingress.Receive(datagram,125,DirectionMac::VerifyCallback,
           &mac,AuthorizedWorld(),game)==IngressStatus::Reject);
    assert(game.empty());
    assert(ingress.CurrentPath(2112)==Path::Direct);
    assert(ingress.CurrentPath(2113)==Path::Relay);
    return 0;
}
