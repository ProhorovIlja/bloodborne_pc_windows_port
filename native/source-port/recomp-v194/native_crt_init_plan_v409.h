/* SPDX-License-Identifier: GPL-2.0-or-later
 * Owner-built AOT initializer plan. IDs are private image-relative
 * identities, never addresses cast to function pointers.
 */
#ifndef SHYT_NATIVE_INIT_V409_H
#define SHYT_NATIVE_INIT_V409_H
#include "native_crt_lifecycle_v409.h"
enum { SHYT_INIT_MAX_V409 = 65536 };
typedef struct {
    uint64_t id;
    int (*fn)(void *, ShytCrtV409 *);
} ShytInitBindingV409;

static inline const ShytInitBindingV409 *shyt_init_lookup_v409(
    const ShytInitBindingV409 *bindings,size_t n,uint64_t id) {
    size_t lo=0,hi=n;
    while(lo<hi){
        const size_t mid=lo+(hi-lo)/2;
        if(bindings[mid].id<id)lo=mid+1;
        else hi=mid;
    }
    return lo<n && bindings[lo].id==id ? &bindings[lo] : NULL;
}

/* Forward and legacy plans are in storage order; legacy runs in
 * reverse. Extraction must remove sentinels and null slots offline.
 * Prevalidate all IDs before calling any initializer. A bound host
 * initializer's own failure stops execution but is not transactional.
 * Caller owns immutable plan and registry for the full invocation.
 */
static inline int shyt_init_run_v409(
    ShytCrtV409 *crt, void *context, const ShytInitBindingV409 *bindings,
    size_t n, const uint64_t *forward, size_t nf,
    const uint64_t *legacy, size_t nl) {
    if(!crt || crt->phase!=SHYT_CRT_INIT_V409 || n>SHYT_INIT_MAX_V409 ||
       nf>SHYT_INIT_MAX_V409 || nl>SHYT_INIT_MAX_V409-nf ||
       (n && !bindings) || (nf && !forward) || (nl && !legacy))
        return 0;
    for(size_t i=0;i<n;++i)
        if(!bindings[i].fn || (i && bindings[i-1].id>=bindings[i].id))
            return 0;
    for(size_t i=0;i<nf;++i)
        if(!shyt_init_lookup_v409(bindings,n,forward[i]))return 0;
    for(size_t i=0;i<nl;++i)
        if(!shyt_init_lookup_v409(bindings,n,legacy[i]))return 0;
    for(size_t i=0;i<nf;++i)
        if(!shyt_init_lookup_v409(bindings,n,forward[i])->fn(context,crt))return 0;
    while(nl)
        if(!shyt_init_lookup_v409(bindings,n,legacy[--nl])->fn(context,crt))return 0;
    return 1;
}
#endif
