/* SPDX-License-Identifier: GPL-2.0-or-later
 * V382: 64-bit native-only indirect CALL/TAIL dispatch for pinned RcApi v4.
 * Synthetic tests; not a complete original-game native runtime.
 */
#ifndef SHYT_NATIVE_AOT_ROUTE_V382_H
#define SHYT_NATIVE_AOT_ROUTE_V382_H
#include "native_strict_aot_v381.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef int (*ShytNativeAotStackWriteV382)(
    void *ctx, uint64_t stack_address, uint64_t return_address);
/* Stack write callback MUST validate the mapped writable stack and
 * commit the 8-byte store atomically with x86 guest memory ordering, OR
 * fail without writes. The dispatcher does not dereference guest memory.
 * The actual native game still needs a memory lease/pin implementation. */
typedef struct ShytNativeAotEntryV382 {
    uint64_t address;
    RcFn function;
} ShytNativeAotEntryV382;
typedef struct ShytNativeAotRouteV382 {
    ShytNativeAotEntryV382 *entries;
    size_t count;
    uint64_t image_base;
    ShytNativeAotStackWriteV382 stack_write;
    void *stack_context;
    uint8_t ready, published;
} ShytNativeAotRouteV382;
/* Requires a V381-admitted complete SUPPLIED table, not a raw RcFunction
 * registration; snapshots native function addresses. The V381 proof alone
 * does not demonstrate that the original game has 100% AOT coverage.
 * Caller must retain immutable route for process life after publishing. */
int shyt_native_aot_prepare_v382(
    ShytNativeAotRouteV382 *route,
    const RcApi *strict_base,
    const RcFunction *functions, size_t count,
    const ShytStrictAotProofV381 *admission,
    ShytNativeAotStackWriteV382 stack_write, void *stack_context);
/* The result is a function pointer or NULL, NEVER an interpreter route. */
RcFn shyt_native_aot_lookup_v382(const ShytNativeAotRouteV382 *route,
                                 uint64_t absolute_address);
/* Try dispatch: return 0 on unknown target/invalid stack/write refusal,
 * without changing the CPU registers. Success invokes native RcFn, which
 * is responsible for its own RET/pop and cpu->rip return semantics. */
int shyt_native_aot_try_call_v382(const ShytNativeAotRouteV382 *route,
                                  BbCpu *cpu, uint64_t target, uint64_t next);
int shyt_native_aot_try_tail_v382(const ShytNativeAotRouteV382 *route,
                                  BbCpu *cpu);
/* Permanently install this ONE immutable route into RcApi callbacks.
 * Must run exactly once in a process BEFORE game worker threads.
 * Any missing/invalid target in the installed callbacks ABORTS; no
 * runtime guest translator or PS4 interpreter can be reached.
 * step/bail remain V381 trap callbacks. Real native import dispatch
 * and indirect function coverage are additional required work. */
int shyt_native_aot_publish_v382(
    ShytNativeAotRouteV382 *route, const RcApi *strict_base,
    RcApi *out);
/* Reclaim an UNPUBLISHED route only. No hot reload/unload. */
int shyt_native_aot_dispose_v382(ShytNativeAotRouteV382 *route);
#ifdef __cplusplus
}
#endif
#endif
