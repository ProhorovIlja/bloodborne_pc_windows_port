/* V203: genuine original bbrecomp normal-mode function FALLOUT to next AOT.
 * Five invented x86-64 functions; no copyrighted game code. The compiled
 * Windows EXE must not load an EBOOT/guest ELF or execute a PS4 runtime.
 */
#include "recomp/rc.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern const RcFunction *bb_recomp_init(const RcApi *, size_t *);
extern RcFn rc_native_find(uint64_t);
static unsigned rejected;
static uint64_t reject_step(BbCpu *c) {(void)c; ++rejected; return 0;}
static void reject_call(BbCpu *c,uint64_t t,uint64_t n)
{(void)c;(void)t;(void)n;++rejected;}
static void reject_tail(BbCpu *c) {(void)c;++rejected;}
static void reject_bail(BbCpu *c,uint64_t sp)
{(void)c;(void)sp;++rejected;}
static void reject_trace(uint64_t off,const uint64_t r[16],const BbCpu *c)
{(void)off;(void)r;(void)c;++rejected;}

static const RcFunction *fns;
static uint64_t B;

static int run(size_t slot,uint64_t expected) {
    uint64_t stack[8]={0};
    const uint64_t sentinel=UINT64_C(0x123456789abcdef0);
    stack[4]=sentinel;
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.mxcsr=0x1f80;
    cpu.r[RAX]=19;
    uint64_t rsp=(uint64_t)(uintptr_t)&stack[4];
    cpu.r[RSP]=rsp;
    const unsigned initial=rejected;
    fns[slot].fn(&cpu);
    if (rejected!=initial || cpu.r[RAX]!=expected ||
        cpu.r[RSP]!=rsp+8 || cpu.rip!=sentinel || stack[3]!=0) {
        fprintf(stderr,"V203 native adjacent-function flow %zu failed\n",slot);
        return 1;
    }
    return 0;
}

static int negative_unregistered_successor(void) {
    /* Deliberately remove the next function's registered native slot.
     * The original fallback MUST remain visible for the unknown target.
     * A host callback records it and returns, avoiding any PS4 runtime.
     * This negative control is NOT a native-game success assertion. */
    uint64_t stack[8]={0};
    stack[4]=UINT64_C(0x123456789abcdef0);
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.mxcsr=0x1f80;
    const uint64_t rsp=(uint64_t)(uintptr_t)&stack[4];
    cpu.r[RSP]=rsp;
    cpu.r[RAX]=19;
    const unsigned initial=rejected;
    *fns[1].direct=(RcFn)0;
    if (rc_native_find(B+0x1007)) return 1;
    fns[0].fn(&cpu);
    *fns[1].direct=fns[1].fn;
    /* Native AOT must NOT execute incorrect destination or fake RET. */
    if (rejected!=initial+1 || cpu.r[RAX]!=42 ||
        cpu.r[RSP]!=rsp || cpu.rip!=B+0x1007) return 2;
    return 0;
}
int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1) return 2; /* never accept an EBOOT argument */
    static unsigned char image[0x2000]={0};
    B=(uint64_t)(uintptr_t)image;
    RcApi api={0};
    api.version=BB_RECOMP_API_VERSION;
    api.image_base=B;
    api.step=reject_step;
    api.call=reject_call;
    api.tail=reject_tail;
    api.bail=reject_bail;
    api.trace=reject_trace;
    size_t n=0;
    fns=bb_recomp_init(&api,&n);
    const uint64_t offsets[]={0x1000,0x1007,0x1010,0x1017,0x1020};
    const uint64_t sizes[]={7,1,7,1,8};
    if(!fns || n!=5) return 3;
    for(size_t i=0;i<5;++i) {
        if (fns[i].offset!=offsets[i] || fns[i].size!=sizes[i] ||
            !fns[i].hash || !fns[i].fn || !fns[i].direct) return 4;
        *fns[i].direct=fns[i].fn;
    }
    if (rc_native_find(B+0x1007)!=fns[1].fn ||
        rc_native_find(B+0x1017)!=fns[3].fn ||
        rc_native_find(B+0x1008) || rc_native_find(B+0x1028)) return 5;
    /* The original GENERIC L_dispatch must transfer to the exact adjacent
     * compiled function, without RcApi.tail/bail. */
    if (run(0,42) || run(2,99) || run(1,19) ||
        run(3,19) || run(4,7)) return 6;
    if (negative_unregistered_successor()) return 7;
    puts("SHYT_NATIVE_V203_ORIGINAL_FUNCTION_FALLTHROUGH_DIRECT_AOT_PASS");
    puts("Synthetic ELF at BUILD time only. Unknown target still uses fallback.");
    return 0;
}
