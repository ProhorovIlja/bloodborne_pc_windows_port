/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "error_destructor_v572.h"
struct fixture { void *seen; unsigned calls; };
static void release(void *ctx,void *self) {
    struct fixture *f=ctx;
    f->seen=self;
    ++f->calls;
}
int main(void) {
    int object=123;
    struct fixture f={0};
    bb_error_destroy_v572(&object);
    if (object!=123 || bb_error_delete_v572(&object,0,&f) || f.calls) return 1;
    if (!bb_error_delete_v572(&object,release,&f) || f.seen!=&object ||
            f.calls!=1 || object!=123) return 2;
    return 0;
}
