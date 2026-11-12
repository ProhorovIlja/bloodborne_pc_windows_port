/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_strict_aot_v381.h"
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>

_Static_assert(sizeof(void*)==8, "native strict AOT requires 64-bit host");
_Static_assert(sizeof(RcApi)==56, "pinned RcApi-v4 ABI drift");
_Static_assert(sizeof(RcFunction)==40, "pinned RcFunction-v4 ABI drift");
enum { SHYT_V381_MAX_FUNCTIONS=1000000 };

static uint64_t forbidden_step(BbCpu *cpu) {
    (void)cpu;
    abort(); /* no guest instruction interpreter */
}
static void forbidden_call(BbCpu *cpu, uint64_t target, uint64_t next) {
    (void)cpu;(void)target;(void)next;
    abort(); /* future genuine native indirect dispatcher is required */
}
static void forbidden_tail(BbCpu *cpu) {
    (void)cpu;
    abort();
}
static void forbidden_bail(BbCpu *cpu, uint64_t entry_rsp) {
    (void)cpu;(void)entry_rsp;
    abort();
}
int shyt_strict_aot_base_v381(RcApi *out, uint64_t image_base) {
    RcApi value={0};
    if (!out || !image_base || sizeof(void*)!=8) return 0;
    value.version=BB_RECOMP_API_VERSION;
    value.image_base=image_base;
    value.step=forbidden_step;
    value.call=forbidden_call;
    value.tail=forbidden_tail;
    value.bail=forbidden_bail;
    value.trace=NULL;
    *out=value;
    return 1;
}
int shyt_strict_aot_is_base_v381(const RcApi *api) {
    return api && api->version==BB_RECOMP_API_VERSION &&
           api->image_base!=0 && api->step==forbidden_step &&
           api->call==forbidden_call && api->tail==forbidden_tail &&
           api->bail==forbidden_bail && api->trace==NULL;
}
static int sort_ptrs(const void *a, const void *b) {
    const uintptr_t aa=*(const uintptr_t*)a;
    const uintptr_t bb=*(const uintptr_t*)b;
    return (aa>bb)-(aa<bb);
}
int shyt_strict_aot_activate_v381(
    const RcApi *strict_base,
    const RcFunction *functions, size_t count, uint64_t image_base,
    ShytStrictAotAttestV381 attester, void *ctx,
    ShytStrictAotProofV381 *out) {
    uintptr_t *slots;
    uint64_t previous=0;
    ShytStrictAotProofV381 proof={0};
    if (!shyt_strict_aot_is_base_v381(strict_base) ||
        strict_base->image_base!=image_base ||
        !functions || !out || !attester || !image_base ||
        !count || count>SHYT_V381_MAX_FUNCTIONS ||
        count>SIZE_MAX/sizeof(uintptr_t)) return 0;

    slots=malloc(count*sizeof(*slots));
    if (!slots) return 0;
    for (size_t i=0;i<count;i++) {
        const RcFunction *f=&functions[i];
        uintptr_t slot=(uintptr_t)f->direct;
        if (!f->fn || !slot || slot%_Alignof(RcFn) ||
            /* A previous epoch must not have an active stale direct ptr. */
            *f->direct!=NULL || !f->size ||
            (i && f->offset<=previous) ||
            f->offset>UINT64_MAX-image_base ||
            f->size>UINT64_MAX-(image_base+f->offset)) {
            free(slots);
            return 0;
        }
        previous=f->offset;
        slots[i]=slot;
    }
    qsort(slots,count,sizeof(*slots),sort_ptrs);
    for (size_t i=1;i<count;i++) {
        if (slots[i]==slots[i-1]) {
            free(slots);
            return 0;
        }
    }
    free(slots);

    /* Full table approval, including import stubs, rewritten functions,
     * indirect dispatch and all executable code, MUST be established by
     * owner-only external checks. This table cannot prove coverage. */
    for (size_t i=0;i<count;i++) {
        const RcFunction *f=&functions[i];
        if (!attester(ctx,image_base+f->offset,f->size,f->hash))
            return 0; /* no partial direct activation */
    }
    /* Detect accidental callback mutations before publishing any slot. */
    for (size_t i=0;i<count;i++) {
        if (*functions[i].direct!=NULL) return 0;
    }
    for (size_t i=0;i<count;i++) {
        *functions[i].direct=functions[i].fn;
    }
    proof.functions_attested=count;
    proof.no_guest_fallback_callbacks=1; /* verified strict_base */
    proof.owner_game_startup_proven=0;
    *out=proof;
    return 1;
}
