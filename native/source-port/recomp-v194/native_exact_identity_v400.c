/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_exact_identity_v400.h"
#include <stddef.h>
#include <stdint.h>

int shyt_native_bind_exact_v400(ShytNativeScaledRouterV398 *router,
    ShytNativeOsVmV388 *owner,
    const ShytNativeSourceSiteV399 *sites,size_t site_count,
    size_t independently_attested_site_count,
    const ShytNativeFunctionProofV399 *actual,size_t actual_count,
    const ShytNativeExpectedFunctionV400 *expected,size_t expected_count,
    uint64_t image_base) {
    if(!router || router->owner || router->sites || router->count ||
       router->capacity || router->sealed ||
       !actual || !expected || !actual_count ||
       actual_count!=expected_count || expected_count>100000u ||
       !site_count || site_count!=independently_attested_site_count ||
       site_count>SHYT_V398_MAX_SITES || image_base==0)
        return 0;
    for(size_t i=0;i<expected_count;i++) {
        const ShytNativeExpectedFunctionV400 *e=&expected[i];
        const ShytNativeFunctionProofV399 *f=&actual[i];
        if(!e->size || !e->hash || !f->compiled || !f->direct_slot ||
           f->offset!=e->offset || f->size!=e->size ||
           f->hash!=e->hash ||
           e->offset>UINT64_MAX-image_base ||
           e->size>UINT64_MAX-image_base-e->offset)return 0;
        if(i && (expected[i-1].offset>=e->offset ||
            expected[i-1].size>e->offset-expected[i-1].offset))
            return 0;
    }
    /* From here, keep the whole V399 fail-closed generated CALL source
     * and exact per-import ABI and return RIP checks unchanged. */
    return shyt_native_bind_attested_v399(router,owner,sites,site_count,
        independently_attested_site_count,actual,actual_count,image_base);
}
