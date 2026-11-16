/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_ro_v476.c"

int main(void) {
    const unsigned char pool[]={'x',0,'a','b'};
    const struct bb_ro_row_v476 rows[]={{100,0,2},{200,2,2}};
    const struct bb_ro_row_v476 bad[]={{100,0,2},{101,2,2}};
    const struct bb_ro_row_v476 wrap[]={{UINT64_MAX,0,4}};
    struct bb_ro_v476 view={0};
    unsigned char data[2]={9,9};
    size_t n=9;
    if (bb_ro_bind_v476(&view,bad,2,pool,4) || bb_ro_bind_v476(&view,wrap,1,pool,4) ||
        bb_ro_bind_v476(&view,rows,2,pool,3) || view.count) return 1;
    if (!bb_ro_bind_v476(&view,rows,2,pool,4) || bb_ro_bind_v476(&view,rows,2,pool,4)) return 2;
    if (bb_ro_read_v476(&view,101,data,2) || bb_ro_read_v476(&view,199,data,1) ||
        data[0]!=9 || data[1]!=9 || bb_ro_strlen_v476(&view,200,&n) || n!=9) return 3;
    if (!bb_ro_read_v476(&view,200,data,2) || memcmp(data,"ab",2) ||
        !bb_ro_strlen_v476(&view,100,&n) || n!=1 || !bb_ro_strlen_v476(&view,101,&n) || n) return 4;
    return 0;
}
