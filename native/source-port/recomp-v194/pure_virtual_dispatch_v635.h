/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_PURE_VIRTUAL_DISPATCH_V635_H
#define BB_PURE_VIRTUAL_DISPATCH_V635_H
#include "pure_virtual_slots_v634.h"

/* For generated call sites that retain a proven relocation-slot identity.
 * The identity is not a loaded vtable value, host pointer or instruction RVA.
 * A miss is returned to the caller, which must stop this call path. */
enum bb_v635_result { BB_V635_UNRESOLVED, BB_V635_TARGET_RETURNED };
static inline enum bb_v635_result bb_v635_dispatch(
        const struct bb_v634_slot *slots, size_t count, uint64_t slot) {
    BbV634Target target = bb_v634_lookup(slots, count, slot);
    if (!target) return BB_V635_UNRESOLVED;
    target();
    /* The production target is fatal. A returning target is NOT success. */
    return BB_V635_TARGET_RETURNED;
}
#endif
