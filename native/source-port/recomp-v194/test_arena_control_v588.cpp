/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_control_v588.h"
#include <array>
#include <cassert>
struct Trace { bool ready; uint32_t status; std::array<unsigned,8> events; unsigned n; };
static bool ready(void *v) { auto &t=*static_cast<Trace *>(v); t.events[t.n++]=1; return t.ready; }
static uint32_t attempt(void *v) { auto &t=*static_cast<Trace *>(v); t.events[t.n++]=2; return t.status; }
static uint32_t release(void *v) { auto &t=*static_cast<Trace *>(v); t.events[t.n++]=3; return t.status; }
static void diag(void *v,unsigned line) { auto &t=*static_cast<Trace *>(v); t.events[t.n++]=line; }
int main() {
    using S=BbControlStateV588;
    Trace t{false,0x8002000bu,{},0};
    const BbMutexControlV588 m{&t,ready,attempt,release,diag};
    assert(bb_arena_control_v588(0xc0,&m).value==0 && t.n==7);
    const std::array<unsigned,8> expected{1,0x7e,2,0x80,0x82,0x84,0x86,0};
    assert(t.events==expected);
    t={true,0x8002003cu,{},0};
    assert(bb_arena_control_v588(0xc0,&m).value==-3 && t.n==2 && t.events[1]==2);
    t={false,0x80020016u,{},0};
    assert(bb_arena_control_v588(0xc8,&m).state==S::complete && t.n==4);
    assert(t.events[1]==0x99 && t.events[2]==3 && t.events[3]==0xc0);
    t={true,0x80020001u,{},0};
    assert(bb_arena_control_v588(0xc8,&m).state==S::complete && t.n==2);
    assert(bb_arena_control_v588(0xc8).state==S::invalid);
    assert(bb_arena_control_v588(0xd0,&m).state==S::invalid);
    for (unsigned s:{0u,0x18u,0x78u,0xb8u}) {
        const auto x=bb_arena_control_v588(s);
        assert(x.state==S::complete && x.value==(s==0x18?-1:0));
    }
}
