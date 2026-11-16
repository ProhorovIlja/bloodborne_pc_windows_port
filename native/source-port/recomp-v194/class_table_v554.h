/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLASS_TABLE_V554_H
#define BB_CLASS_TABLE_V554_H
#include "registry_reserve_v541.h"

enum bb_class_v554 { BB_CLASS_INVALID, BB_CLASS_STOP, BB_CLASS_FULL, BB_CLASS_OK };
/* Primary DLRuntimeClass table only. Input records are sorted by word 3.
 * Caller serializes access, owns nonoverlapping host buffers, and handles
 * terminal allocation failure and the separate secondary table. */
static inline enum bb_class_v554 bb_class_insert_v554(unsigned char *h,size_t n,uint64_t hva,
        const struct bb_vector_block_v541 *old,const uint64_t row[4],void *ctx,
        int (*alloc)(void *,uint64_t,size_t,struct bb_vector_block_v541 *),
        int (*release)(void *,uint64_t,uint64_t)) {
    if (!h || n<40 || !hva || hva>UINT64_MAX-40 || !row || !row[0] || !alloc || !release)
        return BB_CLASS_INVALID;
    uint64_t lo=bb_vector_word_v541(h+8),hi=bb_vector_word_v541(h+16),cap=bb_vector_word_v541(h+24);
    const uint64_t owner=bb_vector_word_v541(h+32);
    const uint64_t item[4]={row[0],row[1],row[2],row[3]};
    if (!owner || hi<lo || cap<hi || ((lo|hi|cap)&7) || ((hi-lo)|(cap-lo))%32 ||
        (!lo && cap) || (lo<hva+40 && hva<cap) ||
        (lo && (!old || !old->data || old->va!=lo || cap-lo>old->size))) return BB_CLASS_INVALID;
    unsigned char *data=lo?old->data:NULL;
    if (lo==hi && cap-lo<0x4000) {
        struct bb_vector_block_v541 b={0};
        if (!alloc(ctx,owner,0x4000,&b) || !b.data || b.size<0x4000 || !b.va || (b.va&7) ||
            b.va>UINT64_MAX-0x4000 || b.va==lo || (b.va<cap && lo<b.va+0x4000) ||
            (b.va<hva+40 && hva<b.va+0x4000) || (lo && !release(ctx,owner,lo))) return BB_CLASS_STOP;
        data=b.data; lo=hi=b.va; cap=lo+0x4000;
        bb_arena_store_v527(h+24,cap);
        bb_arena_store_v527(h+16,hi);
        bb_arena_store_v527(h+8,lo);
    }
    const size_t used=(size_t)(hi-lo);
    size_t first=0,last=used/32;
    while (first<last) {
        const size_t mid=first+(last-first)/2;
        if (item[3]<bb_vector_word_v541(data+32*mid+24)) last=mid;
        else first=mid+1;
    }
    const size_t at=32*first;
    if (hi==cap) {
        const size_t count=used/32, max=SIZE_MAX/32;
        if (count>=max) return BB_CLASS_STOP;
        size_t grown=count/2>max-count?count+1:count+count/2;
        if (grown==count) ++grown;
        const size_t bytes=grown*32;
        struct bb_vector_block_v541 b={0};
        if (!alloc(ctx,owner,bytes,&b) || !b.data || b.size<bytes || !b.va || (b.va&7) ||
            b.va>UINT64_MAX-bytes || (b.va<cap && lo<b.va+bytes) ||
            (b.va<hva+40 && hva<b.va+bytes)) return BB_CLASS_STOP;
        if (at) memcpy(b.data,data,at);
        for (unsigned i=0;i<4;++i) bb_arena_store_v527(b.data+at+8*i,item[i]);
        if (used>at) memcpy(b.data+at+32,data+at,used-at);
        if (!release(ctx,owner,lo)) return BB_CLASS_STOP;
        bb_arena_store_v527(h+24,b.va+bytes);
        bb_arena_store_v527(h+16,b.va+used+32);
        bb_arena_store_v527(h+8,b.va);
        return BB_CLASS_OK;
    }
    memmove(data+at+32,data+at,used-at);
    for (unsigned i=0;i<4;++i) bb_arena_store_v527(data+at+8*i,item[i]);
    bb_arena_store_v527(h+16,hi+32);
    return BB_CLASS_OK;
}
#endif
