// SPDX-License-Identifier: GPL-2.0-or-later
// Compile against EXACT Yharnam Together C++ server packet policy, compare
// with our real BBHost C-native copy across every channel/map/owner state.
// No game data, packets, network or private server configuration.
#include "coop/packet_routes.h"
#include "shyt_yt_packet_routes_v358.h"
#include <array>
#include <cstdint>
#include <cstdio>

int main() {
    using namespace BloodborneCoop;
    constexpr std::array<std::uint32_t,4> maps{0u,0x18000000u,0x18010000u,0x29030000u};
    static_assert(NativeChannelCount==SHYT_YT_NATIVE_CHANNEL_COUNT_V21);
    static_assert(static_cast<int>(EnemyPart::None)==SHYT_YT_ENEMY_NONE_V358);
    static_assert(static_cast<int>(EnemyPart::Owner)==SHYT_YT_ENEMY_OWNER_V358);
    static_assert(static_cast<int>(EnemyPart::Follower)==SHYT_YT_ENEMY_FOLLOWER_V358);
    std::uint64_t checked=0;
    for(std::uint32_t ch=0;ch<NativeChannelCount+2u;++ch) {
        if (ch<NativeChannelCount) {
            const int yt=static_cast<int>(NativeChannelPolicy(ch));
            const int ours=static_cast<int>(shyt_yt_channel_policy_v21(ch));
            if(yt!=ours) return 11;
        }
        if((ch==0x2cu || ch==0x2fu || ch==0x27u) &&
           shyt_yt_routes_native_packet_v358(ch,nullptr))
            return 12;
        for (std::uint32_t sm:maps) for(std::uint32_t tm:maps) {
            for(int sender=0;sender<3;++sender) for(int target=0;target<3;++target) {
                PacketEnds original{};
                original.sender_map=sm;
                original.target_map=tm;
                original.sender=static_cast<EnemyPart>(sender);
                original.target=static_cast<EnemyPart>(target);
                struct ShytYtPacketEndsV358 copied{
                    sm,tm,static_cast<ShytYtEnemyPartV358>(sender),
                    static_cast<ShytYtEnemyPartV358>(target)};
                const bool server=RoutesNativePacket(ch,original);
                const bool host=shyt_yt_routes_native_packet_v358(ch,&copied)!=0;
                if(server!=host) {
                    // No private identifiers or packet data in this fixture.
                    std::fprintf(stderr,"YT/BBHost route table parity failure channel=%u\n",ch);
                    return 13;
                }
                ++checked;
            }
        }
    }
    // 70 channels * 4x4 map combinations * 3x3 ownership combinations
    if(checked!=10080) return 14;
    const ShytYtPacketEndsV358 different{
        0x18000000u,0x29030000u,SHYT_YT_ENEMY_OWNER_V358,
        SHYT_YT_ENEMY_FOLLOWER_V358};
    if(shyt_yt_routes_native_packet_v358(0x06u,&different))return 15;
    if(shyt_yt_routes_native_packet_v358(0x27u,&different))return 16;
    if(shyt_yt_routes_native_packet_v358(0x44u,&different))return 17;
    std::puts("SHYT_V358_ACTUAL_YT_SERVER_VS_BBHOST_ROUTE_PARITY_10080_CASES_PASS");
    std::puts("Source-equivalence ONLY. Authenticated direct-P2P authorization NOT installed.");
    return 0;
}
