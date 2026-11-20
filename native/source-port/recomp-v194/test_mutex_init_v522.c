/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "mutex_init_v522.h"
struct state { unsigned n, missing; uint32_t rc; };
static int hook(void *ctx, enum bb_mutex_op_v522 op, uint64_t object,
                uint64_t *attr, uint32_t type, uint32_t *rc) {
    struct state *s=ctx;
    if ((unsigned)op!=s->n++ || (unsigned)op==s->missing ||
        object!=(op==BB_MUTEX_INIT_V522?55u:0u) ||
        type!=(op==BB_ATTR_TYPE_V522?2u:0u) || *attr!=(op==BB_ATTR_INIT_V522?0u:99u)) return 0;
    *attr=99;
    *rc=op==BB_MUTEX_INIT_V522?s->rc:12u;
    return 1;
}
int main(void) {
    const uint32_t codes[]={0,0x8002000c,0x80020023,0x80020016,12,UINT32_MAX};
    for (unsigned i=0;i<sizeof codes/sizeof *codes;++i) {
        struct state s={0,4,codes[i]};
        struct bb_mutex_result_v522 r=bb_mutex_init_v522(55,hook,&s);
        if (s.n!=4 || r.status!=(i<3?BB_MUTEX_RETURN_V522:BB_MUTEX_DIAG_V522) ||
            r.value!=(i==0?0:i<3?UINT32_MAX:codes[i]) || r.line!=(i<3?0:i==3?57:59)) return 1;
    }
    for (unsigned i=0;i<4;++i) {
        struct state s={0,i,0};
        if (bb_mutex_init_v522(55,hook,&s).status!=BB_MUTEX_MISS_V522 || s.n!=i+1) return 2;
    }
    return 0;
}
