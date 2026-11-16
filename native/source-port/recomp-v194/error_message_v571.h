/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ERROR_MESSAGE_V571_H
#define BB_ERROR_MESSAGE_V571_H
#include "error_category_v570.h"
#include <stddef.h>
#include <string.h>
struct bb_message_v571 {
    uint64_t opaque;
    union { char text[16]; char *heap; } storage;
    uint64_t length, capacity;
};
_Static_assert(sizeof(struct bb_message_v571)==40, "expected 64-bit string layout");
_Static_assert(offsetof(struct bb_message_v571,length)==24, "expected string length slot");
typedef const char *(*bb_error_lookup_v571)(void *, int32_t);
typedef void *(*bb_message_alloc_v571)(void *, size_t);
/* Caller supplies a fresh result, a PS4-domain lookup, and matching allocator.
 * Returns failure rather than implementing the original C++ exception ABI. */
static inline int bb_error_message_v571(struct bb_error_categories_v570 c,
    uint64_t self,int32_t code,bb_error_lookup_v571 lookup,
    bb_message_alloc_v571 alloc,void *ctx,struct bb_message_v571 *out) {
    if (!out || !bb_error_name_v570(c,self)) return 0;
    const char *text;
    if (self==c.iostream && code==1) text="iostream stream error";
    else {
        if (!lookup) return 0;
        text=lookup(ctx,code);
        if (!text) text="unknown error";
    }
    size_t n=strlen(text), cap=n|15u;
    char *dst=out->storage.text;
    if (n>15) {
        if (!alloc || cap==SIZE_MAX || !(dst=alloc(ctx,cap+1))) return 0;
        out->storage.heap=dst;
    }
    memcpy(dst,text,n+1);
    out->length=n;
    out->capacity=cap;
    return 1;
}
#endif
