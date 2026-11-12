/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V388: real OS page-backed owner for immutable V386 guest regions.
 * Still a synthetic host VM, NOT a Bloodborne game runtime or game loader.
 */
#ifndef SHYT_NATIVE_OS_VM_V388_H
#define SHYT_NATIVE_OS_VM_V388_H
#include "native_multi_region_vm_v386.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytNativeOsAllocationV388 {
    _Atomic(uint64_t) *words;
    uint64_t guest_base;
    size_t word_count;
    size_t reserved_bytes;
    unsigned permissions;
    uint8_t live;
} ShytNativeOsAllocationV388;
typedef struct ShytNativeOsVmV388 {
    ShytNativeVmV386 vm;
    ShytNativeOsAllocationV388 allocations[SHYT_V386_MAX_REGIONS];
    size_t allocation_count;
    size_t page_size;
    uint8_t initialized,sealed,released;
} ShytNativeOsVmV388;
/* Owner must be zero-initialized and used single-threaded until seal.
 * Page backings use VirtualAlloc/VirtualProtect on Windows and
 * mmap/mprotect on Linux/macOS, with private anonymous pages.
 * All pages are freshly mapped RW for C11 atomic initialization,
 * then protected at seal according to guest permissions:
 * RO or EXECUTE metadata -> host READONLY; W -> host READWRITE.
 * An EXECUTE guest flag never makes memory executable on host.
 * Guest W-only may be host RW because Win32 does not offer reliable
 * distinct write-only allocation; V386 still enforces guest W-only.
 */
int shyt_native_os_vm_init_v388(ShytNativeOsVmV388 *owner);
int shyt_native_os_vm_add_v388(ShytNativeOsVmV388 *owner,
    uint64_t guest_base,size_t atomic_words,unsigned guest_permissions);
int shyt_native_os_vm_seal_v388(ShytNativeOsVmV388 *owner);
/* Obtain the same V386 guest mapping, for native CALL/TAIL and imports.
 * Requires sealed original-free owner; do not pass this to guest code
 * expecting an actual OS process address space. */
ShytNativeVmV386 *shyt_native_os_vm_mapping_v388(ShytNativeOsVmV388 *owner);

/* Widths 1/2/4/8, including crossing two adjacent 64-bit words INSIDE
 * the same OS allocation/guest region. A crossing operation comprises
 * TWO C11 atomic operations and IS NOT atomic as a whole. It only
 * guarantees race-free C11 word accesses and fail-without-write for
 * invalid/unmapped/permission-denied operations. V386 operations made
 * outside this API can also interleave. More CPU/VM work is needed for
 * full x86-64 guest atomic instruction and memory-ordering equivalence.
 * All operations need a held V386 VM lease (pin first, unpin later).
 */
int shyt_native_os_vm_probe_v388(const ShytNativeOsVmV388 *owner,
    const ShytNativeVmLeaseV386 *lease, uint64_t guest_address,
    size_t width, unsigned permissions);
int shyt_native_os_vm_read_v388(const ShytNativeOsVmV388 *owner,
    const ShytNativeVmLeaseV386 *lease,uint64_t guest_address,
    size_t width,uint64_t *value);
int shyt_native_os_vm_write_v388(const ShytNativeOsVmV388 *owner,
    const ShytNativeVmLeaseV386 *lease,uint64_t guest_address,
    size_t width,uint64_t value);
/* Native AOT V382 guest-stack write callback: guest RSP is logical,
 * never an unvalidated native pointer. Uses same V386 OS-backed map. */
int shyt_native_os_vm_stack_write_v388(void *owner,
    uint64_t guest_address,uint64_t return_address);

/* Closing refuses all NEW pins. Existing pinned operations can finish.
 * Release requires close, zero outstanding pins, and explicit owner
 * confirmation that ALL potential calling threads have been JOINED.
 * Caller owns all callbacks; published AOT routes must not refer to
 * freed backing. Do not release an owner used by a live RcApi route.
 * After release owner and map remain closed and cannot be reinitialized.
 */
int shyt_native_os_vm_close_v388(ShytNativeOsVmV388 *owner);
int shyt_native_os_vm_release_v388(ShytNativeOsVmV388 *owner,
    int all_access_threads_joined);
#ifdef __cplusplus
}
#endif
#endif
