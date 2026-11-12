/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V400: require independent exact 64-bit function hashes, sizes
 * and offsets BEFORE V399/V398 router publication.
 *
 * The EXPECTED array is generated only by verifying a pinned compiler,
 * SHA256-locked invented input image bytes and genuine bbrecomp table.
 * No original Bloodborne code, source or runtime PS4 ELF is involved.
 */
#ifndef SHYT_NATIVE_EXACT_IDENTITY_V400_H
#define SHYT_NATIVE_EXACT_IDENTITY_V400_H
#include "native_attested_import_v399.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytNativeExpectedFunctionV400 {
    uint64_t offset;
    uint64_t size;
    uint64_t hash;
} ShytNativeExpectedFunctionV400;
/* The independently expected table MUST cover exactly ALL actual
 * compiled RcFunction entries and have equal offset/size/hash values.
 * Every target/return site then passes the existing V399 structural
 * and V395 guest permission checks. Failure must leave router empty
 * and must not allocate a native import table.
 * Single-controller initialization only, with zeroed router.
 */
int shyt_native_bind_exact_v400(ShytNativeScaledRouterV398 *router,
    ShytNativeOsVmV388 *owner,
    const ShytNativeSourceSiteV399 *sites,size_t site_count,
    size_t independently_attested_site_count,
    const ShytNativeFunctionProofV399 *actual,size_t actual_count,
    const ShytNativeExpectedFunctionV400 *expected,size_t expected_count,
    uint64_t image_base);
#ifdef __cplusplus
}
#endif
#endif
