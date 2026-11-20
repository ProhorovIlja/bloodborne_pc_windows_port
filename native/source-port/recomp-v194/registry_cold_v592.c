/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdint.h>
#include <stddef.h>
#include <string.h>

typedef void *(*aligned_fn)(void *,size_t,size_t);
typedef void *(*alloc_fn)(void *,size_t);
typedef void (*lock_fn)(void *);
static void word(void *p,uintptr_t value) { memcpy(p,&value,8); }
/* Single cold start after V591 seed. Callback storage is live and disjoint.
 * The owner retains partial state on terminal failure. Never retry in place.
 * This stops before TLS diagnostics and factory finalization. */
int bb_registry_cold_v592(unsigned char *owner,size_t size,aligned_fn aligned,
                          alloc_fn allocate,lock_fn lock,lock_fn unlock) {
    if (!owner || size<0x48c || sizeof(uintptr_t)!=8 || !aligned ||
        !allocate || !lock || !unlock) return -1;
    uintptr_t prior=0,available=0;
    memcpy(&prior,owner+0x468,8);
    if (prior) return -1;
    const uint32_t page=0x1000;
    memcpy(owner+0x488,&page,4);
    unsigned char *meta=aligned(owner+0x458,0x28,8);
    if (!meta) return 0;
    memset(meta+8,0,24);
    word(meta+0x20,(uintptr_t)owner);
    word(owner+0x468,(uintptr_t)meta);
    lock(owner+0x440);
    memcpy(&available,owner+0x18,8);
    void *entries=available>=0x300?allocate(owner,0x300):NULL;
    unlock(owner+0x440);
    if (!entries) return 0;
    word(meta+8,(uintptr_t)entries);
    word(meta+0x10,(uintptr_t)entries);
    word(meta+0x18,(uintptr_t)entries+0x300);
    return 1;
}

#ifdef BB_REGISTRY_TEST
#include <assert.h>
#include <stdio.h>
static unsigned char obj[0x490],meta[0x28],entries[0x300];
static unsigned trace, mode;
static void *aligned(void *p,size_t n,size_t a) {
    assert(p==obj+0x458 && n==0x28 && a==8 && trace==0); trace=1;
    return mode==1?NULL:meta;
}
static void lock(void *p) { assert(p==obj+0x440 && trace==1); trace=2; }
static void *allocate(void *p,size_t n) {
    assert(p==obj && n==0x300 && trace==2); trace=3;
    return mode==3?NULL:entries;
}
static void unlock(void *p) {
    assert(p==obj+0x440 && trace==(mode==2?2:3)); trace=4;
}
static uintptr_t get(const void *p) { uintptr_t v; memcpy(&v,p,8); return v; }
int main(void) {
    for (mode=0;mode<4;++mode) {
        memset(obj,0,sizeof obj); memset(meta,0xa5,sizeof meta);
        memset(entries,0x5a,sizeof entries); trace=0;
        word(obj+0x18,mode==2?0x2ff:0x300);
        assert(bb_registry_cold_v592(obj,sizeof obj,aligned,allocate,lock,unlock)==(mode==0));
        assert(trace==(mode==1?1:4) && get(obj+0x488)==0x1000);
        assert(get(obj+0x468)==(mode==1?0:(uintptr_t)meta));
        assert(meta[0]==0xa5 && entries[0]==0x5a && entries[0x2ff]==0x5a);
        if (mode!=1) {
            assert(get(meta+0x20)==(uintptr_t)obj);
            assert(get(meta+8)==(mode==0?(uintptr_t)entries:0));
            assert(get(meta+0x10)==get(meta+8));
            assert(get(meta+0x18)==(mode==0?(uintptr_t)entries+0x300:0));
            assert(bb_registry_cold_v592(obj,sizeof obj,aligned,allocate,lock,unlock)==-1);
        }
    }
    assert(bb_registry_cold_v592(obj,0x48b,aligned,allocate,lock,unlock)==-1);
    puts("registry cold bootstrap: OK");
}
#endif
