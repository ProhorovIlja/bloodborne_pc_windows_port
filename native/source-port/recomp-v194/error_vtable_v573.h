/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ERROR_VTABLE_V573_H
#define BB_ERROR_VTABLE_V573_H
#include "guarded_publish_v569.h"
#include "error_message_v571.h"
#include "error_destructor_v572.h"

/* A native address point with seven typed slots. Only translated callers
 * may use it: the context and explicit result pointers are host ABI. */
struct bb_error_context_v573 {
    struct bb_error_categories_v570 cats;
    bb_error_lookup_v571 lookup;
    bb_error_known_v570 known;
    bb_message_alloc_v571 alloc;
    bb_error_release_v572 release;
    void *user;
};
struct bb_error_slots_v573 {
    void (*destroy)(void *);
    int (*deleting)(const struct bb_error_context_v573 *,void *);
    const char *(*name)(void);
    int (*message)(const struct bb_error_context_v573 *,uint64_t,int32_t,struct bb_message_v571 *);
    int (*condition)(const struct bb_error_context_v573 *,uint64_t,int32_t,struct bb_error_value_v570 *);
    int (*equiv_condition)(const struct bb_error_context_v573 *,uint64_t,int32_t,struct bb_error_value_v570);
    int (*equiv_code)(uint64_t,struct bb_error_value_v570,int32_t);
};
static inline int bb_deleting_v573(const struct bb_error_context_v573 *c,void *p) {
    const uint64_t id=(uintptr_t)p;
    return c && !bb_error_name_v570(c->cats,id) && bb_error_delete_v572(p,c->release,c->user);
}
static inline int bb_message_slot_v573(const struct bb_error_context_v573 *c,uint64_t self,
    int32_t code,struct bb_message_v571 *out) {
    return c && bb_error_message_v571(c->cats,self,code,c->lookup,c->alloc,c->user,out);
}
static inline int bb_condition_slot_v573(const struct bb_error_context_v573 *c,uint64_t self,
    int32_t code,struct bb_error_value_v570 *out) {
    return c && bb_error_default_v570(c->cats,self,code,c->known,c->user,out);
}
/* -1 is a missing binding, not a false comparison. */
static inline int bb_equiv_condition_v573(const struct bb_error_context_v573 *c,uint64_t self,
    int32_t code,struct bb_error_value_v570 x) {
    struct bb_error_value_v570 out;
    return bb_condition_slot_v573(c,self,code,&out) ? bb_error_equal_v570(out,x) : -1;
}
static inline int bb_equiv_code_v573(uint64_t self,struct bb_error_value_v570 x,int32_t code) {
    return bb_error_equal_v570((struct bb_error_value_v570){(uint64_t)(uint32_t)code<<32,self},x);
}
static inline const char *bb_system_name_v573(void) { return "system"; }
static inline const char *bb_generic_name_v573(void) { return "generic"; }
static inline const char *bb_iostream_name_v573(void) { return "iostream"; }
static inline const struct bb_error_slots_v573 *bb_error_slots_v573(unsigned id) {
#define BB_SLOTS_V573(n) {bb_error_destroy_v572,bb_deleting_v573,n,bb_message_slot_v573, \
    bb_condition_slot_v573,bb_equiv_condition_v573,bb_equiv_code_v573}
    static const struct bb_error_slots_v573 table[]={BB_SLOTS_V573(bb_system_name_v573),
        BB_SLOTS_V573(bb_generic_name_v573),BB_SLOTS_V573(bb_iostream_name_v573)};
#undef BB_SLOTS_V573
    return id<3 ? table+id : NULL;
}
struct bb_publish_row_v573 { size_t dst; unsigned category; };
/* Immutable, disjoint rows; single-threaded, little-endian 64-bit data.
 * This does not synthesize missing intervening constructors. */
static inline int bb_publish_sequence_v573(unsigned char *data,size_t size,
    const struct bb_publish_row_v573 *rows,size_t n) {
    if (!data || !rows || !n || size<16 || sizeof(uintptr_t)!=8) return 0;
    for (size_t i=0;i<n;++i)
        if (rows[i].category>=3 || (rows[i].dst&7) || rows[i].dst>size-16) return 0;
    for (size_t i=0;i<n;++i) {
        const size_t d=rows[i].dst;
        if (!bb_guarded_publish_v569(data,size,d,d+8,(uintptr_t)bb_error_slots_v573(rows[i].category)))
            return 0;
    }
    return 1;
}
#endif
