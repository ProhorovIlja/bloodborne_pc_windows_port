/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>

typedef void (*BbEventIndexed614)(void *,void *,size_t);
typedef void (*BbEventForward614)(void *,void *);

/* Host view of #125: the second argument is forwarded
 * unchanged; the third register holds the count at the tail jump. The resolver supplies a typed host target for slot +0x28. */
int bb_event_indexed_v614(void *const *items,size_t count,void *arg,uint32_t index,
                         BbEventIndexed614 (*resolve)(void *)) {
    if (index>=count) return 0;
    if (!items || !items[index] || !resolve) return -1;
    void *item=items[index];
    BbEventIndexed614 call=resolve(item);
    if (!call) return -1;
    call(item,arg,count);
    return 1;
}

/* Host view of #157: the original tail dispatches slot +0x38 on self. */
int bb_event_forward_v614(void *self,void *arg,BbEventForward614 call) {
    if (!self || !call) return -1;
    call(self,arg);
    return 1;
}
