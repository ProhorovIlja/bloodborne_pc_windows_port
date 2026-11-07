/* SPDX-License-Identifier: GPL-3.0-or-later
 * V428: source+pinned PRIVATE 1.09 image audit; read-only game code sites.
 * The private CUSA03173 decrypted eboot had exact BBHost 1.09 SHA-256.
 * Only 14/20-byte initial instruction sequences are kept here, NEVER
 * the game binary, asset data, or any full function implementation.
 *
 * Independently checked via ELF PT_LOAD mapping and objdump -M intel:
 *  TransportSend RVA 00C8F0A0: push/mov/6 pushes, 14 bytes.
 *  NetSyncUpdate RVA 01789B60: push/mov/5 pushes/sub rsp, 20 bytes.
 *  Existing V17 observer RVA 017894E0: 5 pushes/sub rsp, 20 bytes.
 *  Each initial span ends on a full instruction, with no RIP-relative
 *  addressing, branch or call. This does NOT verify hooking semantics,
 *  packet ownership, guest ABI, original continuation or in-game behavior.
 *  This V428 preflight NEVER calls hook/patch/write/guest functions.
 */
#ifndef SHYT_YT_FULL_GUEST_PREFLIGHT_V428_H
#define SHYT_YT_FULL_GUEST_PREFLIGHT_V428_H
#include "shyt_yt_guest_hook_preflight_v427.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { SHYT_V428_TRANSPORT_BYTES=14, SHYT_V428_UPDATE_BYTES=20,
       SHYT_V428_SAFE_TO_INSTALL_YT_HOOKS=0 };
typedef struct ShytYtFullGuestPreflightV428 {
    uint8_t exact_image;
    uint8_t transport_read;
    uint8_t update_read;
    uint8_t transport_matched;
    uint8_t update_matched;
    uint8_t install_allowed;
} ShytYtFullGuestPreflightV428;

static inline int shyt_yt_full_guest_preflight_v428(
    int exact_109,const char* loaded_sha,ShytYtGuestReadV427 read,
    ShytYtFullGuestPreflightV428* out) {
    static const uint8_t transport[SHYT_V428_TRANSPORT_BYTES]={
        0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
        0x41,0x55,0x41,0x54,0x53,0x50
    };
    static const uint8_t update[SHYT_V428_UPDATE_BYTES]={
        0x55,0x48,0x89,0xe5,0x41,0x57,0x41,0x56,
        0x41,0x55,0x41,0x54,0x53,0x48,0x81,0xec,
        0x18,0x21,0x00,0x00
    };
    if(!out)return 0;
    memset(out,0,sizeof(*out));
    if(!exact_109 || !loaded_sha || !read ||
       strcmp(loaded_sha,SHYT_V427_EXPECTED_EBOOT_SHA256)!=0)
        return 0;
    out->exact_image=1u;
    uint8_t bytes[SHYT_V428_UPDATE_BYTES]={0};
    if(read(SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_TRANSPORT_SEND_RVA,
            bytes,sizeof(transport))==0) {
        out->transport_read=1u;
        out->transport_matched=
            (uint8_t)(memcmp(bytes,transport,sizeof(transport))==0);
    }
    memset(bytes,0,sizeof(bytes));
    if(read(SHYT_V427_PREFERRED_IMAGE_BASE+SHYT_V427_NETSYNC_UPDATE_RVA,
            bytes,sizeof(update))==0) {
        out->update_read=1u;
        out->update_matched=
            (uint8_t)(memcmp(bytes,update,sizeof(update))==0);
    }
    /* Even a perfect exact-image match does not install a hook.
     * No caller can use this as an authorization flag. */
    out->install_allowed=SHYT_V428_SAFE_TO_INSTALL_YT_HOOKS;
    return out->transport_matched && out->update_matched;
}
#ifdef __cplusplus
}
#endif
#endif
