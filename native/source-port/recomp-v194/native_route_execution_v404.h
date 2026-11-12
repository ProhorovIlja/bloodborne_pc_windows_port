/* SPDX-License-Identifier: GPL-2.0-or-later
 * V404: real pinned-compiler GENERATED synthetic TCB execution admission.
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
 * is required before ANY dispatch. Only four independently tested
 * FS/GS synthetic TCB MOV/RET functions are admitted for execution.
 * A successful bind never permits adding entries or changing owner.
 */
int shyt_native_execution_bind_v404(ShytNativeExecutionV404 *out,
    ShytNativeOsVmV388 *owner, const RcFunction *compiled, size_t count);

/* Deny unknown offsets, the unsupported STEP 0x1140, the seven
 * other untested synthetic candidates, malformed guest stack and
 * changed registry. On denial no generated C is called. On success
 * the real pinned-generated RcFn ran through V393 and returned with
 * validated guest RSP/RIP. Abnormal host exits and abort() are NOT
 * recoverable; release/join remains caller responsibility.
 */
int shyt_native_execution_try_v404(ShytNativeExecutionV404 *route,
    uint64_t function_offset, BbCpu *cpu);
#ifdef __cplusplus
}
#endif
#endif
