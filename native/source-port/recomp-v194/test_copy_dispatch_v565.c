/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "copy_dispatch_v565.h"
int main(void) {
    const struct bb_copy_entry_v565 entries[]={{0x10,0,2},{0x40,2,1}};
    struct bb_copy_write_v565 writes[]={{0x1000,0},{0x1000,1},{0x1010,0}};
    const unsigned char pool[32]={0xa5,[16]=0x5a};
    unsigned char data[32]={0}, zero[32]={0};
#define RUN(a) bb_copy_dispatch_v565(entries,2,writes,3,pool,2,(a),data,0x1000,sizeof data)
    if (RUN(0x20)!=BB_COPY_MISS || memcmp(data,zero,32)) return 1;
    writes[1].dst=0x1020;
    if (RUN(0x10)!=BB_COPY_INVALID || memcmp(data,zero,32)) return 2;
    writes[1].dst=0x1000;
    writes[1].constant=2;
    if (RUN(0x10)!=BB_COPY_INVALID || memcmp(data,zero,32)) return 3;
    writes[1].constant=1;
    if (RUN(0x10)!=BB_COPY_OK || memcmp(data,pool+16,16) || memcmp(data+16,zero,16)) return 4;
    if (RUN(0x40)!=BB_COPY_OK || memcmp(data,pool+16,16) || memcmp(data+16,pool,16)) return 5;
    return 0;
}
