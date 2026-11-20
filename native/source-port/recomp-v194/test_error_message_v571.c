/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "error_message_v571.h"
struct fixture { char heap[64]; size_t requested; unsigned calls; };
static const char *lookup(void *ctx,int32_t code) {
    struct fixture *f=ctx;
    ++f->calls;
    switch (code) {
        case 1: return "123456789012345";
        case 2: return "1234567890123456";
        case 3: return "";
        default: return NULL;
    }
}
static void *alloc(void *ctx,size_t n) {
    struct fixture *f=ctx;
    f->requested=n;
    return n<=sizeof f->heap ? f->heap : NULL;
}
int main(void) {
    const struct bb_error_categories_v570 cats={1,2,3};
    struct fixture f={0};
    struct bb_message_v571 out, before;
    memset(&out,0xa5,sizeof out);
    memcpy(&before,&out,sizeof out);
    if (bb_error_message_v571(cats,1,2,lookup,NULL,&f,&out) ||
        memcmp(&out,&before,sizeof out)) return 1;
    if (!bb_error_message_v571(cats,1,1,lookup,alloc,&f,&out) ||
        out.length!=15 || out.capacity!=15 || f.requested || out.opaque!=before.opaque ||
        strcmp(out.storage.text,"123456789012345")) return 2;
    if (!bb_error_message_v571(cats,2,2,lookup,alloc,&f,&out) ||
        out.length!=16 || out.capacity!=31 || f.requested!=32 ||
        out.storage.heap!=f.heap || strcmp(f.heap,"1234567890123456")) return 3;
    if (!bb_error_message_v571(cats,2,-1,lookup,alloc,&f,&out) ||
        out.length!=13 || strcmp(out.storage.text,"unknown error")) return 4;
    if (!bb_error_message_v571(cats,1,3,lookup,alloc,&f,&out) ||
        out.length || out.storage.text[0] || out.capacity!=15) return 5;
    const unsigned calls=f.calls;
    if (!bb_error_message_v571(cats,3,1,lookup,alloc,&f,&out) ||
        f.calls!=calls || out.length!=21 || strcmp(f.heap,"iostream stream error")) return 6;
    return 0;
}
