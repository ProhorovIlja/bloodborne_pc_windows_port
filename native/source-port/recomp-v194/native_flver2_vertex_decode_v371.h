/* SPDX-License-Identifier: GPL-2.0-or-later
 * V371: independently authored, allocation-free FLVER2 vertex semantics.
 * Strictly only the verified BB/DS3 subset; no game source bytes.
 */
#ifndef SHYT_NATIVE_FLVER2_VERTEX_DECODE_V371_H
#define SHYT_NATIVE_FLVER2_VERTEX_DECODE_V371_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define SHYT_V371_MAX_MEMBERS 32u
#define SHYT_V371_POSITION     0x0001u
#define SHYT_V371_NORMAL       0x0002u
#define SHYT_V371_TANGENT0     0x0004u
#define SHYT_V371_TANGENT1     0x0008u
#define SHYT_V371_BONE_INDICES 0x0010u
#define SHYT_V371_BONE_WEIGHTS 0x0020u
#define SHYT_V371_COLOR        0x0040u
#define SHYT_V371_UV0          0x0080u
#define SHYT_V371_UV1          0x0100u

typedef struct ShytNativeFlver2VertexV371 {
    float position[3];
    float normal[3];
    float tangents[2][4];
    float uv[2][2];
    float bone_weights[4];
    uint16_t bone_indices[4];
    float color[4];
    uint32_t present;
    uint32_t normal_w;
} ShytNativeFlver2VertexV371;

typedef struct ShytNativeFlver2VertexMemberV371 {
    uint32_t semantic;
    uint32_t type;
    uint32_t semantic_index;
    uint32_t offset;
    uint32_t bytes;
} ShytNativeFlver2VertexMemberV371;

typedef struct ShytNativeFlver2VertexLayoutV371 {
    uint32_t buffer_index;
    uint32_t vertex_count;
    uint32_t stride;
    uint32_t data_offset;  /* absolute offset from start of immutable FLVER */
    uint32_t member_count;
    uint32_t present;
    ShytNativeFlver2VertexMemberV371 members[SHYT_V371_MAX_MEMBERS];
} ShytNativeFlver2VertexLayoutV371;

/* Re-runs V362's full model validation, then verifies every member in the
 * selected global FLVER vertex buffer is a supported semantic/type pair.
 * Refuses repeated positions/normals, unknown member types and unsupported
 * semantic combinations. No allocations, source writes or output pointers.
 * Unknown layouts are not guessed or silently interpreted.
 */
int shyt_native_flver2_vertex_layout_v371(
    const void *flver, size_t file_bytes, uint32_t buffer_index,
    ShytNativeFlver2VertexLayoutV371 *out);

/* Decode a bounded consecutive range to caller-owned canonical float data.
 * Output must be disjoint from the *entire* immutable source asset.
 * Rejects invalid vertex float components (NaN/Inf). No partial result is
 * usable if decoding fails; no dynamic allocation, GPU or file IO.
 * Little-endian FLVER2 0x20013/0x20014 only. Skinning is NOT applied.
 */
int shyt_native_flver2_decode_vertices_v371(
    const void *flver, size_t file_bytes, uint32_t buffer_index,
    uint32_t first_vertex, uint32_t count,
    ShytNativeFlver2VertexV371 *output, size_t capacity);
#ifdef __cplusplus
}
#endif
#endif
