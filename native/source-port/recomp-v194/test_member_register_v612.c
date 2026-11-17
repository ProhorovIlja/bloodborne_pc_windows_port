/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "member_register_v612.c"
#include "yaw_pitch_v607.c"
#include <assert.h>
#include <stdlib.h>

typedef struct { BbMemberClass608 cls; uint64_t limit,allocator; } Descriptor;
_Static_assert(offsetof(Descriptor,allocator)==0x38,"descriptor");
typedef struct { unsigned count,fail,init,drop,frees; size_t trace[20]; } Heap;
static uintptr_t *alloc612(void *p,size_t n,size_t a) {
    Heap *h=p; assert(a==8 && h->count<20);
    h->trace[h->count++]=n;
    return h->count==h->fail?NULL:calloc(1,n);
}
static void free612(void *p,uintptr_t *x) { ++((Heap *)p)->frees; free(x); }
static int init612(void *p,uintptr_t *x) { ++((Heap *)p)->init; *x=21; return 0; }
static void drop612(void *p,uintptr_t x) { assert(x==21); ++((Heap *)p)->drop; }
int main(void) {
    for (unsigned f=0;f<=3;++f) {
        Heap heap={.fail=f};
        Descriptor parent={.allocator=(uintptr_t)&heap};
        Descriptor child={.cls={.parent=&parent.cls},.allocator=(uintptr_t)&heap};
        const BbMemberHost612 host={&heap,&heap,1,{alloc612,free612},init612,drop612};
        const uintptr_t callback=(uintptr_t)&bb_yaw_pitch_v607;
        int rc=bb_member_register_v612(&parent,"OnValueChanged",NULL,callback,&host);
        assert(rc==(f==3?-2:f?0:1));
        assert(heap.count==(f?f:3));
        assert(heap.trace[0]==128);
        if (!f || f>1) assert(heap.trace[1]==136);
        if (!f || f==3) assert(heap.trace[2]==32);
        if (f==1) assert(!parent.cls.begin);
        if (f==2) assert(parent.cls.begin==parent.cls.end && !heap.init);
        if (!f || f==3) {
            BbMemberObject611 *m=parent.cls.begin->member;
            assert(m->owner==&parent && m->lock_ready && heap.init==1);
            if (!f) {
                for (unsigned j=0;j<6;++j)
                    assert(bb_member_register_v612(&child,"OnValueChanged",NULL,callback,&host)==1);
                assert(!child.cls.begin && heap.count==5 && heap.trace[3]==48 && heap.trace[4]==72);
                assert(m->handlers.end-m->handlers.begin==7);
                unsigned char disabled[0x38]={[0xc]=1};
                for (unsigned j=0;j<7;++j) {
                    int (*call)(unsigned char *,void (*)(void *))=(void *)m->handlers.begin[j];
                    assert(call(disabled,NULL)==0);
                }
            } else assert(!m->handlers.begin);
            free(m->handlers.begin); free(m);
        }
        free((void *)parent.cls.begin);
    }
    return 0;
}
