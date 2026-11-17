/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "member_insert_v609.h"
#include <assert.h>
#include <stdlib.h>

typedef struct {
    struct bb_vector_block_v541 live;
    unsigned calls, frees, fail;
} Test;
static int alloc(void *v,uint64_t owner,size_t n,struct bb_vector_block_v541 *b) {
    Test *t=v; assert(owner==42);
    if (++t->calls==t->fail) return 0;
    assert(n==(t->calls==1?128u:192u));
    unsigned char *p=calloc(1,n); assert(p);
    *b=(struct bb_vector_block_v541){p,n,(uintptr_t)p};
    t->live=*b;
    return 1;
}
static int release(void *v,uint64_t owner,uint64_t p) {
    Test *t=v; assert(owner==42 && p!=t->live.va);
    ++t->frees;
    free((void *)(uintptr_t)p);
    return 1;
}
int main(void) {
    for (unsigned fail=0;fail<=2;++fail) {
        Test t={.fail=fail};
        unsigned char h[40]={0}, before[40];
        bb_arena_store_v527(h,99); bb_arena_store_v527(h+32,42);
        const char *names[]={"abc","a","xyz","pq","uvw",""};
        const uint64_t order[]={6,2,4,1,3,5};
        for (unsigned i=0;i<6;++i) {
            struct bb_vector_block_v541 old=t.live;
            memcpy(before,h,40);
            enum bb_class_v554 rc=bb_member_insert_v609(h,40,(uintptr_t)h,&old,i+1,
                   names[i],i+100,&t,alloc,release);
            if ((fail==1 && i==0) || (fail==2 && i==4)) {
                assert(rc==BB_CLASS_STOP && !memcmp(before,h,40) && !t.frees);
                break;
            }
            assert(rc==BB_CLASS_OK && bb_vector_word_v541(h)==99);
        }
        if (!fail) {
            assert(t.calls==2 && t.frees==1);
            assert(bb_vector_word_v541(h+16)-t.live.va==192);
            for (unsigned i=0;i<6;++i) {
                unsigned char *p=t.live.data+32*i;
                assert(bb_vector_word_v541(p)==order[i]);
                assert(bb_vector_word_v541(p+16)==99+order[i]);
                assert(bb_vector_word_v541(p+24)==strlen(names[order[i]-1]));
            }
        }
        free(t.live.data);
    }
    return 0;
}
