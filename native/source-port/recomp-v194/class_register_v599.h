/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLASS_REGISTER_V599_H
#define BB_CLASS_REGISTER_V599_H
#include "class_table_v554.h"
#include "class_secondary_v557.h"

struct bb_class_vector_v599 {
    unsigned char *header;
    uint64_t va;
    struct bb_vector_block_v541 live;
};
struct bb_class_ops_v599 {
    void *ctx;
    int (*field)(void *,uint64_t,unsigned,uint64_t *);
    int (*alloc)(void *,uint64_t,size_t,struct bb_vector_block_v541 *);
    int (*release)(void *,uint64_t,uint64_t);
};
enum bb_register_v599 { BB_REG_INVALID, BB_REG_PRIMARY_STOP,
    BB_REG_SECONDARY_STOP, BB_REG_OK };

struct bb_class_secondary_v599 { const struct bb_class_ops_v599 *op; };
static inline int bb_class_key_v599(void *v,uint64_t d,unsigned i,uint64_t *out) {
    const struct bb_class_ops_v599 *o=((struct bb_class_secondary_v599 *)v)->op;
    return i<4 && o->field(o->ctx,d,i+2,out);
}
static inline int bb_class_alloc_v599(void *v,uint64_t a,size_t n,struct bb_vector_block_v541 *out) {
    const struct bb_class_ops_v599 *o=((struct bb_class_secondary_v599 *)v)->op;
    return o->alloc(o->ctx,a,n,out);
}
static inline int bb_class_release_v599(void *v,uint64_t a,uint64_t p) {
    const struct bb_class_ops_v599 *o=((struct bb_class_secondary_v599 *)v)->op;
    return o->release(o->ctx,a,p);
}
/* Serialized startup. name is the live, NUL-terminated native string
 * represented by slot 0x10. field(0/1) invokes 0x10/0x18; field(2..5)
 * invokes 0x20..0x38. The two vectors must not overlap each other.
 * A STOP is terminal for this startup session, not a retry invitation:
 * the primary insertion, reserve or earlier secondary appends may be live. */
static inline enum bb_register_v599 bb_class_register_v599(
    const struct bb_class_vector_v599 *p,const struct bb_class_vector_v599 *s,
    uint64_t descriptor,const struct bb_class_ops_v599 *op) {
    if (!p || !s || !p->header || !s->header || p->header==s->header ||
        !descriptor || !op || !op->field || !op->alloc || !op->release) return BB_REG_INVALID;
    uint64_t row[4]={descriptor,0,0,0};
    if (!op->field(op->ctx,descriptor,0,&row[1]) || !row[1] ||
        !op->field(op->ctx,descriptor,1,&row[2])) return BB_REG_INVALID;
    row[3]=strlen((const char *)(uintptr_t)row[1]);
    if (bb_class_insert_v554(p->header,40,p->va,&p->live,row,op->ctx,
            op->alloc,op->release)!=BB_CLASS_OK) return BB_REG_PRIMARY_STOP;
    struct bb_class_secondary_v599 wrap={op};
    return bb_secondary_insert_v557(s->header,40,s->va,&s->live,descriptor,&wrap,
            bb_class_key_v599,bb_class_alloc_v599,bb_class_release_v599)==BB_SEC_OK?BB_REG_OK:BB_REG_SECONDARY_STOP;
}
#endif
