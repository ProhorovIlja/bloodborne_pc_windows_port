/* SPDX-License-Identifier: GPL-2.0-or-later
 * V361: narrow, allocation-free BND4 index for native Bloodborne/DS3 assets.
 * No proprietary bytes, PS4 runtime, ELF/EBOOT, or file execution.
 */
#ifndef SHYT_NATIVE_BND4_INDEX_V361_H
#define SHYT_NATIVE_BND4_INDEX_V361_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Parsed immutable archive layout. Caller must not alter input bytes
 * between probe and file_at calls. Max decoded archive: 512 MiB.
 * Only verified little-endian Unicode format 0x74 is supported.
 * This is a narrow native engine resource reader, not a generic BND tool.
 */
typedef struct ShytNativeBnd4IndexV361 {
    uint32_t file_count;
    uint64_t header_end;
    uint64_t hash_table_offset;
    uint8_t extended;
} ShytNativeBnd4IndexV361;

typedef struct ShytNativeBnd4FileV361 {
    uint64_t data_offset;
    uint64_t stored_bytes;
    uint64_t original_bytes;
    uint32_t file_id;
    uint32_t name_utf16_offset;
    uint32_t name_utf16_code_units;
    uint8_t compressed;
} ShytNativeBnd4FileV361;

/* Fully validates each record, filenames, payload ranges, and optional
 * hash-table bounds without allocating, decoding or copying game data.
 * Refuses unsupported BND endian/format combinations.
 */
int shyt_native_bnd4_index_probe_v361(
    const void *data, size_t data_bytes, ShytNativeBnd4IndexV361 *out);

/* Constant-time record lookup AFTER a successful probe, as long as
 * data and index are unchanged. Returns a bounded reference into
 * caller-owned read-only bytes; never executes or decompresses it.
 * Rejects invalid indices and zeroes *out on failure.
 */
int shyt_native_bnd4_file_at_v361(
    const void *data, size_t data_bytes,
    const ShytNativeBnd4IndexV361 *index, uint32_t file_number,
    ShytNativeBnd4FileV361 *out);
#ifdef __cplusplus
}
#endif
#endif
