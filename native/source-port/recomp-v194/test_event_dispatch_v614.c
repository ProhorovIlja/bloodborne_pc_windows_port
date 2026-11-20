/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_dispatch_v614.c"
#include <assert.h>

static int first, second, payload, seen;
static void indexed(void *item,void *arg,size_t count) {
    assert(item==&second && arg==&payload && count==2);
    ++seen;
}
static BbEventIndexed614 resolve(void *item) {
    assert(item==&second);
    return indexed;
}
static BbEventIndexed614 unresolved(void *item) { (void)item; return NULL; }
static void forwarded(void *item,void *arg) {
    assert(item==&first && arg==&payload);
    ++seen;
}
int main(void) {
    void *items[]={&first,&second};
    assert(bb_event_indexed_v614(items,2,&payload,1,resolve)==1 && seen==1);
    assert(bb_event_indexed_v614(items,2,&payload,2,resolve)==0 && seen==1);
    assert(bb_event_indexed_v614(items,2,&payload,UINT32_MAX,resolve)==0 && seen==1);
    assert(bb_event_indexed_v614(items,2,&payload,1,unresolved)==-1 && seen==1);
    assert(bb_event_forward_v614(&first,&payload,forwarded)==1 && seen==2);
    assert(bb_event_forward_v614(&first,&payload,NULL)==-1 && seen==2);
    return 0;
}
