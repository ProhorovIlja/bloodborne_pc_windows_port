/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "dependency_seed_v659.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    for (unsigned fill=0; fill<256; ++fill) {
        _Alignas(8) unsigned char p[0x498], expect[sizeof p];
        const struct bb_dependency_tables_v659 t={0x102,0x203,0x304};
        const uintptr_t self=(uintptr_t)p;
        memset(p, (int)fill, sizeof p);
        memset(expect, (int)fill, sizeof expect);
        assert(!bb_dependency_seed_v659(p,sizeof p,(struct bb_dependency_tables_v659){1,0,3}));
        assert(!bb_dependency_seed_v659(p,BB_DEPENDENCY_BYTES_V659-1,t));
        assert(!bb_dependency_seed_v659(p+1,sizeof p-1,t));
        assert(!memcmp(p,expect,sizeof p));
        memset(expect,0,0x440);
        const size_t offsets[]={0x440,0x458,0x460,0x468,0x470};
        const uintptr_t values[]={t.primary_lock,t.view,self,0,t.secondary_lock};
        for (size_t i=0;i<5;++i) memcpy(expect+offsets[i],values+i,8);
        expect[0x450]=expect[0x480]=0;
        memset(expect+0x488,0,4);
        assert(bb_dependency_seed_v659(p,sizeof p,t));
        assert(!memcmp(p,expect,sizeof p));
    }
    puts("V659: 256 object layouts and 768 invalid-input checks passed");
    return 0;
}
