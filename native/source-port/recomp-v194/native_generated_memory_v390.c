/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_generated_memory_v390.h"
#include <stdatomic.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
typedef struct ShytGeneratedTlsV390 {
    ShytNativeOsVmV388 *owner;
    ShytNativeVmLeaseV386 lease;
} ShytGeneratedTlsV390;
static _Thread_local ShytGeneratedTlsV390 active;
static int valid_size(int size) {
    return size==1||size==2||size==4||size==8;
}
int shyt_generated_enter_v390(ShytNativeOsVmV388 *owner) {
    if(active.owner || active.lease.live || !owner ||
       owner->sealed!=1 || owner->released ||
       !shyt_native_vm_pin_v386(&owner->vm,&active.lease)) return 0;
    active.owner=owner;
    return 1;
}
int shyt_generated_leave_v390(void) {
    if(!active.owner || !active.lease.live ||
       !shyt_native_vm_unpin_v386(&active.lease))return 0;
    active.owner=NULL;
    return 1;
}
int shyt_generated_active_v390(void) {
    return active.owner!=NULL && active.lease.live==1 &&
        active.lease.vm==&active.owner->vm;
}
static int span(uint64_t addr,size_t bytes,unsigned permission) {
    const ShytNativeOsVmV388 *o=active.owner;
    size_t lo=0,hi;
    if(!shyt_generated_active_v390() || !bytes || bytes>32 ||
       addr>UINT64_MAX-bytes || !permission || (permission&~7u))return 0;
    hi=o->vm.region_count;
    while(lo<hi) {
        size_t mid=lo+(hi-lo)/2;
        if(o->vm.regions[mid].guest_base<=addr)lo=mid+1;
        else hi=mid;
    }
    if(!lo)return 0;
    const ShytNativeRegionV386 *r=&o->vm.regions[lo-1];
    uint64_t relative=addr-r->guest_base;
    if((r->permissions&permission)!=permission ||
       relative/8u>=r->word_count ||
       (uint64_t)bytes>(uint64_t)r->word_count*8u-relative)return 0;
    return 1;
}
int shyt_generated_try_probe_v390(uint64_t addr,size_t bytes,
                                  unsigned permission) {
    return span(addr,bytes,permission);
}
int shyt_generated_try_load_v390(uint64_t addr,int size,uint64_t *out) {
    if(!out || !valid_size(size) ||
       !span(addr,(size_t)size,SHYT_V386_READ))return 0;
    return shyt_native_os_vm_read_v388(
        active.owner,&active.lease,addr,(size_t)size,out);
}
int shyt_generated_try_store_v390(uint64_t addr,int size,uint64_t value) {
    if(!valid_size(size) ||
       !span(addr,(size_t)size,SHYT_V386_WRITE))return 0;
    return shyt_native_os_vm_write_v388(
        active.owner,&active.lease,addr,(size_t)size,value);
}
uint64_t shyt_generated_ld_v390(uint64_t addr,int size) {
    uint64_t result=0;
    if(!shyt_generated_try_load_v390(addr,size,&result))abort();
    return result;
}
void shyt_generated_st_v390(uint64_t addr,int size,uint64_t value) {
    if(!shyt_generated_try_store_v390(addr,size,value))abort();
}
int shyt_generated_cas_v390(uint64_t addr,int size,
    uint64_t expected,uint64_t desired,uint64_t *seen) {
    const ShytNativeOsVmV388 *o=active.owner;
    size_t lo=0,hi;
    if(!seen || !valid_size(size) ||
       !span(addr,(size_t)size,SHYT_V386_READ|SHYT_V386_WRITE))abort();
    hi=o->vm.region_count;
    while(lo<hi){
        size_t mid=lo+(hi-lo)/2;
        if(o->vm.regions[mid].guest_base<=addr)lo=mid+1;
        else hi=mid;
    }
    if(!lo)abort();
    const ShytNativeRegionV386 *r=&o->vm.regions[lo-1];
    uint64_t relative=addr-r->guest_base;
    size_t index=(size_t)(relative/8u);
    unsigned shift=(unsigned)(relative&7u)*8u;
    /* x86 LOCK CAS across two 64-bit word buckets CANNOT be
     * represented by one atomic uint64. Refuse rather than emulate
     * an unsafe, non-atomic multiword compare-and-exchange. */
    if((relative&7u)+(unsigned)size>8u)abort();
    uint64_t mask=size==8?UINT64_MAX:
        ((UINT64_C(1) << ((unsigned)size*8u))-1u);
    const uint64_t field=mask<<shift;
    _Atomic(uint64_t)*word=&r->words[index];
    uint64_t old=atomic_load_explicit(word,memory_order_seq_cst);
    for(;;) {
        uint64_t original=(old>>shift)&mask;
        *seen=original;
        if(original!=(expected&mask))return 0;
        const uint64_t replacement=(old&~field)|
                                    ((desired&mask)<<shift);
        if(atomic_compare_exchange_weak_explicit(
              word,&old,replacement,memory_order_seq_cst,
              memory_order_seq_cst))return 1;
    }
}
