/* SPDX-License-Identifier: GPL-2.0-or-later
 * V392: synchronous generated-C native entry scope. Closes V390's
 * normal-return / recoverable-preflight paths and permits nested
 * SAME-owner calls without double-pinning V386 memory.
 *
 * This is NOT safe across longjmp, signals, C++ exceptions crossing C
 * frames, Windows SEH, abort or host thread cancellation. Those remain
 * strict production blockers until they have an explicit unwind design.
 */
#ifndef SHYT_NATIVE_GENERATED_SCOPE_V392_H
#define SHYT_NATIVE_GENERATED_SCOPE_V392_H
#include "native_generated_memory_v390.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct BbCpu BbCpu;
typedef void (*ShytGeneratedFnV392)(BbCpu *);
typedef int (*ShytGeneratedPreflightV392)(const BbCpu *,void *);
typedef struct ShytGeneratedScopeV392 {
    ShytNativeOsVmV388 *owner;
    unsigned state; /* 0 inactive; 1 owns V390 pin; 2 borrows pin */
} ShytGeneratedScopeV392;

/* Single-threaded scope object, zero-initialized. begin uses the V390
 * per-thread lease or borrows an existing lease ONLY for the same owner.
 * Does not allow switching VM owners during nested calls.
 * A borrower cannot end or detach the outer owner's original lease.
 */
int shyt_generated_scope_begin_v392(ShytGeneratedScopeV392 *scope,
                                    ShytNativeOsVmV388 *owner);
int shyt_generated_scope_end_v392(ShytGeneratedScopeV392 *scope);

/* 1: actual RcFn ran then V390 lease was released as appropriate.
 * 0: no call, including invalid args or an optional preflight returning
 * zero. Preflight takes const CPU and must not change guest memory.
 * This catches CONTROLLED, NORMAL C RETURN paths only. It DOES NOT
 * recover from an access violation, abort or non-local unwinding.
 */
int shyt_generated_call_v392(ShytNativeOsVmV388 *owner,
                            ShytGeneratedFnV392 function,
                            BbCpu *cpu,
                            ShytGeneratedPreflightV392 preflight,
                            void *preflight_context);
#ifdef __cplusplus
}
#endif
#endif
