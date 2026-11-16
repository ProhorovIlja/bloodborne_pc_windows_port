/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_MUTEX_GATE_V574_H
#define BB_MUTEX_GATE_V574_H
#include <stddef.h>
#include <stdint.h>

/* Single-threaded startup adapter. Separate from a general C++ guard or
 * pthread mutex. The callbacks implement the profile-specific helpers. */
struct bb_mutex_gate_v574 {
    size_t object, ready, guard;
    uint64_t table;
};
struct bb_mutex_calls_v574 {
    int (*acquire)(void *, unsigned char *);
    void (*release)(void *, unsigned char *);
    unsigned char (*probe)(void *, unsigned char *);
    int (*init)(void *, unsigned char *);
};
static inline int bb_mutex_gate_v574(unsigned char *data, size_t n,
    struct bb_mutex_gate_v574 x, const struct bb_mutex_calls_v574 *f, void *ctx) {
    if (!data || n<17 || x.object>n-17 || x.ready>=n || x.guard>=n ||
        x.ready==x.guard || (x.ready>=x.object && x.ready-x.object<17) ||
        (x.guard>=x.object && x.guard-x.object<17) || !x.table ||
        !f || !f->acquire || !f->release || !f->probe || !f->init) return 0;
    unsigned char *obj=data+x.object, *g=data+x.guard;
    if (!*g && f->acquire(ctx,g)) {
        data[x.ready]=0;
        f->release(ctx,g);
    }
    if (!data[x.ready]) {
        obj[16]=0;
        for (unsigned i=0;i<8;++i) obj[i]=(unsigned char)(x.table>>(8*i));
        if (!f->probe(ctx,obj) && !f->init(ctx,obj+8)) obj[16]=1;
        data[x.ready]=1;
    }
    return 1;
}
#endif
