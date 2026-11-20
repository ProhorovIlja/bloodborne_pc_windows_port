/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "registry_storage_v656.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static const size_t groups[][4] = {
#ifdef BB_PRIVATE_LAYOUT
#include "private_v656.inc"
#else
    {7,6,5,4}, {0,13,12,11}, {5,9,8,7}, {7,6,5,4},
#endif
};

static void *alloc(void *c,size_t n,size_t align) {
    (void)c;
    assert(align==8);
    return malloc(n);
}
static void release(void *c,void *p) { (void)c; free(p); }

int main(void) {
    const struct bb_registry_allocator_v651 allocator={NULL,alloc,release};
    const size_t count=sizeof groups/sizeof *groups;
    size_t size=1;
    for (size_t i=0;i<count;++i) for (size_t j=0;j<4;++j)
        if (groups[i][j]>=size) size=groups[i][j]+1;
    unsigned char *base[2]={calloc(size,1),calloc(size,1)};
    assert(base[0] && base[1] && base[0]!=base[1]);
    struct bb_registry_v651 reg[2]={0};
    for (size_t i=0;i<count;++i) for (size_t k=0;k<2;++k) {
        const struct bb_registry_row_v650 row={i+1,1,0,i%7};
        assert(bb_registry_register_storage_v656(&reg[k],&allocator,row,base[k],size,groups[i]));
    }
    unsigned seen[sizeof groups/sizeof *groups]={0};
    for (size_t i=0;i<4*count;++i) {
        const struct bb_pending_v651 a=reg[0].pending[i], b=reg[1].pending[i];
        const uint64_t off=a.target-(uintptr_t)base[0];
        assert(a.object && a.object<=count && a.object==b.object &&
               off==b.target-(uintptr_t)base[1]);
        assert(!i || reg[0].pending[i-1].target<=a.target);
        unsigned j=0;
        for (;j<4;++j) if (!(seen[a.object-1]&(1u<<j)) && groups[a.object-1][j]==off) break;
        assert(j<4);
        seen[a.object-1]|=1u<<j;
    }
    for (size_t i=0;i<count;++i) assert(seen[i]==15);
    const size_t invalid[4]={0,0,0,size};
    assert(!bb_registry_register_storage_v656(&reg[0],&allocator,
        (struct bb_registry_row_v650){1,1,0,0},base[0],size,invalid));
    assert(reg[0].count==count && reg[0].used==4*count);
    for (size_t k=0;k<2;++k) {
        free(reg[k].rows); free(reg[k].pending); free(base[k]);
    }
    printf("%zu groups, %zu address keys, two backing bases, OOB rejection OK\n",count,4*count);
    return 0;
}
