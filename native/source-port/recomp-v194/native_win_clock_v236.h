/* SPDX-License-Identifier: GPL-2.0-or-later
 * V236: host Windows timing primitives for future guest-time import adapters.
 * No PS4 ABI or import signatures are claimed by this host-only interface.
 */
#ifndef SHYT_NATIVE_WIN_CLOCK_V236_H
#define SHYT_NATIVE_WIN_CLOCK_V236_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct shyt_win_clock_v236 {
    uint64_t qpc_frequency;
    uint64_t origin_counter;
} shyt_win_clock_v236;

/* Zero on success, nonzero on overflow, unsupported OS, or bad input. */
int shyt_clock_scale_ticks_v236(uint64_t counter_delta, uint64_t source_hz,
                                uint64_t target_hz, uint64_t *result);
int shyt_clock_initialize_v236(shyt_win_clock_v236 *clock);
int shyt_clock_monotonic_ns_v236(const shyt_win_clock_v236 *clock,
                                 uint64_t *elapsed_ns);
int shyt_clock_ticks_v236(const shyt_win_clock_v236 *clock,
                           uint64_t target_hz, uint64_t *elapsed_ticks);
int shyt_clock_realtime_us_v236(int64_t *unix_microseconds);
#ifdef __cplusplus
}
#endif
#endif
