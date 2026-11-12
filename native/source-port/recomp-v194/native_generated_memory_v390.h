/* SPDX-License-Identifier: GPL-2.0-or-later
 * V390: AOT-generated source access to one V389/V388 owner VM.
 * Any guest-memory access without an active per-thread lease ABORTS.
 * Original-free synthetic recompiler test, NOT game parity.
 */
#ifndef SHYT_NATIVE_GENERATED_MEMORY_V390_H
#define SHYT_NATIVE_GENERATED_MEMORY_V390_H
#include "native_os_vm_v388.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Bracket generated RcFn calls with enter/leave, including generated
 * direct calls and indirect native-only V382 CALL/TAIL on SAME thread.
 * No nested enter, no longjmp/exception past leave, no hot unload.
 * Every original generated execution entrypoint MUST be wrapped.
 */
int shyt_generated_enter_v390(ShytNativeOsVmV388 *owner);
int shyt_generated_leave_v390(void);
int shyt_generated_active_v390(void);
/* Read-only identity for nested, same-thread scoped wrappers. NULL if no pin. */
ShytNativeOsVmV388 *shyt_generated_owner_v392(void);

/* Safe diagnostics return 0 (without mutation) on bad/missing mapping.
 * All returned values are 64-bit zero extended; width must be 1/2/4/8.
 * Accesses may cross one 64-bit word inside a single guest region,
 * but are NOT one atomic transaction when they do.
 */
int shyt_generated_try_load_v390(uint64_t address,int size,uint64_t *out);
int shyt_generated_try_store_v390(uint64_t address,int size,uint64_t value);
int shyt_generated_try_probe_v390(uint64_t address,size_t bytes,
                                 unsigned permission);

/* Wrappers emitted into actual pinned bbrecomp generated C shards by
 * instrument_generated_aot_memory_v390.py. These never interpret
 * uint64_t guest address as an arbitrary native host pointer.
 * Rejected memory reads/writes/CAS ABORT immediately, not translator.
 */
uint64_t shyt_generated_ld_v390(uint64_t address,int size);
void shyt_generated_st_v390(uint64_t address,int size,uint64_t value);
int shyt_generated_cas_v390(uint64_t address,int size,
    uint64_t expected,uint64_t desired,uint64_t *seen);
#ifdef __cplusplus
}
#endif
#endif
