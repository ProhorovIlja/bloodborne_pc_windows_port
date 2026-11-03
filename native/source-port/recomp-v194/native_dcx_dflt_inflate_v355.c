/* SPDX-License-Identifier: GPL-2.0-or-later
 * Source-based native DCX_DFLT payload decoder for BB and DS3.
 * zlib v1.3.1 under Zlib license is pinned by the CI workflow.
 * Never interprets proprietary code, game scripts or PS4 executable.
 */
#include "native_dcx_dflt_inflate_v355.h"
#include "native_dcx_dflt_header_v354.h"
#include <limits.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>

int shyt_native_dcx_dflt_inflate_v355(
    const void *dcx,size_t dcx_bytes,void *out,size_t out_capacity,size_t *written) {
    if (!written) return 0;
    *written=0;
    if (!dcx || !out || dcx_bytes<SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354 ||
        dcx_bytes>(size_t)SHYT_NATIVE_DCX_MAX_INPUT_V354+
                  SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354+15u)
        return 0;
    ShytNativeDcxDfltHeaderV354 meta;
    if (!shyt_native_dcx_dflt_probe_v354(dcx,dcx_bytes,(uint64_t)dcx_bytes,&meta))
        return 0;
    /* uint32 DCX lengths already fit zlib's uLong on both Windows
     * (32-bit unsigned long) and Linux (64-bit unsigned long). */
    if (!meta.uncompressed_bytes || out_capacity<(size_t)meta.uncompressed_bytes ||
        meta.payload_offset>dcx_bytes)
        return 0;
    const unsigned char *p=(const unsigned char *)dcx;
    const size_t offset=(size_t)meta.payload_offset;
    const size_t packed=(size_t)meta.compressed_bytes;
    if (packed>dcx_bytes-offset || dcx_bytes-offset-packed>15u)
        return 0;
    /* FromSoftware may align some DCX containers; any unused bytes must
     * be zero. Don't accept concatenated zlib streams or hidden payloads.
     */
    for(size_t i=offset+packed;i<dcx_bytes;++i)
        if(p[i]!=0u) return 0;
    /* zlib uncompress2 checks the Adler-32 and gives the exact number
     * of consumed bytes. This is zlib-wrapped Deflate, not raw Deflate.
     * Caller-supplied memory remains untrusted until the Z_OK result.
     */
    uLongf plain=(uLongf)meta.uncompressed_bytes;
    uLong source=(uLong)packed;
    const int result=uncompress2((Bytef *)out,&plain,(const Bytef *)(p+offset),&source);
    if (result!=Z_OK || plain!=(uLongf)meta.uncompressed_bytes ||
        source!=(uLong)packed)
        return 0;
    *written=(size_t)plain;
    return 1;
}
