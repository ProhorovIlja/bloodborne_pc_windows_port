/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_seed_v527.h"
#include <string.h>
static uint64_t get(const unsigned char *p) {
    uint64_t v=0;
    for (unsigned i=0;i<8;++i) v|=(uint64_t)p[i]<<(8*i);
    return v;
}
int main(void) {
    unsigned char obj[1200], arena[256];
    memset(obj,0xa5,sizeof obj); memset(arena,0xa5,sizeof arena);
    const uint64_t o=0x1000, a=0x8000, head=o+8+24+16*7;
    if (bb_arena_seed_v527(obj,sizeof obj,8,o,arena,sizeof arena,o+8) ||
        bb_arena_seed_v527(obj,100,8,o,arena,sizeof arena,a) ||
        bb_arena_seed_v527(obj,sizeof obj,8,o,arena,sizeof arena,UINT64_MAX-64) ||
        obj[8]!=0xa5 || arena[8]!=0xa5) return 1;
    if (!bb_arena_seed_v527(obj,sizeof obj,8,o,arena,sizeof arena,a)) return 2;
    if (get(obj+8)!=128 || get(obj+16)!=a+16 || get(obj+24)!=a+240 ||
        get(obj+32)!=224 || get(obj+8+40+16*7)!=a ||
        get(obj+8+48+16*7)!=a || get(obj+8+40)!=o+32 ||
        get(arena+8)!=((a+224)|2) || get(arena+16)!=head ||
        get(arena+24)!=head || get(arena+224)!=a || get(arena+232)!=(a|1) ||
        obj[0]!=0xa5 || obj[1199]!=0xa5 || arena[0]!=0xa5 || arena[240]!=0xa5) return 3;
    return 0;
}
