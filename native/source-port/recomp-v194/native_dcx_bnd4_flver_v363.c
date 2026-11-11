/* SPDX-License-Identifier: GPL-2.0-or-later
 * V363: deterministic native resource index, NO game code or runtime.
 */
#include "native_dcx_bnd4_flver_v363.h"
#include <string.h>

int shyt_native_dcx_bnd4_open_v363(
    ShytNativeDcxReadExactV360 read_exact, void *read_context,
    uint64_t dcx_file_bytes, void *decoded_scratch, size_t scratch_capacity,
    ShytNativeDcxBnd4ViewV363 *out) {
    if (!out) return 0;
    memset(out, 0, sizeof(*out));
    if (!read_exact || !decoded_scratch || scratch_capacity < 0x40u)
        return 0;
    size_t decoded_bytes = 0;
    if (!shyt_native_dcx_dflt_stream_core_v360(
            read_exact, read_context, dcx_file_bytes,
            decoded_scratch, scratch_capacity, &decoded_bytes))
        return 0;
    ShytNativeBnd4IndexV361 index;
    if (!shyt_native_bnd4_index_probe_v361(
            decoded_scratch, decoded_bytes, &index))
        return 0;
    out->decoded_bnd4 = (const unsigned char *)decoded_scratch;
    out->decoded_bytes = decoded_bytes;
    out->index = index;
    return 1;
}

int shyt_native_dcx_bnd4_flver_at_v363(
    const ShytNativeDcxBnd4ViewV363 *view, uint32_t file_number,
    ShytNativeFlver2AssetV363 *out) {
    if (!out) return 0;
    memset(out, 0, sizeof(*out));
    if (!view || !view->decoded_bnd4 ||
        file_number >= view->index.file_count) return 0;
    ShytNativeBnd4FileV361 entry;
    if (!shyt_native_bnd4_file_at_v361(
            view->decoded_bnd4, view->decoded_bytes,
            &view->index, file_number, &entry)) return 0;
    /* V361 verifies this but re-check before pointer arithmetic. */
    if (entry.compressed || entry.data_offset > view->decoded_bytes ||
        entry.stored_bytes > view->decoded_bytes - entry.data_offset ||
        entry.stored_bytes > SIZE_MAX) return 0;
    const unsigned char *payload = view->decoded_bnd4 + (size_t)entry.data_offset;
    ShytNativeFlver2GeometryV362 geometry;
    if (!shyt_native_flver2_geometry_probe_v362(
            payload, (size_t)entry.stored_bytes, &geometry)) return 0;
    out->flver = payload;
    out->flver_bytes = (size_t)entry.stored_bytes;
    out->file = entry;
    out->geometry = geometry;
    return 1;
}

int shyt_native_dcx_bnd4_first_flver_v363(
    const ShytNativeDcxBnd4ViewV363 *view, uint32_t *file_number,
    ShytNativeFlver2AssetV363 *out) {
    if (file_number) *file_number = UINT32_MAX;
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!view || !view->decoded_bnd4 || !file_number) return 0;
    for (uint32_t i=0;i<view->index.file_count;++i) {
        ShytNativeBnd4FileV361 entry;
        if (!shyt_native_bnd4_file_at_v361(
                view->decoded_bnd4,view->decoded_bytes,
                &view->index,i,&entry)) return 0;
        /* Per-file compressed entries require a separate, not-yet-
         * implemented decoder. Do not guess their contents. */
        if (entry.compressed || entry.stored_bytes<8u) continue;
        if (entry.data_offset>view->decoded_bytes ||
            entry.stored_bytes>view->decoded_bytes-entry.data_offset ||
            entry.stored_bytes>SIZE_MAX) return 0;
        const unsigned char *candidate =
            view->decoded_bnd4 + (size_t)entry.data_offset;
        if (memcmp(candidate,"FLVER\0L\0",8)!=0) continue;
        if (!shyt_native_dcx_bnd4_flver_at_v363(view,i,out))
            return 0;
        *file_number=i;
        return 1;
    }
    return 0;
}
