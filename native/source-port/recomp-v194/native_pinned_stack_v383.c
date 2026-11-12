/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_pinned_stack_v383.h"
#include <limits.h>
#include <stdint.h>
#define SHYT_V383_CLOSING UINT32_C(0x80000000)
#define SHYT_V383_LEASE_MASK UINT32_C(0x7fffffff)
_Static_assert(sizeof(void*)==8, "native V383 requires 64-bit host");
_Static_assert(sizeof(_Atomic(uint64_t))==8, "native V383 requires 8-byte atomic words");

int shyt_native_stack_init_v383(ShytNativeStackV383 *s,
    _Atomic(uint64_t) *memory, size_t words, uint64_t guest_base) {
    if (!s || !memory || s->ready || s->backing ||
        atomic_load_explicit(&s->leases_and_closing,memory_order_relaxed)!=0 ||
        !words || words>SHYT_V383_MAX_STACK_WORDS ||
        guest_base==0 || (guest_base&7u) ||
        (uintptr_t)memory%_Alignof(_Atomic(uint64_t)) ||
        guest_base>UINT64_MAX-(uint64_t)words*8u) return 0;
    s->backing=memory;
    s->word_count=words;
    s->guest_base=guest_base;
    s->ready=1;
    return 1;
}
int shyt_native_stack_pin_v383(ShytNativeStackV383 *s) {
    uint32_t old;
    if (!s || s->ready!=1) return 0;
    old=atomic_load_explicit(&s->leases_and_closing,memory_order_acquire);
    for (;;) {
        if ((old&SHYT_V383_CLOSING) ||
            (old&SHYT_V383_LEASE_MASK)==SHYT_V383_LEASE_MASK) return 0;
        if (atomic_compare_exchange_weak_explicit(
                &s->leases_and_closing,&old,old+1u,
                memory_order_acq_rel,memory_order_acquire)) return 1;
    }
}
int shyt_native_stack_unpin_v383(ShytNativeStackV383 *s) {
    uint32_t old;
    if (!s || s->ready!=1) return 0;
    old=atomic_load_explicit(&s->leases_and_closing,memory_order_acquire);
    for (;;) {
        if (!(old&SHYT_V383_LEASE_MASK)) return 0;
        if (atomic_compare_exchange_weak_explicit(
                &s->leases_and_closing,&old,old-1u,
                memory_order_acq_rel,memory_order_acquire)) return 1;
    }
}
static int offset_of(const ShytNativeStackV383 *s,
                     uint64_t guest_address,size_t *slot) {
    uint64_t difference;
    if (!s || s->ready!=1 || !s->backing || !slot ||
        guest_address<s->guest_base) return 0;
    difference=guest_address-s->guest_base;
    if ((difference&7u) || difference/8u>=s->word_count) return 0;
    *slot=(size_t)(difference/8u);
    return 1;
}
int shyt_native_stack_write_v383(void *context,uint64_t addr,uint64_t value) {
    ShytNativeStackV383 *s=(ShytNativeStackV383*)context;
    size_t slot=0;
    if (!offset_of(s,addr,&slot) || !shyt_native_stack_pin_v383(s))
        return 0;
    /* Closing may happen after pin: the owner MUST wait for quiescence.
     * The backing address and array length never change while pinned. */
    atomic_store_explicit(&s->backing[slot],value,memory_order_release);
    (void)shyt_native_stack_unpin_v383(s);
    return 1;
}
int shyt_native_stack_read_v383(ShytNativeStackV383 *s,
                                uint64_t addr,uint64_t *out) {
    size_t slot=0;
    uint64_t value;
    if (!out || !offset_of(s,addr,&slot) ||
        !shyt_native_stack_pin_v383(s)) return 0;
    value=atomic_load_explicit(&s->backing[slot],memory_order_acquire);
    (void)shyt_native_stack_unpin_v383(s);
    *out=value;
    return 1;
}
int shyt_native_stack_close_v383(ShytNativeStackV383 *s) {
    if (!s || s->ready!=1) return 0;
    atomic_fetch_or_explicit(&s->leases_and_closing,
        SHYT_V383_CLOSING,memory_order_acq_rel);
    return 1; /* may still have readers; see quiescent */
}
int shyt_native_stack_quiescent_v383(const ShytNativeStackV383 *s) {
    if (!s || s->ready!=1) return 0;
    return atomic_load_explicit(&s->leases_and_closing,
        memory_order_acquire)==SHYT_V383_CLOSING;
}
