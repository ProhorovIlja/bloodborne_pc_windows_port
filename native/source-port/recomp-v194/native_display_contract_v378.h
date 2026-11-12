/* SPDX-License-Identifier: GPL-2.0-or-later
 * V378: renderer-neutral x86-64 output/render aspect and HUD geometry.
 * All source and tests are invented; no copyrighted game assets.
 */
#ifndef SHYT_NATIVE_DISPLAY_CONTRACT_V378_H
#define SHYT_NATIVE_DISPLAY_CONTRACT_V378_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Target only: actual hardware display modes must be enumerated by SDL3/OS,
 * and device-dependent texture, present and memory limits queried at runtime. */
typedef struct ShytDisplayCapsV378 {
    uint32_t max_output_width, max_output_height;
    uint32_t max_texture_dim_2d;
    uint64_t max_output_pixels, max_render_pixels;
} ShytDisplayCapsV378;

typedef struct ShytDisplayRequestV378 {
    uint32_t output_width, output_height;
    uint32_t render_scale_per_mille; /* 500..2000, 1000 = 100% */
    uint32_t hud_safe_per_mille; /* 800..1000; safe fraction of fitted 16:9 */
    double vertical_fov_degrees; /* 20..140; constant across output ratios */
} ShytDisplayRequestV378;

typedef struct ShytDisplayRectV378 {
    uint32_t x,y,width,height;
} ShytDisplayRectV378;

typedef struct ShytDisplayPlanV378 {
    uint32_t output_width, output_height;
    uint32_t render_width, render_height;
    double output_aspect;
    double fov_vertical_degrees, fov_horizontal_degrees;
    /* A completely visible 16:9 overlay inside any native aspect; never
     * stretch 16:9 HUD glyphs across 21:9 or 32:9. Game world fills output. */
    ShytDisplayRectV378 fitted_16_9;
    ShytDisplayRectV378 hud_safe;
} ShytDisplayPlanV378;

/* No device operations, allocations or syscalls. Fail without changing out.
 * A passing plan does NOT indicate the OS actually exposes this display mode.
 */
int shyt_native_display_plan_v378(const ShytDisplayRequestV378 *request,
                                   const ShytDisplayCapsV378 *caps,
                                   ShytDisplayPlanV378 *out);

/* Identical GPU attachments may be reused only if BOTH dimensions and all
 * other allocation-relevant properties match, not width OR height alone. */
typedef struct ShytDisplaySurfaceKeyV378 {
    uint32_t width,height,format,samples,usage,color_space;
} ShytDisplaySurfaceKeyV378;
int shyt_native_surface_reuse_v378(const ShytDisplaySurfaceKeyV378 *allocated,
                                   const ShytDisplaySurfaceKeyV378 *requested);
/* This is a compile-time ABI contract, not a whole-game AOT proof. */
int shyt_native_x64_abi_v378(void);
#ifdef __cplusplus
}
#endif
#endif
