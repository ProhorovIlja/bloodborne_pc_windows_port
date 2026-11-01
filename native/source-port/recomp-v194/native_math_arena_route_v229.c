/* SPDX-License-Identifier: GPL-2.0-or-later
 * V229: all guest math stack/FP-pointer writes occur under a live
 * owner-managed Win64 shared arena lock. Fatal callbacks run after unpin.
 */
#include "native_math_arena_route_v229.h"
#include <stdlib.h>

static int v229_pin(void *ctx) {
    return shyt_guest_arena_v228_pin((ShytGuestArenaV228 *)ctx);
}
static void v229_unpin(void *ctx) {
    /* A corrupted/nested pin must not leave guest execution running. */
    if (!shyt_guest_arena_v228_unpin((ShytGuestArenaV228 *)ctx))
        abort();
}

int shyt_math_arena_route_v229_install(
    ShytMathRcApiRoute *route, const RcApi *original,
    const ShytMathImportTable *table, ShytGuestArenaV228 *arena,
    ShytMathFatalGuestMemory fault, void *fault_context) {
    if (!arena || !arena->initialized || !arena->live ||
        !arena->base || !arena->size || arena->writable_window.count != 1)
        return 0;
    return shyt_math_rcapi_route_v226_install_pinned(
        route, original, table,
        shyt_guest_arena_v228_permit_pinned, arena,
        fault, fault_context, v229_pin, v229_unpin, arena);
}
