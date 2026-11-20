/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct object { uint64_t guest, table; unsigned char initial[16]; };
struct step { uint32_t ordinal, index; };
#ifndef V469_PLAN
#define V469_PLAN "startup_fixture_v469.h"
#endif
#include V469_PLAN
#define COUNT(a) (sizeof(a)/sizeof((a)[0]))
_Static_assert(COUNT(objects)>0 && COUNT(objects)<=4096, "object limit");
_Static_assert(COUNT(steps)>0 && COUNT(steps)<=65536, "step limit");
static unsigned char state[COUNT(objects)][18];
int native_guarded_leaf_v463(unsigned char *, size_t, size_t, uint64_t);

int main(void) {
    for (size_t i=0; i<COUNT(objects); ++i) {
        const uint64_t a=objects[i].guest, t=objects[i].table;
        if (!a || a>UINT64_MAX-15 || a%8 || !t || t>UINT64_MAX-7 || t%8 ||
            (i && a<=objects[i-1].guest+15)) return 2;
    }
    uint32_t prev=0;
    for (size_t i=0; i<COUNT(steps); ++i) {
        if (steps[i].ordinal<=prev || steps[i].ordinal>65536 ||
            steps[i].index>=COUNT(objects)) return 3;
        prev=steps[i].ordinal;
    }
    for (size_t i=0; i<COUNT(objects); ++i) {
        state[i][0]=0xa5; state[i][17]=0x5a;
        memcpy(state[i]+1, objects[i].initial, 16);
    }
    for (size_t i=0; i<COUNT(steps); ++i) {
        const uint32_t k=steps[i].index;
        unsigned char *s=state[k], expected[18];
        const uint64_t table=objects[k].table;
        const int cold=s[9]==0;
        memcpy(expected,s,sizeof expected);
        if (cold) {
            for (unsigned j=0;j<8;++j) expected[1+j]=(unsigned char)(table>>(8*j));
            memset(expected+9,0,8); expected[9]=1;
        }
        if (native_guarded_leaf_v463(s,18,1,table)!=cold ||
            memcmp(s,expected,sizeof expected) ||
            native_guarded_leaf_v463(s,18,1,table)!=0 ||
            memcmp(s,expected,sizeof expected)) return 4;
        if (printf("%" PRIu32 " %d ",steps[i].ordinal,cold)<0) return 5;
        for (unsigned j=1;j<=16;++j)
            if (printf("%02x",(unsigned)s[j])<0) return 5;
        if (putchar('\n')==EOF) return 5;
    }
    return fflush(stdout)==EOF ? 5 : 0;
}
