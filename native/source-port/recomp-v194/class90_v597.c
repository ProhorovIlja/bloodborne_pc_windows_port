/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* Serialized startup only. Callback pointers and descriptor chains must be
 * live. Registration/lookup are provided by the caller, not by this shell. */
typedef struct {
    unsigned char *published;
    void *allocator;
    _Alignas(8) unsigned char descriptor[0x50];
} BbClass90State597;
typedef struct {
    void *ctx;
    uintptr_t base_table, class_table, ascii_name, wide_name;
    int (*prepare)(void *);
    void *(*get_allocator)(void *);
    unsigned (*kind)(void *,void *);
    int (*insert)(void *,unsigned char *);
    unsigned char *(*get_base)(void *);
    void (*diagnose)(void *,unsigned);
} BbClass90Ops597;

static void write597(void *p,uintptr_t v) { memcpy(p,&v,8); }
static unsigned char *parent597(const unsigned char *p) {
    uintptr_t v; memcpy(&v,p+8,8); return (unsigned char *)v;
}
int bb_class90_v597(BbClass90State597 *s,const BbClass90Ops597 *o) {
    if (sizeof(uintptr_t)!=8 || !s || !o || !o->prepare || !o->get_allocator || !o->kind ||
        !o->insert || !o->get_base || !o->diagnose || !o->base_table || !o->class_table ||
        !o->ascii_name || !o->wide_name) return -1;
    unsigned char *d=s->published;
    if (!d) {
        if (o->prepare(o->ctx)) return -2;
        d=s->descriptor;
        write597(d,o->base_table);
        memset(d+8,0,16);
        if (!s->allocator) s->allocator=o->get_allocator(o->ctx);
        if (!s->allocator) return -3;
        if (!(o->kind(o->ctx,s->allocator)&0x20)) {
            o->diagnose(o->ctx,0x3e);
            return -3;
        }
        memset(d+0x20,0,24);
        write597(d+0x38,(uintptr_t)s->allocator);
        write597(d,o->class_table);
        memset(d+0x40,0,16);
        s->published=d;
    }
    write597(d+0x40,o->ascii_name);
    write597(d+0x48,o->wide_name);
    if (o->insert(o->ctx,d)) return -4;
    unsigned char *base=o->get_base(o->ctx), *fast=base;
    for (unsigned char *slow=base; slow; slow=parent597(slow)) {
        if (slow==d) goto cycle;
        if (fast) fast=parent597(fast);
        if (fast) fast=parent597(fast);
        if (fast && fast==parent597(slow)) goto cycle;
    }
    write597(d+8,(uintptr_t)base);
    return 0;
cycle:
    /* Retail reports self ancestry and can write the link if reporting
     * returns. Native leaves the parent unchanged, also for foreign cycles. */
    o->diagnose(o->ctx,0x192);
    return -5;
}
