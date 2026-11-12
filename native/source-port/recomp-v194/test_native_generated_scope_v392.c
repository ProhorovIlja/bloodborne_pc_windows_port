/* SPDX-License-Identifier: GPL-2.0-or-later
 * V391: real pinned bbrecomp-generated x86 LOCK CMPXCHG, MOVDQU and
 * VMOVDQU from an invented build-time ELF. Execute through V390 VM.
 * Not original retail Bloodborne or complete x86-64 memory semantics.
 */
#include "recomp/rc.h"
#include "native_generated_memory_calls_v390.h"
#include "native_generated_scope_v392.h"
#include "native_os_vm_reconfigure_v389.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if !defined(_WIN32)
#include <signal.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V392_ASSERT_LINE_%d\n",__LINE__);return 1;}}while(0)
extern const RcFunction *bb_recomp_init(const RcApi*,size_t*);
static uint64_t forbidden_step(BbCpu *cpu){
    (void)cpu;abort(); /* never execute a guest interpreter */
}
static void forbidden_call(BbCpu *cpu,uint64_t a,uint64_t b){
    (void)cpu;(void)a;(void)b;abort();
}
static void forbidden_tail(BbCpu *cpu){(void)cpu;abort();}
static void forbidden_bail(BbCpu *cpu,uint64_t s){
    (void)cpu;(void)s;abort();
}
static const uint64_t db=UINT64_C(0x600000000000);
static const uint64_t spbase=UINT64_C(0x700000000000);
static const uint64_t robase=UINT64_C(0x500000000000);
static const uint64_t resume=UINT64_C(0xABCDEF0123456789);
static const RcFunction *fn;
static ShytNativeOsVmV388 *owner;
static int write_guest(uint64_t addr,int bytes,uint64_t value){
    ShytNativeVmLeaseV386 l={0};
    if(!shyt_native_vm_pin_v386(&owner->vm,&l))return 0;
    int ok=shyt_native_os_vm_write_v388(owner,&l,addr,(size_t)bytes,value);
    if(!shyt_native_vm_unpin_v386(&l))abort();
    return ok;
}
static int read_guest(uint64_t addr,int bytes,uint64_t *out){
    ShytNativeVmLeaseV386 l={0};
    if(!shyt_native_vm_pin_v386(&owner->vm,&l))return 0;
    int ok=shyt_native_os_vm_read_v388(owner,&l,addr,(size_t)bytes,out);
    if(!shyt_native_vm_unpin_v386(&l))abort();
    return ok;
}
/* Genuine pinned original bbrecomp RcFn under the V392 host scope.
 * The normal return path owns/releases a V390 guest memory lease.
 */
static int execute(unsigned idx,BbCpu *cpu){
    if(idx>=5 || !fn[idx].fn || !cpu ||
       !write_guest(spbase+16*8,8,resume))return 0;
    cpu->r[RSP]=spbase+16*8;
    cpu->mxcsr=0x1f80;
    if(!shyt_generated_call_v392(owner,fn[idx].fn,cpu,NULL,NULL))return 0;
    return cpu->r[RSP]==spbase+17*8 && cpu->rip==resume &&
           !shyt_generated_active_v390();
}
#if !defined(_WIN32)
static int expect_abort(unsigned idx,uint64_t address,uint64_t expected,
                        uint64_t desired) {
    pid_t pid=fork();
    if(pid<0)return 0;
    if(pid==0){
        struct rlimit limit={0,0};
        (void)setrlimit(RLIMIT_CORE,&limit);
        BbCpu cpu={0};
        cpu.r[RDI]=address;
        cpu.r[RAX]=expected;
        cpu.r[RSI]=desired;
        /* Do NOT use execute: it returns only after the actual
         * guest memory CAS or vector operation has succeeded. */
        (void)execute(idx,&cpu);
        _Exit(47);
    }
    int status=0;
    if(waitpid(pid,&status,0)!=pid)return 0;
    return WIFSIGNALED(status) && WTERMSIG(status)==SIGABRT;
}
#endif
/* Callback executes inside a scoped parent VM pin. Its own generated
 * function call borrows EXACTLY that owner, rather than pinning/unpinning
 * a second unrelated VM or letting the original lease escape.
 */
typedef struct NestedPreflightV392 {
    uint64_t previous,replacement;
    unsigned calls;
} NestedPreflightV392;
static int reject_preflight_v392(const BbCpu *cpu,void *unused) {
    (void)cpu;(void)unused;return 0;
}
static int nested_preflight_v392(const BbCpu *cpu,void *context) {
    NestedPreflightV392 *p=(NestedPreflightV392*)context;
    ShytGeneratedScopeV392 nested={0};
    BbCpu inner={0};
    (void)cpu;
    if(!p || !shyt_generated_active_v390() ||
       shyt_generated_owner_v392()!=owner ||
       !shyt_generated_try_store_v390(spbase+16*8,8,resume))
        return 0;
    if(!shyt_generated_scope_begin_v392(&nested,owner) ||
       nested.state!=2u || !shyt_generated_active_v390() ||
       !shyt_generated_scope_end_v392(&nested) ||
       !shyt_generated_active_v390())return 0;
    inner.r[RSP]=spbase+16*8;
    inner.r[RDI]=db;
    inner.r[RAX]=p->previous;
    inner.r[RSI]=p->replacement;
    inner.mxcsr=0x1f80;
    if(!shyt_generated_call_v392(owner,fn[0].fn,&inner,NULL,NULL) ||
       inner.rip!=resume || inner.r[RSP]!=spbase+17*8 ||
       !shyt_generated_active_v390())return 0;
    p->calls++;
    return 1;
}
static int test_all(void){
    ShytNativeOsVmV388 vm={0};
    RcApi api={0};
    size_t count=0;
    uint64_t out=0;
    BbCpu cpu={0};
    static const uint64_t offsets[5]={0x1000,0x1020,0x1040,0x1060,0x1080};
    static const uint64_t sizes[5]={6,5,5,5,5};
    unsigned char initial128[16],initial256[32];
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,db,128,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,spbase,32,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(&vm,robase,16,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    owner=&vm;
    api.version=BB_RECOMP_API_VERSION;
    api.image_base=UINT64_C(0x400000);
    api.step=forbidden_step;
    api.call=forbidden_call;
    api.tail=forbidden_tail;
    api.bail=forbidden_bail;
    fn=bb_recomp_init(&api,&count);
    CHECK(fn && count==5);
    for(size_t i=0;i<count;i++){
        CHECK(fn[i].offset==offsets[i] && fn[i].size==sizes[i] &&
              fn[i].hash && fn[i].fn && fn[i].direct);
        *fn[i].direct=fn[i].fn;
    }
    /* Success LOCK CMPXCHG r/m64,r64, updated once and ZF set. */
    CHECK(write_guest(db,8,UINT64_C(0x1122334455667788)));
    cpu.r[RDI]=db;
    cpu.r[RAX]=UINT64_C(0x1122334455667788);
    cpu.r[RSI]=UINT64_C(0x9988776655443322);
    CHECK(execute(0,&cpu));
    CHECK(read_guest(db,8,&out) && out==UINT64_C(0x9988776655443322));
    CHECK(cpu.r[RAX]==UINT64_C(0x1122334455667788));
    CHECK((cpu.flags&F_ZF)!=0);
    /* Failed CMPXCHG returns observed memory value in RAX. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RDI]=db;
    cpu.r[RAX]=0xBAD;
    cpu.r[RSI]=0xCAFE;
    CHECK(execute(0,&cpu));
    CHECK(read_guest(db,8,&out)&&out==UINT64_C(0x9988776655443322));
    CHECK(cpu.r[RAX]==UINT64_C(0x9988776655443322));
    CHECK((cpu.flags&F_ZF)==0);
    /* Construct full 128- and 256-bit byte vectors in OS guest backing. */
    for(size_t i=0;i<sizeof initial128;i++)initial128[i]=(unsigned char)(i+1u);
    for(size_t i=0;i<sizeof initial256;i++)initial256[i]=(unsigned char)(0x80u+i);
    for(unsigned i=0;i<16;i+=8){
        uint64_t word=0;memcpy(&word,initial128+i,8);
        CHECK(write_guest(db+64u+i,8,word));
    }
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RDI]=db+64;
    CHECK(execute(1,&cpu));
    CHECK(memcmp(cpu.v[0].b,initial128,16)==0);
    /* Store an actual generated vector source register to guest memory. */
    memset(&cpu,0,sizeof(cpu));
    memcpy(cpu.v[0].b,initial128,16);
    cpu.r[RDI]=db+128;
    CHECK(execute(2,&cpu));
    for(unsigned i=0;i<16;i+=8){
        uint64_t expected=0;
        memcpy(&expected,initial128+i,8);
        CHECK(read_guest(db+128u+i,8,&out)&&out==expected);
    }
    /* AVX YMM register high half must be copied, not dropped. */
    for(unsigned i=0;i<32;i+=8){
        uint64_t word=0;memcpy(&word,initial256+i,8);
        CHECK(write_guest(db+192u+i,8,word));
    }
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RDI]=db+192;
    CHECK(execute(3,&cpu));
    CHECK(memcmp(cpu.v[0].b,initial256,32)==0);
    memset(&cpu,0,sizeof(cpu));
    memcpy(cpu.v[0].b,initial256,32);
    cpu.r[RDI]=db+256;
    CHECK(execute(4,&cpu));
    for(unsigned i=0;i<32;i+=8){
        uint64_t expected=0;
        memcpy(&expected,initial256+i,8);
        CHECK(read_guest(db+256u+i,8,&out)&&out==expected);
    }
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_remap_v389(&vm,db,1));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    CHECK(read_guest(db,8,&out)&&out==UINT64_C(0x9988776655443322));
    /* Actual emitted generated LOCK CAS works after OS page remap. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RDI]=db;
    cpu.r[RAX]=UINT64_C(0x9988776655443322);
    cpu.r[RSI]=UINT64_C(0xA1A2A3A4A5A6A7A8);
    CHECK(execute(0,&cpu));
    CHECK(read_guest(db,8,&out)&&out==UINT64_C(0xA1A2A3A4A5A6A7A8));
    /* Other threads cannot remap while generated AOT lease is held. */
    CHECK(shyt_generated_enter_v390(&vm));
    CHECK(!shyt_native_os_vm_pause_v389(&vm));
    CHECK(!shyt_generated_try_store_v390(robase,8,0xDEAD));
    CHECK(!shyt_generated_try_probe_v390(
        db+128*8-16,32,SHYT_V386_READ));
    CHECK(shyt_generated_leave_v390());
#if !defined(_WIN32)
    /* Actual original generator's LOCK CAS must fail closed, not silently
     * break x86 atomicity across two uint64 guest backing words. */
    CHECK(expect_abort(0,db+7,0,1));
    CHECK(expect_abort(0,robase,0,1));
    CHECK(expect_abort(2,robase,0,0));
    CHECK(expect_abort(3,db+128*8-16,0,0));
#endif
    /* V392: normal refusal releases the owned pin and never calls RcFn.
     * CPU and guest memory remain unchanged for this const preflight. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RDI]=db;
    cpu.r[RAX]=UINT64_C(0xA1A2A3A4A5A6A7A8);
    cpu.r[RSI]=UINT64_C(0x1111222233334444);
    BbCpu denied=cpu;
    CHECK(!shyt_generated_call_v392(
        owner,fn[0].fn,&cpu,reject_preflight_v392,NULL));
    CHECK(memcmp(&cpu,&denied,sizeof(cpu))==0);
    CHECK(read_guest(db,8,&out) &&
        out==UINT64_C(0xA1A2A3A4A5A6A7A8));
    CHECK(!shyt_generated_active_v390());
    CHECK(!shyt_generated_call_v392(owner,NULL,&cpu,NULL,NULL));
    CHECK(!shyt_generated_call_v392(owner,fn[0].fn,NULL,NULL,NULL));
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(!shyt_generated_call_v392(owner,fn[0].fn,&cpu,NULL,NULL));
    CHECK(shyt_native_os_vm_resume_v389(&vm));

    /* A nested generated RcFn is allowed to BORROW an already pinned
     * same-owner VM, and both inner and outer calls complete safely. */
    NestedPreflightV392 nested_ctx={
        UINT64_C(0xA1A2A3A4A5A6A7A8),
        UINT64_C(0x1111222233334444),0
    };
    CHECK(write_guest(spbase+16*8,8,resume));
    cpu.r[RSP]=spbase+16*8;
    cpu.mxcsr=0x1f80;
    cpu.r[RAX]=nested_ctx.replacement;
    cpu.r[RSI]=UINT64_C(0x5555666677778888);
    CHECK(shyt_generated_call_v392(
        owner,fn[0].fn,&cpu,nested_preflight_v392,&nested_ctx));
    CHECK(nested_ctx.calls==1);
    CHECK(cpu.rip==resume && cpu.r[RSP]==spbase+17*8);
    CHECK(read_guest(db,8,&out) &&
        out==UINT64_C(0x5555666677778888));
    CHECK(!shyt_generated_active_v390());
    /* No stranded pin after nested call: real V389 PAUSE can succeed. */
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    CHECK(!shyt_generated_call_v392(owner,fn[0].fn,
        &cpu,reject_preflight_v392,NULL) && !shyt_generated_active_v390());

    CHECK(shyt_native_os_vm_close_v388(&vm));
    CHECK(!shyt_generated_enter_v390(&vm));
    CHECK(shyt_native_os_vm_release_v388(&vm,1));
    return 0;
}
int main(int argc,char **argv){
    (void)argv;
    if(argc!=1)return 2; /* do not accept runtime PS4 EBOOT/ELF */
    CHECK(!test_all());
    puts("NATIVE_V392_REAL_GENERATED_LOCK_SIMD_SCOPED_NESTED_RETURN_PASS");
    puts("Original-free invented build-time ELF only; NO retail Bloodborne.");
    return 0;
}
