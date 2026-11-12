/* SPDX-License-Identifier: GPL-2.0-or-later
 * V385: one pinned bounded logical guest memory path for native AOT
 * stack and native-only math/clock imports. Public synthetic host only.
 */
#ifndef SHYT_NATIVE_GUEST_VM_V385_H
#define SHYT_NATIVE_GUEST_VM_V385_H
#include "native_pinned_stack_v383.h"
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef struct ShytGuestVmV385 {
    ShytNativeStackV383 *stack;
    uint8_t ready;
} ShytGuestVmV385;
typedef struct ShytGuestVmLeaseV385 {
    ShytGuestVmV385 *vm;
    uint8_t active;
} ShytGuestVmLeaseV385;

/* The backing MUST be initialized C11 atomic 64-bit words as required
 * by V383 and remain stable while the owner runs/joins its threads.
 * This mapping is intentionally one region, NOT full game paging/MMU.
 */
int shyt_guest_vm_init_v385(ShytGuestVmV385 *vm,
                            ShytNativeStackV383 *stack);
int shyt_guest_vm_pin_v385(ShytGuestVmV385 *vm,
                           ShytGuestVmLeaseV385 *lease);
int shyt_guest_vm_unpin_v385(ShytGuestVmLeaseV385 *lease);

/* All ops require a LIVE lease held by the calling thread. Supported
 * widths 1,2,4,8 little-endian bytes in one aligned atomic 64-bit
 * backing word. Unaligned subword operations work within that word.
 * An unaligned or crossing-boundary 8-byte access, and any smaller
 * access crossing a backing word, FAIL WITHOUT SIDE EFFECTS. This
 * limitation must be lifted with real game VM before production.
 * All read/write participants MUST use these C11 atomics; mixing raw
 * unsynchronized accesses causes undefined behavior.
 */
int shyt_guest_vm_probe_v385(const ShytGuestVmLeaseV385 *lease,
                             uint64_t address, size_t width);
int shyt_guest_vm_write_v385(const ShytGuestVmLeaseV385 *lease,
                             uint64_t address, size_t width, uint64_t value);
int shyt_guest_vm_read_v385(const ShytGuestVmLeaseV385 *lease,
                            uint64_t address, size_t width, uint64_t *value);

/* Direct V382 stack-write callback: uses same VM map as guest imports. */
int shyt_guest_vm_stack_write_v385(void *context,
                                   uint64_t guest_address, uint64_t value);
#ifdef __cplusplus
}
#endif
#endif
