/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "shyt_yt_game_link_observer_v429.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define READ(counter) atomic_load_explicit(&(counter),memory_order_relaxed)
int main(void) {
    ShytYtGameLinkObserverV429 s={0};
    BbHookCtx c={0};
    assert(shyt_yt_v429_observe_send(&c,NULL)==0);
    assert(shyt_yt_v429_observe_update(&c,NULL)==0);
    assert(shyt_yt_v429_observe_send(NULL,&s)==0);
    assert(READ(s.outgoing_calls)==1u && READ(s.outgoing_malformed)==1u);
    shyt_yt_v429_reset(&s);
    /* YT original TakeGamePacket: rcx=packet, rdx=member,
     * rsi=nonzero reliable, r8=native packet size. */
    c.arg[0]=0x1000000u; // rdi independent, must not be touched
    c.arg[1]=1u; // rsi reliable
    c.arg[2]=0x7000000u; // rdx member
    c.arg[3]=0x4000000u; // rcx packet
    c.arg[4]=0x108u; // r8 size including u32 channel and u32 size
    c.arg[5]=0x1234u; // r9 independent
    c.ret=0xdeadbeefu;
    const BbHookCtx original=c;
    assert(shyt_yt_v429_observe_send(&c,&s)==0);
    assert(memcmp(&c,&original,sizeof(c))==0);
    assert(READ(s.outgoing_calls)==1u && READ(s.outgoing_valid)==1u);
    assert(READ(s.outgoing_reliable)==1u &&
           READ(s.outgoing_unreliable)==0u &&
           READ(s.outgoing_game_bytes)==0x108u);
    assert(shyt_yt_v429_observe_update(&c,&s)==0);
    assert(memcmp(&c,&original,sizeof(c))==0);
    assert(READ(s.update_calls)==1u);

    /* Reliable/unreliable are distinct but both pass original game code. */
    c.arg[1]=0u;c.arg[4]=SHYT_V429_MAX_NATIVE_FRAME;
    assert(shyt_yt_v429_observe_send(&c,&s)==0);
    assert(READ(s.outgoing_unreliable)==1u);
    assert(READ(s.outgoing_valid)==2u);
    assert(READ(s.outgoing_game_bytes)==0x108u+SHYT_V429_MAX_NATIVE_FRAME);

    /* Missing member only flags diagnostic, not a network drop. */
    c.arg[2]=0u;c.arg[4]=SHYT_V429_MIN_NATIVE_FRAME;
    assert(shyt_yt_v429_observe_send(&c,&s)==0);
    assert(READ(s.outgoing_without_member)==1u);
    assert(READ(s.outgoing_valid)==3u);

    /* Never inspect a bogus or future payload pointer. */
    c.arg[3]=0x42u;
    assert(shyt_yt_v429_observe_send(&c,&s)==0);
    c.arg[3]=0x4000000u;c.arg[4]=SHYT_V429_MAX_NATIVE_FRAME+1u;
    assert(shyt_yt_v429_observe_send(&c,&s)==0);
    c.arg[4]=SHYT_V429_MIN_NATIVE_FRAME-1u;
    assert(shyt_yt_v429_observe_send(&c,&s)==0);
    assert(READ(s.outgoing_malformed)==3u);
    assert(READ(s.outgoing_valid)==3u &&
           READ(s.outgoing_calls)==6u);
    assert(shyt_yt_v429_observe_update(NULL,&s)==0);
    assert(READ(s.update_calls)==2u);
    shyt_yt_v429_reset(&s);
    assert(READ(s.outgoing_calls)==0u && READ(s.outgoing_game_bytes)==0u &&
           READ(s.update_calls)==0u && READ(s.outgoing_malformed)==0u);
    puts("SHYT_V429_YT_ORIGINAL_GAME_ABI_PASSIVE_CALL_COUNTERS_PASS");
    return 0;
}
