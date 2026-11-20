/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_meta_v587.h"
#include "arena_seed_v577.h"
#include <cassert>
int main() {
    alignas(16) unsigned char mem[128]={};
    BbHeapV581 h{};
    const auto p=reinterpret_cast<uintptr_t>(mem+16);
    const auto next=p+32;
    h.lowest_payload=p;
    h.highest_payload=p+96;
    bb_arena_qword_v577(mem+8,next|1);
    bb_arena_qword_v577(mem+56,2);
    assert(bb_arena_header_live_v587(&h,p));
    assert(!bb_arena_header_live_v587(&h,p+1));
    assert(!bb_arena_header_live_v587(&h,p-16));
    mem[56]=0;
    assert(!bb_arena_header_live_v587(&h,p));
    bb_arena_qword_v577(mem+8,(p+112)|1);
    assert(!bb_arena_header_live_v587(&h,p));
    unsigned char out[]={1,2,3,4,5};
    assert(!bb_arena_kind_v587(out,3) && out[0]==1);
    assert(bb_arena_kind_v587(out,5) && out[0]==0x3b && !out[1] && !out[2] && !out[3] && out[4]==5);
}
