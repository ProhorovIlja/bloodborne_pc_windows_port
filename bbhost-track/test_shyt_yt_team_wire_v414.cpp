// SPDX-License-Identifier: GPL-2.0-or-later
// Compiled with protoc from the exact upstream YT coop.proto, not mock fields.
#include "shyt_yt_team_wire_v414.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
using Gate = SeamlessHunt::YtTeamAuthorityV414;
using Wire = SeamlessHunt::YtTeamWireV414;
using Scope = Wire::Scope;
using Result = Wire::Result;

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
}
