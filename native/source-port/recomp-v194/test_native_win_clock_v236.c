/* SPDX-License-Identifier: GPL-2.0-or-later
 * V236: public synthetic clock arithmetic and real Win32 host API checks.
 */
#include "native_win_clock_v236.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

static void scale_test(void) {
    uint64_t value = UINT64_C(99);
    assert(shyt_clock_scale_ticks_v236(10000000, 10000000,
                                      1000000000, &value) == 0);
    assert(value == UINT64_C(1000000000));
    assert(shyt_clock_scale_ticks_v236(15000000, 10000000,
                                      1600000000, &value) == 0);
    assert(value == UINT64_C(2400000000));
    assert(shyt_clock_scale_ticks_v236(2500000, 10000000,
                                      1000000000, &value) == 0);
    assert(value == UINT64_C(250000000));
    value = 123;
    assert(shyt_clock_scale_ticks_v236(1, 0, 1000000000, &value) != 0);
    assert(value == 123);
    assert(shyt_clock_scale_ticks_v236(1, 2, 0, &value) != 0);
    assert(shyt_clock_scale_ticks_v236(UINT64_MAX, 1, UINT64_MAX,
                                      &value) != 0);
    assert(shyt_clock_scale_ticks_v236(1, 1, 1000000000, 0) != 0);
    /* V271: exact high-frequency arithmetic must work on clang-cl,
     * MSVC and Linux WITHOUT 128-bit compiler runtime division. */
    assert(shyt_clock_scale_ticks_v236(UINT64_C(29999999999),
              UINT64_C(30000000000), UINT64_C(1000000000), &value) == 0);
    assert(value == UINT64_C(999999999));
    assert(shyt_clock_scale_ticks_v236(UINT64_MAX - 1, UINT64_MAX,
                                      UINT64_MAX, &value) == 0);
    assert(value == UINT64_MAX - 1);
    /* Refuse overflow rather than wrapping into apparently valid time. */
    assert(shyt_clock_scale_ticks_v236(UINT64_MAX, UINT64_MAX,
                                      UINT64_MAX, &value) == 0);
    assert(value == UINT64_MAX);
}

int main(void) {
    scale_test();
#if defined(_WIN32)
    shyt_win_clock_v236 clock;
    uint64_t t0, t1, ticks;
    int64_t wall;
    assert(shyt_clock_initialize_v236(&clock) == 0);
    assert(clock.qpc_frequency > 0);
    assert(shyt_clock_monotonic_ns_v236(&clock, &t0) == 0);
    Sleep(2);
    assert(shyt_clock_monotonic_ns_v236(&clock, &t1) == 0);
    assert(t1 >= t0);
    assert(shyt_clock_ticks_v236(&clock, UINT64_C(1600000000), &ticks) == 0);
    assert(shyt_clock_realtime_us_v236(&wall) == 0);
    assert(wall > INT64_C(1577836800000000)); /* After 2020-01-01 */
    assert(shyt_clock_monotonic_ns_v236(0, &t1) != 0);
    assert(shyt_clock_realtime_us_v236(0) != 0);
#else
    shyt_win_clock_v236 unsupported = {0, 0};
    uint64_t out;
    assert(shyt_clock_initialize_v236(&unsupported) != 0);
    assert(shyt_clock_monotonic_ns_v236(&unsupported, &out) != 0);
#endif
    puts("SHYT_V236_HOST_WINDOWS_CLOCK_PASS");
    return 0;
}
