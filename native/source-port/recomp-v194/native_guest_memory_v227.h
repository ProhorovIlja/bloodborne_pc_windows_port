/* SPDX-License-Identifier: GPL-2.0-or-later
 * V227 Win64 host-verified guest writable windows for V226 import routing.
 * A window is an explicit owner-approved live guest allocation, NOT any
 * memory merely accessible inside the process.
 */
#ifndef SHYT_NATIVE_GUEST_MEMORY_V227_H
#define SHYT_NATIVE_GUEST_MEMORY_V227_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define SHYT_GUEST_MAX_WINDOWS_V227 32u
typedef struct {
    uint64_t begin; /* inclusive */
    uint64_t end;   /* exclusive */
} ShytGuestWindowV227;
typedef struct {
    ShytGuestWindowV227 windows[SHYT_GUEST_MAX_WINDOWS_V227];
    size_t count;
} ShytGuestMemoryV227;
/* Must be called before worker threads start. Windows must be disjoint,
 * sorted, nonempty and correspond to stable active guest allocations.
 * Caller MUST keep all allocations mapped for lifetime of in-flight calls.
 */
int shyt_guest_memory_v227_init(ShytGuestMemoryV227 *map,
    const ShytGuestWindowV227 *windows, size_t count);
/* Guest address range containment only. Does NOT prove OS page permissions. */
int shyt_guest_memory_v227_contains(const ShytGuestMemoryV227 *map,
    uint64_t address, size_t bytes);
/* V226 callback, write requests ONLY.
 * Win64: additionally checks VirtualQuery committed writable, non-guard
 * pages for the ENTIRE requested span. Other OS: fail closed.
 * This is a point-in-time check, NOT a guarantee against concurrent unmap.
 */
int shyt_guest_memory_v227_permit(void *context, uint64_t address,
    size_t bytes, int write);
#ifdef __cplusplus
}
#endif
#endif
