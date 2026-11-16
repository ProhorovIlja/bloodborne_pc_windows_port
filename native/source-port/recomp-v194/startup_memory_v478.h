/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_STARTUP_MEMORY_V478_H
#define BB_STARTUP_MEMORY_V478_H
#include <stddef.h>
#include <stdint.h>

struct bb_region_v478 { uint64_t base; size_t size; unsigned char *data; };
struct bb_memory_v478 { struct bb_region_v478 data, stack; };

/* Single-controller startup. Buffers are caller-owned, disjoint host spans.
 * This is not a general guest-memory API. Never map executable bytes here. */
static inline int bb_memory_bind_v478(struct bb_memory_v478 *m,
        struct bb_region_v478 data, struct bb_region_v478 stack) {
    if (!m || m->data.data || m->stack.data || !data.data || !stack.data ||
        !data.base || !stack.base || !data.size || !stack.size ||
        data.size > UINT64_MAX-data.base || stack.size > UINT64_MAX-stack.base ||
        (data.base+data.size > stack.base && stack.base+stack.size > data.base)) return 0;
    *m=(struct bb_memory_v478){data,stack};
    return 1;
}

static inline unsigned char *bb_memory_at_v478(const struct bb_region_v478 *r,
        uint64_t address, size_t width) {
    if (!r->data || !width || width>r->size || address<r->base ||
        address-r->base>r->size-width) return NULL;
    return r->data+(size_t)(address-r->base);
}

/* V464/V465 read receiver, vtable and fields from relocated data only. */
static inline int bb_data_read64_v478(void *ctx,uint64_t address,uint64_t *out) {
    struct bb_memory_v478 *m=ctx;
    if (!m || !out) return 0;
    const unsigned char *p=bb_memory_at_v478(&m->data,address,8);
    if (!p) return 0;
    uint64_t v=0;
    for (unsigned i=0;i<8;++i) v|=(uint64_t)p[i]<<(8*i);
    *out=v;
    return 1;
}

/* V464 sret may write only the controller's dedicated result scratch. */
static inline int bb_stack_write32_v478(void *ctx,uint64_t address,uint32_t v) {
    struct bb_memory_v478 *m=ctx;
    if (!m) return 0;
    unsigned char *p=bb_memory_at_v478(&m->stack,address,4);
    if (!p) return 0;
    for (unsigned i=0;i<4;++i) p[i]=(unsigned char)(v>>(8*i));
    return 1;
}
#endif
