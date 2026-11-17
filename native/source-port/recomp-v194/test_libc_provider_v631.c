/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "libc_provider_v631.c"
#include <assert.h>

int main(void) {
    assert(sizeof routes631/sizeof *routes631==23);
    for (size_t i=0;i<sizeof routes631/sizeof *routes631;++i) {
        const BbLibcRoute631 *r=routes631+i;
        assert(bb_libc_resolve_v631(r->nid,"libc",0x101,"libc",1,2,r->signature)==r);
        assert(!bb_libc_resolve_v631(r->nid,"libc",0x100,"libc",1,2,r->signature));
        assert(!bb_libc_resolve_v631(r->nid,"libc",0x101,"libc",2,2,r->signature));
        assert(!bb_libc_resolve_v631(r->nid,"libc",0x101,"libc",1,1,r->signature));
        assert(!bb_libc_resolve_v631(r->nid,"libc",0x101,"other",1,2,r->signature));
        assert(!bb_libc_resolve_v631(r->nid,"other",0x101,"libc",1,2,r->signature));
        assert(!bb_libc_resolve_v631(r->nid,"libc",0x101,"libc",1,2,r->signature+1));
        for (size_t j=0;j<i;++j) assert(strcmp(r->nid,routes631[j].nid));
    }
    assert(!bb_libc_resolve_v631("unknown","libc",0x101,"libc",1,2,BB_LIBC631_copy));
    const BbLibcRoute631 *n=bb_libc_resolve_v631("aesyjrHVWy4","libc",0x101,"libc",1,2,BB_LIBC631_ncmp);
    assert(n && n->target.ncmp("a","z",1)==-1);
    const BbLibcRoute631 *w=bb_libc_resolve_v631("fnUEjBCNRVU","libc",0x101,"libc",1,2,BB_LIBC631_wchr);
    const uint16_t units[]={0xffff,0,0x8000};
    assert(w && w->target.wchr(units,0x8000,3)==units+2);
    return 0;
}
