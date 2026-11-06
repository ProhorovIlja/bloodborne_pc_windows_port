/* SPDX-License-Identifier: GPL-3.0-or-later
 * Seamless Hunt V427: image-only, READ-ONLY Bloodborne 1.09 hook site
 * preflight for adapting original YT v1.4.0 NetSync to BBHost.
 *
 * Source anchors (YT efa0ad265d84, pinned BBHost v0.2.24):
 * - emulator/src/core/bloodborne_patch_sites.h:
 *     transport send @ RVA 0x00C8F0A0, prefix 55 48 89 E5 41 57
 *     net sync update @ RVA 0x01789B60, same prefix
 * - docs/NATIVE_NETCODE.md: NetSync game packet sender RVA 0x017894E0
 *     is a DIFFERENT observation point already used by V17.
 * - BBHost plugin API takes Binary Ninja addresses = RVA + 0x400000.
 *
 * Six verified bytes NEVER suffice to install a BBHost prologue hook:
 * hook2 requires >=14 whole instruction bytes with no unsafe RIP-relative
 * relocation; a FULL hook ABI, detour length, execution thread, original
 * function continuation and guest delivery are separately unverified.
 *
 * No writes, hooks, remote socket, game packet capture or grants here.
 */
#ifndef SHYT_YT_GUEST_HOOK_PREFLIGHT_V427_H
#define SHYT_YT_GUEST_HOOK_PREFLIGHT_V427_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif
enum {
    SHYT_V427_SITE_COUNT=2,
    SHYT_V427_PREFIX_LENGTH=6,
    SHYT_V427_HOOK_INSTALL_ALLOWED=0
};
#define SHYT_V427_EXPECTED_EBOOT_SHA256 "941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7"
#define SHYT_V427_PREFERRED_IMAGE_BASE UINT64_C(0x400000)
#define SHYT_V427_TRANSPORT_SEND_RVA UINT64_C(0x00C8F0A0)
#define SHYT_V427_NETSYNC_UPDATE_RVA UINT64_C(0x01789B60)

typedef int (*ShytYtGuestReadV427)(uint64_t bn,void* out,size_t n);

typedef struct ShytYtGuestHookPreflightV427 {
    uint8_t expected_image;
    uint8_t sites_read;
    uint8_t sites_matching;
    uint8_t sites_mismatching;
    uint8_t unsafe_hook_install_allowed;
} ShytYtGuestHookPreflightV427;

static inline uint64_t shyt_yt_guest_site_bn_v427(unsigned index) {
    switch(index) {
    case 0u: return SHYT_V427_PREFERRED_IMAGE_BASE+
                    SHYT_V427_TRANSPORT_SEND_RVA;
    case 1u: return SHYT_V427_PREFERRED_IMAGE_BASE+
                    SHYT_V427_NETSYNC_UPDATE_RVA;
    default: return 0u;
    }
}

static inline int shyt_yt_guest_hook_preflight_v427(
    int exact_109,const char* loaded_sha,ShytYtGuestReadV427 read,
    ShytYtGuestHookPreflightV427* result) {
    static const uint8_t expected_prefix[SHYT_V427_PREFIX_LENGTH]={
        0x55u,0x48u,0x89u,0xe5u,0x41u,0x57u
    };
    if(!result)return 0;
    memset(result,0,sizeof(*result));
    /* Do not inspect an unknown eboot or guess its offsets, even when
     * a fake host reports eboot_is_109 but exposes the wrong digest. */
    if(!exact_109 || !loaded_sha || !read ||
       strcmp(loaded_sha,SHYT_V427_EXPECTED_EBOOT_SHA256)!=0)
        return 0;
    result->expected_image=1u;
    for(unsigned i=0u;i<SHYT_V427_SITE_COUNT;++i) {
        uint8_t actual[SHYT_V427_PREFIX_LENGTH]={0};
        const uint64_t addr=shyt_yt_guest_site_bn_v427(i);
        if(!addr || read(addr,actual,sizeof(actual))!=0)continue;
        ++result->sites_read;
        if(memcmp(actual,expected_prefix,sizeof(actual))==0)
            ++result->sites_matching;
        else
            ++result->sites_mismatching;
    }
    /* Deliberate constant false, even when both signatures match.
     * A six-byte prefix is NOT a full 14+ byte instruction-boundary
     * proof. The V17 observer, if separately opted in, is unchanged. */
    result->unsafe_hook_install_allowed=SHYT_V427_HOOK_INSTALL_ALLOWED;
    return result->sites_matching==SHYT_V427_SITE_COUNT;
}
#ifdef __cplusplus
}
#endif
#endif
