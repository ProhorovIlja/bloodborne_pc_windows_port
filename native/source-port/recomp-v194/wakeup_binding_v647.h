/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_WAKEUP_BINDING_V647_H
#define BB_WAKEUP_BINDING_V647_H
#include "mutex_gate_v574.h"

/* Typed replacement for translated callers, not the guest function ABI.
 * Reuse the very same data and gate as constructors 1 and 2. The startup
 * controller serializes calls and owns the data and callbacks' lifetime. */
struct bb_wakeup_binding_v647 {
    unsigned char *data;
    size_t size;
    struct bb_mutex_gate_v574 gate;
    const struct bb_mutex_calls_v574 *calls;
    void *context;
};

static inline unsigned char *bb_wakeup_get_v647(const struct bb_wakeup_binding_v647 *b) {
    if (!b || !bb_mutex_gate_v574(b->data,b->size,b->gate,b->calls,b->context)) return NULL;
    unsigned char *obj=b->data+b->gate.object;
    /* Original returns the object even when initialization fails. A native
     * caller must stop instead of treating an uninitialized lock as usable. */
    return b->calls->probe(b->context,obj) ? obj : NULL;
}
#endif
