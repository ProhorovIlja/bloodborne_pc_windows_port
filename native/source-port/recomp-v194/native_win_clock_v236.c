/* SPDX-License-Identifier: GPL-2.0-or-later
 * V236: Win32 clock source for a future native Bloodborne guest import bridge.
 * Intentionally host-only: PS4 clock-ID and SysV ABI still require validation.
 */
#include "native_win_clock_v236.h"
#include <limits.h>
#include <stddef.h>

#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

int shyt_clock_scale_ticks_v236(uint64_t counter_delta, uint64_t source_hz,
                                uint64_t target_hz, uint64_t *result) {
    uint64_t seconds, remainder, whole, fraction;
    if (!result || !source_hz || !target_hz) return -1;
    seconds = counter_delta / source_hz;
    remainder = counter_delta % source_hz;
    /* Evaluate quotients separately; no floating-point drift at long uptime. */
    if (seconds > UINT64_MAX / target_hz) return -1;
    whole = seconds * target_hz;
    if (remainder && target_hz > UINT64_MAX / remainder) return -1;
    fraction = (remainder * target_hz) / source_hz;
    if (whole > UINT64_MAX - fraction) return -1;
    *result = whole + fraction;
    return 0;
}

int shyt_clock_initialize_v236(shyt_win_clock_v236 *clock) {
#if defined(_WIN32)
    LARGE_INTEGER frequency, now;
    if (!clock || !QueryPerformanceFrequency(&frequency) ||
        frequency.QuadPart <= 0 || !QueryPerformanceCounter(&now) ||
        now.QuadPart < 0) return -1;
    clock->qpc_frequency = (uint64_t)frequency.QuadPart;
    clock->origin_counter = (uint64_t)now.QuadPart;
    return 0;
#else
    (void)clock;
    return -1;
#endif
}

int shyt_clock_ticks_v236(const shyt_win_clock_v236 *clock,
                           uint64_t target_hz, uint64_t *elapsed_ticks) {
#if defined(_WIN32)
    LARGE_INTEGER now;
    if (!clock || !elapsed_ticks || !clock->qpc_frequency || !target_hz ||
        !QueryPerformanceCounter(&now) || now.QuadPart < 0 ||
        (uint64_t)now.QuadPart < clock->origin_counter) return -1;
    return shyt_clock_scale_ticks_v236(
        (uint64_t)now.QuadPart - clock->origin_counter,
        clock->qpc_frequency, target_hz, elapsed_ticks);
#else
    (void)clock;
    (void)target_hz;
    (void)elapsed_ticks;
    return -1;
#endif
}

int shyt_clock_monotonic_ns_v236(const shyt_win_clock_v236 *clock,
                                 uint64_t *elapsed_ns) {
    return shyt_clock_ticks_v236(clock, UINT64_C(1000000000), elapsed_ns);
}

int shyt_clock_realtime_us_v236(int64_t *unix_microseconds) {
#if defined(_WIN32)
    FILETIME filetime;
    ULARGE_INTEGER stamp;
    const uint64_t unix_offset_100ns = UINT64_C(116444736000000000);
    uint64_t micros;
    if (!unix_microseconds) return -1;
    GetSystemTimeAsFileTime(&filetime);
    stamp.LowPart = filetime.dwLowDateTime;
    stamp.HighPart = filetime.dwHighDateTime;
    if (stamp.QuadPart < unix_offset_100ns) return -1;
    micros = (stamp.QuadPart - unix_offset_100ns) / UINT64_C(10);
    if (micros > INT64_MAX) return -1;
    *unix_microseconds = (int64_t)micros;
    return 0;
#else
    (void)unix_microseconds;
    return -1;
#endif
}
