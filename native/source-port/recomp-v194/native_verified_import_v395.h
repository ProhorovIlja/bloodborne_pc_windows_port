/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V395: sealed source-verified synthetic RcApi.call import router.
 *
 * Original-free proof of real generated CALL RAX -> permission-checked
 * imported host service, NOT full original Bloodborne host imports.
 * Router has no PS4 interpreter or unverified address fallback.
 */
#ifndef SHYT_NATIVE_VERIFIED_IMPORT_V395_H
#define SHYT_NATIVE_VERIFIED_IMPORT_V395_H
#include "native_host_recovery_v393.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
enum {
    SHYT_V395_MAX_IMPORTS=16
};
enum {
    SHYT_V395_RETURN_VALUE=1, /* RAX constant, no guest memory */
    SHYT_V395_ADD_GUEST_QWORDS=2, /* *(RDI)+*(RSI) -> *(RDX); RAX=sum */
    SHYT_V395_COOPERATIVE_FAILURE=3 /* explicit V393 recovery, no mutation */
};
enum {
    SHYT_V395_REC_UNKNOWN=501,
    SHYT_V395_REC_CONTINUATION=502,
    SHYT_V395_REC_GUEST_PERMISSIONS=503
};
/* Each import has an exact 64-bit address and exact generated-C
 * continuation RIP. Using a different generated call site with an
 * unregistered next address is a recoverable failure, not a redirect.
 * The pure synthetic services below are intentionally fixed; no
 * untrusted function pointers or arbitrary raw host pointer calls.
 */
typedef struct ShytNativeImportSpecV395 {
    uint64_t guest_target;
    uint64_t expected_next;
    uint32_t service;
    uint32_t recover_code; /* valid only for cooperative-failure service */
    uint64_t constant; /* valid only for return-value service */
} ShytNativeImportSpecV395;
typedef struct ShytNativeImportRouterV395 {
    ShytNativeOsVmV388 *owner; /* must remain mapped for all executions */
    ShytNativeImportSpecV395 spec[SHYT_V395_MAX_IMPORTS];
    size_t count;
    uint8_t sealed;
} ShytNativeImportRouterV395;

/* All router setup occurs on one owner controller BEFORE any AOT worker
 * begins. A sealed router is immutable and owner-managed for the entire
 * lifetime of all native callback invocations. No concurrent mutation. */
int shyt_native_import_init_v395(ShytNativeImportRouterV395 *router,
    ShytNativeOsVmV388 *owner);
int shyt_native_import_add_v395(ShytNativeImportRouterV395 *router,
    const ShytNativeImportSpecV395 *spec);
int shyt_native_import_seal_v395(ShytNativeImportRouterV395 *router);

/* Called only through registered RcApi.call with an active V390/V392/
 * V393 same-thread scoped owner lease. Never returns on routing/guest
 * validation error: explicitly cooperative V393 recovery instead.
 * An unregistered address / wrong next / RO or unmapped output cannot
 * run any service or change guest memory. No interpreter fallback.
 */
void shyt_native_import_dispatch_v395(ShytNativeImportRouterV395 *router,
    BbCpu *cpu,uint64_t guest_target,uint64_t next);

/* V398 shared-service bridge: preserves V395 exact host-service memory,
 * CPU and V393 recovery semantics without 8192 copied singleton routers.
 * Only native host code may invoke this; it requires an active V390
 * same-owner lease and a V393 cooperative recovery checkpoint. It
 * rechecks (guest_target, continuation) against the supplied immutable
 * site spec, then performs the same bounded V395 synthetic service.
 */
int shyt_native_import_spec_valid_v398(const ShytNativeImportSpecV395 *spec);
void shyt_native_import_dispatch_site_v398(ShytNativeOsVmV388 *owner,
    const ShytNativeImportSpecV395 *spec,BbCpu *cpu,
    uint64_t guest_target,uint64_t next);

#ifdef __cplusplus
}
#endif
#endif
