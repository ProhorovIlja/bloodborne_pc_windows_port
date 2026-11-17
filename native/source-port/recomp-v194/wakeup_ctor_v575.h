/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_WAKEUP_CTOR_V575_H
#define BB_WAKEUP_CTOR_V575_H
#include "mutex_gate_v574.h"
/* Translated callers only. The published hook and table must be native
 * bindings. The diagnostic callback owns downstream logging/error policy.
 * Single-threaded; callbacks must not reenter or mutate the profile. */
struct bb_wakeup_v575 {
    struct bb_mutex_gate_v574 gate;
    size_t published;
    uint64_t hook;
};
typedef void (*bb_wakeup_diag_v575)(void *);
static inline int bb_wakeup_ctor_v575(unsigned char *data,size_t n,
    struct bb_wakeup_v575 x,const struct bb_mutex_calls_v574 *f,
    bb_wakeup_diag_v575 diagnostic,void *ctx) {
    const size_t p=x.published,o=x.gate.object,r=x.gate.ready,g=x.gate.guard;
    if (!data || n<17 || o>n-17 || p>n-8 || r>=n || g>=n ||
        ((p|o)&7) || (p<o+17 && o<p+8) || (r>=p && r<p+8) ||
        (g>=p && g<p+8) || r==g || (r>=o && r<o+17) ||
        (g>=o && g<o+17) || !x.hook || !x.gate.table || !diagnostic ||
        !f || !f->acquire || !f->release || !f->probe || !f->init) return 0;
    for (unsigned i=0;i<8;++i) data[p+i]=(unsigned char)(x.hook>>(8*i));
    (void)bb_mutex_gate_v574(data,n,x.gate,f,ctx);
    if (!f->probe(ctx,data+o)) diagnostic(ctx);
    return 1;
}
#endif
