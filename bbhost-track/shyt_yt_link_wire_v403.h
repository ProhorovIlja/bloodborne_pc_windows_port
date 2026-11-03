/* SPDX-License-Identifier: GPL-2.0-or-later
 * BBHost C ABI for ORIGINAL Yharnam Together v1.3.1 outer SHLK v4
 * Data/Coop/Ping/Cookie/Welcome wire messages, not a custom protocol.
 * No UDP sockets, account identifiers, packet logging or handshake here.
 * The caller MUST authenticate/encrypt via original V401 SHLK before
 * accepting inbound frames or sending outbound data. DO NOT expose any
 * decoded Data to the game without verified room/map/owner permissions.
 */
#ifndef SHYT_YT_LINK_WIRE_V403_H
#define SHYT_YT_LINK_WIRE_V403_H
#include <stddef.h>
#include <stdint.h>
#define SHYT_YT_LINK_WIRE_MAX_V403 65536u
#define SHYT_YT_LINK_COOKIE_V403 16u
#define SHYT_YT_LINK_KEY_V403 32u
#define SHYT_YT_LINK_MESSAGE_DATA_V403 3u
#define SHYT_YT_LINK_MESSAGE_COOP_V403 7u
#ifdef __cplusplus
extern "C" {
#endif
/* On failure *written=0, disregard any partially filled output. */
int shyt_yt_link_encode_data_v403(
    uint32_t addr_nbo,uint16_t port_nbo,
    const uint8_t *frame,size_t frame_bytes,
    uint8_t *wire,size_t cap,size_t *written);
int shyt_yt_link_decode_data_v403(
    const uint8_t *wire,size_t wire_bytes,
    uint32_t *addr_nbo,uint16_t *port_nbo,
    uint8_t *frame,size_t cap,size_t *frame_bytes);
int shyt_yt_link_encode_coop_v403(
    const uint8_t *body,size_t body_bytes,
    uint8_t *wire,size_t cap,size_t *written);
int shyt_yt_link_decode_coop_v403(
    const uint8_t *wire,size_t wire_bytes,
    uint8_t *body,size_t cap,size_t *body_bytes);
int shyt_yt_link_decode_cookie_v403(
    const uint8_t *wire,size_t wire_bytes,
    uint8_t cookie[SHYT_YT_LINK_COOKIE_V403],
    uint8_t server_pub[SHYT_YT_LINK_KEY_V403],
    uint8_t *work_bits);
int shyt_yt_link_decode_welcome_v403(
    const uint8_t *wire,size_t wire_bytes,
    int *accepted,char *reason,size_t reason_cap);
int shyt_yt_link_encode_ping_v403(
    uint8_t kind,uint32_t seq,uint64_t sent_ms,
    uint8_t *wire,size_t cap,size_t *written);
int shyt_yt_link_decode_ping_v403(
    uint8_t kind,const uint8_t *wire,size_t wire_bytes,
    uint32_t *seq,uint64_t *sent_ms);
int shyt_yt_link_kind_v403(
    const uint8_t *wire,size_t wire_bytes);
#ifdef __cplusplus
}
#endif
#endif
