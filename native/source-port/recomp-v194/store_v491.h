/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_STORE_V491_H
#define BB_STORE_V491_H
#include <stddef.h>
#include <stdint.h>
struct bb_store_input_v491 { uint64_t rdi,rsi,rdx,rcx; };
struct store_v491 { uint64_t id,disp,value; unsigned width,source; };
enum { BB_STORE_MISS_V491, BB_STORE_OK_V491, BB_STORE_DENIED_V491 };
static inline int store_row_v491(const struct store_v491 *r,
        const struct bb_store_input_v491 *in,unsigned char *mem,uint64_t base,size_t size) {
    uint64_t addr=in->rdi+r->disp;
    if(!mem||size>UINT64_MAX-base||addr<base||r->width>size||addr-base>size-r->width||
       (r->width!=1&&r->width!=2&&r->width!=4&&r->width!=8)) return BB_STORE_DENIED_V491;
    uint64_t v;
    switch(r->source) {
    case 0: v=r->value; break;
    case 1: v=in->rcx; break;
    case 2: v=in->rdx; break;
    case 6: v=in->rsi; break;
    case 7: v=in->rdi; break;
    default: return BB_STORE_DENIED_V491;
    }
    for(unsigned i=0;i<r->width;++i) mem[addr-base+i]=(unsigned char)(v>>(8*i));
    return BB_STORE_OK_V491;
}
static inline int store_dispatch_v491(const struct store_v491 *rows,size_t count,
        uint64_t id,const struct bb_store_input_v491 *in,unsigned char *mem,uint64_t base,size_t size) {
    if(!in) return BB_STORE_MISS_V491;
    size_t lo=0,hi=count;
    while(lo<hi) { size_t m=lo+(hi-lo)/2; if(rows[m].id<id) lo=m+1; else hi=m; }
    if(lo==count||rows[lo].id!=id) return BB_STORE_MISS_V491;
    return store_row_v491(rows+lo,in,mem,base,size);
}
int bb_store_v491(uint64_t,const struct bb_store_input_v491 *,unsigned char *,uint64_t,size_t);
#endif
