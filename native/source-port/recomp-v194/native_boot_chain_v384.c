/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_boot_chain_v384.h"
#include "native_aot_table_audit_v257.h"
#include <stdatomic.h>
#include <stdint.h>
#include <string.h>

static int strict_equal(const RcApi *a,const RcApi *b) {
    return a && b && a->version==b->version &&
        a->image_base==b->image_base &&
        a->step==b->step && a->call==b->call &&
        a->tail==b->tail && a->bail==b->bail &&
        a->trace==b->trace;
}
int shyt_native_boot_preflight_v384(
    const ShytAotServicesV245 *s,
    const RcApi *strict, const ShytNativeStackV383 *stack) {
    const RcApi *published;
    uint64_t base,clock_a,clock_b;
    if (!s || !shyt_strict_aot_is_base_v381(strict) || !stack ||
        !stack->ready || !stack->backing || !stack->word_count ||
        atomic_load_explicit(&stack->leases_and_closing,
                             memory_order_acquire)!=0 ||
        s->native_only_finalized_v384 || !s->published_api ||
        s->published_api!=&s->clock.api || !s->functions ||
        !s->function_count ||
        !strict_equal(&s->math.original,strict))
        return 0;
    base=strict->image_base;
    if (s->math.table.image_base!=base ||
        s->clock.targets.image_base!=base ||
        s->math.api.image_base!=base ||
        s->clock.previous.image_base!=base ||
        s->clock.api.image_base!=base)
        return 0;
    published=s->published_api;
    if (!s->math.api.call || !s->clock.previous.call ||
        !published->call || s->math.api.call==strict->call ||
        s->clock.previous.call!=s->math.api.call ||
        published->call==s->math.api.call ||
        published->tail!=strict->tail ||
        published->step!=strict->step ||
        published->bail!=strict->bail ||
        published->version!=BB_RECOMP_API_VERSION ||
        s->math.api.tail!=strict->tail ||
        s->clock.previous.tail!=strict->tail ||
        s->clock.previous.step!=strict->step ||
        s->clock.previous.bail!=strict->bail ||
        !shyt_aot_table_valid_v257(s->functions,s->function_count,base))
        return 0;
    if (!s->clock.targets.read_tsc_offset ||
        !s->clock.targets.get_tsc_frequency_offset ||
        s->clock.targets.read_tsc_offset>UINT64_MAX-base ||
        s->clock.targets.get_tsc_frequency_offset>UINT64_MAX-base)
        return 0;
    clock_a=base+s->clock.targets.read_tsc_offset;
    clock_b=base+s->clock.targets.get_tsc_frequency_offset;
    if (clock_a==clock_b)return 0;
    for (size_t j=0;j<23;++j) {
        const ShytMathImportEntry *e=&s->math.table.entries[j];
        if (!e->fn || !e->offset || e->offset>UINT64_MAX-base)
            return 0;
        uint64_t target=base+e->offset;
        if (target==clock_a || target==clock_b)return 0;
        for (size_t k=0;k<j;++k) {
            if (e->offset==s->math.table.entries[k].offset ||
                e->fn==s->math.table.entries[k].fn)return 0;
        }
    }
    for (size_t i=0;i<s->function_count;i++) {
        uint64_t fn=base+s->functions[i].offset;
        if (fn==clock_a || fn==clock_b) return 0;
        for(size_t j=0;j<23;j++) {
            if (fn==base+s->math.table.entries[j].offset)return 0;
        }
    }
    return 1;
}
int shyt_native_boot_finalize_v384(
    ShytNativeBootChainV384 *chain,ShytAotServicesV245 *services,
    const RcApi *strict,ShytNativeStackV383 *stack,
    ShytStrictAotAttestV381 attester,void *attest_ctx) {
    ShytStrictAotProofV381 proof={0};
    RcApi native={0};
    ShytDirectStatsV259 revoked={0};
    if (!chain || chain->route.entries || chain->route.ready ||
        chain->route.published || chain->published ||
        !attester ||
        !shyt_native_boot_preflight_v384(services,strict,stack))
        return 0;
    if (!shyt_strict_aot_activate_v381(
            strict,services->functions,services->function_count,
            strict->image_base,attester,attest_ctx,&proof))
        return 0;
    if (!shyt_native_aot_prepare_v382(
            &chain->route,strict,services->functions,
            services->function_count,&proof,
            shyt_native_stack_write_v383,stack)) {
        (void)shyt_aot_revoke_direct_slots_v268(
            services->functions,services->function_count,
            strict->image_base,&revoked);
        return 0;
    }
    if (!shyt_native_aot_publish_v382(&chain->route,strict,&native)) {
        (void)shyt_native_aot_dispose_v382(&chain->route);
        (void)shyt_aot_revoke_direct_slots_v268(
            services->functions,services->function_count,
            strict->image_base,&revoked);
        return 0;
    }
    /* All validation and allocation occur BEFORE the irreversible
     * publication. Single-threaded owner bootstrap guarantees that these
     * pointer assignments cannot race generated function executions. */
    services->math.original.call=native.call;
    services->math.original.tail=native.tail;
    services->math.api.tail=native.tail;
    services->clock.previous.tail=native.tail;
    services->clock.api.tail=native.tail;
    services->native_only_finalized_v384=1;
    chain->proof=proof;
    chain->published=1;
    return 1;
}
