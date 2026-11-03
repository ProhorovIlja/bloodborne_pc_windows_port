/* SPDX-License-Identifier: GPL-2.0-or-later
 * V354: native read-only FromSoftware BB/DS3 DCX Deflate HEADER decoder.
 * Validates supported envelope/size metadata, does not decompress or
 * execute bytes and never loads an EBOOT/PS4 runtime. Refuses KRAK/EDGE/
 * ZSTD, truncated data, excessive expansion and malformed headers.
 */
#ifndef SHYT_NATIVE_DCX_DFLT_HEADER_V354_H
#define SHYT_NATIVE_DCX_DFLT_HEADER_V354_H
#include <stddef.h>
#include <stdint.h>
#define SHYT_NATIVE_DCX_DFLT_HEADER_BYTES_V354 76u
#define SHYT_NATIVE_DCX_MAX_OUTPUT_V354 (512u * 1024u * 1024u)
#define SHYT_NATIVE_DCX_MAX_INPUT_V354 (256u * 1024u * 1024u)
typedef struct ShytNativeDcxDfltHeaderV354 {
    uint32_t uncompressed_bytes;
    uint32_t compressed_bytes;
    uint64_t payload_offset;
    uint8_t compression_level;
} ShytNativeDcxDfltHeaderV354;
#ifdef __cplusplus
extern "C" {
#endif
int shyt_native_dcx_dflt_probe_v354(
    const void *header, size_t header_bytes, uint64_t file_size,
    ShytNativeDcxDfltHeaderV354 *out);
#ifdef __cplusplus
}
#endif
#endif
