/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V402: execute four genuinely generated native FS/GS TCB
 * functions from the independently audited, source-only, 11-function
 * *second* native object. The unsupported f_1140 (FS:[0x40])
 * interpreter fallback is ABSENT from its actual compiled table,
 * shard, and input x86 ELF. This is NOT original Bloodborne 1.09.
 */
#include "recomp/rc.h"
#include "native_os_vm_v388.h"
#include "native_generated_scope_v392.h"
#include "native_host_recovery_v393.h"
#include "native_generated_memory_calls_v390.h"
#include "native_route_execution_v404.h"
#include "native_only_approved_v402_generated.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do {if(!(x)){fprintf(stderr,"V402_ASSERT_LINE_%d\n",__LINE__);return 1;}}while(0)
extern const RcFunction *bb_recomp_init(const RcApi *api,size_t *count);
static unsigned guest_step_hits;
static uint64_t forbidden_step(BbCpu *cpu) {
    (void)cpu;guest_step_hits++;abort();
}
static void forbidden_call(BbCpu *cpu,uint64_t target,uint64_t next){
    (void)cpu;(void)target;(void)next;abort();
}
static void forbidden_tail(BbCpu *cpu){(void)cpu;abort();}
static void forbidden_bail(BbCpu *cpu,uint64_t entry_rsp){
    (void)cpu;(void)entry_rsp;abort();
}
static const uint64_t stack_base=UINT64_C(0x700000000000);
static const uint64_t return_rip=UINT64_C(0x1234567812345678);

static int guest_write(ShytNativeOsVmV388 *owner,uint64_t addr,uint64_t value){
    ShytNativeVmLeaseV386 lease={0};
    if(!shyt_native_vm_pin_v386(&owner->vm,&lease))return 0;
    int ok=shyt_native_os_vm_write_v388(owner,&lease,addr,8u,value);
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    return ok;
}

static int guest_read(ShytNativeOsVmV388 *owner,uint64_t addr,uint64_t *value){
    ShytNativeVmLeaseV386 lease={0};
    if(!shyt_native_vm_pin_v386(&owner->vm,&lease))return 0;
    int ok=shyt_native_os_vm_read_v388(owner,&lease,addr,8u,value);
    if(!shyt_native_vm_unpin_v386(&lease))abort();
    return ok;
}

static void counterfeit(BbCpu *cpu){ (void)cpu; abort(); }

static int test_memory(ShytNativeExecutionV404 *route,uint64_t data,uint64_t ro){
    const uint64_t stack=stack_base+16u*8u;
    ShytNativeOsVmV388 *vm=route->owner;
    BbCpu cpu={0};
    uint64_t word=0;
    unsigned char pattern[32];
    for(size_t i=0;i<sizeof(pattern);++i)pattern[i]=(unsigned char)(i+1u);
    CHECK(guest_write(vm,stack,return_rip));
    CHECK(guest_write(vm,data,11));
    cpu.r[RSP]=stack;
    cpu.r[RDI]=data;
    cpu.r[RAX]=11;
    cpu.r[RSI]=22;
    CHECK(shyt_native_execution_try_v404(route,0x1000,&cpu)==SHYT_V404_COMPLETED);
    CHECK((cpu.flags & F_ZF) && guest_read(vm,data,&word) && word==22);
    cpu.r[RSP]=stack;
    cpu.r[RAX]=33;
    cpu.r[RSI]=44;
    CHECK(shyt_native_execution_try_v404(route,0x1000,&cpu)==SHYT_V404_COMPLETED);
    CHECK(!(cpu.flags & F_ZF) && cpu.r[RAX]==22);
    CHECK(guest_read(vm,data,&word) && word==22);

    /* Both vector widths exercise unaligned, mapped loads and stores. */
    for(unsigned j=0;j<2u;++j){
        const size_t width=j?32u:16u;
        const uint64_t address=data+3u;
        const uint64_t load=j?0x1060u:0x1020u;
        const uint64_t store=j?0x1080u:0x1040u;
        cpu.r[RSP]=stack;
        cpu.r[RDI]=address;
        memcpy(cpu.v[0].b,pattern,width);
        CHECK(shyt_native_execution_try_v404(route,store,&cpu)==SHYT_V404_COMPLETED);
        for(size_t i=0;i<width;i+=8u){
            uint64_t expect=0;
            memcpy(&expect,pattern+i,8u);
            CHECK(guest_read(vm,address+(uint64_t)i,&word) && word==expect);
        }
        memset(cpu.v[0].b,0,width);
        cpu.r[RSP]=stack;
        CHECK(shyt_native_execution_try_v404(route,load,&cpu)==SHYT_V404_COMPLETED);
        CHECK(memcmp(cpu.v[0].b,pattern,width)==0);
    }
    cpu.r[RSP]=stack;
    cpu.r[RDI]=data+1u;
    CHECK(shyt_native_execution_try_v404(route,0x1000,&cpu)==SHYT_V404_DENIED);
    cpu.r[RDI]=ro;
    CHECK(shyt_native_execution_try_v404(route,0x1040,&cpu)==SHYT_V404_DENIED);
    CHECK(shyt_native_execution_try_v404(route,0x1000,&cpu)==SHYT_V404_DENIED);
    cpu.r[RDI]=data+120u; /* first word valid, remainder out of region */
    CHECK(guest_write(vm,cpu.r[RDI],UINT64_C(0x1234)));
    CHECK(shyt_native_execution_try_v404(route,0x1080,&cpu)==SHYT_V404_DENIED);
    CHECK(shyt_native_execution_try_v404(route,0x1060,&cpu)==SHYT_V404_DENIED);
    CHECK(guest_read(vm,cpu.r[RDI],&word) && word==UINT64_C(0x1234));
    cpu.r[RDI]=stack-1u;
    CHECK(shyt_native_execution_try_v404(route,0x1040,&cpu)==SHYT_V404_DENIED);
    CHECK(guest_read(vm,stack,&word) && word==return_rip);
    cpu.r[RDI]=UINT64_MAX-4u;
    CHECK(shyt_native_execution_try_v404(route,0x1060,&cpu)==SHYT_V404_DENIED);
    CHECK(cpu.r[RSP]==stack && cpu.rip==return_rip);
    CHECK(shyt_generated_enter_v390(vm));
    CHECK(shyt_native_execution_try_v404(route,0x10e0,&cpu)==SHYT_V404_DENIED);
    CHECK(shyt_generated_owner_v392()==vm);
    CHECK(shyt_generated_leave_v390());
    puts("NATIVE_V405_GUARDED_CAS_AND_FOUR_SIMD_ROUTES_PASS");
    return 0;
}

int main(void){
    static const uint64_t native_tcb[4]={UINT64_C(0x10e0),
        UINT64_C(0x1100),UINT64_C(0x1120),UINT64_C(0x1160)};
    ShytNativeOsVmV388 vm={0};
    RcApi api={0};
    size_t count=0;
    CHECK(SHYT_V402_APPROVED_FUNCTION_COUNT==11);
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,stack_base,32,SHYT_V386_READ|SHYT_V386_WRITE));
    const uint64_t data=UINT64_C(0x600000000000);
    const uint64_t ro=UINT64_C(0x500000000000);
    CHECK(shyt_native_os_vm_add_v388(&vm,data,16,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(&vm,ro,16,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_seal_v388(&vm));

    api.version=BB_RECOMP_API_VERSION;
    api.image_base=UINT64_C(0x400000);
    api.step=forbidden_step;
    api.call=forbidden_call;
    api.tail=forbidden_tail;
    api.bail=forbidden_bail;
    const RcFunction *fn=bb_recomp_init(&api,&count);
    CHECK(fn && count==SHYT_V402_APPROVED_FUNCTION_COUNT);
    for(size_t i=0;i<count;i++){
        CHECK(fn[i].offset==shyt_v402_allowed[i].offset &&
              fn[i].size==shyt_v402_allowed[i].size &&
              fn[i].hash==shyt_v402_allowed[i].hash &&
              fn[i].fn && fn[i].direct);
        CHECK(fn[i].offset!=UINT64_C(0x1140));
        *fn[i].direct=fn[i].fn;
    }
    /* V404 rejects mutated source registries before any real generated
     * function can execute; it never promotes every V403 member. */
    ShytNativeExecutionV404 route={0}, rejected_route={0};
    RcFunction forged[SHYT_V404_SYNTHETIC_FUNCTIONS];
    memcpy(forged,fn,sizeof(forged));
    forged[0].hash^=UINT64_C(1);
    CHECK(!shyt_native_execution_bind_v404(&rejected_route,&vm,forged,count));
    memcpy(forged,fn,sizeof(forged));
    forged[0].size++;
    CHECK(!shyt_native_execution_bind_v404(&rejected_route,&vm,forged,count));
    memcpy(forged,fn,sizeof(forged));
    RcFn fake_slot=counterfeit;
    forged[7].fn=counterfeit;
    forged[7].direct=&fake_slot;
    CHECK(!shyt_native_execution_bind_v404(&rejected_route,&vm,forged,count));
    CHECK(!shyt_native_execution_bind_v404(&route,&vm,fn,count-1u));
    CHECK(shyt_native_execution_bind_v404(&route,&vm,fn,count));
    CHECK(!shyt_native_execution_bind_v404(&route,&vm,fn,count));
    BbCpu denied={0};
    denied.r[RSP]=stack_base+16u*8u;
    denied.mxcsr=0x1f80u;
    /* A copied table whose hashes matched at bind time can change
     * afterwards; runtime must revalidate, never execute a stale route. */
    ShytNativeExecutionV404 changed_after_bind={0};
    memcpy(forged,fn,sizeof(forged));
    CHECK(shyt_native_execution_bind_v404(
          &changed_after_bind,&vm,forged,count));
    forged[7].hash^=UINT64_C(1);
    CHECK(shyt_native_execution_try_v404(
          &changed_after_bind,UINT64_C(0x10e0),&denied)==SHYT_V404_DENIED);
    CHECK(!shyt_generated_active_v390());

    CHECK(shyt_native_execution_try_v404(&route,UINT64_C(0x1140),&denied)
          ==SHYT_V404_DENIED);
    CHECK(shyt_native_execution_try_v404(&route,UINT64_C(0x1000),&denied)
          ==SHYT_V404_DENIED);
    CHECK(shyt_native_execution_try_v404(&route,UINT64_C(0x10a0),&denied)
          ==SHYT_V404_DENIED);
    CHECK(shyt_native_execution_try_v404(&route,UINT64_C(0x1161),&denied)
          ==SHYT_V404_DENIED);
    CHECK(shyt_native_execution_try_v404(&route,UINT64_C(0x10e0),&denied)
          ==SHYT_V404_DENIED); /* mapped return word not written yet */
    denied.r[RSP]=stack_base+32u*8u;
    CHECK(shyt_native_execution_try_v404(&route,UINT64_C(0x10e0),&denied)
          ==SHYT_V404_DENIED); /* unmapped guest return stack */
    CHECK(shyt_native_execution_try_v404(&route,UINT64_C(0x10e0),NULL)
          ==SHYT_V404_DENIED);
    for(size_t j=0;j<4;j++){
        size_t idx=7+j;
        CHECK(fn[idx].offset==native_tcb[j]);
        CHECK(guest_write(&vm,stack_base+16u*8u,return_rip));
        BbCpu cpu={0};
        cpu.tcb=UINT64_C(0xCAFE003123456789);
        cpu.r[RSP]=stack_base+16u*8u;
        cpu.r[RAX]=UINT64_C(0x777788889999AAAA);
        cpu.r[RBX]=UINT64_C(0xBBBBCCCCDDDDEEEE);
        cpu.mxcsr=0x1f80u;
        CHECK(shyt_native_execution_try_v404(&route,native_tcb[j],&cpu)
              ==SHYT_V404_COMPLETED);
        CHECK(cpu.rip==return_rip &&
              cpu.r[RSP]==stack_base+17u*8u &&
              !shyt_generated_active_v390() &&
              shyt_generated_recovery_depth_v393()==0);
        if(j<2){
            CHECK(cpu.r[RAX]==cpu.tcb &&
                  cpu.r[RBX]==UINT64_C(0xBBBBCCCCDDDDEEEE));
        }else{
            CHECK(cpu.r[RBX]==cpu.tcb &&
                  cpu.r[RAX]==UINT64_C(0x777788889999AAAA));
        }
    }
    CHECK(test_memory(&route,data,ro)==0);
    CHECK(guest_step_hits==0);
    CHECK(shyt_native_os_vm_close_v388(&vm));
    CHECK(shyt_native_execution_try_v404(
          &route,UINT64_C(0x10e0),&denied)==SHYT_V404_DENIED);
    CHECK(shyt_native_os_vm_release_v388(&vm,1));
    puts("NATIVE_V404_FOUR_REAL_GENERATED_TCB_FUNCTIONS_ADMITTED_AND_EXECUTED_PASS");
    puts("NATIVE_V402_FOUR_REAL_GENERATED_NATIVE_TCB_FUNCTIONS_PASS");
    puts("real_pinned_generated_native_functions=11 interpreter_fallbacks_linked=0");
    return 0;
}
