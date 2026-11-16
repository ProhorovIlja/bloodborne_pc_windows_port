/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_FACTORY_SEED_V538_H
#define BB_FACTORY_SEED_V538_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* Object body only. Caller owns guard, mutex, and publication. The child
 * callback receives an opaque guest address; failure leaves a partial object. */
static inline void bb_factory_put_v538(unsigned char *p,uint64_t value,unsigned bytes) {
    for (unsigned i=0;i<bytes;++i) p[i]=(unsigned char)(value>>(i*8));
}
static inline int bb_factory_seed_v538(unsigned char *p,size_t size,uint64_t va,
        uint64_t table0,uint64_t table1,uint64_t child_table,
        int (*init_child)(void *,uint64_t),void *ctx) {
    if (!p || size<0x48c || !va || (va&7) || va>UINT64_MAX-0x48c ||
        !table0 || !table1 || !child_table || !init_child) return 0;
    memset(p,0,0x440);
    bb_factory_put_v538(p+0x440,table0,8);
    p[0x450]=0;
    bb_factory_put_v538(p+0x458,table1,8);
    bb_factory_put_v538(p+0x460,va,8);
    bb_factory_put_v538(p+0x468,0,8);
    p[0x480]=0;
    bb_factory_put_v538(p+0x470,child_table,8);
    if (!init_child(ctx,va+0x470)) return 0;
    bb_factory_put_v538(p+0x488,0,4);
    return 1;
}
#endif
