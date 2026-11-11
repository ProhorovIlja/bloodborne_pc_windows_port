/* SPDX-License-Identifier: GPL-2.0-or-later
 * Portable read-at streaming decoder; zlib is linked, not vendored.
 * Input is DATA only. No EBOOT, ELF, PS4 runtime, or game bytes.
 */
#include "native_dcx_dflt_stream_core_v360.h"
#include "native_dcx_dflt_header_v354.h"
#include <stdint.h>
#include <string.h>
#include <zlib.h>
#define SHYT_DCX_STREAM_BLOCK_V360 65536u

int shyt_native_dcx_dflt_stream_core_v360(
    ShytNativeDcxReadExactV360 read_exact, void *context,
    uint64_t file_size, void *output, size_t output_capacity,
    size_t *written) {
    if (!written) return 0;
    *written=0;
    if (!read_exact || !output ||
        file_size<SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354 ||
        file_size>(uint64_t)SHYT_NATIVE_DCX_MAX_INPUT_V354+
                  SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354+15u)
        return 0;

    unsigned char header[SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354];
    ShytNativeDcxDfltHeaderV354 meta;
    if (!read_exact(context,0,header,sizeof(header)) ||
        !shyt_native_dcx_dflt_probe_v354(
            header,sizeof(header),file_size,&meta) ||
        output_capacity<(size_t)meta.uncompressed_bytes)
        return 0;
    /* The checked header bounds prove payload_offset+compressed_bytes
     * cannot overflow or exceed file_size. Verify again before use. */
    if (meta.payload_offset>file_size ||
        (uint64_t)meta.compressed_bytes>file_size-meta.payload_offset)
        return 0;
    const uint64_t payload_end=meta.payload_offset+meta.compressed_bytes;
    const uint64_t extra=file_size-payload_end;
    if (extra>15u) return 0;
    if (extra) {
        unsigned char tail[15];
        if (!read_exact(context,payload_end,tail,(size_t)extra))
            return 0;
        for (size_t i=0;i<(size_t)extra;++i)
            if (tail[i]!=0) return 0;
    }

    z_stream z;
    memset(&z,0,sizeof(z));
    if (inflateInit(&z)!=Z_OK) return 0;
    z.next_out=(Bytef *)output;
    /* Verified header limits the length to 512 MiB, safely <= UINT_MAX. */
    z.avail_out=(uInt)meta.uncompressed_bytes;
    unsigned char block[SHYT_DCX_STREAM_BLOCK_V360];
    uint64_t offset=meta.payload_offset;
    uint32_t unread=meta.compressed_bytes;
    int success=0;
    for (;;) {
        if (z.avail_in==0 && unread) {
            const size_t count=unread<SHYT_DCX_STREAM_BLOCK_V360 ?
                (size_t)unread : SHYT_DCX_STREAM_BLOCK_V360;
            if (!read_exact(context,offset,block,count))
                break;
            z.next_in=block;
            z.avail_in=(uInt)count;
            offset+=count;
            unread-=(uint32_t)count;
        }
        const uLong before_in=z.total_in;
        const uLong before_out=z.total_out;
        const int result=inflate(&z,Z_NO_FLUSH);
        if (result==Z_STREAM_END) {
            /* No truncated checksum, second stream, hidden compressed
             * suffix, or output length mismatch may be accepted. */
            if (z.total_in==(uLong)meta.compressed_bytes &&
                z.total_out==(uLong)meta.uncompressed_bytes &&
                z.avail_in==0 && unread==0) {
                success=1;
                *written=(size_t)z.total_out;
            }
            break;
        }
        if (result!=Z_OK || z.avail_out==0 ||
            (z.avail_in==0 && unread==0) ||
            (z.total_in==before_in && z.total_out==before_out))
            break;
    }
    inflateEnd(&z);
    if (!success) *written=0;
    return success;
}
