/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "pure_virtual_slots_v634.h"
#include "libc_pure_virtual_v633.c"
#include <assert.h>

int main(void) {
    enum { n = 2613 };
    struct bb_v634_reloc src[n];
    struct bb_v634_slot dst[n];
    BbV634Target t=bb_libc_pure_virtual_resolve_v633("zr094EQ39Ww", "libc", 257, "libc", 1, 2);
    for (size_t i=0; i<n; ++i) {
        src[i]=(struct bb_v634_reloc){16*i+8,1,0};
        dst[i]=(struct bb_v634_slot){UINT64_MAX,NULL};
    }
    const uint64_t extent=16*n;
    assert(!bb_v634_build(src,n,extent,t,dst,n-1));
    const struct bb_v634_reloc old=src[n-1];
    const struct bb_v634_reloc invalid[]={{old.offset,7,0},{old.offset,1,16},
        {old.offset+1,1,0},{extent,1,0},{src[n-2].offset,1,0},{0,1,0}};
    for (size_t j=0;j<sizeof invalid/sizeof *invalid;++j) {
        src[n-1]=invalid[j];
        assert(!bb_v634_build(src,n,extent,t,dst,n));
        for (size_t i=0;i<n;++i) assert(dst[i].offset==UINT64_MAX && !dst[i].target);
    }
    src[n-1]=old;
    assert(bb_v634_build(src,n,extent,t,dst,n));
    for (size_t i=0;i<n;++i) {
        assert(bb_v634_lookup(dst,n,src[i].offset)==t);
        assert(!bb_v634_lookup(dst,n,src[i].offset-8));
    }
    assert(!bb_v634_lookup(dst,n,extent));
}
