/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original-free C11 atomic guest map tests, Linux/Windows/macOS.
 */
#include "native_guest_vm_v385.h"
#include <stdint.h>
#include <stdio.h>
#include <stdatomic.h>
#include <string.h>
#if !defined(_WIN32)
#include <pthread.h>
#endif
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V385_VM_LINE_%d\n",__LINE__);return 1;}}while(0)
#if !defined(_WIN32)
typedef struct VmThreadV385 {
    ShytGuestVmV385 *vm;
    uint64_t addr;
    uint64_t data;
    int pass;
} VmThreadV385;
static void *thread_worker(void *context) {
    VmThreadV385 *w=(VmThreadV385*)context;
    ShytGuestVmLeaseV385 lease={0};
    w->pass=0;
    if (!shyt_guest_vm_pin_v385(w->vm,&lease))return NULL;
    for (int i=0;i<10000;++i)
        if (!shyt_guest_vm_write_v385(&lease,w->addr,1,w->data)) {
            (void)shyt_guest_vm_unpin_v385(&lease);
            return NULL;
        }
    if (!shyt_guest_vm_unpin_v385(&lease))return NULL;
    w->pass=1;
    return NULL;
}
#endif
static int run(void) {
    _Atomic(uint64_t) raw[8];
    ShytNativeStackV383 memory={0};
    ShytGuestVmV385 vm={0},bad={0};
    ShytGuestVmLeaseV385 lease={0},other={0};
    const uint64_t base=UINT64_C(0x0000600000000000);
    uint64_t value=0;
    for(size_t i=0;i<8;i++)atomic_init(&raw[i],0);
    CHECK(!shyt_guest_vm_init_v385(&vm,&memory));
    CHECK(shyt_native_stack_init_v383(&memory,raw,8,base));
    CHECK(!shyt_guest_vm_init_v385(NULL,&memory));
    CHECK(shyt_guest_vm_init_v385(&vm,&memory));
    CHECK(!shyt_guest_vm_init_v385(&vm,&memory));
    CHECK(!shyt_guest_vm_pin_v385(&bad,&lease));
    CHECK(!shyt_guest_vm_pin_v385(&vm,NULL));
    CHECK(shyt_guest_vm_pin_v385(&vm,&lease));
    CHECK(!shyt_guest_vm_pin_v385(&vm,&lease));
    CHECK(!shyt_guest_vm_read_v385(&lease,base,8,NULL));
    CHECK(shyt_guest_vm_write_v385(&lease,base,8,UINT64_C(0x8877665544332211)));
    CHECK(shyt_guest_vm_read_v385(&lease,base,8,&value));
    CHECK(value==UINT64_C(0x8877665544332211));
    CHECK(shyt_guest_vm_read_v385(&lease,base+1,1,&value));
    CHECK(value==0x22);
    CHECK(shyt_guest_vm_read_v385(&lease,base+2,2,&value));
    CHECK(value==0x4433);
    CHECK(shyt_guest_vm_read_v385(&lease,base+4,4,&value));
    CHECK(value==UINT32_C(0x88776655));
    CHECK(shyt_guest_vm_write_v385(&lease,base+1,2,0xABCD));
    CHECK(shyt_guest_vm_read_v385(&lease,base,8,&value));
    CHECK(value==UINT64_C(0x8877665544ABCD11));
    CHECK(shyt_guest_vm_write_v385(&lease,base+1,4,0x11223344));
    CHECK(shyt_guest_vm_read_v385(&lease,base,8,&value));
    CHECK(value==UINT64_C(0x8877661122334411));
    CHECK(!shyt_guest_vm_write_v385(&lease,base+5,4,0xDEAD));
    CHECK(!shyt_guest_vm_write_v385(&lease,base+7,2,0xDEAD));
    CHECK(!shyt_guest_vm_write_v385(&lease,base+1,8,0xBAD));
    CHECK(!shyt_guest_vm_write_v385(&lease,base-1,1,0xBAD));
    CHECK(!shyt_guest_vm_write_v385(&lease,base+8*8,1,0xBAD));
    CHECK(!shyt_guest_vm_write_v385(&lease,UINT64_MAX,8,0xBAD));
    CHECK(!shyt_guest_vm_write_v385(&lease,base,3,0xBAD));
    CHECK(!shyt_guest_vm_read_v385(&lease,base+7,2,&value));
    CHECK(shyt_guest_vm_read_v385(&lease,base,8,&value));
    CHECK(value==UINT64_C(0x8877661122334411));
    CHECK(shyt_guest_vm_probe_v385(&lease,base+7*8,8));
    CHECK(!shyt_guest_vm_probe_v385(&lease,base+7*8+1,8));
    CHECK(!shyt_guest_vm_probe_v385(&lease,base+8*8,1));
    CHECK(shyt_guest_vm_pin_v385(&vm,&other));
    CHECK(shyt_guest_vm_unpin_v385(&other));
    CHECK(!shyt_guest_vm_unpin_v385(&other));
    CHECK(shyt_guest_vm_unpin_v385(&lease));
    CHECK(!shyt_guest_vm_write_v385(&lease,base,8,0xBAD));
#if !defined(_WIN32)
    VmThreadV385 a={&vm,base+16,0x55,0};
    VmThreadV385 b={&vm,base+17,0xAA,0};
    pthread_t t1,t2;
    CHECK(pthread_create(&t1,NULL,thread_worker,&a)==0);
    CHECK(pthread_create(&t2,NULL,thread_worker,&b)==0);
    CHECK(pthread_join(t1,NULL)==0);
    CHECK(pthread_join(t2,NULL)==0);
    CHECK(a.pass && b.pass);
    CHECK(shyt_guest_vm_pin_v385(&vm,&lease));
    CHECK(shyt_guest_vm_read_v385(&lease,base+16,2,&value));
    CHECK(value==0xAA55); /* same 8-byte slot: non-tearing CAS */
    CHECK(shyt_guest_vm_unpin_v385(&lease));
#endif
    CHECK(shyt_guest_vm_stack_write_v385(&vm,base+7*8,0xFF01));
    CHECK(atomic_load(&raw[7])==0xFF01);
    CHECK(!shyt_guest_vm_stack_write_v385(&vm,base+7*8+1,0));
    CHECK(shyt_guest_vm_pin_v385(&vm,&lease));
    CHECK(shyt_native_stack_close_v383(&memory));
    CHECK(!shyt_native_stack_quiescent_v383(&memory));
    CHECK(!shyt_guest_vm_pin_v385(&vm,&other));
    CHECK(!shyt_guest_vm_stack_write_v385(&vm,base,0));
    /* Existing pinned transaction may finish after close, before owner
     * joins workers and frees backing; further new pins are blocked. */
    CHECK(shyt_guest_vm_read_v385(&lease,base,1,&value));
    CHECK(shyt_guest_vm_unpin_v385(&lease));
    CHECK(shyt_native_stack_quiescent_v383(&memory));
    return 0;
}
int main(void) {
    CHECK(!run());
    puts("NATIVE_V385_UNIFIED_VM_ATOMIC_CAS_PIN_CLOSE_PASS");
    return 0;
}
