/* SPDX-License-Identifier: GPL-2.0-or-later
 * Win32 read-only file adapter for the portable V360 stream decoder.
 * Game-owned DATA stays on its owner-provided disk. No guest EBOOT,
 * ELF loading, PS4 compatibility API, path logging, or temporary dump.
 */
#include "native_win_dcx_stream_v359.h"
#include "native_dcx_dflt_stream_core_v360.h"
#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
static int shyt_win_stream_exact_v360(
    void *context, uint64_t offset, void *destination, size_t count) {
    size_t got=0;
    const ShytNativeWinAssetStreamV352 *stream=
        (const ShytNativeWinAssetStreamV352 *)context;
    return shyt_native_win_asset_stream_read_v352(
               stream,offset,destination,count,&got) && got==count;
}

int shyt_native_win_dcx_stream_inflate_v359(
    const ShytNativeWinAssetRootV351 *root,
    const char *logical_path, void *out, size_t out_capacity,
    size_t *written) {
    if (!written) return 0;
    *written=0;
    if (!root || !logical_path || !out) return 0;
    ShytNativeWinAssetStreamV352 file={0};
    if (!shyt_native_win_asset_stream_open_v352(root,logical_path,&file))
        return 0;
    const int ok=shyt_native_dcx_dflt_stream_core_v360(
        shyt_win_stream_exact_v360,&file,file.file_size,out,
        out_capacity,written);
    shyt_native_win_asset_stream_close_v352(&file);
    return ok;
}
#else
int shyt_native_win_dcx_stream_inflate_v359(
    const ShytNativeWinAssetRootV351 *root,
    const char *logical_path, void *out, size_t out_capacity,
    size_t *written) {
    (void)root;(void)logical_path;(void)out;(void)out_capacity;
    if (written) *written=0;
    return 0;
}
#endif
