/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V393: explicit, cooperative same-thread host checkpoint for a
 * generated RcFn. Permits a trusted preflight/host callback to return
 * control to a pinned entry wrapper without leaking its V390 VM lease.
 *
 * NOT recovery from SIGSEGV, SIGABRT, arbitrary C longjmp, SEH, host
 * C++ exceptions, pthread cancellation or async signals. These remain
 * unsupported in production, and must never be claimed as safe.
 */
#ifndef SHYT_NATIVE_HOST_RECOVERY_V393_H
#define SHYT_NATIVE_HOST_RECOVERY_V393_H
#include "native_generated_scope_v392.h"
#ifdef __cplusplus
extern "C" {
#endif

enum {
    SHYT_V393_DENIED=0,    /* validation or VM pin failed; no generated call */
    SHYT_V393_COMPLETED=1, /* genuine generated RcFn returned normally */
    SHYT_V393_RECOVERED=2  /* explicitly requested cooperative host escape */
};
/* Synchronous host-owned generated AOT call, valid scope released on both
 * normal and explicitly requested cooperative-recovery paths.
 * A permitted preflight callback may call shyt_generated_raise_v393().
 * For a generated RcFn to use this, it must reach a TRUSTED same-thread
 * host callback which deliberately calls raise_v393; it cannot directly
 * call arbitrary longjmp and cannot unwind foreign resource owners.
 * Optional recovery_code output is 0 except for RECOVERED.
 */
int shyt_generated_call_recoverable_v393(
    ShytNativeOsVmV388 *owner, ShytGeneratedFnV392 function,
    BbCpu *cpu, ShytGeneratedPreflightV392 preflight,void *ctx,
    int *recovery_code);
/* Only call from trusted synchronous host callbacks with a currently
 * active V393 entry in this SAME thread, while no unmanaged resources,
 * locks, nontrivial C++ objects or other nonlocal-unwind state exist in
 * skipped frames. No return. Incorrect use is fatal: no silent fallback.
 */
_Noreturn void shyt_generated_raise_v393(int code);
unsigned shyt_generated_recovery_depth_v393(void);
#ifdef __cplusplus
}
#endif
#endif
