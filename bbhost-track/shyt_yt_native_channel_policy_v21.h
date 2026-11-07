/* SPDX-License-Identifier: GPL-2.0-or-later
 * V21: Yharnam Together 1.3.1 real server's NativeChannelPolicy,
 * adapted to C for an observe-only BBHost game-hook diagnostic.
 * SOURCE: lKaniel/bloodborne-server 5d2305ee611ef1e03be39ff925f0da75c9a70393
 * server/coop/packet_routes.h Git blob f732c87cd0a030751f5ed23dfa225e98bb8ffc5c
 * Actual source equality is checked by CI on both Windows and Linux.
 * This table IS NOT proof a direct P2P send is authorized. The server
 * additionally filters by map, enemy owner, invasion, and room membership.
 */
#ifndef SHYT_YT_NATIVE_CHANNEL_POLICY_V21_H
#define SHYT_YT_NATIVE_CHANNEL_POLICY_V21_H
#include <stdint.h>

#define SHYT_YT_NATIVE_CHANNEL_COUNT_V21 68u
enum ShytYtNativeChannelPolicyV21 {
    SHYT_YT_CHANNEL_PASS_V21=0,
    SHYT_YT_CHANNEL_SAME_MAP_V21=1,
    SHYT_YT_CHANNEL_OURS_V21=2,
    SHYT_YT_CHANNEL_DROP_V21=3
};
static inline enum ShytYtNativeChannelPolicyV21
shyt_yt_channel_policy_v21(uint32_t channel) {
    if(channel>=SHYT_YT_NATIVE_CHANNEL_COUNT_V21)
        return SHYT_YT_CHANNEL_DROP_V21;
    switch(channel) {
    case 0x04: case 0x05: case 0x06: case 0x0E:
    case 0x0F: case 0x12: case 0x14: case 0x15:
    case 0x16: case 0x17: case 0x24: case 0x25:
    case 0x29: case 0x2A: case 0x2B: case 0x2D:
    case 0x2E: case 0x30: case 0x31: case 0x34:
    case 0x36: case 0x37: case 0x3D: case 0x3E:
    case 0x40: case 0x41:
        return SHYT_YT_CHANNEL_SAME_MAP_V21;
    case 0x2C: case 0x2F:
        return SHYT_YT_CHANNEL_OURS_V21;
    case 0x27:
        return SHYT_YT_CHANNEL_DROP_V21;
    default:
        return SHYT_YT_CHANNEL_PASS_V21;
    }
}
#endif
