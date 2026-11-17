/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_event_v621.c"
#include "member_register_v612.c"
#include <assert.h>
#include <stdlib.h>

typedef struct {
    BbMemberHost612 host;
    unsigned inserted, bound;
} Fixture621;
static uintptr_t *alloc621(void *p,size_t n,size_t a) {
    assert(p && a==8); return calloc(1,n);
}
static void free621(void *p,uintptr_t *x) { assert(p); free(x); }
static int init621(void *p,uintptr_t *x) { *x=(uintptr_t)p; return 0; }
static void drop621(void *p,uintptr_t x) { assert((uintptr_t)p==x); }
static int prep621(void *p) { assert(p); return 0; }
static void *heap621(void *p) { return p; }
static unsigned kind621(void *p,void *h) { assert(p==h); return 0x73; }
static int insert621(void *p,unsigned char *d) { assert(d); ++((Fixture621 *)p)->inserted; return 0; }
static int base621(void *p,unsigned char **d) { assert(p); *d=NULL; return 0; }
static void diag621(void *p,unsigned code) { (void)p; (void)code; abort(); }
static int bind621(void *p,unsigned char *d,const BbEventRecord621 *r,const char *n,const uint16_t *w) {
    Fixture621 *f=p; ++f->bound;
    return bb_member_register_v612(d,n,w,(uintptr_t)r,&f->host);
}
int main(void) {
    Fixture621 f={0};
    f.host=(BbMemberHost612){&f,&f,1,{alloc621,free621},init621,drop621};
    BbClass90State597 cls[4]={0};
    BbEventRecord621 records[4]={0};
    static const uint16_t wide[]={65,0};
    const BbClass90Ops597 op={&f,1,2,(uintptr_t)"Fixture",(uintptr_t)wide,
                             prep621,heap621,kind621,insert621,NULL,diag621};
    const unsigned ids[]={98,125,157,173};
    const BbErasedEvent621 expected[]={(BbErasedEvent621)bb_yaw_pitch_v607,
        (BbErasedEvent621)bb_event_indexed_v614,(BbErasedEvent621)bb_event_forward_v614,
        (BbErasedEvent621)bb_event_walk_v615};
    assert(bb_class_event_v621(cls,&op,base621,records,3,"A",wide,bind621,99)==-1);
    assert(!f.inserted && !f.bound && !cls[0].published && !records[0].table);
    for (unsigned i=0;i<4;++i) {
        assert(bb_class_event_v621(cls+i,&op,base621,records+i,3+i,"A",wide,bind621,ids[i])==0);
        assert(records[i].table==3+i && records[i].body==expected[i] && !records[i].adjustment);
        BbMemberRow608 *row;
        memcpy(&row,cls[i].descriptor+0x20,8);
        assert(row && !strcmp(row->name,"A"));
        BbMemberObject611 *m=row->member;
        assert(m->owner==cls[i].published && m->handlers.end-m->handlers.begin==1);
        assert(m->handlers.begin[0]==(uintptr_t)(records+i));
        free(m->handlers.begin); free(m); free(row);
    }
    assert(f.inserted==4 && f.bound==4);
    return 0;
}
