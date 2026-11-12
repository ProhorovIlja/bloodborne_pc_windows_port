/* SPDX-License-Identifier: GPL-2.0-or-later
 * Only synthetic owner-free functions. Not complete Bloodborne.
 */
#include "full_cpu_abi_v194.h"
#include "native_strict_aot_v381.h"
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
#define CHECK(x) do {if(!(x)){fprintf(stderr,"V381_TEST_LINE_%d\n",__LINE__);return 1;}}while(0)

typedef struct AttestV381 {
    uint32_t approved;
    uint32_t invoked;
} AttestV381;
static void synthetic_a(BbCpu *cpu){cpu->r[0]++;}
static void synthetic_b(BbCpu *cpu){cpu->r[0]*=2;}
static int genuine_only_mock(void *p,uint64_t addr,uint64_t size,uint64_t hash){
    AttestV381 *a=(AttestV381 *)p;
    a->invoked++;
    return a->approved && ((addr==UINT64_C(0x400100) &&
        size==16 && hash==UINT64_C(0x1234)) ||
        (addr==UINT64_C(0x400200) && size==32 &&
         hash==UINT64_C(0x5678)));
}
static int test_registry(void){
    RcApi strict={0},modified;
    RcFn slot_a=NULL,slot_b=NULL;
    RcFunction fn[]={
        {0x100,16,0x1234,synthetic_a,&slot_a},
        {0x200,32,0x5678,synthetic_b,&slot_b}
    };
    ShytStrictAotProofV381 proof={999,9,9},saved=proof;
    AttestV381 auth={0,0};
    CHECK(!shyt_strict_aot_base_v381(NULL,0x400000));
    CHECK(!shyt_strict_aot_base_v381(&strict,0));
    CHECK(shyt_strict_aot_base_v381(&strict,UINT64_C(0x400000)));
    CHECK(strict.version==BB_RECOMP_API_VERSION);
    CHECK(shyt_strict_aot_is_base_v381(&strict));
    CHECK(strict.step && strict.call && strict.tail && strict.bail);
    CHECK(strict.trace==NULL);
    CHECK(!shyt_strict_aot_is_base_v381(NULL));
    modified=strict;modified.call=NULL;
    CHECK(!shyt_strict_aot_is_base_v381(&modified));
    CHECK(!shyt_strict_aot_activate_v381(&modified,fn,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    CHECK(auth.invoked==0 && slot_a==NULL && slot_b==NULL);
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400001,
                                        genuine_only_mock,&auth,&proof));
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,0,0x400000,
                                        genuine_only_mock,&auth,&proof));
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        NULL,&auth,&proof));
    CHECK(!shyt_strict_aot_activate_v381(&strict,NULL,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        genuine_only_mock,&auth,NULL));
    CHECK(!memcmp(&proof,&saved,sizeof(proof)));
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    CHECK(auth.invoked==1); /* refused early, did not partially activate */
    CHECK(slot_a==NULL && slot_b==NULL);
    auth.approved=1;
    fn[1].direct=&slot_a; /* double-use must be detected before hash test */
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    CHECK(auth.invoked==1);
    fn[1].direct=&slot_b;
    fn[1].offset=fn[0].offset; /* duplicate function offset */
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    fn[1].offset=0x200;
    fn[1].direct=NULL; /* strict cannot silently use guest fallback */
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    fn[1].direct=&slot_b;
    slot_b=synthetic_a; /* old epoch must be revoked outside this function */
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    slot_b=NULL;
    CHECK(shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                       genuine_only_mock,&auth,&proof));
    CHECK(proof.functions_attested==2 && proof.no_guest_fallback_callbacks==1);
    CHECK(proof.owner_game_startup_proven==0);
    CHECK(slot_a==synthetic_a && slot_b==synthetic_b);
    BbCpu cpu={0};
    cpu.r[0]=40;
    slot_a(&cpu);
    slot_b(&cpu);
    CHECK(cpu.r[0]==82);
    CHECK(!shyt_strict_aot_activate_v381(&strict,fn,2,0x400000,
                                        genuine_only_mock,&auth,&proof));
    CHECK(slot_a==synthetic_a && slot_b==synthetic_b);
    return 0;
}
#if !defined(_WIN32)
static int test_trap(void) {
    RcApi strict={0};
    CHECK(shyt_strict_aot_base_v381(&strict,0x400000));
    pid_t p=fork();
    CHECK(p>=0);
    if (p==0) {
        struct rlimit no_core={0,0};
        (void)setrlimit(RLIMIT_CORE,&no_core);
        strict.call(NULL,0x1234,0x5678); /* must abort, never return */
        _exit(0);
    }
    int status=0;
    CHECK(waitpid(p,&status,0)==p);
    CHECK(WIFSIGNALED(status));
    CHECK(WTERMSIG(status)==SIGABRT);
    return 0;
}
#endif
int main(void){
    CHECK(!test_registry());
#if !defined(_WIN32)
    CHECK(!test_trap());
#endif
    puts("NATIVE_V381_STRICT_NO_GUEST_AOT_FAIL_CLOSED_SYNTHETIC_PASS");
    return 0;
}
