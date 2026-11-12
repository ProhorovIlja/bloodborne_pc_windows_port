/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_aot_route_v382.h"
#include "full_cpu_abi_v194.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
_Static_assert(sizeof(void*)==8, "V382 is 64-bit native only");
enum { SHYT_NATIVE_RSP_V382=4, SHYT_NATIVE_MAX_FUNCS_V382=1000000 };
/* One immutable host route per process; only published at single-threaded
 * boot. A second publish cannot replace native code while threads run. */
static _Atomic(ShytNativeAotRouteV382 *) published_route_v382=ATOMIC_VAR_INIT(NULL);

int shyt_native_aot_prepare_v382(
    ShytNativeAotRouteV382 *route,
    const RcApi *strict_base,
    const RcFunction *functions, size_t count,
    const ShytStrictAotProofV381 *proof,
    ShytNativeAotStackWriteV382 store, void *ctx) {
    ShytNativeAotEntryV382 *entries;
    if (!route || route->entries || route->ready || route->published ||
        !shyt_strict_aot_is_base_v381(strict_base) || !functions ||
        !proof || !store || !count || count>SHYT_NATIVE_MAX_FUNCS_V382 ||
        proof->functions_attested!=count ||
        proof->no_guest_fallback_callbacks!=1 ||
        proof->owner_game_startup_proven!=0 ||
        count>SIZE_MAX/sizeof(*entries)) return 0;
    entries=(ShytNativeAotEntryV382*)malloc(count*sizeof(*entries));
    if (!entries) return 0;
    for (size_t i=0;i<count;i++) {
        const RcFunction *fn=&functions[i];
        if (!fn->fn || !fn->direct || *fn->direct!=fn->fn ||
            !fn->size || fn->offset>UINT64_MAX-strict_base->image_base ||
            fn->size>UINT64_MAX-(strict_base->image_base+fn->offset) ||
            (i && fn->offset<=functions[i-1].offset)) {
            free(entries);
            return 0;
        }
        entries[i].address=strict_base->image_base+fn->offset;
        entries[i].function=fn->fn;
    }
    route->entries=entries;
    route->count=count;
    route->image_base=strict_base->image_base;
    route->stack_write=store;
    route->stack_context=ctx;
    route->ready=1;
    return 1;
}
RcFn shyt_native_aot_lookup_v382(const ShytNativeAotRouteV382 *route,
                                 uint64_t address) {
    if (!route || route->ready!=1 || !route->entries ||
        !route->count || address<route->image_base) return NULL;
    size_t low=0, high=route->count;
    while (low<high) {
        size_t mid=low+(high-low)/2;
        const uint64_t current=route->entries[mid].address;
        if (current<address) low=mid+1;
        else high=mid;
    }
    return low<route->count && route->entries[low].address==address ?
           route->entries[low].function : NULL;
}
int shyt_native_aot_try_call_v382(const ShytNativeAotRouteV382 *route,
                                  BbCpu *cpu,uint64_t target,uint64_t next) {
    RcFn fn=shyt_native_aot_lookup_v382(route,target);
    uint64_t old_rsp,new_rsp;
    if (!cpu || !fn || !route->stack_write || !next) return 0;
    old_rsp=cpu->r[SHYT_NATIVE_RSP_V382];
    if (old_rsp<8) return 0;
    new_rsp=old_rsp-8;
    if (new_rsp&7u) return 0; /* diagnostic: guest stack needs 8-byte alignment */
    /* A rejecting callback MUST NOT write: return without CPU changes. */
    if (route->stack_write(route->stack_context,new_rsp,next)!=1)
        return 0;
    cpu->r[SHYT_NATIVE_RSP_V382]=new_rsp;
    cpu->rip=target;
    fn(cpu); /* Native RcFn pops its return address when it completes. */
    return 1;
}
int shyt_native_aot_try_tail_v382(const ShytNativeAotRouteV382 *route,
                                  BbCpu *cpu) {
    RcFn fn;
    if (!cpu) return 0;
    fn=shyt_native_aot_lookup_v382(route,cpu->rip);
    if (!fn) return 0;
    fn(cpu); /* existing return address stays on guest stack */
    return 1;
}
static void published_call_v382(BbCpu *cpu,uint64_t target,uint64_t next) {
    const ShytNativeAotRouteV382 *route=
        atomic_load_explicit(&published_route_v382,memory_order_acquire);
    if (!shyt_native_aot_try_call_v382(route,cpu,target,next)) abort();
}
static void published_tail_v382(BbCpu *cpu) {
    const ShytNativeAotRouteV382 *route=
        atomic_load_explicit(&published_route_v382,memory_order_acquire);
    if (!shyt_native_aot_try_tail_v382(route,cpu)) abort();
}
int shyt_native_aot_publish_v382(ShytNativeAotRouteV382 *route,
                                 const RcApi *strict_base,RcApi *out) {
    ShytNativeAotRouteV382 *expected=NULL;
    RcApi result;
    if (!route || !out || !shyt_strict_aot_is_base_v381(strict_base) ||
        route->ready!=1 || route->published ||
        !route->entries || !route->count ||
        route->image_base!=strict_base->image_base) return 0;
    result=*strict_base; /* leave step/bail traps in place */
    result.call=published_call_v382;
    result.tail=published_tail_v382;
    if (!atomic_compare_exchange_strong_explicit(
            &published_route_v382,&expected,route,
            memory_order_release,memory_order_acquire)) return 0;
    route->published=1;
    *out=result;
    return 1;
}
int shyt_native_aot_dispose_v382(ShytNativeAotRouteV382 *route) {
    if (!route || route->published) return 0;
    free(route->entries);
    memset(route,0,sizeof(*route));
    return 1;
}
