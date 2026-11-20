/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_walk_v615.c"
#include <assert.h>

struct State { void *target,*replacement; unsigned releases,cleanups; };
static int release(void *ctx,void *node) {
    struct State *s=ctx;
    assert((read615((unsigned char *)node+8)&0x3fff8000)==0x3fff8000);
    ++s->releases; s->target=s->replacement; return 0;
}
static int cleanup(void *ctx,void *self,void *const *target) {
    struct State *s=ctx; assert(self && target==&s->target); ++s->cleanups; return 0;
}
int main(void) {
    unsigned char a[0x160]={0}, b[0x160]={0};
    struct State s={a,b,0,0};
    BbEventWalk615 op={release,cleanup,&s};
    assert(bb_event_walk_v615(a,&s.target,2,&op)==1);
    assert(read615(a+0x15c)==1 && s.releases==1 && s.target==b);
    unsigned char *next=b;
    memcpy(a+0x128,&next,sizeof next);
    write615(b+8,0xc0001234);
    assert(bb_event_walk_v615(a,&s.target,2,&op)==1);
    assert(read615(b+8)==0xffff9234 && s.releases==2);
    s.target=NULL;
    assert(bb_event_walk_v615(a,&s.target,2,&op)==2 && s.cleanups==1);
    next=a;
    memcpy(b+0x128,&next,sizeof next);
    assert(bb_event_walk_v615(a,&s.target,3,&op)==-1 && s.cleanups==1);
    write615(b+8,0);
    op.release=NULL;
    assert(bb_event_walk_v615(a,&s.target,3,&op)==-2);
    return 0;
}
