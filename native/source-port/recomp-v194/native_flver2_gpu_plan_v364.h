/* SPDX-License-Identifier: GPL-2.0-or-later
 * V364: renderer-neutral upload descriptions from validated FLVER2 assets.
 * Source stays caller-owned, no PS4 runtime, no graphics backend or game data.
 */
#ifndef SHYT_NATIVE_FLVER2_GPU_PLAN_V364_H
#define SHYT_NATIVE_FLVER2_GPU_PLAN_V364_H
#include <stddef.h>
#include <stdint.h>
#include "native_dcx_bnd4_flver_v363.h"
#ifdef __cplusplus
extern "C" {
#endif

/* All byte offsets are relative to asset.flver, NOT file-system or GPU
 * addresses. The caller must hold that immutable source memory live until
 * staging copies finish. No pointers to source memory are stored in plans.
 */
typedef struct ShytNativeGpuVertexSpanV364 {
    uint32_t source_offset;
    uint32_t bytes;
    uint64_t staging_offset; /* aligned destination byte offset */
    uint32_t vertex_count;
    uint32_t vertex_stride;
    uint32_t layout_index;
    uint32_t buffer_index;
} ShytNativeGpuVertexSpanV364;

typedef struct ShytNativeGpuIndexSpanV364 {
    uint32_t source_offset;
    uint32_t bytes;
    uint64_t staging_offset; /* aligned destination byte offset */
    uint32_t index_count;
    uint32_t index_element_bytes; /* two or four; no EDGE encoded stream */
    uint32_t face_flags;         /* LOD/motion blur preserved for backend */
    uint8_t triangle_strip;
    uint8_t cull_backfaces;
} ShytNativeGpuIndexSpanV364;

typedef struct ShytNativeGpuDrawV364 {
    uint32_t mesh_index;
    uint32_t material_index;
    uint32_t face_set_index;
    uint32_t vertex_buffer_count; /* 1..3 (as validated in V362) */
    uint32_t vertex_buffer_indices[3]; /* slots into vertex span array */
    uint32_t vertex_count;
} ShytNativeGpuDrawV364;

typedef struct ShytNativeGpuUploadCountsV364 {
    uint32_t vertex_buffers;
    uint32_t index_buffers;
    uint32_t draws;
    uint64_t vertex_source_bytes;
    uint64_t index_source_bytes;
    uint64_t staging_bytes_total; /* packed, 4-byte-aligned layout */
} ShytNativeGpuUploadCountsV364;

/* Preflight exact capacities, not a GPU allocation. Zeroes output on error.
 * Re-runs V362 full validation so a forged/stale V363 geometry summary is
 * not trusted. The asset source must stay immutable during and after this
 * call until all staging copies finish. The stats output must never overlap
 * the model source; that invalid pointer combination is refused without
 * writing to the aliased output. Never pass unvalidated game bytes.
 */
int shyt_native_flver2_gpu_requirements_v364(
    const ShytNativeFlver2AssetV363 *asset,
    ShytNativeGpuUploadCountsV364 *out);

/* On success, writes descriptors in fixed file order and draw records in
 * mesh/face order. No allocations, GPU calls, or source-data copies.
 * Returns failure if any output capacity or staging budget is too small.
 * Staging ranges are 4-byte aligned for portable graphics backends; zero-
 * length buffers must not result in zero-size GPU copy commands.
 * All descriptor output arrays must be mutually disjoint and disjoint
 * from the model source and result struct. On failure, summary is zero
 * (unless the summary aliases immutable source, which is a rejected
 * caller contract violation) and partial arrays MUST NOT be used.
 */
int shyt_native_flver2_gpu_plan_v364(
    const ShytNativeFlver2AssetV363 *asset,
    ShytNativeGpuVertexSpanV364 *vertices, size_t vertices_capacity,
    ShytNativeGpuIndexSpanV364 *indices, size_t indices_capacity,
    ShytNativeGpuDrawV364 *draws, size_t draws_capacity,
    uint64_t staging_budget_bytes,
    ShytNativeGpuUploadCountsV364 *out);

/* Copy a previously emitted contiguous span to backend-owned staging RAM.
 * No GPU operation occurs here. Destination MUST NOT alias ANY part of
 * caller-owned source model. Exactly bytes is written or nothing is written;
 * capacity/offset/overlap must all pass before memcpy. Caller keeps staging
 * alive until the backend has completed the transfer (GPU fence). The
 * `written` size output must never alias the model or destination. Invalid
 * aliasing is rejected without writing that size output.
 */
int shyt_native_flver2_stage_bytes_v364(
    const ShytNativeFlver2AssetV363 *asset,
    uint32_t source_offset, uint32_t bytes,
    void *destination, size_t destination_capacity,
    size_t *written);
#ifdef __cplusplus
}
#endif
#endif
