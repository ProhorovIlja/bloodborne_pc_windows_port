/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v492.h"
#include "dispatch_v493.h"

/* Build together: the index ordinals and these four units are emitted in
 * the same private preparation run. Do not compile these units separately. */
#include "native.c"
#define rows load_rows_v493
#include "loads.c"
#undef rows
#define rows alu_rows_v493
/* Unique symbols for the generated ALU bodies; the generator emits them
 * with the prefix in prepare_v493.py. */
#include "alu.c"
#undef rows
#include "stores.c"
#include "index_v493.inc"

enum bb_status_v492 bb_dispatch_v493(uint64_t id,const struct bb_input_v487 *in,
    const struct bb_region_v478 *read,const struct bb_write_region_v492 *write,struct bb_result_v484 *out) {
    if(!in||!out) return BB_MISS_V492;
    const size_t n=sizeof bb_ids_v493/sizeof bb_ids_v493[0];
    size_t lo=0,hi=n;
    while(lo<hi){size_t m=lo+(hi-lo)/2;if(bb_ids_v493[m]<id)lo=m+1;else hi=m;}
    if(lo==n||bb_ids_v493[lo]!=id)return BB_MISS_V492;
    const uint32_t code=bb_routes_v493[lo];
    const size_t k=code>>2;
    switch(code&3) {
    case 0:
        if(k>=sizeof table/sizeof *table || table[k].id!=id)return BB_MISS_V492;
        *out=table[k].fn(in->rax,in->rcx,in->rdx,in->rsi,in->rdi,in->flags);
        return BB_OK_V492;
    case 1: {
        uint64_t value;
        if(!load_row_v486(k,in->rdi,read,&value))return BB_READ_DENIED_V492;
        *out=(struct bb_result_v484){value,in->flags,0x8d5};
        return BB_OK_V492;
    }
    case 2:
        if(k>=sizeof alu_rows_v493/sizeof *alu_rows_v493 || alu_rows_v493[k].id!=id)return BB_MISS_V492;
        *out=alu_rows_v493[k].fn(in->rax,in->rcx,in->rdx,in->rsi,in->rdi,in->flags);
        return BB_OK_V492;
    default: {
        if(k>=sizeof stores/sizeof *stores || stores[k].id!=id)return BB_MISS_V492;
        const struct bb_store_input_v491 s={in->rdi,in->rsi,in->rdx,in->rcx};
        const struct bb_result_v484 result={in->rax,in->flags,0x8d5};
        if(store_row_v491(stores+k,&s,write?write->bytes:NULL,write?write->base:0,write?write->size:0)
           !=BB_STORE_OK_V491)return BB_WRITE_DENIED_V492;
        *out=result;
        return BB_OK_V492;
    }}
}
