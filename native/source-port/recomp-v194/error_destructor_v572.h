/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ERROR_DESTRUCTOR_V572_H
#define BB_ERROR_DESTRUCTOR_V572_H
/* Host-side adapters. The caller supplies the allocator that owns self.
 * Never call the deleting slot on the static startup objects. */
typedef void (*bb_error_release_v572)(void *, void *);
static inline void bb_error_destroy_v572(void *self) {
    (void)self;
}
static inline int bb_error_delete_v572(void *self, bb_error_release_v572 release, void *ctx) {
    if (!release) return 0;
    release(ctx,self);
    return 1;
}
#endif
