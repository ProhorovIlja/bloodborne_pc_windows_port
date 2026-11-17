/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "libc_wide_v630.c"
#include <assert.h>

int main(void) {
    const uint16_t a[]={0x8000,0,0xffff,0}, b[]={0x8000,0,0x7fff,0};
    assert(bb_libc_wcslen_v630(a)==1);
    assert(bb_libc_wcscmp_v630(a,b)==0);
    assert(bb_libc_wcsncmp_v630(a,b,4)==0);
    assert(bb_libc_wmemcmp_v630(a,b,4)==1);
    assert(bb_libc_wmemchr_v630(a,0,4)==a+1);
    assert(bb_libc_wmemchr_v630(a,0xffff,4)==a+2);
    assert(!bb_libc_wmemchr_v630(a,0xffff,2));
    assert(bb_libc_wmemcmp_v630(NULL,NULL,0)==0);
    assert(bb_libc_wcsncmp_v630(NULL,NULL,0)==0);
    assert(!bb_libc_wmemchr_v630(NULL,0,0));
    for (unsigned i=0;i<=UINT16_MAX;++i) {
        const uint16_t x[]={(uint16_t)i,0}, y[]={0x8000,0};
        const int expected=(i>0x8000)-(i<0x8000);
        assert(bb_libc_wcscmp_v630(x,y)==expected);
        assert(bb_libc_wcsncmp_v630(x,y,1)==expected);
        assert(bb_libc_wmemcmp_v630(x,y,1)==expected);
    }
    return 0;
}
