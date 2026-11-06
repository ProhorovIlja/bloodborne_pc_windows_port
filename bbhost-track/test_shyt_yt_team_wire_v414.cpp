// SPDX-License-Identifier: GPL-2.0-or-later
// Compiled with protoc from the exact upstream YT coop.proto, not mock fields.
#include "shyt_yt_team_wire_v414.h"
#include "shyt_yt_team_wire_lite_v415.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
using Gate = SeamlessHunt::YtTeamAuthorityV414;
using Wire = SeamlessHunt::YtTeamWireV414;
using Scope = Wire::Scope;
using Result = Wire::Result;
using Lite = SeamlessHunt::YtTeamWireLiteV415;

static std::vector<std::uint8_t> Encode(const bbcoop::Envelope& value) {
    std::string bytes;
    assert(value.SerializeToString(&bytes));
    return {bytes.begin(), bytes.end()};
}
static Result Feed(Gate& gate, Scope scope, std::string party,
                   const bbcoop::Envelope& value) {
    const auto bytes = Encode(value);
    return Wire::FeedAfterVerifiedServerAuth(gate,scope,party,bytes);
}
static bbcoop::Envelope Lobby(int players=5) {
    bbcoop::Envelope env;
    bbcoop::Team* team=env.mutable_lobby_state()->mutable_team();
    team->set_id("t-17");
    team->set_leader("hunter1");
    team->set_world("level-44");
    team->set_party("world:level-44");
    team->set_started(true);
    for(int i=1;i<=players;++i) {
        auto* member=team->add_members();
        member->set_member("hunter"+std::to_string(i));
        member->set_name("Hunter "+std::to_string(i));
        member->set_ready(true);
        member->set_slot(static_cast<std::uint32_t>(i));
        member->set_sign(i==1?0u:static_cast<std::uint32_t>(9-i));
    }
    return env;
}
static bbcoop::Envelope Start(std::string host="hunter1") {
    bbcoop::Envelope env;
    auto* start=env.mutable_team_start();
    start->set_team("t-17");
    start->set_world("level-44");
    start->set_party("world:level-44");
    start->set_host(std::move(host));
    start->set_slot(5);
    return env;
}
static bbcoop::Envelope Welcome(bool ok=true, std::uint64_t epoch=21,
                                 std::uint64_t last=0) {
    bbcoop::Envelope env;
    auto* msg=env.mutable_welcome();
    msg->set_accepted(ok);
    msg->set_epoch(epoch);
    msg->set_last(last);
    return env;
}
int main() {
    // The fast BBHost decoder must agree with REAL generated YT protobuf
    // field values. These bytes are produced by upstream protoc, not mocks.
    const auto original_lobby=Lobby();
    const auto lite_lobby=Lite::Decode(Encode(original_lobby));
    assert(lite_lobby.kind==Lite::Kind::Lobby);
    assert(lite_lobby.lobby.team==original_lobby.lobby_state().team().id());
    assert(lite_lobby.lobby.leader==original_lobby.lobby_state().team().leader());
    assert(lite_lobby.lobby.world==original_lobby.lobby_state().team().world());
    assert(lite_lobby.lobby.party==original_lobby.lobby_state().team().party());
    assert(lite_lobby.lobby.members.size()==5u);
    for (std::size_t i=0; i<5u; ++i) {
        const auto& expected=original_lobby.lobby_state().team().members(static_cast<int>(i));
        const auto& actual=lite_lobby.lobby.members[i];
        assert(actual.id==expected.member() && actual.sign==expected.sign());
        assert(actual.slot==expected.slot() && actual.ready==expected.ready());
    }
    const auto original_start=Start();
    const auto lite_start=Lite::Decode(Encode(original_start));
    assert(lite_start.kind==Lite::Kind::Start);
    assert(lite_start.start.team==original_start.team_start().team());
    assert(lite_start.start.party==original_start.team_start().party());
    assert(lite_start.start.host==original_start.team_start().host());
    assert(lite_start.start.world==original_start.team_start().world());
    assert(lite_start.start.slot==original_start.team_start().slot());
    const auto original_welcome=Welcome();
    const auto lite_welcome=Lite::Decode(Encode(original_welcome));
    assert(lite_welcome.kind==Lite::Kind::Welcome);
    assert(lite_welcome.accepted==original_welcome.welcome().accepted());
    assert(lite_welcome.epoch==original_welcome.welcome().epoch());
    assert(lite_welcome.last==original_welcome.welcome().last());
    // A nested duplicate authority field and malformed trailing varint
    // must not be silently resolved via protobuf's last-field-wins rule.
    auto duplicate=Encode(original_lobby);
    duplicate.insert(duplicate.end(),duplicate.begin(),duplicate.end());
    assert(Lite::Decode(duplicate).kind==Lite::Kind::Invalid);
    auto bad_wire=Encode(original_start);
    bad_wire.push_back(0x80u); // unterminated varint key
    assert(Lite::Decode(bad_wire).kind==Lite::Kind::Invalid);
    Gate gate("hunter5");
    assert(Feed(gate,Scope::Lobby,"",Lobby())==Result::Accepted);
    assert(!gate.Authorized());
    assert(Feed(gate,Scope::Lobby,"",Start())==Result::Accepted);
    assert(Feed(gate,Scope::Lobby,"",Welcome())==Result::Ignored);
    assert(!gate.Authorized()); // a lobby Welcome is not party authorization
    assert(Feed(gate,Scope::Party,"world:other",Welcome())==Result::Revoked);
    assert(!gate.Authorized());
    assert(Feed(gate,Scope::Lobby,"",Lobby())==Result::Accepted);
    assert(Feed(gate,Scope::Lobby,"",Start())==Result::Accepted);
    assert(Feed(gate,Scope::Party,"world:level-44",Welcome())==Result::Accepted);
    assert(gate.Authorized() && gate.IsTeamMember("hunter5"));
    assert(!gate.IsTeamMember("stranger"));
    // Real protobuf oneof scopes: TeamStart on party stream never admits.
    assert(Feed(gate,Scope::Party,"world:level-44",Start())==Result::Ignored);
    assert(gate.Authorized());
    // Server can switch host to an existing teammate; a fresh welcome is
    // required after the new TeamStart. This isn't permission for bare UDP.
    assert(Feed(gate,Scope::Lobby,"",Start("hunter2"))==Result::Accepted);
    assert(!gate.Authorized());
    assert(Feed(gate,Scope::Party,"world:level-44",Welcome(true,22,4))==Result::Accepted);
    assert(gate.Snapshot().host=="hunter2");
    // A stale epoch or reordered last sequence revokes the world.
    assert(Feed(gate,Scope::Party,"world:level-44",Welcome(true,21,4))==Result::Revoked);
    assert(!gate.Authorized());
    assert(Feed(gate,Scope::Lobby,"",Lobby())==Result::Accepted);
    assert(Feed(gate,Scope::Lobby,"",Start())==Result::Accepted);
    assert(Feed(gate,Scope::Party,"world:level-44",Welcome())==Result::Accepted);
    // A member departure immediately invalidates the previously trusted team.
    assert(Feed(gate,Scope::Lobby,"",Lobby(4))==Result::Revoked);
    assert(!gate.Authorized());
    // Malformed or oversized protobuf must also revoke, not silently trust
    // a prior session/party snapshot.
    assert(Feed(gate,Scope::Lobby,"",Lobby())==Result::Accepted);
    assert(Feed(gate,Scope::Lobby,"",Start())==Result::Accepted);
    assert(Feed(gate,Scope::Party,"world:level-44",Welcome())==Result::Accepted);
    const std::uint8_t invalid[]{0xffu,0xffu,0xffu,0xffu};
    assert(Wire::FeedAfterVerifiedServerAuth(gate,Scope::Party,"world:level-44",invalid)==Result::Revoked);
    assert(!gate.Authorized());
    assert(Feed(gate,Scope::Lobby,"",Lobby())==Result::Accepted);
    assert(Feed(gate,Scope::Lobby,"",Start())==Result::Accepted);
    assert(Feed(gate,Scope::Party,"world:level-44",Welcome())==Result::Accepted);
    std::vector<std::uint8_t> huge(Wire::MaxEnvelopeBytes+1u,0);
    assert(Wire::FeedAfterVerifiedServerAuth(gate,Scope::Party,"world:level-44",huge)==Result::Revoked);
    assert(!gate.Authorized());
    // A roster of six must fail even if protobuf accepts it.
    auto six=Lobby(5);
    auto* sixth=six.mutable_lobby_state()->mutable_team()->add_members();
    sixth->set_member("hunter6");
    sixth->set_sign(7);
    assert(Feed(gate,Scope::Lobby,"",six)==Result::Revoked);
    // Unknown world events stay outside the authorization state machine.
    auto unhandled=bbcoop::Envelope{};
    unhandled.mutable_map()->set_map(0x18000000u);
    assert(Feed(gate,Scope::Party,"world:level-44",unhandled)==Result::Ignored);
    std::puts("SHYT_V414_ORIGINAL_YT_PROTOBUF_TEAM_WORLD_ADMISSION_PASS");
    std::puts("SHYT_V415_LITE_WIRE_MATCHES_GENERATED_YT_PROTOBUF_PASS");
}
