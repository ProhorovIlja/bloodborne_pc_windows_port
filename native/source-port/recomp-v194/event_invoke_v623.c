/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef void (*BbErasedInvoke623)(void);
typedef struct {
    BbErasedInvoke623 direct;
    intptr_t adjustment;
    size_t virtual_offset;
    BbErasedInvoke623 (*resolve)(void *,size_t);
} BbInvokeRoute623;
static void *ptr623(const unsigned char *p) {
    void *v; memcpy(&v,p,sizeof v); return v;
}

/* Final invocation only, after the retail type/receiver checks. All non-null
 * object and external argument pointers must describe live host storage.
 * The resolver supplies a host target; never interpret a PS4 code address.
 * Typed target signatures describe the original delivery seam, not V621's
 * normalized wrapper signatures. A native adapter must bridge the two. */
int bb_event_invoke_v623(unsigned kind,unsigned char *frame,size_t size,
                         const BbInvokeRoute623 *route) {
    if (kind!=98 && kind!=125 && kind!=157) return -1;
    if (!frame || size<0x590 || !route || (!!route->direct==!!route->resolve)) return -1;
    void *receiver=ptr623(frame+0x588);
    if (!receiver) return -1;
    uintptr_t base=(uintptr_t)receiver, off=(uintptr_t)route->adjustment;
    if ((route->adjustment<0 && base<0-off) ||
        (route->adjustment>=0 && base>UINTPTR_MAX-off) || !(base+off)) return -1;
    receiver=(void *)(base+off);
    const unsigned char *arg=frame+(kind==157?0x210:0x200);
    if (kind!=98 && (frame[0x45a]&1)) {
        arg=ptr623(frame+0x118);
        if (!arg) return -1;
    }
    BbErasedInvoke623 call=route->direct;
    if (!call) call=route->resolve(receiver,route->virtual_offset);
    if (!call) return -1;
    frame[0x45b]&=0x7f;
    uint32_t value;
    if (kind==98) ((void (*)(void *))call)(receiver);
    if (kind==125) {
        memcpy(&value,arg+8,4);
        ((void (*)(void *,void *,uint32_t))call)(receiver,ptr623(arg),value);
    }
    if (kind==157) {
        memcpy(&value,arg,4);
        ((void (*)(void *,uint32_t))call)(receiver,value);
    }
    return 1;
}
