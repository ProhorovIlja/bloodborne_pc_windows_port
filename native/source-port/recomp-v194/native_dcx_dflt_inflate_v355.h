/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native BB + DS3 DCX_DFLT payload decompressor, not PS4 or EBOOT emulation.
 * Link only pinned, license-compatible zlib v1.3.1.
 * Caller owns the output buffer; no user-derived size allocations performed.
 */
#ifndef SHYT_NATIVE_DCX_DFLT_INFLATE_V355_H
#define SHYT_NATIVE_DCX_DFLT_INFLATE_V355_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Accepts a complete DCX file and a caller-provided output buffer at
 * least as large as its verified uncompressed header length. Rejects
 * truncated streams, invalid zlib checksums, extra encoded members,
 * mismatched uncompressed length and nonzero trailing padding.
 * Successful return=1, failure=0 with *written=0. On failed inflate
 * the caller must treat contents of out as unspecified/untrusted.
 */
int shyt_native_dcx_dflt_inflate_v355(
    const void *dcx, size_t dcx_bytes,
    void *out, size_t out_capacity, size_t *written);
#ifdef __cplusplus
}
#endif
#endif
