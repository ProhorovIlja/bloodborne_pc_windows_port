/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V376: bounded FLVER2 local bone palettes, inverse bind matrices,
 * and deterministic CPU diagnostic weighted positions. All game assets are
 * caller-owned; NO original game executable, PS4 HLE, interpreter or I/O.
 */
#ifndef SHYT_NATIVE_FLVER2_SKIN_PALETTE_V376_H
#define SHYT_NATIVE_FLVER2_SKIN_PALETTE_V376_H
#include "native_flver2_bind_pose_v375.h"
#include "native_flver2_vertex_decode_v371.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define SHYT_NATIVE_V376_MAX_BONES SHYT_NATIVE_V375_MAX_BONES

typedef struct ShytNativeMeshPaletteInfoV376 {
    uint32_t mesh_index, entries, global_bones, dynamic_flag;
    int32_t default_bone;
} ShytNativeMeshPaletteInfoV376;
typedef struct ShytNativeSkinnedPositionV376 {float xyz[3];} ShytNativeSkinnedPositionV376;

/* V362 validates the full FLVER before this data-only metadata extraction.
 * Entries are mesh-local -> skeleton-global indices (not vertex weights).
 * Zero-length palettes, observed in some private BB/DS3 samples, are valid
 * metadata, NOT proof that weighted vertices may address global bones.
 * Every entry must reference an existing global bone; no fallback guessing.
 * On any error, output array remains untouched and stats zeroed except for
 * a forbidden overlap, where neither object is modified.
 */
int shyt_native_flver2_mesh_palette_v376(
    const void *flver,size_t bytes,uint32_t mesh,
    uint32_t *global_bones,size_t capacity,
    ShytNativeMeshPaletteInfoV376 *info);

/* Row-vector affine convention from V375. Inverse bind is the inverse of
 * original world bind transform; it is NOT an animation transform.
 * Reject singular/near-singular or non-affine/non-finite matrices, aliased
 * input/output and insufficient capacity. No partial output on failure.
 */
int shyt_native_flver2_inverse_binds_v376(
    const ShytNativeFlver2BonePoseV375 *bind_pose,size_t bone_count,
    float (*inverse_bind)[16],size_t capacity);

/* CPU diagnostic only, not shader skinning. Each vertex holds exactly four
 * V371 Byte4B local bone indices and Byte4C normalized bone weights;
 * source MUST carry both semantics. The palette explicitly remaps active
 * local influences to global indices. Zero weight ignores its index;
 * zero total weight, out-of-range active index, invalid or non-finite
 * matrices and aliases are rejected without partially writing results.
 * In bind pose, inverseBind * animatedWorld is identity; animatedWorld is
 * caller-supplied, NOT obtained from proprietary HKX animations.
 * No implicit use of normal_w, default_bone or empty palette to fabricate
 * a skinned result. Inputs are immutable for the duration of the call.
 */
int shyt_native_flver2_skin_positions_v376(
    const ShytNativeFlver2VertexV371 *vertices,size_t vertex_count,
    const uint32_t *local_to_global,size_t palette_count,
    const float (*inverse_bind)[16],
    const float (*animated_world)[16],size_t global_bone_count,
    ShytNativeSkinnedPositionV376 *output,size_t output_capacity);
/* Explicit global-index alternative for an owner-validated mesh whose
 * local palette is EMPTY. Do not silently select this for every mesh: the
 * caller must independently establish the byte-index convention against
 * the source asset/animation. Every active bone index must be within
 * global_bone_count. Still a CPU diagnostic, not a shader/animation source.
 */
int shyt_native_flver2_skin_global_positions_v376(
    const ShytNativeFlver2VertexV371 *vertices,size_t vertex_count,
    const float (*inverse_bind)[16],
    const float (*animated_world)[16],size_t global_bone_count,
    ShytNativeSkinnedPositionV376 *output,size_t output_capacity);
#ifdef __cplusplus
}
#endif
#endif
