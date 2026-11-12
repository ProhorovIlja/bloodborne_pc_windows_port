/* SPDX-License-Identifier: GPL-2.0-or-later
 * V397: multiple source-attested return RIPs may share ONE native import.
 * Each (guest_target, expected_next) pair is an exact authorization.
 * This owner-controlled router composes V395 per-site sealed services;
 * it does not admit guest interpreter or arbitrary host function pointers.
 */
#ifndef SHYT_NATIVE_SHARED_IMPORT_V397_H
#define SHYT_NATIVE_SHARED_IMPORT_V397_H
#include "native_verified_import_v395.h"
#ifdef __cplusplus
extern "C" {
#endif
enum { SHYT_V397_MAX_SITES=SHYT_V395_MAX_IMPORTS };
typedef struct ShytNativeSharedRouterV397 {
    ShytNativeOsVmV388 *owner;
    ShytNativeImportSpecV395 entries[SHYT_V397_MAX_SITES];
    ShytNativeImportRouterV395 routes[SHYT_V397_MAX_SITES];
    size_t count;
    uint8_t sealed;
} ShytNativeSharedRouterV397;

/* Single controller only, before native worker threads begin.
 * Duplicate (target,next) pairs are rejected. Reused targets must
 * have identical service type, cooperative failure code and constant.
 * No editing or freeing router, VM or generated entries while live.
 */
int shyt_native_shared_init_v397(ShytNativeSharedRouterV397 *router,
    ShytNativeOsVmV388 *owner);
int shyt_native_shared_add_v397(ShytNativeSharedRouterV397 *router,
    const ShytNativeImportSpecV395 *site);
int shyt_native_shared_seal_v397(ShytNativeSharedRouterV397 *router);

/* The actual pinned bbrecomp-generated RcApi.call invokes this while
 * V393 has a live cooperative frame and V390 holds the SAME owner lease.
 * Unknown target -> V395_REC_UNKNOWN; known target but unregistered
 * next -> V395_REC_CONTINUATION, both before guest memory mutation.
 */
void shyt_native_shared_dispatch_v397(ShytNativeSharedRouterV397 *router,
    BbCpu *cpu,uint64_t target,uint64_t next);
#ifdef __cplusplus
}
#endif
#endif
