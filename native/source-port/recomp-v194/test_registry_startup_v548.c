/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "registry_startup_v548.h"
struct state { ShytStartupRwlockV414 *writer; unsigned calls,mode; unsigned char data[24]; };
static enum bb_alloc_v548 alloc(void *x,uint64_t owner,size_t n,struct bb_vector_block_v541 *out) {
    struct state *s=x;
    if (s->calls++ || owner!=0x4000 || n!=24 || !s->writer->held) return BB_ALLOC_ERROR;
    if (s->mode<2) return BB_ALLOC_NO_SPACE;
    if (s->mode==2) return BB_ALLOC_ERROR;
    *out=(struct bb_vector_block_v541){s->data,sizeof s->data,0x5000};
    return BB_ALLOC_OK;
}
static int release(void *x,uint64_t owner,uint64_t va) { (void)x; (void)owner; (void)va; return 0; }
static int warn(void *x) { (void)x; return 0; }
int main(void) {
    for (unsigned i=0;i<4;++i) {
        unsigned char h[40]={0},tls[80]={0};
        ShytStartupRwlockV414 lock={0}; struct state s={.writer=&lock,.mode=i};
        const struct bb_registry_driver_v548 d={&s,alloc,release};
        const struct bb_registry_tls_v548 t={tls,sizeof tls,48,0x1000,0x9999,-24,-8,-48};
        bb_arena_store_v527(h+32,0x4000); tls[40]=(unsigned char)(i!=0);
        if (!shyt_rw_init_v414(&lock)) return 1;
        const struct bb_registry_result_v548 r=bb_registry_startup_v548(&lock,&t,h,sizeof h,
            0x2000,NULL,7,100,16,warn,NULL,&d);
        if (s.calls!=1 || !r.unlocked || lock.held || tls[32]!=0xfb ||
            bb_vector_word_v541(tls+24)!=0x9999 || !shyt_rw_destroy_v414(&lock)) return 2;
        if (i==3) {
            if (r.insert!=BB_INSERT_OK || bb_vector_word_v541(h+8)!=0x5000 ||
                bb_vector_word_v541(s.data+16)!=116) return 3;
        } else if (r.insert!=BB_INSERT_STOP || bb_vector_word_v541(h+8) ||
                   bb_vector_word_v541(h+16) || bb_vector_word_v541(h+24)) return 4;
        if (r.action.kind!=(i==0?BB_TX_REPORT:i==1?BB_TX_TRANSFER:BB_TX_INVALID) ||
            r.action.argument!=(i==1?0x1000u:0u) || r.action.value!=(i==0?0x109u:i==1?1u:0u)) return 5;
    }
    return 0;
}
