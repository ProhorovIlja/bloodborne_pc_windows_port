/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dispatch_v487.h"
#ifdef BB_ENABLE_V488
#include "alu_v488.h"
#endif
#ifndef V487_ROUTES
#define V487_ROUTES "routes_v487.inc"
#endif
#include V487_ROUTES

enum bb_status_v487 bb_dispatch_v487(uint64_t id, const struct bb_input_v487 *in,
    const struct bb_region_v478 *mem, struct bb_result_v484 *out) {
    if (!in || !out) return BB_MISS_V487;
    size_t lo=0, hi=sizeof(memory_routes)/sizeof(memory_routes[0]);
    const size_t n=hi;
    while (lo<hi) {
        size_t mid=lo+(hi-lo)/2;
        if (memory_routes[mid].id<id) lo=mid+1; else hi=mid;
    }
    if (lo<n && memory_routes[lo].id==id) {
        uint64_t value;
        if (!bb_load_v486(memory_routes[lo].target,in->rdi,mem,&value)) return BB_READ_DENIED_V487;
        *out=(struct bb_result_v484){value,in->flags,0x8d5};
        return BB_OK_V487;
    }
#ifdef BB_ENABLE_V488
    if (bb_alu_call_v488(id,in->rax,in->rcx,in->rdx,in->rsi,in->rdi,in->flags,out))
        return BB_OK_V487;
#endif
    return bb_call_v485(id,in->rax,in->rcx,in->rdx,in->rsi,in->rdi,in->flags,out) ?
        BB_OK_V487 : BB_MISS_V487;
}
