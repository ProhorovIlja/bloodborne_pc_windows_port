/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "libc_strncmp_v629.c"
#include <assert.h>

int main(void) {
    for (unsigned a=0;a<256;++a) for (unsigned b=0;b<256;++b) {
        const unsigned char x[]={(unsigned char)a,0},y[]={(unsigned char)b,0};
        assert(bb_libc_strncmp_v629((const char *)x,(const char *)y,1)==(a>b)-(a<b));
        assert(bb_libc_strncmp_v629((const char *)x,(const char *)y,0)==0);
    }
    assert(bb_libc_strncmp_v629("long prefix x","long prefix y",12)==0);
    assert(bb_libc_strncmp_v629("long prefix x","long prefix y",13)==-1);
    assert(bb_libc_strncmp_v629("a\0x","a\0y",3)==0);
    return 0;
}
