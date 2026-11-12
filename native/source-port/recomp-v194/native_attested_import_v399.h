/* SPDX-License-Identifier: GPL-2.0-or-later
 * V399: bind a build-time source+SHA256 verified generated CALL manifest
 * directly into the scalable V398 sealed runtime import table.
 *
 * The input must come from V396's SOURCE-ATTESTED C header, compiled
 * into native host code. This runtime bridge checks structural closure
 * against the genuine RcFunction table, not cryptographic source hashes.
 * It does not recognize original Bloodborne API/ABI or retail game files.
 */
#ifndef SHYT_NATIVE_ATTESTED_IMPORT_V399_H
#define SHYT_NATIVE_ATTESTED_IMPORT_V399_H
#include "native_scaled_import_v398.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytNativeFunctionProofV399 {
    uint64_t offset;      /* actual emitted RcFunction offset */
    uint64_t size;        /* genuine generated function size */
    const char *hash;     /* nonempty public generator hash */
    uint8_t compiled;     /* genuine RcFunction.fn != NULL */
    uint8_t direct_slot;  /* genuine RcFunction.direct != NULL */
} ShytNativeFunctionProofV399;
typedef struct ShytNativeSourceSiteV399 {
    uint64_t caller_offset;  /* V396 attested function source offset */
    ShytNativeImportSpecV395 import; /* exact attested target + RIP + ABI */
} ShytNativeSourceSiteV399;

/* Single-threaded owner preparation ONLY, before generated functions
 * or host callbacks can use router. Expects zero initialized router.
 * For every site the generated continuation must lie strictly within
 * the identified real compiled function [offset+1,offset+size).
 * Functions must form a sorted, nonoverlapping registry; each source
 * callback pair must be unique. The build-time V396 gate separately
 * proves that EVERY emitted CALL site is declared and the SOURCE SHA256
 * matches; this bridge cannot and does not infer targets dynamically.
 *
 * On success initializes, populates, sorts and seals exactly site_count
 * entries, with zero unrelated synthetic service registrations. Failure
 * leaves router zero when it is owned by this new bootstrap. No guest
 * code, interpreter, OS executable or runtime ELF is loaded.
 */
int shyt_native_bind_attested_v399(ShytNativeScaledRouterV398 *router,
    ShytNativeOsVmV388 *owner,
    const ShytNativeSourceSiteV399 *sites,size_t site_count,
    size_t independently_attested_site_count,
    const ShytNativeFunctionProofV399 *functions,size_t function_count,
    uint64_t image_base);
#ifdef __cplusplus
}
#endif
#endif
