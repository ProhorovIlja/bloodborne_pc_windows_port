/* SPDX-License-Identifier: GPL-2.0-or-later
 * V270: pinned genuine RcApi V4 rc_tsc() uses Windows QPC, not
 * undeclared POSIX clock_gettime. Win64-native, no game bytes.
 */
#include "native_win_rc_time_v270.h"
#include "recomp/rc.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

int main(void) {
#if defined(_WIN32)
    struct timespec before={0},after={0},invalid={0};
    assert(clock_gettime(CLOCK_MONOTONIC,&before)==0);
    const uint64_t tsc_before=rc_tsc();
    Sleep(5);
    assert(clock_gettime(CLOCK_MONOTONIC,&after)==0);
    const uint64_t tsc_after=rc_tsc();
    assert(before.tv_nsec>=0 && before.tv_nsec<1000000000);
    assert(after.tv_nsec>=0 && after.tv_nsec<1000000000);
    assert(after.tv_sec>before.tv_sec ||
           (after.tv_sec==before.tv_sec && after.tv_nsec>=before.tv_nsec));
    assert(tsc_after>tsc_before);
    assert(clock_gettime(-99,&invalid)!=0);
    assert(invalid.tv_sec==0 && invalid.tv_nsec==0);
    assert(clock_gettime(CLOCK_MONOTONIC,NULL)!=0);
#endif
    puts("SHYT_V270_PINNED_WIN64_RCAPI_REAL_QPC_MONOTONIC_PASS");
    return 0;
}
