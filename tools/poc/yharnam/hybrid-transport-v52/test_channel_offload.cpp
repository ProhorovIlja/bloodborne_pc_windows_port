// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_channel_offload.hpp"
#include <array>
#include <cassert>
using namespace SeamlessHunt::Hybrid;

constexpr ChannelAuthority Good() {
    ChannelAuthority g{};
    g.session_grant_verified = true;
    g.both_peers_consented = true;
    g.peer_binding_verified = true;
    g.both_on_same_authorized_team = true;
    g.protocol_compatible = true;
    g.map_known = true;
    g.map_epoch_verified = true;
    g.both_on_same_map = true;
    g.enemy_stream_authorized = true;
    g.reliable_stream_handover_verified = true;
    g.sender_enemy_role = EnemyRole::Owner;
    g.target_enemy_role = EnemyRole::Follower;
    return g;
}
constexpr bool Direct(std::uint32_t ch, const ChannelAuthority& a) {
    return EligibleChannel(ch, NativeReliable(ch), a).direct_eligible;
}
static_assert(Direct(0x06, Good()));
static_assert(Direct(0x04, Good()));
static_assert(Direct(0x05, Good())); // owner --> follower enemy HP, once stream is safe
static_assert(Direct(0x14, Good())); // hits are not server-owned protocol messages
static_assert(Direct(0x40, Good())); // bullets
static_assert(Direct(0x16, []{ auto g=Good();g.sender_enemy_role=EnemyRole::Follower;g.target_enemy_role=EnemyRole::Owner;return g;}()));
static_assert(Direct(0x17, Good()));
static_assert(!Direct(0x15, Good())); // owner cannot send enemy hit to follower
static_assert(!Direct(0x27, Good()));
static_assert(!Direct(0x2C, Good()));
static_assert(!Direct(0x2F, Good()));
static_assert(!Direct(0x44, Good()));
static_assert(!Direct(0x06, ChannelAuthority{}));
static_assert(EligibleGameAck(Good()).direct_eligible);

int main() {
    auto g = Good();
    // Every valid pinned Pass/SameMap channel (not Ours/Drop) should be an
    // offload candidate once the complete stream is proven and game routing
    // allows sender/receiver roles, not only movement channels.
    for (std::uint32_t c=0; c<=kLastChannel; ++c) {
        const auto d = EligibleChannel(c, NativeReliable(c), g);
        if (IsLegacyServerOnly(c)) assert(!d.direct_eligible);
        else if (!IsSameMap(c)) assert(d.direct_eligible);
    }
    const auto noAuth = []{auto a=Good();a.peer_binding_verified=false;return a;}();
    assert(!Direct(0x06,noAuth));
    assert(!Direct(0x14,noAuth));
    const auto noConsent = []{auto a=Good();a.both_peers_consented=false;return a;}();
    assert(!Direct(0x40,noConsent));
    const auto noTeam = []{auto a=Good();a.both_on_same_authorized_team=false;return a;}();
    assert(!Direct(0x06,noTeam));
    const auto staleMap = []{auto a=Good();a.map_epoch_verified=false;return a;}();
    assert(!Direct(0x06,staleMap));
    assert(!Direct(0x14,staleMap));
    assert(Direct(0x01,staleMap)); // game's peer handshake Pass
    const auto differentMap = []{auto a=Good();a.both_on_same_map=false;return a;}();
    assert(!Direct(0x14,differentMap));
    const auto noOwner = []{auto a=Good();a.enemy_stream_authorized=false;return a;}();
    assert(!Direct(0x04,noOwner));
    assert(Direct(0x06,noOwner));
    const auto notFenced = []{auto a=Good();a.reliable_stream_handover_verified=false;return a;}();
    assert(!Direct(0x14,notFenced)); // reliable stream migration not yet safe
    assert(Direct(0x06,notFenced)); // movement is unreliable by native definition
    assert(!EligibleGameAck(notFenced).direct_eligible);
    assert(!EligibleChannel(0x14,false,g).direct_eligible); // class spoof
    assert(!EligibleChannel(0x04,true,g).direct_eligible);
    const auto wrongDirections = []{auto a=Good();a.sender_enemy_role=EnemyRole::Follower;return a;}();
    assert(!Direct(0x17,wrongDirections));
    assert(!Direct(0x05,wrongDirections)); // cannot send owner-only HP
    assert(Direct(0x16, []{auto a=Good();a.sender_enemy_role=EnemyRole::Follower;a.target_enemy_role=EnemyRole::Owner;return a;}()));
    assert(!Direct(0x16,g));
    assert(!Direct(0x15,g));
    assert(Direct(0x15, []{auto a=Good();a.sender_enemy_role=EnemyRole::Follower;a.target_enemy_role=EnemyRole::Owner;return a;}()));
    const auto ownerTarget = []{auto a=Good();a.target_enemy_role=EnemyRole::Owner;return a;}();
    assert(!Direct(0x05,ownerTarget));
    const auto noneTarget = []{auto a=Good();a.target_enemy_role=EnemyRole::None;return a;}();
    assert(Direct(0x05,noneTarget));
    const auto followerToNone = []{auto a=Good();a.sender_enemy_role=EnemyRole::Follower;a.target_enemy_role=EnemyRole::None;return a;}();
    assert(!Direct(0x05,followerToNone));
    // A multiplexed frame with ANY server-only game entry must use relay:
    const std::array<FrameEntry,3> peerBatch = {{{0x04,false},{0x14,true},{0x40,true}}};
    assert(EligibleFrame(peerBatch,g).direct_eligible);
    assert(!EligibleFrame(peerBatch,notFenced).direct_eligible);
    const std::array<FrameEntry,2> mixed = {{{0x06,false},{0x2F,true}}};
    assert(!EligibleFrame(mixed,g).direct_eligible);
    assert(EligibleFrame({},g,true).direct_eligible);
    assert(!EligibleFrame({},g).direct_eligible);
    assert(!EligibleFrame({},notFenced,true).direct_eligible);
    return 0;
}
