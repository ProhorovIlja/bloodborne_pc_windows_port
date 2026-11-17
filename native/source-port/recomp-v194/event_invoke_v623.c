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

typedef struct {
    void *receiver,*argument;
    uint32_t value;
} BbInvokeArgs623;
static int decode623(unsigned kind,unsigned char *frame,size_t size,intptr_t adjustment,
                     BbInvokeArgs623 *out) {
    if (kind!=98 && kind!=125 && kind!=157) return -1;
    if (!frame || size<0x590) return -1;
    void *receiver=ptr623(frame+0x588);
    if (!receiver) return -1;
    uintptr_t base=(uintptr_t)receiver, off=(uintptr_t)adjustment;
    if ((adjustment<0 && base<0-off) ||
        (adjustment>=0 && base>UINTPTR_MAX-off) || !(base+off)) return -1;
    receiver=(void *)(base+off);
    const unsigned char *arg=frame+(kind==157?0x210:0x200);
    if (kind!=98 && (frame[0x45a]&1)) {
        arg=ptr623(frame+0x118);
        if (!arg) return -1;
    }
    *out=(BbInvokeArgs623){.receiver=receiver};
    if (kind==125) out->argument=ptr623(arg);
    if (kind!=98) memcpy(&out->value,arg+(kind==125?8:0),4);
    return 0;
}

/* Final invocation only, after the retail type/receiver checks. All non-null
 * object and external argument pointers must describe live host storage.
 * The resolver supplies a host target; never interpret a PS4 code address.
 * Typed target signatures describe the original delivery seam, not V621's
 * normalized wrapper signatures. A native adapter must bridge the two. */
int bb_event_invoke_v623(unsigned kind,unsigned char *frame,size_t size,
                         const BbInvokeRoute623 *route) {
    BbInvokeArgs623 a;
    if (!route || (!!route->direct==!!route->resolve) ||
        decode623(kind,frame,size,route->adjustment,&a)<0) return -1;
    BbErasedInvoke623 call=route->direct;
    if (!call) call=route->resolve(a.receiver,route->virtual_offset);
    if (!call) return -1;
    frame[0x45b]&=0x7f;
    if (kind==98) ((void (*)(void *))call)(a.receiver);
    if (kind==125) ((void (*)(void *,void *,uint32_t))call)(a.receiver,a.argument,a.value);
    if (kind==157) ((void (*)(void *,uint32_t))call)(a.receiver,a.value);
    return 1;
}
