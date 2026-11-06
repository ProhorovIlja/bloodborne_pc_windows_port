/* SPDX-License-Identifier: GPL-3.0-or-later
 * V429 experimental, disabled-by-default original Bloodborne 1.09
 * GameLink send and NetSyncUpdate CALL-ONLY counters for BBHost.
 *
 * YT v1.4.0 source emulator/src/core/bloodborne_patches.cpp:
 *   TakeGamePacket: rcx=packet, rdx=member, rsi=reliability, r8=size.
 *   DeliverAtNetSyncUpdate: counts call cadence only, no guest writes.
 * BBHost v0.2.24 GUEST_ABI hook_dispatch:
 *   BbHookCtx.arg[0..5] = rdi, rsi, rdx, rcx, r8, r9.
 * No packet payload read, queue action, game change or network socket.
 * Both callbacks always return 0, allowing original guest functions
 * to continue unchanged. This is NOT co-op, NetSync receive/apply or
 * measured WAN bandwidth. All counters lock-free and relaxed.
 */
#ifndef SHYT_YT_GAME_LINK_OBSERVER_V429_H
#define SHYT_YT_GAME_LINK_OBSERVER_V429_H
#include "bbhost_plugin.h"
#include <stdint.h>
#include <stdatomic.h>

enum { SHYT_V429_MIN_NATIVE_FRAME=8u, SHYT_V429_MAX_NATIVE_FRAME=0x6408u };
typedef struct ShytYtGameLinkObserverV429 {
    atomic_ullong outgoing_calls;
    atomic_ullong outgoing_valid;
    atomic_ullong outgoing_malformed;
    atomic_ullong outgoing_without_member;
    atomic_ullong outgoing_reliable;
    atomic_ullong outgoing_unreliable;
    atomic_ullong outgoing_game_bytes;
    atomic_ullong update_calls;
} ShytYtGameLinkObserverV429;

static inline void shyt_yt_v429_reset(ShytYtGameLinkObserverV429* s) {
    if (!s) return;
    atomic_store_explicit(&s->outgoing_calls,0u,memory_order_relaxed);
    atomic_store_explicit(&s->outgoing_valid,0u,memory_order_relaxed);
    atomic_store_explicit(&s->outgoing_malformed,0u,memory_order_relaxed);
    atomic_store_explicit(&s->outgoing_without_member,0u,memory_order_relaxed);
    atomic_store_explicit(&s->outgoing_reliable,0u,memory_order_relaxed);
    atomic_store_explicit(&s->outgoing_unreliable,0u,memory_order_relaxed);
    atomic_store_explicit(&s->outgoing_game_bytes,0u,memory_order_relaxed);
    atomic_store_explicit(&s->update_calls,0u,memory_order_relaxed);
}

static inline int shyt_yt_v429_observe_send(
    BbHookCtx* ctx,void* user) {
    ShytYtGameLinkObserverV429* s=(ShytYtGameLinkObserverV429*)user;
    if (!s) return 0;
    atomic_fetch_add_explicit(&s->outgoing_calls,1u,memory_order_relaxed);
    if (!ctx) {
        atomic_fetch_add_explicit(&s->outgoing_malformed,1u,memory_order_relaxed);
        return 0;
    }
    /* Do NOT dereference ctx->arg[3]. That packet pointer might not be
     * resident during a load, and reading payload has no approval. */
    const uint64_t packet=ctx->arg[3]; // original game's rcx
    const uint64_t member=ctx->arg[2]; // original game's rdx
    // Original TakeGamePacket casts both registers to u32; their
    // upper halves are NOT part of the guest call's logical values.
    const uint32_t reliability=(uint32_t)ctx->arg[1]; // rsi low 32
    const uint32_t size=(uint32_t)ctx->arg[4]; // r8 low 32
    if (packet<0x10000u || size<SHYT_V429_MIN_NATIVE_FRAME ||
        size>SHYT_V429_MAX_NATIVE_FRAME) {
        atomic_fetch_add_explicit(&s->outgoing_malformed,1u,memory_order_relaxed);
        return 0;
    }
    atomic_fetch_add_explicit(&s->outgoing_valid,1u,memory_order_relaxed);
    /* Native game packet bytes at this site, not actual wire/relay bytes. */
    atomic_fetch_add_explicit(&s->outgoing_game_bytes,(unsigned long long)size,
                              memory_order_relaxed);
    if (member<0x10000u)
        atomic_fetch_add_explicit(&s->outgoing_without_member,1u,
                                  memory_order_relaxed);
    if (reliability)
        atomic_fetch_add_explicit(&s->outgoing_reliable,1u,memory_order_relaxed);
    else
        atomic_fetch_add_explicit(&s->outgoing_unreliable,1u,memory_order_relaxed);
    return 0;
}
static inline int shyt_yt_v429_observe_update(BbHookCtx* ctx,void* user) {
    (void)ctx;
    ShytYtGameLinkObserverV429* s=(ShytYtGameLinkObserverV429*)user;
    if (s) atomic_fetch_add_explicit(&s->update_calls,1u,memory_order_relaxed);
    return 0;
}
#endif
