/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V398: bounded heap-allocated, sealed, immutable native import
 * route; O(log N) exact (target,next) lookup, NO hot-path allocation.
 * Supports up to 8192 source-attested CALL sites, not retail game yet.
 */
#ifndef SHYT_NATIVE_SCALED_IMPORT_V398_H
#define SHYT_NATIVE_SCALED_IMPORT_V398_H
#include "native_verified_import_v395.h"
#ifdef __cplusplus
extern "C" {
#endif
enum { SHYT_V398_MAX_SITES=8192 };
typedef struct ShytNativeScaledRouterV398 {
    ShytNativeOsVmV388 *owner;
    ShytNativeImportSpecV395 *sites;
    size_t count,capacity;
    uint8_t sealed;
} ShytNativeScaledRouterV398;

/* Single-threaded owner setup, initially zeroed. Allocates once BEFORE
 * publication (capacity 1..8192), registers specs and sorts on seal.
 * Do not mutate or free after seal until guest VM is CLOSED,
 * QUIESCENT, and all possible calling threads have been JOINED.
 */
int shyt_native_scaled_init_v398(ShytNativeScaledRouterV398 *router,
    ShytNativeOsVmV388 *owner,size_t capacity);
int shyt_native_scaled_add_v398(ShytNativeScaledRouterV398 *router,
    const ShytNativeImportSpecV395 *site);
int shyt_native_scaled_seal_v398(ShytNativeScaledRouterV398 *router);
/* Controller only, AFTER owner close, V386 quiescence and all-thread
 * join. A live router can't be destroyed while callbacks may run. */
int shyt_native_scaled_release_v398(ShytNativeScaledRouterV398 *router,
    int all_access_threads_joined);
/* Requires genuine pinned RcApi.call under live V390+V393 same-owner
 * scope. Unknown target or wrong continuation cooperatively fails with
 * V395 codes 501/502 and no guest store; accepted site delegates to
 * exactly the original validated V395 implementation. */
void shyt_native_scaled_dispatch_v398(ShytNativeScaledRouterV398 *router,
    BbCpu *cpu,uint64_t target,uint64_t next);
#ifdef __cplusplus
}
#endif
#endif
