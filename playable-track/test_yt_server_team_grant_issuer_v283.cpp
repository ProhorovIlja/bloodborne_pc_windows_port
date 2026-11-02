// SPDX-License-Identifier: GPL-2.0-or-later
// V283 eligibility fixture mirrors accessor API of ACTUAL YT
// server/coop/coop.proto Team/TeamMember. Production server MUST use
// the real authoritative TeamLobby, never this fake class.
#include "yt_server_team_grant_issuer_v283.h"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace BloodborneCoop::SHYTHybrid;
namespace {
struct TeamMemberFixture {
    std::string id;
    int status=2;
    const std::string& member() const {return id;}
    int state() const {return status;}
};
struct TeamFixture {
    std::string id_value="team-42",party_value="world:42";
    bool game_started=true;
    std::vector<TeamMemberFixture> current;
    const std::string& id() const {return id_value;}
    const std::string& party() const {return party_value;}
    bool started() const {return game_started;}
    int members_size() const {return static_cast<int>(current.size());}
    const TeamMemberFixture& members(int index) const {return current.at(index);}
};
}
int main() {
    using namespace SignedPeerGrantV279;
    SecretKey secret{};
    PubKey pub{};
    std::array<u8,32> seed{};
    for(size_t i=0;i<seed.size();++i)seed[i]=static_cast<u8>(i+17);
    LinkMonocypher::crypto_eddsa_key_pair(
        secret.data(),pub.data(),seed.data());
    Scope scope{};
    scope.team="team-42";scope.party="world:42";
    scope.sender="A";scope.receiver="B";
    scope.sender_instance=10;scope.receiver_instance=11;
    scope.map=0x101;scope.world_epoch=2;
    scope.issued_unix_ms=1810000000000LL;
    scope.expires_unix_ms=1810000010000LL;
    scope.sender_ip_nbo=0x0100007f;scope.receiver_ip_nbo=0x0200007f;
    scope.sender_port_nbo=0x1234;scope.receiver_port_nbo=0x5678;
    for(size_t i=0;i<32;++i)scope.responder_noise_pub[i]=static_cast<u8>(i+1);
    for(size_t i=0;i<16;++i)scope.grant_nonce[i]=static_cast<u8>(i+2);
    TeamFixture team{};
    team.current={{"A",2},{"B",2}};
    assert(ServerTeamIssuerV283::Eligible(team,scope,"A",4));
    auto authorized=ServerTeamIssuerV283::Issue(
        team,scope,"A",4,secret);
    assert(authorized);
    const Expect live{"team-42","world:42","A","B",10,11,0x101,2};
    assert(Verify(*authorized,pub,live,scope.issued_unix_ms));
    assert(DecodeWire(EncodeWire(*authorized)));

    assert(!ServerTeamIssuerV283::Issue(team,scope,"B",4,secret));
    assert(!ServerTeamIssuerV283::Issue(team,scope,"stranger",4,secret));
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",1,secret));
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",6,secret));
    team.game_started=false;
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    team.game_started=true;
    team.party_value="world:other";
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    team.party_value="world:42";
    team.id_value="other";
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    team.id_value="team-42";
    team.current[0].status=1; // TITLE
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    team.current[0].status=2;
    team.current[1].status=0; // OFFLINE
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    team.current[1].status=2;
    team.current.push_back({"A",2}); // duplicate server member
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    team.current.pop_back();
    team.current.push_back({"C",2});
    team.current.push_back({"D",2});
    assert(ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    team.current.push_back({"E",2}); // 5 only with authoritative 5-seat setting
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",4,secret));
    assert(ServerTeamIssuerV283::Issue(team,scope,"A",5,secret));
    team.current.push_back({"F",2}); // 6 never allowed
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",5,secret));
    team.current.clear();
    assert(!ServerTeamIssuerV283::Issue(team,scope,"A",5,secret));
    puts("SHYT_V283_ORIGINAL_YT_TEAM_MEMBERSHIP_SIGNING_POLICY_PASS");
}
