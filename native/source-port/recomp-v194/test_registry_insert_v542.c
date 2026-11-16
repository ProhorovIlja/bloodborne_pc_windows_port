/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "registry_insert_v542.h"
static int warn(void *p) { ++*(int *)p; return 0; }
int main(void) {
    unsigned char h[40]={0}, data[96]={0};
    const struct bb_vector_block_v541 b={data,sizeof data,0x1000};
    bb_arena_store_v527(h+8,0x1000); bb_arena_store_v527(h+16,0x1000);
    bb_arena_store_v527(h+24,0x1060);
    int warnings=0;
    if (bb_registry_insert_v542(h,sizeof h,&b,10,100,50,warn,&warnings)!=BB_INSERT_OK ||
        bb_vector_word_v541(h+16)!=0x1018) return 1;
    if (bb_registry_insert_v542(h,sizeof h,&b,10,110,10,warn,&warnings)!=BB_INSERT_DUPLICATE ||
        bb_registry_insert_v542(h,sizeof h,&b,20,110,60,warn,&warnings)!=BB_INSERT_STOP ||
        warnings!=1 || bb_vector_word_v541(h+16)!=0x1018) return 2;
    if (bb_registry_insert_v542(h,sizeof h,&b,20,50,20,warn,&warnings)!=BB_INSERT_OK ||
        bb_vector_word_v541(data)!=20 || bb_vector_word_v541(data+24)!=10 ||
        bb_vector_word_v541(h+16)!=0x1030) return 3;
    bb_arena_store_v527(h+24,0x1030);
    if (bb_registry_insert_v542(h,sizeof h,&b,30,1,20,warn,&warnings)!=BB_INSERT_FULL ||
        bb_registry_insert_v542(h,sizeof h,&b,30,UINT64_MAX,2,warn,&warnings)!=BB_INSERT_INVALID) return 4;
    return 0;
}
