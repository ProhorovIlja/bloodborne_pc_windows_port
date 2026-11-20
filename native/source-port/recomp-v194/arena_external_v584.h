/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_EXTERNAL_V584_H
#define BB_ARENA_EXTERNAL_V584_H
#include "arena_query_v583.h"

enum class BbMemoryKindV584 { direct, flexible };
struct BbExternalRecordV584 {
    uintptr_t base;
    uint64_t physical,length;
    BbMemoryKindV584 kind;
    bool unmapped;
};
struct BbExternalV584 {
    BbQueryMapV583 mappings;
    BbExternalRecordV584 *records;
    size_t count;
    void *user;
    bool (*unmap)(void *,uintptr_t,uint64_t);
    bool (*direct)(void *,uint64_t,uint64_t);
    bool (*flexible)(void *,uintptr_t,uint64_t);
};
/* The mapping snapshot is supplied by the caller; exact allocation records
 * authorize release. Under the arena lock, callbacks cannot reenter. A direct
 * allocation whose physical release failed is retried without unmapping twice.
 * Unlike retail, backend errors retain the record rather than dropping it. */
static inline BbForeignV583 bb_external_query_v584(void *p,uintptr_t address) {
    auto *x=static_cast<BbExternalV584 *>(p);
    if (!x || (x->count && !x->records)) return BbForeignV583::unavailable;
    for (size_t i=0;i<x->count;++i)
        if (x->records[i].base==address && x->records[i].unmapped)
            return BbForeignV583::mapped; // pending physical release only
    return bb_query_v583(&x->mappings,address);
}
static inline bool bb_external_free_v584(void *p,uintptr_t address) {
    auto *x=static_cast<BbExternalV584 *>(p);
    if (!x || !address || (x->count && !x->records)) return false;
    BbExternalRecordV584 *found=nullptr;
    for (size_t i=0;i<x->count;++i) {
        auto &r=x->records[i];
        if (r.base!=address) continue;
        if (found) return false;
        found=&r;
    }
    if (!found) return true;
    auto &r=*found;
    if (!r.length || r.length>UINTPTR_MAX-r.base) return false;
    if (r.kind==BbMemoryKindV584::direct) {
        if (!x->unmap || !x->direct || r.length>UINT64_MAX-r.physical) return false;
        if (!r.unmapped) {
            if (!x->unmap(x->user,r.base,r.length)) return false;
            r.unmapped=true;
        }
        if (!x->direct(x->user,r.physical,r.length)) return false;
    } else if (r.kind==BbMemoryKindV584::flexible) {
        if (r.unmapped || !x->flexible || !x->flexible(x->user,r.base,r.length)) return false;
    } else return false;
    r={};
    return true;
}
#endif
