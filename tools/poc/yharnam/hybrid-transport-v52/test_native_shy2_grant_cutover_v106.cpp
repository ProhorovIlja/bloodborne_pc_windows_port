// SPDX-License-Identifier: GPL-2.0-or-later
// Compiles full V84 sealed TLS envelope -> V91 five signed NAT messages ->
// V89 directional keys -> V106 paired SHY2 AES-GCM game frames.
// Real OS UDP socket tests exist separately: test_nat_probe_v91.cpp and
// test_native_game_shy2_udp_loopback.cpp. This does NOT arm public Direct.
#include "sh_native_shy2_grant_cutover_v106.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>
using namespace SeamlessHunt::Hybrid;
static std::array<std::uint8_t,32> Id(unsigned seed) {
    std::array<std::uint8_t,32> v{};
    for(unsigned i=0;i<v.size();++i)
        v[i]=static_cast<std::uint8_t>(seed+i);
    return v;
}
static std::string Hex(std::span<const std::uint8_t> bytes) {
    static constexpr char digits[]="0123456789abcdef";
    std::string output;
    for(auto b:bytes) {
        output.push_back(digits[b>>4]);
        output.push_back(digits[b&15]);
    }
    return output;
}
struct IdentityState {
    bool available=true;
    NativeOfferIdentityV84 live{};
};
static bool Identity(NativeOfferIdentityV84& out,void* ptr) noexcept {
    auto& s=*static_cast<IdentityState*>(ptr);
    if(!s.available)return false;
    out=s.live;return true;
}
struct World {
    bool available=true;
    ChannelAuthority rights{};
};
static bool CurrentWorldAuthority(ChannelAuthority& out,void* ptr) noexcept {
    auto& s=*static_cast<World*>(ptr);
    if(!s.available)return false;
    out=s.rights;return true;
}
static ChannelAuthority Allowed() {
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=
      a.peer_binding_verified=a.both_on_same_authorized_team=
      a.protocol_compatible=a.map_known=a.map_epoch_verified=
      a.both_on_same_map=a.enemy_stream_authorized=
      a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;
    return a;
}
static SecurePeerOfferV84 Offer(
    std::array<std::uint8_t,32> self,
    std::array<std::uint8_t,32> peer,
    std::uint64_t session,
    std::uint32_t endpoint_ip,std::uint16_t endpoint_port,
    std::uint32_t virtual_ip,std::uint16_t virtual_port) {
    SecurePeerOfferV84 o{};
    o.recipient_account=self;
    o.sender_account=peer;
    o.session_epoch=session;
    o.pair_binding=88442;
    o.world_revision=975;
    o.issued_ms=1000;
    o.expires_ms=4000;
    o.peer_ipv4_nbo=endpoint_ip;
    o.peer_port_nbo=endpoint_port;
    o.peer_virtual_ipv4_nbo=virtual_ip;
    o.peer_virtual_port_nbo=virtual_port;
    o.direction_key=Id(120);
    return o;
}
static std::string SealedTlsLine(const SecurePeerOfferV84& offer,
                                 const std::array<std::uint8_t,32>& key) {
    SealedPeerOffersV84 tls{};
    assert(tls.InstallChannelKey(key));
    std::vector<std::uint8_t> wire;
    assert(tls.Seal(offer,1100,wire));
    auto line=std::string(NativeSealedGrantInboxV84::kPrefix)
        +Hex(wire)+"\n";
    CryptoDetail::Erase(wire);
    return line;
}
static void U32(std::vector<std::uint8_t>& bytes,std::uint32_t v) {
    for(unsigned i=0;i<32;i+=8)
        bytes.push_back(static_cast<std::uint8_t>(v>>i));
}
static std::vector<std::uint8_t> Frame(char sender,
                                        std::uint32_t channel=0x06,
                                        bool reliable=false) {
    std::vector<std::uint8_t> bytes{255,255,255,255,'S','H','A','D',
                                   0x40,1,1,static_cast<std::uint8_t>(sender)};
    U32(bytes,1);U32(bytes,1);U32(bytes,0);
    bytes.push_back(1);bytes.push_back(0);
    bytes.push_back(reliable?1:0);
    U32(bytes,17);U32(bytes,8);U32(bytes,channel);U32(bytes,0);
    return bytes;
}
int main() {
    const auto id_a=Id(7);
    const auto id_b=Id(47);
    const PhysicalV4 addr_a{0x0100007fU,0x2101U};
    const PhysicalV4 addr_b{0x0100007fU,0x2102U};
    const VirtualV4 virtual_a{0x0100000aU,0x3101U};
    const VirtualV4 virtual_b{0x0200000aU,0x3102U};
    const auto grant_a=Offer(id_a,id_b,101,addr_b.addr_nbo,
                             addr_b.port_nbo,virtual_b.addr_nbo,
                             virtual_b.port_nbo);
    const auto grant_b=Offer(id_b,id_a,202,addr_a.addr_nbo,
                             addr_a.port_nbo,virtual_a.addr_nbo,
                             virtual_a.port_nbo);
    // Session epochs are RECIPIENT SPECIFIC; the shared world revision
    // used in the encrypted UDP header must be identical to both sides.
    assert(grant_a.session_epoch!=grant_b.session_epoch);
    const auto tls_a=Id(17);
    const auto tls_b=Id(87);
    IdentityState a_state{true,{id_a,id_b,101,975,true}};
    IdentityState b_state{true,{id_b,id_a,202,975,true}};
    NativeSealedGrantInboxV84 inbox_a,inbox_b;
    assert(inbox_a.BeginTrustedTls(tls_a,a_state.live,1,Identity,&a_state));
    assert(inbox_b.BeginTrustedTls(tls_b,b_state.live,1,Identity,&b_state));
    assert(inbox_a.ReceiveSealedTlsLine(SealedTlsLine(grant_a,tls_a),1100));
    assert(inbox_b.ReceiveSealedTlsLine(SealedTlsLine(grant_b,tls_b),1100));
    World world_a{},world_b{};
    world_a.rights=world_b.rights=Allowed();
    NativeGameAeadIngress rx_a,rx_b;
    NativeGameAeadEgress tx_a,tx_b;
    NatProbeProofV91 proof_a(NatProbeProofV91::Role::Initiator);
    NatProbeProofV91 proof_b(NatProbeProofV91::Role::Responder);
    assert(proof_a.Start(grant_a,1100));
    assert(proof_b.Start(grant_b,1100));
    // A random, cryptographically valid mTLS grant is NOT sufficient
    // until five same-socket signed NAT steps have succeeded.
    assert(!NativeShy2GrantCutoverV106::Install(
        inbox_a,proof_a,0,rx_a,tx_a,"A","B",
        CurrentWorldAuthority,&world_a,1101));
    NatProbeCodecV91::Wire w1{},w2{},w3{},w4{},w5{};
    assert(proof_a.Initial(1101,w1));
    assert(proof_b.Reply(w1,addr_a.addr_nbo,addr_a.port_nbo,1102,w2));
    assert(proof_a.Reply(w2,addr_b.addr_nbo,addr_b.port_nbo,1103,w3));
    assert(proof_b.Reply(w3,addr_a.addr_nbo,addr_a.port_nbo,1104,w4));
    assert(proof_a.Complete(w4,addr_b.addr_nbo,addr_b.port_nbo,1105,w5));
    assert(!NativeShy2GrantCutoverV106::Install(
        inbox_a,proof_a,0,rx_a,tx_a,"A","B",
        CurrentWorldAuthority,&world_a,1105)); // receipt NOT sent
    assert(proof_a.ReceiptSent(w5));
    assert(proof_b.CompleteResponder(w5,addr_a.addr_nbo,
                                     addr_a.port_nbo,1106));
    assert(proof_a.VerifiedFor(grant_a,1106));
    assert(proof_b.VerifiedFor(grant_b,1106));
    // Slot bounds and invalid original-game authority fail CLOSED.
    assert(!NativeShy2GrantCutoverV106::Install(
        inbox_a,proof_a,4,rx_a,tx_a,"A","B",
        CurrentWorldAuthority,&world_a,1107));
    world_a.rights.map_epoch_verified=false;
    assert(!NativeShy2GrantCutoverV106::Install(
        inbox_a,proof_a,0,rx_a,tx_a,"A","B",
        CurrentWorldAuthority,&world_a,1107));
    world_a.rights.map_epoch_verified=true;
    // Authentic pair proof tied to another TLS stream cannot be reused.
    assert(!NativeShy2GrantCutoverV106::Install(
        inbox_b,proof_a,0,rx_b,tx_b,"B","A",
        CurrentWorldAuthority,&world_b,1107));
    assert(NativeShy2GrantCutoverV106::Install(
        inbox_a,proof_a,0,rx_a,tx_a,"A","B",
        CurrentWorldAuthority,&world_a,1107));
    assert(NativeShy2GrantCutoverV106::Install(
        inbox_b,proof_b,0,rx_b,tx_b,"B","A",
        CurrentWorldAuthority,&world_b,1107));
    // No duplicate installation, shared nonce or fifth remote peer.
    assert(!NativeShy2GrantCutoverV106::Install(
        inbox_a,proof_a,0,rx_a,tx_a,"A","B",
        CurrentWorldAuthority,&world_a,1108));
    const auto game_a=Frame('A');
    const auto game_b=Frame('B');
    std::vector<std::uint8_t> wire_a,wire_b;
    assert(tx_a.Seal(addr_b,game_a,1109,wire_a));
    assert(tx_b.Seal(addr_a,game_b,1109,wire_b));
    assert(IsSHY2(wire_a) && IsSHY2(wire_b));
    assert(wire_a!=wire_b);
    auto received_b=rx_b.Receive(addr_a,wire_a,1110);
    auto received_a=rx_a.Receive(addr_b,wire_b,1110);
    assert(received_b.status==NativeRxStatus::Game &&
           received_b.native_game_frame==game_a &&
           received_b.sender.addr_nbo==virtual_a.addr_nbo);
    assert(received_a.status==NativeRxStatus::Game &&
           received_a.native_game_frame==game_b &&
           received_a.sender.addr_nbo==virtual_b.addr_nbo);
    assert(rx_b.Receive(addr_a,wire_a,1111).status==
           NativeRxStatus::Dropped); // replay
    assert(rx_a.Receive(addr_a,wire_b,1111).status==
           NativeRxStatus::Dropped); // wrong physical
    assert(!tx_a.Seal(addr_b,Frame('A',0x14,true),1112,wire_a));
    assert(!tx_b.Seal(addr_a,Frame('B',0x2f),1112,wire_b));
    // World authority is refreshed for EVERY packet.
    world_a.rights.map_epoch_verified=false;
    assert(!tx_a.Seal(addr_b,game_a,1113,wire_a));
    world_a.rights.map_epoch_verified=true;
    world_b.available=false;
    assert(tx_a.Seal(addr_b,game_a,1114,wire_a));
    assert(rx_b.Receive(addr_a,wire_a,1114).status==
           NativeRxStatus::Dropped);
    world_b.available=true;
    assert(rx_b.Receive(addr_a,wire_a,1115).status==
           NativeRxStatus::Dropped); // revoked, cannot un-revoke
    rx_a.RevokeAll();rx_b.RevokeAll();
    tx_a.RevokeAll();tx_b.RevokeAll();
    assert(!tx_a.Seal(addr_b,game_a,1116,wire_a));
    // TLS freshness still binds the grant after one side opts out.
    a_state.live.locally_opted_in=false;
    assert(!inbox_a.PendingForNat(1117));
    inbox_a.Revoke();inbox_b.Revoke();
    return 0;
}
