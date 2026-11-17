/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdint.h>
#include <string.h>
#include <float.h>

_Static_assert(sizeof(void *)==8 && sizeof(float)==4 && FLT_RADIX==2 && FLT_MANT_DIG==24,
               "64-bit host with IEEE binary32 required");
static void *ptr607(const unsigned char *p) { void *v; memcpy(&v,p,8); return v; }
static uint32_t word607(const unsigned char *p) { uint32_t v; memcpy(&v,p,4); return v; }
static uint32_t radians607(uint32_t bits) {
    const float factor=0x1.1df46ap-6f;
    float x; memcpy(&x,&bits,4); x=factor*x; memcpy(&bits,&x,4); return bits;
}
/* Live object graph supplied by the host. Notification dispatch is supplied
 * explicitly rather than loading a PS4 vtable. A disabled object needs no graph. */
int bb_yaw_pitch_v607(unsigned char *o,void (*notify)(void *)) {
    if (!o) return -1;
    if (o[0xc]&1) return 0;
    const unsigned char *source=ptr607(o+0x18);
    unsigned char *out=ptr607(o+0x20);
    void *listener=ptr607(o+0x10);
    if (!source || !out || (listener && !notify)) return -1;
    const unsigned char *a=ptr607(source+0x110),*b=ptr607(source+0x118);
    if (!a || !b) return -1;
    a=ptr607(a+0x148); b=ptr607(b+0x148);
    if (!a || !b) return -1;
    uint32_t x=word607(a+0x14),y=word607(b+0x14);
    const unsigned flags=o[0x30];
    if (!(flags&2)) { x=radians607(x); y=radians607(y); }
    if (flags&8) x^=UINT32_C(0x80000000);
    if (flags&4) y^=UINT32_C(0x80000000);
    if (flags&1) { uint32_t t=x; x=y; y=t; }
    const uint64_t result=((uint64_t)y<<32)|x;
    memcpy(o+0x28,&result,8); memcpy(out,&result,8);
    if (listener) notify(listener);
    return 1;
}
