/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_guest_vm_v385.h"
#include <stdatomic.h>
#include <stdint.h>
#include <string.h>
_Static_assert(sizeof(void*)==8, "native guest VM requires a 64-bit host");
_Static_assert(sizeof(_Atomic(uint64_t))==8, "atomic guest words must be 8 bytes");

int shyt_guest_vm_init_v385(ShytGuestVmV385 *vm,
                             ShytNativeStackV383 *stack) {
    if (!vm || vm->ready || vm->stack || !stack || stack->ready!=1 ||
        !stack->backing || !stack->word_count) return 0;
    vm->stack=stack;
    vm->ready=1;
    return 1;
}
int shyt_guest_vm_pin_v385(ShytGuestVmV385 *vm,
                            ShytGuestVmLeaseV385 *lease) {
    if (!vm || vm->ready!=1 || !vm->stack || !lease ||
        lease->active || lease->vm ||
        !shyt_native_stack_pin_v383(vm->stack)) return 0;
    lease->vm=vm;
    lease->active=1;
    return 1;
}
int shyt_guest_vm_unpin_v385(ShytGuestVmLeaseV385 *lease) {
    if (!lease || lease->active!=1 || !lease->vm ||
        !shyt_native_stack_unpin_v383(lease->vm->stack)) return 0;
    memset(lease,0,sizeof(*lease));
    return 1;
}
static int locate(const ShytGuestVmLeaseV385 *lease,uint64_t addr,
                  size_t bytes,size_t *index,unsigned *shift) {
    const ShytNativeStackV383 *stack;
    uint64_t delta;
    if (!lease || lease->active!=1 || !lease->vm ||
        lease->vm->ready!=1 || !index || !shift) return 0;
    stack=lease->vm->stack;
    if (!stack || stack->ready!=1 || !stack->backing ||
        !stack->word_count || addr<stack->guest_base ||
        (bytes!=1 && bytes!=2 && bytes!=4 && bytes!=8)) return 0;
    delta=addr-stack->guest_base; /* no subtraction overflow */
    if (delta/8u>=stack->word_count ||
        (delta&7u)+bytes>8u) return 0;
    *index=(size_t)(delta/8u);
    *shift=(unsigned)(delta&7u)*8u;
    return 1;
}
int shyt_guest_vm_probe_v385(const ShytGuestVmLeaseV385 *lease,
                             uint64_t addr,size_t bytes) {
    size_t index=0;unsigned shift=0;
    return locate(lease,addr,bytes,&index,&shift);
}
int shyt_guest_vm_write_v385(const ShytGuestVmLeaseV385 *lease,
                             uint64_t addr,size_t bytes,uint64_t value) {
    size_t index;unsigned shift;
    if (!locate(lease,addr,bytes,&index,&shift)) return 0;
    _Atomic(uint64_t) *slot=&lease->vm->stack->backing[index];
    if (bytes==8) {
        atomic_store_explicit(slot,value,memory_order_release);
        return 1;
    }
    uint64_t bits=(UINT64_C(1) << (bytes*8u))-1u;
    uint64_t mask=bits<<shift;
    uint64_t old=atomic_load_explicit(slot,memory_order_acquire);
    for (;;) {
        uint64_t next=(old&~mask)|((value&bits)<<shift);
        if (atomic_compare_exchange_weak_explicit(
                slot,&old,next,memory_order_acq_rel,
                memory_order_acquire)) return 1;
    }
}
int shyt_guest_vm_read_v385(const ShytGuestVmLeaseV385 *lease,
                            uint64_t addr,size_t bytes,uint64_t *value) {
    size_t index;unsigned shift;
    if (!value || !locate(lease,addr,bytes,&index,&shift)) return 0;
    uint64_t word=atomic_load_explicit(
        &lease->vm->stack->backing[index],memory_order_acquire);
    if (bytes!=8)word=(word>>shift)&((UINT64_C(1)<<(bytes*8u))-1u);
    *value=word;
    return 1;
}
int shyt_guest_vm_stack_write_v385(void *context,uint64_t addr,uint64_t value){
    ShytGuestVmV385 *vm=(ShytGuestVmV385 *)context;
    ShytGuestVmLeaseV385 lease={0};
    if (!shyt_guest_vm_pin_v385(vm,&lease))return 0;
    int success=shyt_guest_vm_write_v385(&lease,addr,8,value);
    if (!shyt_guest_vm_unpin_v385(&lease))return 0;
    return success;
}
