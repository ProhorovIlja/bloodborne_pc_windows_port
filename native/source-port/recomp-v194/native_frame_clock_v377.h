/* SPDX-License-Identifier: GPL-2.0-or-later
 * V377: reference fixed-60Hz simulation accumulator, separate render FPS caps.
 * Portable clock math only; not yet connected to Bloodborne gameplay.
 */
#ifndef SHYT_NATIVE_FRAME_CLOCK_V377_H
#define SHYT_NATIVE_FRAME_CLOCK_V377_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define SHYT_V377_SIM_HZ 60u
#define SHYT_V377_MAX_SUBSTEPS 8u
#define SHYT_V377_MAX_INTERVAL_NS 250000000ull

typedef struct ShytNativeFrameClockV377 {
    uint64_t last_ns, phase_units, simulated_steps;
    uint64_t last_present_ns, present_remainder;
    uint32_t present_fps;
    uint8_t initialized, paused, present_initialized, overloaded;
} ShytNativeFrameClockV377;

typedef struct ShytNativeFrameUpdateV377 {
    uint32_t steps, backlog_steps;
    double interpolation_alpha;
    uint8_t overload;
} ShytNativeFrameUpdateV377;
/* fps: 0=unlimited; 30/60/120/240; fixed simulation ALWAYS 60Hz. */
int shyt_native_frame_init_v377(ShytNativeFrameClockV377 *clock, uint32_t present_fps);
/* Negative elapsed, clock discontinuity >250ms, or impossible backlog: fail
 * and leave clock/output unchanged; caller must explicitly resync on suspend.
 * Max 8 logical ticks per invocation; if behind, return overload/backlog and
 * allow a subsequent update to catch up without silently dropping ticks.
 * Caller owns input snapshots, physics, animation, render interpolation.
 */
int shyt_native_frame_advance_v377(ShytNativeFrameClockV377 *clock,
    uint64_t monotonic_now_ns, ShytNativeFrameUpdateV377 *result);
/* Pause/resume rebases wall clock and rejects catch-up while paused. */
int shyt_native_frame_pause_v377(ShytNativeFrameClockV377 *clock, int paused,
    uint64_t monotonic_now_ns);
int shyt_native_frame_cap_v377(ShytNativeFrameClockV377 *clock, uint32_t cap);
/* Optional target for next presentation; does NOT sleep/busy-wait or submit
 * GPU work. Must combine with OS frame pacing, VRR and GPU queue metrics.
 */
int shyt_native_frame_present_deadline_v377(ShytNativeFrameClockV377 *clock,
    uint64_t present_now_ns, uint64_t *next_deadline_ns);
#ifdef __cplusplus
}
#endif
#endif
