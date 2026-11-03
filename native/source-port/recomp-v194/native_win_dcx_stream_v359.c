/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual Win32 streaming DCX_DFLT inflater, pinned zlib v1.3.1.
 * Reads game-owned resources, not game executable code. No runtime
 * shell, PS4 file service, network, upload, temp uncompressed file.
 */
#include "native_win_dcx_stream_v359.h"
#include "native_dcx_dflt_header_v354.h"
#include <stdint.h>
#include <string.h>

#if defined(_WIN32)
#include <zlib.h>
#define SHYT_STREAM_BLOCK_V359 65536u

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
    int success=0, initialized=0;
    z_stream z;
    memset(&z,0,sizeof(z));
    unsigned char block[SHYT_STREAM_BLOCK_V359];
    unsigned char header[SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354];
    ShytNativeDcxDfltHeaderV354 meta;
    size_t n=0;

    if (file.file_size<SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354 ||
        file.file_size>(uint64_t)SHYT_NATIVE_DCX_MAX_INPUT_V354+
                        SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354+15u ||
        !shyt_native_win_asset_stream_read_v352(
            &file,0,header,sizeof(header),&n) || n!=sizeof(header) ||
        !shyt_native_dcx_dflt_probe_v354(
            header,sizeof(header),file.file_size,&meta) ||
        out_capacity<(size_t)meta.uncompressed_bytes)
        goto done;

    const uint64_t compressed_end=meta.payload_offset+meta.compressed_bytes;
    const uint64_t extra=file.file_size-compressed_end;
    if (extra>15u) goto done;
    if (extra) {
        unsigned char tail[15];
        if (!shyt_native_win_asset_stream_read_v352(
              &file,compressed_end,tail,(size_t)extra,&n) || n!=extra)
            goto done;
        for(size_t i=0;i<(size_t)extra;++i)
            if(tail[i]!=0) goto done;
    }

    if (inflateInit(&z)!=Z_OK) goto done;
    initialized=1;
    z.next_out=(Bytef *)out;
    z.avail_out=(uInt)meta.uncompressed_bytes;
    uint64_t position=meta.payload_offset;
    uint32_t unread=meta.compressed_bytes;
    for (;;) {
        if (z.avail_in==0 && unread) {
            const size_t chunk=unread<SHYT_STREAM_BLOCK_V359 ?
                               (size_t)unread:SHYT_STREAM_BLOCK_V359;
            if (!shyt_native_win_asset_stream_read_v352(
                  &file,position,block,chunk,&n) || n!=chunk)
                goto done;
            z.next_in=block;
            z.avail_in=(uInt)chunk;
            position+=chunk;
            unread-=(uint32_t)chunk;
        }
        const int result=inflate(&z,Z_NO_FLUSH);
        if (result==Z_STREAM_END) {
            /* Source must have exactly ONE zlib stream, including Adler32;
             * no extra compressed bytes, truncated suffix or hidden stream.
             */
            if (z.total_in!=(uLong)meta.compressed_bytes ||
                z.total_out!=(uLong)meta.uncompressed_bytes ||
                z.avail_in!=0 || unread!=0)
                goto done;
            success=1;
            *written=(size_t)z.total_out;
            break;
        }
        if (result!=Z_OK || z.avail_out==0 ||
            (z.avail_in==0 && unread==0))
            goto done;
    }
done:
    if (initialized) inflateEnd(&z);
    shyt_native_win_asset_stream_close_v352(&file);
    if (!success) *written=0;
    return success;
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
