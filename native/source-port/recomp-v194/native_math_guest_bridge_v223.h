/* SPDX-License-Identifier: GPL-2.0-or-later
 * V223: typed BbCpu math return bridge. Uses upstream guest CPU layout,
 * not the host Windows calling convention at the call site.
 */
#ifndef SHYT_NATIVE_MATH_GUEST_BRIDGE_V223_H
#define SHYT_NATIVE_MATH_GUEST_BRIDGE_V223_H
#include "cpu/cpu_internal.h"
/* Exactly RcFn's upstream signature without including rc.h timer internals. */
typedef void (*ShytGuestMathFn)(BbCpu *cpu);
#ifdef __cplusplus
extern "C" {
#endif
/* NULL means unsupported: never silently report successful import. */
ShytGuestMathFn shyt_guest_math_v223_find(const char *name);
#ifdef __cplusplus
}
#endif
#endif
