/* SPDX-License-Identifier: GPL-2.0-or-later
 * V358: PURE C port of Yharnam Together's real co-op packet filter,
 * source-locked by CI with the original C++ packet_routes.h.
 *
 * RoutesNativePacket is NOT a secure direct-P2P authorization. The
 * original server supplies map and enemy-owner information and applies
 * further invader/team membership restrictions. Never use a locally
 * constructed PacketEnds to bypass SHLK server consent.
 *
 * Upstream: lKaniel/bloodborne-server at exact
 * 5d2305ee611ef1e03be39ff925f0da75c9a70393
 * server/coop/packet_routes.h (Git blob f732c87cd0a030751f5ed23dfa225e98bb8ffc5c)
 */
#ifndef SHYT_YT_PACKET_ROUTES_V358_H
#define SHYT_YT_PACKET_ROUTES_V358_H
#include <stdint.h>
#include "shyt_yt_native_channel_policy_v21.h"

enum ShytYtEnemyPartV358 {
    SHYT_YT_ENEMY_NONE_V358=0,
    SHYT_YT_ENEMY_OWNER_V358=1,
    SHYT_YT_ENEMY_FOLLOWER_V358=2
};
struct ShytYtPacketEndsV358 {
    uint32_t sender_map;
    uint32_t target_map;
    enum ShytYtEnemyPartV358 sender;
    enum ShytYtEnemyPartV358 target;
};
static inline int shyt_yt_owner_enemy_channel_v358(uint32_t ch) {
    return ch==0x05u || ch==0x29u || ch==0x36u;
}
static inline int shyt_yt_routes_native_packet_v358(
    uint32_t channel,const struct ShytYtPacketEndsV358 *ends) {
    if (!ends || channel>=SHYT_YT_NATIVE_CHANNEL_COUNT_V21) return 0;
    switch (shyt_yt_channel_policy_v21(channel)) {
    case SHYT_YT_CHANNEL_PASS_V21: return 1;
    case SHYT_YT_CHANNEL_OURS_V21:
    case SHYT_YT_CHANNEL_DROP_V21: return 0;
    case SHYT_YT_CHANNEL_SAME_MAP_V21: break;
    default: return 0;
    }
    /* The native game permits the handshake before the map is known.
     * This is not sufficient to establish a direct P2P authorization.
     */
    if (ends->sender_map!=0 && ends->target_map!=0 &&
        ends->sender_map!=ends->target_map)
        return 0;
    if (channel==0x16u)
        return ends->sender==SHYT_YT_ENEMY_FOLLOWER_V358 &&
               ends->target==SHYT_YT_ENEMY_OWNER_V358;
    if (channel==0x17u)
        return ends->sender==SHYT_YT_ENEMY_OWNER_V358 &&
               ends->target==SHYT_YT_ENEMY_FOLLOWER_V358;
    if (channel==0x15u)
        return ends->sender!=SHYT_YT_ENEMY_OWNER_V358 &&
               ends->target!=SHYT_YT_ENEMY_FOLLOWER_V358;
    if (shyt_yt_owner_enemy_channel_v358(channel)) {
        switch (ends->target) {
        case SHYT_YT_ENEMY_NONE_V358:
            return ends->sender!=SHYT_YT_ENEMY_FOLLOWER_V358;
        case SHYT_YT_ENEMY_FOLLOWER_V358:
            return ends->sender==SHYT_YT_ENEMY_OWNER_V358;
        case SHYT_YT_ENEMY_OWNER_V358:
            return 0;
        default: return 0;
        }
    }
    return 1;
}
#endif
