/* SPDX-License-Identifier: GPL-2.0-or-later
 * V406: pinned generated synthetic TCB, memory and typed import admission.
 * NOT a Bloodborne runtime, not a PS4 EBOOT loader, not game call coverage.
 * The producer and all registry pointers must stay alive while bound.
 * Single-controller bind; execute requires sealed pinned V388 VM.
 */
#ifndef SHYT_NATIVE_ROUTE_EXECUTION_V404_H
#define SHYT_NATIVE_ROUTE_EXECUTION_V404_H
#include "recomp/rc.h"
#include "native_host_recovery_v393.h"
#ifdef __cplusplus
extern "C" {
#endif

enum { SHYT_V404_DENIED = 0, SHYT_V404_COMPLETED = 1 };
enum { SHYT_V404_SYNTHETIC_FUNCTIONS = 11 };
typedef struct ShytNativeExecutionV404 {
    ShytNativeOsVmV388 *owner;
    const RcFunction *table;
    RcFn approved[SHYT_V404_SYNTHETIC_FUNCTIONS];
    RcFn *direct[SHYT_V404_SYNTHETIC_FUNCTIONS];
    unsigned bound;
} ShytNativeExecutionV404;

/* Full 11-function SHA-derived offset/size/hash + direct slot match
 * is required before ANY dispatch. The pinned 11-entry synthetic corpus is admitted.
 * A successful bind never permits adding entries or changing owner.
 */
int shyt_native_execution_bind_v404(ShytNativeExecutionV404 *out,
    ShytNativeOsVmV388 *owner, const RcFunction *compiled, size_t count);

/* Deny unknown offsets, the unsupported STEP 0x1140, unknown import targets or
 * continuations, bad stack or operands, nested entry and changed registry.
 * Preflight denial calls no generated code. Typed callback denial may
 * follow register materialization but precedes service writes. On success
 * the real pinned-generated RcFn ran through V393 and returned with
 * validated guest RSP/RIP. Abnormal host exits and abort() are NOT
 * recoverable; release/join remains caller responsibility. The caller
 * must exclusively own the CPU and return slot during the call, and
 * keep the registry and direct slots stable while executing.
 */
int shyt_native_execution_try_v404(ShytNativeExecutionV404 *route,
    uint64_t function_offset, BbCpu *cpu);

/* Install as RcApi.call for this pinned generated module (image base
 * 0x400000). The RcApi must stay live and immutable after init. */
void shyt_native_execution_call_v406(BbCpu *cpu, uint64_t target,
                                     uint64_t next);
#ifdef __cplusplus
}
#endif
#endif
