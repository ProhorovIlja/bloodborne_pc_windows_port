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
    return g;
}
static_assert(EligibleChannel(kPlayerMovement, false, Good()).direct_eligible);
static_assert(EligibleChannel(kEnemyMovement, false, Good()).direct_eligible);
static_assert(!EligibleChannel(kPlayerMovement, true, Good()).direct_eligible);
static_assert(!EligibleChannel(0x05, false, Good()).direct_eligible);
static_assert(!EligibleChannel(0x14, false, Good()).direct_eligible);
static_assert(!EligibleChannel(0x2C, false, Good()).direct_eligible);
static_assert(!EligibleChannel(0x2F, false, Good()).direct_eligible);
static_assert(!EligibleChannel(0x27, false, Good()).direct_eligible);
static_assert(!EligibleChannel(0x44, false, Good()).direct_eligible);
static_assert(!EligibleChannel(0x00, false, ChannelAuthority{}).direct_eligible);

int main() {
    const auto good = Good();
    const std::array must_relay = {0x05U,0x0EU,0x0FU,0x12U,0x14U,0x15U,0x16U,
        0x17U,0x24U,0x25U,0x27U,0x29U,0x2AU,0x2BU,0x2CU,0x2DU,0x2EU,0x2FU,
        0x30U,0x31U,0x34U,0x36U,0x37U,0x3DU,0x3EU,0x40U,0x41U};
    for (const auto ch : must_relay) {
        assert(!EligibleChannel(ch, false, good).direct_eligible);
    }
    const auto noMap = [] {
        auto p = Good();
        p.map_known = false;
        return p;
    }();
    assert(!EligibleChannel(kPlayerMovement, false, noMap).direct_eligible);
    const auto staleEpoch = [] {
        auto p = Good();
        p.map_epoch_verified = false;
        return p;
    }();
    assert(!EligibleChannel(kEnemyMovement, false, staleEpoch).direct_eligible);
    const auto differentMap = [] {
        auto p = Good();
        p.both_on_same_map = false;
        return p;
    }();
    assert(!EligibleChannel(kPlayerMovement, false, differentMap).direct_eligible);
    const auto enemyNotAuthorized = [] {
        auto p = Good();
        p.enemy_stream_authorized = false;
        return p;
    }();
    assert(EligibleChannel(kPlayerMovement, false, enemyNotAuthorized).direct_eligible);
    assert(!EligibleChannel(kEnemyMovement, false, enemyNotAuthorized).direct_eligible);
    const auto noTeam = [] {
        auto p = Good();
        p.both_on_same_authorized_team = false;
        return p;
    }();
    assert(!EligibleChannel(kPlayerMovement, false, noTeam).direct_eligible);
    const auto noConsent = [] {
        auto p = Good();
        p.both_peers_consented = false;
        return p;
    }();
    assert(!EligibleChannel(kPlayerMovement, false, noConsent).direct_eligible);
    const auto unboundPeer = [] {
        auto p = Good();
        p.peer_binding_verified = false;
        return p;
    }();
    assert(!EligibleChannel(kPlayerMovement, false, unboundPeer).direct_eligible);
    const auto untrustedGrant = [] {
        auto p = Good();
        p.session_grant_verified = false;
        return p;
    }();
    assert(!EligibleChannel(kPlayerMovement, false, untrustedGrant).direct_eligible);
    const auto wrongProtocol = [] {
        auto p = Good();
        p.protocol_compatible = false;
        return p;
    }();
    assert(!EligibleChannel(kPlayerMovement, false, wrongProtocol).direct_eligible);

    const std::array<FrameEntry, 2> bulkMovement = {{
        {kPlayerMovement, false}, {kEnemyMovement, false}
    }};
    assert(EligibleFrame(bulkMovement, good).direct_eligible);
    assert(!EligibleFrame(bulkMovement, enemyNotAuthorized).direct_eligible);
    const std::array<FrameEntry, 2> mixed = {{
        {kPlayerMovement, false}, {0x14, true}
    }};
    assert(!EligibleFrame(mixed, good).direct_eligible);
    const std::array<FrameEntry, 1> passChannel = {{{0x01, false}}};
    assert(EligibleFrame(passChannel, good).direct_eligible);
    assert(!EligibleFrame(passChannel, untrustedGrant).direct_eligible);
    assert(!EligibleFrame(std::span<const FrameEntry>{}, good).direct_eligible);
    return 0;
}
