/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "registry_batch_v651.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

struct tracker { size_t calls, live, fail; };
static void *alloc(void *ctx,size_t size,size_t align) {
    struct tracker *t=ctx;
    assert(align==8 && size && size%16==0);
    if (++t->calls==t->fail) return NULL;
    void *p=malloc(size);
    assert(p);
    ++t->live;
    return p;
}
static void release(void *ctx,void *p) {
    struct tracker *t=ctx;
    assert(t->live && p);
    --t->live;
    free(p);
}
int main(void) {
    struct tracker t={0};
    struct bb_registry_v651 v={0};
    const struct bb_registry_allocator_v651 a={&t,alloc,release};
    const uint64_t tags[]={10,20,0,40};
    const struct bb_registry_row_v650 row={1,2,3,4};
    for (size_t i=1;i<=2;++i) {
        t.fail=t.calls+i;
        assert(!bb_registry_register_v651(&v,&a,row,tags));
        assert(!v.rows && !v.pending && !v.count && !v.used && !t.live);
    }
    t.fail=0;
    /* Rollback with both arrays populated and both scheduled to grow. */
    const struct bb_pending_v651 old_pending[]={{10,1},{20,1},{0,1},{40,1}};
    v=(struct bb_registry_v651){alloc(&t,sizeof row,8),
        alloc(&t,sizeof old_pending,8),1,1,4,4};
    v.rows[0]=row;
    memcpy(v.pending,old_pending,sizeof old_pending);
    const struct bb_registry_v651 before=v;
    for (size_t i=1;i<=2;++i) {
        t.fail=t.calls+i;
        assert(!bb_registry_register_v651(&v,&a,row,tags));
        assert(v.rows==before.rows && v.pending==before.pending &&
               v.count==1 && v.capacity==1 && v.used==4 && v.reserved==4 && t.live==2);
        assert(!memcmp(v.rows,&row,sizeof row));
        assert(!memcmp(v.pending,old_pending,sizeof old_pending));
    }
    release(&t,v.rows);
    release(&t,v.pending);
    v=(struct bb_registry_v651){0};
    t.fail=0;
    size_t rc=512,pc=512;
    for (size_t i=0;i<2048;++i) {
        if (i==rc) rc+=rc/2;
        for (size_t j=0;j<4;++j) if (4*i+j==pc) pc+=pc/2;
        struct bb_registry_row_v650 x={i+1,2,3,(i*13)%17};
        assert(bb_registry_register_v651(&v,&a,x,tags));
        assert(v.count==i+1 && v.used==4*(i+1) && v.capacity==rc && v.reserved==pc && t.live==2);
        for (size_t j=1;j<v.count;++j) assert(v.rows[j-1].key<v.rows[j].key ||
            (v.rows[j-1].key==v.rows[j].key && v.rows[j-1].object<v.rows[j].object));
        for (size_t j=0;j<4;++j) assert(v.pending[4*i+j].target==tags[j] && v.pending[4*i+j].object==i+1);
    }
    release(&t,v.rows);
    release(&t,v.pending);
    assert(!t.live && !bb_registry_capacity_v651(SIZE_MAX/32,SIZE_MAX/32,1,32));
    assert(!bb_registry_capacity_v651(2,1,1,16));
    const size_t max=SIZE_MAX/32;
    assert(bb_registry_capacity_v651(max-max/4,max-max/4,max/4,32)==max);
    assert(bb_registry_capacity_v651(max-max/4,max-max/4,max/4+1,32)==0);
    assert(bb_registry_capacity_v651(1,1,1,32)==2);
    puts("2048 registrations, 8192 pending records, 4 allocation failures and capacity bounds OK");
}
