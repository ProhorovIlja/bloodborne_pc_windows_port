/* SPDX-License-Identifier: GPL-2.0-or-later
 * V362: SHAD GamePacketsType (0x40) game-frame BODY codec from pinned
 * Yharnam Together v1.3.1 server/coop/game_link.h,
 * Git blob 5029581251bfe5decf562c19a10bdd079150cdad.
 *
 * This is only the body AFTER SHAD+type, NOT SHLK link authentication,
 * Noise NK encryption, authorized peer delivery or a working co-op game.
 * Original YT permits larger sender frames and more entries. This C
 * interop codec deliberately bounds any decoded body to 64 KiB and 64
 * entries before use by a future verified transport.
 */
#ifndef SHYT_YT_GAME_FRAME_V362_H
#define SHYT_YT_GAME_FRAME_V362_H
#include <stddef.h>
#include <stdint.h>
#define SHYT_YT_GAME_FRAME_VERSION_V362 1u
#define SHYT_YT_GAME_PACKETS_TYPE_V362 0x40u
#define SHYT_YT_GAME_MAX_SENDER_V362 255u
#define SHYT_YT_GAME_MAX_ENTRIES_V362 64u
#define SHYT_YT_GAME_MAX_WIRE_V362 65536u

typedef struct ShytYtGameFrameEntryV362 {
    uint8_t packet_class;  /* 0 = unreliable, 1 = reliable */
    uint32_t seq;
    const uint8_t *packet; /* points into owner input on decode */
    uint32_t packet_size;
} ShytYtGameFrameEntryV362;
typedef struct ShytYtGameFrameV362 {
    uint8_t sender_len;
    uint8_t sender[SHYT_YT_GAME_MAX_SENDER_V362];
    uint32_t instance;      /* owner game launch incarnation */
    uint32_t peer_instance; /* peer game launch incarnation */
    uint32_t ack;           /* reliable stream cumulative ACK */
    uint16_t entries_count;
    ShytYtGameFrameEntryV362 entries[SHYT_YT_GAME_MAX_ENTRIES_V362];
} ShytYtGameFrameV362;
#ifdef __cplusplus
extern "C" {
#endif
/* Succeeds only for the original body format, no outer SHAD/SHLK header.
 * With failed decode, out is entirely reset to zeros.
 * Any decoded packet pointers borrow input bytes, never store past input.
 */
int shyt_yt_game_frame_decode_v362(
    const uint8_t *body,size_t body_len,ShytYtGameFrameV362 *out);
/* On failure written=0; caller must discard any partially encoded bytes. */
int shyt_yt_game_frame_encode_v362(
    const ShytYtGameFrameV362 *in,
    uint8_t *out,size_t out_capacity,size_t *written);
#ifdef __cplusplus
}
#endif
#endif
