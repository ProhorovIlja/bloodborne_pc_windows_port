// SPDX-License-Identifier: GPL-2.0-or-later
// V289 original YT compiled bbcoop::Envelope, real Monocypher signature,
// synthetic authoritative Team. No active game or server credentials.
#include "yt_signed_grant_coop_stream_v289.h"
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>
namespace Grant=BloodborneCoop::SHYTHybrid::SignedPeerGrantV279;
namespace Bridge=BloodborneCoop::SHYTHybrid::SignedGrantCoopV289;
namespace Hybrid=BloodborneCoop::SHYTHybrid;
struct Member {
    std::string who;
    int current=2;
    const std::string& member() const{return who;}
    int state() const{return current;}
};
struct Team {
    std::string team="team-7",group="party-7";
    bool started_game=true;
    std::vector<Member> players{{"A",2},{"B",2}};
    const std::string& id() const{return team;}
    const std::string& party() const{return group;}
    bool started() const{return started_game;}
    int members_size() const{return static_cast<int>(players.size());}
    const Member& members(int i)const{return players.at(i);}
};
int main(){
    Grant::PubKey authority{};
    Grant::SecretKey signing{};
    std::array<u8,32> seed{};
    for(size_t i=0;i<seed.size();++i)seed[i]=static_cast<u8>(i+19);
    LinkMonocypher::crypto_eddsa_key_pair(
        signing.data(),authority.data(),seed.data());
    Grant::Scope s{};
    s.team="team-7";s.party="party-7";s.sender="A";s.receiver="B";
    s.sender_instance=17;s.receiver_instance=29;
    s.map=0x101;s.world_epoch=42;
    s.issued_unix_ms=1810000000000LL;
    s.expires_unix_ms=1810000010000LL;
    s.sender_ip_nbo=0x0100007f;s.receiver_ip_nbo=0x0200007f;
    s.sender_port_nbo=23001;s.receiver_port_nbo=23002;
    for(size_t i=0;i<32;++i)s.responder_noise_pub[i]=static_cast<u8>(i+2);
    for(size_t i=0;i<16;++i)s.grant_nonce[i]=static_cast<u8>(i+3);
    Team members{};
    auto signed_message=Bridge::ServerIssue(members,s,"A",4,signing,authority);
    assert(signed_message && signed_message->has_direct_peer_grant());
    std::string serialized;
    assert(signed_message->SerializeToString(&serialized));
    bbcoop::Envelope received{};
    assert(received.ParseFromString(serialized));
    const Grant::Expect expected{"team-7","party-7","A","B",17,29,0x101,42};
    const Hybrid::PeerCryptoScopeV241 noise_scope{
        "party-7","A","B",17,29,42,0x101};
    auto valid=Bridge::ClientTake(received,authority,expected,
        noise_scope,s.responder_noise_pub,s.issued_unix_ms);
    assert(valid && valid->scope==s);
    assert(!Bridge::ServerIssue(members,s,"B",4,signing,authority));
    members.players[0].current=0; // offline authoritative player
    assert(!Bridge::ServerIssue(members,s,"A",4,signing,authority));
    members.players[0].current=2;
    auto other=authority;other[0]^=1;
    assert(!Bridge::ClientTake(received,other,expected,noise_scope,
                               s.responder_noise_pub,s.issued_unix_ms));
    auto forged=received;
    auto* body=forged.mutable_direct_peer_grant();
    std::string payload=body->signed_grant();
    payload.back()^=1;body->set_signed_grant(payload);
    assert(!Bridge::ClientTake(forged,authority,expected,noise_scope,
                               s.responder_noise_pub,s.issued_unix_ms));
    forged=received;
    forged.mutable_direct_peer_grant()->set_authority_public_key(
        std::string(32,'X'));
    assert(!Bridge::ClientTake(forged,authority,expected,noise_scope,
                               s.responder_noise_pub,s.issued_unix_ms));
    forged=received;
    forged.mutable_direct_peer_grant()->set_signed_grant(std::string(513,'X'));
    assert(!Bridge::ClientTake(forged,authority,expected,noise_scope,
                               s.responder_noise_pub,s.issued_unix_ms));
    forged=received;
    forged.mutable_direct_peer_grant()->clear_signed_grant();
    assert(!Bridge::ClientTake(forged,authority,expected,noise_scope,
                               s.responder_noise_pub,s.issued_unix_ms));
    assert(!Bridge::ClientTake(received,authority,expected,noise_scope,
                               s.responder_noise_pub,s.expires_unix_ms));
    auto bad_noise=noise_scope;bad_noise.world_epoch++;
    assert(!Bridge::ClientTake(received,authority,expected,bad_noise,
                               s.responder_noise_pub,s.issued_unix_ms));
    bbcoop::Envelope unrelated{};
    unrelated.mutable_duel_state();
    assert(!Bridge::ClientTake(unrelated,authority,expected,noise_scope,
                               s.responder_noise_pub,s.issued_unix_ms));
    puts("SHYT_V289_ORIGINAL_YT_COOP_STREAM_SIGNED_GRANT_ADAPTER_PASS");
}
