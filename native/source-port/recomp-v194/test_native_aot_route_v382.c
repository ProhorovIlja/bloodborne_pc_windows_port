/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic RcApi-v4 indirect calls, never original Bloodborne execution.
 */
#include "full_cpu_abi_v194.h"
#include "native_aot_route_v382.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#if !defined(_WIN32)
#include <signal.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif
#define CHECK(expr) do {if(!(expr)){fprintf(stderr,"V382_TEST_LINE_%d\n",__LINE__);return 1;}}while(0)
typedef struct Stack {
    uint64_t words[8];
    unsigned writes;
    int allow;
} Stack;
static int validated_stack_store(void *ctx,uint64_t addr,uint64_t value) {
    Stack *s=(Stack *)ctx;
    uintptr_t start, end;
    if (!s || s->allow!=1) return 0;
    start=(uintptr_t)&s->words[0];
    end=(uintptr_t)&s->words[8];
    if (addr<start || addr>end-8 || (addr&7u)) return 0;
    memcpy((void *)(uintptr_t)addr,&value,sizeof(value));
    ++s->writes;
    return 1;
}
static void guest_ret(BbCpu *cpu) {
    uint64_t value=0;
    memcpy(&value,(void *)(uintptr_t)cpu->r[4],8);
    cpu->rip=value;
    cpu->r[4]+=8;
}
static void fn_plus(BbCpu *cpu) {
    cpu->r[0]+=3;
    guest_ret(cpu);
}
static void fn_double(BbCpu *cpu) {
    cpu->r[0]*=2;
    guest_ret(cpu);
}
static int attest(void *ctx,uint64_t address,uint64_t size,uint64_t hash) {
    unsigned *n=(unsigned *)ctx;
    ++*n;
    return (address==UINT64_C(0x400100) && size==16 &&
            hash==UINT64_C(0xA1)) ||
           (address==UINT64_C(0x400200) && size==32 &&
            hash==UINT64_C(0xB2));
}
static int test_route(void) {
    RcApi strict={0},published={0},saved={0};
    RcFn slot_plus=NULL, slot_double=NULL;
    RcFunction table[]={
        {0x100,16,0xA1,fn_plus,&slot_plus},
        {0x200,32,0xB2,fn_double,&slot_double}
    };
    ShytStrictAotProofV381 proof={0},invalid;
    ShytNativeAotRouteV382 r={0},rejected={0};
    Stack s={0};
    BbCpu cpu={0},before;
    unsigned attest_checks=0;
    CHECK(shyt_strict_aot_base_v381(&strict,0x400000));
    CHECK(shyt_strict_aot_activate_v381(&strict,table,2,0x400000,
                                       attest,&attest_checks,&proof));
    CHECK(attest_checks==2);
    CHECK(proof.functions_attested==2);
    CHECK(!shyt_native_aot_lookup_v382(&r,0x400100));
    CHECK(!shyt_native_aot_prepare_v382(&r,NULL,table,2,&proof,
                                        validated_stack_store,&s));
    invalid=proof;invalid.functions_attested=1;
    CHECK(!shyt_native_aot_prepare_v382(&r,&strict,table,2,&invalid,
                                        validated_stack_store,&s));
    invalid=proof;invalid.owner_game_startup_proven=1;
    CHECK(!shyt_native_aot_prepare_v382(&r,&strict,table,2,&invalid,
                                        validated_stack_store,&s));
    invalid=proof;invalid.no_guest_fallback_callbacks=0;
    CHECK(!shyt_native_aot_prepare_v382(&r,&strict,table,2,&invalid,
                                        validated_stack_store,&s));
    table[1].offset=0x100; /* no duplicate offsets */
    CHECK(!shyt_native_aot_prepare_v382(&r,&strict,table,2,&proof,
                                        validated_stack_store,&s));
    table[1].offset=0x200;
    slot_double=NULL; /* reject missing direct admission */
    CHECK(!shyt_native_aot_prepare_v382(&r,&strict,table,2,&proof,
                                        validated_stack_store,&s));
    slot_double=fn_double;
    CHECK(shyt_native_aot_prepare_v382(&r,&strict,table,2,&proof,
                                       validated_stack_store,&s));
    CHECK(r.ready==1 && r.count==2);
    CHECK(!shyt_native_aot_prepare_v382(&r,&strict,table,2,&proof,
                                        validated_stack_store,&s));
    CHECK(shyt_native_aot_lookup_v382(&r,0x400100)==fn_plus);
    CHECK(shyt_native_aot_lookup_v382(&r,0x400200)==fn_double);
    CHECK(!shyt_native_aot_lookup_v382(&r,0x400101));
    CHECK(!shyt_native_aot_lookup_v382(&r,0x400199));
    CHECK(!shyt_native_aot_lookup_v382(&r,0));
    /* The snapshot must not change if the caller mutates the source. */
    table[0].fn=fn_double;
    CHECK(shyt_native_aot_lookup_v382(&r,0x400100)==fn_plus);
    table[0].fn=fn_plus;
    cpu.r[4]=(uint64_t)(uintptr_t)&s.words[6];
    cpu.r[0]=10;
    cpu.rip=0x400100;
    before=cpu;
    s.allow=1;
    CHECK(!shyt_native_aot_try_call_v382(&r,&cpu,0x400999,0x123456));
    CHECK(!memcmp(&before,&cpu,sizeof(cpu)) && s.writes==0);
    s.allow=0;
    CHECK(!shyt_native_aot_try_call_v382(&r,&cpu,0x400100,0x123456));
    CHECK(!memcmp(&before,&cpu,sizeof(cpu)) && s.writes==0);
    s.allow=1;
    CHECK(shyt_native_aot_try_call_v382(&r,&cpu,0x400100,0x123456));
    CHECK(cpu.r[0]==13 && cpu.rip==0x123456);
    CHECK(cpu.r[4]==(uint64_t)(uintptr_t)&s.words[6] && s.writes==1);
    /* RSP underflow and zero next are denied before writing stack. */
    before=cpu;cpu.r[4]=0;
    CHECK(!shyt_native_aot_try_call_v382(&r,&cpu,0x400100,0x123456));
    CHECK(cpu.r[4]==0 && s.writes==1);
    cpu=before;
    CHECK(!shyt_native_aot_try_call_v382(&r,&cpu,0x400100,0));
    CHECK(!shyt_native_aot_try_call_v382(&r,NULL,0x400100,0x123456));
    CHECK(s.writes==1);
    /* Tail has no push: preexisting return address remains on stack. */
    s.words[6]=0xABCDEF;
    cpu.rip=0x400200;
    CHECK(shyt_native_aot_try_tail_v382(&r,&cpu));
    CHECK(cpu.r[0]==26 && cpu.rip==0xABCDEF && s.writes==1);
    CHECK(cpu.r[4]==(uint64_t)(uintptr_t)&s.words[7]);
    before=cpu;
    CHECK(!shyt_native_aot_try_tail_v382(&r,&cpu));
    CHECK(!memcmp(&cpu,&before,sizeof(cpu)));
    CHECK(!shyt_native_aot_try_tail_v382(&r,NULL));
    /* Once published, strict base still owns forbidden step and bail. */
    CHECK(!shyt_native_aot_publish_v382(&rejected,&strict,&published));
    CHECK(shyt_native_aot_publish_v382(&r,&strict,&published));
    CHECK(published.call && published.tail);
    CHECK(published.step==strict.step && published.bail==strict.bail);
    CHECK(!shyt_strict_aot_is_base_v381(&published));
    CHECK(!shyt_native_aot_publish_v382(&r,&strict,&saved));
    CHECK(!shyt_native_aot_dispose_v382(&r)); /* no hot unload */
    cpu.r[4]=(uint64_t)(uintptr_t)&s.words[6];
    cpu.r[0]=2;
    published.call(&cpu,0x400100,0x111111);
    CHECK(cpu.r[0]==5 && cpu.rip==0x111111);
    s.words[6]=0x222222;
    cpu.rip=0x400200;
    published.tail(&cpu);
    CHECK(cpu.r[0]==10 && cpu.rip==0x222222);
#if !defined(_WIN32)
    pid_t pid=fork();
    CHECK(pid>=0);
    if (pid==0) {
        struct rlimit no_core={0,0};
        (void)setrlimit(RLIMIT_CORE,&no_core);
        published.call(&cpu,0xDEADBEEF,0x123456); /* MUST abort */
        _exit(0);
    }
    int status=0;
    CHECK(waitpid(pid,&status,0)==pid);
    CHECK(WIFSIGNALED(status) && WTERMSIG(status)==SIGABRT);
#endif
    CHECK(shyt_native_aot_dispose_v382(&rejected));
    return 0;
}
int main(void) {
    CHECK(!test_route());
    puts("NATIVE_V382_AOT_ONLY_INDIRECT_CALL_TAIL_NO_GUEST_DISPATCH_PASS");
    return 0;
}
