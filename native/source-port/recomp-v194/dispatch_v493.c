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
#ifdef BB_WITH_RIP_V497
#include "dispatch_v497.h"
#include "rip.c"
#endif
#include "index_v493.inc"
#include "routes_v487.inc"
#include "load_route_v504.h"
_Static_assert(sizeof bb_ids_v493/sizeof *bb_ids_v493 == sizeof bb_routes_v493/sizeof *bb_routes_v493,
    "dispatch ID and route counts must agree");
#ifdef BB_WITH_RIP_V497
_Static_assert(BB_ROUTE_BITS_V493==3,"V497 requires a five-family generated index");
enum bb_status_v492 bb_dispatch_v497(uint64_t id,const struct bb_input_v487 *in,
    const struct bb_region_v478 *read,const struct bb_write_region_v492 *write,
    uint64_t slide,struct bb_result_v484 *out) {
#else
_Static_assert(BB_ROUTE_BITS_V493==2,"V493 requires a four-family generated index");

enum bb_status_v492 bb_dispatch_v493(uint64_t id,const struct bb_input_v487 *in,
    const struct bb_region_v478 *read,const struct bb_write_region_v492 *write,struct bb_result_v484 *out) {
#endif
    if(!in||!out) return BB_MISS_V492;
    const size_t n=sizeof bb_ids_v493/sizeof bb_ids_v493[0];
    size_t lo=0,hi=n;
    while(lo<hi){size_t m=lo+(hi-lo)/2;if(bb_ids_v493[m]<id)lo=m+1;else hi=m;}
    if(lo==n||bb_ids_v493[lo]!=id)return BB_MISS_V492;
    const uint32_t code=bb_routes_v493[lo];
    const size_t k=code>>BB_ROUTE_BITS_V493;
    switch(code&((1u<<BB_ROUTE_BITS_V493)-1)) {
    case 0:
        if(k>=sizeof table/sizeof *table || table[k].id!=id)return BB_MISS_V492;
        *out=table[k].fn(in->rax,in->rcx,in->rdx,in->rsi,in->rdi,in->flags);
        return BB_OK_V492;
    case 1: {
        if(k>=sizeof load_rows_v493/sizeof *load_rows_v493 ||
           !bb_load_matches_v504(id,load_rows_v493[k].id))return BB_MISS_V492;
        uint64_t value;
        if(!load_row_v486(k,in->rdi,read,&value))return BB_READ_DENIED_V492;
        *out=(struct bb_result_v484){value,in->flags,0x8d5};
        return BB_OK_V492;
    }
    case 2:
        if(k>=sizeof alu_rows_v493/sizeof *alu_rows_v493 || alu_rows_v493[k].id!=id)return BB_MISS_V492;
        *out=alu_rows_v493[k].fn(in->rax,in->rcx,in->rdx,in->rsi,in->rdi,in->flags);
        return BB_OK_V492;
    case 3: {
        if(k>=sizeof stores/sizeof *stores || stores[k].id!=id)return BB_MISS_V492;
        const struct bb_store_input_v491 s={in->rdi,in->rsi,in->rdx,in->rcx};
        const struct bb_result_v484 result={in->rax,in->flags,0x8d5};
        if(store_row_v491(stores+k,&s,write?write->bytes:NULL,write?write->base:0,write?write->size:0)
           !=BB_STORE_OK_V491)return BB_WRITE_DENIED_V492;
        *out=result;
        return BB_OK_V492;
    }
#ifdef BB_WITH_RIP_V497
    case 4:
        if(k>=sizeof rip_rows_v496/sizeof *rip_rows_v496||rip_rows_v496[k].id!=id)return BB_MISS_V492;
        return rip_row_v496(k,slide,in->flags,out)==BB_RIP_OK_V496?BB_OK_V492:BB_ADDRESS_DENIED_V497;
#endif
    default: return BB_MISS_V492;
    }
}
