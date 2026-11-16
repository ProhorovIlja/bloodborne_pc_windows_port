/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_sort_v556.h"
int main(void) {
    static const size_t ns[]={32,33,41,42,513};
    static const uint64_t sums[][2]={
        {UINT64_C(0xd603853c438d7e52),UINT64_C(0xd603853c438d7e52)},
        {UINT64_C(0x15e1c2856fd9fba7),UINT64_C(0x1822dd4d417a495)},
        {UINT64_C(0x41e5851b21143013),UINT64_C(0x6cadf8fc21a711e9)},
        {UINT64_C(0x843e886ea1b8b51b),UINT64_C(0x1c4a08a6d762de79)},
        {UINT64_C(0xb2b25d7e1dec1f73),UINT64_C(0x2a501f73c2b0d9b3)},
    };
    unsigned char b[513*16+2];
    unsigned char *p=b+1;
    if (!bb_class_sort_v556(NULL,0,0) || bb_class_sort_v556(p,15,1) ||
        bb_class_sort_v556(NULL,16,1) || bb_class_sort_v556(p,sizeof b-2,514)) return 1;
    for (size_t j=0;j<sizeof ns/sizeof *ns;++j) for (unsigned k=0;k<2;++k) {
        const size_t n=ns[j];
        b[0]=0xc3; p[16*n]=0xa5;
        for (size_t i=0;i<n;++i) {
            bb_arena_store_v527(p+16*i,(uint64_t)((int)((17*i)%11)-5));
            bb_arena_store_v527(p+16*i+8,i+1);
        }
        if (k) {
            if (!bb_class_sort_v556(p,16*n,n)) return 2;
        } else bb_class_sort_rows_v556(p,n,0);
        uint64_t h=0;
        for (size_t i=0;i<n;++i) {
            if (i && bb_class_key_v556(p,i-1)>bb_class_key_v556(p,i)) return 3;
            h=131*h+bb_vector_word_v541(p+16*i+8);
        }
        if (h!=sums[j][k] || b[0]!=0xc3 || p[16*n]!=0xa5) return 4;
    }
    return 0;
}
