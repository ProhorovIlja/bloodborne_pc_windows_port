/* SPDX-License-Identifier: GPL-2.0-or-later
 * V239: genuine RcApi V4 host-clock bridge smoke test, no retail game data.
 */
#include "native_clock_rcapi_route_v239.h"
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint64_t begin, end;
    int deny;
} Range;
static int permits(void *ctx, uint64_t at, size_t count, int write) {
    const Range *r = (const Range *)ctx;
    return !r->deny && write && count == 8 && at >= r->begin &&
           at <= r->end && count <= r->end - at;
}
static int pinned, denies, leaves, entries, fallbacks, faults;
static jmp_buf trap;
static int enter(void *ctx) {
    (void)ctx;
    if (pinned || denies) return 0;
    pinned = 1; ++entries; return 1;
}
static void leave(void *ctx) {
    (void)ctx;
    assert(pinned);
    pinned = 0; ++leaves;
}
static void fatal_guest(BbCpu *cpu, uint64_t target, uint64_t next, void *ctx) {
    (void)cpu; (void)target; (void)next; (void)ctx;
    assert(!pinned);
    ++faults; longjmp(trap, 1);
}
static void old_call(BbCpu *cpu, uint64_t target, uint64_t next) {
    (void)target; (void)next;
    assert(!pinned && cpu);
    ++fallbacks;
}
static uint64_t old_step(BbCpu *cpu) { return cpu->rip; }
static void old_tail(BbCpu *cpu) { (void)cpu; }
static void old_bail(BbCpu *cpu, uint64_t rsp) { (void)cpu; (void)rsp; }

int main(void) {
#if defined(_WIN32)
    const uint64_t base = UINT64_C(0x10000000);
    uint64_t stack[16] = {0};
    Range range = {(uint64_t)(uintptr_t)&stack[0],
                   (uint64_t)(uintptr_t)&stack[16], 0};
    RcApi upstream = {0};
    upstream.version = BB_RECOMP_API_VERSION;
    upstream.image_base = base;
    upstream.call = old_call;
    upstream.step = old_step;
    upstream.tail = old_tail;
    upstream.bail = old_bail;
    ShytClockTargetsV239 mapping = {base, 0x1000, 0x1020};
    ShytClockRouteV239 route;
    assert(!shyt_clock_rcapi_api_v239(&route));
    assert(shyt_clock_rcapi_install_v239(&route, &upstream, &mapping,
           permits, &range, fatal_guest, 0, enter, leave, 0));
    assert(!shyt_clock_rcapi_install_v239(&route, &upstream, &mapping,
           permits, &range, fatal_guest, 0, enter, leave, 0));
    const RcApi *api = shyt_clock_rcapi_api_v239(&route);
    assert(api && api->call != upstream.call);
    assert(api->step == upstream.step && api->tail == upstream.tail);
    BbCpu cpu;
    memset(&cpu, 0, sizeof(cpu));
    cpu.r[RSP] = (uint64_t)(uintptr_t)&stack[8];
    cpu.rip = 0x200;
    const uint64_t rsp = cpu.r[RSP];
    api->call(&cpu, base + 0xbeef, 0x202);
    assert(fallbacks == 1 && cpu.rip == 0x200 && cpu.r[RSP] == rsp);
    api->call(&cpu, base + mapping.get_tsc_frequency_offset, 0x310);
    assert(cpu.r[RAX] == UINT64_C(1600000000));
    assert(cpu.rip == 0x310 && cpu.r[RSP] == rsp);
    assert(stack[7] == 0x310);
    api->call(&cpu, base + mapping.read_tsc_offset, 0x320);
    assert(cpu.rip == 0x320 && cpu.r[RSP] == rsp);
    assert(stack[7] == 0x320);
    assert(cpu.r[RAX] < UINT64_C(160000000000)); /* <100 s */
    range.deny = 1;
    cpu.rip = 0x333;
    if (setjmp(trap) == 0)
        api->call(&cpu, base + mapping.read_tsc_offset, 0x444);
    assert(faults == 1 && cpu.rip == 0x333 && !pinned);
    range.deny = 0; denies = 1;
    if (setjmp(trap) == 0)
        api->call(&cpu, base + mapping.read_tsc_offset, 0x445);
    assert(faults == 2 && cpu.rip == 0x333 && !pinned);
    denies = 0;
    cpu.r[RSP] = 0;
    if (setjmp(trap) == 0)
        api->call(&cpu, base + mapping.get_tsc_frequency_offset, 0x446);
    assert(faults == 3 && cpu.r[RSP] == 0 && !pinned);
    assert(entries == leaves);
    assert(fallbacks == 1);
#else
    /* Host clock availability intentionally requires Windows for V239. */
#endif
    puts("SHYT_V239_CLOCK_RCAPI_WINDOWS_PASS");
    return 0;
}
