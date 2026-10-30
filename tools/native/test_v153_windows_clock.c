/* V153: actual original staged C ABI on Windows, no game data or renderer.
 * Build with clang -std=c11 -Wall -Wextra -Werror -I original/bbport/src.
 * This includes the real YT1.3 runtime_time.c, not a transcribed function.
 */
#include <stdint.h>
#include <time.h>
#include <windows.h>
#include <stdio.h>
#include "runtime_time.c"

/* The real host implementation comes from compat_win.c. This isolated test
 * substitutes a zero offset so that it can link without the entire game. */
long compat_utc_offset(time_t utc) { (void)utc; return 0; }

int main(void) {
    if (runtime_time_resolve("n88vx3C5nW8#I#J")!=(uintptr_t)&guest_gettimeofday) return 2;
    if (runtime_time_resolve("some-unknown-native-symbol")!=0) return 3;
    if (guest_gettimeofday(NULL,NULL)!=0) return 4;
    for (int i=0;i<1024;++i) {
        GuestTimeval guest={0,0};
        GuestTimezone zone={0,0};
        if (guest_gettimeofday(&guest,&zone)!=0) return 5;
        if (guest.microseconds<0 || guest.microseconds>=1000000) return 6;
        if (guest.seconds<1700000000 || guest.seconds>3000000000LL) return 7;
        FILETIME t;
        GetSystemTimePreciseAsFileTime(&t);
        const uint64_t ticks=((uint64_t)t.dwHighDateTime<<32)|t.dwLowDateTime;
        const int64_t current_us=((int64_t)ticks-INT64_C(116444736000000000))/10;
        const int64_t guest_us=guest.seconds*INT64_C(1000000)+guest.microseconds;
        if (current_us<guest_us-INT64_C(2000000) ||
            current_us>guest_us+INT64_C(2000000)) return 8;
        if (zone.minuteswest!=0) return 9;
        TIME_ZONE_INFORMATION timezone;
        DWORD status=GetTimeZoneInformation(&timezone);
        if (zone.dsttime!=(status==TIME_ZONE_ID_DAYLIGHT ? 1 : 0)) return 10;
    }
    puts("SHYT_V153_ACTUAL_PINNED_YT130_NATIVE_WIN32_CLOCK_GUEST_ABI_PASS");
    return 0;
}
