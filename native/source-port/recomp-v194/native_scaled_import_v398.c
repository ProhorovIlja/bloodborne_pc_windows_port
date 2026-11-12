/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_scaled_import_v398.h"
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>

static int compare_site(const ShytNativeImportSpecV395 *a,
                        const ShytNativeImportSpecV395 *b) {
    if(a->guest_target!=b->guest_target)
        return a->guest_target<b->guest_target?-1:1;
    if(a->expected_next!=b->expected_next)
        return a->expected_next<b->expected_next?-1:1;
    return 0;
}
static int qsort_site(const void *a,const void *b) {
    return compare_site((const ShytNativeImportSpecV395 *)a,
                        (const ShytNativeImportSpecV395 *)b);
}
static int same_abi(const ShytNativeImportSpecV395 *a,
                    const ShytNativeImportSpecV395 *b) {
    return a->service==b->service &&
           a->recover_code==b->recover_code &&
           a->constant==b->constant;
}
int shyt_native_scaled_init_v398(ShytNativeScaledRouterV398 *r,
    ShytNativeOsVmV388 *owner,size_t capacity) {
    if(!r || r->owner || r->sites || r->count || r->capacity ||
       r->sealed || !owner || owner->initialized!=1 ||
       owner->sealed!=1 || owner->released || !capacity ||
       capacity>SHYT_V398_MAX_SITES ||
       capacity>SIZE_MAX/sizeof(ShytNativeImportSpecV395))
        return 0;
    ShytNativeImportSpecV395 *data=
        (ShytNativeImportSpecV395 *)calloc(
            capacity,sizeof(ShytNativeImportSpecV395));
    if(!data)return 0;
    r->owner=owner;r->sites=data;r->capacity=capacity;
    return 1;
}
int shyt_native_scaled_add_v398(ShytNativeScaledRouterV398 *r,
    const ShytNativeImportSpecV395 *s) {
    if(!r || !r->owner || !r->sites || !s || r->sealed ||
       r->count>=r->capacity ||
       !shyt_native_import_spec_valid_v398(s))return 0;
    for(size_t i=0;i<r->count;i++) {
        const ShytNativeImportSpecV395 *prev=&r->sites[i];
        if(compare_site(prev,s)==0)return 0;
        if(prev->guest_target==s->guest_target &&
           !same_abi(prev,s))return 0;
    }
    r->sites[r->count++]=*s;
    return 1;
}
int shyt_native_scaled_seal_v398(ShytNativeScaledRouterV398 *r) {
    if(!r || !r->owner || !r->sites || r->sealed || !r->count ||
       r->count>r->capacity)return 0;
    qsort(r->sites,r->count,sizeof(r->sites[0]),qsort_site);
    for(size_t i=0;i<r->count;i++) {
        if(!shyt_native_import_spec_valid_v398(&r->sites[i]))
            return 0;
        if(i && (compare_site(&r->sites[i-1],&r->sites[i])>=0 ||
                 (r->sites[i-1].guest_target==r->sites[i].guest_target &&
                  !same_abi(&r->sites[i-1],&r->sites[i]))))
            return 0;
    }
    r->sealed=1;
    return 1;
}
int shyt_native_scaled_release_v398(ShytNativeScaledRouterV398 *r,
    int all_access_threads_joined) {
    if(!r || !r->owner || !r->sites || !all_access_threads_joined ||
       !shyt_native_vm_quiescent_v386(&r->owner->vm))
        return 0;
    /* All potential threads have been joined, no one can start a new
     * guest pin after VM close; no concurrent callbacks or table reads. */
    free(r->sites);
    r->sites=NULL;r->owner=NULL;r->count=0;r->capacity=0;r->sealed=0;
    return 1;
}
void shyt_native_scaled_dispatch_v398(ShytNativeScaledRouterV398 *r,
    BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!r || !r->owner || !r->sites || !r->sealed || !cpu ||
       shyt_generated_owner_v392()!=r->owner ||
       !shyt_generated_active_v390() ||
       !shyt_generated_recovery_depth_v393())abort();
    /* First binary search targets. Unknown targets get 501. */
    size_t lo=0,hi=r->count;
    while(lo<hi) {
        size_t mid=lo+(hi-lo)/2;
        if(r->sites[mid].guest_target<target)lo=mid+1;
        else hi=mid;
    }
    if(lo>=r->count || r->sites[lo].guest_target!=target)
        shyt_generated_raise_v393(SHYT_V395_REC_UNKNOWN);
    const size_t first=lo;
    /* Second binary search the continuation among this target's
     * pair-sorted registrations, still O(log N), not a linear walk. */
    hi=r->count;
    while(lo<hi){
        size_t mid=lo+(hi-lo)/2;
        if(r->sites[mid].guest_target<target ||
          (r->sites[mid].guest_target==target &&
           r->sites[mid].expected_next<next))lo=mid+1;
        else hi=mid;
    }
    if(lo>=r->count || r->sites[lo].guest_target!=target ||
       r->sites[lo].expected_next!=next) {
        (void)first;
        shyt_generated_raise_v393(SHYT_V395_REC_CONTINUATION);
    }
    shyt_native_import_dispatch_site_v398(r->owner,&r->sites[lo],
                                         cpu,target,next);
}
