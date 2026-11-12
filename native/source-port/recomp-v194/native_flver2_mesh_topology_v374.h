/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V374: narrow standalone FLVER2 mesh/LOD/face topology from a
 * caller-owned immutable file. Original game data never shipped.
 */
#ifndef SHYT_NATIVE_FLVER2_MESH_TOPOLOGY_V374_H
#define SHYT_NATIVE_FLVER2_MESH_TOPOLOGY_V374_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define SHYT_V374_LOD_BASE 0u
#define SHYT_V374_LOD1 1u
#define SHYT_V374_LOD2 2u

typedef struct ShytNativeMeshFaceV374 {
    uint32_t mesh_index, material_index, face_set_index, face_slot;
    int32_t default_bone_index;
    uint32_t local_bone_count, vertex_count, vertex_buffer_count;
    uint32_t vertex_buffer_indices[3];
    uint32_t lod, motion_blur, cull_backfaces, triangle_strip;
    uint32_t index_element_bytes, index_count, index_absolute_offset;
    uint32_t triangle_count, degenerate_count, restart_count;
} ShytNativeMeshFaceV374;

/* Complete V362 validation plus one bounded mesh/face reference. Rejects
 * unknown LOD and EDGE compression, ambiguous strip primitive restart.
 * Data-only: never allocates, reads disk, reads skeleton matrices or draws.
 * Output may not overlap ANY part of the immutable source model.
 */
int shyt_native_flver2_mesh_face_v374(const void *flver, size_t bytes,
    uint32_t mesh, uint32_t face_slot, ShytNativeMeshFaceV374 *out);

/* Count-only: triangles=NULL, capacity=0. If non-NULL, destination holds
 * exactly 3*triangle_count 32-bit vertex indices, after degenerates and
 * primitive-restart markers are removed. Triangle strips alternate winding,
 * including across degenerate triangles; restarts reset winding. List faces
 * must have an index count divisible by 3. Does not alter destination on
 * failure; refuses output aliasing the *whole* original source file.
 * Also refuses overlapping output/metadata storage; output stats only set
 * after successful complete enumeration. Caller may generate a GPU buffer
 * from the resulting indices but must not submit before that completes.
 */
int shyt_native_flver2_triangles_v374(const void *flver, size_t bytes,
    uint32_t mesh, uint32_t face_slot,
    uint32_t *triangles, size_t capacity_indices,
    ShytNativeMeshFaceV374 *info);
#ifdef __cplusplus
}
#endif
#endif
