/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_QUERY_V583_H
#define BB_ARENA_QUERY_V583_H
#include "arena_routes_v582.h"
#include <cstddef>

struct BbQueryRegionV583 { uintptr_t start,end; };
struct BbQueryMapV583 { const BbQueryRegionV583 *rows; size_t count; bool complete; };
/* Containment-only subset (retail flags=0). A partial registry cannot
 * establish a miss. An empty complete registry is a valid snapshot.
 * Keep the snapshot immutable for the duration of the locked call. */
static inline BbForeignV583 bb_query_v583(void *ctx,uintptr_t address) {
    using R=BbForeignV583;
    const auto *m=static_cast<const BbQueryMapV583 *>(ctx);
    if (!m || (m->count && !m->rows)) return R::unavailable;
    for (size_t i=0;i<m->count;++i) {
        const auto &r=m->rows[i];
        if (r.start>=r.end || (i && m->rows[i-1].end>r.start)) return R::unavailable;
    }
    size_t lo=0,hi=m->count;
    while (lo<hi) {
        const size_t mid=lo+(hi-lo)/2;
        if (m->rows[mid].end<=address) lo=mid+1;
        else hi=mid;
    }
    if (lo<m->count && m->rows[lo].start<=address) return R::mapped;
    return m->complete ? R::unmapped : R::unavailable;
}
#endif
