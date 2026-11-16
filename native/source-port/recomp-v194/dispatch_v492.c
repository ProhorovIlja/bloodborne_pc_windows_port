/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v492.h"
#include "store_v491.h"

enum bb_status_v492 bb_dispatch_v492(uint64_t id,const struct bb_input_v487 *in,
    const struct bb_region_v478 *read,const struct bb_write_region_v492 *write,struct bb_result_v484 *out) {
    if(!in||!out) return BB_MISS_V492;
    const struct bb_store_input_v491 s={in->rdi,in->rsi,in->rdx,in->rcx};
    const uint64_t old_rax=in->rax, old_flags=in->flags;
    const int w=bb_store_v491(id,&s,write?write->bytes:NULL,write?write->base:0,write?write->size:0);
    if(w==BB_STORE_DENIED_V491) return BB_WRITE_DENIED_V492;
    if(w==BB_STORE_OK_V491) {
        *out=(struct bb_result_v484){old_rax,old_flags,0x8d5};
        return BB_OK_V492;
    }
    switch(bb_dispatch_v487(id,in,read,out)) {
    case BB_OK_V487: return BB_OK_V492;
    case BB_READ_DENIED_V487: return BB_READ_DENIED_V492;
    default: return BB_MISS_V492;
    }
}
