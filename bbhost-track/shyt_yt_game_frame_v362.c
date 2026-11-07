/* SPDX-License-Identifier: GPL-2.0-or-later
 * BBHost C ABI codec for original YT 1.3.1 SHAD GamePacketsType=0x40.
 * Exact source-based format, not a standalone authenticated transport.
 * All integers LE. No dynamic allocation, sockets, file IO, game memory
 * dereference, player IDs or packet payload logging.
 */
#include "shyt_yt_game_frame_v362.h"
#include <string.h>

static int read_bytes_v362(const uint8_t *in,size_t cap,size_t *at,
                           void *dest,size_t n) {
    if (!in || !at || !dest || *at>cap || n>cap-*at) return 0;
    if (n) memcpy(dest,in+*at,n);
    *at+=n;
    return 1;
}
static int read_le_v362(const uint8_t *in,size_t cap,size_t *at,
                        unsigned n,uint32_t *value) {
    if (!in || !at || !value || n>4u || *at>cap || n>cap-*at)
        return 0;
    uint32_t result=0;
    for(unsigned i=0;i<n;++i) result|=(uint32_t)in[*at+i]<<(8u*i);
    *at+=n;
    *value=result;
    return 1;
}
static int write_bytes_v362(uint8_t *out,size_t cap,size_t *at,
                            const void *src,size_t n) {
    if (!out || !at || (n && !src) || *at>cap ||
        n>cap-*at || n>SHYT_YT_GAME_MAX_WIRE_V362-*at)
        return 0;
    if (n) memcpy(out+*at,src,n);
    *at+=n;
    return 1;
}
static int write_le_v362(uint8_t *out,size_t cap,size_t *at,
                         uint32_t value,unsigned n) {
    if (n>4u || !out || !at || *at>cap ||
        n>cap-*at || n>SHYT_YT_GAME_MAX_WIRE_V362-*at)
        return 0;
    for(unsigned i=0;i<n;++i) out[(*at)++]=(uint8_t)(value>>(8u*i));
    return 1;
}

int shyt_yt_game_frame_decode_v362(
    const uint8_t *body,size_t body_len,ShytYtGameFrameV362 *out) {
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!body || body_len>SHYT_YT_GAME_MAX_WIRE_V362) return 0;
    ShytYtGameFrameV362 tmp={0};
    size_t at=0;
    uint32_t version=0,sender=0,count=0;
    if (!read_le_v362(body,body_len,&at,1u,&version) ||
        version!=SHYT_YT_GAME_FRAME_VERSION_V362 ||
        !read_le_v362(body,body_len,&at,1u,&sender) ||
        sender>SHYT_YT_GAME_MAX_SENDER_V362)
        return 0;
    tmp.sender_len=(uint8_t)sender;
    if (!read_bytes_v362(body,body_len,&at,tmp.sender,sender) ||
        !read_le_v362(body,body_len,&at,4u,&tmp.instance) ||
        !read_le_v362(body,body_len,&at,4u,&tmp.peer_instance) ||
        !read_le_v362(body,body_len,&at,4u,&tmp.ack) ||
        !read_le_v362(body,body_len,&at,2u,&count) ||
        count>SHYT_YT_GAME_MAX_ENTRIES_V362)
        return 0;
    tmp.entries_count=(uint16_t)count;
    for (uint32_t i=0;i<count;++i) {
        uint32_t klass=0,packet_size=0;
        ShytYtGameFrameEntryV362 *e=&tmp.entries[i];
        if (!read_le_v362(body,body_len,&at,1u,&klass) ||
            klass>1u ||
            !read_le_v362(body,body_len,&at,4u,&e->seq) ||
            !read_le_v362(body,body_len,&at,4u,&packet_size) ||
            at>body_len || packet_size>body_len-at)
            return 0;
        e->packet_class=(uint8_t)klass;
        e->packet_size=packet_size;
        e->packet=body+at;
        at+=packet_size;
    }
    if (at!=body_len) return 0;
    *out=tmp;
    return 1;
}

int shyt_yt_game_frame_encode_v362(
    const ShytYtGameFrameV362 *in,
    uint8_t *out,size_t out_capacity,size_t *written) {
    if (!written) return 0;
    *written=0;
    if (!in || !out || out_capacity==0 ||
        in->entries_count>SHYT_YT_GAME_MAX_ENTRIES_V362)
        return 0;
    size_t at=0;
    if (!write_le_v362(out,out_capacity,&at,SHYT_YT_GAME_FRAME_VERSION_V362,1u) ||
        !write_le_v362(out,out_capacity,&at,in->sender_len,1u) ||
        !write_bytes_v362(out,out_capacity,&at,in->sender,in->sender_len) ||
        !write_le_v362(out,out_capacity,&at,in->instance,4u) ||
        !write_le_v362(out,out_capacity,&at,in->peer_instance,4u) ||
        !write_le_v362(out,out_capacity,&at,in->ack,4u) ||
        !write_le_v362(out,out_capacity,&at,in->entries_count,2u))
        return 0;
    for (uint32_t i=0;i<in->entries_count;++i) {
        const ShytYtGameFrameEntryV362 *e=&in->entries[i];
        if (e->packet_class>1u ||
            e->packet_size>SHYT_YT_GAME_MAX_WIRE_V362 ||
            (e->packet_size && !e->packet) ||
            !write_le_v362(out,out_capacity,&at,e->packet_class,1u) ||
            !write_le_v362(out,out_capacity,&at,e->seq,4u) ||
            !write_le_v362(out,out_capacity,&at,e->packet_size,4u) ||
            !write_bytes_v362(out,out_capacity,&at,e->packet,e->packet_size))
            return 0;
    }
    *written=at;
    return 1;
}
