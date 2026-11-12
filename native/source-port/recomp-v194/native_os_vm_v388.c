/* SPDX-License-Identifier: GPL-2.0-or-later */
#if !defined(_WIN32) && !defined(_DEFAULT_SOURCE)
#define _DEFAULT_SOURCE 1
#endif
#include "native_os_vm_v388.h"
#include <limits.h>
#include <stdint.h>
#include <stdatomic.h>
#include <string.h>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN 1
#include <windows.h>
#else
#include <sys/mman.h>
#include <unistd.h>
#if !defined(MAP_ANONYMOUS) && defined(MAP_ANON)
#define MAP_ANONYMOUS MAP_ANON
#endif
#endif
_Static_assert(sizeof(void*)==8,"V388 is 64-bit native only");
_Static_assert(sizeof(_Atomic(uint64_t))==8,"V388 atomic word must be 8 bytes");

static size_t os_page_size(void){
#if defined(_WIN32)
    SYSTEM_INFO info;
    GetSystemInfo(&info);
    return (size_t)info.dwPageSize;
#else
    long p=sysconf(_SC_PAGESIZE);
    return p>0?(size_t)p:0;
#endif
}
static void *os_map_rw(size_t bytes){
#if defined(_WIN32)
    return VirtualAlloc(NULL,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
#else
    void *p=mmap(NULL,bytes,PROT_READ|PROT_WRITE,
                  MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    return p==MAP_FAILED?NULL:p;
#endif
}
static int os_protect(size_t bytes,void *p,int writable){
#if defined(_WIN32)
    DWORD previous=0;
    return VirtualProtect(p,bytes,writable?PAGE_READWRITE:PAGE_READONLY,
                          &previous)!=0;
#else
    return mprotect(p,bytes,PROT_READ|(writable?PROT_WRITE:0))==0;
#endif
}
static int os_unmap(void *p,size_t bytes){
#if defined(_WIN32)
    (void)bytes;
    return VirtualFree(p,0,MEM_RELEASE)!=0;
#else
    return munmap(p,bytes)==0;
#endif
}
int shyt_native_os_vm_init_v388(ShytNativeOsVmV388 *o){
    size_t p;
    if(!o || o->initialized || o->sealed || o->released ||
       o->allocation_count || o->vm.region_count)return 0;
    p=os_page_size();
    if(p<sizeof(_Atomic(uint64_t)) || (p&(p-1u)))return 0;
    o->page_size=p;
    o->initialized=1;
    return 1;
}
int shyt_native_os_vm_add_v388(ShytNativeOsVmV388 *o,
    uint64_t guest_base,size_t word_count,unsigned perms) {
    size_t bytes,rounded;
    _Atomic(uint64_t) *words;
    if(!o || o->initialized!=1 || o->sealed || o->released ||
       o->allocation_count>=SHYT_V386_MAX_REGIONS ||
       !o->page_size || !word_count ||
       word_count>SHYT_V386_MAX_WORDS ||
       word_count>SIZE_MAX/sizeof(_Atomic(uint64_t)))return 0;
    bytes=word_count*sizeof(_Atomic(uint64_t));
    if(bytes>SIZE_MAX-(o->page_size-1u))return 0;
    rounded=(bytes+o->page_size-1u)&~(o->page_size-1u);
    words=(_Atomic(uint64_t)*)os_map_rw(rounded);
    if(!words)return 0;
    for(size_t i=0;i<word_count;i++)atomic_init(&words[i],0);
    if(!shyt_native_vm_add_region_v386(
            &o->vm,guest_base,words,word_count,perms)) {
        (void)os_unmap(words,rounded);
        return 0;
    }
    o->allocations[o->allocation_count++]=(ShytNativeOsAllocationV388){
        words,guest_base,word_count,rounded,perms,1
    };
    return 1;
}
int shyt_native_os_vm_seal_v388(ShytNativeOsVmV388 *o) {
    if(!o || o->initialized!=1 || o->sealed || o->released ||
       !o->allocation_count)return 0;
    /* Protect BEFORE exposing the sealed VM to worker threads.
     * All resident words have already been initialized atomically. */
    for(size_t i=0;i<o->allocation_count;i++){
        ShytNativeOsAllocationV388 *a=&o->allocations[i];
        if(!a->live || !os_protect(a->reserved_bytes,a->words,
                (a->permissions&SHYT_V386_WRITE)!=0)) {
            for(size_t j=0;j<i;j++){
                ShytNativeOsAllocationV388 *old=&o->allocations[j];
                (void)os_protect(old->reserved_bytes,old->words,1);
            }
            return 0;
        }
    }
    if(!shyt_native_vm_seal_v386(&o->vm))return 0;
    o->sealed=1;
    return 1;
}
ShytNativeVmV386 *shyt_native_os_vm_mapping_v388(ShytNativeOsVmV388 *o){
    return o && o->sealed==1 && !o->released?&o->vm:NULL;
}
static uint64_t byte_mask(size_t bytes) {
    return bytes==8?UINT64_MAX:(UINT64_C(1)<<(bytes*8u))-1u;
}
/* C11 atomic CAS for a partial 64-bit word, never mixes plain writes. */
static void replace_bytes(_Atomic(uint64_t) *word,
                          unsigned offset,size_t count,uint64_t value) {
    if(count==8){
        atomic_store_explicit(word,value,memory_order_release);
        return;
    }
    const uint64_t mask=byte_mask(count)<<(offset*8u);
    uint64_t old=atomic_load_explicit(word,memory_order_acquire);
    for(;;){
        const uint64_t next=(old&~mask)|
                             ((value&byte_mask(count))<<(offset*8u));
        if(atomic_compare_exchange_weak_explicit(
               word,&old,next,memory_order_acq_rel,memory_order_acquire))
            return;
    }
}
static int locate(const ShytNativeOsVmV388 *o,
                  const ShytNativeVmLeaseV386 *lease,uint64_t addr,
                  size_t width,unsigned required,
                  _Atomic(uint64_t) **words,size_t *index,
                  unsigned *byte_offset) {
    if(!o || o->sealed!=1 || o->released || !lease ||
       lease->live!=1 || lease->vm!=&o->vm ||
       !words || !index || !byte_offset ||
       (width!=1 && width!=2 && width!=4 && width!=8) ||
       !required || (required&~7u))return 0;
    size_t low=0,high=o->vm.region_count;
    while(low<high){
        size_t mid=low+(high-low)/2u;
        if(o->vm.regions[mid].guest_base<=addr)low=mid+1u;
        else high=mid;
    }
    if(!low)return 0;
    const ShytNativeRegionV386 *r=&o->vm.regions[low-1u];
    uint64_t offset=addr-r->guest_base;
    if((r->permissions&required)!=required ||
       offset/8u>=r->word_count ||
       (uint64_t)width>(uint64_t)r->word_count*8u-offset)return 0;
    *words=r->words;
    *index=(size_t)(offset/8u);
    *byte_offset=(unsigned)(offset&7u);
    return 1;
}
int shyt_native_os_vm_probe_v388(const ShytNativeOsVmV388 *o,
    const ShytNativeVmLeaseV386 *lease,uint64_t addr,size_t width,
    unsigned needed){
    _Atomic(uint64_t)*w=NULL;size_t i=0;unsigned shift=0;
    return locate(o,lease,addr,width,needed,&w,&i,&shift);
}
int shyt_native_os_vm_read_v388(const ShytNativeOsVmV388 *o,
    const ShytNativeVmLeaseV386 *lease,uint64_t addr,
    size_t width,uint64_t *value) {
    _Atomic(uint64_t)*w=NULL;size_t i=0;unsigned offset=0;
    if(!value || !locate(o,lease,addr,width,SHYT_V386_READ,
                          &w,&i,&offset))return 0;
    uint64_t first=atomic_load_explicit(&w[i],memory_order_acquire);
    uint64_t result=first>>(offset*8u);
    if((size_t)offset+width>8u){
        const size_t low=8u-offset;
        uint64_t high=atomic_load_explicit(&w[i+1u],memory_order_acquire);
        result=(result&byte_mask(low))|
               ((high&byte_mask(width-low))<<(low*8u));
    }else result&=byte_mask(width);
    *value=result;
    return 1;
}
int shyt_native_os_vm_write_v388(const ShytNativeOsVmV388 *o,
    const ShytNativeVmLeaseV386 *lease,uint64_t addr,
    size_t width,uint64_t value) {
    _Atomic(uint64_t)*w=NULL;size_t i=0;unsigned offset=0;
    if(!locate(o,lease,addr,width,SHYT_V386_WRITE,
               &w,&i,&offset))return 0;
    if((size_t)offset+width>8u){
        const size_t low=8u-offset;
        replace_bytes(&w[i],offset,low,value);
        replace_bytes(&w[i+1u],0,width-low,value>>(low*8u));
        /* Two separate atomic updates, NOT transactionally atomic. */
    }else replace_bytes(&w[i],offset,width,value);
    return 1;
}
int shyt_native_os_vm_stack_write_v388(void *ctx,
    uint64_t address,uint64_t value) {
    ShytNativeOsVmV388 *o=(ShytNativeOsVmV388*)ctx;
    ShytNativeVmLeaseV386 lease={0};
    if(!o || !shyt_native_vm_pin_v386(&o->vm,&lease))return 0;
    int ok=shyt_native_os_vm_write_v388(o,&lease,address,8,value);
    if(!shyt_native_vm_unpin_v386(&lease))return 0;
    return ok;
}
int shyt_native_os_vm_close_v388(ShytNativeOsVmV388 *o){
    return o && o->sealed==1 && !o->released &&
           shyt_native_vm_close_v386(&o->vm);
}
int shyt_native_os_vm_release_v388(ShytNativeOsVmV388 *o,
                                   int joined) {
    if(!o || o->sealed!=1 || o->released || joined!=1 ||
       !shyt_native_vm_quiescent_v386(&o->vm))return 0;
    for(size_t i=0;i<o->allocation_count;i++){
        ShytNativeOsAllocationV388 *a=&o->allocations[i];
        if(!a->live || !os_unmap(a->words,a->reserved_bytes))return 0;
        a->live=0;
        a->words=NULL;
        /* V386 remains CLOSED and can never issue a new pin. */
    }
    for(size_t i=0;i<o->vm.region_count;i++)
        o->vm.regions[i].words=NULL;
    o->released=1;
    return 1;
}
