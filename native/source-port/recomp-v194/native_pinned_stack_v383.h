/* SPDX-License-Identifier: GPL-2.0-or-later
 * V383: bounded, pinned host-backed 64-bit guest stack memory.
 * A synthetic source-port component, NOT proof of whole-game memory parity.
 */
#ifndef SHYT_NATIVE_PINNED_STACK_V383_H
#define SHYT_NATIVE_PINNED_STACK_V383_H
#include <stddef.h>
#include <stdint.h>
#include <stdatomic.h>
#ifdef __cplusplus
extern "C" {
#endif
enum { SHYT_V383_MAX_STACK_WORDS=1048576 };
typedef struct ShytNativeStackV383 {
    _Atomic(uint32_t) leases_and_closing; /* top bit closing; rest active pins */
    _Atomic(uint64_t) *backing;
    uint64_t guest_base;
    size_t word_count;
    uint8_t ready;
} ShytNativeStackV383;

/* Initialize before starting workers, exactly once, from a ZEROED state.
 * Backing MUST be a live array of initialized _Atomic(uint64_t) values
 * whose owner promises to keep it mapped/writable until AFTER close,
 * quiescence, and joining every thread that might use this state.
 * A guest address is NOT treated as a raw host pointer.
 * Does NOT perform OS VM mapping, probe arbitrary caller pointers, own/free
 * backing memory, or permit backing relocation during active use.
 */
int shyt_native_stack_init_v383(ShytNativeStackV383 *stack,
    _Atomic(uint64_t) *backing, size_t words, uint64_t guest_base);

/* Explicit bounded pin for the native memory lease protocol.
 * Closing blocks new leases. The owner must release each successful pin.
 * Use these from future game memory consumers sharing the same region. */
int shyt_native_stack_pin_v383(ShytNativeStackV383 *stack);
int shyt_native_stack_unpin_v383(ShytNativeStackV383 *stack);

/* Validated 8-byte stores / reads with C11 release/acquire ordering.
 * Reject failures without modifying backing. The writer matches the
 * V382 stack_write callback signature (ctx, address, return_address).
 * Only atomic operations participating in this same memory model can
 * establish portable data-race-free cross-thread access.
 */
int shyt_native_stack_write_v383(void *context, uint64_t address,
                                 uint64_t value);
int shyt_native_stack_read_v383(ShytNativeStackV383 *stack,
                                uint64_t address, uint64_t *out);

/* Close blocks all NEW pins, but existing operations may still finish.
 * Once quiescent, join worker threads before unmapping/freeing backing
 * or the stack state. NEVER unmap while callbacks may still run.
 * State is NOT reset/reusable after closing. */
int shyt_native_stack_close_v383(ShytNativeStackV383 *stack);
int shyt_native_stack_quiescent_v383(const ShytNativeStackV383 *stack);
#ifdef __cplusplus
}
#endif
#endif
