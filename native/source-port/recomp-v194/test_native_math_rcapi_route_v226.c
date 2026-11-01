/* V226: invented math imports, REAL pinned upstream BbCpu and RcApi V4. */
#include "native_math_rcapi_route_v226.h"
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <setjmp.h>

typedef struct { uint64_t begin, end; int deny_stack, deny_exponent; } Bounds;
static int permit(void *ctx, uint64_t a, size_t n, int write) {
    const Bounds *b = (const Bounds *)ctx;
    if (!write || !n || a < b->begin || a > b->end || n > b->end-a)
        return 0;
    if ((n == 8 && b->deny_stack) ||
        (n == sizeof(int) && b->deny_exponent)) return 0;
    return 1;
}
static jmp_buf fault_jump;
static unsigned faults, fallbacks;
static uint64_t last_target, last_next, last_rsp, last_rip;
static void fatal_guest(BbCpu *cpu, uint64_t t, uint64_t n, void *ctx) {
    (void)cpu; (void)t; (void)n; (void)ctx;
    ++faults;
    longjmp(fault_jump,1);
}
static void previous_call(BbCpu *cpu,uint64_t target,uint64_t next) {
    ++fallbacks;
    last_target=target;last_next=next;
    last_rsp=cpu->r[RSP];last_rip=cpu->rip;
}
static uint64_t previous_step(BbCpu *cpu) { return cpu->rip; }
static void previous_tail(BbCpu *cpu) { (void)cpu; }
static void previous_bail(BbCpu *cpu, uint64_t rsp) { (void)cpu; (void)rsp; }

int main(void) {
    static const char *names[23] = {
        "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
        "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
        "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"};
    ShytMathImportDesc desc[23];
    for (size_t i=0; i<23; ++i) {
        desc[i].name=names[i];desc[i].offset=0x100+16*i;
    }
    const uint64_t base=0x1000000;
    ShytMathImportTable table;
    assert(shyt_math_import_table_v224_init(&table,base,desc,23));
    RcApi upstream={0};
    upstream.version=BB_RECOMP_API_VERSION;
    upstream.image_base=base;
    upstream.step=previous_step; upstream.call=previous_call;
    upstream.tail=previous_tail; upstream.bail=previous_bail;
    uint64_t stack[16]={0};
    Bounds bound={(uint64_t)(uintptr_t)&stack[0],
                  (uint64_t)(uintptr_t)&stack[16],0,0};
    ShytMathRcApiRoute route;
    assert(shyt_math_rcapi_route_v226_install(
        &route,&upstream,&table,permit,&bound,fatal_guest,NULL));
    const RcApi *api=shyt_math_rcapi_route_v226_api(&route);
    assert(api && api->call!=upstream.call);
    assert(api->step==upstream.step && api->tail==upstream.tail);
    assert(api->bail==upstream.bail && api->image_base==base);
    /* A repeated installation must NOT overwrite the active router. */
    assert(!shyt_math_rcapi_route_v226_install(
        &route,&upstream,&table,permit,&bound,fatal_guest,NULL));
    assert(shyt_math_rcapi_route_v226_api(&route)==api);
    BbCpu cpu;memset(&cpu,0,sizeof(cpu));
    cpu.r[RSP]=(uint64_t)(uintptr_t)&stack[8];
    cpu.rip=0x900; cpu.flags=0x202; cpu.r[RAX]=123;
    cpu.v[0].fd[0]=2.;cpu.v[1].fd[0]=4.;
    const uint64_t sp=cpu.r[RSP];
    const uint64_t pow_target=base+desc[18].offset;
    assert(!shyt_math_import_v224_try_call(&table,&cpu,pow_target,0x600));
    assert(cpu.r[RSP]==sp && cpu.rip==0x900);
    api->call(&cpu,base+0xbeef,0x222);
    assert(fallbacks==1 && last_target==base+0xbeef);
    assert(last_next==0x222 && last_rsp==sp && last_rip==0x900);
    assert(cpu.r[RSP]==sp && cpu.v[0].fd[0]==2.);
    bound.deny_stack=1;
    if(setjmp(fault_jump)==0) api->call(&cpu,pow_target,0x444);
    assert(faults==1 && fallbacks==1);
    assert(cpu.r[RSP]==sp && cpu.rip==0x900 && cpu.v[0].fd[0]==2.);
    bound.deny_stack=0;
    api->call(&cpu,pow_target,0x777);
    assert(fallbacks==1 && cpu.v[0].fd[0]==16.0);
    assert(cpu.r[RSP]==sp && cpu.rip==0x777);
    assert(cpu.r[RAX]==123 && cpu.flags==0x202);
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RSP]=sp; cpu.rip=0x990; cpu.v[0].fd[0]=8.;
    const uint64_t frexp_target=base+desc[14].offset;
    cpu.r[RDI]=0;
    if(setjmp(fault_jump)==0) api->call(&cpu,frexp_target,0xaab);
    assert(faults==2 && fallbacks==1);
    assert(cpu.r[RSP]==sp && cpu.rip==0x990);
    cpu.r[RDI]=(uint64_t)(uintptr_t)&stack[2];
    bound.deny_exponent=1;
    if(setjmp(fault_jump)==0) api->call(&cpu,frexp_target,0xaac);
    assert(faults==3 && fallbacks==1);
    assert(cpu.r[RSP]==sp && cpu.rip==0x990);
    bound.deny_exponent=0;
    cpu.r[RDI]=sp-8; /* overlaps return slot */
    if(setjmp(fault_jump)==0) api->call(&cpu,frexp_target,0xaad);
    assert(faults==4 && fallbacks==1);
    assert(cpu.r[RSP]==sp && cpu.rip==0x990);
    cpu.r[RDI]=(uint64_t)(uintptr_t)&stack[2];
    api->call(&cpu,frexp_target,0xaae);
    assert(faults==4 && fallbacks==1 && cpu.v[0].fd[0]==0.5);
    assert(stack[2]==4 && cpu.rip==0xaae && cpu.r[RSP]==sp);
    return 0;
}
