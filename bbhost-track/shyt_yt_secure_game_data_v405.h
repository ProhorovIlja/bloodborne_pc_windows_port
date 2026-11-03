/* SPDX-License-Identifier: GPL-2.0-or-later
 * V405: REAL authenticated game-packet datagram path inside BBHost:
 * game vport P2P frame -> original YT SHLK Data -> original Noise NK Seal
 * and original Noise NK Open -> YT SHLK Data -> game vport P2P frame.
 * The configured server endpoint MUST be verified by a future socket
 * adapter. This primitive DOES NOT AUTHORIZE direct peers, rooms,
 * invaders, owner/map routing, or write anything to guest memory.
 */
#ifndef SHYT_YT_SECURE_GAME_DATA_V405_H
#define SHYT_YT_SECURE_GAME_DATA_V405_H
#include "shyt_yt_shlk_client_v401.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* On failure, *written=0 and any prior outer plaintext bytes produced
 * within "wire" are wiped. On success, "wire" is sealed, authenticated
 * and includes the full server-forwarded SHLK4 header and 24-byte trailer.
 */
int shyt_yt_secure_send_data_v405(
    ShytYtShlkClientV401 *link,uint32_t addr_nbo,uint16_t port_nbo,
    const uint8_t *game,size_t game_bytes,
    uint8_t *wire,size_t wire_capacity,size_t *written);
/* On failure *game_bytes=0, *addr_nbo=0, *port_nbo=0. On success the
 * datagram has passed Noise NK authentication and anti-replay, but
 * the caller MUST STILL enforce YT room/map/owner rules and verify that
 * it arrived from the configured server's actual UDP socket address.
 */
int shyt_yt_secure_receive_data_v405(
    ShytYtShlkClientV401 *link,
    const uint8_t *wire,size_t wire_bytes,
    uint32_t *addr_nbo,uint16_t *port_nbo,
    uint8_t *game,size_t game_capacity,size_t *game_bytes);
#ifdef __cplusplus
}
#endif
#endif
