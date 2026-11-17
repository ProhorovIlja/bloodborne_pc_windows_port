/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Isolated constructor #90 heap seed. The backing buffer is caller-owned;
 * no direct-memory reservation, registration, or game executable is needed.
 * Compare Paleblood game/engine/regular_heap_initialize.cpp (GPL-2.0-or-later)
 * for the shared DLRegularHeap layout; this owner has its own mutex wrapper. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>

enum { HEAP = 0x440, OWNER = 0x451 };
typedef int (*mutex_fn)(void *);
static void put(unsigned char *p, uint64_t v) {
    for (unsigned i=0;i<8;++i) p[i]=(unsigned char)(v>>(8*i));
}
static int registry_seed(unsigned char *o, size_t os, unsigned char *m, size_t len,
                         mutex_fn ready, mutex_fn init) {
    uintptr_t a=(uintptr_t)m, x=(uintptr_t)o;
    if (!o || !m || sizeof(uintptr_t)!=8 || os<OWNER || (x&7) ||
        !ready || !init || len<8 || a>UINTPTR_MAX-len || a>UINTPTR_MAX-23 ||
        x>UINTPTR_MAX-OWNER || (x<a+len && a<x+OWNER)) return 0;
    uintptr_t first=(a+23)&~(uintptr_t)15, end=(a+len-8)&~(uintptr_t)15;
    if (end<first) return 0; /* reject unsigned underflow before touching memory */
    if (!ready(o+0x440)) {
        if (init(o+0x448)!=0) return 0;
        o[0x450]=1;
    }
    const uint64_t capacity=end-first;
    if (capacity<64) { memset(o,0,HEAP); return 0; }
    unsigned bucket=0;
    for (uint64_t i=capacity;i>1;i>>=1) ++bucket;
    for (unsigned i=0;i<64;++i) {
        size_t off=0x18+16*i;
        put(o+off+16,x+off);
        put(o+off+24,x+off);
    }
    uintptr_t lo=first-16, hi=end-16;
    unsigned char *b=m+(lo+8-a), *e=m+(hi-a);
    size_t off=0x18+16*bucket;
    put(o,UINT64_C(1)<<bucket);
    put(o+8,first); put(o+0x10,end); put(o+0x18,capacity); put(o+0x20,0);
    put(o+0x428,lo); put(o+0x430,hi); put(o+0x438,capacity);
    put(o+off+16,lo); put(o+off+24,lo);
    put(b,hi|2); put(b+8,x+off); put(b+16,x+off);
    put(e,lo); put(e+8,lo|1);
    return 1;
}

#ifdef BB_PRIVATE_DIFFERENTIAL
int candidate(unsigned char *o,size_t os,unsigned char *m,size_t len,mutex_fn r,mutex_fn i) {
    return registry_seed(o,os,m,len,r,i);
}
#else
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d\n",__LINE__); return 1; } } while (0)
static int calls, result;
static int not_ready(void *p) { (void)p; ++calls; return 0; }
static int is_ready(void *p) { (void)p; ++calls; return 1; }
static int initialize(void *p) { (void)p; ++calls; return result; }
static uint64_t get(const unsigned char *p) {
    uint64_t n=0; for (unsigned i=0;i<8;++i) n|=(uint64_t)p[i]<<(8*i); return n;
}
int main(void) {
    const size_t n=0x100000;
    _Alignas(16) unsigned char o[0x460], before[sizeof o];
    unsigned char *m=malloc(n+32);
    CHECK(m!=NULL);
    for (unsigned shift=0;shift<16;++shift) {
        memset(o,0xa5,sizeof o); memset(m,0x5a,n+32); calls=0;
        unsigned char *p=m+shift;
        uintptr_t a=(uintptr_t)p, x=(uintptr_t)o;
        uintptr_t first=(a+23)&~(uintptr_t)15, end=(a+n-8)&~(uintptr_t)15;
        CHECK(registry_seed(o,sizeof o,p,n,not_ready,initialize)==1 && calls==2);
        CHECK(get(o)==(UINT64_C(1)<<19) && get(o+8)==first && get(o+16)==end);
        CHECK(get(o+0x18)==end-first && get(o+0x438)==end-first && get(o+0x20)==0);
        CHECK(get(o+0x428)==first-16 && get(o+0x430)==end-16);
        CHECK(get(o+0x18+16*19+16)==first-16 && get(o+0x18+16*19+24)==first-16);
        CHECK(get(o+0x28)==x+0x18 && get(o+0x30)==x+0x18);
        CHECK(get(p+(first-a)-8)==((end-16)|2) && get(p+(end-a)-8)==((first-16)|1));
        CHECK(o[0x440]==0xa5 && o[0x450]==1 && o[0x451]==0xa5 && p[n-1]==0x5a);
    }
    memset(o,0xa5,sizeof o); memcpy(before,o,sizeof o); calls=0; result=-1;
    CHECK(!registry_seed(o,sizeof o,m,n,not_ready,initialize) && calls==2);
    CHECK(memcmp(o,before,sizeof o)==0);
    calls=0;
    CHECK(!registry_seed(o,HEAP,m,n,is_ready,initialize) && calls==0);
    CHECK(!registry_seed(o,sizeof o,o+16,128,is_ready,initialize) && calls==0);
    CHECK(!registry_seed(o,sizeof o,m,8,is_ready,initialize) && calls==0);
    CHECK(!registry_seed(o,sizeof o,NULL,n,is_ready,initialize) && calls==0);
    CHECK(memcmp(o,before,sizeof o)==0);
    CHECK(!registry_seed(o,sizeof o,m,48,is_ready,initialize) && calls==1);
    for (unsigned i=0;i<HEAP;++i) CHECK(o[i]==0);
    CHECK(memcmp(o+HEAP,before+HEAP,sizeof o-HEAP)==0);
    CHECK(registry_seed(o,sizeof o,m,96,is_ready,initialize) && calls==2 && o[0x450]==0xa5);
    free(m);
    puts("registry heap seed: OK");
    return 0;
}
#endif
