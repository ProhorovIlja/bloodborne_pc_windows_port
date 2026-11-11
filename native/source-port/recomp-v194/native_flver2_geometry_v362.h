/* SPDX-License-Identifier: GPL-2.0-or-later
 * V362 standalone data-only FLVER2 0x20013/0x20014 geometry validator.
 * No PS4 binary, proprietary asset, guest CPU or runtime dependency.
 */
#ifndef SHYT_NATIVE_FLVER2_GEOMETRY_V362_H
#define SHYT_NATIVE_FLVER2_GEOMETRY_V362_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef struct ShytNativeFlver2GeometryV362 {
    uint32_t version;
    uint32_t data_offset;
    uint32_t data_bytes;
    uint32_t dummy_count;
    uint32_t material_count;
    uint32_t bone_count;
    uint32_t mesh_count;
    uint32_t vertex_buffer_count;
    uint32_t face_set_count;
    uint32_t layout_count;
    uint32_t texture_count;
    uint32_t total_vertices;
    uint64_t total_index_elements;
    uint64_t validated_vertex_bytes;
    uint64_t validated_index_bytes;
    uint32_t first_mesh_record_offset;
    uint32_t first_face_record_offset;
    uint32_t first_vertex_record_offset;
} ShytNativeFlver2GeometryV362;

/* Only validates an immutable caller-owned FLVER2 buffer; no allocation,
 * decoding, disk access, or logging. Records must not be modified after
 * validation. Refuses unknown compression/layout/endianness variants.
 * No output is valid if this call returns zero.
 */
int shyt_native_flver2_geometry_probe_v362(
    const void *flver, size_t file_size,
    ShytNativeFlver2GeometryV362 *out);
#ifdef __cplusplus
}
#endif
#endif
