/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "pending_sort_v652.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static size_t live;
static void *alloc(void *ctx, size_t n, size_t alignment) {
    (void)ctx;
    assert(alignment == 8);
    void *p = malloc(n);
    if (p) ++live;
    return p;
}
static void release(void *ctx, void *p) {
    (void)ctx;
    assert(live);
    --live;
    free(p);
}
int main(void) {
    struct bb_registry_v651 v = {0};
    const struct bb_registry_allocator_v651 a = {NULL,alloc,release};
    const uint64_t keys[] = {UINT64_MAX,0,UINT64_C(1)<<63,INT64_MAX};
    for (size_t i = 1; i <= 8; ++i) {
        const struct bb_registry_row_v650 row = {i,1,0,i};
        assert(bb_registry_register_small_v652(&v,&a,row,keys));
        assert(v.count == i && v.used == 4*i && live == 2);
        for (size_t j = 0; j < i; ++j) {
            static const size_t order[] = {2,0,1,3};
            for (size_t k = 0; k < 4; ++k) {
                assert(v.pending[k*i+j].target == keys[order[k]]);
                assert(v.pending[k*i+j].object == j+1);
            }
        }
    }
    struct bb_pending_v651 copy[32];
    memcpy(copy,v.pending,sizeof copy);
    assert(!bb_registry_register_small_v652(&v,&a,(struct bb_registry_row_v650){9,1,0,9},keys));
    assert(v.count == 8 && v.used == 32 && live == 2 && !memcmp(copy,v.pending,sizeof copy));
    assert(!bb_pending_sort_v652(copy,33) && !memcmp(copy,v.pending,sizeof copy));
    assert(bb_pending_sort_v652(NULL,0) && !bb_pending_sort_v652(NULL,1));
    release(NULL,v.rows);
    release(NULL,v.pending);
    assert(!live);
    puts("8 registrations, signed keys, stable equal keys, no mutation above 32: OK");
}
