/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CTOR_REGISTER_V537_H
#define BB_CTOR_REGISTER_V537_H
#include "ctor_publish_v536.h"
#include "ctor_link_v535.h"

enum bb_register_v537 { BB_REGISTER_OK, BB_REGISTER_OBJECT, BB_REGISTER_HEAD, BB_REGISTER_LINK };
/* The caller must validate the retail layout and complete both guard phases
 * first. Publication precedes linkage; on failure do not retry this route. */
static inline enum bb_register_v537 bb_ctor_register_v537(
        unsigned char *rw, size_t size, const struct bb_publish_layout_v536 *obj,
        const struct bb_publish_layout_v536 *head, void *ctx,
        int (*source)(void *,uint64_t *), int (*flags)(void *,uint64_t,uint32_t *),
        int (*flag_diag)(void *), int (*link_diag)(void *), size_t budget,
        int (*read_next)(void *,uint64_t,uint64_t *),
        int (*write_next)(void *,uint64_t,uint64_t)) {
    uint64_t a,b;
    if (bb_ctor_publish_v536(rw,size,obj,ctx,source,flags,flag_diag,&a)!=BB_PUBLISH_OK)
        return BB_REGISTER_OBJECT;
    if (bb_ctor_publish_v536(rw,size,head,ctx,source,flags,flag_diag,&b)!=BB_PUBLISH_OK)
        return BB_REGISTER_HEAD;
    return bb_ctor_link_v535(a,b,budget,ctx,read_next,link_diag,write_next)==BB_LINK_OK
        ? BB_REGISTER_OK : BB_REGISTER_LINK;
}
#endif
