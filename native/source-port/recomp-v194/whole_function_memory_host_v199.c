/* V199: real original bbrecomp full-function generator across native PC
 * heap memory operations, lazy x86 flags, branch targets, PC-relative LEA
 * and unaligned read. Inputs are invented ELF64 bytes, NO GAME DATA.
 * The Linux/Windows executable does not parse or load an ELF or EBOOT.
 */
#include "recomp/rc.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

extern const RcFunction *bb_recomp_init(const RcApi *, size_t *);
static unsigned unexpected;
static uint64_t forbid_step(BbCpu *c) {(void)c;++unexpected;return 0;}
static void forbid_call(BbCpu *c,uint64_t t,uint64_t n)
{(void)c;(void)t;(void)n;++unexpected;}
static void forbid_tail(BbCpu *c) {(void)c;++unexpected;}
static void forbid_bail(BbCpu *c,uint64_t sp)
{(void)c;(void)sp;++unexpected;}
static void forbid_trace(uint64_t off,const uint64_t r[16],const BbCpu *c)
{(void)off;(void)r;(void)c;++unexpected;}

static const RcFunction *functions;
static int execute(size_t index,uint64_t initial_rax,uint64_t rdi,
                   uint64_t rsi,uint64_t expected,uint64_t *observed_flags) {
    if(index>=6 || !functions[index].fn) return 1;
    uint64_t stack[8]={0};
    stack[4]=UINT64_C(0x123456789abcdef0);
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.mxcsr=0x1f80;
    cpu.r[RAX]=initial_rax;
    cpu.r[RDI]=rdi;
    cpu.r[RSI]=rsi;
    const uint64_t original_stack=(uint64_t)(uintptr_t)&stack[4];
    cpu.r[RSP]=original_stack;
    functions[index].fn(&cpu);
    if(observed_flags) *observed_flags=cpu.flags;
    if(cpu.r[RAX]!=expected || cpu.r[RSP]!=original_stack+8 ||
       cpu.rip!=stack[4] || unexpected) {
        fprintf(stderr,"V199 native code execution failed for function %zu\n",index);
        return 2;
    }
    return 0;
}
int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1) return 2;
    static unsigned char image[0x2000];
    RcApi api={0};
    api.version=BB_RECOMP_API_VERSION;
    api.image_base=(uint64_t)(uintptr_t)image;
    api.step=forbid_step;
    api.call=forbid_call;
    api.tail=forbid_tail;
    api.bail=forbid_bail;
    api.trace=forbid_trace;
    size_t count=0;
    functions=bb_recomp_init(&api,&count);
    static const uint64_t offsets[6]={0x1000,0x1010,0x1020,0x1030,0x1050,0x1070};
    static const uint64_t sizes[6]={4,4,12,7,8,5};
    if(!functions || count!=6) return 3;
    for(size_t i=0;i<count;++i) {
        if(functions[i].offset!=offsets[i] ||
           functions[i].size!=sizes[i] ||
           !functions[i].hash || !functions[i].direct || !functions[i].fn)
            return 4;
        *functions[i].direct=functions[i].fn;
    }
    uint64_t cell=UINT64_C(0x1122334455667788);
    const uint64_t ptr=(uint64_t)(uintptr_t)&cell;
    if(execute(0,3,ptr,8,cell,NULL)) return 10;
    if(execute(1,51,ptr,UINT64_C(0x9988776655443322),51,NULL)) return 11;
    if(cell!=UINT64_C(0x9988776655443322)) return 12;
    uint64_t flags_zero=0,flags_nonzero=0;
    if(execute(2,19,0,0,0,&flags_zero)) return 13;
    if(execute(2,19,17,0,17,&flags_nonzero)) return 14;
    if(execute(2,19,UINT64_MAX,0,UINT64_MAX,NULL)) return 15;
    if(!(flags_zero & F_ZF) || (flags_nonzero & F_ZF)) return 16;
    if(execute(3,3,ptr,17,UINT64_C(0x9988776655443333),NULL)) return 17;
    if(execute(4,3,ptr,17,(uint64_t)(uintptr_t)&image[0x1090],NULL)) return 18;
    unsigned char bytes[16]={0};
    const uint64_t unaligned_value=UINT64_C(0xfedcba9876543210);
    memcpy(&bytes[1],&unaligned_value,sizeof unaligned_value);
    if(execute(5,3,(uint64_t)(uintptr_t)&bytes[0],17,unaligned_value,NULL))
        return 19;
    puts("SHYT_V199_REAL_BBRECOMP_MEMORY_BRANCH_FLAGS_RIP_NATIVE_PE_PASS");
    puts("Synthetic x86 functions ONLY. No original game, eboot, PS4 runtime or ELF loader.");
    return 0;
}
