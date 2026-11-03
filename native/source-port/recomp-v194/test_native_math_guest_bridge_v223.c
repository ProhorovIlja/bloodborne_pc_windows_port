/* V223: invented CPU register/stack fixture using PINNED upstream BbCpu. */
#include "native_math_guest_bridge_v223.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

static void setup(BbCpu *cpu, uint64_t stack[4]) {
    memset(cpu,0,sizeof(*cpu));
    cpu->flags=0x202;
    cpu->r[RSP]=(uint64_t)(uintptr_t)&stack[0];
    cpu->r[RAX]=0xdeadbabe;
    stack[0]=UINT64_C(0x123456789abcdef0);
    cpu->rip=0x9000;
}
static void returned(BbCpu *cpu,uint64_t old_sp) {
    assert(cpu->r[RSP]==old_sp+8);
    assert(cpu->rip==UINT64_C(0x123456789abcdef0));
    assert(cpu->flags==0x202);
    assert(cpu->r[RAX]==0xdeadbabe);
}
int main(void) {
    BbCpu cpu;
    uint64_t stack[4]={0};
    assert(shyt_guest_math_v223_find("sceFiosFHSyncSync")==NULL);
    assert(shyt_guest_math_v223_find("_FLog")==NULL);
    assert(shyt_guest_math_v223_find(NULL)==NULL);
    setup(&cpu,stack);
    cpu.v[0].fd[0]=2.0; cpu.v[1].fd[0]=4.0;
    uint64_t sp=cpu.r[RSP];
    shyt_guest_math_v223_find("pow")(&cpu);
    assert(cpu.v[0].fd[0]==16.0); returned(&cpu,sp);
    setup(&cpu,stack);
    cpu.v[0].f[0]=2.0f; cpu.v[1].f[0]=3.0f;
    sp=cpu.r[RSP]; shyt_guest_math_v223_find("powf")(&cpu);
    assert(cpu.v[0].f[0]==8.0f); returned(&cpu,sp);
    int exponent=-1;
    setup(&cpu,stack);
    cpu.v[0].fd[0]=8.0; cpu.r[RDI]=(uint64_t)(uintptr_t)&exponent;
    sp=cpu.r[RSP]; shyt_guest_math_v223_find("frexp")(&cpu);
    assert(cpu.v[0].fd[0]==0.5 && exponent==4); returned(&cpu,sp);
    exponent=-1;
    setup(&cpu,stack);
    cpu.v[0].f[0]=8.0f; cpu.r[RDI]=(uint64_t)(uintptr_t)&exponent;
    sp=cpu.r[RSP]; shyt_guest_math_v223_find("frexpf")(&cpu);
    assert(cpu.v[0].f[0]==0.5f && exponent==4); returned(&cpu,sp);
    setup(&cpu,stack);
    cpu.v[0].fd[0]=0.5; cpu.r[RDI]=4;
    sp=cpu.r[RSP]; shyt_guest_math_v223_find("ldexp")(&cpu);
    assert(cpu.v[0].fd[0]==8.0); returned(&cpu,sp);
    setup(&cpu,stack);
    cpu.v[0].f[0]=0.5f; cpu.r[RDI]=4;
    sp=cpu.r[RSP]; shyt_guest_math_v223_find("ldexpf")(&cpu);
    assert(cpu.v[0].f[0]==8.0f); returned(&cpu,sp);
    setup(&cpu,stack);
    cpu.v[0].q[1]=UINT64_C(0xabcdef1987654321);
    cpu.v[0].fd[0]=0.; sp=cpu.r[RSP];
    shyt_guest_math_v223_find("exp")(&cpu);
    assert(cpu.v[0].fd[0]==1.0);
    assert(cpu.v[0].q[1]==UINT64_C(0xabcdef1987654321));
    returned(&cpu,sp);
    const char *names[] = {
        "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
        "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
        "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
    };
    for (size_t i=0; i<sizeof(names)/sizeof(names[0]); i++)
        assert(shyt_guest_math_v223_find(names[i])!=NULL);
    return 0;
}
