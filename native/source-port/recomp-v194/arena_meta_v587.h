/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_META_V587_H
#define BB_ARENA_META_V587_H
#include "arena_inspect_v585.h"

/* Retail +0xb0. Requires a live arena with trusted, mapped bounds;
 * this checks header flags, not provenance. Never use it to authorize free. */
static inline bool bb_arena_header_live_v587(const BbHeapV581 *h,uintptr_t p) {
    if (!h || !p || (p&15) || p<h->lowest_payload || p>h->highest_payload) return false;
    uintptr_t word;
    std::memcpy(&word,reinterpret_cast<const void *>(p-8),sizeof word);
    const uintptr_t next=word&~uintptr_t{3};
    if (!(word&1) || next<h->lowest_payload || next>h->highest_payload || (next&15)) return false;
    unsigned char flags;
    std::memcpy(&flags,reinterpret_cast<const void *>(next+8),1);
    return (flags&2)!=0;
}
/* Retail +0x20 writes a four-byte result, not a pointer-sized value. */
static inline bool bb_arena_kind_v587(void *out,size_t size) {
    if (!out || size<4) return false;
    const unsigned char kind[]={0x3b,0,0,0};
    std::memcpy(out,kind,sizeof kind);
    return true;
}
#endif
