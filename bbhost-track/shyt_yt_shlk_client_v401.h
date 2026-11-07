/* SPDX-License-Identifier: GPL-2.0-or-later
 * V401 original YT 1.3.1 SHLK v4 Noise NK CLIENT C ABI for BBHost.
 * Actual cryptographic code is directly linked from source-pinned original
 * YT server/coop/link_auth.h + Monocypher 4.0.3.
 *
 * This is an in-process crypto/session primitive only, NOT network I/O,
 * matchmaking, relay, host permission, game hook or online gameplay.
 * Identity/credential construction belongs to the original YT handshake.
 * DO NOT accept a user-generated random/nonce from game packets: fresh_ephemeral
 * must come from a cryptographically secure OS random source for each NEW hello.
 */
#ifndef SHYT_YT_SHLK_CLIENT_V401_H
#define SHYT_YT_SHLK_CLIENT_V401_H
#include <stddef.h>
#include <stdint.h>
#define SHYT_YT_SHLK_KEY_V401 32u
#define SHYT_YT_SHLK_COOKIE_V401 16u
#define SHYT_YT_SHLK_MAX_WIRE_V401 65536u
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytYtShlkClientV401 ShytYtShlkClientV401;
ShytYtShlkClientV401 *shyt_yt_shlk_new_v401(void);
void shyt_yt_shlk_free_v401(ShytYtShlkClientV401 *link);
/* Server identity MUST already be checked against launcher's pinned key. */
int shyt_yt_shlk_pin_v401(ShytYtShlkClientV401 *link,
                           const uint8_t pub[SHYT_YT_SHLK_KEY_V401]);
int shyt_yt_shlk_cookie_v401(ShytYtShlkClientV401 *link,
                              const uint8_t cookie[SHYT_YT_SHLK_COOKIE_V401],
                              const uint8_t server_pub[SHYT_YT_SHLK_KEY_V401]);
/* Handshake: valid SHLK4 original hello plaintext, caller-held CSPRNG 32B. */
int shyt_yt_shlk_hello_v401(ShytYtShlkClientV401 *link,
                             const uint8_t *plain,size_t plain_len,
                             const uint8_t fresh_ephemeral[SHYT_YT_SHLK_KEY_V401],
                             uint8_t *wire,size_t cap,size_t *written);
/* Inbound sealed welcome or established-server datagram. Must not bypass
 * original Client::Open which checks tag, identity and anti-replay. */
int shyt_yt_shlk_open_v401(ShytYtShlkClientV401 *link,
                            const uint8_t *wire,size_t size,
                            uint8_t *plain,size_t cap,size_t *written);
/* Outbound established SHLK datagram (header+body), encrypted and tagged.
 * No sending or bypass to BBHost UDP sockets is performed. */
int shyt_yt_shlk_seal_v401(ShytYtShlkClientV401 *link,
                            const uint8_t *plain,size_t size,
                            uint8_t *wire,size_t cap,size_t *written);
int shyt_yt_shlk_linked_v401(const ShytYtShlkClientV401 *link);
#ifdef __cplusplus
}
#endif
#endif
