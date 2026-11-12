/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V397: seven real pinned-generated invented RcFns, including
 * TWO distinct CALL RAX functions, safely share ONE import target but
 * must keep separately attested continuation RIP authorization.
 * Invalid pairs fail without guest memory mutation or translator.
 * NOT original Bloodborne 1.09 runtime/engine/import closure.
 */
#include "recomp/rc.h"
#include "native_generated_memory_calls_v390.h"
#include "native_generated_scope_v392.h"
#include "native_host_recovery_v393.h"
#include "native_verified_import_v395.h"
#include "native_shared_import_v397.h"
#include "native_import_closure_v396_generated.h"
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
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V397_ASSERT_LINE_%d\n",__LINE__);return 1;}}while(0)
extern const RcFunction *bb_recomp_init(const RcApi*,size_t*);
static uint64_t forbidden_step(BbCpu *cpu){
    (void)cpu;abort(); /* never execute a guest interpreter */
}
static void real_generated_host_callback_v394(BbCpu *cpu,
                                                uint64_t target,
                                                uint64_t next);
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
static ShytNativeSharedRouterV397 import_router_v397;
static const uint64_t host_target_v394=UINT64_C(0x40009000);
static const uint64_t generated_next_v394=UINT64_C(0x4010a2);
static int host_mode_v394;
static unsigned host_hits_v394;
static unsigned nested_host_recoveries_v394;
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
/* Called through the RcApi.call function pointer INSIDE a genuine
 * pinned bbrecomp-generated 'call rax; ret' function. This is not a
 * handwritten invocation of shyt_generated_raise_v393 from preflight.
 * Mode 1 raises the explicit cooperative checkpoint; Mode 2 triggers
 * another actual emitted 'call rax; ret' via nested V393 scope and
 * recovers the INNER frame while preserving the outer pinned mapping.
 * No raw host pointers to guest memory and no interpreter fallback.
 */
static void real_generated_host_callback_v394(BbCpu *cpu,
                                                uint64_t target,
                                                uint64_t next) {
    const unsigned depth=shyt_generated_recovery_depth_v393();
    if(!cpu || !shyt_generated_active_v390() ||
       shyt_generated_owner_v392()!=owner || !depth)abort();
    ++host_hits_v394;
    if(host_mode_v394==3) {
        /* Actual generated CALL RAX reaches V395 import verifier:
         * unlike V394 tests, unknown targets and mismatched generated
         * return sites must be recovered rather than accepted. */
        shyt_native_shared_dispatch_v397(&import_router_v397,cpu,
                                        target,next);
        return;
    }
    if(target!=host_target_v394 ||
       next!=generated_next_v394)abort();
    if(host_mode_v394==1){
        shyt_generated_raise_v393(91);
    }
    if(host_mode_v394==2) {
        if(depth==2) {
            shyt_generated_raise_v393(97);
        }
        if(depth!=1)abort();
        BbCpu inner={0};
        int recovered=0;
        inner.mxcsr=0x1f80;
        inner.r[RAX]=host_target_v394;
        inner.r[RSP]=spbase+8u*8u;
        /* This nested RcFn is the same REAL generated function as
         * the outer one. Its lease is borrowed, not unpinned. */
        if(shyt_generated_call_recoverable_v393(
               owner,fn[5].fn,&inner,NULL,NULL,&recovered)!=
                   SHYT_V393_RECOVERED || recovered!=97 ||
           !shyt_generated_active_v390() ||
           shyt_generated_recovery_depth_v393()!=1u ||
           shyt_native_os_vm_pause_v389(owner))abort();
        ++nested_host_recoveries_v394;
    }else if(host_mode_v394!=0)abort();
    /* For imported host functions, RcApi.call models normal return:
     * leave guest RSP for the generated RET, expose RIP at next. */
    cpu->r[RAX]=UINT64_C(0xBEEF);
    cpu->rip=next;
}

/* Genuine pinned original bbrecomp RcFn under the V392 host scope.
 * The normal return path owns/releases a V390 guest memory lease.
 */
static int execute(unsigned idx,BbCpu *cpu){
    if(idx>=7 || !fn[idx].fn || !cpu ||
       !write_guest(spbase+16*8,8,resume))return 0;
    cpu->r[RSP]=spbase+16*8;
    cpu->mxcsr=0x1f80;
    if(shyt_generated_call_recoverable_v393(
           owner,fn[idx].fn,cpu,NULL,NULL,NULL)!=SHYT_V393_COMPLETED)return 0;
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
/* V393 recovery is explicitly requested by trusted same-thread host
 * callback. The V393 wrapper, NOT arbitrary POSIX/Win32 faults, owns
 * setjmp and the V390 release on a controlled longjmp to that wrapper.
 */
typedef struct RecoveryCtxV393 {
    int reason;
    unsigned visited;
} RecoveryCtxV393;
static int signal_recovery_v393(const BbCpu *cpu,void *context) {
    RecoveryCtxV393 *r=(RecoveryCtxV393*)context;
    (void)cpu;
    if(!r || !shyt_generated_active_v390() ||
       shyt_generated_owner_v392()!=owner ||
       !shyt_generated_recovery_depth_v393())abort();
    r->visited++;
    shyt_generated_raise_v393(r->reason);
    return 0; /* unreachable */
}
static int nested_recovery_preflight_v393(const BbCpu *cpu,void *context) {
    RecoveryCtxV393 *r=(RecoveryCtxV393*)context;
    BbCpu inner={0};
    int code=0;
    (void)cpu;
    if(!r || shyt_generated_recovery_depth_v393()<1 ||
       shyt_generated_owner_v392()!=owner)return 0;
    inner.r[RDI]=db;
    inner.r[RAX]=r->reason;
    inner.r[RSI]=UINT64_C(0xDADBEEF);
    int status=shyt_generated_call_recoverable_v393(
        owner,fn[0].fn,&inner,signal_recovery_v393,r,&code);
    if(status!=SHYT_V393_RECOVERED || code!=r->reason ||
       !shyt_generated_active_v390() ||
       !shyt_generated_recovery_depth_v393() ||
       shyt_native_os_vm_pause_v389(owner))return 0;
    return 0; /* outer preflight denial; no outer generated function */
}
static int test_all(void){
    ShytNativeOsVmV388 vm={0},other_owner={0};
    RcApi api={0};
    size_t count=0;
    uint64_t out=0;
    BbCpu cpu={0};
    static const uint64_t offsets[7]={0x1000,0x1020,0x1040,0x1060,0x1080,0x10a0,0x10c0};
    static const uint64_t sizes[7]={6,5,5,5,5,3,3};
    unsigned char initial128[16],initial256[32];
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,db,128,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,spbase,32,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(&vm,robase,16,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    owner=&vm;
    /* Only exact pre-registered guest imports. Register intentionally
     * out-of-order to test deterministic target sort, duplicate denial,
     * invalid spec rejection and immutable publication. */
    CHECK(shyt_native_shared_init_v397(&import_router_v397,owner));
    CHECK(SHYT_V396_SITE_COUNT==2);
    CHECK(shyt_v396_sites[0].caller_offset==0x10a0 &&
          shyt_v396_sites[1].caller_offset==0x10c0);
    ShytNativeImportSpecV395 sum_spec={
        UINT64_C(0x40009100),generated_next_v394,
        SHYT_V395_ADD_GUEST_QWORDS,0,0
    };
    ShytNativeImportSpecV395 failure_spec={
        UINT64_C(0x40009200),generated_next_v394,
        SHYT_V395_COOPERATIVE_FAILURE,671,0
    };
    ShytNativeImportSpecV395 constant_spec={
        host_target_v394,generated_next_v394,
        SHYT_V395_RETURN_VALUE,0,UINT64_C(0xBEEF)
    };
    CHECK(shyt_v396_sites[0].import.guest_target==sum_spec.guest_target &&
          shyt_v396_sites[0].import.expected_next==sum_spec.expected_next &&
          shyt_v396_sites[0].import.service==sum_spec.service);
    ShytNativeImportSpecV395 second_site_spec=shyt_v396_sites[1].import;
    CHECK(second_site_spec.guest_target==sum_spec.guest_target &&
          second_site_spec.expected_next==UINT64_C(0x4010c2) &&
          second_site_spec.service==sum_spec.service &&
          second_site_spec.recover_code==sum_spec.recover_code &&
          second_site_spec.constant==sum_spec.constant);
    /* Same target with DIFFERENT approved service ABI must be rejected
     * during V397 publication, not at first runtime invocation. */
    ShytNativeImportSpecV395 conflicting_spec={
        sum_spec.guest_target,UINT64_C(0x4010e2),
        SHYT_V395_RETURN_VALUE,0,UINT64_C(0x99)
    };
    CHECK(!shyt_native_shared_add_v397(&import_router_v397,
                                       &conflicting_spec));
    CHECK(shyt_native_shared_add_v397(&import_router_v397,&failure_spec));
    CHECK(shyt_native_shared_add_v397(&import_router_v397,&sum_spec));
    CHECK(shyt_native_shared_add_v397(&import_router_v397,&constant_spec));
    CHECK(shyt_native_shared_add_v397(&import_router_v397,
                                      &second_site_spec));
    CHECK(!shyt_native_shared_add_v397(&import_router_v397,&sum_spec));
    ShytNativeImportSpecV395 invalid_spec=sum_spec;
    invalid_spec.guest_target=UINT64_C(0x40009300);
    invalid_spec.service=99;
    CHECK(!shyt_native_shared_add_v397(&import_router_v397,&invalid_spec));
    CHECK(shyt_native_shared_seal_v397(&import_router_v397));
    CHECK(import_router_v397.count==4 &&
       import_router_v397.entries[0].guest_target==host_target_v394 &&
       import_router_v397.entries[1].guest_target==sum_spec.guest_target &&
       import_router_v397.entries[1].expected_next==UINT64_C(0x4010a2) &&
       import_router_v397.entries[2].guest_target==sum_spec.guest_target &&
       import_router_v397.entries[2].expected_next==UINT64_C(0x4010c2) &&
       import_router_v397.entries[3].guest_target==failure_spec.guest_target);
    CHECK(!shyt_native_shared_add_v397(&import_router_v397,&invalid_spec));
    CHECK(!shyt_native_shared_seal_v397(&import_router_v397));
    CHECK(!shyt_native_shared_init_v397(&import_router_v397,owner));
    /* Second fully initialized and sealed VM proves nested borrowing
     * cannot silently switch to an unrelated guest address space. */
    CHECK(shyt_native_os_vm_init_v388(&other_owner));
    CHECK(shyt_native_os_vm_add_v388(&other_owner,
        UINT64_C(0x400000000000),8,
        SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_seal_v388(&other_owner));
    api.version=BB_RECOMP_API_VERSION;
    api.image_base=UINT64_C(0x400000);
    api.step=forbidden_step;
    api.call=real_generated_host_callback_v394;
    api.tail=forbidden_tail;
    api.bail=forbidden_bail;
    fn=bb_recomp_init(&api,&count);
    CHECK(fn && count==7);
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
    CHECK(shyt_generated_enter_v390(owner));
    ShytGeneratedScopeV392 alien_scope={0};
    CHECK(!shyt_generated_scope_begin_v392(&alien_scope,&other_owner));
    CHECK(!alien_scope.owner && alien_scope.state==0);
    CHECK(shyt_generated_owner_v392()==owner);
    CHECK(shyt_generated_leave_v390());
    CHECK(shyt_native_os_vm_pause_v389(&other_owner));
    CHECK(shyt_native_os_vm_resume_v389(&other_owner));
    CHECK(shyt_native_os_vm_close_v388(&other_owner));
    CHECK(shyt_native_os_vm_release_v388(&other_owner,1));

    /* Explicit recovery from a V393 host preflight callback MUST
     * release V390's owned lease and leave CPU/guest data unchanged. */
    CHECK(write_guest(db,8,UINT64_C(0x5555666677778888)));
    RecoveryCtxV393 recover={73,0};
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RDI]=db;
    cpu.r[RAX]=UINT64_C(0x5555666677778888);
    cpu.r[RSI]=UINT64_C(0xBAD);
    BbCpu before_recovery=cpu;
    int recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[0].fn,&cpu,signal_recovery_v393,
        &recover,&recovered_code)==SHYT_V393_RECOVERED);
    CHECK(recovered_code==73 && recover.visited==1);
    CHECK(memcmp(&before_recovery,&cpu,sizeof(cpu))==0);
    CHECK(read_guest(db,8,&out) && out==UINT64_C(0x5555666677778888));
    CHECK(!shyt_generated_active_v390());
    CHECK(shyt_generated_recovery_depth_v393()==0);
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));

    /* Nested V393 recovery drops ONLY the inner borrowed frame. Outer
     * recoverable caller can return a controlled preflight denial and
     * then release the final real VM lease. */
    RecoveryCtxV393 inner={79,0};
    recovered_code=-1;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[0].fn,&cpu,nested_recovery_preflight_v393,
        &inner,&recovered_code)==SHYT_V393_DENIED);
    CHECK(inner.visited==1 && recovered_code==0);
    CHECK(!shyt_generated_active_v390());
    CHECK(shyt_generated_recovery_depth_v393()==0);
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));

    /* The normal-return V393 path still executes the ACTUAL pinned
     * bbrecomp function and clears its recovery frame/lease. */
    CHECK(write_guest(spbase+16*8,8,resume));
    cpu.r[RSP]=spbase+16*8;
    cpu.r[RAX]=UINT64_C(0x5555666677778888);
    cpu.r[RSI]=UINT64_C(0x123456789);
    recovered_code=999;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[0].fn,&cpu,NULL,NULL,
        &recovered_code)==SHYT_V393_COMPLETED);
    CHECK(recovered_code==0 && shyt_generated_recovery_depth_v393()==0);
    CHECK(!shyt_generated_active_v390());
    CHECK(read_guest(db,8,&out) && out==UINT64_C(0x123456789));
    CHECK(cpu.rip==resume && cpu.r[RSP]==spbase+17*8);

    /* V394: actual generated x86 CALL RAX emits RcApi.call. A
     * successful host callback returns to the same generated code,
     * which then executes the original guest RET through V390. */
    CHECK(write_guest(spbase+16u*8u,8,resume));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=host_target_v394;
    cpu.r[RSP]=spbase+16u*8u;
    cpu.mxcsr=0x1f80;
    host_mode_v394=0;
    host_hits_v394=0;
    recovered_code=-1;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
            SHYT_V393_COMPLETED);
    CHECK(recovered_code==0 && cpu.r[RAX]==UINT64_C(0xBEEF) &&
        cpu.rip==resume && cpu.r[RSP]==spbase+17u*8u &&
        host_hits_v394==1 && !shyt_generated_active_v390() &&
        shyt_generated_recovery_depth_v393()==0);

    /* Real generated CALLBACK invokes V393 controlled recovery,
     * not the preflight. The function does not execute its guest RET,
     * while V393 still releases the C11 VM owner pin. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=host_target_v394;
    cpu.r[RSP]=spbase+16u*8u;
    cpu.mxcsr=0x1f80;
    host_mode_v394=1;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
            SHYT_V393_RECOVERED);
    CHECK(recovered_code==91 && host_hits_v394==2 &&
        !shyt_generated_active_v390() &&
        shyt_generated_recovery_depth_v393()==0);
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));

    /* Nested real emitted CALL RAX: the inner callback recovers,
     * but outer callback safely continues, retaining its same-owner
     * mapping pin until its actual generated RET has completed. */
    CHECK(write_guest(spbase+16u*8u,8,resume));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=host_target_v394;
    cpu.r[RSP]=spbase+16u*8u;
    cpu.mxcsr=0x1f80;
    host_mode_v394=2;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
            SHYT_V393_COMPLETED);
    CHECK(recovered_code==0 && nested_host_recoveries_v394==1 &&
        host_hits_v394==4 && cpu.rip==resume &&
        cpu.r[RAX]==UINT64_C(0xBEEF) &&
        cpu.r[RSP]==spbase+17u*8u &&
        !shyt_generated_active_v390() &&
        shyt_generated_recovery_depth_v393()==0);
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    /* Only the trust-modeled import was executed; no guest translator. */
    host_mode_v394=0;

    /* V395: REAL generated CALL RAX -> RcApi.call -> sealed guest
     * allowlist -> two guest 64-bit reads and one bounded write.
     * Guest pointers are logical V386 addresses, never host pointers. */
    host_mode_v394=3;
    const uint64_t v395_a=db+384u,v395_b=db+392u,v395_out=db+400u;
    CHECK(write_guest(v395_a,8,UINT64_C(0x1020304050607080)));
    CHECK(write_guest(v395_b,8,UINT64_C(0x0102030405060708)));
    CHECK(write_guest(v395_out,8,UINT64_C(0xAABBCCDD)));
    CHECK(write_guest(spbase+16u*8u,8,resume));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=sum_spec.guest_target;
    cpu.r[RDI]=v395_a;
    cpu.r[RSI]=v395_b;
    cpu.r[RDX]=v395_out;
    cpu.r[RSP]=spbase+16u*8u;
    cpu.mxcsr=0x1f80;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
            SHYT_V393_COMPLETED);
    const uint64_t sum_v395=UINT64_C(0x1122334455667788);
    CHECK(recovered_code==0 && cpu.r[RAX]==sum_v395 &&
          cpu.rip==resume && cpu.r[RSP]==spbase+17u*8u);
    CHECK(read_guest(v395_out,8,&out) && out==sum_v395);
    CHECK(!shyt_generated_active_v390());
    CHECK(shyt_generated_recovery_depth_v393()==0);

    /* Both independently attested generated CALL RAX sources now
     * invoke the SAME native host service/target with distinct RIPs.
     * Its V390 guest read/write still must work from either caller. */
    CHECK(write_guest(v395_out,8,UINT64_C(0xABCD)));
    CHECK(write_guest(spbase+16u*8u,8,resume));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=second_site_spec.guest_target;
    cpu.r[RDI]=v395_a;
    cpu.r[RSI]=v395_b;
    cpu.r[RDX]=v395_out;
    cpu.r[RSP]=spbase+16u*8u;
    cpu.mxcsr=0x1f80;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[6].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_COMPLETED);
    CHECK(recovered_code==0 && cpu.r[RAX]==sum_v395 &&
          cpu.rip==resume && cpu.r[RSP]==spbase+17u*8u &&
          read_guest(v395_out,8,&out) && out==sum_v395 &&
          !shyt_generated_active_v390());
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));

    /* An unknown guest target from the genuine generated function
     * MUST recover with no guest output mutation; no translator. */
    CHECK(write_guest(v395_out,8,UINT64_C(0xDEADCAFE)));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=UINT64_C(0x40009300);
    cpu.r[RDI]=v395_a;
    cpu.r[RSI]=v395_b;
    cpu.r[RDX]=v395_out;
    cpu.r[RSP]=spbase+16u*8u;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_RECOVERED);
    CHECK(recovered_code==SHYT_V395_REC_UNKNOWN &&
          read_guest(v395_out,8,&out) &&
          out==UINT64_C(0xDEADCAFE) &&
          !shyt_generated_active_v390());
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));

    /* A KNOWN target authorized ONLY at 0x4010a2 must still fail
     * from the second real generated source at 0x4010c2. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=failure_spec.guest_target;
    cpu.r[RDI]=v395_a;
    cpu.r[RSI]=v395_b;
    cpu.r[RDX]=v395_out;
    cpu.r[RSP]=spbase+16u*8u;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[6].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_RECOVERED);
    CHECK(recovered_code==SHYT_V395_REC_CONTINUATION &&
          read_guest(v395_out,8,&out) &&
          out==UINT64_C(0xDEADCAFE));
    CHECK(!shyt_generated_active_v390());
    CHECK(shyt_generated_recovery_depth_v393()==0);

    /* Read-only destination, or missing input, is rejected BEFORE
     * the first write and the CPU return-value publication. */
    CHECK(write_guest(spbase+16u*8u,8,resume));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=sum_spec.guest_target;
    cpu.r[RDI]=v395_a;
    cpu.r[RSI]=v395_b;
    cpu.r[RDX]=robase;
    cpu.r[RSP]=spbase+16u*8u;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_RECOVERED);
    CHECK(recovered_code==SHYT_V395_REC_GUEST_PERMISSIONS &&
          read_guest(robase,8,&out) && out==0);
    CHECK(write_guest(v395_out,8,UINT64_C(0xABCDEF55)));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=sum_spec.guest_target;
    cpu.r[RDI]=UINT64_C(0xBAD10000);
    cpu.r[RSI]=v395_b;
    cpu.r[RDX]=v395_out;
    cpu.r[RSP]=spbase+16u*8u;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_RECOVERED);
    CHECK(recovered_code==SHYT_V395_REC_GUEST_PERMISSIONS &&
          read_guest(v395_out,8,&out) &&
          out==UINT64_C(0xABCDEF55));

    /* Registered cooperative failure has an exact reason code and
     * never writes. Pure constant import can return normally. */
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=failure_spec.guest_target;
    cpu.r[RSP]=spbase+16u*8u;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_RECOVERED);
    CHECK(recovered_code==671 && !shyt_generated_active_v390());
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=constant_spec.guest_target;
    cpu.r[RSP]=spbase+16u*8u;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_COMPLETED);
    CHECK(cpu.r[RAX]==UINT64_C(0xBEEF) && recovered_code==0 &&
          cpu.rip==resume && cpu.r[RSP]==spbase+17u*8u);

    /* The same compiled callsite still resolves imports after an OS
     * backing remap, because every import uses V390 logical access. */
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_remap_v389(&vm,db,1));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    CHECK(write_guest(spbase+16u*8u,8,resume));
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RAX]=sum_spec.guest_target;
    cpu.r[RDI]=v395_a;
    cpu.r[RSI]=v395_b;
    cpu.r[RDX]=v395_out;
    cpu.r[RSP]=spbase+16u*8u;
    recovered_code=0;
    CHECK(shyt_generated_call_recoverable_v393(
        owner,fn[5].fn,&cpu,NULL,NULL,&recovered_code)==
             SHYT_V393_COMPLETED);
    CHECK(cpu.r[RAX]==sum_v395 &&
          read_guest(v395_out,8,&out) && out==sum_v395);
    CHECK(!shyt_generated_active_v390());
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    host_mode_v394=0;

    CHECK(shyt_native_os_vm_close_v388(&vm));
    CHECK(!shyt_generated_enter_v390(&vm));
    CHECK(shyt_native_os_vm_release_v388(&vm,1));
    return 0;
}
int main(int argc,char **argv){
    (void)argv;
    if(argc!=1)return 2; /* do not accept runtime PS4 EBOOT/ELF */
    CHECK(!test_all());
    puts("NATIVE_V397_TWO_REAL_GENERATED_SHARED_TARGET_ABI_RETURN_PASS");
    puts("Original-free invented build-time ELF only; NO retail Bloodborne.");
    return 0;
}
