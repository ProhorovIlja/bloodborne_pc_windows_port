/* SPDX-License-Identifier: GPL-2.0-or-later
 * V270: real Win64 host clock adapter for ORIGINAL upstream RcApi V4
 * `rc.h`, which uses POSIX clock_gettime(CLOCK_MONOTONIC) in rc_tsc().
 * This is a compile-time Windows source-port adjustment, NOT a PS4
 * compatibility layer, runtime EBOOT/ELF loader or invented game import.
 *
 * Clang-cl /FI: include BEFORE the pinned upstream recomp/rc.h.
 */
#ifndef SHYT_NATIVE_WIN_RC_TIME_V270_H
#define SHYT_NATIVE_WIN_RC_TIME_V270_H
#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <time.h>
#include <stdint.h>
#include <stdatomic.h>
#ifndef CLOCK_MONOTONIC
#define CLOCK_MONOTONIC 1
#endif

/* Windows QPC is monotonic. Timestamp is relative to an arbitrary
 * stable system origin; the upstream rc_tsc function only needs
 * monotonic, high-resolution deltas in 1.6GHz guest clock units.
 * No uninitialized timespec even if a Win32 API unexpectedly fails.
 */
static inline int shyt_native_win_clock_gettime_v270(int clockid,
                                                     struct timespec* out) {
    if(!out) return -1;
    out->tv_sec=0;
    out->tv_nsec=0;
    if(clockid!=CLOCK_MONOTONIC) return -1;

    static _Atomic(uint64_t) cached_frequency=0;
    uint64_t hz=atomic_load_explicit(&cached_frequency,memory_order_acquire);
    if(!hz) {
        LARGE_INTEGER freq={0};
        if(!QueryPerformanceFrequency(&freq) || freq.QuadPart<=0)
            return -1;
        hz=(uint64_t)freq.QuadPart;
        atomic_store_explicit(&cached_frequency,hz,memory_order_release);
    }
    LARGE_INTEGER now={0};
    if(!QueryPerformanceCounter(&now) || now.QuadPart<0)
        return -1;
    const uint64_t ticks=(uint64_t)now.QuadPart;
    const uint64_t seconds=ticks/hz;
    const uint64_t remainder=ticks%hz;
    uint64_t nanoseconds=0;
    if(remainder<=UINT64_MAX/UINT64_C(1000000000)) {
        nanoseconds=(remainder*UINT64_C(1000000000))/hz;
    } else {
        /* Extremely high QPC frequencies: avoid 64-bit overflow.
         * The remainder fraction, not elapsed whole seconds, is
         * converted; its quantization is sub-nanosecond for normal QPC.
         */
        const long double exact=((long double)remainder*
                                 1000000000.0L)/(long double)hz;
        nanoseconds=(uint64_t)exact;
    }
    if(nanoseconds>=UINT64_C(1000000000))
        nanoseconds=UINT64_C(999999999);
    out->tv_sec=(time_t)seconds;
    out->tv_nsec=(long)nanoseconds;
    return 0;
}
#define clock_gettime shyt_native_win_clock_gettime_v270
#endif /* _WIN32 */
#endif /* SHYT_NATIVE_WIN_RC_TIME_V270_H */
