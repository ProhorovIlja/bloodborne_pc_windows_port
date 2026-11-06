// SPDX-License-Identifier: GPL-2.0-or-later
// Exhaustive parity against original released YT v1.4.0 production
// server/coop/packet_routes.h and game_link.h (not mirrored fixtures).
#include "shyt_yt_game_route_assessment_v433.h"
#include "coop/packet_routes.h"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>
using Local=SeamlessHunt::YtGameRouteAssessmentV433;
using Original=BloodborneCoop::PacketEnds;

static Local::EnemyPart local_role(unsigned i) {
    switch(i){case 1u:return Local::EnemyPart::Owner;
              case 2u:return Local::EnemyPart::Follower;
              default:return Local::EnemyPart::None;}
}
static BloodborneCoop::EnemyPart orig_role(unsigned i) {
    switch(i){case 1u:return BloodborneCoop::EnemyPart::Owner;
              case 2u:return BloodborneCoop::EnemyPart::Follower;
              default:return BloodborneCoop::EnemyPart::None;}
}
static std::vector<u8> packet(std::uint32_t channel) {
    // Original in-game packet is u32 channel, u32 length, payload.
    return {static_cast<u8>(channel),0u,0u,0u,0u,0u,0u,0u};
}
int main() {
    std::uint64_t comparisons=0u;
    // channel range includes invalid 68 and 255; map 0 means loading.
    for(const std::uint32_t ch :
        [] {std::vector<std::uint32_t> ids;
            for(unsigned c=0u;c<=68u;++c)ids.push_back(c);
            ids.push_back(255u);return ids;}()) {
      for(const std::uint32_t sm:std::array<std::uint32_t,4>{0u,1u,2u,0x18000000u})
        for(const std::uint32_t tm:std::array<std::uint32_t,4>{0u,1u,2u,0x18000000u})
          for(unsigned sr=0u;sr<3u;++sr)
            for(unsigned tr=0u;tr<3u;++tr) {
                const Local::Ends local{sm,tm,local_role(sr),local_role(tr)};
                const Original orig{sm,tm,orig_role(sr),orig_role(tr)};
                const bool expected=
                    BloodborneCoop::RoutesNativePacket(ch,orig);
                assert(Local::CoOpPolicy(ch,local)==expected);
                for(const bool from_visitor:{false,true}) {
                    const bool hostile=BloodborneCoop::RoutesHostilePacket(
                        ch,orig,from_visitor);
                    assert(Local::HostilePolicy(ch,local,from_visitor)==hostile);
                    for(const bool reliable:{false,true}) {
                        const auto teammate=Local::Inspect(
                            ch,Local::Relation::Teammate,local,from_visitor,
                            reliable);
                        const auto invader=Local::Inspect(
                            ch,Local::Relation::HostileVisitor,local,
                            from_visitor,reliable);
                        assert(teammate.original_server_policy_would_pass==expected);
                        assert(invader.original_server_policy_would_pass==hostile);
                        assert(teammate.needs_reliable_drop_placeholder==
                               (!expected && reliable));
                        assert(invader.needs_reliable_drop_placeholder==
                               (!hostile && reliable));
                        // NO set of original map/owner/channel fields
                        // can authorize direct P2P or guest NetSync.
                        assert(!teammate.can_forward_game &&
                               !teammate.can_arm_game_queue);
                        assert(!invader.can_forward_game &&
                               !invader.can_arm_game_queue);
                        ++comparisons;
                    }
                }
            }
    }
    assert(comparisons>39000u);

    // Reference ORIGINAL server RouteGameFrame algorithm: dropping a
    // reliable packet MUST preserve seq and use {68,0}, while dropping
    // unreliable packet removes that entry entirely.
    BloodborneCoop::GameFrame game;
    game.sender="hunter2";
    game.instance=11u;
    game.entries={
        {BloodborneCoop::PacketClass::Reliable,14u,packet(0x27u)},
        {BloodborneCoop::PacketClass::Unreliable,7u,packet(0x27u)},
        {BloodborneCoop::PacketClass::Reliable,15u,packet(0x07u)},
        {BloodborneCoop::PacketClass::Reliable,16u,packet(68u)}
    };
    const auto before=game;
    const auto n=BloodborneCoop::RouteGameFrame(game,
        [&](u32 ch) {return Local::CoOpPolicy(ch,{});});
    assert(n==3u && game.entries.size()==3u);
    assert(game.entries[0].seq==14u &&
           game.entries[0].packet_class==BloodborneCoop::PacketClass::Reliable &&
           game.entries[0].packet==
             std::vector<u8>(Local::DroppedReliablePacket.begin(),
                             Local::DroppedReliablePacket.end()));
    assert(game.entries[1]==before.entries[2]);
    assert(game.entries[2].seq==16u &&
           game.entries[2].packet==
             std::vector<u8>(Local::DroppedReliablePacket.begin(),
                             Local::DroppedReliablePacket.end()));
    // Normal original coder is still authoritative for reliability /
    // acknowledgement semantics; do not replace it with guesswork.
    const auto encoded=BloodborneCoop::EncodeGameFrame(game);
    const auto decoded=BloodborneCoop::DecodeGameFrame(encoded);
    assert(decoded && *decoded==game);

    std::printf("SHYT_V433_ORIGINAL_YT_140_COOP_HOSTILE_ROUTE_PARITY_PASS comparisons=%llu\n",
                static_cast<unsigned long long>(comparisons));
}
