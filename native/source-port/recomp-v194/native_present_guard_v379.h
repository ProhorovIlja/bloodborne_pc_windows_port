/* SPDX-License-Identifier: GPL-2.0-or-later
 * V379: host-mode validation and fence-bound render-target retirement.
 * Pure C11; no original game executable, files, or vendor SDK.
 */
#ifndef SHYT_NATIVE_PRESENT_GUARD_V379_H
#define SHYT_NATIVE_PRESENT_GUARD_V379_H
#include <stddef.h>
#include <stdint.h>
#include "native_display_contract_v378.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Each entry must come from a REAL display's enumerated OS fullscreen modes.
 * Width/height are physical render pixels, not DPI-independent window units.
 * Rate is a positive exact rational; e.g. 60000/1001 != 60/1.
 */
typedef struct ShytNativeModeV379 {
    uint32_t width, height;
    uint32_t refresh_num, refresh_den;
} ShytNativeModeV379;

/* Target refresh 0/0 means choose highest enumerated refresh at exact size.
 * No fallback to an invented/interpolated resolution or frequency. */
int shyt_native_exact_mode_v379(const ShytNativeModeV379 *enumerated,
                                size_t count,
                                const ShytNativeModeV379 *requested,
                                ShytNativeModeV379 *selected);

/* Snapshot of the CURRENT queried native backend surface capabilities.
 * UINT32_MAX/UINT32_MAX = Vulkan-style unspecified current extent.
 * 0/0 = minimized; a fixed nonzero pair must match the requested mode.
 * The three booleans must be 1 ONLY after the backend explicitly verified
 * the requested surface format+colorspace, presentation support, and usage.
 */
typedef struct ShytNativeWsiCapsV379 {
    uint32_t min_width, min_height, max_width, max_height;
    uint32_t current_width, current_height;
    uint64_t max_surface_pixels;
    uint8_t format_colorspace_supported;
    uint8_t presentation_supported;
    uint8_t usage_supported;
} ShytNativeWsiCapsV379;
int shyt_native_surface_extent_v379(const ShytNativeModeV379 *selected,
                                   const ShytNativeWsiCapsV379 *caps);

/* CPU bookkeeping only: generation changes NEVER free GPU resources.
 * A renderer must query real completed GPU timeline/fence values, destroy
 * retired allocations itself, then explicitly acknowledge destruction.
 * A single retirement slot intentionally blocks bursts of unsafe resizes.
 */
typedef struct ShytNativeTargetStateV379 {
    ShytDisplaySurfaceKeyV378 active_key, retired_key;
    uint64_t generation, last_submitted, active_last_submit;
    uint64_t completed_fence, retired_last_submit;
    uint8_t has_active, has_retired;
} ShytNativeTargetStateV379;
int shyt_native_target_init_v379(ShytNativeTargetStateV379 *state,
                                 const ShytDisplaySurfaceKeyV378 *initial);
int shyt_native_target_submit_v379(ShytNativeTargetStateV379 *state,
                                   uint64_t fence_value);
int shyt_native_target_complete_v379(ShytNativeTargetStateV379 *state,
                                     uint64_t observed_completed_fence);
int shyt_native_target_resize_v379(ShytNativeTargetStateV379 *state,
                                   const ShytDisplaySurfaceKeyV378 *next);
int shyt_native_target_may_destroy_retired_v379(
    const ShytNativeTargetStateV379 *state);
int shyt_native_target_ack_destroy_v379(ShytNativeTargetStateV379 *state);
#ifdef __cplusplus
}
#endif
#endif
