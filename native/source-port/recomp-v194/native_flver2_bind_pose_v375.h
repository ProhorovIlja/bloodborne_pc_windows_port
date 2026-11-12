/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V375: self-contained, bounded FLVER2 bone graph and bind pose.
 * No original game bytes, PS4 ABI, emulator, external allocator or I/O.
 */
#ifndef SHYT_NATIVE_FLVER2_BIND_POSE_V375_H
#define SHYT_NATIVE_FLVER2_BIND_POSE_V375_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define SHYT_NATIVE_V375_MAX_BONES 2048u

typedef struct ShytNativeFlver2BonePoseV375 {
    int16_t parent, first_child, next_sibling, previous_sibling;
    uint32_t depth;
    float translation[3], rotation_xzy[3], scale[3];
    /* Row-vector, row-major 4x4 matrices. Translation is in [12,13,14].
     * local = Scale * RotationX * RotationZ * RotationY * Translation.
     * world = local * parent.world, roots have world = local.
     * world is bind-pose geometry transform, NOT an inverse bind matrix,
     * animation sample or skinning palette. */
    float local[16], world[16];
} ShytNativeFlver2BonePoseV375;

typedef struct ShytNativeFlver2SkeletonStatsV375 {
    uint32_t bone_count, root_count, max_depth;
} ShytNativeFlver2SkeletonStatsV375;

/* Verify the entire FLVER2 file first (V362), then all bone relationships,
 * finite TRS, UTF16LE name bounds, and a cycle-free parent graph.
 * Rejects cyclic parents, inconsistent child/sibling links and unsupported
 * layouts; does not silently repair data. No dynamic allocations.
 * If no bones are present, stats=0 and a NULL pose output is accepted.
 * 
 * poses must be non-NULL and capacity>=bone_count otherwise. Output must
 * be disjoint from the ENTIRE source file, and stats disjoint from both.
 * On failure, stats are zeroed (unless aliasing rejects without writing),
 * and no pose result may be consumed. Caller owns output memory.
 */
int shyt_native_flver2_bind_pose_v375(
    const void *flver, size_t bytes,
    ShytNativeFlver2BonePoseV375 *poses, size_t capacity,
    ShytNativeFlver2SkeletonStatsV375 *stats);
#ifdef __cplusplus
}
#endif
#endif
