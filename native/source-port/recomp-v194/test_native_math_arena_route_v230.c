/* V230: real native Windows executable, pinned upstream BbCpu / RcApi.
 * FICTITIOUS imported math addresses. No game binary, source or assets.
 * This tests integration, not native Bloodborne game boot.
 */
#include "native_math_arena_route_v229.h"
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <string.h>

static jmp_buf g_fault_boundary;
static unsigned g_faults, g_fallbacks;
static ShytGuestArenaV228 *g_arena;

static void fatal(BbCpu *cpu, uint64_t target, uint64_t next, void *ctx) {
    (void)cpu; (void)target; (void)next; (void)ctx;
    /* The V229 route MUST release the shared arena pin before longjmp. */
    assert(!shyt_guest_arena_v228_permit_pinned(g_arena,
            (uint64_t)(uintptr_t)g_arena->base + 16, 8, 1));
    ++g_faults;
    longjmp(g_fault_boundary,1);
}
static void previous_call(BbCpu *cpu, uint64_t target, uint64_t next) {
    (void)cpu; (void)target; (void)next;
    ++g_fallbacks;
    assert(!shyt_guest_arena_v228_permit_pinned(g_arena,
            (uint64_t)(uintptr_t)g_arena->base + 16, 8, 1));
}
static uint64_t previous_step(BbCpu *cpu) { return cpu->rip; }
static void previous_tail(BbCpu *cpu) { (void)cpu; }
static void previous_bail(BbCpu *cpu, uint64_t value) {
    (void)cpu; (void)value;
}

int main(void) {
    SYSTEM_INFO info;
    GetSystemInfo(&info);
    const size_t page=(size_t)info.dwPageSize;
    assert(page >= 4096);
    ShytGuestArenaV228 arena={0};
    assert(shyt_guest_arena_v228_create(&arena,page*3));
    g_arena=&arena;
    const uint64_t memory=(uint64_t)(uintptr_t)arena.base;
    const uint64_t stack=memory+(uint64_t)(page*2)+128;
    static const char *names[23]={
        "acos","acosf","asin","asinf","atan","atan2","atan2f",
        "atanf","exp","exp2","exp2f","expf","fmod","fmodf",
        "frexp","frexpf","ldexp","ldexpf","pow","powf","tan",
        "tanf","tanhf"
    };
    ShytMathImportDesc original_like[23];
    for(size_t i=0;i<23;++i) {
        original_like[i].name=names[i];
        original_like[i].offset=0x100u+(uint64_t)i*16u;
    }
    ShytMathImportTable table;
    const uint64_t image_base=0x1000000;
    assert(shyt_math_import_table_v224_init(
        &table,image_base,original_like,23));
    RcApi upstream={0};
    upstream.version=BB_RECOMP_API_VERSION;
    upstream.image_base=image_base;
    upstream.call=previous_call;
    upstream.step=previous_step;
    upstream.tail=previous_tail;
    upstream.bail=previous_bail;
    ShytMathRcApiRoute routed;
    assert(!shyt_math_rcapi_route_v226_install(
        &routed,&upstream,&table,
        shyt_guest_arena_v228_permit_pinned,&arena,fatal,NULL));
    assert(shyt_math_arena_route_v229_install(
        &routed,&upstream,&table,&arena,fatal,NULL));
    const RcApi *api=shyt_math_rcapi_route_v226_api(&routed);
    assert(api && api->call);
    assert(api->step==upstream.step && api->tail==upstream.tail);
    BbCpu cpu;
    memset(&cpu,0,sizeof(cpu));
    cpu.r[RSP]=stack;
    cpu.rip=0x5000;
    cpu.v[0].fd[0]=2.0;
    cpu.v[1].fd[0]=4.0;
    const uint64_t pow_target=image_base+original_like[18].offset;
    api->call(&cpu,pow_target,0x5001);
    assert(cpu.v[0].fd[0]==16.0);
    assert(cpu.rip==0x5001 && cpu.r[RSP]==stack);
    api->call(&cpu,image_base+0xfeed,0x9000);
    assert(g_fallbacks==1 && g_faults==0);
    /* Known target with a read-only return page is fatal, NOT fallback. */
    assert(shyt_guest_arena_v228_protect(
        &arena,page*2,page,PAGE_READONLY));
    cpu.v[0].fd[0]=2.0;
    cpu.v[1].fd[0]=4.0;
    if(setjmp(g_fault_boundary)==0)
        api->call(&cpu,pow_target,0x5002);
    assert(g_faults==1 && g_fallbacks==1);
    assert(cpu.r[RSP]==stack && cpu.rip==0x5001);
    /* If the trap leaked a reader lock this EXCLUSIVE protection call hangs. */
    assert(shyt_guest_arena_v228_protect(
        &arena,page*2,page,PAGE_READWRITE));
    api->call(&cpu,pow_target,0x5003);
    assert(cpu.v[0].fd[0]==16.0 && cpu.rip==0x5003);
    /* frexp writes through guest RDI and must validate that other page. */
    cpu.v[0].fd[0]=8.0;
    cpu.r[RDI]=memory+256;
    const uint64_t frexp_target=image_base+original_like[14].offset;
    assert(shyt_guest_arena_v228_protect(
        &arena,0,page,PAGE_READONLY));
    if(setjmp(g_fault_boundary)==0)
        api->call(&cpu,frexp_target,0x5004);
    assert(g_faults==2 && g_fallbacks==1);
    assert(shyt_guest_arena_v228_protect(
        &arena,0,page,PAGE_READWRITE));
    api->call(&cpu,frexp_target,0x5005);
    int exponent=0;
    memcpy(&exponent,(void *)(uintptr_t)(memory+256),sizeof(exponent));
    assert(exponent==4 && cpu.v[0].fd[0]==0.5);
    assert(cpu.rip==0x5005 && cpu.r[RSP]==stack);
    /* Releasing the whole guest arena makes all future calls fatal. */
    assert(shyt_guest_arena_v228_destroy(&arena));
    if(setjmp(g_fault_boundary)==0)
        api->call(&cpu,pow_target,0x5006);
    assert(g_faults==3 && g_fallbacks==1);
    return 0;
}
