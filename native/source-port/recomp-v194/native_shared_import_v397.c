/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_shared_import_v397.h"
#include <stdlib.h>
static int spec_match(const ShytNativeImportSpecV395 *a,
                      const ShytNativeImportSpecV395 *b) {
    return a->service==b->service &&
           a->recover_code==b->recover_code &&
           a->constant==b->constant;
}
static int compare(const ShytNativeImportSpecV395 *a,
                   const ShytNativeImportSpecV395 *b){
    if(a->guest_target!=b->guest_target)
        return a->guest_target<b->guest_target?-1:1;
    if(a->expected_next!=b->expected_next)
        return a->expected_next<b->expected_next?-1:1;
    return 0;
}
int shyt_native_shared_init_v397(ShytNativeSharedRouterV397 *r,
    ShytNativeOsVmV388 *owner){
    if(!r || r->owner || r->count || r->sealed ||
       !owner || owner->initialized!=1 || owner->sealed!=1 ||
       owner->released)return 0;
    r->owner=owner;
    return 1;
}
int shyt_native_shared_add_v397(ShytNativeSharedRouterV397 *r,
    const ShytNativeImportSpecV395 *spec){
    if(!r || !r->owner || r->sealed || !spec ||
       r->count>=SHYT_V397_MAX_SITES)return 0;
    /* Reuse V395's own service validation before publishing. These
     * per-site temporary routers are never used for runtime dispatch. */
    ShytNativeImportRouterV395 check={0};
    if(!shyt_native_import_init_v395(&check,r->owner) ||
       !shyt_native_import_add_v395(&check,spec))return 0;
    for(size_t i=0;i<r->count;i++){
        const ShytNativeImportSpecV395 *prev=&r->entries[i];
        if(compare(prev,spec)==0)return 0; /* duplicate site */
        if(prev->guest_target==spec->guest_target &&
           !spec_match(prev,spec))return 0; /* conflicting ABI */
    }
    r->entries[r->count++]=*spec;
    return 1;
}
int shyt_native_shared_seal_v397(ShytNativeSharedRouterV397 *r) {
    if(!r || !r->owner || r->sealed || !r->count ||
       r->count>SHYT_V397_MAX_SITES)return 0;
    for(size_t i=1;i<r->count;i++){
        ShytNativeImportSpecV395 key=r->entries[i];
        size_t j=i;
        while(j && compare(&r->entries[j-1],&key)>0) {
            r->entries[j]=r->entries[j-1]; --j;
        }
        r->entries[j]=key;
    }
    for(size_t i=1;i<r->count;i++){
        if(compare(&r->entries[i-1],&r->entries[i])>=0 ||
           (r->entries[i-1].guest_target==r->entries[i].guest_target &&
            !spec_match(&r->entries[i-1],&r->entries[i])))return 0;
    }
    for(size_t i=0;i<r->count;i++){
        if(!shyt_native_import_init_v395(&r->routes[i],r->owner) ||
           !shyt_native_import_add_v395(&r->routes[i],&r->entries[i]) ||
           !shyt_native_import_seal_v395(&r->routes[i]))return 0;
    }
    r->sealed=1;
    return 1;
}
void shyt_native_shared_dispatch_v397(ShytNativeSharedRouterV397 *r,
    BbCpu *cpu,uint64_t target,uint64_t next){
    size_t lo=0,hi;
    if(!r || !r->owner || !r->sealed || !cpu ||
       shyt_generated_owner_v392()!=r->owner ||
       !shyt_generated_active_v390() ||
       !shyt_generated_recovery_depth_v393())abort();
    hi=r->count;
    while(lo<hi){
        size_t mid=lo+(hi-lo)/2;
        if(r->entries[mid].guest_target<target)lo=mid+1;
        else hi=mid;
    }
    if(lo>=r->count || r->entries[lo].guest_target!=target)
        shyt_generated_raise_v393(SHYT_V395_REC_UNKNOWN);
    size_t first=lo;
    while(lo<r->count && r->entries[lo].guest_target==target){
        if(r->entries[lo].expected_next==next){
            shyt_native_import_dispatch_v395(&r->routes[lo],cpu,target,next);
            return;
        }
        ++lo;
    }
    (void)first;
    shyt_generated_raise_v393(SHYT_V395_REC_CONTINUATION);
}
