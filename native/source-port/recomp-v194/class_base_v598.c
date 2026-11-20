/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class90_v597.c"

/* The descriptor getter and constructor run on serialized startup. The
 * allocator cache is shared with #90; storage is owned by the caller. */
unsigned char *bb_class_base_v598(BbClass90State597 *base,void **allocator,
                                 const BbClass90Ops597 *op) {
    if (sizeof(uintptr_t)!=8 || !base || !allocator || !op || !op->prepare ||
        !op->get_allocator || !op->kind || !op->diagnose || !op->base_table ||
        !op->class_table) return NULL;
    if (base->published) return base->published;
    if (op->prepare(op->ctx)) return NULL;
    unsigned char *d=base->descriptor;
    write597(d,op->base_table);
    memset(d+8,0,16);
    if (!*allocator) *allocator=op->get_allocator(op->ctx);
    if (!*allocator) return NULL;
    if (!(op->kind(op->ctx,*allocator)&0x20)) {
        op->diagnose(op->ctx,0x3e);
        return NULL;
    }
    memset(d+0x20,0,24);
    write597(d+0x38,(uintptr_t)*allocator);
    write597(d,op->class_table);
    memset(d+0x40,0,16);
    return base->published=d;
}
