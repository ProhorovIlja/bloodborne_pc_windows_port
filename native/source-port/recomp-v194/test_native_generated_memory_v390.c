/* SPDX-License-Identifier: GPL-2.0-or-later
 * V390: execute ACTUAL upstream bbrecomp generated whole functions
 * from a synthetic invented ELF64 THROUGH a V389 OS-backed guest VM.
 * No original Bloodborne binaries, PS4 code or runtime ELF loader.
 */
#include "recomp/rc.h"
#include "native_generated_memory_calls_v390.h"
#include "native_os_vm_reconfigure_v389.h"
#include "native_strict_aot_v381.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"V390_TEST_LINE_%d\n",__LINE__);return 1;}}while(0)
extern const RcFunction *bb_recomp_init(const RcApi *,size_t *);
static const uint64_t image_base=UINT64_C(0x400000);
static const uint64_t data_base=UINT64_C(0x0000600000000000);
static const uint64_t stack_base=UINT64_C(0x0000700000000000);
static const uint64_t ro_base=UINT64_C(0x0000500000000000);
static int run_native(const RcFunction *f,ShytNativeOsVmV388 *vm,
                      uint64_t rdi,uint64_t rsi,uint64_t rax,
                      uint64_t expected,uint64_t *flags) {
    ShytNativeVmLeaseV386 lease={0};
    uint64_t return_address=UINT64_C(0x123456789ABCDEF0);
    if(!shyt_native_vm_pin_v386(&vm->vm,&lease))return 21;
    if(!shyt_native_os_vm_write_v388(
          vm,&lease,stack_base+16*8,8,return_address)){
        (void)shyt_native_vm_unpin_v386(&lease);return 22;
    }
    if(!shyt_native_vm_unpin_v386(&lease))return 23;
    BbCpu cpu={0};
    cpu.mxcsr=0x1f80;
    cpu.r[RAX]=rax;
    cpu.r[RDI]=rdi;
    cpu.r[RSI]=rsi;
    cpu.r[RSP]=stack_base+16*8;
    if(!shyt_generated_enter_v390(vm))return 24;
    if(!shyt_generated_active_v390())return 25;
    if(shyt_generated_enter_v390(vm))return 26; /* double pin denied */
    f->fn(&cpu);  /* actual ORIGINAL bbrecomp emitted C, not hand-written */
    if(!shyt_generated_leave_v390())return 27;
    if(shyt_generated_active_v390() ||
       shyt_generated_leave_v390())return 28;
    if(flags)*flags=cpu.flags;
    if(cpu.r[RAX]!=expected ||
       cpu.r[RSP]!=stack_base+17*8 ||
       cpu.rip!=return_address)return 29;
    return 0;
}
static int test(void) {
    const uint64_t initial=UINT64_C(0x1122334455667788);
    const uint64_t updated=UINT64_C(0x9988776655443322);
    ShytNativeOsVmV388 vm={0};
    ShytNativeVmLeaseV386 lease={0};
    RcApi strict={0};
    const RcFunction *functions=NULL;
    size_t count=0;
    static const uint64_t offsets[6]={
        0x1000,0x1010,0x1020,0x1030,0x1050,0x1070
    };
    static const uint64_t sizes[6]={4,4,12,7,8,5};
    uint64_t flags0=0,flags1=0,value=0;
    CHECK(shyt_native_os_vm_init_v388(&vm));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,data_base,64,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,stack_base,32,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_add_v388(
        &vm,ro_base,16,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_seal_v388(&vm));
    CHECK(shyt_strict_aot_base_v381(&strict,image_base));
    functions=bb_recomp_init(&strict,&count);
    CHECK(functions && count==6);
    for(size_t i=0;i<count;i++){
        CHECK(functions[i].offset==offsets[i] &&
              functions[i].size==sizes[i] &&
              functions[i].hash && functions[i].fn && functions[i].direct);
        *functions[i].direct=functions[i].fn;
    }
    CHECK(shyt_native_vm_pin_v386(&vm.vm,&lease));
    CHECK(shyt_native_os_vm_write_v388(
        &vm,&lease,data_base,8,initial));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!run_native(&functions[0],&vm,data_base,0,3,initial,NULL));
    CHECK(!run_native(&functions[1],&vm,data_base,updated,51,51,NULL));
    CHECK(shyt_native_vm_pin_v386(&vm.vm,&lease));
    CHECK(shyt_native_os_vm_read_v388(
        &vm,&lease,data_base,8,&value)&&value==updated);
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!run_native(&functions[2],&vm,0,0,19,0,&flags0));
    CHECK(!run_native(&functions[2],&vm,17,0,19,17,&flags1));
    CHECK((flags0&F_ZF)!=0 && (flags1&F_ZF)==0);
    CHECK(!run_native(&functions[3],&vm,data_base,17,3,updated+17,NULL));
    CHECK(!run_native(&functions[4],&vm,0,0,3,
         image_base+0x1090,NULL));
    CHECK(shyt_native_vm_pin_v386(&vm.vm,&lease));
    CHECK(shyt_native_os_vm_write_v388(
        &vm,&lease,data_base+8+1,8,UINT64_C(0xFEDCBA9876543210)));
    CHECK(shyt_native_vm_unpin_v386(&lease));
    CHECK(!run_native(&functions[5],&vm,data_base+8,0,3,
        UINT64_C(0xFEDCBA9876543210),NULL));
    /* V389 changes the real OS page while NO source AOT lease exists.
     * Original generated C uses logical guest memory after remap. */
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_remap_v389(&vm,data_base,1));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    CHECK(!run_native(&functions[0],&vm,data_base,0,0,updated,NULL));
    CHECK(shyt_generated_enter_v390(&vm));
    CHECK(shyt_generated_try_load_v390(data_base,8,&value) &&
          value==updated);
    CHECK(!shyt_generated_try_load_v390(
        UINT64_C(0xBAD0000),8,&value));
    CHECK(!shyt_generated_try_store_v390(ro_base,8,0xBAD));
    CHECK(!shyt_generated_try_store_v390(data_base+64*8-1,2,0xAA));
    CHECK(!shyt_native_os_vm_pause_v389(&vm)); /* active AOT lease */
    /* Test seq_cst CAS, including expected-on-mismatch semantics. */
    CHECK(!shyt_generated_cas_v390(
        data_base,8,0xBAD,UINT64_C(0xFFEEDDCCBBAA9988),&value));
    CHECK(value==updated);
    CHECK(shyt_generated_cas_v390(
        data_base,8,updated,UINT64_C(0xFFEEDDCCBBAA9988),&value));
    CHECK(value==updated);
    CHECK(!shyt_generated_cas_v390(
        data_base,1,0x11,0xFF,&value));
    CHECK(value==0x88);
    CHECK(shyt_generated_cas_v390(
        data_base,1,0x88,0xFE,&value));
    CHECK(value==0x88);
    /* Vector data memory accesses must never dereference guest pointers.
     * Vector helper prescans the entire mapped span before writing. */
    BbVec vector=rc_vld(data_base,16);
    CHECK(vector.b[0]==0xFE);
    rc_vst(data_base+32,16,vector);
    BbVec copied=rc_vld(data_base+32,16);
    CHECK(memcmp(copied.b,vector.b,16)==0);
    CHECK(!shyt_generated_try_probe_v390(
        data_base+64*8-8,16,SHYT_V386_WRITE));
    CHECK(shyt_generated_leave_v390());
    CHECK(!run_native(&functions[0],&vm,data_base,0,0,
         UINT64_C(0xFFEEDDCCBBAA99FE),NULL));
    /* OS page permissions are updated only after all AOT leases exit. */
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_reprotect_v389(&vm,data_base,SHYT_V386_READ));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    CHECK(shyt_generated_enter_v390(&vm));
    CHECK(!shyt_generated_try_store_v390(data_base,8,0xDEAD));
    CHECK(shyt_generated_try_load_v390(data_base,8,&value));
    CHECK(value==UINT64_C(0xFFEEDDCCBBAA99FE));
    CHECK(shyt_generated_leave_v390());
    CHECK(shyt_native_os_vm_pause_v389(&vm));
    CHECK(shyt_native_os_vm_reprotect_v389(
        &vm,data_base,SHYT_V386_READ|SHYT_V386_WRITE));
    CHECK(shyt_native_os_vm_resume_v389(&vm));
    CHECK(shyt_native_os_vm_close_v388(&vm));
    CHECK(!shyt_generated_enter_v390(&vm));
    CHECK(shyt_native_os_vm_release_v388(&vm,1));
    CHECK(vm.released);
    return 0;
}
int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1)return 2; /* Original PS4 EBOOT at runtime forbidden. */
    CHECK(!test());
    puts("NATIVE_V390_ACTUAL_PINNED_GENERATED_C_VM_REMAP_SCALAR_CAS_VECTOR_PASS");
    puts("Invented ELF at BUILD TIME only; NOT original Bloodborne game.");
    return 0;
}
