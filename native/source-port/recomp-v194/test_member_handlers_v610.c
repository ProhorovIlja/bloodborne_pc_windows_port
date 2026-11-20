/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "member_handlers_v610.h"
#include "yaw_pitch_v607.c"
#include <assert.h>
#include <stdlib.h>

struct State { size_t last; unsigned allocs,frees,fail; };
static uintptr_t *alloc610(void *v,size_t bytes,size_t align) {
    struct State *s=v;
    assert(align==8);
    ++s->allocs; s->last=bytes;
    return s->fail?NULL:malloc(bytes);
}
static void free610(void *v,uintptr_t *p) { ++((struct State *)v)->frees; free(p); }
int main(void) {
    struct State s={0};
    const BbHandlerOps610 op={alloc610,free610};
    BbHandlerVector610 v={.allocator=&s};
    const uintptr_t callback=(uintptr_t)&bb_yaw_pitch_v607;
    for (unsigned i=0;i<4;++i) assert(bb_handler_append_v610(&v,callback,&op)==1);
    assert(s.allocs==1 && s.last==32 && !s.frees);
    s.fail=1;
    const BbHandlerVector610 before=v;
    assert(bb_handler_append_v610(&v,callback,&op)==0);
    assert(v.begin==before.begin && v.end==before.end && v.limit==before.limit && !s.frees);
    s.fail=0;
    for (unsigned i=0;i<3;++i) assert(bb_handler_append_v610(&v,callback,&op)==1);
    assert(s.allocs==4 && s.last==72 && s.frees==2 && v.end-v.begin==7);
    unsigned char obj[0x38]={0},source[0x120]={0},a[0x150]={0},b[0x150]={0};
    unsigned char x[0x18]={0},y[0x18]={0};
    const uint32_t xv=0x3f800000,yv=0x40000000;
    uint64_t result=0;
    void *ptr=source; memcpy(obj+0x18,&ptr,8);
    ptr=&result; memcpy(obj+0x20,&ptr,8);
    ptr=a; memcpy(source+0x110,&ptr,8);
    ptr=b; memcpy(source+0x118,&ptr,8);
    ptr=x; memcpy(a+0x148,&ptr,8);
    ptr=y; memcpy(b+0x148,&ptr,8);
    memcpy(x+0x14,&xv,4); memcpy(y+0x14,&yv,4);
    obj[0x30]=2;
    for (unsigned i=0;i<7;++i) {
        assert(v.begin[i]==callback);
        int (*call)(unsigned char *,void (*)(void *))=(int (*)(unsigned char *,void (*)(void *)))v.begin[i];
        assert(call(obj,NULL)==1 && result==UINT64_C(0x400000003f800000));
    }
    free610(&s,v.begin);
    return 0;
}
