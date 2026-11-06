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
    // Proto3 does NOT serialize accepted=false; a denied Welcome
    // with its refusal text is valid and must be reported as Refused.
    bbcoop::Envelope denied_welcome;
    denied_welcome.mutable_welcome()->set_text("wrong party");
    assert(!denied_welcome.welcome().accepted());
    const auto lite_denied=Lite::Decode(Encode(denied_welcome));
    assert(lite_denied.kind==Lite::Kind::Welcome && !lite_denied.accepted);
    bbcoop::Envelope empty_refusal;
    empty_refusal.mutable_welcome();
    const auto lite_empty=Lite::Decode(Encode(empty_refusal));
    assert(lite_empty.kind==Lite::Kind::Welcome && !lite_empty.accepted);
    // V420: original v1.4.0 SnapshotRequest (empty proto3 defaults)
    // must match the two canonical bytes transmitted by the BBHost link.
    bbcoop::Envelope original_snapshot_request;
    auto* sr=original_snapshot_request.mutable_snapshot_request();
    sr->set_epoch(0u);
    sr->set_seq(0u);
    assert(Encode(original_snapshot_request)==
           (std::vector<std::uint8_t>{0x32u,0x00u}));
    bbcoop::Envelope original_snapshot;
    original_snapshot.mutable_snapshot()->set_epoch(77u);
    original_snapshot.mutable_snapshot()->set_last(9u);
    original_snapshot.mutable_snapshot()->set_shown_map(0x00112233u);
    const auto lite_snapshot=Lite::Decode(Encode(original_snapshot));
    assert(lite_snapshot.kind==Lite::Kind::Snapshot);
    assert(lite_snapshot.epoch==original_snapshot.snapshot().epoch());
    assert(lite_snapshot.last==original_snapshot.snapshot().last());
    // Proto3 omits last=0, which is valid for an otherwise fresh world.
    original_snapshot.mutable_snapshot()->set_last(0u);
    assert(Lite::Decode(Encode(original_snapshot)).kind==Lite::Kind::Snapshot);
    assert(Lite::Decode(Encode(original_snapshot)).last==0u);
    // Conflicting duplicate world epochs must never be silently accepted.
    // Envelope.snapshot=7; duplicate nested epoch field=1 is invalid.
    const std::vector<std::uint8_t> duplicate_meta{
        0x3au,0x04u,0x08u,0x4du,0x08u,0x4du};
    assert(Lite::Decode(duplicate_meta).kind==Lite::Kind::Invalid);
    // V421: full source-generated original Snapshot with packed uint32
    // handles, shown characters, ZigZag HP, map state, flags and wipe.
    bbcoop::Envelope complex_snapshot;
    auto* world=complex_snapshot.mutable_snapshot();
    world->set_epoch(77u);
    world->set_last(9u);
    auto* killed=world->add_kills();
    killed->set_map(0x18000000u);
    killed->add_handles(7u);
    killed->add_handles(300u);
    world->set_shown_map(0x18000000u);
    auto* shown=world->add_shown();
    shown->set_handle(55u);
    shown->set_bits(7u);
    world->set_map_state_map(0x18000000u);
    world->set_map_state_bits(std::string(128,'z'));
    world->set_return_point(-12);
    world->set_return_point_map(0x18000000u);
    auto* hp=world->add_hp();
    hp->set_source(0x123456789ull);
    hp->set_map(0x18000000u);
    auto* enemy=hp->add_enemies();
    enemy->set_handle(55u);
    enemy->set_value(-51);
    enemy->set_max(100);
    auto* flag=world->add_recent_flags();
    flag->set_seq(7u);
    flag->set_map(0x18000000u);
    flag->set_kind(1u);
    flag->set_subject(1200u);
    flag->set_value(1u);
    world->set_after_wipe(true);
    auto full_lite=Lite::Decode(Encode(complex_snapshot));
    assert(full_lite.kind==Lite::Kind::Snapshot);
    assert(full_lite.epoch==77u && full_lite.last==9u);
    // A protobuf-valid sequence beyond the snapshot's last cannot be
    // used as a validated world descriptor.
    world->mutable_recent_flags(0)->set_seq(10u);
    assert(Lite::Decode(Encode(complex_snapshot)).kind==Lite::Kind::Invalid);
    world->mutable_recent_flags(0)->set_seq(7u);
    world->set_map_state_bits(std::string(16385,'x'));
    assert(Lite::Decode(Encode(complex_snapshot)).kind==Lite::Kind::Invalid);
    world->set_map_state_bits(std::string(128,'z'));
    // Canonical v1.4.0 repeated packed handles share one bounded budget.
    auto* extra=world->add_kills();
    extra->set_map(1u);
    for(unsigned i=0;i<8200u;++i)extra->add_handles(i);
    assert(Lite::Decode(Encode(complex_snapshot)).kind==Lite::Kind::Invalid);
    world->mutable_kills()->RemoveLast();
    assert(Lite::Decode(Encode(complex_snapshot)).kind==Lite::Kind::Snapshot);
    // Nested MapKills.map has wire-0 uint32, not length-delimited.
    const std::vector<std::uint8_t> wrong_nested_map{
        0x3au,0x06u,0x08u,0x4du,0x1au,0x02u,0x0au,0x00u};
    assert(Lite::Decode(wrong_nested_map).kind==Lite::Kind::Invalid);
    // after_wipe bool only accepts canonical 0 or 1.
    const std::vector<std::uint8_t> wrong_bool{
        0x3au,0x04u,0x08u,0x4du,0x60u,0x02u};
    assert(Lite::Decode(wrong_bool).kind==Lite::Kind::Invalid);
    // Original protobuf can put valid fields in different order.
    const std::vector<std::uint8_t> out_of_order{
        0x3au,0x08u,
        0x5au,0x02u,0x08u,0x07u, // recent_flags seq=7
        0x10u,0x09u,              // last=9
        0x08u,0x4du};             // epoch=77
    assert(Lite::Decode(out_of_order).kind==Lite::Kind::Snapshot);
    // Independently cross-check the V418 outbound party Hello wire tags
    // against the REAL YT v1.4.0 protobuf serializer, not a second local
    // homegrown parser. This locks protocol/party/member/run/host/owner.
    bbcoop::Envelope source_party_hello;
    auto* ph=source_party_hello.mutable_hello();
    ph->set_protocol(8u);
    ph->set_party("world:level-44");
    ph->set_member("68756e74657235"); // online ID "hunter5" in server hex
    ph->set_run(707u);
    ph->set_host(true);
    ph->set_enemy_owner(true);
    const std::vector<std::uint8_t> expected_hello_inner{
        0x08u,0x08u, // protocol = 8
        0x12u,0x0eu, // party: 14 bytes
        'w','o','r','l','d',':','l','e','v','e','l','-','4','4',
        0x1au,0x0eu, // member: 14 lowercase ASCII hex bytes
        '6','8','7','5','6','e','7','4','6','5','7','2','3','5',
        0x20u,0xc3u,0x05u, // run = 707, protobuf varint
        0x28u,0x01u, // host
        0x30u,0x01u  // enemy owner
    };
    std::vector<std::uint8_t> expected_party_wire{0x0au,
        static_cast<std::uint8_t>(expected_hello_inner.size())};
    expected_party_wire.insert(expected_party_wire.end(),
        expected_hello_inner.begin(),expected_hello_inner.end());
    assert(Encode(source_party_hello)==expected_party_wire);
    // A nested duplicate authority field and malformed trailing varint
    // must not be silently resolved via protobuf's last-field-wins rule.
    auto duplicate=Encode(original_lobby);
    const auto copy_of_body=duplicate;
    duplicate.insert(duplicate.end(),copy_of_body.begin(),copy_of_body.end());
    assert(Lite::Decode(duplicate).kind==Lite::Kind::Invalid);
    auto bad_wire=Encode(original_start);
    bad_wire.push_back(0x80u); // unterminated varint key
    assert(Lite::Decode(bad_wire).kind==Lite::Kind::Invalid);
    // The first response to LobbyHello on a public YT server commonly
    // contains NO team. This is valid protobuf and must not be mistaken
    // for a malformed packet or an authority grant.
    bbcoop::Envelope teamless;
    teamless.mutable_lobby_state()->set_notice("make a team");
    assert(!teamless.lobby_state().has_team());
    const auto lite_teamless=Lite::Decode(Encode(teamless));
    assert(lite_teamless.kind==Lite::Kind::Lobby);
    assert(!lite_teamless.lobby_has_team);
    Gate gate("hunter5");
    assert(Feed(gate,Scope::Lobby,"",teamless)==Result::Revoked);
    assert(!gate.Authorized());
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
