/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "class_base_v602.c"
#include <assert.h>
#include <stdio.h>

typedef struct { unsigned prepare, allocate, kind, report, fault; } Test;
static int prepare(void *p) { Test *t=p; ++t->prepare; return t->fault==1; }
static void *alloc(void *p) { Test *t=p; ++t->allocate; return t->fault==2?NULL:p; }
static unsigned kind(void *p,void *a) { Test *t=p; assert(p==a); ++t->kind; return t->fault==3?0:0x73; }
static void report(void *p,unsigned n) { Test *t=p; assert(n==0x3e); ++t->report; }
int main(void) {
    for (unsigned f=0; f<4; ++f) {
        Test t={.fault=f};
        BbClass90Ops597 o={.ctx=&t,.base_table=1,.class_table=2,.prepare=prepare,
                           .get_allocator=alloc,.kind=kind,.diagnose=report};
        BbClass90State597 base[2]={0};
        void *cache=NULL;
        for (unsigned i=0; i<2; ++i) {
            unsigned char *result=base[i].descriptor;
            assert(bb_class_base_v602(base+i,&cache,&o,&result)==(f?-1:0));
            if (f) assert(!result && !base[i].published);
            else {
                assert(result==base[i].descriptor && result==base[i].published);
                assert(!bb_class_base_v602(base+i,&cache,&o,&result));
                assert(result==base[i].descriptor && cache==&t);
            }
        }
        assert(t.prepare==2 && t.allocate==(f==1?0:f==2?2:1));
        assert(t.kind==(f<1 || f==3?2:0) && t.report==(f==3?2:0));
    }
    puts("V602: two descriptors, shared allocator, warm getter, explicit failure: OK");
}
