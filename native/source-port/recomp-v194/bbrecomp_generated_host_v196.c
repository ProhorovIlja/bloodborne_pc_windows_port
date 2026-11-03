/* V196 independent Windows-native host for C actually emitted by the exact
 * bloodborne-native/bloodborne-recomp bbrecomp --snippets generator.
 * NO original PS4 executable, game code, emulator, JIT or generated game
 * data. The snippet input is entirely synthetic x86-64 instructions.
 */
#include "recomp/rc.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern const RcFunction *bb_recomp_init(const RcApi *, size_t *);
static unsigned callbacks;
static uint64_t forbidden_step(BbCpu *c) { ++callbacks; return c->rip; }
static void forbidden_call(BbCpu *c,uint64_t t,uint64_t n)
{(void)c;(void)t;(void)n;++callbacks;}
static void forbidden_tail(BbCpu *c) {(void)c;++callbacks;}
static void forbidden_bail(BbCpu *c,uint64_t sp)
{(void)c;(void)sp;++callbacks;}
static void forbidden_trace(uint64_t off,const uint64_t regs[16],const BbCpu *c)
{(void)off;(void)regs;(void)c;++callbacks;}

static int check(const RcFunction *table,size_t count,size_t slot,
                 uint64_t rax,uint64_t rdi,uint64_t rsi,uint64_t expected) {
    if (slot>=count || !table[slot].fn || table[slot].offset!=slot+1) return 11;
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.mxcsr=0x1f80;
    cpu.r[RAX]=rax;
    cpu.r[RDI]=rdi;
    cpu.r[RSI]=rsi;
    cpu.r[RSP]=0x10000u; /* instruction snippet has NO guest stack access */
    table[slot].fn(&cpu);
    if (cpu.r[RAX]!=expected || cpu.r[RSP]!=0x10000u ||
        cpu.rip!=0x400000u + (slot==0 ? 3u : slot==1 ? 3u :
                               slot==2 ? 2u : slot==3 ? 3u : 7u) ||
        callbacks) return 12;
    return 0;
}
int main(int argc,char **argv) {
    (void)argv;
    if (argc!=1) return 2; /* even an EBOOT argument must be rejected */
    RcApi api={0};
    api.version=BB_RECOMP_API_VERSION;
    api.image_base=0x400000u;
    api.step=forbidden_step;
    api.call=forbidden_call;
    api.tail=forbidden_tail;
    api.bail=forbidden_bail;
    api.trace=forbidden_trace;
    size_t count=0;
    const RcFunction *table=bb_recomp_init(&api,&count);
    if (!table || count!=5) {
        fprintf(stderr,"V196 exact upstream snippet table count mismatch: %zu\n",count);
        return 3;
    }
    /* Entirely invented instruction input in fixture:
     *   mov rax,rdi; add rax,rsi; xor eax,eax; inc rax;
     *   mov rax,1.
     * Independently test actual generated C semantics across two platforms.
     */
    if (check(table,count,0,20,41,17,41)) return 21;
    if (check(table,count,1,20,41,17,37)) return 22;
    if (check(table,count,2,20,41,17,0)) return 23;
    if (check(table,count,3,20,41,17,21)) return 24;
    if (check(table,count,4,20,41,17,1)) return 25;
    puts("SHYT_V196_ACTUAL_UPSTREAM_BBRECOMP_TO_NATIVE_WINDOWS_EXE_PASS");
    puts("SYNTHETIC INSTRUCTIONS ONLY. Full Bloodborne native engine NOT proven.");
    return 0;
}
