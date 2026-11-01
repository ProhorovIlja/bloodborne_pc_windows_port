/* SPDX-License-Identifier: GPL-2.0-or-later
 * V228 Windows OWNER of committed guest allocations and lifetime locks.
 * Only this owner can release/change protections while the game runs.
 * Not a full engine allocator, and not a complete game memory map.
 */
#ifndef SHYT_NATIVE_GUEST_ARENA_V228_H
#define SHYT_NATIVE_GUEST_ARENA_V228_H
#if !defined(_WIN64)
#error V228 guest arena is Win64-only; never simulate its memory guarantees
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "native_guest_memory_v227.h"

typedef struct {
    SRWLOCK lifetime_lock;
    void *base;
    size_t size;
    int live;
    ShytGuestMemoryV227 writable_window;
} ShytGuestArenaV228;

/* Single-thread initialization, caller supplies ZERO-initialized stable
 * arena. Arena object must outlive all possible callers, including teardown.
 * Pages are reserved and committed together, initially PAGE_READWRITE.
 */
int shyt_guest_arena_v228_create(ShytGuestArenaV228 *arena, size_t bytes);

/* A successful pin holds shared lock until unpin on the SAME thread.
 * Nested pins are forbidden; ensure all code paths unpin including errors.
 * No VirtualFree/VirtualProtect on arena memory outside this module.
 */
int shyt_guest_arena_v228_pin(ShytGuestArenaV228 *arena);
int shyt_guest_arena_v228_unpin(ShytGuestArenaV228 *arena);

/* ShytGuestMemoryPermit callback; only valid on a thread currently pinned
 * to this same arena. Enforces owner window AND live Win32 page protection.
 */
int shyt_guest_arena_v228_permit_pinned(void *arena, uint64_t addr,
                                      size_t bytes, int write);

/* Exclusive operations wait for every active pin to leave. Protect permits
 * only PAGE_READWRITE, PAGE_READONLY or PAGE_NOACCESS. */
int shyt_guest_arena_v228_protect(ShytGuestArenaV228 *arena,
                                 size_t offset, size_t bytes, DWORD protect);
int shyt_guest_arena_v228_destroy(ShytGuestArenaV228 *arena);
#endif
