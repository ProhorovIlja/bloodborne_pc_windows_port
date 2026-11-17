/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct {
    void *source;
    const void *event;
    void *target,*member;
    uint32_t extra,flags;
} BbDispatchRow620;
typedef struct {
    uint64_t tag;
    BbDispatchRow620 *begin,*end,*limit;
    void *allocator;
} BbDispatchLane620;
typedef struct {
    BbDispatchRow620 *(*allocate)(void *,size_t,size_t);
    void (*free)(void *,BbDispatchRow620 *);
    void (*last)(void *,void *);
    void *ctx;
} BbDispatchOps620;
_Static_assert(sizeof(BbDispatchRow620)==40 && sizeof(BbDispatchLane620)==40 &&
    offsetof(BbDispatchRow620,extra)==32,"dispatch ABI");

static uint32_t read_ref620(const void *p) {
    uint32_t x; memcpy(&x,(const unsigned char *)p+8,4); return x;
}
static void write_ref620(void *p,uint32_t x) { memcpy((unsigned char *)p+8,&x,4); }
static void retain620(void *p) {
    if (!p) return;
    uint32_t x=read_ref620(p),mask=UINT32_C(0x3fff8000);
    write_ref620(p,(x&~mask)|((x+0x8000)&mask));
}
static void drop620(void *p,const BbDispatchOps620 *o) {
    if (!p) return;
    uint32_t x=read_ref620(p),mask=UINT32_C(0x3fff8000),n=(x-0x8000)&mask;
    write_ref620(p,(x&~mask)|(n?n:mask));
    if (!n) o->last(o->ctx,p);
}
static void assign_ref620(void **dst,void *const *src,const BbDispatchOps620 *o) {
    if (*dst==*src) return;
    if (*dst) { drop620(*dst,o); *dst=NULL; }
    *dst=*src;
    retain620(*dst);
}
static void assign620(BbDispatchRow620 *dst,const BbDispatchRow620 *src,const BbDispatchOps620 *o) {
    assign_ref620(&dst->source,&src->source,o);
    dst->event=src->event;
    assign_ref620(&dst->target,&src->target,o);
    dst->member=src->member;
    dst->extra=src->extra;
    dst->flags=src->flags;
}
static void clear620(BbDispatchRow620 *r,const BbDispatchOps620 *o) {
    drop620(r->target,o); r->target=NULL;
    drop620(r->source,o); r->source=NULL;
}

/* 31 live lanes, serialized, no re-entry or vector mutation from host callbacks.
 * Return 0 for a missing identity, 1 for insert/update, negative on failure.
 * Allocation failure is terminal; pruning may already have removed stale rows. */
int bb_event_dispatch_v620(BbDispatchLane620 *lanes,void *source,const void *event,
    void *target,void *member,uint32_t flags,uint32_t extra,const BbDispatchOps620 *o) {
    if (!source || !event || !target || !member) return 0;
    if (!lanes || !o || !o->allocate || !o->free || !o->last) return -1;
    BbDispatchLane620 *v=&lanes[(uintptr_t)source%31];
    uintptr_t b=(uintptr_t)v->begin,e=(uintptr_t)v->end,l=(uintptr_t)v->limit;
    if (((b|e|l)&7) || b>e || e>l || (!b && l) || (e-b)%40 || (l-b)%40 || !v->allocator)
        return -1;
    size_t used=(e-b)/40,cap=(l-b)/40;
    for (size_t i=0;i<used;++i) {
        BbDispatchRow620 *r=v->begin+i;
        if (r->source!=source || r->event!=event || r->target!=target || r->member!=member) continue;
        retain620(source); retain620(target);
        r->extra=extra; r->flags=flags;
        drop620(target,o); drop620(source,o);
        return 1;
    }
    if (used==cap && cap>=21) {
        for (size_t i=0;i<used;) {
            const BbDispatchRow620 *r=v->begin+i;
            if (r->source && r->target && (read_ref620(r->source)&UINT32_C(0x40000000)) &&
                (read_ref620(r->target)&UINT32_C(0x40000000))) { ++i; continue; }
            for (size_t j=i+1;j<used;++j) assign620(v->begin+j-1,v->begin+j,o);
            clear620(v->begin+used-1,o);
            --used; --v->end;
        }
    }
    retain620(source); retain620(target);
    if (used==cap) {
        const size_t max=SIZE_MAX/40;
        size_t n=cap/2<=max-cap?cap+cap/2:cap;
        if (n<=cap && cap<max) n=cap+1;
        BbDispatchRow620 *p=n>cap?o->allocate(v->allocator,n*40,8):NULL;
        if (!p) { drop620(target,o); drop620(source,o); return -2; }
        for (size_t i=0;i<used;++i) {
            p[i]=v->begin[i]; retain620(p[i].source); retain620(p[i].target);
        }
        for (size_t i=0;i<used;++i) clear620(v->begin+i,o);
        if (v->begin) o->free(v->allocator,v->begin);
        v->begin=p; v->end=p+used; v->limit=p+n;
    }
    *v->end=(BbDispatchRow620){source,event,target,member,extra,flags};
    retain620(source); retain620(target);
    ++v->end;
    drop620(target,o); drop620(source,o);
    return 1;
}
