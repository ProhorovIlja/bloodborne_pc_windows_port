/* Native V201: invoke FULL original bbrecomp-generated function C with indirect
 * register JMP, vtable/pointer-slot JMP and MOV->register JMP. All input
 * bytes are invented. No PS4 ELF/EBOOT or interpreter callbacks at runtime.
 */
#include "recomp/rc.h"
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

extern const RcFunction *bb_recomp_init(const RcApi *, size_t *);
extern RcFn rc_native_find(uint64_t target);
static unsigned unwanted;
static uint64_t deny_step(BbCpu *c) {(void)c;++unwanted;return 0;}
static void deny_call(BbCpu *c,uint64_t t,uint64_t n)
{(void)c;(void)t;(void)n;++unwanted;}
static void deny_tail(BbCpu *c) {(void)c;++unwanted;}
static void deny_bail(BbCpu *c,uint64_t sp)
{(void)c;(void)sp;++unwanted;}
static void deny_trace(uint64_t offset,const uint64_t regs[16],const BbCpu *c)
{(void)offset;(void)regs;(void)c;++unwanted;}
static const RcFunction *table;
static uint64_t image_base;

static int run(unsigned i,uint64_t initial_rax,uint64_t rdi,uint64_t expected,
               uint64_t call_next) {
    if(i>=5 || !table[i].fn) return 4;
    uint64_t guest_stack[8]={0};
    const uint64_t sentinel=UINT64_C(0x123456789abcdef0);
    guest_stack[4]=sentinel;
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.mxcsr=0x1f80;
    cpu.r[RAX]=initial_rax;
    cpu.r[RDI]=rdi;
    const uint64_t sp=(uint64_t)(uintptr_t)&guest_stack[4];
    cpu.r[RSP]=sp;
    const unsigned old=unwanted;
    table[i].fn(&cpu);
    if(unwanted!=old || cpu.r[RAX]!=expected ||
       cpu.r[RSP]!=sp+8 || cpu.rip!=sentinel) {
        fprintf(stderr,"V201 function %u returned unexpected result/callback\n",i);
        return 5;
    }
    /* x86 tail JMP does not push any return address onto the stack. */
    if (call_next != 0 || guest_stack[3]!=0) {
        fprintf(stderr,"V201 indirect tail jump unexpectedly pushed a return address\n");
        return 6;
    }
    return 0;
}

int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1) return 2;
    static unsigned char image[0x2000]={0};
    image_base=(uint64_t)(uintptr_t)image;
    RcApi api={0};
    api.version=BB_RECOMP_API_VERSION;
    api.image_base=image_base;
    api.step=deny_step;
    api.call=deny_call;
    api.tail=deny_tail;
    api.bail=deny_bail;
    api.trace=deny_trace;
    size_t n=0;
    table=bb_recomp_init(&api,&n);
    const uint64_t offsets[]={0x1000,0x1010,0x1020,0x1030,0x1050};
    const uint64_t sizes[]={2,2,8,8,5};
    if(!table || n!=5) return 3;
    for(size_t i=0;i<n;++i) {
        if(table[i].offset!=offsets[i] || table[i].size!=sizes[i] ||
           !table[i].fn || !table[i].direct || !table[i].hash) return 7;
        *table[i].direct=table[i].fn;
    }
    /* Fail closed: only exact original-generated compiled entry addresses
     * are eligible. Never dispatch to function interiors/unknown targets. */
    if(rc_native_find(image_base+0x1020)!=table[2].fn ||
       rc_native_find(image_base+0x1030)!=table[3].fn ||
       rc_native_find(image_base+0x1021) ||
       rc_native_find(image_base+0x1011) ||
       rc_native_find(image_base+0x2000) ||
       rc_native_find(image_base-1)) return 8;
    *table[2].direct=(RcFn)0;
    if(rc_native_find(image_base+0x1020)) return 9;
    *table[2].direct=table[2].fn;
    /* JMP RAX -> native 0x1020 -> RET with no additional stack push. */
    if(run(0,image_base+0x1020,0,42,0)) return 10;
    /* JMP [RDI], pointer slot is native 0x1030 -> RET. */
    uint64_t vtable_slot=image_base+0x1030;
    if(run(1,3,(uint64_t)(uintptr_t)&vtable_slot,99,0)) return 11;
    /* MOV RAX,RDI; JMP RAX -> native compiled 0x1020. */
    if(run(4,5,image_base+0x1020,42,0)) return 12;
    /* Control: direct native entrypoints unchanged by source patch. */
    if(run(2,1,0,42,0)) return 13;
    if(run(3,1,0,99,0)) return 14;
    if(unwanted) return 15;
    puts("SHYT_V201_ORIGINAL_BBRECOMP_NATIVE_INDIRECT_TAIL_JUMPS_NO_RUNTIME_PASS");
    puts("Synthetic x86 full functions ONLY; no game, no EBOOT/PS4 loader, no HLE.");
    return 0;
}
