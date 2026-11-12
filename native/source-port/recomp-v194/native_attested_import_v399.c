/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_attested_import_v399.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static int functions_valid(const ShytNativeFunctionProofV399 *functions,
                           size_t count,uint64_t base) {
    if(!functions || !count || count>100000u || base==0)return 0;
    for(size_t i=0;i<count;i++) {
        const ShytNativeFunctionProofV399 *f=&functions[i];
        if(!f->hash || !f->hash[0] || f->compiled!=1 ||
           f->direct_slot!=1 || !f->size ||
           f->offset>UINT64_MAX-base ||
           f->size>UINT64_MAX-f->offset ||
           f->size>UINT64_MAX-base-f->offset)return 0;
        if(i) {
            const ShytNativeFunctionProofV399 *prev=&functions[i-1];
            if(prev->offset>=f->offset ||
               prev->size>f->offset-prev->offset)return 0;
        }
    }
    return 1;
}
int shyt_native_bind_attested_v399(ShytNativeScaledRouterV398 *router,
    ShytNativeOsVmV388 *owner,
    const ShytNativeSourceSiteV399 *sites,size_t site_count,
    size_t independently_attested_site_count,
    const ShytNativeFunctionProofV399 *functions,size_t function_count,
    uint64_t image_base) {
    if(!router || router->owner || router->sites || router->count ||
       router->capacity || router->sealed ||
       !owner || owner->initialized!=1 || owner->sealed!=1 ||
       owner->released || !sites || !site_count ||
       site_count!=independently_attested_site_count ||
       site_count>SHYT_V398_MAX_SITES ||
       !functions_valid(functions,function_count,image_base))return 0;
    /* Fail closed BEFORE allocating any router backing. No unverified
     * source entry can be silently published or truncated. */
    for(size_t i=0;i<site_count;i++) {
        const ShytNativeSourceSiteV399 *s=&sites[i];
        if(!shyt_native_import_spec_valid_v398(&s->import) ||
           s->import.expected_next<image_base)return 0;
        uint64_t rel=s->import.expected_next-image_base;
        size_t low=0,high=function_count;
        while(low<high){
            size_t mid=low+(high-low)/2;
            if(functions[mid].offset<s->caller_offset)low=mid+1;
            else high=mid;
        }
        if(low>=function_count ||
           functions[low].offset!=s->caller_offset ||
           rel<=s->caller_offset ||
           rel-s->caller_offset>=functions[low].size)return 0;
        for(size_t j=0;j<i;j++) {
            if(sites[j].caller_offset==s->caller_offset &&
               sites[j].import.expected_next==s->import.expected_next)
                return 0;
            if(sites[j].import.guest_target==s->import.guest_target &&
               (sites[j].import.service!=s->import.service ||
                sites[j].import.recover_code!=s->import.recover_code ||
                sites[j].import.constant!=s->import.constant))return 0;
            if(sites[j].import.guest_target==s->import.guest_target &&
               sites[j].import.expected_next==s->import.expected_next)
                return 0;
        }
    }
    if(!shyt_native_scaled_init_v398(router,owner,site_count))return 0;
    for(size_t i=0;i<site_count;i++) {
        if(!shyt_native_scaled_add_v398(router,&sites[i].import)) {
            /* Not published: fail atomically if V398 unexpectedly
             * refuses a validated entry, no leaked setup allocation. */
            free(router->sites);
            memset(router,0,sizeof(*router));
            return 0;
        }
    }
    if(!shyt_native_scaled_seal_v398(router)){
        free(router->sites);
        memset(router,0,sizeof(*router));
        return 0;
    }
    return router->count==site_count;
}
