/* V197: REAL original bbrecomp whole-function C pipeline, native Win64.
 * Functions are invented x86-64 instructions in a synthetic ELF generated
 * inside CI. Neither PS4 EBOOT nor emulator loads at program startup.
 */
#include "recomp/rc.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern const RcFunction *bb_recomp_init(const RcApi *, size_t *);
static unsigned unsupported;
static uint64_t forbidden_step(BbCpu *c) {
    ++unsupported;
    return c->rip;
}
static void forbidden_call(BbCpu *c,uint64_t t,uint64_t n)
{(void)c;(void)t;(void)n;++unsupported;}
static void forbidden_tail(BbCpu *c) {(void)c;++unsupported;}
static void forbidden_bail(BbCpu *c,uint64_t sp)
{(void)c;(void)sp;++unsupported;}
static void forbidden_trace(uint64_t off,const uint64_t r[16],const BbCpu *c)
{(void)off;(void)r;(void)c;++unsupported;}

static int execute(const RcFunction *table, unsigned index,
                   uint64_t initial_rax, uint64_t rdi, uint64_t rsi,
                   uint64_t expected) {
    if (index>=5 || !table[index].fn) return 10;
    uint64_t stack[8]={0};
    const uint64_t guest_return=UINT64_C(0x123456789abcdef0);
    stack[4]=guest_return;
    BbCpu cpu;
    memset(&cpu,0,sizeof cpu);
    cpu.mxcsr=0x1f80;
    cpu.r[RAX]=initial_rax;
    cpu.r[RDI]=rdi;
    cpu.r[RSI]=rsi;
    const uint64_t sp=(uint64_t)(uintptr_t)&stack[4];
    cpu.r[RSP]=sp;
    table[index].fn(&cpu);
    if (cpu.r[RAX]!=expected || cpu.r[RSP]!=sp+8 ||
        cpu.rip!=guest_return || unsupported) {
        fprintf(stderr,"V197 native function %u failed: rax=%llu, sp=%llu, rip=%llx, callbacks=%u\n",
                index,(unsigned long long)cpu.r[RAX],
                (unsigned long long)(cpu.r[RSP]-sp),
                (unsigned long long)cpu.rip,unsupported);
        return 11;
    }
    if (index==3 && stack[3] != UINT64_C(0x401035)) {
        fprintf(stderr,"V197 original inter-function CALL return address mismatch\n");
        return 12;
    }
    return 0;
}
int main(int argc,char **argv) {
    (void)argv;
    if (argc!=1) return 2; /* no retail executable arguments */
    RcApi api={0};
    api.version=BB_RECOMP_API_VERSION;
    api.image_base=UINT64_C(0x400000);
    api.step=forbidden_step;
    api.call=forbidden_call;
    api.tail=forbidden_tail;
    api.bail=forbidden_bail;
    api.trace=forbidden_trace;
    size_t count=0;
    const RcFunction *table=bb_recomp_init(&api,&count);
    static const uint64_t offsets[5]={0x1000,0x1010,0x1020,0x1030,0x1050};
    static const uint64_t sizes[5]={4,4,5,6,8};
    if (!table || count!=5) {
        fprintf(stderr,"V197 real whole-function table size mismatch\n");
        return 3;
    }
    for (size_t i=0;i<5;++i) {
        if (table[i].offset!=offsets[i] || table[i].size!=sizes[i] ||
            !table[i].hash || !table[i].fn || !table[i].direct)
            return 4;
        /* Own real direct-call dispatch table initialized before gameplay. */
        *table[i].direct=table[i].fn;
    }
    if (execute(table,0,12,42,10,42)) return 20;
    if (execute(table,1,12,42,10,22)) return 21;
    if (execute(table,2,12,42,10,52)) return 22;
    /* Direct CALL 0x1030 -> 0x1050 -> RET -> outer RET, no translator. */
    if (execute(table,3,12,42,10,42)) return 23;
    if (execute(table,4,12,42,10,42)) return 24;
    puts("SHYT_V197_ACTUAL_ORIGINAL_BBRECOMP_FUNCTION_CALL_RET_NATIVE_EXE_PASS");
    puts("Synthetic ELF build-time only; no runtime eboot, emulator or PS4 kernel.");
    return 0;
}
