/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_multi_region_vm_v386.h"
#include <stdint.h>
#include <string.h>
#define SHYT_V386_CLOSING UINT32_C(0x80000000)
#define SHYT_V386_COUNT_MASK UINT32_C(0x7fffffff)
_Static_assert(sizeof(void*)==8,"64-bit native host required");
_Static_assert(sizeof(_Atomic(uint64_t))==8,"8-byte C11 atomic backing required");

int shyt_native_vm_add_region_v386(ShytNativeVmV386 *vm,
    uint64_t base, _Atomic(uint64_t) *words, size_t n, unsigned perms) {
    uint64_t end;
    uintptr_t host, host_end;
    size_t where=0;
    if (!vm || vm->sealed || !words ||
        vm->region_count>=SHYT_V386_MAX_REGIONS ||
        atomic_load_explicit(&vm->pins_and_closing,
                             memory_order_acquire)!=0 ||
        !base || (base&7u) || !n || n>SHYT_V386_MAX_WORDS ||
        (perms&~7u) || !perms ||
        ((perms&SHYT_V386_WRITE)&&(perms&SHYT_V386_EXECUTE)) ||
        (uintptr_t)words%_Alignof(_Atomic(uint64_t)) ||
        n>UINT64_MAX/8u || base>UINT64_MAX-(uint64_t)n*8u ||
        n>UINTPTR_MAX/sizeof(*words)) return 0;
    end=base+(uint64_t)n*8u; /* half-open; no overflow */
    host=(uintptr_t)words;
    if (host>UINTPTR_MAX-n*sizeof(*words))return 0;
    host_end=host+n*sizeof(*words);
    for(size_t i=0;i<vm->region_count;i++) {
        const ShytNativeRegionV386 *e=&vm->regions[i];
        uint64_t other_end=e->guest_base+(uint64_t)e->word_count*8u;
        uintptr_t other_host=(uintptr_t)e->words;
        uintptr_t other_host_end=other_host+e->word_count*sizeof(*words);
        if (base<other_end && e->guest_base<end) return 0;
        if (host<other_host_end && other_host<host_end) return 0;
        if (e->guest_base<base)where++;
    }
    for(size_t i=vm->region_count;i>where;i--)
        vm->regions[i]=vm->regions[i-1];
    vm->regions[where]=(ShytNativeRegionV386){base,words,n,(uint8_t)perms};
    vm->region_count++;
    return 1;
}
int shyt_native_vm_seal_v386(ShytNativeVmV386 *vm) {
    if (!vm || vm->sealed || !vm->region_count ||
        atomic_load_explicit(&vm->pins_and_closing,
                             memory_order_acquire)!=0) return 0;
    vm->sealed=1;
    return 1;
}
int shyt_native_vm_pin_v386(ShytNativeVmV386 *vm,
    ShytNativeVmLeaseV386 *lease) {
    uint32_t old;
    if (!vm || vm->sealed!=1 || !lease || lease->live || lease->vm)
        return 0;
    old=atomic_load_explicit(&vm->pins_and_closing,memory_order_acquire);
    for(;;) {
        if ((old&SHYT_V386_CLOSING) ||
            (old&SHYT_V386_COUNT_MASK)==SHYT_V386_COUNT_MASK) return 0;
        if (atomic_compare_exchange_weak_explicit(
                &vm->pins_and_closing,&old,old+1u,
                memory_order_acq_rel,memory_order_acquire))break;
    }
    lease->vm=vm;lease->live=1;
    return 1;
}
int shyt_native_vm_unpin_v386(ShytNativeVmLeaseV386 *lease) {
    uint32_t old;
    ShytNativeVmV386 *vm;
    if (!lease || lease->live!=1 || !lease->vm) return 0;
    vm=lease->vm;
    old=atomic_load_explicit(&vm->pins_and_closing,memory_order_acquire);
    for(;;) {
        if (!(old&SHYT_V386_COUNT_MASK)) return 0;
        if (atomic_compare_exchange_weak_explicit(
                &vm->pins_and_closing,&old,old-1u,
                memory_order_acq_rel,memory_order_acquire))break;
    }
    lease->vm=NULL;lease->live=0;
    return 1;
}
int shyt_native_vm_close_v386(ShytNativeVmV386 *vm) {
    if (!vm || vm->sealed!=1)return 0;
    atomic_fetch_or_explicit(&vm->pins_and_closing,SHYT_V386_CLOSING,
                             memory_order_acq_rel);
    return 1;
}
int shyt_native_vm_quiescent_v386(const ShytNativeVmV386 *vm) {
    return vm && vm->sealed==1 &&
        atomic_load_explicit(&vm->pins_and_closing,memory_order_acquire)==
        SHYT_V386_CLOSING;
}
static int locate(const ShytNativeVmLeaseV386 *lease,uint64_t guest,
                  size_t width,unsigned need,
                  _Atomic(uint64_t) **slot,unsigned *shift) {
    const ShytNativeVmV386 *vm;
    size_t left=0,right;
    if (!lease || lease->live!=1 || !lease->vm ||
        lease->vm->sealed!=1 || !slot || !shift ||
        (width!=1 && width!=2 && width!=4 && width!=8) ||
        !need || (need&~7u)) return 0;
    vm=lease->vm;
    right=vm->region_count;
    while(left<right) {
        size_t mid=left+(right-left)/2;
        if (vm->regions[mid].guest_base<=guest)left=mid+1;
        else right=mid;
    }
    if(!left)return 0;
    const ShytNativeRegionV386 *r=&vm->regions[left-1];
    uint64_t offset=guest-r->guest_base;
    if ((r->permissions&need)!=need ||
        offset/8u>=r->word_count ||
        (offset&7u)+width>8u) return 0;
    *slot=&r->words[(size_t)(offset/8u)];
    *shift=(unsigned)(offset&7u)*8u;
    return 1;
}
int shyt_native_vm_probe_v386(const ShytNativeVmLeaseV386 *lease,
    uint64_t guest,size_t width,unsigned need) {
    _Atomic(uint64_t) *slot=NULL;unsigned shift=0;
    return locate(lease,guest,width,need,&slot,&shift);
}
int shyt_native_vm_read_v386(const ShytNativeVmLeaseV386 *lease,
    uint64_t guest,size_t width,uint64_t *out) {
    _Atomic(uint64_t) *slot=NULL;unsigned shift=0;
    if (!out || !locate(lease,guest,width,SHYT_V386_READ,&slot,&shift))
        return 0;
    uint64_t value=atomic_load_explicit(slot,memory_order_acquire);
    if(width!=8)value=(value>>shift)&((UINT64_C(1)<<(width*8u))-1u);
    *out=value;
    return 1;
}
int shyt_native_vm_write_v386(const ShytNativeVmLeaseV386 *lease,
    uint64_t guest,size_t width,uint64_t value) {
    _Atomic(uint64_t) *slot=NULL;unsigned shift=0;
    if (!locate(lease,guest,width,SHYT_V386_WRITE,&slot,&shift))return 0;
    if(width==8){
        atomic_store_explicit(slot,value,memory_order_release);
        return 1;
    }
    uint64_t bits=(UINT64_C(1)<<(width*8u))-1u;
    uint64_t mask=bits<<shift;
    uint64_t old=atomic_load_explicit(slot,memory_order_acquire);
    for(;;){
        uint64_t next=(old&~mask)|((value&bits)<<shift);
        if(atomic_compare_exchange_weak_explicit(
              slot,&old,next,memory_order_acq_rel,memory_order_acquire))
            return 1;
    }
}
int shyt_native_vm_stack_write_v386(void *context,
    uint64_t address,uint64_t value) {
    ShytNativeVmV386 *vm=(ShytNativeVmV386 *)context;
    ShytNativeVmLeaseV386 lease={0};
    if(!shyt_native_vm_pin_v386(vm,&lease))return 0;
    int ok=shyt_native_vm_write_v386(&lease,address,8,value);
    if(!shyt_native_vm_unpin_v386(&lease))return 0;
    return ok;
}
