/* SPDX-License-Identifier: GPL-3.0-or-later
 * V432: bounded READ-ONLY extraction of original Bloodborne 1.09
 * guest NetSync member's SceNpId (online ID), for checking V431's
 * authenticated server roster; NOT proof of peer/link authority.
 *
 * Pinned original YT v1.4.0:
 * emulator/src/core/bloodborne_patches.cpp::OnlineIdOfMember:
 *   member -> [u64 identity* at offset 0] -> SceNpId at identity+0x36
 * emulator/src/core/bloodborne_party.cpp::NpOnlineIdAt:
 *   17 bytes maximum, 3..16 ASCII [A-Za-z0-9_-] followed by NUL.
 * Server AuthenticatedMember hex-encodes original OnlineID bytes using
 * lower-case ASCII. That member hex must match the authenticated
 * TeamMember.member, not a display name, network endpoint or game slot.
 *
 * Production guest reader is BBHost BbHostApi.read: 0 on success.
 * All memory operations are bounded 8+17 bytes, no payload access.
 * The game's pointer may be stale or malicious; no guest writes, hooks,
 * packet routing, data injection or P2P grants permitted here.
 */
#ifndef SHYT_YT_GUEST_MEMBER_V432_H
#define SHYT_YT_GUEST_MEMBER_V432_H
#include "shyt_yt_guest_hook_preflight_v427.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#ifdef __cplusplus
extern "C" {
#endif
enum {
    SHYT_V432_SCE_NP_ID_BYTES=17,
    SHYT_V432_MEMBER_PTR_BYTES=8,
    SHYT_V432_ID_OFFSET=0x36,
    SHYT_V432_MIN_ONLINE_ID=3,
    SHYT_V432_MAX_ONLINE_ID=16,
    SHYT_V432_TRAFFIC_ALLOWED=0
};
typedef struct ShytYtGuestMemberV432 {
    char raw_online_id[SHYT_V432_SCE_NP_ID_BYTES];
    char canonical_member_hex[2*SHYT_V432_MAX_ONLINE_ID+1];
    uint8_t online_id_len;
    uint8_t candidate_read_only;
    uint8_t can_route_game;
} ShytYtGuestMemberV432;

static inline uint64_t shyt_yt_v432_le64(const uint8_t bytes[8]) {
    uint64_t value=0;
    for(unsigned i=0u;i<8u;++i)
        value |= (uint64_t)bytes[i] << (i*8u);
    return value;
}
static inline int shyt_yt_v432_id_ascii(uint8_t c) {
    return (c>='A' && c<='Z') || (c>='a' && c<='z') ||
           (c>='0' && c<='9') || c=='-' || c=='_';
}
static inline int shyt_yt_v432_resolve(
    int exact_109,const char *loaded_sha,ShytYtGuestReadV427 read,
    uint64_t game_member_addr,ShytYtGuestMemberV432 *out) {
    static const char lower_hex[]="0123456789abcdef";
    if(!out)return 0;
    memset(out,0,sizeof(*out));
    if(!exact_109 || !loaded_sha || !read ||
       strcmp(loaded_sha,SHYT_V427_EXPECTED_EBOOT_SHA256)!=0 ||
       game_member_addr<UINT64_C(0x10000) ||
       game_member_addr>UINT64_MAX-SHYT_V432_MEMBER_PTR_BYTES)
        return 0;
    uint8_t ptr[SHYT_V432_MEMBER_PTR_BYTES]={0};
    if(read(game_member_addr,ptr,sizeof(ptr))!=0)return 0;
    const uint64_t identity=shyt_yt_v432_le64(ptr);
    if(identity<UINT64_C(0x10000) ||
       identity>UINT64_MAX-SHYT_V432_ID_OFFSET-SHYT_V432_SCE_NP_ID_BYTES)
        return 0;
    uint8_t id[SHYT_V432_SCE_NP_ID_BYTES]={0};
    if(read(identity+SHYT_V432_ID_OFFSET,id,sizeof(id))!=0)return 0;
    unsigned len=0u;
    for(;len<SHYT_V432_SCE_NP_ID_BYTES;++len) {
        const uint8_t ch=id[len];
        if(ch==0u)break;
        if(!shyt_yt_v432_id_ascii(ch))return 0;
    }
    if(len<SHYT_V432_MIN_ONLINE_ID || len>SHYT_V432_MAX_ONLINE_ID ||
       len==SHYT_V432_SCE_NP_ID_BYTES)return 0;
    for(unsigned i=0u;i<len;++i) {
        out->raw_online_id[i]=(char)id[i];
        out->canonical_member_hex[2u*i]=lower_hex[id[i]>>4u];
        out->canonical_member_hex[2u*i+1u]=lower_hex[id[i]&15u];
    }
    out->online_id_len=(uint8_t)len;
    out->candidate_read_only=1u;
    out->can_route_game=SHYT_V432_TRAFFIC_ALLOWED; /* ALWAYS 0 */
    return 1;
}
#ifdef __cplusplus
}
#endif
#endif
