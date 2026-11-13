/* SPDX-License-Identifier: GPL-2.0-or-later
 * Single-controller subset for the first C++ static initializer.
 * A pending guard is a hard stop (no blocking / thread ownership yet).
 * Use explicit guest addresses, not host pointers. Low byte is the
 * initialized marker; our private pending bit is in byte 1.
 */
#ifndef SHYT_NATIVE_STATIC_GUARD_V413_H
#define SHYT_NATIVE_STATIC_GUARD_V413_H
#include <stdint.h>

enum ShytGuardAction { SHYT_GUARD_ACQUIRE, SHYT_GUARD_RELEASE, SHYT_GUARD_ABORT };
enum ShytGuardResult { SHYT_GUARD_REFUSED=-1, SHYT_GUARD_NO_INIT=0, SHYT_GUARD_INIT=1 };
static inline enum ShytGuardResult shyt_guard_transition_v413(
    uint64_t old,enum ShytGuardAction action,uint64_t *next) {
    if(!next || (old&UINT64_C(0xfffffffffffffefe)))return SHYT_GUARD_REFUSED;
    if(action==SHYT_GUARD_ACQUIRE) {
        if(old==UINT64_C(1)) { *next=old;return SHYT_GUARD_NO_INIT; }
        if(old!=0)return SHYT_GUARD_REFUSED;
        *next=UINT64_C(0x100);return SHYT_GUARD_INIT;
    }
    if(old!=UINT64_C(0x100))return SHYT_GUARD_REFUSED;
    if(action==SHYT_GUARD_RELEASE) { *next=1;return SHYT_GUARD_NO_INIT; }
    if(action==SHYT_GUARD_ABORT) { *next=0;return SHYT_GUARD_NO_INIT; }
    return SHYT_GUARD_REFUSED;
}
#endif
