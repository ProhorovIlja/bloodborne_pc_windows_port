/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
struct object { uint64_t guest, table; unsigned char initial[16]; };
struct step { unsigned ordinal,index; };
struct startup_copy_v470 { size_t source,destination; };
struct row { unsigned ordinal,count; struct startup_copy_v470 steps[4]; };
#ifndef V471_GUARDS
#define V471_GUARDS "guard_fixture_v471.h"
#endif
#ifndef V471_COPIES
#define V471_COPIES "copy_fixture_v471.h"
#endif
#include V471_GUARDS
#include V471_COPIES
#define N(a) (sizeof(a)/sizeof(*(a)))
_Static_assert(N(objects)>0 && N(objects)<=4096 && STATE_SIZE>=16 && STATE_SIZE<=1048576,"state bounds");
_Static_assert(N(steps)+N(rows)<=65536 && N(pool)>=16,"plan bounds");
static unsigned char guards[N(objects)][18], state[STATE_SIZE+2];
int native_guarded_leaf_v463(unsigned char *,size_t,size_t,uint64_t);
int native_startup_copy_v470(const struct startup_copy_v470 *,size_t,const unsigned char *,size_t,unsigned char *,size_t,unsigned char [32]);
static void hex(const unsigned char *p,size_t n) {
    for (size_t i=0;i<n;++i) printf("%02x",(unsigned)p[i]);
}
static int validate(void) {
    for (size_t i=0;i<N(objects);++i) {
        uint64_t a=objects[i].guest,t=objects[i].table;
        if (!a || a>UINT64_MAX-15 || a%8 || !t || t>UINT64_MAX-7 || t%8 ||
            (i && a<=objects[i-1].guest+15)) return 0;
    }
    for (size_t i=0;i<N(steps);++i)
        if (!steps[i].ordinal || steps[i].ordinal>65536 || steps[i].index>=N(objects) ||
            (i && steps[i-1].ordinal>=steps[i].ordinal)) return 0;
    size_t j=0;
    for (size_t i=0;i<N(rows);++i) {
        const struct row *r=&rows[i];
        if (!r->ordinal || r->ordinal>65536 || (i && rows[i-1].ordinal>=r->ordinal) ||
            (r->count!=1 && r->count!=3 && r->count!=4)) return 0;
        while (j<N(steps) && steps[j].ordinal<r->ordinal) ++j;
        if (j<N(steps) && steps[j].ordinal==r->ordinal) return 0;
        for (unsigned k=0;k<r->count;++k) {
            const struct startup_copy_v470 *s=&r->steps[k];
            if (s->source>N(pool)-16 || s->destination>STATE_SIZE-16 ||
                s->source%16 || s->destination%16) return 0;
        }
    }
    return 1;
}
int main(int argc,char **argv) {
    if (argc!=2 || (strcmp(argv[1],"--projection") && strcmp(argv[1],"--strict"))) return 1;
    const int strict=!strcmp(argv[1],"--strict");
    if (!validate()) return 2;
    for (size_t i=0;i<N(objects);++i) {
        guards[i][0]=0xa5; guards[i][17]=0x5a;
        memcpy(guards[i]+1,objects[i].initial,16);
    }
    state[0]=0xa5; state[STATE_SIZE+1]=0x5a;
    size_t i=0,j=0;
    unsigned next=1;
    while (i<N(steps) || j<N(rows)) {
        const int guard=i<N(steps) && (j==N(rows) || steps[i].ordinal<rows[j].ordinal);
        const unsigned ordinal=guard?steps[i].ordinal:rows[j].ordinal;
        if (strict && ordinal!=next) { fprintf(stderr,"MISSING %u\n",next); return 3; }
        next=ordinal+1;
        if (guard) {
            size_t k=steps[i++].index;
            unsigned char *s=guards[k];
            const int cold=s[9]==0;
            if (native_guarded_leaf_v463(s,18,1,objects[k].table)!=cold || s[0]!=0xa5 || s[17]!=0x5a) return 4;
            printf("%u %d ",ordinal,cold); hex(s+1,16);
        } else {
            unsigned char ymm[32];
            const struct row *r=&rows[j++];
            if (!native_startup_copy_v470(r->steps,r->count,pool,N(pool),state+1,STATE_SIZE,ymm) ||
                state[0]!=0xa5 || state[STATE_SIZE+1]!=0x5a) return 4;
            printf("%u ",ordinal); hex(ymm,32);
            for (unsigned k=0;k<r->count;++k) { putchar(' '); hex(state+1+r->steps[k].destination,16); }
        }
        putchar('\n');
    }
    /* A plan has no authority to assert end of startup. */
    if (strict) { fprintf(stderr,"MISSING %u\n",next); return 3; }
    return fflush(stdout)==EOF?5:0;
}
