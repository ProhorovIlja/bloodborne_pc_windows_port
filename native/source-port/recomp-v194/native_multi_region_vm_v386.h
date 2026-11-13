/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V386: immutable multi-region bounded guest VM + atomic lease.
 * No PS4 executable, translation runtime, retail game or OS VM in CI.
 */
#ifndef SHYT_NATIVE_MULTI_REGION_VM_V386_H
#define SHYT_NATIVE_MULTI_REGION_VM_V386_H
#include <stdatomic.h>
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* 128 MiB per region: the observed startup allocation alone is 116 MiB.
 * This is a validation ceiling, not an eager reservation. */
enum { SHYT_V386_MAX_REGIONS=32, SHYT_V386_MAX_WORDS=16777216 };
enum { SHYT_V386_READ=1, SHYT_V386_WRITE=2, SHYT_V386_EXECUTE=4 };
typedef struct ShytNativeRegionV386 {
    uint64_t guest_base;
    _Atomic(uint64_t) *words;
    size_t word_count;
    uint8_t permissions;
} ShytNativeRegionV386;
typedef struct ShytNativeVmV386 {
    _Atomic(uint32_t) pins_and_closing; /* high bit is irreversible close */
    ShytNativeRegionV386 regions[SHYT_V386_MAX_REGIONS];
    size_t region_count;
    uint8_t sealed;
} ShytNativeVmV386;
typedef struct ShytNativeVmLeaseV386 {
    ShytNativeVmV386 *vm;
    uint8_t live;
} ShytNativeVmLeaseV386;

/* Single-threaded owner setup ONLY, on zero-initialized struct.
 * Regions are ordered, nonoverlapping guest intervals and MUST NOT
 * alias the same host atomic array. W^X is enforced. All backing is
 * caller-owned and stays mapped until close + quiescence + thread JOIN.
 * EXECUTE only describes a permission; no code can execute here.
 */
int shyt_native_vm_add_region_v386(ShytNativeVmV386 *vm,
    uint64_t guest_base, _Atomic(uint64_t) *words, size_t word_count,
    unsigned permissions);
int shyt_native_vm_seal_v386(ShytNativeVmV386 *vm);

/* Thread-safe pins after seal. Mapping remains immutable in normal use;
 * V389 adds a controller-only, zero-active-pin PAUSE for safe remapping.
 * A successful lease must be released.
 * Close denies new leases; owner must additionally JOIN every thread
 * which might access these structures before unmapping/backing free.
 */
int shyt_native_vm_pin_v386(ShytNativeVmV386 *vm,
    ShytNativeVmLeaseV386 *lease);
int shyt_native_vm_unpin_v386(ShytNativeVmLeaseV386 *lease);
int shyt_native_vm_close_v386(ShytNativeVmV386 *vm);
int shyt_native_vm_quiescent_v386(const ShytNativeVmV386 *vm);

/* Atomic little-endian 1/2/4/8 within a single aligned 64-bit backing
 * word. Cross-word accesses are rejected *without mutation*. This is
 * deliberate: real original game requires safe cross-word accesses and
 * page protections before this can be called full guest VM parity.
 * All participants must use compatible C11 atomic memory operations.
 */
int shyt_native_vm_probe_v386(const ShytNativeVmLeaseV386 *lease,
    uint64_t guest_address, size_t width, unsigned needed_permissions);
int shyt_native_vm_read_v386(const ShytNativeVmLeaseV386 *lease,
    uint64_t guest_address, size_t width, uint64_t *value);
int shyt_native_vm_write_v386(const ShytNativeVmLeaseV386 *lease,
    uint64_t guest_address, size_t width, uint64_t value);

/* Native V382 stack_write callback for AOT-only indirect calls. */
int shyt_native_vm_stack_write_v386(void *vm,
    uint64_t guest_address, uint64_t return_address);

#ifdef __cplusplus
}
#endif
#endif
