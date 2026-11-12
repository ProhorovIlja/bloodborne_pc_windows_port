/* SPDX-License-Identifier: GPL-2.0-or-later
 * V389: controller-only quiescent reconfiguration of V388 OS-backed VM.
 * Synthetic original-free host infrastructure, NOT real game MMU parity.
 */
#ifndef SHYT_NATIVE_OS_VM_RECONFIGURE_V389_H
#define SHYT_NATIVE_OS_VM_RECONFIGURE_V389_H
#include "native_os_vm_v388.h"
#ifdef __cplusplus
extern "C" {
#endif

/* PAUSE succeeds only with ZERO pinned V386 leases, a sealed owner,
 * and no existing pause/close. Fails immediately, never spins/waits.
 * It atomically gates all subsequent V386 pins until RESUME.
 *
 * The owner MUST serialize ALL V389 control calls in ONE control thread.
 * Every user of region metadata and backing MUST hold a V386 lease,
 * including generated native AOT adapters. Direct/unsynchronized raw
 * pointers outside leases invalidate this safety contract.
 * A live published RcApi keeps the V388 owner and this VM alive.
 */
int shyt_native_os_vm_pause_v389(ShytNativeOsVmV388 *owner);
int shyt_native_os_vm_resume_v389(ShytNativeOsVmV388 *owner);

/* All mutations require PAUSED owner; no thread has a V386 pin then.
 * New page mappings are native Windows VirtualAlloc / POSIX mmap, all
 * C11 atomic backing words are initialized, and OS mprotect/
 * VirtualProtect is applied before region publication.
 * Sorted guest regions, non-overlap, no RWX and bounded counts preserved.
 *
 * Reprotect: changes BOTH V386 logical R/W/X and OS READONLY/READWRITE.
 * Guest EXECUTE never means host executable permissions. No mid-call
 * access can race a valid pinned lease, since PAUSE rejects live pins.
 *
 * Remap: replace a full region's host page allocation while keeping its
 * guest address/size/permissions stable. Optionally COPY all atomically
 * read 64-bit words or zero initialize. A stale external pointer is not
 * protected: owner must not cache backing addresses outside leases.
 *
 * Add/remove: guest region membership may change only during PAUSE;
 * old mappings are unmapped only when no lease can hold a pointer.
 * No original game files or guest executable pages are loaded.
 */
int shyt_native_os_vm_map_v389(ShytNativeOsVmV388 *owner,
    uint64_t guest_base, size_t atomic_words, unsigned permissions);
int shyt_native_os_vm_reprotect_v389(ShytNativeOsVmV388 *owner,
    uint64_t guest_base, unsigned permissions);
int shyt_native_os_vm_remap_v389(ShytNativeOsVmV388 *owner,
    uint64_t guest_base, int preserve_contents);
int shyt_native_os_vm_unmap_v389(ShytNativeOsVmV388 *owner,
    uint64_t guest_base);

#ifdef __cplusplus
}
#endif
#endif
