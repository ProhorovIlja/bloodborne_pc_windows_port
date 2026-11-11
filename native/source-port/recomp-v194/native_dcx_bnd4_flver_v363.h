/* SPDX-License-Identifier: GPL-2.0-or-later
 * V363: read-only, no-allocation DCX_DFLT -> BND4 -> FLVER2 adapter.
 * No PS4 executable, guest ABI, or game-owned bytes in this source.
 */
#ifndef SHYT_NATIVE_DCX_BND4_FLVER_V363_H
#define SHYT_NATIVE_DCX_BND4_FLVER_V363_H
#include <stddef.h>
#include <stdint.h>
#include "native_dcx_dflt_stream_core_v360.h"
#include "native_bnd4_index_v361.h"
#include "native_flver2_geometry_v362.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct ShytNativeDcxBnd4ViewV363 {
    const unsigned char *decoded_bnd4;
    size_t decoded_bytes;
    ShytNativeBnd4IndexV361 index;
} ShytNativeDcxBnd4ViewV363;

typedef struct ShytNativeFlver2AssetV363 {
    const unsigned char *flver;
    size_t flver_bytes;
    ShytNativeBnd4FileV361 file;
    ShytNativeFlver2GeometryV362 geometry;
} ShytNativeFlver2AssetV363;

/* Read one DCX file into caller-owned scratch exactly once; validate its
 * BND4 index before publishing any pointer. Never owns/allocates memory.
 * Input reader and output scratch MUST NOT overlap. On any failure out is
 * zero; discard/overwrite scratch because it may contain unverified data.
 * The returned view is valid only while scratch remains LIVE AND IMMUTABLE.
 */
int shyt_native_dcx_bnd4_open_v363(
    ShytNativeDcxReadExactV360 read_exact, void *read_context,
    uint64_t dcx_file_bytes, void *decoded_scratch, size_t scratch_capacity,
    ShytNativeDcxBnd4ViewV363 *out);

/* O(1) binder entry lookup after one validated open, plus bounded FLVER2
 * validation. Rejects per-entry compressed BND files until that distinct
 * format has its own verified decoder. Views alias immutable scratch;
 * no geometry is uploaded to GPU or interpreted as executable code.
 */
int shyt_native_dcx_bnd4_flver_at_v363(
    const ShytNativeDcxBnd4ViewV363 *view, uint32_t file_number,
    ShytNativeFlver2AssetV363 *out);
#ifdef __cplusplus
}
#endif
#endif
