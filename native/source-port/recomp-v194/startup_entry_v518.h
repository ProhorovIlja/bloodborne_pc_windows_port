/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_STARTUP_ENTRY_V518_H
#define BB_STARTUP_ENTRY_V518_H
#include <stddef.h>
#include <stdint.h>

/* Host callbacks for an observed startup boundary, not guest ABI bindings.
 * Guest addresses are opaque IDs. The caller bounds the startup vector. */
struct bb_entry_ops_v518 {
    void (*init_env)(void *, uint64_t, uint64_t);
    void (*register_exit)(void *, uint64_t);
    void (*init)(void *);
    uint32_t (*main_call)(void *, uint32_t, uint64_t, uint64_t);
    void (*main_returned)(void *, uint32_t);
    void (*exit_call)(void *, uint32_t);
};
enum bb_entry_result_v518 { BB_ENTRY_INVALID_V518, BB_ENTRY_EXIT_RETURNED_V518 };

static inline enum bb_entry_result_v518 bb_entry_v518(
        const struct bb_entry_ops_v518 *ops, void *ctx, const unsigned char *vector,
        size_t size, uint64_t vector_id, uint64_t incoming, uint64_t fini) {
    if (!ops || !ops->init_env || !ops->register_exit || !ops->init || !ops->main_call ||
        !ops->main_returned || !ops->exit_call || !vector || size < 8 ||
        !vector_id || vector_id > UINT64_MAX-8 || !fini) return BB_ENTRY_INVALID_V518;
    uint32_t argc=0;
    for (unsigned i=0;i<4;++i) argc|=(uint32_t)vector[i]<<(8*i);
    ops->init_env(ctx,vector_id,incoming);
    ops->register_exit(ctx,incoming);
    ops->register_exit(ctx,fini);
    ops->init(ctx);
    const uint32_t result=ops->main_call(ctx,argc,vector_id+8,0);
    ops->main_returned(ctx,result);
    ops->exit_call(ctx,result);
    return BB_ENTRY_EXIT_RETURNED_V518;
}
#endif
