/* SPDX-License-Identifier: GPL-2.0-or-later */
#if !defined(_WIN32) && !defined(_DEFAULT_SOURCE)
#define _DEFAULT_SOURCE 1
#endif
#include "native_os_vm_reconfigure_v389.h"
#include <stdint.h>
#include <stdatomic.h>
#include <string.h>
#if defined(_WIN32)
#if !defined(WIN32_LEAN_AND_MEAN)
#define WIN32_LEAN_AND_MEAN 1
#endif
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#if !defined(MAP_ANONYMOUS) && defined(MAP_ANON)
#define MAP_ANONYMOUS MAP_ANON
#endif
#endif

#define SHYT_V389_PAUSE UINT32_C(0x40000000)
_Static_assert(sizeof(void*)==8,"V389 requires 64-bit native pointers");
_Static_assert(sizeof(_Atomic(uint64_t))==8,"V389 requires native 64-bit atomic backing");

static int is_paused(const ShytNativeOsVmV388 *o) {
    return o && o->initialized==1 && o->sealed==1 &&
        !o->released && o->vm.sealed==1 &&
        atomic_load_explicit(&o->vm.pins_and_closing,
                             memory_order_acquire)==SHYT_V389_PAUSE;
}
int shyt_native_os_vm_pause_v389(ShytNativeOsVmV388 *o) {
    uint32_t old=0;
    if (!o || o->initialized!=1 || o->sealed!=1 ||
        o->released || o->vm.sealed!=1) return 0;
    return atomic_compare_exchange_strong_explicit(
        &o->vm.pins_and_closing,&old,SHYT_V389_PAUSE,
        memory_order_acq_rel,memory_order_acquire);
}
int shyt_native_os_vm_resume_v389(ShytNativeOsVmV388 *o) {
    uint32_t old=SHYT_V389_PAUSE;
    if (!o || o->initialized!=1 || o->sealed!=1 || o->released)
        return 0;
    return atomic_compare_exchange_strong_explicit(
        &o->vm.pins_and_closing,&old,0,
        memory_order_acq_rel,memory_order_acquire);
}
static void *page_alloc(size_t bytes){
#if defined(_WIN32)
    return VirtualAlloc(NULL,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
#else
    void *p=mmap(NULL,bytes,PROT_READ|PROT_WRITE,
                 MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    return p==MAP_FAILED?NULL:p;
#endif
}
static int page_protect(void *p,size_t bytes,unsigned perm){
#if defined(_WIN32)
    DWORD previous=0;
    return VirtualProtect(p,bytes,(perm&SHYT_V386_WRITE)?
        PAGE_READWRITE:PAGE_READONLY,&previous)!=0;
#else
    return mprotect(p,bytes,PROT_READ|
        ((perm&SHYT_V386_WRITE)?PROT_WRITE:0))==0;
#endif
}
static int page_release(void *p,size_t bytes){
#if defined(_WIN32)
    (void)bytes;
    return VirtualFree(p,0,MEM_RELEASE)!=0;
#else
    return munmap(p,bytes)==0;
#endif
}
static int permissions_ok(unsigned p){
    return p && !(p&~7u) &&
           !((p&SHYT_V386_WRITE)&&(p&SHYT_V386_EXECUTE));
}
static size_t find_guest(const ShytNativeVmV386 *vm,uint64_t base){
    if(!vm)return SHYT_V386_MAX_REGIONS;
    for(size_t i=0;i<vm->region_count;i++)
        if(vm->regions[i].guest_base==base)return i;
    return SHYT_V386_MAX_REGIONS;
}
static size_t find_owner(const ShytNativeOsVmV388 *o,uint64_t base){
    if(!o)return SHYT_V386_MAX_REGIONS;
    for(size_t i=0;i<o->allocation_count;i++)
        if(o->allocations[i].guest_base==base)return i;
    return SHYT_V386_MAX_REGIONS;
}
static int same_region(const ShytNativeOsVmV388 *o,
                       size_t guest_idx,size_t alloc_idx){
    if(!o || guest_idx>=o->vm.region_count ||
       alloc_idx>=o->allocation_count)return 0;
    const ShytNativeRegionV386 *g=&o->vm.regions[guest_idx];
    const ShytNativeOsAllocationV388 *a=&o->allocations[alloc_idx];
    return a->live && a->words && g->words==a->words &&
        g->guest_base==a->guest_base &&
        g->word_count==a->word_count && g->permissions==a->permissions;
}
int shyt_native_os_vm_reprotect_v389(ShytNativeOsVmV388 *o,
                                     uint64_t base,unsigned perms) {
    size_t gi,ai;
    if(!is_paused(o) || !permissions_ok(perms))return 0;
    gi=find_guest(&o->vm,base);
    ai=find_owner(o,base);
    if(!same_region(o,gi,ai))return 0;
    ShytNativeOsAllocationV388 *a=&o->allocations[ai];
    if(a->permissions==perms)return 1;
    /* The OS change is attempted BEFORE publishing new guest metadata.
     * Any OS failure leaves both original guest/host permissions intact. */
    if(!page_protect(a->words,a->reserved_bytes,perms))return 0;
    o->vm.regions[gi].permissions=(uint8_t)perms;
    a->permissions=perms;
    return 1;
}
int shyt_native_os_vm_remap_v389(ShytNativeOsVmV388 *o,
                                uint64_t base,int preserve) {
    size_t gi,ai;
    _Atomic(uint64_t) *next,*previous;
    if(!is_paused(o) || (preserve!=0 && preserve!=1))return 0;
    gi=find_guest(&o->vm,base);
    ai=find_owner(o,base);
    if(!same_region(o,gi,ai))return 0;
    ShytNativeOsAllocationV388 *a=&o->allocations[ai];
    previous=a->words;
    next=(_Atomic(uint64_t)*)page_alloc(a->reserved_bytes);
    if(!next)return 0;
    for(size_t i=0;i<a->word_count;i++) {
        uint64_t value=preserve?
            atomic_load_explicit(&previous[i],memory_order_acquire):0;
        atomic_init(&next[i],value);
    }
    if(!page_protect(next,a->reserved_bytes,a->permissions)){
        (void)page_release(next,a->reserved_bytes);
        return 0;
    }
    /* No active pins and no new pins are admitted while PAUSED.
     * Keep original allocation in place if OS unmap unexpectedly fails. */
    if(!page_release(previous,a->reserved_bytes)) {
        (void)page_release(next,a->reserved_bytes);
        return 0;
    }
    a->words=next;
    o->vm.regions[gi].words=next;
    return 1;
}
int shyt_native_os_vm_map_v389(ShytNativeOsVmV388 *o,
    uint64_t base,size_t n,unsigned perms) {
    size_t bytes,rounded,slot=0;
    uint64_t end;
    _Atomic(uint64_t) *words;
    if(!is_paused(o) || !permissions_ok(perms) ||
       !base || (base&7u) || !n || n>SHYT_V386_MAX_WORDS ||
       o->allocation_count>=SHYT_V386_MAX_REGIONS ||
       o->vm.region_count>=SHYT_V386_MAX_REGIONS ||
       !o->page_size || n>SIZE_MAX/sizeof(_Atomic(uint64_t)) ||
       n>UINT64_MAX/8u || base>UINT64_MAX-(uint64_t)n*8u)
        return 0;
    end=base+(uint64_t)n*8u;
    bytes=n*sizeof(_Atomic(uint64_t));
    if(bytes>SIZE_MAX-(o->page_size-1u))return 0;
    rounded=(bytes+o->page_size-1u)&~(o->page_size-1u);
    for(size_t i=0;i<o->vm.region_count;i++) {
        const ShytNativeRegionV386 *r=&o->vm.regions[i];
        uint64_t upper=r->guest_base+(uint64_t)r->word_count*8u;
        if(base<upper && r->guest_base<end)return 0;
        if(r->guest_base<base)slot++;
    }
    words=(_Atomic(uint64_t)*)page_alloc(rounded);
    if(!words)return 0;
    for(size_t i=0;i<n;i++)atomic_init(&words[i],0);
    if(!page_protect(words,rounded,perms)){
        (void)page_release(words,rounded);
        return 0;
    }
    for(size_t i=o->vm.region_count;i>slot;i--)
        o->vm.regions[i]=o->vm.regions[i-1];
    o->vm.regions[slot]=(ShytNativeRegionV386){
        base,words,n,(uint8_t)perms
    };
    o->vm.region_count++;
    o->allocations[o->allocation_count++]=(ShytNativeOsAllocationV388){
        words,base,n,rounded,perms,1
    };
    return 1;
}
int shyt_native_os_vm_unmap_v389(ShytNativeOsVmV388 *o,
                                 uint64_t base) {
    size_t gi,ai;
    if(!is_paused(o))return 0;
    gi=find_guest(&o->vm,base);
    ai=find_owner(o,base);
    if(!same_region(o,gi,ai))return 0;
    ShytNativeOsAllocationV388 *a=&o->allocations[ai];
    /* Unmapping before removing metadata is safe: no live leases can
     * dereference any of the region's backing under the PAUSE gate.
     * Failure leaves both the pointer and guest registration unchanged. */
    if(!page_release(a->words,a->reserved_bytes))return 0;
    for(size_t i=gi+1;i<o->vm.region_count;i++)
        o->vm.regions[i-1]=o->vm.regions[i];
    --o->vm.region_count;
    memset(&o->vm.regions[o->vm.region_count],0,
           sizeof(o->vm.regions[0]));
    for(size_t i=ai+1;i<o->allocation_count;i++)
        o->allocations[i-1]=o->allocations[i];
    --o->allocation_count;
    memset(&o->allocations[o->allocation_count],0,
           sizeof(o->allocations[0]));
    return 1;
}
